"""Best-effort NSE last-price lookup for enrichment (quotes are indicative, delayed)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _positive_inr_price(value: Any) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return v


def _price_from_history(ticker: Any) -> float | None:
    try:
        hist = ticker.history(period="5d")
        if hist is None or hist.empty:
            return None
        last = float(hist["Close"].iloc[-1])
        return _positive_inr_price(last)
    except Exception as e:
        logger.debug("yfinance history failed: %s", e)
        return None


def _price_from_info(info: dict[str, Any] | None) -> float | None:
    if not info:
        return None
    for key in (
        "currentPrice",
        "regularMarketPrice",
        "postMarketPrice",
        "previousClose",
        "regularMarketPreviousClose",
        "open",
    ):
        p = _positive_inr_price(info.get(key))
        if p is not None:
            return p
    return None


def _price_from_fast_info(fi: Any) -> float | None:
    if fi is None:
        return None
    for key in ("last_price", "previous_close", "regular_market_previous_close"):
        try:
            if hasattr(fi, "get"):
                raw = fi.get(key)
            else:
                raw = getattr(fi, key, None)
        except Exception:  # noqa: BLE001
            raw = None
        p = _positive_inr_price(raw)
        if p is not None:
            return p
    return None


def fetch_nse_last_close_inr(symbol: str) -> tuple[float | None, str]:
    """Return last close-ish price for NSE symbol (Yahoo ``TICKER.NS``); None if unavailable.

    Uses several yfinance surfaces: daily history first (most reliable for closes),
    then ``info`` / ``fast_info`` when history is empty (common for thinly traded
    names or transient API gaps). Wrong or non-NSE symbols still yield None.
    """
    raw = (symbol or "").strip().upper()
    if not raw:
        return None, ""
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed; omitting quote for %s", raw)
        return None, ""

    yahoo_symbol = f"{raw}.NS"
    ticker = yf.Ticker(yahoo_symbol)

    px = _price_from_history(ticker)
    if px is not None:
        return px, ""

    try:
        info = getattr(ticker, "info", None) or {}
        if not isinstance(info, dict):
            info = dict(info) if info else {}
    except Exception as e:  # noqa: BLE001
        logger.debug("yfinance info unavailable for %s: %s", yahoo_symbol, e)
        info = {}

    px = _price_from_info(info)
    if px is not None:
        logger.debug("NSE quote for %s from info (history empty)", raw)
        return px, ""

    try:
        fi = getattr(ticker, "fast_info", None)
    except Exception as e:  # noqa: BLE001
        logger.debug("yfinance fast_info failed for %s: %s", yahoo_symbol, e)
        fi = None

    px = _price_from_fast_info(fi)
    if px is not None:
        logger.debug("NSE quote for %s from fast_info (history empty)", raw)
        return px, ""

    logger.debug("No yfinance price for %s (.NS); ticker may be invalid or untraded", raw)
    return None, ""
