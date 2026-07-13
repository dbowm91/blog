---
name: e2e_testing
description: "End-to-end browser testing with Playwright. Triggers: E2E tests, playwright, browser tests, pytest-playwright, UI testing."
metadata:
  requires: "playwright>=1.58.0, pytest-playwright>=0.7.0"
  homepage: "https://playwright.dev/python/"
---

## Overview

End-to-end browser testing for the blog CMS using Playwright with pytest integration.

## Setup

### Installation

```bash
# Install in virtual environment
pip install playwright pytest-playwright

# Install browser binaries (do this once)
playwright install chromium

# For headless mode (CI/testing)
playwright install --only-shell chromium
```

### Virtual Environment Setup

The project uses a virtual environment at `.venv/`:

```bash
# Activate venv (if needed)
source .venv/bin/activate

# Install all dependencies including E2E
pip install -r requirements.txt

# Verify installation
.venv/bin/playwright --version
```

## Running E2E Tests

Use the project's `.venv` Python to avoid fixture errors:
```bash
# Run all E2E tests
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/e2e/ -v

# Run with browser visible (headed mode)
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/e2e/ -v --headed

# Run specific test class
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/e2e/test_e2e.py::TestAdminLogin -v

# Run with slow motion (helpful for debugging)
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/e2e/ -v --slowmo 1000
```

## Test Structure

E2E tests are in `tests/e2e/`:

```
tests/e2e/
├── conftest.py          # Fixtures: app_server, browser config
└── test_e2e.py        # Test classes
```

### Key Fixtures (from conftest.py)

- `app_server` - Starts Flask dev server in thread, creates test DB
- `page` - Playwright page object (from pytest-playwright)
- `browser` - Playwright browser instance
- `context` - Browser context for isolation

### Test Classes

```python
class TestAdminLogin:
    """Test admin login and logout flows."""
    def test_login_page_loads(self, page, app_server):
        """Login page should display without errors."""
    
    def test_login_success(self, page, app_server):
        """Admin should be able to log in with valid credentials."""
    
    def test_login_failure(self, page, app_server):
        """Invalid credentials should show error message (toast)."""

class TestPostCreation:
    """Test post creation and publishing flows."""

class TestNewsletterSubscription:
    """Test newsletter subscription flows."""

class TestMobileResponsiveness:
    """Test mobile responsiveness."""
```

## Important Notes

### Toast Notifications vs Flash Messages

The blog CMS uses **toast notifications** for messages (not Flask flash messages):

```python
# WRONG - looks for flash messages
page.wait_for_selector(".flash-error")  # This won't work!

# CORRECT - looks for toast notifications
page.wait_for_selector(".toast-message")
toast = page.text_content(".toast-message")
assert "invalid" in toast.lower()
```

### Page Object Model

For complex tests, consider using Page Object Model:

```python
class LoginPage:
    def __init__(self, page):
        self.page = page
    
    def login(self, username, password):
        self.page.fill('input[name="username"]', username)
        self.page.fill('input[name="password"]', password)
        self.page.click('button[type="submit"]')
```

## Debugging Tips

```python
# Take screenshot on failure
page.screenshot(path="screenshot.png")

# Get page content
print(page.content())

# Wait for network idle (all requests complete)
page.wait_for_load_state("networkidle")

# Check for specific text
assert "Welcome" in page.content()

# Slow down execution
page.set_default_timeout(10000)  # 10 seconds
```

## CI/CD Integration

For CI environments:

```yaml
# Example GitHub Actions step
- name: Install Playwright
  run: |
    pip install playwright pytest-playwright
    playwright install chromium
    
- name: Run E2E tests
  run: |
    ADMIN_PASSWORD=test SECRET_KEY=test python -m pytest tests/e2e/ -v
  env:
    ADMIN_PASSWORD: test
    SECRET_KEY: test-secret-key-that-is-at-least-32-chars-long
```

## Common Issues

### "fixture 'page' not found"

Make sure `pytest-playwright` is installed in the same environment as pytest:

```bash
pip list | grep playwright
# Should show: playwright and pytest-playwright
```

### Browser binary not found

```bash
# Install browser binaries
playwright install chromium

# Check installed browsers
ls ~/.cache/ms-playwright/
```

### Timeout errors

Increase timeout for slower systems:

```python
# In test file
page.wait_for_selector(".toast-message", timeout=10000)  # 10 seconds
```

## Current Status

- **10 E2E tests** currently passing
- Covers: admin login/logout, post creation, newsletter subscription, mobile responsiveness
- All tests run in headless Chromium browser
- Test database is created fresh for each session
