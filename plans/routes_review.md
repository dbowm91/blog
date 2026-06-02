# Routes Architecture Review

**Reviewed:** 2026-06-02
**Architecture Docs:** architecture/routes/admin-routes.md, architecture/routes/api-routes.md, architecture/routes/public-routes.md, architecture/routes/rss-feeds.md
**Source Files:** app/routes/admin/*.py, app/routes/api/*.py, app/routes/public/*.py, app/routes/rss.py, app/routes/errors.py

## Findings

### Verified Claims (Correct)

#### Admin Routes
- All documented admin routes exist and match implementation
- `admin_required` decorator with IP binding at `app/routes/admin/__init__.py:25-55`
- Login rate limit 5/min at `auth.py:33`
- 2FA login rate limit 5/min at `auth.py:341`
- Forgot password rate limit 5/min at `auth.py:154`
- Newsletter reset route at `auth.py:123`
- Post editor routes at `posts/editor.py:126,201`
- Preview markdown at `posts/editor.py:307`
- Post delete at `posts/manage.py:59`
- Post preview at `posts/manage.py:89` with share=1 option at line 97
- Dashboard at `posts/__init__.py:51`
- Bulk operations at `posts/__init__.py:116`
- Post revisions routes at `posts/revisions.py:48,74`
- Subscriber routes (list, export, bulk, delete) all verified
- Tag routes (list, create, rename, delete) all verified
- User routes (list, create, delete, promote, demote, make-owner, password) all verified
- Session routes (list, revoke) verified
- Media routes (list, upload, delete) verified
- Backup routes (list, create, download, restore, delete, verify, verify-all) verified
- Analytics, newsletter, settings, audit, pages, series, comments routes verified

#### API Routes
- All documented API endpoints exist and match implementation
- Webhook events for post publish/unpublish at `posts.py:307-318`
- Subscriber confirmed webhook at `subscribe.py:174-182`
- Rate limits: 20/min DEFAULT_LIMIT, 10/min WRITE_LIMIT in each API module
- `require_api_key` and `require_scope` decorators at `auth.py:75,91`
- Scopes documented match implementation at `auth.py:18-34`
- Error responses (400, 401, 403, 404, 409, 429, 500, 503) match code

#### Public Routes
- All documented public routes exist and match implementation
- Home page at `browse.py:98`
- Archive with cursor-based pagination at `browse.py:123`
- Tag pages at `browse.py:233`
- Search at `browse.py:262`
- Series at `browse.py:326`
- Static page at `browse.py:220`
- Post view at `posts.py:46`
- Preview with HMAC token at `posts.py:101`
- Short URL redirect at `posts.py:155`
- Share tracking at `posts.py:178`
- Subscribe at `subscribe.py:55`
- Confirm/unsubscribe with TOKEN_ENUMERATION_DELAY at `subscribe.py:142,188`
- Comments with honeypot, spam scoring at `comments.py:77-149`
- Meta routes (robots, sitemap, health, metrics, favicon) at `meta.py`
- Error handlers (404, 500, 413) at `errors.py:37-70`

#### RSS/Feeds
- All documented feed routes exist at `rss.py`
- ETag/conditional GET support documented and implemented
- Cache-Control header at `rss.py:90`
- Server-side cache TTL 300s documented and implemented

### Discrepancies (Doc vs Code)

1. **admin-routes.md:228** - Syntax themes claim `github-dark, github-light, solarized-dark, monokai` from `app/models.py:366-457`, but these are THEME_PRESETS (CSS color schemes), NOT syntax highlighting themes. The actual syntax themes are Prism-based: `prism, prism-coy, prism-dark, prism-funky, prism-okaidia, prism-tomorrow` as defined in `app/routes/admin/settings.py:24-31`.

2. **admin-routes.md:153** - References `admin_required` decorator at lines 25-55, but actual decorator is at lines 16-59 in `__init__.py` (slight drift).

3. **api-routes.md:43** - Query parameter `published` documented for GET /api/posts but the full query parameter list for subscribers (confirmed) is correctly documented at line 95.

4. **admin-routes.md:280-296** - Rate limits table references line numbers that may drift over time (e.g., "per-IP  `app/routes/admin/auth.py:33`") - accurate as of review date but could become stale.

### Missing Documentation

1. **CSRF on API routes** - `AGENTS.md` notes CSRF applies to ALL POST requests including API endpoints (`app/__init__.py:297-298`), but api-routes.md does not document this. API clients using ApiToken don't have Flask sessions with CSRF tokens, so POST requests would get 403.

2. **Comment rate limit configuration** - public-routes.md mentions configurable rate limits but doesn't specify the actual config keys: `COMMENT_RATE_LIMIT_PER_IP` and `COMMENT_RATE_LIMIT_PER_POST` from `app/config.py`.

3. **Rate limit key functions** - The dual-key rate limiting for comments uses custom key functions (`get_client_ip`, `get_per_post_comment_key`) not documented.

4. **Honeypot field name** - Documentation mentions "hidden website_url field" but doesn't specify the exact field name in the code (`comments.py:90`).

5. **Preview token parameters** - The public preview route accepts `token` (HMAC signature) and `expires` (Unix timestamp) but docs don't explain how to generate the token.

6. **Backup encryption dependency** - Backup endpoints mention AES-256-GCM encryption but don't document that it requires `BACKUP_ENCRYPTION_KEY` environment variable.

7. **Series feed ordering** - rss-feeds.md notes series feeds preserve order_index but doesn't explain they don't use date-based ordering like other feeds.

8. **Admin helpers module structure** - The `helpers/` directory contents not documented in admin-routes.md.

9. **Series `image` field** - Series API returns `image` field (`series.py:29`) but not documented in api-routes.md.

10. **Webhook delivery architecture** - API docs mention webhook events trigger but don't document the two-level dispatch pattern.

### Potential Bugs / Concerns

1. **Comment rate limit IP header bypass** (`comments.py:24-32`) - As noted in AGENTS.md, rate limiting uses X-Forwarded-For header which can be spoofed if behind a trusted proxy that doesn't sanitize this header. Known limitation.

2. **Preview token expiry check** (`posts.py:121`) - Uses `time() > expires` without clock skew tolerance. Valid tokens could be rejected if server time is slightly behind.

3. **Admin session deletion error handling** (`__init__.py:41-45`) - When IP binding enforces and session deletion fails, invalid AdminSession record may remain in DB.

4. **Series reorder lacks validation** (`series.py:265-270`) - Accepts any order_index values without checking for gaps or duplicates.

5. **Tag API post count race condition** (`tags.py:31`) - `len(tag.posts)` loads relationship; under high concurrency, counts could be stale.

6. **No pagination on series API** - `GET /api/series` returns ALL series without pagination (`series.py:61`).

7. **Favicon route redirect** (`meta.py:180-186`) - Returns 302 to SVG; if SVG missing, users get 404 on redirect target rather than graceful fallback.

8. **Health check scheduler dependency** (`meta.py:215`) - Scheduler check only runs if SMTP_HOST is set, but scheduler runs other jobs besides newsletter.

### Improvement Suggestions

1. **Update syntax theme documentation** - Split conflation of THEME_PRESETS (color schemes) and syntax themes (Prism themes).

2. **Add pagination to series API** - Consider adding pagination for scalability.

3. **Document API CSRF behavior** - Clearly note API endpoints enforce CSRF.

4. **Add line number refresh process** - Use symbolic references (function name) instead of line numbers where possible.

5. **Document rate limit configuration** - Add explicit documentation for config keys with defaults.

6. **Add preview token generation docs** - Document HMAC-SHA256 generation process or reference helper.

7. **Document webhook delivery retry logic** - Two-level dispatch and retry count (default 5).

8. **Add API scope requirements table** - Clear table showing scopes required for each endpoint.

9. **Document admin helpers API** - The helpers module exports should be documented.

10. **Add error response examples** - Include example error responses for each error code.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Fix syntax theme documentation - THEME_PRESETS (github-dark, etc.) are NOT syntax themes | docs |
| 2 | high | Document API CSRF enforcement - POST requests require CSRF token even with API key auth | docs |
| 3 | medium | Add pagination to GET /api/series | source |
| 4 | medium | Document rate limit configuration keys and defaults | docs |
| 5 | medium | Add API scope requirements table | docs |
| 6 | medium | Add preview token generation documentation | docs |
| 7 | low | Consider clock skew tolerance for preview token expiry | source |
| 8 | low | Document webhook delivery architecture (two-level dispatch, retry count) | docs |
| 9 | low | Update line number references to use function names where possible | docs |
| 10 | low | Add explicit CSRF exemption documentation for programmatic API access | docs |
