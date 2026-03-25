import os
import tomllib
from typing import Any


def _env(key: str, default: Any = None) -> Any:
    """Get environment variable with optional default."""
    val = os.environ.get(key)
    if val is not None:
        return val
    return default


def load_config() -> dict[str, Any]:
    """Load configuration from TOML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")
    with open(config_path, "rb") as f:
        return tomllib.load(f)


_config = load_config()

APP_TITLE = _config["app"]["title"]
APP_DESCRIPTION = _config["app"]["description"]
POSTS_PER_PAGE = _config["app"]["posts_per_page"]
SECRET_KEY = _env("SECRET_KEY", _config["app"].get("secret_key", ""))
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is required. Set it via the SECRET_KEY environment variable."
    )

ADMIN_USERNAME = _env("ADMIN_USERNAME", _config["admin"]["username"])
ADMIN_PASSWORD = _env("ADMIN_PASSWORD")

SERVER_HOST = _config["server"]["host"]
SERVER_PORT = int(_config["server"]["port"])
DEBUG = _config["server"].get("debug", False)

AUTHOR_NAME = _config["author"]["name"]
AUTHOR_ROLE = _config["author"]["role"]
AUTHOR_AVATAR = _config["author"].get("avatar", "")

BASE_URL = _config["site"]["base_url"].rstrip("/")
RELATED_POSTS_COUNT = _config["site"]["related_posts_count"]

SMTP_HOST = _config["email"]["smtp_host"]
SMTP_PORT = int(_config["email"]["smtp_port"])
SMTP_USER = _env("SMTP_USER", _config["email"].get("smtp_user", ""))
SMTP_PASSWORD = _env("SMTP_PASSWORD", _config["email"].get("smtp_password", ""))
FROM_ADDRESS = _config["email"]["from_address"]

NEWSLETTER_SEND_TIME = _config["newsletter"]["send_time"]
