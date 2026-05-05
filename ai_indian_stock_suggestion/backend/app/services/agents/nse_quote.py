"""Best-effort NSE last-price lookup for enrichment (quotes are indicative, delayed)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def fetch_nse_last_close_inr(symbol: str) -> tuple[float | None, str]:
    """Return last close-ish price for NSE symbol (Yahoo ``TICKER.NS``); None if unavailable."""
    raw = (symbol or "").strip().upper()
    if not raw:
        return None, ""
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed; omitting quote for %s", raw)
        return None, ""

    ticker = yf.Ticker(f"{raw}.NS")
    try:
        hist = ticker.history(period="5d")
        if hist is not None and not hist.empty:
            last = float(hist["Close"].iloc[-1])
            if last > 0:
                return last, ""
    except Exception as e:
        logger.debug("yfinance history failed for %s: %s", raw, e)
    return None, ""
