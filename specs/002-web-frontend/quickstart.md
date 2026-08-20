# Quickstart: Multi-Tenant Web Frontend & API

## Backend (FastAPI)

```bash
# from repo root, existing .venv
pip install -r requirements.txt   # now includes fastapi, uvicorn, bcrypt, cryptography, itsdangerous
```

Add to `.env` (in addition to feature 001's existing keys):

```
APP_ENCRYPTION_KEY=   # generate once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
APP_SESSION_COOKIE_SECURE=false   # true in production (HTTPS)
```

Run the API:

```bash
uvicorn api.main:app --reload --port 8000
```

`init_db()` runs automatically on startup (creates new tables, migrates any existing
single-tenant rows to a legacy user per research.md R7).

## Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000, proxies /api/* to http://localhost:8000
```

## Verifying each user story manually

1. **US1**: Visit `/`, read the marketing content, go to `/signup`, create an account →
   should land on `/dashboard` with an empty state.
2. **US2**: On `/dashboard/integrations`, submit a Trello key/token/board/list, a Discord
   bot token, a Gemini API key, and complete Otter's OAuth flow → all four show
   "Connected" with a masked hint, and persist across a page reload.
3. **US3**: Once feature-001's pipelines have produced data for that user (see feature
   001's own quickstart for how a meeting gets processed, now run against this user's
   connected credentials), `/dashboard` shows recent meetings; `/dashboard/meetings/[id]`
   shows the full summary; `/dashboard/tasks` shows outstanding action items;
   `/dashboard/reports` shows morning/evening reports.
4. **US4**: On `/dashboard`, click "Start assistant" → status flips to Running with a
   live "last activity" timestamp after the next scheduled tick; click "Stop" → status
   flips back to Stopped.

## Tests

```bash
pytest tests/unit tests/integration   # includes new api/ router tests + isolation tests
cd frontend && npm test               # component/unit tests (no e2e in this feature)
```
