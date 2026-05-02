"""OpenAI completions constrained to JSON, parsed into Pydantic models."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ai_indian_stock_suggestion.backend.app.services.agents.call_openai import get_openai_client

TModel = TypeVar("TModel", bound=BaseModel)

_JSON_CONTRACT_SUFFIX = """

You MUST respond with a single JSON object only (no markdown code fences, no commentary).
"""


def _relax_json_extract(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Assistant did not return valid JSON: {text[:500]!r}")


def chat_completion_json_model(
    *,
    system_prompt: str,
    user_content: str,
    model: str,
    temperature: float,
    response_model: type[TModel],
) -> TModel:
    client = get_openai_client()
    full_system = system_prompt.strip() + _JSON_CONTRACT_SUFFIX
    completion = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content or ""
    try:
        payload = _relax_json_extract(raw)
        return response_model.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"Structured parse failed for {response_model.__name__}: {e}") from e
