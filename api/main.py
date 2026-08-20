"""FastAPI app entry point (specs/002-web-frontend/plan.md): the only HTTP
surface the Next.js frontend talks to (FR-022). Run with:

    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from models.db import init_db
from tools.logging_setup import get_logger

load_dotenv()

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("api_startup", extra={"fields": {}})
    yield


app = FastAPI(title="MeetMind API", version="1.0.0", lifespan=lifespan)


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}


from api.routers import assistant, auth, dashboard, integrations  # noqa: E402

app.include_router(auth.router)
app.include_router(integrations.router)
app.include_router(dashboard.router)
app.include_router(assistant.router)
