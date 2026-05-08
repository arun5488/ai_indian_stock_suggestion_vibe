"""Run the Flask web UI (sidebar + in-page API results). Default port 5000."""

from ai_indian_stock_suggestion.backend.app.flask_ui import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
