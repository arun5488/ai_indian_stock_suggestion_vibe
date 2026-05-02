# ai_indian_stock_suggestion_vibe

## Step 1: User registration API (FastAPI + MongoDB)

### Project structure

```text
app/
  api/
    routes/
      users.py
  core/
    config.py
  db/
    mongo.py
  schemas/
    user.py
  main.py
```

`app/main.py` is the only FastAPI entrypoint.

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Configure environment variables

Copy `.env.example` to `.env` and update values if needed:

```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=ai_stock_suggestion
```

### 3) Run API server

```bash
python -m uvicorn app.main:app --reload
```

### 4) Test registration endpoint

Endpoint: `POST /register`

Request:

```json
{
  "email_id":"abc@gmail.com",
  "stock_account":"icicidirect",
  "stock_plan":"20 per txn"
}
```

Response:

```json
{
  "customerid": "CUST-XXXXXXXXXXXX"
}
```

Behavior:
- User details are stored in MongoDB collection: `users`
- If `email_id` already exists, API returns existing `customerid`
- If `email_id` is new, API generates and stores a new `customerid`
