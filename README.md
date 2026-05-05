# AI Indian Stock Suggestion

FastAPI backend that records user requests (MongoDB), runs a **three-agent** recommendation pipeline (**stock research**, **behaviour analysis**, **recommendation**) via OpenAI, enriches research with **Tavily web search** and **approximate NSE last prices (yfinance)**, and persists recommendations optionally to a dedicated collection.

Each request gets a **`transaction_id`** (12-character alphanumeric) stored on both the **users** ledger row and the **`stock_recommendations`** document so you can join them for dashboards or follow-up APIs.

## Requirements

- Python **3.10+**
- **MongoDB** (Atlas or local)
- **OpenAI API** key  
- **Tavily API** key (for live web snippets in stock research)
- **yfinance** (via `requirements.txt`) for indicative NSE quotes used in research and recommendations

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
| `AGENT_PROMPTS_YAML_PATH` | *(packaged YAML)* | Override path to `agents_prompts.yaml` |
| `XFACTOR_YAML_PATH` | *(packaged `ai_indian_stock_suggestion/backend/app/services/agents/Xfactor.yaml`)* | Override path to stock-research X-factor / personality rules |
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

Success response includes **`transaction_id`** for this request (use it with `PUT /users/update-action`). Other fields (conceptually): `pipeline_status`, `recommendation` (symbol → quantity), `stock_recommendations`, `research_outputs`, `behaviour_analysis`, `error` — see `/docs` after startup.

- **`research_outputs`**: each row includes narrative `research` plus **`current_price_inr`** when yfinance returns a quote for the NSE symbol (indicative / delayed).
- **`stock_recommendations`**: each row can include **`current_price_inr`** echoed from research for sizing context.

Without `OPENAI_API_KEY`: `pipeline_status` is `skipped_no_api_key` and recommendations are empty.

### `GET /users/customer-last-requests`

Query: `email_id` (required), `limit` (optional, default 5, max 50). Returns recent interaction rows (newest first). Every row includes **`transaction_id`** (`""` if missing on older documents).

### `PUT /users/update-action`

Updates `action_taken` for an existing suggestion row matched by `email_id`, `transaction_id`, and `date`.

**Body (JSON)**

```json
{
  "email_id": "abc@gmail.com",
  "transaction_id": "A1B2C3D4E5F6",
  "date": "2-May-2026",
  "action_taken": "accepted"
}
```

`action_taken` supports only `accepted` or `rejected`.

`transaction_id` is returned from `POST /users/create` (and on ledger rows); it is **12 characters**, **uppercase A–Z and digits**.

Errors: `400` if `action_taken` is invalid; `404` if no row matches `email_id` + `transaction_id` + `date`.

**Response**

```json
{
  "msg": "action updated"
}
```

## Behaviour and data model (short)

- **Users collection**: Multiple documents per email / `customer_id` (interaction history). Each row has `transaction_id`, `date`, `budget` (**INR**), `action_taken` (empty until updated via `PUT /users/update-action`).
- **`stock_recommendations`**: One document per successful pipeline when saving is enabled: `transaction_id`, `customer_id`, `date`, `budget`, `recommendation` (map ticker → quantity). Linked to the users row by **`transaction_id`**.
- **Agents**: Main prompts live in `ai_indian_stock_suggestion/backend/app/services/agents/agents_prompts.yaml` (`AGENT_PROMPTS_YAML_PATH` to override). **Stock-research “X-factor” rules** are loaded from **`Xfactor.yaml`** next to it (`XFACTOR_YAML_PATH` to override) so you can tune personality without editing the main prompts file.
- **Pipeline**: **Behaviour analysis** runs only for **existing** customers (email already had prior ledger rows) and only using transactions where **`action_taken` is set** (non-empty). Budgets and prices in agent inputs are **INR**, not USD. The recommendation step may reorder the three research tickers; it receives **prior suggestion cycles** (from DB) so a **previously rejected** ticker can be justified more strongly if suggested again.

## Disclaimer

Price and quantity outputs are **illustrative** (delayed quotes, rounding, no fees). Not investment advice.

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
      Xfactor.yaml
      prompts_config.py
      nse_quote.py
      json_completion.py
      tavily_search.py
      ...
utils/logging_config.py
main.py                   # Repo root → uvicorn entry
```
