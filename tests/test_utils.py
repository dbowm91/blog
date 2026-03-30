import pytest
from app.utils import is_valid_email, xml_escape, generate_slug


class TestEmailValidation:
    def test_valid_email(self):
        assert is_valid_email("user@example.com") is True

    def test_valid_email_with_dots(self):
        assert is_valid_email("first.last@example.co.uk") is True

    def test_invalid_email_no_at(self):
        assert is_valid_email("userexample.com") is False

    def test_invalid_email_no_domain(self):
        assert is_valid_email("user@") is False

    def test_invalid_email_empty(self):
        assert is_valid_email("") is False

    def test_invalid_email_spaces(self):
        assert is_valid_email("user @example.com") is False


class TestXmlEscape:
    def test_ampersand(self):
        assert xml_escape("a&b") == "a&amp;b"

    def test_less_than(self):
        assert xml_escape("a<b") == "a&lt;b"

    def test_greater_than(self):
        assert xml_escape("a>b") == "a&gt;b"

    def test_double_quote(self):
        assert xml_escape('a"b') == "a&quot;b"

    def test_single_quote(self):
        assert xml_escape("a'b") == "a&apos;b"

    def test_empty_string(self):
        assert xml_escape("") == ""

    def test_none(self):
        assert xml_escape(None) == ""

    def test_combined(self):
        assert xml_escape('<a href="x&y">') == '&lt;a href=&quot;x&amp;y&quot;&gt;'


class TestSlugGeneration:
    def test_simple(self):
        assert generate_slug("Hello World") == "hello-world"

    def test_special_chars(self):
        assert generate_slug("Hello! World?") == "hello-world"

    def test_unicode(self):
        assert generate_slug("Café Résumé") == "cafe-resume"

    def test_empty_string(self):
        assert generate_slug("") == "untitled"

    def test_none(self):
        assert generate_slug(None) == "untitled"

    def test_whitespace_only(self):
        assert generate_slug("   ") == "untitled"

    def test_multiple_spaces(self):
        assert generate_slug("hello   world") == "hello-world"

    def test_leading_trailing_dashes(self):
        assert generate_slug("--hello--") == "hello"

    def test_underscores(self):
        assert generate_slug("hello_world") == "hello-world"
