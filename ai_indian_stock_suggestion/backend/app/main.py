from fastapi import FastAPI

from ai_indian_stock_suggestion.backend.app.db.mongodb import (
    ensure_stock_recommendations_collection,
    ensure_users_collection,
    ping_mongodb,
)
from ai_indian_stock_suggestion.backend.app.routes.user_routes import router as user_router
from ai_indian_stock_suggestion.backend.app.utils.logging_config import setup_file_logging

app = FastAPI(title="AI Indian Stock Suggestion API")
app.include_router(user_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def startup_event() -> None:
    setup_file_logging()
    ping_mongodb()
    ensure_users_collection()
    ensure_stock_recommendations_collection()
