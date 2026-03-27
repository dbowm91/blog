# Comprehensive Remediation Plan

Merged from plan2.md, plan3.md, plan4.md, and plan5.md. Items deduplicated, verified against codebase, and organized by priority. Unnecessary or overengineered items dropped with justification.

---

## P0 — Security Fixes

### S1. Remove `secret_key` fallback from config.toml
**Source:** plan5 item 1 | **Verified:** `app/config.py:26`
**Effort:** 5 min

`SECRET_KEY` falls back to `config.toml`, encouraging secrets in version control. Remove the fallback so it must come from the environment.

```python
# app/config.py:26 — change to:
SECRET_KEY = _env("SECRET_KEY", "")
```

The existing `RuntimeError` in `create_app()` already catches the empty-string case.

---

### S2. Session cookie security attributes
**Source:** plan2 item 1.1 | **Verified:** no `SESSION_COOKIE_*` config exists
**Effort:** 15 min

Add to `app/__init__.py` in `create_app()`:

```python
app.config["SESSION_COOKIE_SECURE"] = not app.debug
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
```

Prevents session cookies being sent over HTTP in production and mitigates cross-site request attacks.

---

### S3. Path traversal guard in `delete_media`
**Source:** plan5 item 2 | **Verified:** `app/routes/admin.py:532-540` — raw `filename` from URL joined directly
**Effort:** 15 min

`delete_media()` takes `filename` from the URL and joins it with the upload folder with no sanitization. Add `secure_filename()` and verify the resolved path stays within the upload directory:

```python
from werkzeug.utils import secure_filename

@admin.route("/media/delete/<filename>", methods=["POST"])
@login_required
def delete_media(filename):
    filename = secure_filename(filename)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    real_path = os.path.realpath(filepath)
    upload_dir = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    if not real_path.startswith(upload_dir + os.sep):
        abort(400)
    if not os.path.exists(real_path):
        abort(404)
    os.remove(real_path)
    flash(f"Deleted {filename}.", "success")
    return redirect(url_for("admin.media"))
```

---

### S4. Subscribe endpoint rate limiting
**Source:** plan2 item 1.4, plan3 item 2 | **Verified:** `app/routes/public.py:203-229` — no rate limiting
**Effort:** 15 min

`/subscribe` sends confirmation emails with no rate limit — vulnerable to email bombing. Add the existing `api_rate_limit()`:

```python
@public.route("/subscribe", methods=["POST"])
def subscribe():
    limited = api_rate_limit(max_requests=10, window=300)
    if limited:
        return limited
    # existing code...
```

---

### S5. Unsubscribe token enumeration prevention
**Source:** plan2 item 1.5 | **Verified:** `app/routes/public.py:241-251` — `first_or_404()` reveals token existence
**Effort:** 20 min

`first_or_404()` leaks whether a token exists via 404 vs 200. Return identical responses for invalid and expired tokens, add a timing-attack mitigation delay, and log enumeration attempts.

---

### S6. Search query length limit
**Source:** plan2 item 1.2 | **Verified:** `app/routes/public.py:136` — no max length on query
**Effort:** 5 min

Truncate the search query to prevent DoS via extremely long input:

```python
query = request.args.get("q", "", type=str)[:200].strip()
```

---

### S7. Share tracking: check post is published
**Source:** plan2 item 3.2 | **Verified:** `app/routes/public.py:183-200` — no published check
**Effort:** 5 min

Share events can be recorded for unpublished posts. Add check:

```python
if not post or not post.published:
    return jsonify({"error": "not found"}), 404
```

---

## P1 — Correctness & Robustness

### C1. Tag count cache invalidation
**Source:** plan2 item 2.4, plan3 item 3 | **Verified:** `app/routes/public.py:20-38` — cache never invalidated
**Effort:** 20 min

`_TAG_COUNTS_CACHE` is populated on first request but never invalidated when tags change. Add an `invalidate_tag_cache()` function and call it from tag create/rename/delete routes in `admin.py`.

---

### C2. Improve error message for missing `config.toml`
**Source:** plan5 item 7 | **Verified:** `app/config.py:17` — bare `FileNotFoundError`
**Effort:** 5 min

Wrap `load_config()` with a helpful message:

```python
except FileNotFoundError:
    raise RuntimeError(
        f"Configuration file not found: {config_path}\n"
        "Copy config.toml.example to config.toml and edit it."
    )
```

---

### C3. `ADMIN_PASSWORD` change detection
**Source:** plan5 item 8 | **Verified:** `app/__init__.py` — existing user password not compared on startup
**Effort:** 10 min

If the admin user exists but `ADMIN_PASSWORD` env var doesn't match, log a warning. Prevents silent misconfiguration after env var changes.

---

### C4. Check SMTP config before starting scheduler
**Source:** plan5 item 4 | **Verified:** `app/scheduler.py` — starts unconditionally
**Effort:** 5 min

Guard `init_scheduler()` so it skips startup if `SMTP_HOST` is not configured, avoiding silent failures and log noise on every scheduled run.

---

### C5. Empty slug fallback
**Source:** plan2 item 3.4 | **Verified:** `app/utils.py:18-27` — returns empty string for empty input
**Effort:** 5 min

Add fallback in `generate_slug()`:

```python
if not name:
    return "untitled"
```

---

### C6. Newsletter resend support
**Source:** plan3 item 4 | **Verified:** `newsletter_sent_at == None` filter means posts only send once
**Effort:** 30 min

Add admin route to reset `newsletter_sent_at` to `None`, allowing posts to be re-sent. Include a "Reset Newsletter" button on the dashboard for posts that have already been sent.

---

### C7. Newsletter batch sending
**Source:** plan2 item 2.3 | **Verified:** `app/email.py:64-90` — sends one-by-one sequentially over a single SMTP connection
**Effort:** 1 hour

Current implementation opens one SMTP connection and loops through subscribers sequentially, creating and sending a new `MIMEMultipart` message per subscriber. This is fine for small lists but becomes slow as the subscriber base grows.

Improvements:
- Reuse a single SMTP connection with `sendmail()` batching (already done — keep this)
- Add per-subscriber exception handling so one failure doesn't stop the batch (already done — keep this)
- Add a progress log line every N subscribers for operational visibility
- Consider SMTP connection reconnection on transient failures (wrap the loop with reconnect logic)

```python
# In app/email.py send_newsletter(), add progress logging:
for i, sub in enumerate(subscribers, 1):
    # ... existing message construction ...
    try:
        server.sendmail(FROM_ADDRESS, sub.email, msg.as_string())
        if i % 50 == 0:
            logger.info("Newsletter progress: %d/%d sent", i, len(subscribers))
    except Exception:
        logger.exception("Failed to send newsletter to %s", sub.email)
        # Reconnect on connection errors
        try:
            server.quit()
        except Exception:
            pass
        server = _connect_smtp()
        if not server:
            logger.error("SMTP reconnection failed; aborting newsletter")
            break
```

---

### C8. Load hardcoded constants from config
**Source:** plan2 item 2.2 | **Verified:** `app/routes/public.py:82` (`MAX_VIEWED_POSTS = 100`), `app/__init__.py:112` (`SESSION_LIFETIME_SECONDS = 24 * 60 * 60`)
**Effort:** 30 min

These constants are hardcoded in source but should be configurable:

1. Add to `config.toml`:
   ```toml
   [app]
   max_viewed_posts = 100
   session_lifetime_hours = 24
   ```

2. Add to `app/config.py`:
   ```python
   MAX_VIEWED_POSTS = int(_config["app"].get("max_viewed_posts", 100))
   SESSION_LIFETIME_HOURS = int(_config["app"].get("session_lifetime_hours", 24))
   ```

3. Update `app/routes/public.py:82` to import `MAX_VIEWED_POSTS` from config instead of defining locally.

4. Update `app/__init__.py:112` to compute `SESSION_LIFETIME_SECONDS = SESSION_LIFETIME_HOURS * 3600` from config.

---

## P2 — Test Infrastructure

### T1. Fix test fixture scope and cleanup
**Source:** plan5 item 5 | **Verified:** `tests/conftest.py` — manual temp file handling
**Effort:** 15 min

Use `tmp_path_factory` for session-scoped temp directories with automatic cleanup. Removes manual `os.close()` / `os.unlink()` calls and prevents temp file leaks on interrupted test runs.

---

### T2. Add missing test coverage
**Source:** plan5 item 6 | **Verified:** 46 tests exist but RSS, bulk ops, tags, media untested
**Effort:** 1 hour

Add tests for:
- **RSS:** feed content structure, draft exclusion
- **Bulk operations:** publish, delete, no-selection handling
- **Tag management:** create, rename, delete, invalid name rejection
- **Media library:** page loads

---

## P3 — Portability

### P1. Windows compatibility for `fcntl` import
**Source:** plan5 item 3 | **Verified:** `app/scheduler.py:1` — bare `import fcntl`
**Effort:** 10 min

Guard the import so the app doesn't crash on Windows:

```python
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
```

Skip file locking when `HAS_FCNTL` is `False`. Single-worker Windows dev servers are unaffected.

---

## P4 — Documentation (Low Effort)

### D1. Subscriber expiry documentation
**Source:** plan3 item 5 | **Verified:** `expires_at` field has no docstring
**Effort:** 5 min

Add a docstring to `Subscriber.expires_at` explaining the 365-day expiry is for unsubscribe link security, not subscription duration. Add a code comment in the unsubscribe route.

---

## Dropped Items (with rationale)

| Item | Source | Reason |
|------|--------|--------|
| SQLite-backed rate limiting | plan3 item 1 | Overengineering for a small blog. In-memory is fine; document the limitation. |
| Rate limiting shared across workers | plan2 item 1.3 | Same as above. Not needed for single-worker SQLite deployment. |
| Media library pagination | plan2 item 2.1 | Small blog upload directories don't need pagination. |
| Config validation timing | plan2 item 3.3, plan3 item 6 | Current behavior is correct per plan3's own analysis — error at `create_app()` time is appropriate. |
| Favicon 301→302 redirect | plan3 item 8 | 301 caching is actually desirable for favicon. |
| Analytics query optimization | plan3 item 9 | Current `replace()` approach works fine with timezone-naive datetimes used consistently. |
| Image type detection (BMP) | plan3 item 10 | 4 formats (PNG, JPEG, GIF, WebP) sufficient for a blog. |
| Health check endpoint | plan2 item 4.1 | Nice-to-have, not actionable priority. |
| Admin activity audit log | plan2 item 4.2 | Significant scope addition; defer unless needed. |
| Request ID for logging | plan2 item 4.3 | Low value for single-worker blog. |
| Database backup utility | plan3 item 7 | SQLite can be backed up with `cp` or `sqlite3 .backup`. No need for a custom script. |

---

## Implementation Order

| # | Task | Priority | Effort | Cumulative |
|---|------|----------|--------|------------|
| 1 | S1 — Remove secret_key fallback | P0 | 5 min | 5 min |
| 2 | S6 — Search query length limit | P0 | 5 min | 10 min |
| 3 | S7 — Share tracking published check | P0 | 5 min | 15 min |
| 4 | S4 — Subscribe rate limiting | P0 | 15 min | 30 min |
| 5 | S2 — Session cookie security | P0 | 15 min | 45 min |
| 6 | S3 — Path traversal in delete_media | P0 | 15 min | 60 min |
| 7 | S5 — Unsubscribe token enumeration | P0 | 20 min | 80 min |
| 8 | C2 — config.toml error message | P1 | 5 min | 85 min |
| 9 | C4 — SMTP guard in scheduler | P1 | 5 min | 90 min |
| 10 | C5 — Empty slug fallback | P1 | 5 min | 95 min |
| 11 | C3 — ADMIN_PASSWORD change detection | P1 | 10 min | 105 min |
| 12 | C1 — Tag cache invalidation | P1 | 20 min | 125 min |
| 13 | C6 — Newsletter resend support | P1 | 30 min | 155 min |
| 14 | C7 — Newsletter batch sending | P1 | 1 hour | 215 min |
| 15 | C8 — Load hardcoded constants from config | P1 | 30 min | 245 min |
| 16 | D1 — Subscriber expiry docs | P4 | 5 min | 250 min |
| 17 | P1 — Windows fcntl guard | P3 | 10 min | 260 min |
| 18 | T1 — Fix test fixtures | P2 | 15 min | 275 min |
| 19 | T2 — Add missing tests | P2 | 1 hour | 335 min |

**Total estimated effort: ~5.5 hours**

---

## Verification

After implementation, run:

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

All existing and new tests must pass.
