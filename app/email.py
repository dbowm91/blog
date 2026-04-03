import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from flask import render_template

from app.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    FROM_ADDRESS,
    APP_TITLE,
    BASE_URL,
    SMTP_TIMEOUT,
)

logger = logging.getLogger(__name__)


def _send_email(
    to: str, subject: str, html_body: str, text_body: Optional[str] = None
) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = FROM_ADDRESS
    msg["To"] = to
    msg["Subject"] = subject

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
        server.ehlo()
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(FROM_ADDRESS, to, msg.as_string())


def send_confirmation(subscriber) -> None:
    unsub_url = f"{BASE_URL}/unsubscribe/{subscriber.token}"
    html = render_template(
        "email/confirm.html",
        subscriber=subscriber,
        site_title=APP_TITLE,
        base_url=BASE_URL,
        unsubscribe_url=unsub_url,
    )
    text = (
        f"Confirm your subscription to {APP_TITLE}\n\n"
        f"Click this link to confirm: {BASE_URL}/confirm/{subscriber.token}\n\n"
        f"If you didn't request this, you can unsubscribe: {unsub_url}"
    )
    _send_email(
        subscriber.email, f"Confirm your subscription to {APP_TITLE}", html, text
    )


def _connect_smtp() -> Optional[smtplib.SMTP]:
    """Open an authenticated SMTP connection. Returns None on failure."""
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
        server.ehlo()
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return server
    except Exception:
        logger.exception("Failed to connect to SMTP server")
        return None


def send_newsletter(posts, subscribers) -> bool:
    if not posts or not subscribers:
        return True

    server = _connect_smtp()
    if not server:
        logger.error("Cannot send newsletter: SMTP connection failed")
        return False

    all_sent = True
    try:
        for i, sub in enumerate(subscribers, 1):
            unsub_url = f"{BASE_URL}/unsubscribe/{sub.token}"
            html = render_template(
                "email/newsletter.html",
                posts=posts,
                site_title=APP_TITLE,
                base_url=BASE_URL,
                unsubscribe_url=unsub_url,
            )
            text = (
                f"Latest from {APP_TITLE}\n\n"
                + "\n\n".join(
                    f"{p.title}\n{BASE_URL}/post/{p.slug}\n{p.summary}" for p in posts
                )
                + f"\n\nUnsubscribe: {unsub_url}"
            )
            msg = MIMEMultipart("alternative")
            msg["From"] = FROM_ADDRESS
            msg["To"] = sub.email
            msg["Subject"] = f"Latest from {APP_TITLE}"
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))
            try:
                server.sendmail(FROM_ADDRESS, sub.email, msg.as_string())
                if i % 50 == 0:
                    logger.info("Newsletter progress: %d/%d sent", i, len(subscribers))
            except smtplib.SMTPServerDisconnected:
                logger.exception(
                    "SMTP disconnected while sending to %s; reconnecting", sub.email
                )
                all_sent = False
                server = _connect_smtp()
                if not server:
                    logger.error(
                        "SMTP reconnection failed; aborting newsletter after %d/%d",
                        i - 1,
                        len(subscribers),
                    )
                    break
                try:
                    server.sendmail(FROM_ADDRESS, sub.email, msg.as_string())
                    all_sent = True
                except smtplib.SMTPException:
                    logger.exception(
                        "Failed to send newsletter to %s after reconnect", sub.email
                    )
            except smtplib.SMTPException:
                logger.exception("Failed to send newsletter to %s", sub.email)
                all_sent = False
    finally:
        try:
            server.quit()
        except Exception:
            pass
    return all_sent
