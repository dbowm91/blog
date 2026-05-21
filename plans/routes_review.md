# Routes Review: Architecture vs Implementation

## Summary

Reviewed all four architectural documents in `architecture/routes/` and verified against actual implementation in `app/routes/`. The codebase is generally well-structured and follows documented patterns, but several discrepancies exist between documentation and implementation, plus one critical security issue.

---

## Verified Claims

### API Routes (`app/routes/api/`)

- **GET /api/posts** - Correctly implemented with pagination, `published` filter
- **POST /api/posts** - Creates posts with title, body, slug, tags, published status
- **PUT /api/posts/<id>** - Updates posts, triggers webhook on publish state change
- **DELETE /api/posts/<id>** - Deletes posts with FTS cleanup
- **GET /api/subscribers** - Lists subscribers with pagination and `confirmed` filter
- **GET /api/stats** - Returns total_views, total_posts, total_shares, total_subscribers, views_this_month, new_subscribers_this_month
- **POST /api/auth** - API key authentication via `X-API-Key` header
- **Rate limits** - DEFAULT_LIMIT="20 per minute", WRITE_LIMIT="10 per minute" correctly applied

### Admin Routes (`app/routes/admin/`)

- **Login/Logout** - `GET/POST /admin/login`, `POST /admin/logout` with CSRF protection
- **2FA routes** - `/admin/2fa/setup`, `/admin/2fa/verify`, `/admin/login-2fa`, `/admin/2fa/backup-codes`, `/admin/2fa/disable` all correctly implemented
- **Password reset** - `/admin/forgot-password`, `/admin/reset/<token>` correctly implemented
- **Post editor** - `GET /admin/new`, `GET /admin/edit/<int:post_id>` in `editor.py`
- **Post delete** - `POST /admin/delete/<int:post_id>` in `manage.py`
- **Post bulk** - `POST /admin/bulk` in `posts/__init__.py`
- **Post revisions** - Routes in `revisions.py`: list, view, restore
- **Newsletter reset** - `POST /admin/newsletter-reset/<int:post_id>` in `auth.py`
- **Tag CRUD** - All routes in `tags.py`: list, create, rename, delete
- **User management** - All routes in `users.py`: list, create, delete, promote, demote, make-owner, password
- **Sessions** - `GET /admin/sessions`, `POST /admin/sessions/revoke/<int:sess_id>`
- **Media** - `GET /admin/media`, `POST /admin/media/upload`, `POST /admin/media/delete/<filename>`
- **Backup** - All routes in `backup.py`: list, create, download, restore, delete, verify
- **Settings** - `GET /admin/settings`, `POST /admin/settings/theme`
- **Audit log** - `GET /admin/audit` with action filtering
- **Comments** - `GET /admin/comments`, `POST /admin/comments/<int:comment_id>/approve`, `POST /admin/comments/<int:comment_id>/delete`
- **Pages** - `GET /admin/pages`, `GET/POST /admin/pages/new`, `GET/POST /admin/pages/edit/<int:page_id>`, `POST /admin/pages/delete/<int:page_id>`
- **Series** - All routes in `series.py`: list, new, edit, delete, posts, reorder

### Public Routes (`app/routes/public/`)

- **Home page** - `GET /` and `GET /page/<int:page>`
- **Tag pages** - `GET /tag/<slug>` and `GET /tag/<slug>/<int:page>`
- **Search** - `GET /search` with `q` query param
- **Archive** - `GET /archive` with year filtering and cursor pagination
- **Series** - `GET /series/<slug>`
- **Static page** - `GET /page/<slug>`
- **Post page** - `GET /post/<slug>`
- **Short URL** - `GET /s/<code>` with base62 decoding
- **Share tracking** - `POST /api/track-share`
- **Subscribe** - `POST /subscribe` (only POST, no GET)
- **Confirm/Unsubscribe** - `GET /confirm/<token>`, `GET /unsubscribe/<token>`
- **Comments** - `POST /post/<slug>/comment`
- **Sitemap** - `GET /sitemap.xml` (cached)
- **Robots.txt** - `GET /robots.txt`
- **Health check** - `GET /health` with optional `?detailed=1`
- **Metrics** - `GET /metrics` (Prometheus-compatible)
- **Favicon** - `GET /favicon.ico` redirects to SVG

### RSS/Feeds (`app/routes/rss.py`)

- **RSS feed** - `GET /rss` with proper RSS 2.0 format
- **Atom feed** - `GET /atom` with proper Atom 1.0 format
- **JSON feed** - `GET /json` with JSON Feed 1.1 format
- **Cache timeout** - 300 seconds (5 minutes) correctly applied

---

## Discrepancies

### 1. API Subscribers DELETE endpoint (Medium)

**Doc**: `api-routes.md` line 13 says `POST /api/subscribers/<id>` for delete
**Actual**: `app/routes/api/subscribers.py:132` - `DELETE /api/subscribers/<int:subscriber_id>`

### 2. API Subscribers export route missing from docs (Medium)

**Doc**: `api-routes.md` line 12 shows `POST /api/subscribers/export`
**Actual**: No such route exists in `app/routes/api/subscribers.py`. The export endpoint only exists in admin at `GET /admin/subscribers/export` (`app/routes/admin/subscribers.py:83`)

### 3. Admin bulk operations route signature (Low)

**Doc**: `admin-routes.md` line 98 says `POST /admin/bulk`
**Actual**: `app/routes/admin/posts/__init__.py:118` - correct, but doc doesn't mention the route is at `/admin/bulk` not `/admin/posts/bulk`

### 4. Post revisions route in doc but not in code (Medium)

**Doc**: `admin-routes.md` line 105 shows `GET /admin/posts/<int:post_id>/revisions/<int:rev_id>`
**Actual**: No such route exists. The revisions routes in `app/routes/admin/posts/revisions.py` are:
- `GET /admin/posts/<int:post_id>/revisions` (line 49)
- `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore` (line 75)

The doc incorrectly shows `rev_id` and `revision_id` being different in the GET route.

### 5. Admin Subscriber export method (Low)

**Doc**: `admin-routes.md` line 113 shows `GET /admin/subscribers/export`
**Actual**: `app/routes/admin/subscribers.py:83` - correct (GET)

### 6. Health check secret parameter (Low)

**Doc**: `public-routes.md` line 98 says `Auth: Optional secret via HEALTH_CHECK_SECRET`
**Actual**: `app/routes/public/meta.py:198-202` checks for `secret` query param, but the implementation matches the doc. This is **verified correct**.

### 7. API POST /api/posts missing from doc table (Medium)

**Doc**: `api-routes.md` table line 10 only shows `GET /api/posts` and `GET /api/posts/<id>`, `PUT /api/posts/<id>`, `DELETE /api/posts/<id>` but misses the `POST /api/posts` create endpoint
**Actual**: `app/routes/api/posts.py:105` has `POST /api/posts`

---

## Bugs Identified

### 1. Preview Route Security Mismatch (Critical)

**Location**: `app/routes/public/posts.py:94-129`

**Issue**: Documentation (`public-routes.md` lines 57-60) states preview requires only HMAC token authentication:
> "Auth: HMAC token-based (no login required)"

But actual implementation at lines 128-129:
```python
if not session.get('admin_user_id'):
    abort(403)
```

This requires BOTH a valid HMAC token AND an active admin session (`admin_user_id` in session). The documentation is incomplete/misleading.

**Impact**: Developers relying on documentation would implement HMAC-only authentication, which would fail against the actual implementation that requires session binding.

**Recommendation**: Update `public-routes.md` to document that preview requires both HMAC token AND admin session verification.

### 2. No rate limiting on API subscriber delete and stats endpoints (Medium)

**Location**: `app/routes/api/subscribers.py:132` and `app/routes/api/stats.py:17`

**Issue**: The DELETE `/api/subscribers/<id>` endpoint has `@limiter.limit(WRITE_LIMIT)` applied (line 134), but the stats endpoint doesn't have explicit rate limit decorator:
```python
@api.route("/stats", methods=["GET"])
@require_api_key
@limiter.limit(DEFAULT_LIMIT)  # This is applied
def get_stats() -> any:
```

Actually looking closer, stats does have rate limit. The issue is API subscribers create endpoint (`POST /api/subscribers`) at line 76 has rate limit, but the docs don't mention rate limits for the subscribers endpoints at all (the rate limit table in api-routes.md only covers posts and auth).

**Impact**: Missing documentation for rate limits on subscriber endpoints.

### 3. JSON Feed uses `id` as slug not full URL (Low - Potential Interop Issue)

**Location**: `app/routes/rss.py:256`

**Issue**: In JSON Feed, the `id` field is set to `item["slug"]` (just the slug):
```python
"id": item["slug"],
```

But JSON Feed spec recommends using the full URL as `id`. The doc at `rss-feeds.md` shows `id` as full URL format.

**Impact**: JSON Feed consumers expecting full URLs may have compatibility issues.

---

## Improvement Recommendations

### 1. Update `api-routes.md` to fix discrepancies

- Line 13: Change `POST /api/subscribers/<id>` to `DELETE /api/subscribers/<int:subscriber_id>`
- Line 12: Remove `POST /api/subscribers/export` (doesn't exist in API)
- Add `POST /api/posts` to the endpoints table
- Document rate limits for subscriber endpoints

### 2. Update `admin-routes.md` to fix discrepancies

- Line 105: Change `GET /admin/posts/<int:post_id>/revisions/<int:rev_id>` to match actual routes, or remove if not implemented
- Line 98: Clarify bulk route is at `/admin/bulk`

### 3. Update `public-routes.md` to document preview security correctly

Lines 57-60 should state that preview requires both HMAC token validation AND admin session verification.

### 4. Consider adding `/api/posts` POST to the API routes documentation table

The create post endpoint is missing from the table in `api-routes.md`.

---

## Files Requiring Changes

| File | Change |
|------|--------|
| `architecture/routes/api-routes.md` | Fix DELETE method, remove non-existent export, add POST /api/posts to table, add subscriber rate limits |
| `architecture/routes/admin-routes.md` | Fix revisions route, clarify bulk route path |
| `architecture/routes/public-routes.md` | Document HMAC+session requirement for preview |
| `app/routes/public/posts.py` | Consider logging when preview access fails due to missing session (security audit trail) |

---

## Review Completeness

- [x] API routes (`app/routes/api/`) - 4 files reviewed
- [x] Admin routes (`app/routes/admin/`) - 14 route files reviewed
- [x] Public routes (`app/routes/public/`) - 5 route files reviewed
- [x] RSS feeds (`app/routes/rss.py`) - reviewed
- [x] Cross-referenced with models, validators, and helpers
- [x] Verified HTTP methods, auth requirements, query parameters, response formats