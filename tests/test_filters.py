import pytest
from flask import Flask
from app.filters import register_filters


def test_markdown_safe_filter():
    """Test markdown_safe_filter."""
    app = Flask(__name__)
    register_filters(app)
    with app.test_client() as client:
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
        # Mock post with no image
        post = type("Post", (), {"image": None, "id": 1})()
        result = app.jinja_env.filters["post_image_srcset"](post)
        assert result is None
