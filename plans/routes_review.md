# Routes Architecture Review

**Reviewed:** 2026-05-29
**Architecture Docs:** admin-routes.md, api-routes.md, public-routes.md, rss-feeds.md
**Source Files:** app/routes/admin/, app/routes/api/, app/routes/public/, app/routes/rss.py, app/routes/errors.py

## Findings

### Verified Claims (Correct)

**Admin Routes:**
- Login: `GET/POST /admin/login` (auth.py:32)
- Logout: `POST /admin/logout` with CSRF protection (auth.py:97)
- 2FA routes: setup, verify, login-2fa, backup-codes, disable (auth.py:257,306,343,414,430)
- Forgot/Reset password routes (auth.py:153,194)
- Newsletter reset: `POST /admin/newsletter-reset/<int:post_id>` (auth.py:123)
- Dashboard: `GET /admin/` with bulk operations `POST /admin/bulk` (posts/__init__.py:51,116)
- Post editor: `GET/POST /admin/new`, `GET/POST /admin/edit/<int:post_id>` (editor.py:138,213)
- Post delete: `POST /admin/delete/<int:post_id>` (manage.py:71)
- Post preview: `GET /admin/preview/<int:post_id>` (manage.py:96)
- Post revisions routes (revisions.py:48,74)
- Markdown preview: `POST /admin/preview-markdown` (editor.py:319)
- Subscribers: list, export, bulk, delete routes (subscribers.py:17,55,82,120)
- Tags: list, create, rename, delete routes (tags.py:14,37,82,110)
- Users: list, create, delete, promote, demote, make-owner, password routes (users.py:16,38,84,116,146,181,229)
- Sessions: list, revoke routes (sessions.py:15,43)
- Media: list, upload, delete routes (media.py:100,137,167)
- Backup: list, create, download, restore, delete, verify, verify-all routes (backup.py:20,50,81,104,169,197,225)
- Analytics: `GET /admin/analytics` (analytics.py:10)
- Newsletter: preview and test routes (newsletter.py:24,65)
- Settings: view and theme update routes (settings.py:13,40)
- Audit log: `GET /admin/audit` (audit.py:13)
- Pages: CRUD routes (pages.py:14,28,98,175)
- Series: full CRUD plus posts management and reorder (series.py:22,39,83,128,151,250)
- Comments: list, approve, delete routes (comments.py:15,61,82)

**Public Routes:**
- Home page: `GET /` and `GET /page/<int:page>` (browse.py:98)
- Tag pages: `GET /tag/<slug>` and `GET /tag/<slug>/<int:page>` (browse.py:233)
- Search: `GET /search` with `q` param (browse.py:262)
- Archive: `GET /archive` (browse.py:123)
- Series: `GET /series/<slug>` (browse.py:326)
- Static page: `GET /page/<slug>` (browse.py:220)
- Post view: `GET /post/<slug>` (posts.py:46)
- Preview: `GET /preview/<int:post_id>?token=<hmac>&expires=<timestamp>` (posts.py:101)
- Comment submission: `POST /post/<slug>/comment` with CSRF (comments.py:77)
- Short URL: `GET /s/<code>` (posts.py:155)
- Share tracking: `POST /api/track-share` (posts.py:178)
- Subscribe: `POST /subscribe` only (subscribe.py:55)
- Confirm: `GET /confirm/<token>` (subscribe.py:117)
- Unsubscribe: `GET /unsubscribe/<token>` (subscribe.py:158)
- Sitemap: `GET /sitemap.xml` (meta.py:174)
- Robots.txt: `GET /robots.txt` (meta.py:92)
- Health: `GET /health` with optional `?detailed=true` (meta.py:188)
- Metrics: `GET /metrics` (meta.py:323)
- Favicon: `GET /favicon.ico` redirects to SVG (meta.py:180)

**API Routes:**
- Posts API: full CRUD at `/api/posts` and `/api/posts/<id>` (posts.py:46,87,111,213,320)
- Subscribers API: list, create, delete at `/api/subscribers` and `/api/subscribers/<id>` (subscribers.py:33,70,123)
- Stats API: `GET /api/stats` (stats.py:17)
- Pages API: full CRUD with scope requirements (pages.py:35,66,83,161,223)
- Series API: full CRUD plus posts management and reorder (series.py:45,71,93,157,217,247,320,351)
- Tags API: full CRUD with scope requirements (tags.py:35,61,78,134,193)
- Authentication: `X-API-Key` header with HMAC comparison (auth.py:75)
- Scope decorator for additional authorization (auth.py:91)

**RSS/Feeds:**
- Main feeds: `/rss`, `/atom`, `/json` (rss.py:564,481,614)
- Cache timeout: 300 seconds (5 minutes) - all cached feeds use timeout=300
- ETag and conditional GET support (rss.py:95-100)

**Error Handlers:**
- 404, 500, 413 handlers in errors.py (errors.py:37,49,62)

### Discrepancies (Doc vs Code)

1. **admin-routes.md:79-84 - Post Editor Features Not Documented**
   - Doc claims editor has "Markdown editor, tag selection, image upload, series assignment"
   - Code: These features exist but the doc doesn't mention `/admin/new` handles both GET (render form) and POST (process form). Same for `/admin/edit/<int:post_id>`.

2. **admin-routes.md:85 - Post Delete Location**
   - Doc says "(posts/manage.py)"
   - Code: `manage.py` does contain delete, but `posts/__init__.py` imports it via `register_manage_routes`. The doc is technically correct but implies `posts/manage.py` is a standalone route file when it's actually imported.

3. **admin-routes.md:143-145 - Markdown Preview Location**
   - Doc places markdown preview under "Session Monitoring"
   - Code: `preview_markdown` is in `posts/editor.py`, not `sessions.py`. Misleading organization.

4. **admin-routes.md:202-208 - Series Route Methods**
   - Doc says: "GET /admin/series/new (POST to create)"
   - Code: `series.py:39` shows `@admin.route("/series/new", methods=["GET", "POST"])` - both methods on same route. Doc's phrasing could be clearer.

5. **api-routes.md:301-309 - Rate Limit Table Discrepancy**
   - Doc says: "Authenticated reads | 20/min | GET /api/posts, GET /api/subscribers, GET /api/stats"
   - Doc also says: "Authenticated writes | 10/min | POST, PUT, DELETE operations"
   - Code: `DEFAULT_LIMIT = "20 per minute"` and `WRITE_LIMIT = "10 per minute"` in posts.py:18-19 and subscribers.py:15-16. The docs are **correct** for posts and subscribers, but pages, series, and tags don't have documented rate limits.

6. **api-routes.md:88-99 - Subscriber Export Not in API**
   - Doc says "Subscriber export is only available in admin routes, not the public API. See `/admin/subscribers/export`"
   - Code: Confirmed - admin/subscribers.py:82 has `export_subscribers` but no equivalent in api/subscribers.py. This is correctly documented.

7. **rss-feeds.md:1 - Module Location**
   - Doc says "RSS/Feeds (`app/routes/rss.py`)"
   - Code: Confirmed at `app/routes/rss.py`. Correct.

8. **rss-feeds.md - Missing Tag and Series Feeds**
   - Doc only documents main feeds: `/rss`, `/atom`, `/json`
   - Code: Also has tag-specific feeds (`/tag/<slug>/rss`, `/tag/<slug>/atom`, `/tag/<slug>/json`) and series-specific feeds (`/series/<slug>/rss`, `/series/<slug>/atom`, `/series/<slug>/json`). These are undocumented.

9. **rss-feeds.md:80-82 - Caching Documentation**
   - Doc says: "All feeds are cached for 5 minutes"
   - Code: Uses `@flask_cache.cached(timeout=300, key_prefix="...")` - 300 seconds = 5 minutes. Correct.

### Missing Documentation

1. **API Rate Limits for Pages, Series, Tags**
   - These endpoints have `DEFAULT_LIMIT` and `WRITE_LIMIT` but docs only mention rate limits for posts and subscribers.

2. **Tag and Series RSS/Atom/JSON Feeds**
   - Undocumented feeds at `/tag/<slug>/{rss,atom,json}` and `/series/<slug>/{rss,atom,json}`.

3. **Webhook Events Triggered by API**
   - `PUT /api/posts/<id>` triggers `post.published` or `post.unpublished` events (documented in api-routes.md:27-29)
   - Subscriber confirmation via `/confirm/<token>` triggers `subscriber.confirmed` (documented correctly)
   - But webhook delivery architecture (two-level dispatch pattern mentioned in AGENTS.md) is not documented in routes docs.

4. **API Error Responses**
   - No documentation of error response formats (401 for invalid API key, 403 for missing scope, 404 for not found, 409 for conflicts, 429 for rate limiting, 503 for FTS unavailable).

5. **Request/Response Examples for API**
   - Limited examples in api-routes.md. Series reorder endpoint has no example.
   - Tags API update request body not documented.

6. **Public Preview Route Authentication**
   - `GET /preview/<int:post_id>?token=<hmac>&expires=<timestamp>` uses HMAC token auth but no rate limit documented.

7. **CSRF Protection Scope**
   - No documentation of which routes require CSRF tokens (all POST/PUT/DELETE admin routes, public comment submission, public subscribe).

8. **Session Fixation Protection**
   - `login()` at auth.py:70 calls `session.clear()` before `login_user()` with comment "SEC-7: Session Fixation Protection" but not documented.

9. **IP Binding for Sessions**
   - Admin sessions have IP binding (admin/__init__.py:27-55) but docs don't explain this security feature.

10. **Backup Encryption Details**
    - Admin backup routes mention "AES-256-GCM encryption" but don't explain when/why encryption is used.

### Potential Bugs / Concerns

1. **No GET Handler for /subscribe (public-routes.md:84)**
   - The doc states "no GET handler exists" - this is intentional to prevent form display, but could confuse users who navigate directly. Not a bug but worth noting.

2. **Rate Limit Key Functions in Comments (comments.py:35-38)**
   - `get_per_post_comment_key` uses `request.view_args.get("slug")` but the route is `/post/<slug>/comment`. If `slug` is missing from view_args for any reason, rate limiting would use "unknown" as key, potentially allowing bypass.

3. **Health Check /metrics Without Auth (meta.py:323)**
   - `/metrics` endpoint has no authentication and returns database health status, disk space, and scheduler status. While it doesn't expose sensitive data, exposing infrastructure health publicly may be undesirable.

4. **Comments Rate Limit Uses Client IP (comments.py:78-79)**
   - `get_client_ip()` function checks `X-Forwarded-For` header. If behind a trusted proxy that doesn't sanitize this header, rate limiting could be bypassed.

5. **Login Failure Delay Timing (auth.py:90)**
   - `time.sleep(LOGIN_FAILURE_DELAY)` is called after invalid credentials. If `LOGIN_FAILURE_DELAY` is 0, there's no delay between failed attempts making brute force easier.

6. **Preview Token Expiry Not Validated Against Post (posts.py:101-133)**
   - Preview token validates expiration time and HMAC signature, but doesn't check if the post was unpublished/deleted after token generation. Token could theoretically access deleted content until expiry.

7. **Series Feed Shows Unpublished Posts (rss.py:154)**
   - `_get_series_posts` filters: `sp.post.published` - only published posts included. CORRECT behavior but not obviously documented.

### Improvement Suggestions

1. **Add Tag and Series Feed Documentation**
   - Document the undocumented `/tag/<slug>/{rss,atom,json}` and `/series/<slug>/{rss,atom,json}` feeds.

2. **Clarify Series Route Methods**
   - Change "GET /admin/series/new (POST to create)" to "GET/POST /admin/series/new" to match actual decorator syntax.

3. **Document API Error Response Codes**
   - Add section on standard error responses: 400, 401, 403, 404, 409, 429, 503.

4. **Add Request/Response Examples for Series Reorder**
   - The API docs show reorder endpoint but lack JSON body example.

5. **Document CSRF Protection Scope**
   - Add section listing all routes requiring CSRF tokens.

6. **Separate Markdown Preview to Own Section**
   - Move `/admin/preview-markdown` from "Session Monitoring" to its own "Markdown Editor" section under Post Management.

7. **Document Rate Limits for All API Endpoints**
   - Pages, series, and tags API endpoints have rate limits but aren't documented.

8. **Add Security Considerations Section**
   - Document IP binding, session fixation protection, rate limiting approach, and token enumeration delays.

9. **Document Webhook Event Types**
   - Add full list of webhook event types triggered by various routes.

10. **Improve Backup Route Documentation**
    - Clarify when encryption is available (requires BACKUP_ENCRYPTION_KEY env var).

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | high | Document tag and series RSS/Atom/JSON feeds | docs |
| 2 | high | Document rate limits for pages, series, tags API endpoints | docs |
| 3 | high | Add API error response documentation | docs |
| 4 | medium | Clarify series route methods in admin-routes.md | docs |
| 5 | medium | Move markdown preview from "Session Monitoring" section | docs |
| 6 | medium | Add request/response examples for series reorder API | docs |
| 7 | medium | Document CSRF protection scope for all routes | docs |
| 8 | low | Add security considerations section (IP binding, session fixation) | docs |
| 9 | low | Verify LOGIN_FAILURE_DELAY configuration is properly set | source |
| 10 | low | Consider adding auth to /metrics endpoint | source |
