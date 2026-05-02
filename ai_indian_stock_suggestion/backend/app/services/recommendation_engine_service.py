"""Three-agent recommendation pipeline: research → behaviour → sizing recommendations."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from ai_indian_stock_suggestion.backend.app.config import (
    ACTION_ANALYSIS,
    OPENAI_API_KEY,
    SAVE_STOCK_RECOMMENDATIONS_TO_DB,
)
from ai_indian_stock_suggestion.backend.app.db.mongodb import (
    insert_stock_recommendation_doc,
    list_transactions_for_customer,
)
from ai_indian_stock_suggestion.backend.app.models.recommendation_state import (
    BehaviourAnalysisAgentLLM,
    BehaviourAnalysisOutput,
    RecommendationAgentLLM,
    RecommendationOutputState,
    RecommendationPipelineResult,
    ResearchOutputState,
    StockResearchAgentLLM,
)
from ai_indian_stock_suggestion.backend.app.services.agents.json_completion import (
    chat_completion_json_model,
)
from ai_indian_stock_suggestion.backend.app.services.agents.prompts_config import (
    resolve_agent_prompt,
)
from ai_indian_stock_suggestion.backend.app.services.agents.recommendation_agents import (
    AGENT_KEY_BEHAVIOUR_ANALYSIS,
    AGENT_KEY_RECOMMENDATION,
    AGENT_KEY_STOCK_RESEARCH,
)
from ai_indian_stock_suggestion.backend.app.services.agents.tavily_search import (
    fetch_stock_research_tavily_context,
)

logger = logging.getLogger(__name__)


def _normalize_ticker(raw: str) -> str:
    return re.sub(r"\s+", "", (raw or "").strip()).upper()


def _request_date_as_utc(request_date: datetime) -> datetime:
    if request_date.tzinfo is None:
        return request_date.replace(tzinfo=timezone.utc)
    return request_date.astimezone(timezone.utc)


def analyze_previous_action_taken(user_document: dict, analysis_mode: str) -> dict:
    return {
        "analysis_mode": analysis_mode,
        "last_action_taken": user_document.get("action_taken") or "",
    }


def _run_stock_research(
    *,
    customer_id: str,
    budget: float,
    request_date_utc: datetime,
    spec_system: str,
    model: str,
    temperature: float,
) -> list[ResearchOutputState]:
    tavily_context = fetch_stock_research_tavily_context(
        budget=budget,
        request_date_utc=request_date_utc,
    )
    parsed = chat_completion_json_model(
        system_prompt=spec_system,
        user_content=json.dumps(
            {
                "customer_id": customer_id,
                "budget": budget,
                "date": request_date_utc.isoformat(),
                "web_enrichment_from_tavily": tavily_context
                or "(empty — Tavily disabled, failed, or returned no snippets; still respond with JSON)",
            },
            default=str,
        ),
        model=model,
        temperature=temperature,
        response_model=StockResearchAgentLLM,
    )

    normalized_suggestions: list[tuple[str, str]] = []
    for item in parsed.suggestions:
        code = _normalize_ticker(item.stock_code)
        if not code:
            raise ValueError("Stock research produced an empty ticker")
        normalized_suggestions.append((code, item.research.strip()))

    if len({c for c, _ in normalized_suggestions}) != 3:
        raise ValueError("Stock research suggestions must contain 3 distinct tickers")

    states = [
        ResearchOutputState(
            date=request_date_utc,
            customer_id=customer_id,
            budget=budget,
            stock_code=code,
            research=text,
        )
        for code, text in normalized_suggestions
    ]
    return states


def _run_behaviour(
    *,
    customer_id: str,
    transactions: list[dict],
    prior_signals: dict,
    spec_system: str,
    model: str,
    temperature: float,
    request_date_utc: datetime,
) -> BehaviourAnalysisOutput:
    payload = {
        "customer_id": customer_id,
        "transaction_records": transactions,
        "prior_action_signals": prior_signals,
    }
    parsed = chat_completion_json_model(
        system_prompt=spec_system,
        user_content=json.dumps(payload, default=str),
        model=model,
        temperature=temperature,
        response_model=BehaviourAnalysisAgentLLM,
    )
    return BehaviourAnalysisOutput(
        date=request_date_utc,
        customer_id=customer_id,
        behaviour_analysis=parsed.behaviour_analysis.strip(),
    )


def _run_recommendation_combo(
    *,
    customer_id: str,
    budget: float,
    request_date_utc: datetime,
    behaviour: BehaviourAnalysisOutput,
    research_states: list[ResearchOutputState],
    spec_system: str,
    model: str,
    temperature: float,
) -> tuple[list[RecommendationOutputState], RecommendationAgentLLM]:
    ordered_codes = [r.stock_code for r in research_states]
    research_payload = [
        {"stock_code": r.stock_code, "research_excerpt": r.research[:800]}
        for r in research_states
    ]
    combo = {
        "customer_id": customer_id,
        "budget_inr": budget,
        "request_date": request_date_utc.isoformat(),
        "behaviour_analysis": behaviour.behaviour_analysis,
        "stock_research_stocks_ordered": research_payload,
        "enforce_order_exactly_three_codes": ordered_codes,
    }
    parsed = chat_completion_json_model(
        system_prompt=spec_system,
        user_content=json.dumps(combo, default=str),
        model=model,
        temperature=temperature,
        response_model=RecommendationAgentLLM,
    )

    recos_normalized = [_normalize_ticker(x.stock_code) for x in parsed.recommendations]
    if recos_normalized != ordered_codes:
        raise ValueError(
            f"Recommendation tickers mismatch: expected {ordered_codes}, got {recos_normalized}"
        )

    out: list[RecommendationOutputState] = []
    for row, canon in zip(parsed.recommendations, ordered_codes, strict=True):
        out.append(
            RecommendationOutputState(
                date=request_date_utc,
                customer_id=customer_id,
                stock_code=canon,
                recommendation=row.recommendation.strip(),
                quantity=int(row.quantity),
                time_period=row.time_period.strip(),
            )
        )

    return out, parsed


def execute_recommendation_pipeline(
    *,
    customer_id: str,
    request_date: datetime,
    budget: float,
    prior_focus_row_for_behaviour: dict | None,
) -> RecommendationPipelineResult:
    if not OPENAI_API_KEY.strip():
        logger.warning("OPENAI_API_KEY missing; skipping recommendation pipeline.")
        return RecommendationPipelineResult(pipeline_status="skipped_no_api_key")

    try:
        request_date_utc = _request_date_as_utc(request_date)
        logger.info(
            "Recommendation pipeline started for customer_id=%s date=%s budget=%s",
            customer_id,
            request_date_utc.isoformat(),
            budget,
        )

        sr_spec = resolve_agent_prompt(AGENT_KEY_STOCK_RESEARCH)
        ba_spec = resolve_agent_prompt(AGENT_KEY_BEHAVIOUR_ANALYSIS)
        rc_spec = resolve_agent_prompt(AGENT_KEY_RECOMMENDATION)

        research_states = _run_stock_research(
            customer_id=customer_id,
            budget=budget,
            request_date_utc=request_date_utc,
            spec_system=sr_spec.system_prompt,
            model=sr_spec.model,
            temperature=sr_spec.temperature,
        )

        transactions = list_transactions_for_customer(customer_id)
        seed_row = dict(prior_focus_row_for_behaviour or {})
        prior_signals = analyze_previous_action_taken(seed_row, ACTION_ANALYSIS)

        behaviour = _run_behaviour(
            customer_id=customer_id,
            transactions=transactions,
            prior_signals=prior_signals,
            spec_system=ba_spec.system_prompt,
            model=ba_spec.model,
            temperature=ba_spec.temperature,
            request_date_utc=request_date_utc,
        )

        reco_states, _ = _run_recommendation_combo(
            customer_id=customer_id,
            budget=budget,
            request_date_utc=request_date_utc,
            behaviour=behaviour,
            research_states=research_states,
            spec_system=rc_spec.system_prompt,
            model=rc_spec.model,
            temperature=rc_spec.temperature,
        )

        bucket = {r.stock_code: r.quantity for r in reco_states}
        if SAVE_STOCK_RECOMMENDATIONS_TO_DB:
            insert_stock_recommendation_doc(
                customer_id,
                request_date_utc,
                budget,
                bucket,
            )
            logger.info(
                "Persisted stock recommendations for customer_id=%s symbols=%s",
                customer_id,
                sorted(bucket.keys()),
            )

        logger.info("Recommendation pipeline completed for customer_id=%s", customer_id)
        return RecommendationPipelineResult(
            pipeline_status="ok",
            recommendation=bucket,
            stock_recommendations=reco_states,
            research_outputs=research_states,
            behaviour_analysis=behaviour.behaviour_analysis,
        )
    except Exception as e:
        logger.exception(
            "Recommendation pipeline failed for customer_id=%s: %s",
            customer_id,
            e,
        )
        return RecommendationPipelineResult(
            pipeline_status="error",
            error=str(e),
        )
