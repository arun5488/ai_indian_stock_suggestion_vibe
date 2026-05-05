from datetime import datetime
from fastapi import HTTPException

from ai_indian_stock_suggestion.backend.app.db.mongodb import (
    create_user_if_not_exists,
    get_customer_last_requests,
    update_action_taken_by_transaction,
)
from ai_indian_stock_suggestion.backend.app.services.recommendation_engine_service import (
    execute_recommendation_pipeline,
)


def _parse_contract_date(contract_date: str) -> datetime:
    return datetime.strptime(contract_date, "%d-%b-%Y")


def create_user_from_request(request_payload: dict) -> dict:
    email_id = request_payload["email_id"]
    request_date = _parse_contract_date(request_payload["date"])
    budget = float(request_payload["budget"])

    user_document, is_new_user = create_user_if_not_exists(
        email_id=email_id,
        date=request_date,
        budget=budget,
    )

    prior_row: dict | None = None
    if not is_new_user:
        recent = get_customer_last_requests(email_id, limit=100)
        prior_row = recent[1] if len(recent) > 1 else {}

    pipeline = execute_recommendation_pipeline(
        transaction_id=user_document["transaction_id"],
        customer_id=user_document["customer_id"],
        request_date=request_date,
        budget=budget,
        is_existing_customer=not is_new_user,
        prior_focus_row_for_behaviour=prior_row,
    )

    response = pipeline.to_api_dict()
    response["transaction_id"] = user_document["transaction_id"]
    return response


def update_action_taken_from_request(request_payload: dict) -> dict:
    email_id = request_payload["email_id"]
    transaction_id = request_payload["transaction_id"]
    request_date = _parse_contract_date(request_payload["date"])
    action_taken = request_payload["action_taken"].lower()

    if action_taken not in {"accepted", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="action_taken must be either 'accepted' or 'rejected'",
        )

    updated = update_action_taken_by_transaction(
        email_id=email_id,
        transaction_id=transaction_id,
        date=request_date,
        action_taken=action_taken,
    )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="No matching suggestion found for email_id/transaction_id/date",
        )

    return {"msg": "action updated"}
