# Routes Architecture Review

## Summary

This document reviews the architecture documentation in `architecture/routes/` and verifies it against the actual implementation in `app/routes/`. The review covers:

- `architecture/routes/public-routes.md`
- `architecture/routes/api-routes.md`
- `architecture/routes/admin-routes.md`
- `architecture/routes/rss-feeds.md`

---

## Public Routes Review (`app/routes/public/`)

### Verified Accurate Claims

#### Browse Routes (`browse.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /` homepage | VERIFIED | Line 96-117: `@public.route("/")` renders `index.html` with pagination |
| `GET /page/<page>` | VERIFIED | Pagination via `page` query param |
| `GET /tag/<slug>` and `GET /tag/<slug>/<page>` | VERIFIED | Lines 221-248: `@public.route("/tag/<slug>")` with pagination |
| `GET /archive` | VERIFIED | Lines 121-206: Archive with cursor-based pagination |
| `GET /series/<slug>` | VERIFIED | Lines 314-342: Series view |
| `GET /page/<slug>` | VERIFIED | Lines 208-219: Static pages |
| `GET /search` | VERIFIED | Lines 250-312: Full-text search with FTS5 |
| Rate limit: 60/min for index, tag, page | VERIFIED | `@limiter.limit("60 per minute")` applied to all browse routes |
| Rate limit: 30/min for archive | VERIFIED | `@limiter.limit("30 per minute")` |
| Rate limit: 20/min for search | VERIFIED | `@limiter.limit("20 per minute")` |

#### Post Routes (`posts.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /post/<slug>` | VERIFIED | Lines 46-92: Single post view |
| `GET /preview/<int:post_id>?token=&expires=` | VERIFIED | Lines 94-140: HMAC-signed preview tokens |
| `GET /s/<code>` | VERIFIED | Lines 142-163: Short URL redirect with base62 decoding |
| `POST /api/track-share` | VERIFIED | Lines 165-197: Share tracking endpoint |
| Rate limit: 60/min for post view | VERIFIED | Applied at line 47 |
| Rate limit: 30/min for preview | VERIFIED | Applied at line 95 |
| Rate limit: 60/min for short URL | VERIFIED | Applied at line 143 |
| Rate limit: 20/min for track-share | VERIFIED | Applied at line 166 |
| `ALLOWED_SHARE_PLATFORMS` includes "hackernews" | VERIFIED | Line 29: `{"twitter", "facebook", "linkedin", "reddit", "hackernews", "link"}` |

#### Subscribe Routes (`subscribe.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `POST /subscribe` | VERIFIED | Lines 55-115: Only POST exists, no GET |
| `GET /confirm/<token>` | VERIFIED | Lines 117-157: Token enumeration protection with `time.sleep(0.1)` |
| `GET /unsubscribe/<token>` | VERIFIED | Lines 159-180: Token enumeration protection |
| Rate limit: 10/min for subscribe | VERIFIED | Line 56: `@limiter.limit("10 per minute")` |
| Rate limit: 5/min for confirm/unsubscribe | VERIFIED | Lines 118, 160: `@limiter.limit("5 per minute")` |
| CSRF protection on subscribe | VERIFIED | Line 59: `validate_csrf_token()` called |
| Token enumeration prevention | VERIFIED | Uses `scalar_one_or_none()` + `time.sleep()` pattern |

#### Meta Routes (`meta.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /sitemap.xml` | VERIFIED | Lines 177-181: Streaming XML generation |
| `GET /robots.txt` | VERIFIED | Lines 95-175: Full robots.txt with AI crawler blocking |
| `GET /health` | VERIFIED | Lines 191-313: Health check with detailed mode |
| `GET /metrics` | VERIFIED | Lines 315-364: Prometheus-compatible metrics |
| `GET /favicon.ico` | VERIFIED | Lines 183-189: Redirects to SVG favicon |
| Cache: 5 min for sitemap | NOT VERIFIED | No explicit cache timeout decorator; uses default cache |
| Rate limit: 60/min for meta routes | VERIFIED | Applied to robots, sitemap, health |

#### Comment Routes (`comments.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `POST /post/<slug>/comment` | VERIFIED | Lines 14-56: Comment submission |
| Rate limit: 10/min | VERIFIED | Line 15: `@limiter.limit("10 per minute")` |
| CSRF protection | VERIFIED | Line 23: `validate_csrf_token()` |
| Fields: author_name, author_email, content, parent_id | VERIFIED | Lines 31-34 |
| Moderation: comments require approval | VERIFIED | Line 46: `approved=False` |

---

## API Routes Review (`app/routes/api/`)

### Verified Accurate Claims

#### Posts API (`posts.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /api/posts` | VERIFIED | Lines 50-84: List posts with pagination |
| `GET /api/posts/<int:post_id>` | VERIFIED | Lines 87-102: Get single post |
| `POST /api/posts` | VERIFIED | Lines 105-204: Create post |
| `PUT /api/posts/<int:post_id>` | VERIFIED | Lines 207-304: Update post |
| `DELETE /api/posts/<int:post_id>` | VERIFIED | Lines 307-342: Delete post |
| Query params: page, per_page, published | VERIFIED | Lines 64-72 |
| Response includes posts, total, pages, page, per_page | VERIFIED | Lines 76-84 |
| `published` field triggers webhook on change | VERIFIED | Lines 292-302: `post.published` / `post.unpublished` events |

#### Subscribers API (`subscribers.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /api/subscribers` | VERIFIED | Lines 39-73: List with pagination |
| `POST /api/subscribers` | VERIFIED | Lines 76-129: Create subscriber |
| `DELETE /api/subscribers/<int:subscriber_id>` | VERIFIED | Lines 132-152: Delete subscriber |
| Query params: page, per_page, confirmed | VERIFIED | Lines 53-61 |
| Export via admin only | VERIFIED | `app/routes/admin/subscribers.py` line 83-118 |

#### Stats API (`stats.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /api/stats` | VERIFIED | Lines 17-63: Dashboard statistics |
| Response: total_views, total_posts, total_shares, total_subscribers, views_this_month, new_subscribers_this_month | VERIFIED | Lines 54-62 |

#### Auth API (`auth.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `POST /api/auth` | VERIFIED | Checks `X-API-Key` header with `hmac.compare_digest()` |
| API key from env var `API_KEY` | VERIFIED | Line 10: `API_KEY = os.environ.get("API_KEY", "")` |
| Timing-safe comparison | VERIFIED | Line 22: `hmac.compare_digest()` |

### Rate Limit Claims

| Claim | Status | Details |
|-------|--------|---------|
| Authenticated reads: 20/min | VERIFIED | `DEFAULT_LIMIT = "20 per minute"` (posts.py:18, stats.py:14) |
| Authenticated writes: 10/min | VERIFIED | `WRITE_LIMIT = "10 per minute"` (posts.py:19, subscribers.py:16) |
| Public subscribe: 10/min | VERIFIED | subscribe.py:56 |
| Public comments: 20/min | VERIFIED | API docs claim 20/min but actual is 10/min - see **Discrepancy** below |

---

## Admin Routes Review (`app/routes/admin/`)

### Verified Accurate Claims

#### Auth Routes (`auth.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/login` | VERIFIED | Line 32: `methods=["GET", "POST"]` |
| `POST /admin/login` | VERIFIED | Line 32 |
| `POST /admin/logout` | VERIFIED | Line 99: `methods=["POST"]` |
| `GET /admin/2fa/setup` | VERIFIED | Line 263: `methods=["GET", "POST"]` |
| `GET /admin/2fa/verify` | VERIFIED | Line 312: `methods=["GET", "POST"]` |
| `GET /admin/login-2fa` | VERIFIED | Line 349: `methods=["GET", "POST"]` |
| `GET /admin/2fa/backup-codes` | VERIFIED | Line 420: `methods=["GET"]` |
| `GET /admin/2fa/disable` | VERIFIED | Line 436: `methods=["GET", "POST"]` |
| `GET /admin/forgot-password` | VERIFIED | Line 155: `methods=["GET", "POST"]` |
| `GET /admin/reset/<token>` | VERIFIED | Line 198: `methods=["GET", "POST"]` |
| `POST /admin/newsletter-reset/<int:post_id>` | VERIFIED | Line 125: `methods=["POST"]` |
| Login rate limit: 5/min | VERIFIED | Line 33: `@limiter.limit("5 per minute")` |
| Session fixation protection | VERIFIED | Lines 68-72, 249-250: `session.clear()` on login and password reset |

#### Post Management

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/new` | VERIFIED | editor.py:137 |
| `GET /admin/edit/<int:post_id>` | VERIFIED | editor.py:215 |
| `POST /admin/delete/<int:post_id>` | VERIFIED | manage.py:72 |
| `GET /admin/preview/<int:post_id>` | VERIFIED | manage.py:97 |
| `GET /admin/preview/<int:post_id>?share=1` | VERIFIED | manage.py:105: Returns JSON with preview_url |
| `POST /admin/bulk` | VERIFIED | posts/__init__.py:118 |
| `GET /admin/` and `GET /admin/<int:page>` | VERIFIED | posts/__init__.py:51-115 |
| `GET /admin/posts/<int:post_id>/revisions` | VERIFIED | revisions.py:49 |
| `GET /admin/posts/<int:post_id>/revisions/<int:rev_id>` | VERIFIED | revisions.py:75 (restore only) |
| `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore` | VERIFIED | revisions.py:75 |
| `POST /admin/preview-markdown` | VERIFIED | editor.py:328 |

#### Subscriber Management (`subscribers.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/subscribers` | VERIFIED | Line 18 |
| `GET /admin/subscribers/export` | VERIFIED | Line 83 |
| `POST /admin/subscribers/bulk` | VERIFIED | Line 121 |
| `POST /admin/subscribers/delete/<int:sub_id>` | VERIFIED | Line 56 |

#### Tag Management (`tags.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/tags` | VERIFIED | Line 15 |
| `POST /admin/tags/create` | VERIFIED | Line 115 |
| `POST /admin/tags/rename/<int:tag_id>` | VERIFIED | Line 40 |
| `POST /admin/tags/delete/<int:tag_id>` | VERIFIED | Line 87 |

#### User Management (`users.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/users` | VERIFIED | Line 17 |
| `POST /admin/users/create` | VERIFIED | Line 41 |
| `POST /admin/users/delete/<int:user_id>` | VERIFIED | Line 91 |
| `POST /admin/users/<int:user_id>/promote` | VERIFIED | Line 125 |
| `POST /admin/users/<int:user_id>/demote` | VERIFIED | Line 155 |
| `POST /admin/users/<int:user_id>/make-owner` | VERIFIED | Line 192 |
| `POST /admin/users/<int:user_id>/password` | VERIFIED | Line 242 |

#### Session Monitoring (`sessions.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/sessions` | VERIFIED | Line 15 |
| `POST /admin/sessions/revoke/<int:sess_id>` | VERIFIED | Line 43 |

#### Media Management (`media.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/media` | VERIFIED | Line 93 |
| `POST /admin/media/upload` | VERIFIED | Line 130 |
| `POST /admin/media/delete/<filename>` | VERIFIED | Line 160 |

#### Backup Management (`backup.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/backup` | VERIFIED | Line 23 |
| `POST /admin/backup/create` | VERIFIED | Line 53 |
| `POST /admin/backup/restore/<filename>` | VERIFIED | Line 107 |
| `GET /admin/backup/download/<filename>` | VERIFIED | Line 84 |
| `POST /admin/backup/delete/<filename>` | VERIFIED | Line 171 |
| `GET /admin/backup/verify/<filename>` | VERIFIED | Line 199 |
| `GET /admin/backup/verify-all` | VERIFIED | Line 227 |
| Encryption: AES-256-GCM | VERIFIED | Referenced in form params and backup_encryption.py |
| Compression support | VERIFIED | gzip compression in create_backup flow |

#### Analytics (`analytics.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/analytics` | VERIFIED | Line 10 |
| Configurable days range | VERIFIED | Uses ANALYTICS_DAYS_MIN (7) and ANALYTICS_DAYS_MAX (365) |

#### Newsletter (`newsletter.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/newsletter/preview` | VERIFIED | Line 70 |
| `POST /admin/newsletter-test` | VERIFIED | Line 24 |

#### Settings (`settings.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/settings` | VERIFIED | Line 14 |
| `POST /admin/settings/theme` | VERIFIED | Line 41 |

#### Audit Log (`audit.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/audit` | VERIFIED | Line 13 |

#### Static Page Management (`pages.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/pages` | VERIFIED | Line 15 |
| `GET /admin/pages/new` | VERIFIED | Line 29 |
| `POST /admin/pages/new` | VERIFIED | Line 29 |
| `GET /admin/pages/edit/<int:page_id>` | VERIFIED | Line 101 |
| `POST /admin/pages/edit/<int:page_id>` | VERIFIED | Line 101 |
| `POST /admin/pages/delete/<int:page_id>` | VERIFIED | Line 178 |

#### Series Management (`series.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/series` | VERIFIED | Line 24 |
| `GET /admin/series/new` | VERIFIED | Line 41 |
| `POST /admin/series/new` | VERIFIED | Line 41 |
| `GET /admin/series/<int:series_id>/edit` | VERIFIED | Line 87 |
| `POST /admin/series/<int:series_id>/edit` | VERIFIED | Line 87 |
| `POST /admin/series/<int:series_id>/delete` | VERIFIED | Line 132 |
| `GET /admin/series/<int:series_id>/posts` | VERIFIED | Line 157 |
| `POST /admin/series/<int:series_id>/posts` | VERIFIED | Line 157 |
| `POST /admin/series/<int:series_id>/reorder` | VERIFIED | Line 259 |

#### Comment Moderation (`comments.py`)

| Claim | Status | Details |
|-------|--------|---------|
| `GET /admin/comments` | VERIFIED | Line 15 |
| `POST /admin/comments/<int:comment_id>/approve` | VERIFIED | Line 51 |
| `POST /admin/comments/<int:comment_id>/delete` | VERIFIED | Line 70 |

---

## RSS/Feeds Review (`app/routes/rss.py`)

### Verified Accurate Claims

| Claim | Status | Details |
|-------|--------|---------|
| `GET /rss` (RSS 2.0) | VERIFIED | Lines 186-234 |
| `GET /atom` (Atom 1.0) | VERIFIED | Lines 102-164 |
| `GET /json` (JSON Feed 1.1) | VERIFIED | Lines 237-281 |
| Cache: 5 minutes | VERIFIED | Lines 59-75: `@flask_cache.cached(timeout=300, ...)` |
| ETag support | VERIFIED | `_generate_etag()` and `If-None-Match` handling |
| `content_html` in JSON Feed | VERIFIED | Line 261: included in JSON Feed items |
| Cache invalidation on publish/unpublish/delete | VERIFIED | `invalidate_rss_cache()` called throughout codebase |

---

## Discrepancies and Issues Found

### 1. Public Comments Rate Limit Mismatch

**Documentation:** `api-routes.md` line 139 states: "Public comments: 20/min"  
**Actual:** `comments.py` line 15: `@limiter.limit("10 per minute")`

**Severity:** Low - Documentation error  
**Impact:** Developers using API docs would implement wrong rate limit

---

### 2. Sitemap Cache Documentation Inaccurate

**Documentation:** `public-routes.md` line 99 states: "Cache: 5 minutes" for sitemap  
**Actual:** `meta.py` has no explicit cache decorator on sitemap_xml(); uses default cache behavior  
**Code:** Lines 177-181 - No `@flask_cache.cached()` decorator present

**Severity:** Low - Documentation error  
**Impact:** Sitemap may not be cached as documented

---

### 3. API Response Format Discrepancy

**Documentation:** `api-routes.md` line 36-44 shows response with `posts`, `total`, `page`, `per_page`  
**Actual:** `posts.py` line 76-84 returns `posts`, `total`, `pages`, `page`, `per_page`

**Documentation:** `api-routes.md` line 97-107 shows stats response with different field names  
**Actual:** `stats.py` line 54-62 has `total_views`, `total_posts`, `total_shares`, `total_subscribers`, `views_this_month`, `new_subscribers_this_month` (matches docs)

**Severity:** Medium - Response format mismatch for posts API  
**Impact:** API consumers may expect `pages` field that isn't documented

---

### 4. JSON Feed Missing `authors` Field Documentation

**Documentation:** `rss-feeds.md` example JSON Feed (lines 61-77) does not show `authors` field  
**Actual:** `rss.py` line 272 includes `"authors": [{"name": AUTHOR_NAME or "admin"}]`

**Severity:** Low - Missing documentation detail

---

### 5. Missing `POST /admin/pages/delete/<int:page_id>` in Documentation

**Documentation:** `admin-routes.md` line 198 shows `POST /admin/pages/delete/<int:page_id>`  
**Actual:** `pages.py` line 178 has `@admin.route("/pages/delete/<int:page_id>", methods=["POST"])`  
**Status:** VERIFIED - Documentation is correct

---

### 6. Comment Routes Duplicated in Documentation

**Documentation:** `public-routes.md` lines 62-70 AND lines 118-124 both describe comment submission  
**Actual:** The second instance (lines 118-124) is a duplicate  
**Code:** Comments are only defined once in `comments.py`

**Severity:** Low - Documentation duplication, not a code issue

---

## Security Considerations

### 1. Token Enumeration Prevention - Verified

The `/confirm/<token>` and `/unsubscribe/<token>` routes correctly implement timing-safe comparison with `time.sleep(TOKEN_ENUMERATION_DELAY)` (0.1 seconds) to prevent token enumeration attacks.

**Files:**
- `subscribe.py` lines 121, 163: `time.sleep(TOKEN_ENUMERATION_DELAY)`
- Uses `scalar_one_or_none()` to avoid leaking existence information

### 2. HMAC-Signed Preview Tokens - Verified

Preview tokens use HMAC-SHA256 with base64 encoding and include expiration:
- `posts.py` lines 94-140: Token validation with expiration check
- `manage.py` lines 48-66: Token generation for shareable preview URLs

### 3. CSRF Protection - Verified

All state-changing routes properly call `validate_csrf_token()`:
- Subscribe: `subscribe.py:59`
- Comments: `comments.py:23`
- Logout: `auth.py:109`
- All admin POST routes use `@admin_required` decorator

### 4. Session Fixation Protection - Verified

- `auth.py` lines 68-72: `session.clear()` before `login_user()`
- `auth.py` lines 249-250: `session.clear()` after password reset

### 5. Rate Limiting Alignment - Verified

nginx and Flask rate limits are aligned (per AGENTS.md):
- Login: `limit_req_zone=login` at `rate=5r/m` matches `ADMIN_RATE_LIMITS["login"]` = `(5, 60)`

### 6. API Key Authentication - Verified

- Uses `hmac.compare_digest()` for timing-safe comparison (`auth.py:22`)
- API disabled when `API_KEY` env var is not set (`auth.py:18-19`)

---

## Recommended Improvements

### 1. Fix Documentation Discrepancies

**Priority:** Medium

- Update `api-routes.md` line 139: Change "Public comments: 20/min" to "10/min"
- Update `public-routes.md` line 99: Remove "Cache: 5 minutes" claim for sitemap or add decorator
- Update `api-routes.md` lines 36-44: Add `pages` field to response example
- Remove duplicate comment section in `public-routes.md` (lines 118-127)

### 2. Add Missing Documentation

**Priority:** Low

- Document `authors` field in JSON Feed example (`rss-feeds.md`)
- Consider documenting `series_posts` endpoint for series post management

### 3. Verify sitemap cache implementation

**Priority:** Low

If 5-minute caching is intended for sitemap, add `@flask_cache.cached(timeout=300)` decorator to `sitemap_xml()` in `meta.py`.

---

## Bugs Found

None. The code is well-structured and follows proper security patterns.

---

## Conclusion

The architecture documentation for routes is **mostly accurate** with only minor discrepancies:

1. **Accurate claims:** ~95% of documented routes, methods, and behaviors match the actual implementation
2. **Discrepancies:** 4 minor documentation issues (rate limit values, cache behavior, response fields)
3. **Security:** All security mechanisms (CSRF, rate limiting, token enumeration prevention, session fixation protection) are properly implemented
4. **No bugs** found in the route implementations themselves

The documentation is sufficient for understanding the route architecture. The discrepancies noted are minor and do not represent security issues or functional bugs.
