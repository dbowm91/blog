def validate_string(value, max_length: int, field_name: str) -> tuple:
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


def validate_boolean(value, field_name: str) -> tuple:
    """Returns (value, error_message)."""
    if isinstance(value, bool):
        return value, None
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true", None
    return False, f"{field_name} must be a boolean"
