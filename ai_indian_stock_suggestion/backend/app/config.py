import os
from dotenv import load_dotenv

load_dotenv()


MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "")

# OpenAI (recommendation agents)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Optional override: absolute path to a copy of agents_prompts.yaml
AGENT_PROMPTS_YAML_PATH = os.getenv("AGENT_PROMPTS_YAML_PATH", "")
# Optional override: stock_research X-factor tuning (defaults next to agents_prompts.yaml)
XFACTOR_YAML_PATH = os.getenv("XFACTOR_YAML_PATH", "")

# Tavily (live web enrichment for stock_research agent)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


def _int_clamped(raw: str, *, fallback: int, low: int, high: int) -> int:
    try:
        v = int(raw)
    except ValueError:
        return fallback
    return max(low, min(v, high))


def _float_or_default(raw: str, default: float) -> float:
    try:
        return float(raw)
    except ValueError:
        return default


TAVILY_MAX_RESULTS = _int_clamped(
    os.getenv("TAVILY_MAX_RESULTS", "10"),
    fallback=10,
    low=5,
    high=20,
)
_depth = os.getenv("TAVILY_SEARCH_DEPTH", "advanced").strip().lower()
TAVILY_SEARCH_DEPTH = _depth if _depth in {"basic", "advanced"} else "advanced"
TAVILY_TIMEOUT_SECONDS = max(10.0, _float_or_default(os.getenv("TAVILY_TIMEOUT_SECONDS", "45"), 45.0))

# Centralize collection names here.
MONGODB_COLLECTIONS = {
    "stocks": os.getenv("MONGODB_COLLECTION_STOCKS", "stocks"),
    "watchlist": os.getenv("MONGODB_COLLECTION_WATCHLIST", "watchlist"),
    "users": os.getenv("MONGODB_COLLECTION_USERS", "users"),
    "signals": os.getenv("MONGODB_COLLECTION_SIGNALS", "signals"),
    "stock_recommendations": os.getenv(
        "MONGODB_COLLECTION_STOCK_RECOMMENDATIONS",
        "stock_recommendations",
    ),
}

# Recommendation engine: persist OpenAI-derived rows unless false
SAVE_STOCK_RECOMMENDATIONS_TO_DB = os.getenv("SAVE_STOCK_RECOMMENDATIONS_TO_DB", "true").lower() not in {"0", "false", "no"}

# Logging
APP_LOG_DIR = os.getenv("APP_LOG_DIR", "logs")
APP_LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "INFO")

# Placeholder strategy selectors for upcoming business logic.
ACTION_ANALYSIS = os.getenv("ACTION_ANALYSIS", "latest_action")
RECOMMENDATION_ANALYSIS = os.getenv("RECOMMENDATION_ANALYSIS", "baseline_recommendation")
