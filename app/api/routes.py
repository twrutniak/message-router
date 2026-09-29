import logging
from typing import Annotated

import aiosmtplib
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError

from app.agent import RouterDeps, route_message
from app.api.errors import LLM_UNAVAILABLE, MAIL_UNAVAILABLE
from app.schemas import RouteRequest, RouteResponse
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.api_prefix)


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str


def get_agent(request: Request) -> Agent[RouterDeps, str]:
    return request.app.state.agent


@router.post(
    "/messages",
    response_model=RouteResponse,
    summary="Skieruj wiadomość do właściwego działu",
    responses={
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "Silnik LLM lub serwer pocztowy jest niedostępny.",
        }
    },
)
async def post_message(
    payload: RouteRequest, agent: Annotated[Agent[RouterDeps, str], Depends(get_agent)]
) -> RouteResponse:
    try:
        return await route_message(agent, payload.email, payload.message)
    except ModelAPIError as exc:
        logger.error("Błąd silnika LLM: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, LLM_UNAVAILABLE) from exc
    except (aiosmtplib.SMTPException, OSError) as exc:
        logger.error("Błąd wysyłki SMTP: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, MAIL_UNAVAILABLE) from exc


@router.get("/health", response_model=HealthResponse, summary="Stan usługi")
async def get_health() -> HealthResponse:
    return HealthResponse(status="ok")
