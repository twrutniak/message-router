from email.message import EmailMessage

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False


class SentMails(list):
    """Maile przechwycone zamiast wysyłki SMTP: krotki (EmailMessage, kwargs połączenia)."""

    @property
    def messages(self) -> list[EmailMessage]:
        return [message for message, _ in self]


@pytest.fixture(autouse=True)
def sent_mails(monkeypatch: pytest.MonkeyPatch) -> SentMails:
    mails = SentMails()

    async def fake_send(message: EmailMessage, **kwargs):
        mails.append((message, kwargs))

    monkeypatch.setattr("app.mailer.aiosmtplib.send", fake_send)
    return mails


def send_email_call(to: str, subject: str = "Temat", **extra) -> ToolCallPart:
    return ToolCallPart("send_email", {"to": to, "subject": subject, **extra})


def scripted_model(*runs: list[ToolCallPart] | str) -> FunctionModel:
    """Model odgrywający scenariusz: n-ty element to zachowanie modelu w n-tym `agent.run()`.

    Lista wywołań toola = model woła narzędzie, a po jego wyniku odpowiada tekstem;
    string = model odpowiada samym tekstem (bez wywołania toola).
    """
    state = {"run": -1}

    def respond(messages, info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            state["run"] += 1
        action = runs[min(state["run"], len(runs) - 1)]
        tool_already_returned = len(messages) > 1
        if isinstance(action, str) or tool_already_returned:
            return ModelResponse(parts=[TextPart(action if isinstance(action, str) else "gotowe")])
        return ModelResponse(parts=action)

    return FunctionModel(respond)
