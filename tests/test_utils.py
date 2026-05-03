import pytest
from app.utils import (
    utc_now,
    is_valid_email,
    generate_slug,
    xml_escape,
    sanitize_css,
    is_safe_webhook_url,
    safe_delete_file,
    ErrorLogContext,
    log_storage_error,
    log_security_event,
    log_scheduler_error,
    handle_error,
)
from unittest.mock import patch, MagicMock
import os
import tempfile


def test_utc_now():
    """Test utc_now returns timezone-aware UTC datetime."""
    result = utc_now()
    assert result.tzinfo is not None
    assert str(result.tzinfo) == "UTC"


def test_is_valid_email_valid():
    """Test valid email addresses."""
    assert is_valid_email("test@example.com") is True
    assert is_valid_email("user.name+tag@example.co.uk") is True


def test_is_valid_email_invalid():
    """Test invalid email addresses."""
    assert is_valid_email("") is False
    assert is_valid_email("invalid") is False
    assert is_valid_email("user@") is False
    assert is_valid_email("@example.com") is False


def test_generate_slug_normal():
    """Test slug generation for normal text."""
    assert generate_slug("Hello World") == "hello-world"
    assert generate_slug("Python & Flask") == "python-flask"


def test_generate_slug_unicode():
    """Test slug generation with unicode characters."""
    assert generate_slug("Café au Lait") == "cafe-au-lait"
    assert generate_slug("Ünïcödé") == "unicode"


def test_generate_slug_empty():
    """Test slug generation for empty/whitespace."""
    assert generate_slug("") == "untitled"
    assert generate_slug("   ") == "untitled"


def test_xml_escape():
    """Test XML escaping."""
    assert xml_escape("<test>") == "&lt;test&gt;"
    assert xml_escape("a&b") == "a&amp;b"
    assert xml_escape('"hello"') == "&quot;hello&quot;"
    assert xml_escape("'world'") == "&#x27;world&#x27;"


def test_sanitize_css_empty():
    """Test CSS sanitization with empty input."""
    assert sanitize_css("") == ""


def test_sanitize_css_removes_url():
    """Test CSS sanitization removes url()."""
    css = "body { background: url('http://evil.com/xss.jpg'); }"
    assert "url(" not in sanitize_css(css)


def test_sanitize_css_removes_expression():
    """Test CSS sanitization removes expression()."""
    css = "div { expression(alert('xss')); }"
    assert "expression(" not in sanitize_css(css)


def test_sanitize_css_removes_content():
    """Test CSS sanitization removes content property."""
    css = "div { content: 'hidden text'; }"
    sanitized = sanitize_css(css)
    assert "content:" in sanitized.lower()
    assert "hidden text" not in sanitized


def test_is_safe_webhook_url_valid():
    """Test safe webhook URLs."""
    import socket
    from unittest.mock import patch
    # Mock getaddrinfo to return a public IP
    with patch("socket.getaddrinfo") as mock_getaddrinfo:
        # Return public IP 8.8.8.8
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 80))
        ]
        is_safe, reason = is_safe_webhook_url("http://example.com/webhook")
        assert is_safe is True
        is_safe, reason = is_safe_webhook_url("https://api.example.com/hook")
        assert is_safe is True


def test_is_safe_webhook_url_invalid_scheme():
    """Test webhook URL with invalid scheme."""
    is_safe, reason = is_safe_webhook_url("ftp://example.com")
    assert is_safe is False
    assert "scheme" in reason.lower()


def test_is_safe_webhook_url_loopback():
    """Test webhook URL with loopback address."""
    is_safe, reason = is_safe_webhook_url("http://127.0.0.1/admin")
    assert is_safe is False
    assert "loopback" in reason.lower()


def test_is_safe_webhook_url_private_ip():
    """Test webhook URL with private IP."""
    is_safe, reason = is_safe_webhook_url("http://192.168.1.1/webhook")
    assert is_safe is False
    assert "private" in reason.lower()


def test_is_safe_webhook_url_aws_metadata():
    """Test webhook URL with AWS metadata endpoint."""
    is_safe, reason = is_safe_webhook_url("http://169.254.169.254/latest")
    assert is_safe is False
    # Code blocks it as private IP, which is correct
    assert "private" in reason.lower()


def test_safe_delete_file_success():
    """Test safe_delete_file deletes existing file."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test")
        tmp_path = f.name
    assert os.path.exists(tmp_path)
    result = safe_delete_file(tmp_path)
    assert result is True
    assert not os.path.exists(tmp_path)


def test_safe_delete_file_not_found():
    """Test safe_delete_file handles missing file."""
    result = safe_delete_file("/nonexistent/file.txt")
    assert result is True


def test_error_log_context_constants():
    """Test ErrorLogContext constants."""
    assert ErrorLogContext.STORAGE == "storage"
    assert ErrorLogContext.SECURITY == "security"
    assert ErrorLogContext.SCHEDULER == "scheduler"
    assert ErrorLogContext.DATABASE == "database"
    assert ErrorLogContext.GENERAL == "general"


def test_log_storage_error():
    """Test log_storage_error logs correctly."""
    with patch("app.utils.logger") as mock_logger:
        log_storage_error("upload", "test detail")
        mock_logger.error.assert_called_once()
        log_storage_error("delete", "test detail", Exception("test"))
        assert mock_logger.error.call_count == 2


def test_log_security_event():
    """Test log_security_event logs correctly."""
    with patch("app.utils.logger") as mock_logger:
        log_security_event("login_failed", user_id=1, ip="127.0.0.1")
        mock_logger.warning.assert_called_once()


def test_handle_error():
    """Test handle_error returns default value."""
    result = handle_error("storage", "test_op", "test detail", default="fallback")
    assert result == "fallback"
