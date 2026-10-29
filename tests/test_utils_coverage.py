"""The shared error-handling helpers and the webhook URL guard.

`app/utils.py` is used by the storage, security, scheduler and database
layers, so its error helpers decide what a failure looks like in the log and
what a caller receives. `is_safe_webhook_url` is the SSRF guard in front of
every outbound webhook delivery.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from app.utils import (
    ErrorLogContext,
    handle_error,
    is_safe_webhook_url,
    log_scheduler_error,
    safe_delete_file,
    sanitize_css,
    unified_error_handler,
    xml_escape,
)


class TestSchedulerErrorLog:
    def test_the_exception_is_part_of_the_message(self, caplog):
        with caplog.at_level("ERROR"):
            log_scheduler_error("newsletter_send", "sending failed", ValueError("boom"))

        assert "scheduler_error" in caplog.text
        assert "ValueError" in caplog.text

    def test_the_message_stands_alone_without_an_exception(self, caplog):
        with caplog.at_level("ERROR"):
            log_scheduler_error("newsletter_send", "sending failed")

        assert "scheduler_error" in caplog.text
        assert "exception=" not in caplog.text


class TestHandleError:
    def test_a_storage_failure_is_logged_as_a_storage_error(self, caplog):
        with caplog.at_level("ERROR"):
            handle_error(ErrorLogContext.STORAGE, "upload", "could not save")

        assert "storage_error" in caplog.text

    def test_a_scheduler_failure_is_logged_as_a_scheduler_error(self, caplog):
        with caplog.at_level("ERROR"):
            handle_error(ErrorLogContext.SCHEDULER, "backup", "could not run")

        assert "scheduler_error" in caplog.text

    def test_a_security_failure_is_logged_as_a_security_event(self, caplog):
        with caplog.at_level("WARNING"):
            handle_error(ErrorLogContext.SECURITY, "login", "rejected", ValueError("bad"))

        assert "security_event" in caplog.text

    def test_any_other_context_is_logged_under_its_own_name(self, caplog):
        with caplog.at_level("ERROR"):
            handle_error(ErrorLogContext.DATABASE, "query", "failed")

        assert "database_error" in caplog.text

    def test_the_default_is_returned_when_nothing_is_raised(self):
        assert (
            handle_error(ErrorLogContext.STORAGE, "upload", "failed", default="fallback")
            == "fallback"
        )

    def test_the_exception_is_raised_again_when_asked(self):
        error = ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            handle_error(ErrorLogContext.STORAGE, "upload", "failed", error, reraise=True)

    def test_a_failure_without_an_exception_still_raises(self):
        with pytest.raises(RuntimeError, match="upload failed"):
            handle_error(ErrorLogContext.STORAGE, "upload", "failed", reraise=True)


class TestUnifiedErrorHandler:
    def test_the_wrapped_function_returns_its_value(self):
        @unified_error_handler(ErrorLogContext.STORAGE, "read", "reading failed")
        def read() -> str:
            return "value"

        assert read() == "value"

    def test_a_failure_is_swallowed_and_the_default_returned(self, caplog):
        @unified_error_handler(
            ErrorLogContext.STORAGE, "read", "reading failed", default="fallback"
        )
        def read() -> str:
            raise ValueError("boom")

        with caplog.at_level("ERROR"):
            assert read() == "fallback"

        assert "storage_error" in caplog.text

    def test_a_failure_is_raised_again_when_asked(self):
        @unified_error_handler(ErrorLogContext.STORAGE, "read", "reading failed", reraise=True)
        def read() -> str:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            read()


class TestSafeDeleteFile:
    def test_a_file_the_storage_backend_knows_is_deleted(self, app, tmp_path):
        from app.extensions import db  # noqa: F401

        with app.app_context():
            from app.storage import get_storage

            storage = get_storage()
            storage.save("safe-delete-target.png", b"data")
            assert safe_delete_file("safe-delete-target.png") is True
            assert storage.exists("safe-delete-target.png") is False

    def test_a_missing_file_is_not_an_error(self, app):
        with app.app_context():
            assert safe_delete_file("never-existed.png") is True

    def test_a_failure_is_reported(self, app):
        with app.app_context():
            with patch("app.storage.get_storage", side_effect=OSError("disk gone")):
                assert safe_delete_file("whatever.png") is False


class TestXmlEscape:
    def test_an_empty_string_stays_empty(self):
        assert xml_escape("") == ""

    def test_markup_is_escaped(self):
        assert xml_escape('<a href="x">&</a>') == "&lt;a href=&quot;x&quot;&gt;&amp;&lt;/a&gt;"


class TestSanitizeCss:
    def test_empty_css_stays_empty(self):
        assert sanitize_css("") == ""

    def test_an_allowlisted_property_survives(self):
        assert "color" in sanitize_css("p { color: red; }")

    def test_a_property_outside_the_allowlist_is_removed(self):
        assert "behavior" not in sanitize_css("p { behavior: url(x); }")


def _addr_info(ip: str) -> tuple:
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sockaddr = (ip, 0, 0, 0) if family == socket.AF_INET6 else (ip, 0)
    return (family, socket.SOCK_STREAM, 6, "", sockaddr)


class TestIsSafeWebhookUrl:
    def test_a_public_address_is_allowed(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("93.184.216.34")]):
            assert is_safe_webhook_url("https://example.com/hook") == (True, "URL is safe")

    def test_a_malformed_url_is_rejected(self):
        safe, reason = is_safe_webhook_url("http://[::1]extra/hook")

        assert safe is False
        assert "Invalid URL" in reason

    def test_a_non_http_scheme_is_rejected(self):
        safe, reason = is_safe_webhook_url("ftp://example.com/hook")

        assert safe is False
        assert "Unsupported scheme" in reason

    def test_a_url_without_a_hostname_is_rejected(self):
        safe, reason = is_safe_webhook_url("http:///hook")

        assert safe is False
        assert "No hostname" in reason

    def test_a_url_with_userinfo_is_rejected(self):
        safe, reason = is_safe_webhook_url("http://user:pass@example.com/hook")

        assert safe is False
        assert "userinfo" in reason

    @pytest.mark.parametrize("hostname", ["127.0.0.1", "localhost", "0.0.0.0"])
    def test_a_loopback_hostname_is_rejected(self, hostname):
        safe, reason = is_safe_webhook_url(f"http://{hostname}/hook")

        assert safe is False
        assert "Blocked loopback hostname" in reason

    def test_a_bracketed_loopback_hostname_is_rejected(self):
        safe, reason = is_safe_webhook_url("http://[::1]/hook")

        assert safe is False
        assert "Blocked loopback hostname" in reason

    def test_a_hostname_that_does_not_resolve_is_rejected(self):
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("no such host")):
            safe, reason = is_safe_webhook_url("https://nowhere.invalid/hook")

        assert safe is False
        assert "Cannot resolve hostname" in reason

    def test_a_hostname_without_addresses_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[]):
            safe, reason = is_safe_webhook_url("https://empty.invalid/hook")

        assert safe is False
        assert "No IP addresses found" in reason

    def test_an_address_that_is_not_an_ip_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("not-an-ip")]):
            safe, reason = is_safe_webhook_url("https://odd.invalid/hook")

        assert safe is False
        assert "Invalid IP address" in reason

    def test_a_loopback_address_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("127.0.0.1")]):
            safe, reason = is_safe_webhook_url("https://example.com/hook")

        assert safe is False
        assert "Blocked loopback IP" in reason

    def test_a_private_address_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("10.0.0.1")]):
            safe, reason = is_safe_webhook_url("https://example.com/hook")

        assert safe is False
        assert "Blocked private IP" in reason

    def test_a_link_local_address_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("169.254.1.1")]):
            safe, reason = is_safe_webhook_url("https://example.com/hook")

        assert safe is False
        assert "169.254.1.1" in reason

    def test_a_multicast_address_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("224.0.0.1")]):
            safe, reason = is_safe_webhook_url("https://example.com/hook")

        assert safe is False
        assert "Blocked multicast IP" in reason

    def test_an_ipv4_mapped_address_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("::ffff:10.0.0.1")]):
            safe, reason = is_safe_webhook_url("https://example.com/hook")

        assert safe is False
        assert "::ffff:10.0.0.1" in reason

    def test_the_cloud_metadata_endpoint_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("169.254.169.254")]):
            safe, reason = is_safe_webhook_url("https://example.com/hook")

        assert safe is False
        assert "169.254.169.254" in reason

    def test_the_google_metadata_hostname_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("169.254.169.254")]):
            safe, reason = is_safe_webhook_url(
                "http://metadata.google.internal/computeMetadata/v1/"
            )

        assert safe is False
        assert "metadata.google.internal" in reason or "169.254.169.254" in reason

    def test_an_address_that_is_not_globally_routable_is_rejected(self):
        with patch("socket.getaddrinfo", return_value=[_addr_info("100.64.0.1")]):
            safe, reason = is_safe_webhook_url("https://example.com/hook")

        assert safe is False
        assert "non-global" in reason
