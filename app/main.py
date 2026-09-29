import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic_ai import Agent
from pydantic_ai.exceptions import AgentRunError

from app.agent import build_agent, build_llm_client, build_model
from app.api.routes import router
from app.prompts import WARMUP_PROMPT
from app.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    client = build_llm_client()
    model = build_model(client)
    app.state.agent = build_agent(model)
    try:
        # Pierwsze zapytanie ładuje wagi modelu do pamięci (na CPU trwa długo) – robimy to
        # przy starcie, żeby pierwszy request użytkownika nie czekał.
        await Agent(model).run(WARMUP_PROMPT)
    except AgentRunError as exc:
        logger.warning("Warm-up modelu nie powiódł się: %s", exc)
    try:
        yield
    finally:
        await client.close()


app = FastAPI(
    title="Message Router",
    description="Router wiadomości: agent AI kieruje zgłoszenia do właściwego działu.",
    docs_url=f"{settings.api_prefix}/docs",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)
app.include_router(router)
