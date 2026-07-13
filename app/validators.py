"""Input validation utilities for API endpoints."""

import re
from functools import wraps
from typing import Any, Callable, Optional, List, Tuple, Union

from flask import request, jsonify


def validate_string(value: Any, max_length: int, field_name: str) -> tuple:
    """Returns (value, error_message)."""
    if not isinstance(value, str):
        return "", f"{field_name} must be a string"
    if len(value) > max_length:
        return "", f"{field_name} exceeds {max_length} chars"
    return value, None


def validate_email(value: str, max_length: int = 256) -> tuple:
    """Returns (value, error_message)."""
    if not isinstance(value, str):
        return "", "email must be a string"
    if len(value) > max_length:
        return "", f"email exceeds {max_length} chars"
    from app.utils import is_valid_email

    if not is_valid_email(value):
        return "", "Invalid email format"
    return value, None


def validate_boolean(value: Any, field_name: str) -> tuple:
    """Returns (value, error_message)."""
    if isinstance(value, bool):
        return value, None
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true", None
    return False, f"{field_name} must be a boolean"


def validate_integer(
    value: Any,
    field_name: str,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> Tuple[Union[int, None], Optional[str]]:
    """Validate that a value is an integer within optional bounds.

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        min_value: Optional minimum allowed value (inclusive)
        max_value: Optional maximum allowed value (inclusive)

    Returns:
        Tuple of (validated_value, error_message)
        - If valid: (int_value, None)
        - If invalid: (None, error_message)
    """
    if not isinstance(value, int) or isinstance(value, bool):
        # bool is a subclass of int in Python, so we need to exclude it
        try:
            # Try to convert string to int
            if isinstance(value, str):
                value = int(value)
            else:
                return None, f"{field_name} must be an integer"
        except (ValueError, TypeError):
            return None, f"{field_name} must be an integer"

    if min_value is not None and value < min_value:
        return None, f"{field_name} must be at least {min_value}"

    if max_value is not None and value > max_value:
        return None, f"{field_name} must be at most {max_value}"

    return value, None


def validate_list(
    value: Any,
    field_name: str,
    max_length: Optional[int] = None,
    item_type: Optional[type] = None,
) -> Tuple[Union[List[Any], None], Optional[str]]:
    """Validate that a value is a list with optional constraints.

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        max_length: Optional maximum length of the list
        item_type: Optional type that all items must be

    Returns:
        Tuple of (validated_value, error_message)
        - If valid: (list_value, None)
        - If invalid: (None, error_message)
    """
    if not isinstance(value, list):
        return None, f"{field_name} must be a list"

    if max_length is not None and len(value) > max_length:
        return None, f"{field_name} exceeds maximum length of {max_length}"

    if item_type is not None:
        for i, item in enumerate(value):
            if not isinstance(item, item_type):
                return None, f"{field_name}[{i}] must be of type {item_type.__name__}"

    return value, None


# Regex for valid tag: alphanumeric characters, hyphens, underscores
# Max 50 characters per tag
TAG_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")


def validate_tags(
    tags: Any,
    field_name: str = "tags",
    max_tags: int = 10,
) -> Tuple[Union[List[str], None], Optional[str]]:
    """Validate a list of tags with regex-based validation.

    Rules:
    - Must be a list
    - Maximum of max_tags (default 10) tags
    - Each tag must be 1-50 characters
    - Each tag must match regex: ^[a-zA-Z0-9_-]{1,50}$

    Args:
        tags: The tags value to validate
        field_name: Name of the field (for error messages)
        max_tags: Maximum number of allowed tags

    Returns:
        Tuple of (validated_value, error_message)
        - If valid: (list_of_tags, None)
        - If invalid: (None, error_message)
    """
    # First validate it's a list
    validated_list, error = validate_list(tags, field_name, max_length=max_tags)
    if error:
        return None, error

    validated_tags = []
    for i, tag in enumerate(tags):
        # Ensure tag is a string
        if not isinstance(tag, str):
            return None, f"{field_name}[{i}] must be a string"

        # Check length
        if len(tag) < 1:
            return None, f"{field_name}[{i}] must not be empty"

        if len(tag) > 50:
            return None, f"{field_name}[{i}] exceeds 50 characters"

        # Check regex (alphanumeric, hyphens, underscores only)
        if not TAG_REGEX.match(tag):
            return None, (
                f"{field_name}[{i}] contains invalid characters. "
                "Only letters, digits, hyphens, and underscores are allowed."
            )

        validated_tags.append(tag)

    return validated_tags, None


def require_json_content_type(f: Callable) -> Callable:
    """Decorator to require JSON content type on requests.

    Returns a 415 error if the Content-Type is not application/json.

    Usage:
        @app.route('/api/endpoint', methods=['POST'])
        @require_json_content_type
        def my_endpoint():
            ...
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415
        return f(*args, **kwargs)

    return decorated_function
