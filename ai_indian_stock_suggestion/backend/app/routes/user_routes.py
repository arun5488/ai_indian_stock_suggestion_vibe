from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr

from ai_indian_stock_suggestion.backend.app.db.mongodb import get_customer_last_requests
from ai_indian_stock_suggestion.backend.app.services.user_creation_service import (
    create_user_from_request,
    update_action_taken_from_request,
)

router = APIRouter(prefix="/users", tags=["users"])


class UserCreateRequest(BaseModel):
    email_id: EmailStr
    date: str
    budget: str


class UpdateActionTakenRequest(BaseModel):
    email_id: EmailStr
    transaction_id: str
    date: str
    action_taken: str


@router.post("/create")
def create_user_api(request_payload: UserCreateRequest) -> dict:
    return create_user_from_request(request_payload.model_dump())


@router.put("/update-action")
def update_action_api(request_payload: UpdateActionTakenRequest) -> dict:
    return update_action_taken_from_request(request_payload.model_dump())


@router.get("/customer-last-requests")
def customer_last_requests_api(
    email_id: EmailStr = Query(..., description="Customer email address"),
    limit: int = Query(5, ge=1, le=50, description="Max rows (most recent first)"),
) -> list[dict]:
    return get_customer_last_requests(email_id=str(email_id), limit=limit)
