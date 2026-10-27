from flask import Flask
from app.filters import register_filters
from app.storage import LocalStorageBackend
from unittest.mock import patch
import tempfile


def test_markdown_safe_filter():
    """Test markdown_safe_filter."""
    app = Flask(__name__)
    register_filters(app)
    with app.test_client():
        # Test with markdown text
        with app.app_context():
            result = app.jinja_env.filters["markdown_safe"]("# Hello\n\nThis is **bold**.")
            assert "<h1" in result
            assert "<strong>" in result


def test_reading_time_filter():
    """Test reading_time_filter."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        # Test with 200 words (should be 1 min)
        text = "word " * 200
        result = app.jinja_env.filters["reading_time"](text)
        assert "1 min" in result

        # Test empty text
        result = app.jinja_env.filters["reading_time"]("")
        assert "1 min" in result


def test_sanitize_css_filter():
    """Test sanitize_css_filter."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        # Test with dangerous CSS
        dangerous = "body { url('http://evil.com/xss.jpg'); }"
        result = app.jinja_env.filters["sanitize_css"](dangerous)
        assert "url(" not in result

        # Test safe CSS
        safe = "body { color: red; }"
        result = app.jinja_env.filters["sanitize_css"](safe)
        assert "color:" in result

        # Test None
        result = app.jinja_env.filters["sanitize_css"](None)
        assert result == ""


def test_post_image_url_filter_no_image():
    """Test post_image_url with no image."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        # Mock post with no image
        post = type("Post", (), {"image": None, "id": 1})()
        result = app.jinja_env.filters["post_image_url"](post)
        assert result is None


def test_post_image_srcset_filter_no_image():
    """Test post_image_srcset with no image."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        post = type("Post", (), {"image": None, "id": 1})()
        result = app.jinja_env.filters["post_image_srcset"](post)
        assert result is None


def test_post_image_url_filter_with_image():
    """Test post_image_url with image that exists."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorageBackend(tmpdir)
            storage.save("test.jpg", b"fake image data")
            with patch("app.storage.get_storage", return_value=storage):
                post = type("Post", (), {"image": "test.jpg", "id": 1})()
                result = app.jinja_env.filters["post_image_url"](post)
                assert result == storage.url("test.jpg")


def test_post_image_url_filter_with_missing_image():
    """Test post_image_url with image that doesn't exist."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorageBackend(tmpdir)
            with patch("app.storage.get_storage", return_value=storage):
                post = type("Post", (), {"image": "nonexistent.jpg", "id": 1})()
                result = app.jinja_env.filters["post_image_url"](post)
                assert result is None


def test_markdown_safe_filter_code_blocks():
    """Test markdown_safe_filter with code blocks."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        md_text = """# Code Example

```python
def hello():
    print("world")
```

Regular text.
"""
        result = app.jinja_env.filters["markdown_safe"](md_text)
        assert "<h1" in result
        assert "<pre" in result and "<code" in result
        assert 'class="language-python"' in result
        assert '<span class="code-line">' in result


def test_markdown_safe_filter_tables():
    """Test markdown_safe_filter with tables."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        md_text = """# Table Example

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
"""
        result = app.jinja_env.filters["markdown_safe"](md_text)
        assert "<table" in result


def test_markdown_safe_filter_footers():
    """Test markdown_safe_filter with footnotes."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        md_text = """# Footnotes Example

Some text with a footnote[^1].

[^1]: The footnote content.
"""
        result = app.jinja_env.filters["markdown_safe"](md_text)
        assert "<h1" in result


def test_reading_time_empty_text():
    """Test reading_time_filter with empty text."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        result = app.jinja_env.filters["reading_time"]("")
        assert "1 min" in result


def test_reading_time_very_long_text():
    """Test reading_time_filter with very long text."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        long_text = "word " * 1000
        result = app.jinja_env.filters["reading_time"](long_text)
        mins = int(result.split()[0])
        assert mins >= 1


def test_markdown_safe_filter_preserves_safe_html():
    """Test markdown_safe_filter preserves safe HTML tags."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        html_text = "<p>Paragraph with <strong>bold</strong> text.</p>"
        result = app.jinja_env.filters["markdown_safe"](html_text)
        assert "<strong>" in result or "<b>" in result


def test_markdown_safe_filter_removes_script_tags():
    """Test markdown_safe_filter removes dangerous script tags."""
    app = Flask(__name__)
    register_filters(app)
    with app.app_context():
        dangerous_text = "<p>Safe</p><script>alert('xss')</script>"
        result = app.jinja_env.filters["markdown_safe"](dangerous_text)
        assert "<script>" not in result
        assert "<p>Safe</p>" in result
