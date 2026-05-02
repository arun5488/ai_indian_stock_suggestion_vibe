"""Tavily web search for enriching stock research (live context vs generic mega-cap picks)."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from ai_indian_stock_suggestion.backend.app.config import (
    TAVILY_API_KEY,
    TAVILY_MAX_RESULTS,
    TAVILY_SEARCH_DEPTH,
    TAVILY_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def _normalize_bearer_token(raw: str) -> str:
    """Env may store `tvly-...` or `Bearer tvly-...`; curl uses `Authorization: Bearer tvly-...`."""
    k = raw.strip()
    if k.lower().startswith("bearer "):
        k = k[7:].strip()
    if k and not k.startswith("tvly-"):
        k = f"tvly-{k}"
    return k


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def build_stock_research_queries(*, budget: float, request_date_utc: datetime) -> list[str]:
    """Two complementary queries bias toward lesser-covered / thematic Indian names."""
    ym = request_date_utc.strftime("%B %Y")
    budget_inr = int(round(float(budget)))
    return [
        (
            f"{ym} Indian NSE BSE stocks mid-cap small-cap sector themes "
            f"research stock ideas diversification retail investor INR budget {budget_inr} "
            f"avoid mega-cap headline index heavyweights"
        ),
        (
            f"{ym} India equities underfollowed NSE listings thematic picks "
            f"specialty exporters industrials renewables defense SME "
            f"stock screen lesser-known liquid names analyst coverage niche"
        ),
    ]


def _flatten_results(payload: dict) -> list[dict]:
    rows = payload.get("results") or []
    out: list[dict] = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                out.append(row)
    return out


def _search_once(client: httpx.Client, bearer: str, query: str) -> dict:
    cap = max(5, min(int(TAVILY_MAX_RESULTS), 20))
    body = {
        "query": query,
        "search_depth": TAVILY_SEARCH_DEPTH,
        "max_results": cap,
        "include_answer": True,
        "include_raw_content": False,
        "topic": "general",
        # Biases toward recent crawling for novelty vs stale mega-cap commentary.
        "time_range": "month",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer}",
    }
    response = client.post(TAVILY_SEARCH_URL, json=body, headers=headers)
    response.raise_for_status()
    return response.json()


def fetch_stock_research_tavily_context(
    *,
    budget: float,
    request_date_utc: datetime,
) -> str:
    """
    Formatted Tavily excerpts for the stock_research agent.
    Empty if key missing or every query fails.
    """
    raw_key = (TAVILY_API_KEY or "").strip()
    if not raw_key:
        logger.warning("TAVILY_API_KEY not set; stock research runs without Tavily enrichment.")
        return ""

    bearer = _normalize_bearer_token(raw_key)
    queries = build_stock_research_queries(budget=budget, request_date_utc=request_date_utc)
    merged_rows: list[dict] = []
    seen_urls: set[str] = set()
    summarized_answers: list[str] = []

    try:
        with httpx.Client(timeout=TAVILY_TIMEOUT_SECONDS) as client:
            for q in queries:
                try:
                    data = _search_once(client, bearer, q)
                except Exception as exc:
                    logger.warning("Tavily search failed (%s): %s", q[:100], exc)
                    continue
                ans = (data.get("answer") or "").strip()
                if ans:
                    summarized_answers.append(ans)
                for row in _flatten_results(data):
                    url = str(row.get("url") or "").strip()
                    title = str(row.get("title") or "").strip()
                    key = url or title
                    if not key:
                        continue
                    if url and url in seen_urls:
                        continue
                    if url:
                        seen_urls.add(url)
                    merged_rows.append(row)
    except Exception as exc:
        logger.exception("Tavily session failure: %s", exc)
        return ""

    if not merged_rows and not summarized_answers:
        logger.warning("Tavily returned no snippets after multi-query enrichment.")
        return ""

    parts: list[str] = []
    if summarized_answers:
        parts.append(
            "--- Tavily answer (synthesized; cross-check snippets) ---\n"
            + "\n\n".join(_truncate(a, 900) for a in summarized_answers)
        )

    parts.append("--- Tavily sources (cite [n] in each research paragraph) ---")
    snippet_cap = max(5, min(int(TAVILY_MAX_RESULTS), 20))
    max_snippets = min(24, snippet_cap * 3)
    for idx, row in enumerate(merged_rows[:max_snippets], start=1):
        title = str(row.get("title") or "").strip() or "(no title)"
        url = str(row.get("url") or "").strip()
        snippet = _truncate(str(row.get("content") or ""), 1200)
        parts.append(f"[{idx}] {title}\nURL: {url}\nSnippet: {snippet}")

    blob = "\n\n".join(parts).strip()
    blob_cap = 24_000
    if len(blob) > blob_cap:
        logger.info("Truncating Tavily blob from %d to %d chars", len(blob), blob_cap)
        blob = blob[:blob_cap] + "\n...[tavily_web_enrichment_truncated]"

    logger.info(
        "Tavily enrichment prepared %d snippets (~%d chars).",
        min(len(merged_rows), max_snippets),
        len(blob),
    )
    return blob