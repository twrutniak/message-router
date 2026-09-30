from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from app.agent import build_agent
from app.api.errors import LLM_UNAVAILABLE, MAIL_UNAVAILABLE
from app.api.routes import get_agent
from app.domain_keywords import ALLOWED_ADDRESSES, FALLBACK_ADDRESS
from app.main import app
from app.settings import settings
from tests.conftest import scripted_model, send_email_call

PREFIX = settings.api_prefix
DEPARTMENT = ALLOWED_ADDRESSES[0]
VALID = {"email": "jan.nowak@example.com", "message": "Chciałbym zgłosić urlop na jutro"}


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


def use_model(model) -> None:
    agent = build_agent(model)
    app.dependency_overrides[get_agent] = lambda: agent


async def test_swagger_docs_available(client):
    response = await client.get(f"{PREFIX}/docs")

    assert response.status_code == 200
    assert "swagger" in response.text.lower()


async def test_openapi_schema_lists_endpoints(client):
    response = await client.get(f"{PREFIX}/openapi.json")

    paths = response.json()["paths"]
    assert "post" in paths[f"{PREFIX}/messages"]
    assert "get" in paths[f"{PREFIX}/health"]


async def test_health(client):
    response = await client.get(f"{PREFIX}/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_message_is_routed(client, sent_mails):
    use_model(scripted_model([send_email_call(DEPARTMENT, "Urlop", "Chcę urlop")]))

    response = await client.post(f"{PREFIX}/messages", json=VALID)

    assert response.status_code == 200
    assert response.json() == {
        "status": "sent",
        "routed_to": DEPARTMENT,
        "subject": "Urlop",
    }
    (message,) = sent_mails.messages
    assert message["To"] == DEPARTMENT
    assert message["Reply-To"] == VALID["email"]


async def test_fallback_is_reported(client, sent_mails):
    use_model(scripted_model("nie wiem"))

    response = await client.post(f"{PREFIX}/messages", json=VALID)

    assert response.status_code == 200
    assert response.json()["status"] == "fallback"
    assert response.json()["routed_to"] == FALLBACK_ADDRESS
    assert sent_mails.messages[0]["Reply-To"] == VALID["email"]


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "nie-email", "message": "Cześć"},
        {"email": VALID["email"], "message": ""},
        {"email": VALID["email"], "message": "   "},
        {"email": VALID["email"]},
        {"message": "Cześć"},
        {},
    ],
)
async def test_invalid_payload_returns_422(client, sent_mails, payload):
    use_model(scripted_model([send_email_call(DEPARTMENT)]))

    response = await client.post(f"{PREFIX}/messages", json=payload)

    assert response.status_code == 422
    assert len(sent_mails) == 0


async def test_llm_unavailable_returns_502(client, sent_mails):
    def broken(messages, info: AgentInfo) -> ModelResponse:
        raise ModelAPIError("qwen", "Connection error.")

    use_model(FunctionModel(broken))

    response = await client.post(f"{PREFIX}/messages", json=VALID)

    assert response.status_code == 502
    assert response.json() == {"detail": LLM_UNAVAILABLE}
    assert len(sent_mails) == 0


async def test_smtp_unavailable_returns_502(client, monkeypatch):
    async def failing_send(*args, **kwargs):
        raise ConnectionRefusedError("smtp down")

    monkeypatch.setattr("app.mailer.aiosmtplib.send", failing_send)
    use_model(scripted_model([send_email_call(DEPARTMENT)]))

    response = await client.post(f"{PREFIX}/messages", json=VALID)

    assert response.status_code == 502
    assert response.json() == {"detail": MAIL_UNAVAILABLE}


async def test_lifespan_builds_agent_and_closes_client(monkeypatch):
    class FakeClient:
        closed = False

        async def close(self):
            self.closed = True

    fake_client = FakeClient()
    warmup_requests = []

    def warmup_model(messages, info: AgentInfo) -> ModelResponse:
        warmup_requests.append(messages)
        return ModelResponse(parts=[TextPart("gotowe")])

    monkeypatch.setattr("app.main.build_llm_client", lambda: fake_client)
    monkeypatch.setattr("app.main.build_model", lambda client: FunctionModel(warmup_model))

    async with app.router.lifespan_context(app):
        assert app.state.agent is not None
        assert len(warmup_requests) == 1
        assert not fake_client.closed

    assert fake_client.closed


async def test_lifespan_survives_failed_warmup(monkeypatch):
    class FakeClient:
        async def close(self):
            pass

    def broken(messages, info: AgentInfo) -> ModelResponse:
        raise ModelAPIError("qwen", "Connection error.")

    monkeypatch.setattr("app.main.build_llm_client", lambda: FakeClient())
    monkeypatch.setattr("app.main.build_model", lambda client: FunctionModel(broken))

    async with app.router.lifespan_context(app):
        assert app.state.agent is not None


async def test_real_agent_wiring_with_test_model(client, sent_mails):
    use_model(TestModel())

    response = await client.post(f"{PREFIX}/messages", json=VALID)

    assert response.status_code == 200
    assert sent_mails.messages[0]["Reply-To"] == VALID["email"]
