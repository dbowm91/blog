"""Shared test fixtures."""
import pytest
from app.page_view_buffer import shutdown_page_view_buffer
import app.config as _app_config

@pytest.fixture(autouse=True)
def ensure_buffer_disabled():
    """Ensure page view buffer is disabled during tests."""
    _app_config.PAGE_VIEW_BUFFER_SIZE = 0
    shutdown_page_view_buffer()
    yield
    shutdown_page_view_buffer()