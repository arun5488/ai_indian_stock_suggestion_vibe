from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ai_indian_stock_suggestion.backend.app.config import APP_LOG_DIR, APP_LOG_LEVEL


def setup_file_logging() -> None:
    """Configure root logger once with rotating app and error files."""
    root_logger = logging.getLogger()
    if any(getattr(h, "_ai_stock_file_handler", False) for h in root_logger.handlers):
        return

    log_dir = Path(APP_LOG_DIR).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)

    level_name = APP_LOG_LEVEL.upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    app_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_handler.setLevel(level)
    app_handler.setFormatter(formatter)
    app_handler._ai_stock_file_handler = True  # type: ignore[attr-defined]

    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler._ai_stock_file_handler = True  # type: ignore[attr-defined]

    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)
