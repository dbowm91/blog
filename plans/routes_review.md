# Routes Module Architecture Review

**Reviewed:** May 29, 2026
**Architecture Docs:** admin-routes.md, api-routes.md, public-routes.md, rss-feeds.md
**Source Files:** app/routes/admin/, app/routes/api/, app/routes/public/, app/routes/rss.py, app/routes/errors.py

## Findings

### Verified Claims (Correct)

- Admin module structure matches doc: all 15 files accounted for (`admin-routes.md:7-27`)
- Auth routes: login GET/POST, logout POST, 2FA setup/verify/login-2fa/backup-codes/disable, forgot-password, reset-password, newsletter-reset — all correct (`auth.py`)
- Post editor routes: GET /admin/new, GET /admin/edit/<int:post_id> — correct (`editor.py:138,213`)
- Post revisions: GET list, GET detail, POST restore — correct (`revisions.py:48,74`)
- Subscriber routes: GET list, GET export, POST bulk, POST delete — correct (`subscribers.py:17,82,120,55`)
- Tag routes: GET list, POST create, POST rename, POST delete — correct (`tags.py:14,110,37,82`)
- User routes: GET list, POST create/delete/promote/demote/make-owner/password — correct (`users.py`)
- Session routes: GET list, POST revoke — correct (`sessions.py:15,43`)
- Media routes: GET list, POST upload, POST delete — correct (`media.py:100,137,167`)
- Backup routes: GET list, POST create, GET download, POST restore, POST delete, GET verify, GET verify-all — correct (`backup.py`)
- Analytics: GET /admin/analytics — correct (`analytics.py:10`)
- Newsletter: POST /admin/newsletter-test, GET /admin/newsletter/preview — correct (`newsletter.py:24,65`)
- Settings: GET /admin/settings, POST /admin/settings/theme — correct (`settings.py:13,40`)
- Audit log: GET /admin/audit — correct (`audit.py:13`)
- Pages: GET list, GET/POST new, GET/POST edit, POST delete — correct (`pages.py`)
- Series: GET list, GET/POST new, GET/POST edit, POST delete, GET/POST posts, POST reorder — correct (`series.py`)
- Comments moderation: GET list, POST approve, POST delete — correct (`comments.py`)
- Preview markdown: POST /admin/preview-markdown — correct (`editor.py:319`)
- API auth: require_api_key decorator with HMAC comparison, X-API-Key header, 401 on failure — correct (`api/auth.py:75-88`)
- API rate limits: 20/min reads, 10/min writes — correct (`api/posts.py:18-19`, `api/subscribers.py:15-16`, `api/stats.py:14`)
- API posts: GET list, GET single, POST create, PUT update, DELETE — correct (`api/posts.py`)
- API subscribers: GET list, POST create, DELETE — correct (`api/subscribers.py`)
- API stats: GET — correct (`api/stats.py`)
- Webhook events: post.published, post.unpublished, subscriber.confirmed — correct (`api/posts.py:304-315`, `public/subscribe.py:144-154`)
- Public browse routes: /, /page/<page>, /tag/<slug>, /archive, /series/<slug>, /page/<slug>, /search — correct (`browse.py`)
- Public post routes: /post/<slug>, /preview/<int:post_id> with HMAC token, /s/<code>, /api/track-share — correct (`posts.py`)
- Comment submission: POST /post/<slug>/comment with CSRF, spam scoring — correct (`comments.py`)
- Subscribe routes: POST /subscribe, GET /confirm/<token>, GET /unsubscribe/<token> — correct (`subscribe.py`)
- Meta routes: /sitemap.xml, /robots.txt, /health, /metrics, /favicon.ico — correct (`meta.py`)
- RSS feeds: /rss, /atom, /json with 5-minute caching — correct (`rss.py`)
- Errors blueprint: 404, 500, 413 handlers — correct (`errors.py`)

### Discrepancies (Doc vs Code)

1. **Post list route path is wrong** — Doc says `GET /admin/<int:page>` (`admin-routes.md:96`) but actual route is `GET /admin/` with `page` as a query parameter (`posts/__init__.py:51`). The `<int:page>` path parameter does not exist.

2. **Backup route URLs have trailing slashes in doc but not in code** — Doc shows `/admin/backup/restore/`, `/admin/backup/download/`, `/admin/backup/delete/`, `/admin/backup/verify/` with trailing slashes (`admin-routes.md:160-163`) but actual routes have `<filename>` path parameters: `/backup/restore/<filename>`, `/backup/download/<filename>`, `/backup/delete/<filename>`, `/backup/verify/<filename>` (`backup.py:104,81,169,197`).

3. **Post delete and preview reference wrong file** — Doc says `manage.py` (`admin-routes.md:85,89`) but the actual file is `posts/manage.py`. The functions are registered via `register_manage_routes()` in `posts/__init__.py:47`.

4. **Doc says `POST /admin/newsletter-test` and `GET /admin/newsletter/preview`** (`admin-routes.md:177-178`) — The actual function names are `newsletter_test` (POST) and `newsletter_preview` (GET). The doc is correct on methods but says "Preview and send newsletters" as purpose, which is vague. The actual purpose is: test sends to a specific email, preview renders HTML template.

5. **Doc says health check uses `?detailed=1`** (`public-routes.md:106`) but actual code checks for `detailed=true` (lowercase string comparison) (`meta.py:194`). The parameter is `request.args.get("detailed", "").lower() == "true"`.

6. **Doc says health check uses `HEALTH_CHECK_SECRET`** (`public-routes.md:107`) — Correct, but the doc says "Optional secret via `HEALTH_CHECK_SECRET`" without noting that detailed mode requires the secret to match via HMAC comparison (`meta.py:197`).

7. **Doc says `/page/<int:page>` for home pagination** (`public-routes.md:9`) — Actual route is `GET /page/<page>` where `page` is not typed as int in the route decorator; the int conversion happens via `request.args.get("page", 1, type=int)` inside the function. The route parameter is just `<page>` but since there's no `index_page` route with a page parameter (the index route is just `/`), this is misleading. The actual pagination uses query parameters.

### Missing Documentation

1. **API tags endpoints entirely undocumented** — `api/tags.py` provides: GET /api/tags, GET /api/tags/<id>, POST /api/tags, PUT /api/tags/<id>, DELETE /api/tags/<id>. Uses `require_scope("tags:read")` and `require_scope("tags:write")` decorators. Not mentioned in `api-routes.md` at all.

2. **API pages endpoints entirely undocumented** — `api/pages.py` provides: GET /api/pages, GET /api/pages/<id>, POST /api/pages, PUT /api/pages/<id>, DELETE /api/pages/<id>. Uses `require_scope("pages:read")` and `require_scope("pages:write")`. Not mentioned in `api-routes.md`.

3. **API series endpoints entirely undocumented** — `api/series.py` provides: GET /api/series, GET /api/series/<id>, POST /api/series, PUT /api/series/<id>, DELETE /api/series/<id>, POST /api/series/<id>/posts, DELETE /api/series/<id>/posts/<post_id>, POST /api/series/<id>/reorder. Uses `require_scope("series:read")` and `require_scope("series:write")`. Not mentioned in `api-routes.md`.

4. **Scoped token auth system undocumented** — `api/auth.py` implements a full scoped token system with `ApiToken` model, `require_scope()` decorator, and 14 defined scopes (`posts:read`, `posts:write`, `media:read`, `media:write`, `subscribers:read`, `subscribers:write`, `newsletter:send`, `analytics:read`, `tags:read`, `tags:write`, `pages:read`, `pages:write`, `series:read`, `series:write`, `admin:*`). `api-routes.md` only documents the legacy `API_KEY` env var approach.

5. **RSS tag-specific and series-specific feeds undocumented** — `rss.py` provides 6 additional feed endpoints not mentioned in `rss-feeds.md`: `/tag/<slug>/atom`, `/tag/<slug>/rss`, `/tag/<slug>/json`, `/series/<slug>/atom`, `/series/<slug>/rss`, `/series/<slug>/json`.

6. **Admin preview-markdown route not in module structure** — `admin-routes.md:7-27` module structure doesn't list the markdown preview functionality. The route exists in `editor.py:319`.

7. **Error handlers blueprint not documented** — `app/routes/errors.py` defines a blueprint with app-level error handlers for 404, 500, and 413. Not mentioned in any architecture doc.

8. **Admin login rate limiting not documented** — `auth.py:33` applies `@limiter.limit("5 per minute")` to the login route. `admin-routes.md` doesn't mention rate limits for admin routes.

9. **Admin forgot-password and login-2fa rate limiting not documented** — `auth.py:154,344` apply `@limiter.limit("5 per minute")` to these routes.

10. **Public route rate limits not documented** — Browse routes have rate limits (60/min for index, 30/min for archive, 20/min for search, etc.) defined in `browse.py` and `posts.py`. `public-routes.md` doesn't mention any rate limits.

11. **API auth.py not listed in architecture doc endpoints table** — `api-routes.md:7-13` table doesn't include `auth.py` as a file, even though it provides the `require_api_key` decorator and token generation utilities.

### Potential Bugs / Concerns

1. **Dead code in rss.py** — Lines 201, 306, 354, 459, 640 have standalone expressions like `utc_now().isoformat() + "Z"` that compute a value but never assign or use it. These are no-ops (e.g., `rss.py:201`, `rss.py:306`, `rss.py:354`, `rss.py:459`, `rss.py:640`). Not a bug but wasteful and confusing.

2. **`_save_revision` duplicated in 3 files** — The function `_save_revision(post, author_id)` is identically defined in `editor.py:36`, `manage.py:34`, and `revisions.py:32`. This violates DRY and could drift out of sync.

3. **Admin `__init__.py` references `logger` before import** — `admin/__init__.py:50` calls `logger.warning(...)` in the `admin_required` decorator, but `logger` is imported later at line 83 from `helpers`. This works at runtime because the decorator is only called after module initialization completes, but it's fragile.

4. **Missing `import logging` in admin/__init__.py** — `logger` is used at line 50 but only imported at line 83 from `helpers`. If `helpers` import fails, `logger` would be undefined at decorator call time.

5. **Health check uses `?detailed=true` but doc says `?detailed=1`** — Users following the doc would use `?detailed=1` which would not enable detailed mode (`meta.py:194`).

### Improvement Suggestions

1. **Update `api-routes.md` to document tags, pages, and series endpoints** — These are fully implemented API resources with CRUD operations and scoped auth.

2. **Document the scoped token auth system** — Add a section to `api-routes.md` explaining `ApiToken` model, `require_scope()` decorator, and available scopes. This is a significant authentication feature.

3. **Add RSS tag/series feeds to `rss-feeds.md`** — Document the 6 additional feed endpoints for tag-specific and series-specific feeds.

4. **Fix backup route paths in `admin-routes.md`** — Remove trailing slashes and add `<filename>` parameter documentation.

5. **Fix post list route path** — Change `GET /admin/<int:page>` to `GET /admin/` with `page` query parameter.

6. **Fix file reference for post delete/preview** — Change `manage.py` to `posts/manage.py`.

7. **Document rate limits for admin and public routes** — Add rate limit information to `admin-routes.md` and `public-routes.md`.

8. **Fix health check parameter documentation** — Change `?detailed=1` to `?detailed=true` in `public-routes.md`.

9. **Consolidate `_save_revision`** — Extract the duplicated function into a shared helper module.

10. **Document error handlers** — Add `errors.py` to `admin-routes.md` or create a separate section.

## Action Items

| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high | Add tags, pages, series API endpoint documentation | api-routes.md |
| 2 | high | Document scoped token auth system (ApiToken, require_scope, 14 scopes) | api-routes.md |
| 3 | high | Add RSS tag/series feed endpoints (6 routes) | rss-feeds.md |
| 4 | high | Fix backup route paths: remove trailing slashes, add `<filename>` param | admin-routes.md |
| 5 | high | Fix post list route: `GET /admin/` not `GET /admin/<int:page>` | admin-routes.md |
| 6 | medium | Fix file reference: `manage.py` → `posts/manage.py` | admin-routes.md |
| 7 | medium | Fix health check param: `?detailed=1` → `?detailed=true` | public-routes.md |
| 8 | medium | Document rate limits for admin routes (login: 5/min, etc.) | admin-routes.md |
| 9 | medium | Document rate limits for public routes (index: 60/min, etc.) | public-routes.md |
| 10 | medium | Add `auth.py` to API endpoints table | api-routes.md |
| 11 | low | Document error handlers blueprint (404, 500, 413) | admin-routes.md or new doc |
| 12 | low | Add markdown preview route to admin module structure | admin-routes.md |
| 13 | low | Fix newsletter route purpose descriptions | admin-routes.md |
