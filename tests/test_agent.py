import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from app.agent import build_agent, route_message
from app.domain_keywords import ALLOWED_ADDRESSES, FALLBACK_ADDRESS
from app.prompts import FALLBACK_SUBJECT
from app.settings import settings
from tests.conftest import scripted_model, send_email_call

SENDER = "jan.nowak@example.com"


async def test_tool_call_sends_mail_with_reply_to(sent_mails):
    agent = build_agent(
        scripted_model([send_email_call("kadry@example.com", "Urlop", "Chcę urlop")])
    )

    response = await route_message(agent, SENDER, "Chcę urlop")

    assert response.status == "sent"
    assert response.routed_to == "kadry@example.com"
    assert response.subject == "Urlop"
    (message,) = sent_mails.messages
    assert message["To"] == "kadry@example.com"
    assert message["Reply-To"] == SENDER
    assert message["Subject"] == "Urlop"


@pytest.mark.parametrize("address", ALLOWED_ADDRESSES)
async def test_every_department_reachable(sent_mails, address):
    agent = build_agent(scripted_model([send_email_call(address)]))

    response = await route_message(agent, SENDER, "wiadomość")

    assert response.status == "sent"
    assert sent_mails.messages[0]["To"] == address


async def test_tool_schema_restricts_address_and_hides_reply_to():
    captured = {}

    def inspect_tools(messages, info: AgentInfo) -> ModelResponse:
        captured["tools"] = {tool.name: tool.parameters_json_schema for tool in info.function_tools}
        return ModelResponse(parts=[TextPart("nic")])

    agent = build_agent(FunctionModel(inspect_tools))
    await route_message(agent, SENDER, "x")

    schema = captured["tools"]["send_email"]
    assert set(schema["properties"]) == {"to", "subject", "body"}
    assert "reply_to" not in schema["properties"]
    to_schema = schema["properties"]["to"]
    assert set(to_schema.get("enum", [])) == set(ALLOWED_ADDRESSES)


async def test_reply_to_comes_from_deps_not_model(sent_mails):
    call = send_email_call("it@example.com")
    call.args["reply_to"] = "attacker@evil.com"
    agent = build_agent(scripted_model([call], [send_email_call("it@example.com")]))

    await route_message(agent, SENDER, "x")

    assert all(message["Reply-To"] == SENDER for message in sent_mails.messages)


async def test_address_outside_list_falls_back(sent_mails):
    agent = build_agent(scripted_model([send_email_call("ceo@evil.com")]))

    response = await route_message(agent, SENDER, "hej")

    assert response.status == "fallback"
    assert response.routed_to == FALLBACK_ADDRESS
    (message,) = sent_mails.messages
    assert message["To"] == FALLBACK_ADDRESS
    assert message["Reply-To"] == SENDER


async def test_no_tool_call_retries_then_falls_back(sent_mails):
    runs = []

    def text_only(messages, info: AgentInfo) -> ModelResponse:
        runs.append(messages)
        return ModelResponse(parts=[TextPart("nie wiem")])

    agent = build_agent(FunctionModel(text_only))

    response = await route_message(agent, SENDER, "asdf")

    assert len(runs) == 1 + settings.agent_retries
    assert response.status == "fallback"
    assert response.routed_to == FALLBACK_ADDRESS
    assert response.subject == FALLBACK_SUBJECT
    (message,) = sent_mails.messages
    assert message["To"] == FALLBACK_ADDRESS
    assert message["Reply-To"] == SENDER
    assert message.get_content().strip() == "asdf"


async def test_retry_succeeds_without_fallback(sent_mails):
    agent = build_agent(scripted_model("nie wiem", [send_email_call("it@example.com")]))

    response = await route_message(agent, SENDER, "Nie działa komputer")

    assert response.status == "sent"
    assert response.routed_to == "it@example.com"
    (message,) = sent_mails.messages
    assert message["To"] == "it@example.com"


async def test_duplicate_tool_calls_send_single_mail(sent_mails):
    agent = build_agent(
        scripted_model([send_email_call("it@example.com"), send_email_call("kadry@example.com")])
    )

    response = await route_message(agent, SENDER, "x")

    assert response.routed_to == "it@example.com"
    assert len(sent_mails) == 1


async def test_smtp_failure_propagates(monkeypatch):
    async def failing_send(*args, **kwargs):
        raise ConnectionRefusedError("smtp down")

    monkeypatch.setattr("app.mailer.aiosmtplib.send", failing_send)
    agent = build_agent(scripted_model([send_email_call("it@example.com")]))

    with pytest.raises(ConnectionRefusedError):
        await route_message(agent, SENDER, "x")


async def test_test_model_calls_tool(sent_mails):
    agent = build_agent(TestModel())

    response = await route_message(agent, SENDER, "x")

    assert response.status == "sent"
    assert response.routed_to in ALLOWED_ADDRESSES
    assert sent_mails.messages[0]["Reply-To"] == SENDER
