import logging
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from app.domain_keywords import ALLOWED_ADDRESSES, FALLBACK_ADDRESS
from app.mailer import send_mail
from app.prompts import (
    FALLBACK_SUBJECT,
    RETRY_PROMPT,
    TOOL_ALREADY_SENT,
    TOOL_SENT,
    build_system_prompt,
)
from app.schemas import RouteResponse
from app.settings import settings

logger = logging.getLogger(__name__)

Address = Literal[ALLOWED_ADDRESSES]  # type: ignore[valid-type]


@dataclass
class RouterDeps:
    sender_email: str
    routed_to: str | None = None
    subject: str | None = None


def build_model() -> Model:
    http_client = httpx.AsyncClient(timeout=settings.ollama_timeout)
    provider = OpenAIProvider(
        base_url=settings.ollama_base_url,
        api_key=settings.ollama_api_key,
        http_client=http_client,
    )
    return OpenAIChatModel(settings.ollama_model, provider=provider)


def build_agent(model: Model | None = None) -> Agent[RouterDeps, str]:
    agent = Agent(
        model or build_model(),
        deps_type=RouterDeps,
        output_type=str,
        system_prompt=build_system_prompt(),
        model_settings=ModelSettings(temperature=settings.ollama_temperature),
    )

    @agent.tool
    async def send_email(ctx: RunContext[RouterDeps], to: Address, subject: str, body: str) -> str:
        """Wysyła wiadomość e-mail do wybranego działu firmy."""
        if ctx.deps.routed_to:
            return TOOL_ALREADY_SENT.format(to=ctx.deps.routed_to)
        subject = " ".join(subject.split())
        await send_mail(to=to, subject=subject, body=body, reply_to=ctx.deps.sender_email)
        ctx.deps.routed_to = to
        ctx.deps.subject = subject
        return TOOL_SENT.format(to=to)

    return agent


async def route_message(
    agent: Agent[RouterDeps, str], sender_email: str, message: str
) -> RouteResponse:
    """Uruchamia agenta; gdy nie wywoła toola – ponawia, a na końcu wysyła na adres awaryjny."""
    deps = RouterDeps(sender_email=sender_email)
    prompt = message

    for attempt in range(1 + settings.agent_retries):
        try:
            await agent.run(prompt, deps=deps)
        except UnexpectedModelBehavior as exc:
            logger.warning("Agent zwrócił błąd (próba %d): %s", attempt + 1, exc)
        if deps.routed_to:
            return RouteResponse(
                status="sent", routed_to=deps.routed_to, subject=deps.subject or ""
            )
        logger.warning("Model nie wywołał send_email (próba %d)", attempt + 1)
        prompt = RETRY_PROMPT.format(message=message)

    logger.warning("Wysyłka awaryjna do %s dla nadawcy %s", FALLBACK_ADDRESS, sender_email)
    subject = FALLBACK_SUBJECT
    await send_mail(to=FALLBACK_ADDRESS, subject=subject, body=message, reply_to=sender_email)
    return RouteResponse(status="fallback", routed_to=FALLBACK_ADDRESS, subject=subject)
