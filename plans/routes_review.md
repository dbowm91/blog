# Routes Module Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** admin-routes.md, api-routes.md, public-routes.md, rss-feeds.md
**Source Files:** app/routes/admin/, app/routes/api/, app/routes/public/, app/routes/rss.py, app/routes/errors.py

## Findings

### Verified Claims (Correct)

- All route paths and HTTP methods in `admin-routes.md` are accurate except for two discrepancies noted below (user password route, single revision route).
- Auth decorators on admin routes: all admin routes use `@admin_required` correctly; public routes use no auth; API routes use `@require_api_key`.
- `SESSION_IP_BINDING` enforcement via `admin_required` decorator in `app/routes/admin/__init__.py:27-55` confirmed (enforce/warn modes).
- `LOGIN_FAILURE_DELAY` applied after failed login at `app/routes/admin/auth.py:90` confirmed.
- Logout route uses `validate_csrf_token()` explicitly (line 107) alongside `@login_required`.
- Global CSRF protection: `before_request_handler()` in `app/__init__.py:296-298` calls `validate_csrf_token()` on every POST request, providing blanket CSRF protection for all form routes.
- API rate limits: 20/min reads, 10/min writes confirmed via `DEFAULT_LIMIT` and `WRITE_LIMIT` constants.
- Subscribe rate limit: 10/min confirmed.
- Comment rate limit: dual-layer (per-IP and per-post+IP) confirmed via `COMMENT_RATE_LIMIT_PER_IP` and `COMMENT_RATE_LIMIT_PER_POST` config values.
- All API routes in `api-routes.md` endpoints table (posts, subscribers, stats, pages, series, tags) match actual code.
- All RSS/Atom/JSON feed routes in `rss-feeds.md` match actual code.
- Feed caching timeout of 300 seconds (5 min) confirmed via `@flask_cache.cached(timeout=300, ...)`.
- ETag-based conditional GET support for all feeds confirmed.
- Backup management routes (create, download, restore, delete, verify, verify-all) all confirmed.
- Admin comment moderation routes (list, approve, delete) confirmed.
- Admin audit log route with pagination and action filtering confirmed.
- Admin series management (list, new, edit, delete, posts, reorder) confirmed.
- Admin page management (list, new, edit, delete) confirmed.
- Admin settings route (GET settings, POST settings/theme) confirmed.
- Admin analytics route with configurable `days` parameter confirmed.
- Admin newsletter routes (preview GET, test POST) confirmed.
- Admin media management (list, upload, delete) confirmed.
- Public preview route with HMAC token verification at `/preview/<int:post_id>` confirmed.
- Short URL redirect at `/s/<code>` with base62 decoding confirmed.
- Share tracking API at `/api/track-share` with platform validation confirmed.
- Token enumeration prevention on `/confirm/<token>` and `/unsubscribe/<token>` via `time.sleep(TOKEN_ENUMERATION_DELAY)` confirmed.
- SPA token for API authentication with HMAC comparison confirmed (`hmac.compare_digest`).
- Error handlers for 404, 500, 413 confirmed.

### Discrepancies (Doc vs Code)

- **`admin-routes.md:103`** -- Doc claims route `GET /admin/posts/<int:post_id>/revisions/<int:rev_id>` for viewing a single revision. No such route exists in code. The only revision detail route is `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore` (revisions.py:74). The only GET route is the list: `GET /admin/posts/<int:post_id>/revisions` (revisions.py:48).

- **`admin-routes.md:133`** -- Doc claims route `POST /admin/users/<int:user_id>/password`. Actual code has `POST /admin/users/password/<int:user_id>` (users.py:229). The path segments are swapped.

- **`admin-routes.md:143-146`** -- "Markdown Preview" section (`POST /admin/preview-markdown`) is placed under the "Session Monitoring (sessions.py)" heading, implying it is in `sessions.py`. It is actually implemented in `posts/editor.py:319`.

- **`public-routes.md:9`** -- Route table lists `/page/<page>` as a route in `browse.py`. No such route exists. The home page route is `GET /` only; pagination is via `?page=N` query parameter (browse.py:102), not a path segment.

- **`public-routes.md:18`** -- Detail section claims `GET /page/<int:page>` exists alongside `GET /` for home page pagination. No `/page/<int:page>` route exists. The index function at browse.py:98 is only `@public.route("/")`.

- **`public-routes.md:24`** -- Detail section claims `GET /tag/<slug>/<int:page>` for tag page pagination. No such route exists. The tag function at browse.py:233 is only `@public.route("/tag/<slug>")`; pagination uses `?page=N` query parameter.

- **`public-routes.md:106`** -- Doc says health check uses `?detailed=1` but code at meta.py:194 checks `request.args.get("detailed", "").lower() == "true"`, requiring the string "true", not "1".

- **`api-routes.md:291`** -- Doc claims auth returns 503 when `API_KEY` environment variable is not set. Code at auth.py:82-83 returns 401 with `{"error": "Invalid or missing API key"}` in all auth failure cases, regardless of whether `API_KEY` is set.

- **`api-routes.md:289-297`** -- Doc describes only the legacy `API_KEY` environment variable authentication mechanism. The actual code implements a two-tier system: (1) legacy `API_KEY` env var via `_verify_api_key()`, and (2) scoped `ApiToken` model via `_verify_token()` with hash-based lookup, `is_valid()` check, and `last_used_at` tracking. The `require_api_key` decorator tries legacy first, then falls back to scoped tokens.

- **`api-routes.md:309`** -- Doc claims "API key check: 1000/hour" rate limit. No such rate limit exists in code. The default limiter is "100 per minute" (app/__init__.py:54) applied globally when no per-route limit is set.

- **`public-routes.md:72-74`** -- Short URL redirect (`GET /s/<code>`) is documented under the "Comment Routes" section header, but it is defined in `posts.py`, not `comments.py`.

- **`rss-feeds.md:233`** -- Doc states "All feeds are cached for 5 minutes" which is correct for server-side Flask-Caching. However, the HTTP `Cache-Control` header is set to `max-age=3600` (1 hour) at rss.py:98. The doc should clarify the distinction between server-side cache TTL and client-side HTTP cache TTL.

### Missing Documentation

- **Global CSRF Protection Mechanism**: The architecture docs do not mention that CSRF is enforced globally via `before_request_handler()` in `app/__init__.py:296-298`. All POST requests are CSRF-validated automatically. This is a critical architectural detail that affects all routes.

- **Admin Helpers Module**: `admin-routes.md` module structure listing omits the `app/routes/admin/helpers/` directory which contains 9 submodules: `__init__.py`, `analytics.py`, `dashboard.py`, `images.py`, `posts.py`, `shared.py`, `slug.py`, `tags.py`. These provide shared utilities used across admin routes.

- **Scoped API Token System**: No documentation exists for the `ApiToken` model-based authentication, the `require_scope()` decorator, or the full list of scopes (`posts:read`, `posts:write`, `media:read`, `media:write`, `subscribers:read`, `subscribers:write`, `newsletter:send`, `analytics:read`, `tags:read`, `tags:write`, `pages:read`, `pages:write`, `series:read`, `series:write`, `admin:*`).

- **Error Handler Coverage**: `app/routes/errors.py` only handles 404, 500, and 413. No custom handlers exist for 403, 405, 429, or other status codes. Flask defaults are used. This is undocumented.

- **Archive Pagination**: The archive page uses cursor-based pagination (cursor, direction, year query params) rather than standard page-number pagination. This is not documented.

- **Comment Spam Scoring**: The comment submission system includes a spam heuristic scorer (`compute_spam_score`) with configurable spam words, link detection, and case analysis. Auto-quarantine threshold is 0.7. This is not documented.

- **Rate Limit Key Function Differences**: The global limiter in `app/__init__.py:45-49` uses the full `X-Forwarded-For` header value as the rate limit key, while `comments.py:24-32` properly splits by comma and takes the first IP. This inconsistency is undocumented.

- **Metrics Endpoint Rate Limiting**: `GET /metrics` has no `@limiter.limit()` decorator, unlike all other public meta routes which have "60 per minute". This could allow unbounded request rates.

- **Newsletter Test vs Preview Distinction**: The doc correctly lists both routes but does not explain the functional difference: preview renders HTML in-browser, while test sends an actual email.

- **Password Change Authorization**: `POST /admin/users/password/<int:user_id>` allows any admin to change any other user's password without confirmation (no current-password check). Only `make-owner` requires password confirmation. This security-sensitive behavior is undocumented.

### Potential Bugs / Concerns

- **RSS Cache Invalidation Incomplete** (`rss.py:103-105`): `invalidate_rss_cache()` only deletes the `"rss_feed_posts"` cache key. It does not invalidate `"atom_feed_posts"` or `"json_feed_posts"`. After a post is published/unpublished/deleted, the Atom and JSON feeds will serve stale content for up to 5 minutes. This is a functional bug.

- **Duplicate `_save_revision` Function**: The function `_save_revision(post, author_id)` is defined identically in three files: `posts/editor.py:36`, `posts/manage.py:34`, and `posts/revisions.py:32`. The import chain in `posts/__init__.py:38` imports from `revisions.py`. The copies in `editor.py` and `manage.py` are unused dead code that should be consolidated.

- **X-Forwarded-For Rate Limit Bypass** (`app/__init__.py:45-49`): The global `get_client_ip()` used as the default rate limit key returns the full `X-Forwarded-For` header value without sanitization. An attacker can send arbitrary `X-Forwarded-For` headers to create unique rate limit keys, bypassing the global "100 per minute" default limit. The `comments.py` implementation (line 28-30) correctly splits by comma and takes only the first IP, but the global limiter does not.

- **`_get_cached_feed_posts` Calls Atom Cache** (`rss.py:52-57`): `_get_cached_feed_posts()` is defined but delegates to `_get_cached_atom_posts()` rather than its own cache key. This function appears to be dead code (never called from any route handler), but it is misleading and could cause confusion.

- **Admin Route Missing `logger` Import Order** (`admin/__init__.py:50`): The `admin_required` decorator references `logger` (line 50) which is imported later at line 83 via `from app.routes.admin.helpers import logger`. This works at runtime because Python resolves global names at call time, but it is fragile and could break if the import is restructured.

- **Health Check Secret in Query Parameter** (`meta.py:195-197`): The `HEALTH_CHECK_SECRET` is passed as a `?secret=` query parameter, which may be logged in web server access logs, proxy logs, or browser history. A more secure approach would be an `Authorization` header.

- **Password Reset Token Logged** (`auth.py:246-250`): After a successful password reset, the code logs `user_id` and `username` via `logger.info("Password reset completed: user_id=%d username=%s", user.id, user.username)`. Logging the username is a PII concern per the codebase's own security rules (AGENTS.md says "Log ID, not Username").

- **Missing `try/except` in `delete_post`** (`manage.py:88`): `db.session.commit()` after `db.session.delete(post)` is not wrapped in `try/except (IntegrityError, OperationalError)`. If the delete fails at the database level, an unhandled exception will propagate.

- **Newsletter Reset Missing CSRF** (`auth.py:123-150`): The `newsletter_reset` route uses `@admin_required` but the global CSRF handler at `app/__init__.py:296-298` should cover it since it's a POST request. This is correct but the doc's claim of "CSRF protection required" for logout (and by implication other routes) could be more explicit about the global mechanism.

- **User Password Change Self-Service Gap**: `POST /admin/users/password/<int:user_id>` has no guard preventing an admin from changing another admin's password without their consent or a confirmation step. Only `make-owner` requires the current user's password.

### Improvement Suggestions

- **Fix `invalidate_rss_cache()`**: Add cache deletion for `"atom_feed_posts"` and `"json_feed_posts"` keys alongside `"rss_feed_posts"` to ensure all feed formats are refreshed when content changes.

- **Consolidate `_save_revision()`**: Remove the duplicate definitions from `editor.py` and `manage.py`. Import from `revisions.py` where needed (or move to a shared helper module like `app/routes/admin/helpers/posts.py`).

- **Fix global `get_client_ip()`**: Update `app/__init__.py:45-49` to split `X-Forwarded-For` by comma and return only the first IP (client IP), matching the approach in `comments.py:28-30`.

- **Document Global CSRF**: Add a section to `admin-routes.md` explaining that CSRF protection is applied globally to all POST requests via `before_request_handler()`, so individual route-level CSRF checks are redundant (though some routes like `logout`, `subscribe`, and `add_comment` have explicit checks as defense-in-depth).

- **Add Rate Limit to Metrics**: Add `@limiter.limit("60 per minute")` to the `metrics` route to match other meta routes.

- **Document Auth Tier System**: Update `api-routes.md` to describe both legacy API_KEY and scoped ApiToken authentication, including the full scope list and the `require_scope()` decorator.

- **Fix Route Table in public-routes.md**: Remove the phantom `/page/<page>` and `/tag/<tag>/<page>` entries from the route table since these routes do not exist in code.

- **Fix Health Check Query Param**: Change `?detailed=1` to `?detailed=true` in documentation to match actual code behavior, or update code to accept both.

- **Fix Password Route Path**: Update `admin-routes.md` to document the correct path: `POST /admin/users/password/<int:user_id>` (not `/users/<user_id>/password`).

- **Move Markdown Preview Section**: Relocate the "Markdown Preview" documentation from under "Session Monitoring" to under "Post Management" in `admin-routes.md`.

- **Add Password Change Safeguard**: Consider requiring the current admin's password (like `make-owner` does) before allowing password changes on other users, or at minimum log the action in the audit trail.

- **Avoid Logging Usernames**: In `auth.py:247`, change `username=%s` to remove the username from the log line to comply with the "Log ID, not Username" security rule.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Fix `invalidate_rss_cache()` to also clear `atom_feed_posts` and `json_feed_posts` cache keys | source |
| 2 | high | Fix global `get_client_ip()` to split X-Forwarded-For by comma and use first IP only | source |
| 3 | high | Document global CSRF protection mechanism in architecture docs | docs |
| 4 | high | Document scoped API token system (ApiToken, require_scope, full scope list) | docs |
| 5 | med | Fix user password route path in admin-routes.md: `/users/password/<user_id>` not `/users/<user_id>/password` | docs |
| 6 | med | Remove phantom routes `/page/<page>` and `/tag/<slug>/<page>` from public-routes.md | docs |
| 7 | med | Remove phantom route `/posts/<post_id>/revisions/<rev_id>` GET from admin-routes.md | docs |
| 8 | med | Fix health check `?detailed=1` to `?detailed=true` in public-routes.md | docs |
| 9 | med | Move "Markdown Preview" section from under "Session Monitoring" to "Post Management" in admin-routes.md | docs |
| 10 | med | Add `@limiter.limit("60 per minute")` to `GET /metrics` route | source |
| 11 | med | Consolidate three duplicate `_save_revision()` functions into single definition | source |
| 12 | med | Fix `api-routes.md` auth section: 401 not 503 when API_KEY unset; describe two-tier auth | docs |
| 13 | med | Remove "API key check: 1000/hour" claim from api-routes.md rate limits table (does not exist) | docs |
| 14 | med | Document the `helpers/` directory in admin-routes.md module structure | docs |
| 15 | med | Clarify RSS cache doc: server-side 5 min vs HTTP Cache-Control 1 hour | docs |
| 16 | low | Remove username from password reset log line (auth.py:247) for PII compliance | source |
| 17 | low | Add `try/except` around `db.session.commit()` in `manage.py:88` (delete_post) | source |
| 18 | low | Move short URL redirect documentation out of "Comment Routes" section to "Post Routes" | docs |
| 19 | low | Add `try/except` guard on `db.session.commit()` in `subscribe.py:74,82,114,143` where not already wrapped | source |
| 20 | low | Document archive cursor-based pagination parameters in public-routes.md | docs |
| 21 | low | Document comment spam scoring system (thresholds, heuristics, auto-quarantine) | docs |
| 22 | low | Remove dead code `_get_cached_feed_posts()` from rss.py (misleading, delegates to atom cache) | source |
