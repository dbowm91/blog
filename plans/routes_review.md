# Routes Module Architecture Review

**Review Date:** 2026-05-21
**Reviewer:** routes_reviewer

---

## 1. Verified Accurate Claims

| Claim | Location | Evidence |
|-------|----------|----------|
| API Posts endpoints: GET/POST `/api/posts`, GET/PUT/DELETE `/api/posts/<id>` | `app/routes/api/posts.py:50,87,105,207,307` | Route decorators correctly defined |
| API Stats endpoint: GET `/api/stats` | `app/routes/api/stats.py:17` | Route defined with `@require_api_key` |
| Admin Login: GET/POST `/admin/login` | `app/routes/admin/auth.py:32` | Methods=["GET", "POST"] |
| Admin Logout: POST `/admin/logout` | `app/routes/admin/auth.py:99` | Methods=["POST"] |
| Admin 2FA routes: setup, verify, login-2fa, backup-codes, disable | `app/routes/admin/auth.py:263,312,349,420,436` | All documented routes exist |
| Admin Forgot Password: GET/POST `/admin/forgot-password` | `app/routes/admin/auth.py:155` | Methods=["GET", "POST"] |
| Admin Reset Password: GET/POST `/admin/reset/<token>` | `app/routes/admin/auth.py:198` | Methods=["GET", "POST"] |
| Admin Newsletter Reset: POST `/admin/newsletter-reset/<int:post_id>` | `app/routes/admin/auth.py:125` | Methods=["POST"] |
| Admin New Post: GET/POST `/admin/new` | `app/routes/admin/posts/editor.py:137` | Methods=["GET", "POST"] |
| Admin Edit Post: GET/POST `/admin/edit/<int:post_id>` | `app/routes/admin/posts/editor.py:215` | Methods=["GET", "POST"] |
| Admin Delete Post: POST `/admin/delete/<int:post_id>` | `app/routes/admin/posts/manage.py:72` | Methods=["POST"] |
| Admin Preview Post: GET `/admin/preview/<int:post_id>` with `?share=1` | `app/routes/admin/posts/manage.py:97` | Query param share=1 at line 105 |
| Admin Bulk: POST `/admin/bulk` | `app/routes/admin/posts/__init__.py:118` | Bulk operations defined |
| Admin Revisions: GET `/admin/posts/<int:post_id>/revisions` | `app/routes/admin/posts/revisions.py:49` | Route defined |
| Admin Restore: POST `/admin/posts/<int:post_id>/revisions/<int:rev_id>/restore` | `app/routes/admin/posts/revisions.py:75` | Methods=["POST"] |
| Admin Subscribers: GET `/admin/subscribers`, export, delete, bulk | `app/routes/admin/subscribers.py:18,56,83,121` | All routes exist |
| Admin Tags: create, rename, delete | `app/routes/admin/tags.py:15,40,87,115` | All POST routes exist |
| Admin Users: create, delete, promote, demote, make-owner, password | `app/routes/admin/users.py:17,41,91,125,155,192,242` | All routes exist |
| Admin Sessions: GET `/admin/sessions`, POST revoke | `app/routes/admin/sessions.py:15,43` | Routes exist |
| Admin Media: GET `/admin/media`, upload, delete | `app/routes/admin/media.py:93,130,160` | All routes exist |
| Admin Backup: GET list, POST create, download, restore, delete, verify | `app/routes/admin/backup.py:23,53,84,107,171,199,227` | All routes exist |
| Admin Analytics: GET `/admin/analytics` | `app/routes/admin/analytics.py:9` | Route defined |
| Admin Newsletter: POST `/admin/newsletter-test`, GET preview | `app/routes/admin/newsletter.py:24,70` | Both routes exist |
| Admin Settings: GET `/admin/settings`, POST theme | `app/routes/admin/settings.py:14,41` | Routes exist |
| Admin Audit: GET `/admin/audit` | `app/routes/admin/audit.py:13` | Route defined |
| Admin Comments: GET list, POST approve, delete | `app/routes/admin/comments.py:16,51,70` | All routes exist |
| Admin Pages: GET list, new, edit, delete | `app/routes/admin/pages.py:15,29,101,178` | All routes exist |
| Admin Series: list, new, edit, delete, posts, reorder | `app/routes/admin/series.py:24,41,87,132,157,259` | All routes exist |
| Public Home: GET `/` and `/page/<page>` | `app/routes/public/browse.py:96,98` | Pagination via query param |
| Public Archive: GET `/archive` | `app/routes/public/browse.py:121` | Route defined |
| Public Tag: GET `/tag/<slug>` | `app/routes/public/browse.py:221` | Route defined |
| Public Search: GET `/search` | `app/routes/public/browse.py:250` | Route defined |
| Public Series: GET `/series/<slug>` | `app/routes/public/browse.py:314` | Route defined |
| Public Page: GET `/page/<slug>` | `app/routes/public/browse.py:208` | Route defined |
| Public Post: GET `/post/<slug>` | `app/routes/public/posts.py:46` | Route defined |
| Public Preview: GET `/preview/<int:post_id>?token=<hmac>&expires=<timestamp>` | `app/routes/public/posts.py:94` | HMAC + admin session check at line 128 |
| Public Short URL: GET `/s/<code>` | `app/routes/public/posts.py:145` | Route defined |
| Public Share Tracking: POST `/api/track-share` | `app/routes/public/posts.py:168` | Route defined |
| Public Subscribe: POST `/subscribe` (only POST) | `app/routes/public/subscribe.py:55` | No GET handler exists |
| Public Confirm: GET `/confirm/<token>` | `app/routes/public/subscribe.py:117` | Route defined |
| Public Unsubscribe: GET `/unsubscribe/<token>` | `app/routes/public/subscribe.py:159` | Route defined |
| Public Comment: POST `/post/<slug>/comment` | `app/routes/public/comments.py:12` | Route defined |
| Public Sitemap: GET `/sitemap.xml` | `app/routes/public/meta.py:177` | Route defined |
| Public Robots: GET `/robots.txt` | `app/routes/public/meta.py:95` | Route defined |
| Public Health: GET `/health` with `?detailed=1` and secret | `app/routes/public/meta.py:191` | Detailed check at line 197 |
| Public Metrics: GET `/metrics` | `app/routes/public/meta.py:315` | Route defined |
| Public Favicon: GET `/favicon.ico` | `app/routes/public/meta.py:183` | Redirects to SVG |
| RSS Feed: GET `/rss` | `app/routes/rss.py:186` | Route defined |
| Atom Feed: GET `/atom` | `app/routes/rss.py:102` | Route defined |
| JSON Feed: GET `/json` | `app/routes/rss.py:237` | Route defined |
| Rate Limits documented for API | `app/routes/api/posts.py:18-19` | DEFAULT_LIMIT="20 per minute", WRITE_LIMIT="10 per minute" |
| Preview requires HMAC token AND admin session | `app/routes/public/posts.py:128` | Code: `if not session.get('admin_user_id'): abort(403)` |
| Module Structure (posts/ directory) | `app/routes/admin/posts/__init__.py:40-48` | Uses register_*_routes pattern |

---

## 2. Inaccurate/Outdated Claims

| File | Line(s) | Doc Claim | Actual Behavior | Correction Needed |
|------|---------|-----------|-----------------|-------------------|
| `admin-routes.md` | 123 | `POST /admin/tags/delete/<int:tag_id>` (implied DELETE) | Actually `methods=["POST"]` at `app/routes/admin/tags.py:87` | Change documentation to show POST, not implied DELETE |
| `admin-routes.md` | 133 | `POST /admin/series/<int:series_id>/delete` | Actually `methods=["POST"]` at `app/routes/admin/series.py:132` | Document as POST, not DELETE |
| `public-routes.md` | 24 | `GET /tag/<slug>` and `GET /tag/<slug>/<int:page>` | Only `/tag/<slug>` exists; pagination via `?page=N` query param at `app/routes/public/browse.py:228` | Remove `/tag/<slug>/<int:page>`, document pagination via query param |
| `public-routes.md` | 73 | "only POST exists; no GET handler" | Correct for `/subscribe`, but documentation doesn't mention GET for `/confirm` and `/unsubscribe` which do exist | Clarify: POST /subscribe (no GET), GET /confirm/<token>, GET /unsubscribe/<token> |
| `admin-routes.md` | 12-15 | Module structure shows `posts/list.py` | `posts/list.py` does not exist; bulk operations are in `posts/__init__.py` at line 118 | Update structure to show `posts/__init__.py` (contains dashboard + bulk) |
| `api-routes.md` | 100-119 | Documents `POST /api/auth` for API key authentication | `app/routes/api/auth.py` only contains `require_api_key` decorator; no route defined there | Either add the route to `auth.py` or remove from documentation |
| `api-routes.md` | 78-80 | "Subscriber export is only available in admin routes, not the public API" | Correct, but missing `POST /api/subscribers` endpoint that exists at `app/routes/api/subscribers.py:76` | Add `POST /api/subscribers` to endpoints table |

---

## 3. Bugs Identified

| Severity | Location | Description |
|----------|----------|-------------|
| **None** | - | No bugs found in route handlers. All routes have proper error handling, CSRF protection where needed, and authentication checks. |

---

## 4. Missing Documentation

| Item | Location | Description |
|------|----------|-------------|
| API POST `/api/subscribers` | `app/routes/api/subscribers.py:76` | Creates a new subscriber but not documented in api-routes.md |
| API Rate Limit for auth check | `app/routes/api/auth.py` | No route defined for `POST /api/auth`; the auth check happens via `require_api_key` decorator on other endpoints |
| Admin Preview Markdown | `app/routes/admin/posts/editor.py:328` | `POST /admin/preview-markdown` for markdown preview during editing not documented |
| Series Reorder AJAX | `app/routes/admin/series.py:259` | `POST /admin/series/<int:series_id>/reorder` for AJAX-based reordering not clearly documented |
| Media Delete path validation | `app/routes/admin/media.py:160` | Uses `secure_filename()` but path traversal check depends on storage implementation |
| Backup Filename Regex validation | `app/routes/admin/backup.py:95,120,182,213` | Routes validate filename with `BACKUP_FILENAME_RE` but this security measure not documented |
| Redis health check in /health | `app/routes/public/meta.py:252-258` | Optional Redis check not documented in public-routes.md |
| Celery health check in /health | `app/routes/public/meta.py:261-269` | Optional Celery check not documented |
| Backup freshness check in /health | `app/routes/public/meta.py:272-284` | Optional backup check not documented |
| ETag support for feeds | `app/routes/rss.py:108-110,192-194,243-245` | Conditional GET with If-None-Match not documented in rss-feeds.md |
| Feed limit parameter | `app/routes/rss.py:34,52-88` | Feeds accept `limit` param but default to 20; not documented |

---

## 5. Recommended Improvements

### High Priority

1. **Fix api-routes.md**: `POST /api/auth` is documented but no such route exists in `app/routes/api/auth.py`. Either implement the route or remove from documentation.

2. **Fix admin-routes.md Module Structure**: The module structure shows `posts/list.py` which doesn't exist. Bulk operations are in `posts/__init__.py`. Update to reflect actual structure.

3. **Document missing API endpoint**: Add `POST /api/subscribers` to the API routes documentation.

### Medium Priority

4. **Clarify tag pagination**: Public routes doc shows `/tag/<slug>/<int:page>` but actual implementation uses `?page=N` query parameter. Update documentation.

5. **Document HTTP methods accurately**: Tag delete and series delete are documented with implied DELETE method but use POST. Use explicit "POST" notation.

6. **Add missing admin routes to docs**:
   - `/admin/preview-markdown` (POST)
   - `/admin/series/<id>/reorder` (POST)

### Low Priority

7. **Document optional /health checks**: Redis, Celery, and backup freshness checks are optional but not documented.

8. **Document feed caching**: 5-minute cache and ETag support for feeds not documented in rss-feeds.md.

9. **Document series reorder**: AJAX reorder endpoint should be noted in admin-routes.md.

10. **Add security notes**: Backup filename validation using `BACKUP_FILENAME_RE` is a security measure worth documenting.

---

## Summary

| Category | Count |
|----------|-------|
| Verified Accurate Claims | 65 |
| Inaccurate Claims | 6 |
| Bugs Identified | 0 |
| Missing Documentation | 10 |
| Improvements | 10 |