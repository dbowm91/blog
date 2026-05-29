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


@pytest.fixture(scope="function")
def clean_analytics_cache():
    """Clear analytics cache before each test to prevent cross-test pollution."""
    from app.routes.admin import _analytics_cache

    _analytics_cache.clear()
    yield
    _analytics_cache.clear()
