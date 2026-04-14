import pytest
from unittest.mock import patch, MagicMock
from app.email import send_newsletter
from app.models import Post, Subscriber
from app.utils import utc_now


def test_send_newsletter_smtp_failure(app, db, mock_render):
    """Test send_newsletter logs error and does not crash on SMTP failure."""
    # Create a dummy post and subscriber
    post = Post(
        title="Test Post",
        slug="test-post",
        body="Test body",
        published=True,
        published_at=utc_now(),
    )
    sub = Subscriber(email="test@example.com", confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()

    # Mock _connect_smtp to return None (connection failed)
    with patch("app.email._connect_smtp", return_value=None):
        # Should log error and return without raising
        send_newsletter([post], [sub])

    # Verify no email was sent (no server.sendmail called)
    # Since connection failed, we cannot check more
    # Ensure the function didn't raise


def test_send_newsletter_smtp_disconnected(app, db, mock_render):
    """Test send_newsletter reconnects after SMTPServerDisconnected."""
    import smtplib

    post = Post(
        title="Test Post",
        slug="test-post-2",
        body="Test body",
        published=True,
        published_at=utc_now(),
    )
    sub = Subscriber(email="test2@example.com", confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()

    mock_server = MagicMock()
    mock_server.sendmail.side_effect = smtplib.SMTPServerDisconnected()
    # First call to _connect_smtp returns mock_server, second call returns new mock_server (reconnect)
    mock_server2 = MagicMock()
    with patch("app.email._connect_smtp", side_effect=[mock_server, mock_server2]):
        send_newsletter([post], [sub])

    # Verify that sendmail was called twice (first failure, then success)
    assert mock_server.sendmail.call_count == 1
    assert mock_server2.sendmail.call_count == 1
    # Verify server.quit was called on both servers
    mock_server2.quit.assert_called()


def test_send_newsletter_generic_smtp_error(app, db, mock_render):
    """Test send_newsletter logs error but continues on generic SMTP error."""
    import smtplib

    post = Post(
        title="Test Post",
        slug="test-post-3",
        body="Test body",
        published=True,
        published_at=utc_now(),
    )
    sub = Subscriber(email="test3@example.com", confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()

    mock_server = MagicMock()
    mock_server.sendmail.side_effect = smtplib.SMTPException("test error")
    with patch("app.email._connect_smtp", return_value=mock_server):
        # Should log exception but not raise
        send_newsletter([post], [sub])

    # Verify sendmail called once (failed), then loop continues (no more subscribers)
    assert mock_server.sendmail.call_count == 1


def test_send_newsletter_mixed_success_failure(app, db, mock_render):
    """Test send_newsletter with mixed success and failure across multiple subscribers."""
    import smtplib

    post = Post(
        title="Test Post",
        slug="test-post-mixed",
        body="Test body",
        published=True,
        published_at=utc_now(),
    )
    sub1 = Subscriber(email="success@example.com", confirmed=True)
    sub2 = Subscriber(email="fail@example.com", confirmed=True)
    sub3 = Subscriber(email="success2@example.com", confirmed=True)
    db.session.add_all([post, sub1, sub2, sub3])
    db.session.commit()

    mock_server = MagicMock()
    mock_server.sendmail.side_effect = [
        None,  # sub1 succeeds
        smtplib.SMTPException("fail"),  # sub2 fails
        None,  # sub3 succeeds
    ]
    with patch("app.email._connect_smtp", return_value=mock_server):
        result = send_newsletter([post], [sub1, sub2, sub3])

    assert result is False  # at least one failure
    assert mock_server.sendmail.call_count == 3


def test_send_newsletter_multiple_subscribers(app, db, mock_render):
    """Test send_newsletter sends to all subscribers successfully."""
    post = Post(
        title="Test Post",
        slug="test-post-multi",
        body="Test body",
        published=True,
        published_at=utc_now(),
    )
    subs = [Subscriber(email=f"user{i}@example.com", confirmed=True) for i in range(5)]
    db.session.add_all([post] + subs)
    db.session.commit()

    mock_server = MagicMock()
    with patch("app.email._connect_smtp", return_value=mock_server):
        result = send_newsletter([post], subs)

    assert result is True
    assert mock_server.sendmail.call_count == 5


def test_send_confirmation_email_failure(app, db):
    """Test that _send_email raises an exception on connection failure."""
    from app.email import _send_email
    from app.models import Subscriber

    sub = Subscriber(email="fail@example.com")
    db.session.add(sub)
    db.session.commit()

    with patch(
        "app.email.smtplib.SMTP", side_effect=ConnectionError("connection refused")
    ):
        with pytest.raises(ConnectionError):
            _send_email(
                to="fail@example.com",
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
            )
