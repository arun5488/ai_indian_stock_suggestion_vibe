"""Flask web UI that wraps the same API logic as the FastAPI app."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for
from pydantic import EmailStr, TypeAdapter, ValidationError

from ai_indian_stock_suggestion.backend.app.db.mongodb import (
    ensure_stock_recommendations_collection,
    ensure_users_collection,
    get_customer_last_requests,
    ping_mongodb,
)
from ai_indian_stock_suggestion.backend.app.services.user_creation_service import (
    create_user_from_request,
    update_action_taken_from_request,
)
from ai_indian_stock_suggestion.backend.app.routes.user_routes import (
    UpdateActionTakenRequest,
    UserCreateRequest,
)
from ai_indian_stock_suggestion.backend.app.utils.logging_config import setup_file_logging

_BASE = Path(__file__).resolve().parent
_email_adapter = TypeAdapter(EmailStr)

app = Flask(
    __name__,
    template_folder=str(_BASE / "templates"),
    static_folder=str(_BASE / "static"),
)

_flask_ui_initialized = False


@app.before_request
def _ensure_flask_startup() -> None:
    global _flask_ui_initialized
    if _flask_ui_initialized:
        return
    setup_file_logging()
    ping_mongodb()
    ensure_users_collection()
    ensure_stock_recommendations_collection()
    _flask_ui_initialized = True


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@app.get("/")
def index():
    return redirect(url_for("page_health"))


@app.get("/health")
def page_health():
    return render_template("health.html")


@app.get("/users/create")
def page_create_user():
    return render_template("create_user.html")


@app.get("/users/customer-last-requests")
def page_customer_last_requests():
    return render_template("customer_last_requests.html")


@app.get("/users/update-action")
def page_update_action():
    return render_template("update_action.html")


@app.get("/api/health")
def api_health():
    return jsonify({"status": "ok"})


@app.post("/api/users/create")
def api_create_user():
    if not request.is_json:
        return _json_error("Expected JSON body")
    payload = request.get_json(force=True, silent=False) or {}
    try:
        body = UserCreateRequest.model_validate(payload)
    except ValidationError as e:
        return jsonify({"error": "validation_error", "details": e.errors()}), 422

    try:
        result = create_user_from_request(body.model_dump())
        return jsonify(result)
    except Exception as e:  # noqa: BLE001
        return _json_error(str(e), 500)


@app.get("/api/users/customer-last-requests")
def api_customer_last_requests():
    raw_email = request.args.get("email_id")
    if not raw_email or not str(raw_email).strip():
        return _json_error("email_id query parameter is required")
    limit_raw = request.args.get("limit", "5")
    try:
        limit = int(limit_raw)
    except ValueError:
        return _json_error("limit must be an integer")
    if limit < 1 or limit > 50:
        return _json_error("limit must be between 1 and 50")

    try:
        _email_adapter.validate_python(str(raw_email).strip())
    except ValidationError as e:
        return jsonify({"error": "validation_error", "details": e.errors()}), 422

    rows = get_customer_last_requests(email_id=str(raw_email).strip(), limit=limit)
    return jsonify(rows)


@app.put("/api/users/update-action")
def api_update_action():
    if not request.is_json:
        return _json_error("Expected JSON body")
    payload = request.get_json(force=True, silent=False) or {}
    try:
        body = UpdateActionTakenRequest.model_validate(payload)
    except ValidationError as e:
        return jsonify({"error": "validation_error", "details": e.errors()}), 422

    try:
        result = update_action_taken_from_request(body.model_dump())
        return jsonify(result)
    except Exception as e:  # noqa: BLE001
        return _json_error(str(e), 500)
