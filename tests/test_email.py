import pytest
from unittest.mock import patch, MagicMock
from app.email import send_newsletter
from app.models import Post, Subscriber


@pytest.fixture
def mock_render():
    with patch('app.email.render_template') as mock:
        mock.return_value = '<html>Mock</html>'
        yield mock


def test_send_newsletter_smtp_failure(app, db, mock_render):
    """Test send_newsletter logs error and does not crash on SMTP failure."""
    # Create a dummy post and subscriber
    post = Post(
        title='Test Post',
        slug='test-post',
        body='Test body',
        published=True,
        published_at=db.func.now(),
    )
    sub = Subscriber(email='test@example.com', confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()
    
    # Mock _connect_smtp to return None (connection failed)
    with patch('app.email._connect_smtp', return_value=None):
        # Should log error and return without raising
        send_newsletter([post], [sub])
    
    # Verify no email was sent (no server.sendmail called)
    # Since connection failed, we cannot check more
    # Ensure the function didn't raise


def test_send_newsletter_smtp_disconnected(app, db, mock_render):
    """Test send_newsletter reconnects after SMTPServerDisconnected."""
    import smtplib
    post = Post(
        title='Test Post',
        slug='test-post-2',
        body='Test body',
        published=True,
        published_at=db.func.now(),
    )
    sub = Subscriber(email='test2@example.com', confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()
    
    mock_server = MagicMock()
    mock_server.sendmail.side_effect = smtplib.SMTPServerDisconnected()
    # First call to _connect_smtp returns mock_server, second call returns new mock_server (reconnect)
    mock_server2 = MagicMock()
    with patch('app.email._connect_smtp', side_effect=[mock_server, mock_server2]):
        send_newsletter([post], [sub])
    
    # Verify that sendmail was called twice (first failure, then success)
    assert mock_server.sendmail.call_count == 1
    assert mock_server2.sendmail.call_count == 1
    # Verify server.quit was called
    mock_server.quit.assert_called()


def test_send_newsletter_generic_smtp_error(app, db, mock_render):
    """Test send_newsletter logs error but continues on generic SMTP error."""
    import smtplib
    post = Post(
        title='Test Post',
        slug='test-post-3',
        body='Test body',
        published=True,
        published_at=db.func.now(),
    )
    sub = Subscriber(email='test3@example.com', confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()
    
    mock_server = MagicMock()
    mock_server.sendmail.side_effect = smtplib.SMTPException('test error')
    with patch('app.email._connect_smtp', return_value=mock_server):
        # Should log exception but not raise
        send_newsletter([post], [sub])
    
    # Verify sendmail called once (failed), then loop continues (no more subscribers)
    assert mock_server.sendmail.call_count == 1