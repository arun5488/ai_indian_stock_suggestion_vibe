# AI Indian Stock Suggestion

FastAPI backend that records user requests (MongoDB), runs a **three-agent** recommendation pipeline (**stock research**, **behaviour analysis**, **recommendation**) via OpenAI, enriches research with **Tavily web search**, and persists recommendations optionally to a dedicated collection.

## Requirements

- Python **3.10+**
- **MongoDB** (Atlas or local)
- **OpenAI API** key  
- **Tavily API** key (for live web snippets in stock research)

## Setup

```bash
cd path/to/ai_indian_stock_suggestion_vibe
pip install -r requirements.txt
# or: uv sync
```

Create a `.env` file in the project root (same folder as this `README`). Example variables:

| Variable | Required | Purpose |
|---------|----------|---------|
| `MONGODB_URI` | Yes | MongoDB connection string |
| `MONGODB_DB_NAME` | Yes | Database name |
| `OPENAI_API_KEY` | Yes for full pipeline | OpenAI completions for agents |
| `TAVILY_API_KEY` | Recommended | Tavily Bearer token (`tvly-…`; prefix added if omitted) |

Optional:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENT_PROMPTS_YAML_PATH` | *(packaged YAML)* | Override path to prompts file |
| `MONGODB_COLLECTION_USERS` | `users` | Users / interaction ledger collection |
| `MONGODB_COLLECTION_STOCK_RECOMMENDATIONS` | `stock_recommendations` | Saved recommendation rows |
| `SAVE_STOCK_RECOMMENDATIONS_TO_DB` | `true` | Set `false` to skip inserting recommendations |
| `TAVILY_MAX_RESULTS` | `10` | Snippets per search (clamped 5–20) |
| `TAVILY_SEARCH_DEPTH` | `advanced` | `basic` or `advanced` |
| `TAVILY_TIMEOUT_SECONDS` | `45` | Tavily HTTP timeout |
| `APP_LOG_DIR` | `logs` | Rotating log files directory |
| `APP_LOG_LEVEL` | `INFO` | Root log level |

## Run the API

From the repo root:

```bash
python main.py
```

Or explicitly:

```bash
python -m uvicorn ai_indian_stock_suggestion.backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API overview

### `GET /health`

Returns `{ "status": "ok" }`.

### `POST /users/create`

Creates **one ledger row per request** per email (reuse of `customer_id` for the same email). Runs the recommendation pipeline and returns pipeline JSON (API shape omits nested `customer_id` from list items).

**Body (JSON)**

| Field | Type | Notes |
|-------|------|------|
| `email_id` | email | Unique contact key |
| `date` | string | Contract-style date **`DD-MMM-YYYY`** (e.g. `02-May-2026`) |
| `budget` | string (numeric) | Parsed as INR float |

Success response shape (conceptually): `pipeline_status`, `recommendation` (symbol → quantity), `stock_recommendations`, `research_outputs`, `behaviour_analysis`, `error` — see `/docs` after startup.

Without `OPENAI_API_KEY`: `pipeline_status` is `skipped_no_api_key` and recommendations are empty.

### `GET /users/customer-last-requests`

Query: `email_id` (required), `limit` (optional, default 5, max 50). Returns recent interaction rows (newest first).

## Behaviour and data model (short)

- **Users collection**: Multiple documents per email / `customer_id` (interaction history).
- **`stock_recommendations`**: One inserted document per successful pipeline when saving is enabled: `customer_id`, `date`, `budget`, `recommendation` (map ticker → quantity).
- Agents and models are driven by `ai_indian_stock_suggestion/backend/app/services/agents/agents_prompts.yaml` unless overridden by `AGENT_PROMPTS_YAML_PATH`.

## Logging

On startup the app configures **rotating file logs**:

- `logs/app.log` — general log
- `logs/error.log` — errors / exceptions only

Tune with `APP_LOG_DIR` and `APP_LOG_LEVEL`.

## Project layout (backend)

```text
ai_indian_stock_suggestion/backend/app/
  main.py                 # FastAPI app + startup (DB, logs)
  config.py               # Env-driven settings
  db/mongodb.py           # Mongo access, indexes, inserts
  models/recommendation_state.py
  routes/user_routes.py
  services/
    user_creation_service.py
    recommendation_engine_service.py
    agents/
      agents_prompts.yaml
      json_completion.py
      tavily_search.py
      ...
utils/logging_config.py
main.py                   # Repo root → uvicorn entry
```
