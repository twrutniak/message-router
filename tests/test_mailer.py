import pytest

from app.mailer import send_mail
from app.settings import settings


async def test_headers_and_body(sent_mails):
    await send_mail(
        to="kadry@example.com",
        subject="Urlop",
        body="Chcę urlop",
        reply_to="jan.nowak@example.com",
    )

    (message,) = sent_mails.messages
    assert message["From"] == settings.mail_from
    assert message["To"] == "kadry@example.com"
    assert message["Reply-To"] == "jan.nowak@example.com"
    assert message["Subject"] == "Urlop"
    assert message.get_content().strip() == "Chcę urlop"


async def test_smtp_connection_uses_settings(sent_mails):
    await send_mail(to="it@example.com", subject="s", body="b", reply_to="a@example.com")

    _, kwargs = sent_mails[0]
    assert kwargs == {
        "hostname": settings.smtp_host,
        "port": settings.smtp_port,
        "timeout": settings.smtp_timeout,
    }


async def test_subject_newlines_collapsed(sent_mails):
    await send_mail(
        to="it@example.com", subject="Awaria\r\nBcc: x@evil.com", body="b", reply_to="a@example.com"
    )

    (message,) = sent_mails.messages
    assert message["Subject"] == "Awaria Bcc: x@evil.com"
    assert message["Bcc"] is None


async def test_smtp_error_propagates(monkeypatch):
    async def failing_send(*args, **kwargs):
        raise ConnectionRefusedError("smtp down")

    monkeypatch.setattr("app.mailer.aiosmtplib.send", failing_send)

    with pytest.raises(ConnectionRefusedError):
        await send_mail(to="it@example.com", subject="s", body="b", reply_to="a@example.com")
