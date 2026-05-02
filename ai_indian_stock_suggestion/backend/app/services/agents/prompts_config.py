from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ai_indian_stock_suggestion.backend.app.config import AGENT_PROMPTS_YAML_PATH

_raw_config_cache: dict[str, Any] | None = None
_cached_path: Path | None = None


def _default_yaml_path() -> Path:
    return Path(__file__).resolve().parent / "agents_prompts.yaml"


def prompts_yaml_path() -> Path:
    if AGENT_PROMPTS_YAML_PATH:
        return Path(AGENT_PROMPTS_YAML_PATH).expanduser()
    return _default_yaml_path()


def load_agents_config() -> dict[str, Any]:
    global _raw_config_cache, _cached_path
    path = prompts_yaml_path().resolve()
    if _raw_config_cache is not None and _cached_path == path:
        return _raw_config_cache
    if not path.is_file():
        raise FileNotFoundError(f"Agents prompts YAML not found: {path}")
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("agents_prompts.yaml must parse to a mapping at the root")
    _raw_config_cache = parsed
    _cached_path = path
    return parsed


@dataclass(frozen=True)
class AgentRuntimePrompt:
    key: str
    model: str
    temperature: float
    system_prompt: str


def resolve_agent_prompt(agent_key: str) -> AgentRuntimePrompt:
    raw = load_agents_config()
    defaults = raw.get("defaults") or {}
    default_model = str(defaults.get("model", "gpt-4o-mini"))
    default_temp = float(defaults.get("temperature", 0.3))

    agents = raw.get("agents") or {}
    if agent_key not in agents:
        raise KeyError(f"Unknown agent key {agent_key!r}; expected one of {sorted(agents)}")

    cfg = agents[agent_key] or {}
    model = cfg.get("model") or default_model
    temperature = cfg.get("temperature")
    if temperature is None:
        temperature = default_temp
    else:
        temperature = float(temperature)

    system_prompt = str(cfg.get("system_prompt", "")).strip()
    if not system_prompt:
        raise ValueError(f"Missing or empty system_prompt for agent {agent_key!r}")

    return AgentRuntimePrompt(
        key=agent_key,
        model=str(model),
        temperature=temperature,
        system_prompt=system_prompt,
    )
