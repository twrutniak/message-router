from email.message import EmailMessage

import aiosmtplib

from app.settings import settings


async def send_mail(*, to: str, subject: str, body: str, reply_to: str) -> None:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    message["Reply-To"] = reply_to
    message["Subject"] = " ".join(subject.split())
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        timeout=settings.smtp_timeout,
    )
