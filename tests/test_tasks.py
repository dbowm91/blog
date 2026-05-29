from unittest.mock import patch, MagicMock
from app.models import Webhook, WebhookEvent
import json


def test_generate_image_variants_local_file_not_found(db):
    """Test generate_image_variants returns False if file not found."""
    from app.tasks import generate_image_variants

    with patch("app.storage.get_storage") as mock_get_storage:
        storage = MagicMock()
        storage.__class__.__name__ = "LocalStorageBackend"
        storage.exists.return_value = False
        mock_get_storage.return_value = storage
        result = generate_image_variants.apply(args=("nonexistent.jpg",))
        assert result.get() is False


def test_generate_image_variants_local_success(db, tmp_path):
    """Test generate_image_variants works for local storage."""
    from app.tasks import generate_image_variants
    from PIL import Image

    # Create a test image
    img_path = tmp_path / "test.jpg"
    img = Image.new("RGB", (1200, 800), color="red")
    img.save(img_path)

    # Mock storage to return local path
    with (
        patch("app.storage.get_storage") as mock_get_storage,
        patch("os.path.exists", return_value=True),
        patch("os.environ.get", return_value=str(tmp_path)),
    ):
        storage = MagicMock()
        storage.__class__.__name__ = "LocalStorageBackend"
        storage.exists.return_value = True
        mock_get_storage.return_value = storage

        result = generate_image_variants.apply(args=("test.jpg",))
        assert result.get() is True


def test_send_newsletter_task_no_posts(db):
    """Test send_newsletter_task returns False with no valid posts."""
    from app.tasks import send_newsletter_task

    result = send_newsletter_task.apply(args=([999],))
    assert result.get() is False


def test_send_newsletter_task_no_subscribers(db, sample_post):
    """Test send_newsletter_task returns False with no confirmed subscribers."""
    from app.tasks import send_newsletter_task

    result = send_newsletter_task.apply(args=([sample_post.id],))
    assert result.get() is False


def test_send_newsletter_task_success(db, sample_post, sample_subscriber, mock_email):
    """Test send_newsletter_task succeeds with valid posts and subscribers."""
    from app.tasks import send_newsletter_task

    sample_subscriber.confirmed = True
    db.session.commit()
    result = send_newsletter_task.apply(args=([sample_post.id],))
    assert result.get() is True


def test_deliver_webhook_task_event_not_found(db):
    """Test deliver_webhook_task returns False if event not found."""
    from app.tasks import deliver_webhook_task

    result = deliver_webhook_task.apply(args=(999,))
    assert result.get() is False


def test_deliver_webhook_task_no_webhooks(db):
    """Test deliver_webhook_task marks event delivered if no webhooks."""
    from app.tasks import deliver_webhook_task
    from app.models import WebhookEvent

    event = WebhookEvent(event_type="test", payload=json.dumps({"test": "data"}))
    db.session.add(event)
    db.session.commit()
    event_id = event.id
    result = deliver_webhook_task.apply(args=(event_id,))
    assert result.get() is True
    # Re-query event
    event = db.session.execute(db.select(WebhookEvent).filter_by(id=event_id)).scalar_one()
    assert event.delivered is True


def test_deliver_webhook_task_ssrf_block(db):
    """Test deliver_webhook_task blocks unsafe URLs."""
    from app.tasks import deliver_webhook_task

    webhook = Webhook(
        name="Test Webhook", url="http://169.254.169.254/latest", secret="secret", event_type="test"
    )
    db.session.add(webhook)
    event = WebhookEvent(event_type="test", payload=json.dumps({"test": "data"}))
    db.session.add(event)
    db.session.commit()

    with patch("app.utils.is_safe_webhook_url", return_value=(False, "SSRF risk")):
        result = deliver_webhook_task.apply(args=(event.id,))
        assert result.get() is False


def test_send_confirmation_task_user_not_found(db):
    """Test send_confirmation_task returns False if subscriber not found."""
    from app.tasks import send_confirmation_task

    result = send_confirmation_task.apply(args=(999,))
    assert result.get() is False


def test_send_confirmation_task_success(db, sample_subscriber):
    """Test send_confirmation_task succeeds."""
    from app.tasks import send_confirmation_task

    with patch("app.email.send_confirmation", return_value=True) as mock_send:
        result = send_confirmation_task.apply(args=(sample_subscriber.id,))
        assert result.get() is True
        mock_send.assert_called_once()


def test_send_password_reset_task_user_not_found(db):
    """Test send_password_reset_task returns False if user not found."""
    from app.tasks import send_password_reset_task

    result = send_password_reset_task.apply(args=(999, "token"))
    assert result.get() is False


def test_send_password_reset_task_success(db, admin_user, mock_email):
    """Test send_password_reset_task succeeds."""
    from app.tasks import send_password_reset_task

    admin_user.email = "admin@example.com"
    db.session.commit()
    with patch("app.email._send_email") as mock_send:
        mock_send.return_value = True
        result = send_password_reset_task.apply(args=(admin_user.id, "test-token"))
        assert result.get() is True
