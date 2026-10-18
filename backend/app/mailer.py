"""Outgoing email (OTP codes). SMTP when configured, otherwise logged to the console for local development."""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from .config import get_settings

log = logging.getLogger(__name__)


class MailError(RuntimeError):
    pass


def send_email(to: str, subject: str, body: str) -> None:
    s = get_settings()
    if not s.smtp_host:
        log.warning("SMTP not configured; email to %s not sent.\nSubject: %s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"] = s.smtp_from or s.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        if s.smtp_security == "ssl":
            server = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, context=ssl.create_default_context(), timeout=15)
        else:
            server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15)
        with server:
            if s.smtp_security == "starttls":
                server.starttls(context=ssl.create_default_context())
            if s.smtp_user:
                server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        log.error("sending email to %s failed: %s", to, e)
        raise MailError("Could not send email") from e
