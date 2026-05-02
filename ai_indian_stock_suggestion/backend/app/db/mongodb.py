import os
import secrets
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from pymongo.collection import Collection
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.database import Database
from pymongo.errors import CollectionInvalid
from ai_indian_stock_suggestion.backend.app.config import (
    MONGODB_COLLECTIONS,
    MONGODB_DB_NAME,
    MONGODB_URI,
)

load_dotenv()
logger = logging.getLogger(__name__)

_USER_ID_ATTEMPTS = 50


def _new_unique_customer_id(users_collection: Collection) -> str:
    for _ in range(_USER_ID_ATTEMPTS):
        candidate = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
        if users_collection.find_one({"customer_id": candidate}, {"_id": 1}) is None:
            return candidate
    raise RuntimeError("Unable to allocate a unique 10-digit customer_id")


def _migrate_users_indexes(users_collection: Collection) -> None:
    """Allow multiple interaction rows per email / customer_id (non-unique indexes)."""
    for name, spec in users_collection.index_information().items():
        if name == "_id_":
            continue
        key = tuple(spec.get("key", []))
        if spec.get("unique") and key in {(("email_id", 1),), (("customer_id", 1),)}:
            users_collection.drop_index(name)
    users_collection.create_index("email_id")
    users_collection.create_index("customer_id")


def get_mongo_client() -> MongoClient:
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI is not set in the environment.")
    return MongoClient(MONGODB_URI, server_api=ServerApi("1"))


def get_database() -> Database:
    if not MONGODB_DB_NAME:
        raise ValueError("MONGODB_DB_NAME is not set in the environment.")

    client = get_mongo_client()
    return client[MONGODB_DB_NAME]


def get_collection(collection_key: str) -> Collection:
    collection_name = MONGODB_COLLECTIONS.get(collection_key, collection_key)
    if not collection_name:
        raise ValueError("Collection name is empty.")
    return get_database()[collection_name]


def ensure_users_collection() -> Collection:
    db = get_database()
    users_collection_name = MONGODB_COLLECTIONS["users"]

    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "customer_id",
                "email_id",
                "date",
                "budget",
                "action_taken",
            ],
            "properties": {
                "customer_id": {"bsonType": "string"},
                "email_id": {"bsonType": "string"},
                "date": {"bsonType": "date"},
                "budget": {"bsonType": ["double", "int", "long", "decimal"]},
                "action_taken": {"bsonType": "string"},
            },
        }
    }

    if users_collection_name not in db.list_collection_names():
        try:
            db.create_collection(users_collection_name, validator=validator)
            logger.info("Created collection: %s", users_collection_name)
        except CollectionInvalid:
            pass

    users_collection = db[users_collection_name]
    _migrate_users_indexes(users_collection)
    return users_collection


def normalize_user_document(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    return out


def insert_user_record(
    email_id: str,
    date: datetime,
    budget: float,
    action_taken: str,
) -> tuple[dict, bool]:
    """
    Append one interaction row. Reuses existing customer_id for this email when present;
    otherwise allocates a random 10-digit customer_id.

    Returns (inserted_document_without__id_normalized_for_json, True if first row for email).
    """
    users_collection = ensure_users_collection()
    latest_for_email = users_collection.find_one(
        {"email_id": email_id},
        sort=[("date", -1)],
        projection={"customer_id": 1},
    )

    if latest_for_email is None:
        customer_id = _new_unique_customer_id(users_collection)
        is_first_interaction_for_email = True
    else:
        customer_id = latest_for_email["customer_id"]
        is_first_interaction_for_email = False

    created_user = {
        "customer_id": customer_id,
        "email_id": email_id,
        "date": date,
        "budget": budget,
        "action_taken": action_taken,
    }
    result = users_collection.insert_one(created_user)
    created_user["_id"] = result.inserted_id
    return normalize_user_document(created_user) or {}, is_first_interaction_for_email


def upsert_user_by_email(email_id: str, budget: float, action_taken: str) -> dict:
    """Insert one interaction row (legacy name retained for callers)."""
    doc, _ = insert_user_record(
        email_id,
        datetime.now(timezone.utc),
        budget,
        action_taken,
    )
    return doc


def get_user_by_email(email_id: str) -> dict | None:
    users_collection = ensure_users_collection()
    return users_collection.find_one({"email_id": email_id}, sort=[("date", -1)])


def create_user_if_not_exists(email_id: str, date: datetime, budget: float) -> tuple[dict, bool]:
    """
    Append a request row with empty action_taken.
    Returns (inserted row, True if this email had no prior rows).
    """
    return insert_user_record(email_id, date, budget, "")


def get_customer_last_requests(email_id: str, limit: int = 5) -> list[dict]:
    """Most recent interactions first; all fields plus stringified _id."""
    users_collection = ensure_users_collection()
    cursor = (
        users_collection.find({"email_id": email_id}).sort("date", -1).limit(limit)
    )
    docs = [normalize_user_document(d) for d in cursor]
    return [d for d in docs if d is not None]


def list_transactions_for_customer(customer_id: str, limit: int = 200) -> list[dict]:
    """Oldest-first ledger rows for behaviour analysis."""
    users_collection = ensure_users_collection()
    cursor = (
        users_collection.find({"customer_id": customer_id})
        .sort("date", 1)
        .limit(limit)
    )
    return [d for d in (normalize_user_document(dict(x)) for x in cursor) if d]


def ensure_stock_recommendations_collection() -> Collection:
    db = get_database()
    name = MONGODB_COLLECTIONS["stock_recommendations"]
    coll = db[name]
    if name not in db.list_collection_names():
        db.create_collection(name)
    coll.create_index([("customer_id", 1), ("date", -1)])
    return coll


def insert_stock_recommendation_doc(
    customer_id: str,
    date: datetime,
    budget: float,
    recommendation: dict[str, int],
) -> None:
    coll = ensure_stock_recommendations_collection()
    doc = {
        "customer_id": customer_id,
        "date": date,
        "budget": budget,
        "recommendation": recommendation,
    }
    coll.insert_one(doc)


def ping_mongodb() -> None:
    try:
        client = get_mongo_client()
        client.admin.command('ping')
        logger.info("MongoDB connectivity ping succeeded.")
    except Exception as e:
        logger.exception("MongoDB connection failed: %s", e)