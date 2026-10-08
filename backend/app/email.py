"""Отправка писем (fastapi-users: подтверждение почты, сброс пароля).

- dev (не задан SMTP_HOST): письмо дописывается в файл-«исходящие» EMAIL_OUTBOX
  (JSON-по-строчно) — так можно посмотреть ссылку и покрыть тестами;
- прод (задан SMTP_HOST): отправка через SMTP (в отдельном потоке, чтобы не
  блокировать event loop).
"""
import asyncio
import json
import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from .config import (
    EMAIL_OUTBOX,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_STARTTLS,
    SMTP_USER,
)

logger = logging.getLogger("app.email")


def _write_outbox(to: str, subject: str, text: str) -> None:
    record = {
        "to": to,
        "subject": subject,
        "text": text,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(EMAIL_OUTBOX, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.info("письмо (outbox) → %s: %s", to, subject)


def _send_smtp(to: str, subject: str, text: str) -> None:
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        if SMTP_STARTTLS:
            server.starttls()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    logger.info("письмо (smtp) → %s: %s", to, subject)


def send_email(to: str, subject: str, text: str) -> None:
    """Отправить письмо: SMTP, если настроен, иначе — в outbox-файл."""
    if SMTP_HOST:
        try:
            _send_smtp(to, subject, text)
            return
        except Exception:  # SMTP упал — не роняем запрос, кладём в outbox
            logger.exception("не удалось отправить письмо через SMTP")
    _write_outbox(to, subject, text)


async def send_email_async(to: str, subject: str, text: str) -> None:
    """То же самое, но не блокирует event loop."""
    await asyncio.to_thread(send_email, to, subject, text)
