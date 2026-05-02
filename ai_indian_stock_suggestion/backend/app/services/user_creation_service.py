from datetime import datetime

from ai_indian_stock_suggestion.backend.app.db.mongodb import (
    create_user_if_not_exists,
    get_customer_last_requests,
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
        customer_id=user_document["customer_id"],
        request_date=request_date,
        budget=budget,
        prior_focus_row_for_behaviour=prior_row,
    )

    return pipeline.to_api_dict()
