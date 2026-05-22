# Routes Review - Discrepancies and Improvement Plan

## Executive Summary

Reviewed 4 architecture documents against actual route implementations. Found **17 discrepancies** between documentation and code, **4 missing routes**, **3 security gaps**, and **2 potential bugs**.

---

## ADMIN ROUTES (`app/routes/admin/`)

### Discrepancies

| Doc Location | Doc Claim | Actual Implementation | Severity |
|-------------|-----------|----------------------|----------|
| `admin-routes.md:104` | `GET /admin/posts/<int:post_id>/revisions` | `GET /posts/<int:post_id>/revisions` (line 49 of `posts/revisions.py`) | Low |
| `admin-routes.md:75` | `POST /admin/newsletter-reset/<int:post_id>` | `POST /admin/newsletter-reset/<int:post_id>` (line 125 of `auth.py`) | OK |
| `admin-routes.md:104-107` | `GET /admin/posts/<int:post_id>/revisions/<int:rev_id>` | `GET /posts/<int:post_id>/revisions/<int:revision_id>` (line 75) | Low |
| `admin-routes.md:80-82` | `GET /admin/new`, `GET /admin/edit/<int:post_id>` | `GET /new`, `GET /edit/<int:post_id>` - actual routes correct, doc path issue | Low |
| `admin-routes.md:21` | Module structure shows `series.py` but doc only lists `/series/<slug>` | Additional routes: `/series/new`, `/series/<int:series_id>/edit`, `/series/<int:series_id>/delete`, `/series/<int:series_id>/posts`, `/series/<int:series_id>/reorder` | Medium |
| `admin-routes.md:169-172` | `GET /admin/newsletter/preview` listed as separate route | Actually `@admin.route("/newsletter/preview")` (line 70 of `newsletter.py`) - correct | OK |
| `admin-routes.md:87-92` | Post preview only documents `share=1` param | Missing `preview-markdown` POST route at `editor.py:328-345` | Medium |

### Missing Routes (not in doc)

1. **`POST /admin/preview-markdown`** - Markdown preview for live editing (`editor.py:328`)
2. **`POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore`** - Restore revision actually at `/posts/<int:post_id>/revisions/<int:revision_id>/restore` (line 75-76)
3. **`POST /admin/sessions/revoke/<int:sess_id>`** - Revoke session (`sessions.py:43`)
4. **`POST /admin/media/delete/<filename>`** - Delete media (documented but path format unclear)

### Security Issues

1. **Comment submission lacks CSRF protection** (`comments.py:12-52`)
   - Public comment route `POST /post/<slug>/comment` has no CSRF decorator
   - Subscribe route does call `validate_csrf_token()` (`subscribe.py:59`)
   - **BUG**: Inconsistent CSRF protection

2. **Preview route has redundant auth check** (`posts.py:128`)
   - `public_preview` requires BOTH valid HMAC token AND `session.get('admin_user_id')`
   - But HMAC token generation in `manage.py:48-60` doesn't involve `admin_user_id`
   - The session check appears to be legacy or incorrect

### Code Quality Issues

1. **Slug collision in backup routes** (`backup.py:95,120,182,213`)
   - Uses same `BACKUP_FILENAME_RE` pattern repeated 4 times
   - Should extract to shared helper

2. **Hardcoded page size in analytics** (`analytics.py:23`)
   - `days = min(max(days, 7), 365)` - magic numbers 7 and 365 not from config

3. **Media cleanup function not registered** (`media.py:186`)
   - `cleanup_orphaned_images()` exists but is never exposed as route/task

---

## API ROUTES (`app/routes/api/`)

### Discrepancies

| Doc Location | Doc Claim | Actual Implementation | Severity |
|-------------|-----------|----------------------|----------|
| `api-routes.md:11-12` | `DELETE /api/subscribers/<int:subscriber_id>` only | Also has `POST /api/subscribers` (line 76-129 of `subscribers.py`) | Medium |
| `api-routes.md:125-131` | Rate limits table | Actual limits differ: `DEFAULT_LIMIT = "20 per minute"`, `WRITE_LIMIT = "10 per minute"` (posts.py:18-19) | Low |
| `api-routes.md:127` | "Authenticated reads 20/min" | All API reads use `DEFAULT_LIMIT` (20/min), writes use `WRITE_LIMIT` (10/min) | Documentation only |
| `api-routes.md:100-119` | API auth endpoint returns `{valid: true}` | Actual returns `{error: "..."}` on failure with 401/503 | Low |

### Missing Documentation

1. **Webhook events triggered on publish state change** (`posts.py:292-302`)
   - `post.published` state change triggers `create_webhook_event()` but not documented
   - `subscriber.confirmed` event not documented in subscribe routes

2. **`POST /api/subscribers`** - Creates new subscriber, returns existing if duplicate

3. **API validation errors** - Each endpoint returns specific error formats not documented

### Security Issues

1. **Single API key for all clients** (`auth.py:10`)
   - Uses single `API_KEY` env var - no per-client keys
   - No rate limiting per API key (only per IP via Flask-Limiter)

2. **API key logged on error** (`auth.py:23`)
   - Uses `hmac.compare_digest` - correct timing-safe comparison
   - But `Invalid or missing API key` error message could aid enumeration

---

## PUBLIC ROUTES (`app/routes/public/`)

### Discrepancies

| Doc Location | Doc Claim | Actual Implementation | Severity |
|-------------|-----------|----------------------|----------|
| `public-routes.md:9` | `/page/<slug>` only in browse.py routes column | Actually in `browse.py:208-219` - correct | OK |
| `public-routes.md:55-60` | Preview route docs `token` and `expires` params | Also requires `session.get('admin_user_id')` check at `posts.py:128` | Medium |
| `public-routes.md:113` | Comment fields listed | Missing that `approved=False` always on submit | Low |

### Missing Documentation

1. **Static pages** (`/page/<slug>`) not explained in browse routes detail
2. **Archive pagination** uses cursor-based navigation with `year`, `cursor`, `direction` params
3. **Share tracking** `/api/track-share` uses base62 short codes not documented

### Security Issues

1. **Public preview leaks admin session check logic** (`posts.py:128`)
   ```python
   if not session.get('admin_user_id'):
       abort(403)
   ```
   This check is after HMAC validation - HMAC token should be sufficient for preview access

2. **Short URL decode error silently redirects to home** (`posts.py:153-154`)
   ```python
   except (ValueError, KeyError):
       return redirect("/")
   ```
   Could be used to enumerate valid post IDs via timing differences

3. **Subscribe CSRF token required but other public forms not** (`subscribe.py:59`)
   - Comments route has no CSRF protection
   - Inconsistent form security

---

## RSS FEEDS (`app/routes/rss.py`)

### Discrepancies

| Doc Location | Doc Claim | Actual Implementation | Severity |
|-------------|-----------|----------------------|----------|
| `rss-feeds.md:79-81` | "All feeds are cached for 5 minutes" | Cache timeout is 300 seconds (`@flask_cache.cached(timeout=300)`) - correct | OK |

### Issues

1. **Conditional GET support** - ETag generation and `If-None-Match` handling not documented
2. **Favicon redirect** to SVG not documented (`meta.py:183-189`)
3. **Atom feed author** falls back to "admin" if `AUTHOR_NAME` not set (line 144)

---

## RATE LIMITING GAPS

| Area | Documented | Actual | Issue |
|------|-----------|--------|-------|
| API reads | 20/min | 20/min | OK |
| API writes | 10/min | 10/min | OK |
| Public subscribe | 10/min | 10/min | OK |
| Public comments | 20/min | No rate limit on comments.py | **Missing** |
| Public preview | Not documented | 30/min | Should document |
| API key check | 1000/hour | No hourly limit | **Not implemented** |

---

## RECOMMENDATIONS

### Priority 1 (Security)

1. **Add CSRF protection to comment submission** (`comments.py`)
2. **Fix public preview redundant session check** (`posts.py:128`)
   - Either remove session check (HMAC sufficient) or document it
3. **Add rate limiting to comment submission** (`comments.py:12`)
   - Currently no `@limiter.limit()` decorator

### Priority 2 (Documentation)

1. **Update `admin-routes.md`**:
   - Add `POST /admin/preview-markdown`
   - Add `POST /admin/sessions/revoke/<int:sess_id>`
   - Fix revision route paths (remove `/admin` prefix, use `revision_id`)
   - Add series management routes

2. **Update `api-routes.md`**:
   - Add `POST /api/subscribers`
   - Document webhook event triggering on publish/unpublish
   - Fix rate limits table to match actual constants

3. **Update `public-routes.md`**:
   - Document preview route admin session requirement
   - Add rate limit for comments (when implemented)

### Priority 3 (Code Quality)

1. **Extract backup path validation** to helper function
2. **Add `cleanup_orphaned_images` to admin routes or remove dead code**
3. **Configurable analytics days range** in `analytics.py`

---

## Files Referenced

| File | Issues |
|------|--------|
| `app/routes/admin/auth.py:32-34` | Login rate limit "5 per minute" correct |
| `app/routes/admin/posts/revisions.py:75-76` | Route path inconsistent with doc |
| `app/routes/admin/newsletter.py:70` | Preview route correct |
| `app/routes/public/posts.py:94-143` | Preview auth logic confusing |
| `app/routes/public/comments.py:12-52` | Missing CSRF, missing rate limit |
| `app/routes/api/posts.py:292-302` | Undocumented webhook events |
| `app/routes/rss.py:59-75` | Cache correctly 300s (5 min) |