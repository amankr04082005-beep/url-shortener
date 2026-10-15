# URL Shortener API

A REST API that shortens URLs, redirects short codes to the original link, and tracks click statistics.
Built with **FastAPI**, **PostgreSQL**, and **SQLAlchemy**, containerised with **Docker**.

## Features
- `POST /shorten` - create a short link (random 6-char base62 code, or an optional custom alias)
- `GET /{code}` - redirect (HTTP 307) to the original URL and record the click
- `GET /stats/{code}` - total clicks, last clicked time, creation time
- URL validation (Pydantic), custom-code validation, reserved-word protection, `409` on duplicate codes
- 10 automated tests (pytest) running against an isolated in-memory database

## Tech stack
Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, psycopg2, pytest, Docker, Docker Compose

## Database design
| Table | Columns |
|-------|---------|
| `urls` | id, **code (unique index)**, original_url, click_count, created_at |
| `clicks` | id, **url_id (FK, indexed)**, clicked_at, user_agent |

- The unique index on `code` makes redirect lookups fast and is the source of truth for collisions.
- `click_count` is incremented with an atomic SQL `UPDATE ... SET click_count = click_count + 1`, so concurrent requests do not lose counts.

## Run with Docker (recommended)
```bash
docker compose up --build
# API:  http://localhost:8000      Docs: http://localhost:8000/docs
```

## Run locally without Docker
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload                        # uses SQLite if DATABASE_URL is not set
```
To use PostgreSQL, set `DATABASE_URL=postgresql://user:password@localhost:5432/dbname`.

## Example
```bash
curl -X POST localhost:8000/shorten -H "Content-Type: application/json" \
     -d '{"url": "https://fastapi.tiangolo.com", "custom_code": "fastapi"}'
# {"code":"fastapi","short_url":"http://localhost:8000/fastapi","original_url":"https://fastapi.tiangolo.com/"}

curl -i localhost:8000/fastapi          # 307 redirect
curl localhost:8000/stats/fastapi       # {"total_clicks": 1, ...}
```
A ready-made **Postman collection** is in `postman_collection.json` (import it and set `base_url`).

## Tests
```bash
pytest -q        # 10 passed
```

## Deploy on Render
1. Push this repo to GitHub.
2. Render -> **New PostgreSQL** -> copy the *Internal Database URL*.
3. Render -> **New Web Service** -> connect the repo -> Runtime: **Docker**.
4. Add environment variables: `DATABASE_URL` (the URL from step 2) and `BASE_URL` (your Render service URL).
5. Deploy. Tables are created automatically on startup.

## Project structure
```
app/
  main.py      # routes
  models.py    # SQLAlchemy models
  schemas.py   # request/response validation
  crud.py      # DB logic, code generation, click recording
  database.py  # engine/session, DATABASE_URL handling
tests/test_api.py
Dockerfile
docker-compose.yml
postman_collection.json
```
