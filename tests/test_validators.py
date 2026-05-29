from app.validators import (
    validate_string,
    validate_email,
    validate_boolean,
    validate_integer,
    validate_list,
    validate_tags,
    require_json_content_type,
)
from flask import Flask, jsonify


def test_validate_string_valid():
    """Test validate_string with valid input."""
    value, error = validate_string("hello", 10, "test")
    assert value == "hello"
    assert error is None


def test_validate_string_too_long():
    """Test validate_string with too long input."""
    value, error = validate_string("hello world", 5, "test")
    assert value == ""
    assert "exceeds" in error


def test_validate_string_not_string():
    """Test validate_string with non-string input."""
    value, error = validate_string(123, 10, "test")
    assert value == ""
    assert "must be a string" in error


def test_validate_email_valid():
    """Test validate_email with valid email."""
    value, error = validate_email("test@example.com", 256)
    assert value == "test@example.com"
    assert error is None


def test_validate_email_invalid():
    """Test validate_email with invalid email."""
    value, error = validate_email("invalid-email", 256)
    assert value == ""
    assert "Invalid email" in error


def test_validate_boolean_true():
    """Test validate_boolean with True."""
    value, error = validate_boolean(True, "test")
    assert value is True
    assert error is None


def test_validate_boolean_false():
    """Test validate_boolean with False."""
    value, error = validate_boolean(False, "test")
    assert value is False
    assert error is None


def test_validate_boolean_string_true():
    """Test validate_boolean with 'true' string."""
    value, error = validate_boolean("true", "test")
    assert value is True
    assert error is None


def test_validate_boolean_invalid():
    """Test validate_boolean with invalid input."""
    value, error = validate_boolean("yes", "test")
    assert value is False
    assert "must be a boolean" in error


def test_validate_integer_valid():
    """Test validate_integer with valid integer."""
    value, error = validate_integer(10, "test", 1, 100)
    assert value == 10
    assert error is None


def test_validate_integer_too_small():
    """Test validate_integer with value below min."""
    value, error = validate_integer(5, "test", 10, 100)
    assert value is None
    assert "at least" in error


def test_validate_integer_too_large():
    """Test validate_integer with value above max."""
    value, error = validate_integer(150, "test", 10, 100)
    assert value is None
    assert "at most" in error


def test_validate_integer_invalid():
    """Test validate_integer with non-integer input."""
    value, error = validate_integer("abc", "test")
    assert value is None
    assert "must be an integer" in error


def test_validate_list_valid():
    """Test validate_list with valid list."""
    value, error = validate_list([1, 2, 3], "test", 5)
    assert value == [1, 2, 3]
    assert error is None


def test_validate_list_too_long():
    """Test validate_list with list exceeding max length."""
    value, error = validate_list([1, 2, 3, 4, 5, 6], "test", 5)
    assert value is None
    assert "exceeds maximum" in error


def test_validate_list_not_list():
    """Test validate_list with non-list input."""
    value, error = validate_list("not a list", "test")
    assert value is None
    assert "must be a list" in error


def test_validate_tags_valid():
    """Test validate_tags with valid tags."""
    tags, error = validate_tags(["python", "flask"], "tags", 5)
    assert tags == ["python", "flask"]
    assert error is None


def test_validate_tags_too_many():
    """Test validate_tags with too many tags."""
    tags, error = validate_tags(["t1", "t2", "t3", "t4", "t5", "t6"], "tags", 5)
    assert tags is None
    assert "exceeds maximum" in error


def test_validate_tags_invalid_chars():
    """Test validate_tags with invalid characters."""
    tags, error = validate_tags(["python!", "flask"], "tags")
    assert tags is None
    assert "invalid characters" in error


def test_require_json_content_type():
    """Test require_json_content_type decorator."""
    app = Flask(__name__)

    @app.route("/test", methods=["POST"])
    @require_json_content_type
    def test_route():
        return jsonify({"ok": True})

    with app.test_client() as client:
        # Test with JSON content type
        response = client.post("/test", json={"data": "test"})
        assert response.status_code == 200

        # Test with non-JSON content type
        response = client.post("/test", data="not json")
        assert response.status_code == 415
        assert b"Content-Type must be application/json" in response.data
