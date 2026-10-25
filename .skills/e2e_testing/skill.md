---
name: e2e_testing
description: "End-to-end browser testing for DevLog with Playwright and pytest. Use when writing, running or debugging browser tests: E2E tests, playwright, pytest-playwright, UI testing, the tests/e2e/ suite, the app_server fixture, or the CI e2e job."
metadata:
  requires: "playwright>=1.58.0, pytest-playwright>=0.7.0"
  homepage: "https://playwright.dev/python/"
---

# End-to-End Testing Skill

Browser-level testing for DevLog with Playwright driven by pytest.

## Setup

```bash
pip install playwright pytest-playwright
playwright install chromium          # once
playwright install --only-shell chromium   # headless shell for CI
```

## Running

```bash
# The whole suite
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 \
  python3 -m pytest tests/e2e/ -v

# Headed, for watching a failure
... python3 -m pytest tests/e2e/ -v --headed

# One test
... python3 -m pytest tests/e2e/test_e2e.py::TestAdminLogin -v

# Slow motion, for debugging
... python3 -m pytest tests/e2e/ -v --slowmo 1000
```

`E2E_BASE_URL` sets the target URL (default `http://127.0.0.1:5010`). CI sets
it to `http://localhost:5000` and runs through `docker-compose.ci.yml`, which
publishes the port directly and bypasses nginx.

## Suite Layout

`tests/e2e/` — 8 test modules, 75 tests:

| File | Tests | Covers |
|---|---|---|
| `test_e2e.py` | 10 | Admin login/logout, post creation, newsletter subscription, mobile responsiveness |
| `test_accessibility.py` | 15 | Accessibility checks on rendered pages |
| `test_admin_ui_fixes.py` | 14 | Admin UI regressions |
| `test_color_scheme.py` | 17 | The three-state colour scheme |
| `test_visual_regression.py` | 11 | Screenshot comparison |
| `test_code_line_numbers.py` | 3 | Code-block line numbering |
| `test_frontend_interactions.py` | 3 | Public interaction regressions |
| `test_image_visibility.py` | 2 | Lazy-image restoration |

## Fixtures

From `tests/e2e/conftest.py`:

- **`app`** — session-scoped. Builds its own Flask app against a separate
  `blog_e2e` database, so `pytest tests/e2e/` runs standalone.
- **`app_server`** — session-scoped. Starts the server in a thread and polls
  for readiness before yielding the URL.
- **`app_url`** — session-scoped. `E2E_BASE_URL`, default
  `http://127.0.0.1:5010`.
- **`browser_type_launch_args`** — overridden session-scoped to set headless
  mode and the viewport.

The `page`, `browser` and `context` fixtures come from `pytest-playwright`.

## Rules

**Browser tests belong under `tests/e2e/`, on the e2e app's own database.** A
live server thread on the session-scoped application shares its database with
the migration round-trip tests and corrupts their DDL. Do not put browser
tests in the unit suite.

**Do not run the Playwright suite concurrently with the full pytest suite.**
They collide on the same development database.

**Assert the user-visible message, not a specific node.** The server renders
flashes as `.flash-container > .flash > .flash-message`; `shared/toast.js`
converts them into toasts and removes the container on load. The final DOM may
contain either representation.

```python
# wrong — the toast may not exist yet
page.wait_for_selector(".flash-error")

# right — wait for the toast
page.wait_for_selector(".toast-message")
assert "invalid" in page.text_content(".toast-message").lower()
```

**Assert on computed style or geometry, not on CSS source.** A rule that
"looks right" in the stylesheet may be overridden by a later sheet or a media
query. Measure `getComputedStyle` in the browser.

## Debugging

```python
page.screenshot(path="screenshot.png", full_page=True)
print(page.content())
page.wait_for_load_state("networkidle")
page.set_default_timeout(10000)
```

### "fixture 'page' not found"

`pytest-playwright` is not installed in the same environment as pytest.

```bash
pip list | grep playwright
```

### "Browser binary not found"

```bash
playwright install chromium
ls ~/.cache/ms-playwright/
```

### Timeouts

Raise the timeout for slow systems, but first check whether the page is
actually rendering — a selector that never appears is usually a broken
feature, not a slow one.

## Related

- `architecture/testing/test-suite.md` — the whole test suite layout
- `app/static/AGENTS.override.md` — the cross-layer contracts an E2E test
  depends on
- `.skills/release_validation/skill.md` — running the full release gate
