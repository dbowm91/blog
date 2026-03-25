# Codebase Review: Action Plan

Merged from plan.md, plan2.md, plan3.md — inaccurate claims removed, already-fixed items verified.

## Status of Previous Items

All original Priority 1 and Priority 2 items have been **fixed** in the current code:

| Item | Status | Evidence |
|------|--------|----------|
| 1.1 Slug regeneration | **Fixed** | `admin.py:192` — conditional on `title != post.title` |
| 1.2 Newsletter dedup | **Fixed** | `scheduler.py:24` — uses `newsletter_sent_at == None` |
| 1.3 Timezone comparison | **Not a bug** | `utc_now()` returns naive, `expires_at` default is naive — consistent |
| 1.4 Race condition | **Fixed** | `__init__.py:187-192` — `IntegrityError` handling present |
| 2.1 Remove `create_all()` | **Fixed** | Not in `create_app()` — only in test fixtures |
| 2.2 SMTP reuse | **Fixed** | `email.py:56` — single connection for newsletter batch |
| 2.3 Base62 validation | **Fixed** | `base62.py:20-21` — explicit character check |
| 2.4 Tag count cache | **Fixed** | `public.py:20-21` — 60-second TTL cache |
| 2.5 Lock file cleanup | **Fixed** | `scheduler.py:43-49` — `os.remove` in finally block |
| 3.3 Delete confirmation | **Fixed** | `dashboard.html:43` — `confirm()` onsubmit |
| 3.4 Invalid tag feedback | **Fixed** | `admin.py:245-246` — flash warning |
| 5.2 Variable shadowing | **Fixed** | `admin.py:197` — `was_published` saved before overwrite |

---

## Remaining Issues

### Priority 1 — Code Quality

#### 1.1 Remove unused `markdown` filter
**File:** `app/__init__.py:83-85`
**Problem:** The `markdown` filter outputs unsanitized HTML. No template uses it (all use `markdown_safe`). It's dead code and a potential XSS vector if accidentally used.
**Fix:** Remove the `markdown` filter entirely.

#### 1.2 Remove or document `csrf_exempt` decorator
**File:** `app/csrf.py:24-27`
**Problem:** Decorator defined but never used on any route. Dead code.
**Fix:** Remove it. It can be re-added if a webhook or public API route needs it later.

#### 1.3 Consolidate duplicate `before_request` handlers
**File:** `app/__init__.py:114-139`
**Problem:** Two separate `@app.before_request` functions (CSRF validation and session timeout). Flask executes both, but the intent isn't obvious — consolidation improves readability.
**Fix:** Merge into a single `before_request` function with clear sections.

### Priority 2 — Security & UX

#### 2.1 Image upload silent failure
**File:** `app/routes/admin.py:52-58`
**Problem:** When `_save_image()` detects an invalid image type (magic bytes don't match extension), it returns `None` with no feedback. The user uploads a file, the post is saved, and the image is silently dropped.
**Fix:** Return an error message tuple from `_save_image()` and flash it:
```python
def _save_image(file):
    if file and file.filename and _allowed_file(file.filename):
        header = file.read(32)
        file.seek(0)
        detected = _detect_image_type(header)
        if detected not in ("png", "jpeg", "gif", "webp"):
            return None, "Uploaded file is not a valid image."
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        return filename, None
    return None, None
```
Then in `new_post()` and `edit_post()`, flash the error if present.

#### 2.2 CSP blocks inline `onsubmit`
**File:** `app/__init__.py:150-157`, `app/templates/admin/dashboard.html:43`
**Problem:** CSP is `'self'` only (no `unsafe-inline`). The delete confirmation uses `onsubmit="return confirm(...)"` which is an inline script and will be blocked by strict CSP enforcement.
**Fix:** Move the confirmation to an external JS handler or add a data attribute and handle it in `main.js`:
```html
<form ... data-confirm="Are you sure you want to delete this post? This cannot be undone.">
```
```javascript
document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
        if (!confirm(form.dataset.confirm)) e.preventDefault();
    });
});
```

#### 2.3 Update default base_url to HTTPS
**File:** `config.toml:23`
**Problem:** `http://localhost:5000` means all links and OG tags are HTTP if deployed without overriding. The `Strict-Transport-Security` header is meaningless with HTTP defaults.
**Fix:** Change default to `https://localhost:5000` or add a comment warning that production deployments must override this.

### Priority 3 — Minor Improvements

#### 3.1 Move config validation out of module-level imports
**File:** `app/__init__.py:10-13`, `app/config.py:27-30`
**Problem:** Runtime errors at import time make the module hard to import in scripts, tests, or tools without env vars set.
**Fix:** Defer validation to `create_app()`. The test fixture already sets env vars before import, so this is a minor ergonomic issue.

#### 3.2 Add type hints to public-facing functions
**File:** `app/utils.py`, `app/base62.py`, `app/csrf.py`, `app/rate_limit.py`
**Problem:** Most functions lack type hints. Inconsistent across the codebase.
**Fix:** Add type hints to function signatures. Low priority but improves maintainability.

---

## Rejected Items

| Source | Claim | Verdict | Reason |
|--------|-------|---------|--------|
| plan2.md 1.1 | Newsletter resends on partial failure | **Acceptable trade-off** | Per-subscriber tracking adds complexity; resending a few emails on crash is tolerable for a personal blog |
| plan2.md 2.2 | `fromisoformat` timezone mismatch | **False** | `utc_now()` returns naive, `session["last_activity"]` stores naive ISO — `fromisoformat` produces naive, no mismatch |
| plan2.md 3.1 | NewsletterRecipient tracking table | **Overengineering** | Per-subscriber delivery tracking is unnecessary for a personal blog |
| plan2.md 3.2 | Newsletter retry with backoff | **Overengineering** | APScheduler runs daily; natural retry on next run is sufficient |
| plan2.md 5.1 | Per-route request size limits | **Already handled** | `MAX_CONTENT_LENGTH = 16MB` enforced globally |
| plan2.md 5.2 | Rate limit admin POST routes | **Overengineering** | Single-user blog; login is rate-limited, which is the realistic attack surface |
| plan3.md 1.1 | Newsletter sends all unpublished posts | **False** | Query filters `Post.published == True` — unpublished posts are excluded |
| plan3.md 1.2 | `expires_at`/`utc_now()` timezone mismatch | **False** | Both are naive datetimes |
| plan3.md 2.1 | Slug regeneration unconditional | **Already fixed** | `admin.py:192` has `if title != post.title` guard |
| plan3.md 2.3 | SMTP connection per subscriber | **False** | `send_newsletter()` opens one connection and reuses it |
| plan3.md 2.4 | Add user deletion route | **Not applicable** | Single-user blog; user management via env vars |
| plan3.md 3.1 | Missing `tests/__init__.py` | **False** | File exists |
| plan.md 3.1 | Timezone-aware `expires_at` | **Not needed** | Naive datetimes are used consistently throughout |

---

## Execution Order

1. **1.1** — Remove unused `markdown` filter (quick, removes XSS risk)
2. **1.2** — Remove unused `csrf_exempt` (quick, dead code cleanup)
3. **2.1** — Image upload error feedback (real UX improvement)
4. **2.2** — Fix CSP / inline onsubmit (correctness)
5. **2.3** — HTTPS default base_url (security)
6. **1.3** — Consolidate before_request handlers (readability)
7. **3.1** — Defer config validation (ergonomics)
8. **3.2** — Type hints (as time permits)
