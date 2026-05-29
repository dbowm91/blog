"""Tests for webhooks module."""

import hashlib
import hmac
import json
from unittest.mock import patch, MagicMock


class TestSignWebhookPayload:
    """Tests for sign_webhook_payload function."""

    def test_sign_webhook_payload_basic(self):
        """Test basic payload signing."""
        from app.webhooks import sign_webhook_payload

        payload = {"event": "test", "data": "value"}
        secret = "test-secret"

        result = sign_webhook_payload(payload, secret)

        assert result.startswith("sha256=")
        signature = result[7:]

        expected_payload = json.dumps(payload, sort_keys=True).encode("utf-8")
        expected_sig = hmac.new(
            secret.encode("utf-8"), expected_payload, hashlib.sha256
        ).hexdigest()

        assert signature == expected_sig

    def test_sign_webhook_payload_empty_payload(self):
        """Test signing empty payload."""
        from app.webhooks import sign_webhook_payload

        payload = {}
        secret = "test-secret"

        result = sign_webhook_payload(payload, secret)

        assert result.startswith("sha256=")
        assert len(result) == 7 + 64

    def test_sign_webhook_payload_different_secrets(self):
        """Test that different secrets produce different signatures."""
        from app.webhooks import sign_webhook_payload

        payload = {"event": "test"}
        sig1 = sign_webhook_payload(payload, "secret1")
        sig2 = sign_webhook_payload(payload, "secret2")

        assert sig1 != sig2

    def test_sign_webhook_payload_deterministic(self):
        """Test that same payload and secret produce same signature."""
        from app.webhooks import sign_webhook_payload

        payload = {"key": "value"}
        secret = "secret"

        sig1 = sign_webhook_payload(payload, secret)
        sig2 = sign_webhook_payload(payload, secret)

        assert sig1 == sig2

    def test_sign_webhook_payload_key_order_matters(self):
        """Test that JSON key order affects signature."""
        from app.webhooks import sign_webhook_payload

        payload1 = {"a": 1, "b": 2}
        payload2 = {"b": 2, "a": 1}
        secret = "secret"

        sig1 = sign_webhook_payload(payload1, secret)
        sig2 = sign_webhook_payload(payload2, secret)

        assert sig1 == sig2


class TestDeliverWebhook:
    """Tests for deliver_webhook function."""

    def test_deliver_webhook_success(self):
        """Test successful webhook delivery."""
        from app.webhooks import deliver_webhook

        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch("app.utils.is_safe_webhook_url") as mock_ssrf,
            patch("requests.post") as mock_post,
        ):
            mock_ssrf.return_value = (True, "")
            mock_post.return_value = mock_response

            success, message = deliver_webhook(
                "https://example.com/webhook", {"event": "test"}, "secret"
            )

            assert success is True
            assert "200" in message

    def test_deliver_webhook_ssrf_blocked(self):
        """Test webhook delivery blocked by SSRF protection."""
        from app.webhooks import deliver_webhook

        with patch("app.utils.is_safe_webhook_url") as mock_ssrf:
            mock_ssrf.return_value = (False, "Private IP range blocked")

            success, message = deliver_webhook(
                "http://10.0.0.1/webhook", {"event": "test"}, "secret"
            )

            assert success is False
            assert "SSRF protection" in message

    def test_deliver_webhook_localhost_blocked(self):
        """Test webhook delivery blocked for localhost URLs."""
        from app.webhooks import deliver_webhook

        with patch("app.utils.is_safe_webhook_url") as mock_ssrf:
            mock_ssrf.return_value = (False, "Localhost addresses not allowed")

            success, message = deliver_webhook(
                "http://localhost/webhook", {"event": "test"}, "secret"
            )

            assert success is False
            assert "SSRF protection" in message

    def test_deliver_webhook_http_error(self):
        """Test webhook delivery with HTTP error response."""
        from app.webhooks import deliver_webhook

        mock_response = MagicMock()
        mock_response.status_code = 500

        with (
            patch("app.utils.is_safe_webhook_url") as mock_ssrf,
            patch("requests.post") as mock_post,
        ):
            mock_ssrf.return_value = (True, "")
            mock_post.return_value = mock_response

            success, message = deliver_webhook(
                "https://example.com/webhook", {"event": "test"}, "secret"
            )

            assert success is False
            assert "500" in message

    def test_deliver_webhook_request_exception(self):
        """Test webhook delivery with request exception."""
        from app.webhooks import deliver_webhook
        from requests.exceptions import RequestException

        with (
            patch("app.utils.is_safe_webhook_url") as mock_ssrf,
            patch("requests.post") as mock_post,
        ):
            mock_ssrf.return_value = (True, "")
            mock_post.side_effect = RequestException("Connection refused")

            success, message = deliver_webhook(
                "https://example.com/webhook", {"event": "test"}, "secret"
            )

            assert success is False
            assert "Connection refused" in message

    def test_deliver_webhook_includes_signature_header(self):
        """Test that webhook request includes signature header."""
        from app.webhooks import deliver_webhook

        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch("app.utils.is_safe_webhook_url") as mock_ssrf,
            patch("requests.post") as mock_post,
        ):
            mock_ssrf.return_value = (True, "")
            mock_post.return_value = mock_response

            deliver_webhook("https://example.com/webhook", {"event": "test"}, "secret")

            call_kwargs = mock_post.call_args[1]
            assert "headers" in call_kwargs
            assert "X-Webhook-Signature" in call_kwargs["headers"]


class TestCreateWebhookEvent:
    """Tests for create_webhook_event function."""

    def test_create_webhook_event_success(self, db):
        """Test creating a webhook event."""
        from app.webhooks import create_webhook_event
        from app.models import WebhookEvent

        event_id = create_webhook_event(
            event_type="test_event", payload={"key": "value"}, target_id=1, target_type="post"
        )

        assert event_id is not None

        event = db.session.execute(
            db.select(WebhookEvent).filter_by(id=event_id)
        ).scalar_one_or_none()

        assert event is not None
        assert event.event_type == "test_event"
        assert event.payload == {"key": "value"}
        assert event.target_id == 1
        assert event.target_type == "post"

    def test_create_webhook_event_minimal(self, db):
        """Test creating webhook event with minimal data."""
        from app.webhooks import create_webhook_event
        from app.models import WebhookEvent

        event_id = create_webhook_event(event_type="minimal_event", payload={})

        event = db.session.execute(
            db.select(WebhookEvent).filter_by(id=event_id)
        ).scalar_one_or_none()

        assert event is not None
        assert event.event_type == "minimal_event"
        assert event.target_id is None
        assert event.target_type is None

    def test_create_webhook_event_with_webhook(self, db, admin_user):
        """Test creating webhook event associated with a webhook."""
        from app.webhooks import create_webhook_event
        from app.models import Webhook, WebhookEvent

        webhook = Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            secret="test-secret",
            event_type="test_event",
            enabled=True,
        )
        db.session.add(webhook)
        db.session.commit()

        event_id = create_webhook_event(
            event_type="test_event", payload={"data": "test"}, target_id=1, target_type="post"
        )

        event = db.session.execute(
            db.select(WebhookEvent).filter_by(id=event_id)
        ).scalar_one_or_none()

        assert event is not None
        assert event.event_type == "test_event"


class TestInitWebhooks:
    """Tests for init_webhooks function."""

    def test_init_webhooks_no_op(self, app):
        """Test that init_webhooks is a placeholder that does nothing."""
        from app.webhooks import init_webhooks

        init_webhooks(app)


class TestWebhookEventDeliveryStatus:
    """Tests for WebhookEvent.delivery_status field."""

    def test_delivery_status_delivered(self, db, admin_user):
        """Test delivery_status='delivered' when all webhooks succeed."""
        from app.webhooks import create_webhook_event
        from app.models import Webhook, WebhookEvent
        from unittest.mock import patch, MagicMock

        webhook = Webhook(
            name="Success Webhook",
            url="https://example.com/webhook",
            secret="test-secret",
            event_type="test_event",
            enabled=True,
        )
        db.session.add(webhook)
        db.session.commit()

        event_id = create_webhook_event(
            event_type="test_event", payload={"data": "test"}, target_id=1, target_type="post"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.utils.is_safe_webhook_url", return_value=(True, "")):
            with patch("requests.post", return_value=mock_response):
                from app.tasks import deliver_webhook_task

                deliver_webhook_task(event_id)

        event = db.session.get(WebhookEvent, event_id)
        assert event.delivery_status == "delivered"
        assert event.delivered is True

    def test_delivery_status_failed(self, db, admin_user):
        """Test delivery_status='failed' when all webhooks fail."""
        from app.webhooks import create_webhook_event
        from app.models import Webhook, WebhookEvent
        from unittest.mock import patch

        webhook = Webhook(
            name="Fail Webhook",
            url="https://example.com/webhook",
            secret="test-secret",
            event_type="fail_event",
            enabled=True,
        )
        db.session.add(webhook)
        db.session.commit()

        event_id = create_webhook_event(
            event_type="fail_event", payload={"data": "test"}, target_id=1, target_type="post"
        )

        with patch("app.utils.is_safe_webhook_url", return_value=(True, "")):
            with patch("requests.post") as mock_post:
                mock_post.side_effect = Exception("Connection refused")
                from app.tasks import deliver_webhook_task

                deliver_webhook_task(event_id)

        event = db.session.get(WebhookEvent, event_id)
        assert event.delivery_status == "failed"
        assert event.delivered is False

    def test_delivery_status_partial_failure(self, db, admin_user):
        """Test delivery_status='partial_failure' when some webhooks fail."""
        from app.webhooks import create_webhook_event
        from app.models import Webhook, WebhookEvent
        from unittest.mock import patch, MagicMock

        webhook1 = Webhook(
            name="Success Webhook",
            url="https://example.com/webhook1",
            secret="test-secret",
            event_type="partial_event",
            enabled=True,
        )
        webhook2 = Webhook(
            name="Fail Webhook",
            url="https://example.com/webhook2",
            secret="test-secret",
            event_type="partial_event",
            enabled=True,
        )
        db.session.add_all([webhook1, webhook2])
        db.session.commit()

        event_id = create_webhook_event(
            event_type="partial_event", payload={"data": "test"}, target_id=1, target_type="post"
        )

        success_response = MagicMock()
        success_response.status_code = 200

        with patch("app.utils.is_safe_webhook_url", return_value=(True, "")):
            with patch("requests.post") as mock_post:
                mock_post.side_effect = [success_response, Exception("Connection refused")]
                from app.tasks import deliver_webhook_task

                deliver_webhook_task(event_id)

        event = db.session.get(WebhookEvent, event_id)
        assert event.delivery_status == "partial_failure"

    def test_delivery_status_none_when_no_webhooks(self, db):
        """Test delivery_status=None when no webhooks configured."""
        from app.webhooks import create_webhook_event
        from app.models import WebhookEvent

        event_id = create_webhook_event(
            event_type="no_webhook_event", payload={"data": "test"}, target_id=1, target_type="post"
        )

        from app.tasks import deliver_webhook_task

        deliver_webhook_task(event_id)

        event = db.session.get(WebhookEvent, event_id)
        assert event.delivery_status is None
