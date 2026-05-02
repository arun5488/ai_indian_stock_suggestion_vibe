from __future__ import annotations

import json
from typing import Any, Mapping

from ai_indian_stock_suggestion.backend.app.services.agents.call_openai import chat_completion
from ai_indian_stock_suggestion.backend.app.services.agents.prompts_config import resolve_agent_prompt

AGENT_KEY_STOCK_RESEARCH = "stock_research"
AGENT_KEY_BEHAVIOUR_ANALYSIS = "behaviour_analysis"
AGENT_KEY_RECOMMENDATION = "recommendation"


def _user_message(context: Mapping[str, Any] | str | None) -> str:
    if context is None:
        return json.dumps({}, default=str)
    if isinstance(context, str):
        return context
    return json.dumps(dict(context), default=str)


def run_stock_research_agent(context: Mapping[str, Any] | str | None = None) -> str:
    spec = resolve_agent_prompt(AGENT_KEY_STOCK_RESEARCH)
    return chat_completion(
        system_prompt=spec.system_prompt,
        user_content=_user_message(context),
        model=spec.model,
        temperature=spec.temperature,
    )


def run_behaviour_analysis_agent(context: Mapping[str, Any] | str | None = None) -> str:
    spec = resolve_agent_prompt(AGENT_KEY_BEHAVIOUR_ANALYSIS)
    return chat_completion(
        system_prompt=spec.system_prompt,
        user_content=_user_message(context),
        model=spec.model,
        temperature=spec.temperature,
    )


def run_recommendation_agent(context: Mapping[str, Any] | str | None = None) -> str:
    spec = resolve_agent_prompt(AGENT_KEY_RECOMMENDATION)
    return chat_completion(
        system_prompt=spec.system_prompt,
        user_content=_user_message(context),
        model=spec.model,
        temperature=spec.temperature,
    )
