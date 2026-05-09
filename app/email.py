import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Any
from flask import render_template
from smtplib import SMTP

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


def send_confirmation(subscriber: Any) -> None:
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


def send_password_reset(user: Any, token: str) -> None:
    reset_url = f"{BASE_URL}/admin/reset/{token}"
    html = render_template(
        "email/password_reset.html",
        user=user,
        site_title=APP_TITLE,
        reset_url=reset_url,
    )
    text = (
        f"Password Reset Request for {APP_TITLE}\n\n"
        f"Click this link to reset your password: {reset_url}\n\n"
        f"If you didn't request this, you can safely ignore this email.\n"
        f"This link will expire in 1 hour."
    )
    _send_email(user.email, f"Password Reset for {APP_TITLE}", html, text)


def _connect_smtp() -> Optional[smtplib.SMTP]:
    """Open an authenticated SMTP connection. Returns None on failure."""
    server = None
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
        server.ehlo()
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return server
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPConnectError, smtplib.SMTPSenderRefused, OSError):
        logger.exception("Failed to connect to SMTP server")
        if server is not None:
            try:
                server.quit()
            except OSError:
                pass
        return None


def _send_email_with_retry(
    server: Optional[SMTP],
    from_address: str,
    to: str,
    msg_str: str,
    max_retries: int = 3,
) -> tuple[bool, str, Optional[SMTP]]:
    """Send an email with retry logic and exponential backoff.

    Returns (success, error_message, server). The server may be a new connection
    if reconnection occurred during retry.
    """

    last_error = ""
    for attempt in range(max_retries):
        try:
            if server is None:
                return False, "Server is None", None
            server.sendmail(from_address, to, msg_str)
            return True, "", server
        except smtplib.SMTPServerDisconnected:
            last_error = "SMTP server disconnected"
            if attempt < max_retries - 1:
                try:
                    new_server = _connect_smtp()
                    if not new_server:
                        last_error = "SMTP reconnection failed"
                        break
                    server = new_server
                except (smtplib.SMTPAuthenticationError, smtplib.SMTPConnectError, smtplib.SMTPSenderRefused, OSError):
                    last_error = "SMTP reconnection failed"
                    break
        except smtplib.SMTPException as e:
            last_error = str(e)
        except OSError as e:
            last_error = str(e)
    return False, last_error, server


def send_newsletter(posts: list[Any], subscribers: Any, total_subscribers: Optional[int] = None) -> bool:
    """Send newsletter to all subscribers.

    Args:
        posts: List of posts to include in the newsletter
        subscribers: Generator or list of Subscriber objects
        total_subscribers: Optional count of subscribers for progress logging

    Returns True if all sent successfully, False otherwise.
    """
    from app.config import NEWSLETTER_MAX_RETRY_ATTEMPTS

    if not posts or not subscribers:
        return True

    server = _connect_smtp()
    if not server:
        logger.error("Cannot send newsletter: SMTP connection failed")
        return False

    unsub_url_base = f"{BASE_URL}/unsubscribe/"
    unsub_placeholder = "%%UNSUB_PLACEHOLDER%%"
    pre_rendered_html = render_template(
        "email/newsletter.html",
        posts=posts,
        site_title=APP_TITLE,
        base_url=BASE_URL,
        unsubscribe_url=unsub_placeholder,
    )
    pre_rendered_text = (
        f"Latest from {APP_TITLE}\n\n"
        + "\n\n".join(
            f"{p.title}\n{BASE_URL}/post/{p.slug}\n{p.summary}" for p in posts
        )
        + f"\n\nUnsubscribe: {unsub_placeholder}"
    )

    all_sent = True
    try:
        for i, sub in enumerate(subscribers, 1):
            unsub_url = unsub_url_base + sub.token
            html = pre_rendered_html.replace(unsub_placeholder, unsub_url)
            text = pre_rendered_text.replace(unsub_placeholder, unsub_url)
            msg = MIMEMultipart("alternative")
            msg["From"] = FROM_ADDRESS
            msg["To"] = sub.email
            msg["Subject"] = f"Latest from {APP_TITLE}"
            msg["List-Unsubscribe"] = f"<{unsub_url}>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            success, error, server = _send_email_with_retry(
                server, FROM_ADDRESS, sub.email, msg.as_string(),
                max_retries=NEWSLETTER_MAX_RETRY_ATTEMPTS
            )
            if not success:
                logger.warning(
                    "Failed to send newsletter to %s after %d attempts: %s",
                    sub.email, NEWSLETTER_MAX_RETRY_ATTEMPTS, error
                )
                all_sent = False

            if total_subscribers and i % 50 == 0:
                logger.info(
                    "Newsletter progress: %d/%d sent", i, total_subscribers
                )
    finally:
        if server:
            try:
                server.quit()
            except OSError:
                pass
    return all_sent
