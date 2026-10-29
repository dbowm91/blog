"""Coverage for app/tasks.py.

Targets the failure paths of the Celery tasks: S3 variant generation, a
newsletter that cannot be delivered, webhook retries, a failing backup and a
comment notification.
"""

from __future__ import annotations

import io
import logging
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
import requests
from celery.exceptions import MaxRetriesExceededError, Retry
from PIL import Image


def _fake_botocore(monkeypatch):
    """Install a stub botocore package and return its error classes."""
    exceptions = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        def __init__(self, response=None, operation_name=None):
            super().__init__(str(response))
            self.response = response
            self.operation_name = operation_name

    class BotoCoreError(Exception):
        pass

    exceptions.ClientError = ClientError
    exceptions.BotoCoreError = BotoCoreError

    botocore = types.ModuleType("botocore")
    botocore.exceptions = exceptions

    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", exceptions)

    return types.SimpleNamespace(
        botocore=botocore,
        exceptions=exceptions,
        ClientError=ClientError,
        BotoCoreError=BotoCoreError,
    )


class _ChunkBody:
    """Minimal stand-in for a botocore streaming body."""

    def __init__(self, payload: bytes = b""):
        self.payload = payload

    def iter_chunks(self, chunk_size=None):
        if self.payload:
            yield self.payload


@pytest.fixture
def webhook_pair(db):
    from app.models import Webhook, WebhookEvent

    webhook = Webhook(
        name="Hook",
        url="https://example.com/hook",
        event_type="post.created",
    )
    webhook.secret = "sectest"
    event = WebhookEvent(event_type="post.created", payload={"id": 1})
    db.session.add(webhook)
    db.session.add(event)
    db.session.commit()
    return webhook, event


def test_generate_image_variants_resizes_wide_images(db, tmp_path, monkeypatch):
    from app.storage import LocalStorageBackend
    from app.tasks import generate_image_variants

    Image.new("RGB", (1600, 1200), color="red").save(tmp_path / "wide.png")
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path))
    backend = LocalStorageBackend(str(tmp_path))

    with patch("app.storage.get_storage", return_value=backend):
        result = generate_image_variants.apply(args=("wide.png",))

    assert result.get() is True
    for width in (400, 800, 1200):
        assert (tmp_path / f"{width}_wide.webp").exists()
        assert (tmp_path / f"{width}_wide.png").exists()


def test_generate_image_variants_uploads_s3_variants(db, monkeypatch):
    from app.storage import S3StorageBackend
    from app.tasks import generate_image_variants

    _fake_botocore(monkeypatch)

    buffer = io.BytesIO()
    Image.new("RGB", (1600, 1200), color="blue").save(buffer, format="PNG")

    backend = S3StorageBackend(bucket="blog-bucket", region="eu-west-1")
    client = MagicMock(name="s3-client")
    client.get_object.return_value = {"Body": _ChunkBody(buffer.getvalue())}
    backend._client = client

    with patch("app.storage.get_storage", return_value=backend):
        result = generate_image_variants.apply(args=("wide.png",))

    assert result.get() is True
    saved = sorted(call.kwargs["Key"] for call in client.put_object.call_args_list)
    assert saved == [
        "1200_wide.png",
        "1200_wide.webp",
        "400_wide.png",
        "400_wide.webp",
        "800_wide.png",
        "800_wide.webp",
    ]


def test_generate_image_variants_returns_false_when_the_s3_read_fails(db, monkeypatch):
    from app.storage import S3StorageBackend
    from app.tasks import generate_image_variants

    fake = _fake_botocore(monkeypatch)

    backend = S3StorageBackend(bucket="blog-bucket", region="eu-west-1")
    client = MagicMock(name="s3-client")
    client.get_object.side_effect = fake.ClientError({"Error": "missing"})
    backend._client = client

    with patch("app.storage.get_storage", return_value=backend):
        result = generate_image_variants.apply(args=("wide.png",))

    assert result.get() is False


def test_generate_image_variants_returns_false_for_an_empty_s3_object(db, monkeypatch):
    from app.storage import S3StorageBackend
    from app.tasks import generate_image_variants

    _fake_botocore(monkeypatch)

    backend = S3StorageBackend(bucket="blog-bucket", region="eu-west-1")
    client = MagicMock(name="s3-client")
    client.get_object.return_value = {"Body": _ChunkBody()}
    backend._client = client

    with patch("app.storage.get_storage", return_value=backend):
        result = generate_image_variants.apply(args=("wide.png",))

    assert result.get() is False


def test_send_newsletter_task_counts_a_failed_delivery(db, sample_post, sample_subscriber):
    from app.models import Post
    from app.tasks import send_newsletter_task

    sample_subscriber.confirmed = True
    db.session.commit()
    post_id = sample_post.id

    with patch("app.email.send_newsletter", return_value=False):
        with pytest.raises(Retry):
            send_newsletter_task.apply(args=([post_id],))

    post = db.session.get(Post, post_id)
    assert post.newsletter_attempts == 1
    assert post.newsletter_sent_at is None


def test_deliver_single_webhook_task_returns_false_without_a_webhook(db):
    from app.models import WebhookEvent
    from app.tasks import deliver_single_webhook_task

    event = WebhookEvent(event_type="post.created", payload={"id": 1})
    db.session.add(event)
    db.session.commit()
    event_id = event.id

    result = deliver_single_webhook_task.apply(args=(event_id, 999))

    assert result.get() is False


def test_deliver_single_webhook_task_skips_a_webhook_without_a_secret(db):
    from app.models import Webhook, WebhookEvent
    from app.tasks import deliver_single_webhook_task

    webhook = Webhook(
        name="Hook",
        url="https://example.com/hook",
        event_type="post.created",
    )
    event = WebhookEvent(event_type="post.created", payload={"id": 1})
    db.session.add(webhook)
    db.session.add(event)
    db.session.commit()
    event_id = event.id
    webhook_id = webhook.id

    with patch("app.utils.is_safe_webhook_url", return_value=(True, "URL is safe")):
        result = deliver_single_webhook_task.apply(args=(event_id, webhook_id))

    assert result.get() is False
    stored = db.session.get(WebhookEvent, event_id)
    assert stored.failed_deliveries == 1
    assert stored.delivery_attempts == 1


def test_deliver_single_webhook_task_retries_an_http_error(db, webhook_pair):
    from app.models import WebhookEvent
    from app.tasks import deliver_single_webhook_task

    webhook, event = webhook_pair
    event_id = event.id
    webhook_id = webhook.id
    response = MagicMock(status_code=500)

    with (
        patch("app.utils.is_safe_webhook_url", return_value=(True, "URL is safe")),
        patch("requests.post", return_value=response),
    ):
        with pytest.raises(Retry):
            deliver_single_webhook_task.apply(args=(event_id, webhook_id))

    stored = db.session.get(WebhookEvent, event_id)
    assert stored.delivery_attempts == 1
    assert stored.failed_deliveries == 0


def test_deliver_single_webhook_task_retries_a_failed_request(db, webhook_pair):
    from app.models import WebhookEvent
    from app.tasks import deliver_single_webhook_task

    webhook, event = webhook_pair
    event_id = event.id
    webhook_id = webhook.id

    with (
        patch("app.utils.is_safe_webhook_url", return_value=(True, "URL is safe")),
        patch("requests.post", side_effect=requests.RequestException("connection reset")),
    ):
        with pytest.raises(Retry):
            deliver_single_webhook_task.apply(args=(event_id, webhook_id))

    stored = db.session.get(WebhookEvent, event_id)
    assert stored.delivery_attempts == 1
    assert stored.failed_deliveries == 0


def test_deliver_single_webhook_task_handles_exhausted_retries(db, webhook_pair):
    from app.models import WebhookEvent
    from app.tasks import deliver_single_webhook_task

    webhook, event = webhook_pair
    event_id = event.id
    webhook_id = webhook.id

    with (
        patch("app.utils.is_safe_webhook_url", return_value=(True, "URL is safe")),
        patch("requests.post", side_effect=MaxRetriesExceededError("no retries left")),
    ):
        result = deliver_single_webhook_task.apply(args=(event_id, webhook_id))

    assert result.get() is False
    stored = db.session.get(WebhookEvent, event_id)
    assert stored.failed_deliveries == 1
    assert stored.delivery_status == "failed"


def test_deliver_single_webhook_task_reraises_a_retry(db, webhook_pair):
    from app.tasks import deliver_single_webhook_task

    webhook, event = webhook_pair

    with (
        patch("app.utils.is_safe_webhook_url", return_value=(True, "URL is safe")),
        patch("requests.post", side_effect=Retry("try again later")),
    ):
        with pytest.raises(Retry):
            deliver_single_webhook_task.apply(args=(event.id, webhook.id))


def test_update_delivery_status_warns_about_celery_concurrency(
    db, webhook_pair, monkeypatch, caplog
):
    from app.tasks import _update_delivery_status

    _, event = webhook_pair
    monkeypatch.setenv("CELERYD_CONCURRENCY", "4")

    with caplog.at_level(logging.WARNING):
        _update_delivery_status(event, db)

    assert "concurrency" in caplog.text.lower()


def test_update_delivery_status_ignores_a_non_numeric_concurrency(db, webhook_pair, monkeypatch):
    from app.tasks import _update_delivery_status

    _, event = webhook_pair
    monkeypatch.setenv("CELERYD_CONCURRENCY", "not-a-number")

    _update_delivery_status(event, db)

    assert event.delivery_status is None


def test_update_delivery_status_waits_for_every_webhook(db, webhook_pair):
    from app.tasks import _update_delivery_status

    _, event = webhook_pair

    _update_delivery_status(event, db)

    assert event.delivery_status is None
    assert event.delivered is False


def test_send_confirmation_task_retries_when_sending_fails(db, sample_subscriber):
    from app.tasks import send_confirmation_task

    subscriber_id = sample_subscriber.id

    with patch("app.email.send_confirmation", side_effect=RuntimeError("smtp is down")):
        with pytest.raises(Retry):
            send_confirmation_task.apply(args=(subscriber_id,))


def test_send_password_reset_task_retries_when_sending_fails(db, admin_user):
    from app.tasks import send_password_reset_task

    user_id = admin_user.id

    with patch("app.email.send_password_reset", side_effect=RuntimeError("smtp is down")):
        with pytest.raises(Retry):
            send_password_reset_task.apply(args=(user_id, "token"))


def test_run_backup_task_creates_a_backup(db, tmp_path):
    from app.tasks import run_backup_task

    backup_dir = tmp_path / "backups"

    with patch("app.services.backup.resolve_backup_dir", return_value=str(backup_dir)):
        result = run_backup_task.apply(args=())

    assert result.get() is True
    assert list(backup_dir.iterdir())


def test_run_backup_task_returns_false_without_a_database_file(db, tmp_path):
    from app.tasks import run_backup_task

    with (
        patch("app.services.backup.resolve_backup_dir", return_value=str(tmp_path)),
        patch("app.services.backup.resolve_database_file", return_value=None),
    ):
        result = run_backup_task.apply(args=())

    assert result.get() is False


def test_run_backup_task_reports_a_failing_backup(db, tmp_path):
    from app.tasks import run_backup_task

    with (
        patch("app.services.backup.resolve_backup_dir", return_value=str(tmp_path)),
        patch("app.services.backup.create_backup", side_effect=OSError("disk full")),
    ):
        result = run_backup_task.apply(args=())

    assert result.get() is False


def test_notify_pending_comment_task_notifies_the_admins(db, sample_post, admin_user):
    from app.models import Comment
    from app.tasks import notify_pending_comment_task

    comment = Comment(
        post_id=sample_post.id,
        author_name="Reader",
        author_email="reader@example.com",
        content="Nice post",
    )
    db.session.add(comment)
    db.session.commit()

    with patch("app.email._send_email") as mock_send:
        result = notify_pending_comment_task.apply(args=(comment.id,))

    assert result.get() is True
    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == admin_user.email
    assert "Nice post" in mock_send.call_args.args[2]


def test_notify_pending_comment_task_returns_false_without_a_comment(db):
    from app.tasks import notify_pending_comment_task

    result = notify_pending_comment_task.apply(args=(999,))

    assert result.get() is False


def test_notify_pending_comment_task_copes_with_a_missing_post(db, admin_user):
    from app.models import Comment
    from app.tasks import notify_pending_comment_task

    comment = Comment(
        post_id=999999,
        author_name="Reader",
        author_email="reader@example.com",
        content="Nice post",
    )
    db.session.add(comment)
    db.session.commit()
    comment_id = comment.id

    with patch("app.email._send_email") as mock_send:
        result = notify_pending_comment_task.apply(args=(comment_id,))

    assert result.get() is True
    mock_send.assert_called_once()
    assert "Unknown post" in mock_send.call_args.args[1]


def test_notify_pending_comment_task_reports_a_failing_mailer(db, sample_post, admin_user):
    from app.models import Comment
    from app.tasks import notify_pending_comment_task

    comment = Comment(
        post_id=sample_post.id,
        author_name="Reader",
        author_email="reader@example.com",
        content="Nice post",
    )
    db.session.add(comment)
    db.session.commit()

    with patch("app.email._send_email", side_effect=OSError("smtp is down")):
        result = notify_pending_comment_task.apply(args=(comment.id,))

    assert result.get() is False
