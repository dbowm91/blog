# Routes Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** admin-routes.md, api-routes.md, public-routes.md, rss-feeds.md
**Source Files:** app/routes/admin/, app/routes/api/, app/routes/public/, app/routes/rss.py, app/routes/errors.py

## Findings

### Verified Claims (Correct)

- All admin route paths and HTTP methods in admin-routes.md match actual code (auth.py, posts/, subscribers.py, tags.py, users.py, sessions.py, media.py, backup.py, analytics.py, newsletter.py, settings.py, pages.py, series.py, audit.py, comments.py)
- All API route paths and HTTP methods in api-routes.md match actual code (posts.py, subscribers.py, stats.py, pages.py, series.py, tags.py)
- All public route paths and methods in public-routes.md match actual code (browse.py, posts.py, comments.py, subscribe.py, meta.py)
- All RSS/Atom/JSON feed endpoints in rss-feeds.md match actual code (rss.py)
- API authentication uses two-tier system: legacy `API_KEY` env var and scoped `ApiToken` model (auth.py:42-72)
- `require_api_key` and `require_scope` decorators exist as documented (auth.py:75-108)
- All 15 scopes listed in api-routes.md exist in the SCOPES set (auth.py:18-34)
- Admin helpers re-export pattern confirmed (admin/__init__.py:79-98)
- Global CSRF protection applied to all POST requests (app/__init__.py:296-298)
- Rate limiting confirmed: API reads 20/min, writes 10/min, subscribe 10/min, comments dual-key limiting
- Spam scoring heuristic in comments.py:41-74 matches documented thresholds
- Honeypot field `website_url` in comments.py:90 matches documentation
- Webhook events fire on publish/unpublish via API (posts.py:304-315) and subscriber confirmation (subscribe.py:174-184)
- Preview token HMAC generation and verification implemented correctly (manage.py:35-53, posts.py:101-133)
- ETag-based conditional GET (304) implemented for all feed types (rss.py)
- Backup filename validation and path traversal protection confirmed (backup.py:92-101, 117-125)

### Discrepancies (Doc vs Code)

- **rss-feeds.md:236**: Doc claims Cache-Control header is set at `app/routes/rss.py:98`. Actual location is `rss.py:90` inside `_add_cache_headers()` function. Line 98 is `invalidate_rss_cache()` function definition.
- **api-routes.md:289-291**: Doc describes `require_api_key` decorator as implementing "two-tier authentication" with "Legacy API_KEY" and "Scoped ApiToken". The actual implementation in auth.py:75-88 shows `require_api_key` checks `_verify_api_key() or _verify_token()` — the tier ordering is correct but the doc implies `require_api_key` is the only auth decorator, when in practice it's always paired with `require_scope` on protected endpoints. The doc correctly describes both decorators but could clarify the composition pattern.
- **admin-routes.md:181-185**: Doc says newsletter preview "Renders the newsletter HTML in-browser (no email sent)" and test "Sends an actual email to the admin's address for delivery verification". The code at newsletter.py:65-95 confirms preview returns HTML directly (no email), and newsletter_test (line 24-62) sends via `send_newsletter()` to a test address. Accurate.
- **api-routes.md:14**: Doc lists `pages.py` endpoint as `/api/pages` but the file reference says just `pages.py`. The actual file is `app/routes/api/pages.py`. No discrepancy — just noting the doc table format is consistent.
- **public-routes.md:81-87**: Doc says spam score threshold is 0.7 for auto-quarantine. Code at comments.py:122 confirms `is_spam = spam_score >= 0.7`. Correct.
- **api-routes.md:352**: Doc says ApiToken model is at `app/models.py:625-657`. This would need model verification to confirm exact line numbers — not in scope for routes review.

### Missing Documentation

- **RSS ETag/Conditional GET**: All feed endpoints implement ETag-based conditional GET returning 304 Not Modified (rss.py:190-192, 240-242, 292-294, etc.). This important caching feature is not documented in rss-feeds.md.
- **Error Handlers**: `app/routes/errors.py` registers error handlers for 404, 500, and 413. No architecture doc covers error handling routes.
- **Admin Login Rate Limiting**: `GET/POST /admin/login` has `@limiter.limit("5 per minute")` (auth.py:33). Not documented in admin-routes.md.
- **2FA Login Rate Limiting**: `GET/POST /admin/login-2fa` has `@limiter.limit("5 per minute")` (auth.py:343). Not documented.
- **Forgot Password Rate Limiting**: `GET/POST /admin/forgot-password` has `@limiter.limit("5 per minute")` (auth.py:154). Not documented.
- **Comment Dual Rate Limiting**: Comments use both per-IP (`COMMENT_RATE_LIMIT_PER_IP`) and per-post (`COMMENT_RATE_LIMIT_PER_POST`) rate limits with custom key functions (comments.py:78-79). Doc only mentions "10 per minute" without the dual-key approach.
- **Token Enumeration Delay**: Subscribe confirm/unsubscribe routes use `time.sleep(TOKEN_ENUMERATION_DELAY)` to prevent token enumeration attacks (subscribe.py:146, 192). Security-critical behavior not documented.
- **Metrics Authentication**: `/metrics` endpoint uses `HEALTH_CHECK_SECRET` for authentication when configured (meta.py:334-337). Doc just says "Prometheus-compatible metrics endpoint" without auth details.
- **Admin Preview Shareable URL**: The admin preview route with `?share=1` generates a time-limited HMAC-signed URL (manage.py:97-107). Doc mentions "optional shareable URL" but doesn't document the HMAC mechanism or expiry.
- **Post Delete FTS Cleanup**: API post delete calls `remove_fts(post_id)` after commit (posts.py:357-359). Admin post delete also calls `remove_fts` (manage.py:82). The FTS lifecycle during delete isn't documented.
- **Bulk Operations**: Admin bulk operations support publish, unpublish, delete, and unschedule actions (posts/__init__.py:148-232). The unschedule action is not documented in admin-routes.md.
- **Subscriber Bulk Resend**: Subscriber bulk operations include a "resend" action (subscribers.py:183-195) that re-sends confirmation emails. Not documented.
- **Page View Buffer**: Post page views use `record_page_view()` from `app.page_view_buffer` (posts.py:75-77) rather than direct DB writes. Not documented.
- **Search Fallback**: When FTS returns no results, browse.py:290-308 falls back to ILIKE-based search. Not documented.
- **Search "Did You Mean"**: The search route provides "did you mean" suggestions using `get_did_you_mean()` (browse.py:311-314). Not documented.
- **Series Feed Ordering**: Series feeds preserve `PostSeries.order_index` ordering (rss.py:142-143). Not documented.
- **JSON Feed `description` Field**: Tag and series JSON feeds include a top-level `description` field (rss.py:320, 465). Not shown in rss-feeds.md JSON examples.
- **Backup Encryption**: Backup restore handles AES-256-GCM decryption (backup.py:136-150). Documented in admin-routes.md line 171 but decryption flow details are absent.
- **Backup Integrity Verification**: `GET /admin/backup/verify/<filename>` and `GET /admin/backup/verify-all` return JSON with verification results (backup.py:197-240). Return format not documented.
- **Settings Syntax Themes**: The settings route documents available syntax themes as a hardcoded list (settings.py:24-31). Not documented in admin-routes.md.
- **Admin Session IP Binding Behavior**: The `admin_required` decorator implements session IP binding with "enforce" and "warn" modes (admin/__init__.py:16-55). Behavior details not in admin-routes.md.

### Potential Bugs / Concerns

- **admin/auth.py:272-277 — 2FA setup confusing condition**: In `setup_2fa` POST handler, the code checks `if secret and pyotp.TOTP(secret).verify(token)` — if the submitted TOTP token validates against the user's *existing* secret, it says "2FA is already enabled" and redirects. This is confusing because the user is on the 2FA setup page trying to enable 2FA. If they already have it enabled, they shouldn't be on this page. The condition should likely check `user.totp_enabled` instead.
- **public/comments.py:24-32 — X-Forwarded-For spoofing**: `get_client_ip()` trusts `X-Forwarded-For` header for rate limiting. Without a trusted proxy that strips/overwrites this header, rate limiting can be bypassed by spoofing the header. This is a known limitation but should be documented.
- **rss.py:91 — Hardcoded Expires header**: `response.headers["Expires"] = "Thu, 01 Jan 2027 00:00:00 GMT"` is a hardcoded date that will become stale. Should be dynamically calculated or removed in favor of Cache-Control max-age.
- **api/subscribers.py:103 — `__import__("datetime")` hack**: Uses `__import__("datetime").timedelta(...)` instead of a normal import at the top of the file. Anti-pattern that hurts readability.
- **admin/posts/editor.py:311 — content_length None comparison**: `request.content_length and request.content_length > 1024 * 1024` — while the `and` short-circuits correctly when `content_length` is `None`, this is fragile. A explicit `is not None` check would be clearer.
- **admin/series.py:264-271 — series_reorder silently ignores missing PostSeries**: If a `PostSeries` ID in the reorder request doesn't exist or doesn't belong to the series, it's silently skipped. No error or warning is returned.
- **api/posts.py:304-315 — Webhook exception swallowed**: `create_webhook_event` is wrapped in bare `except Exception: pass`. Webhook delivery failures are completely silent. Should at least log the error.
- **subscribe.py:174-184 — Webhook exception swallowed**: Same pattern — `create_webhook_event` failures silently ignored.
- **admin/__init__.py:50 — logger reference before import**: `admin_required` function references `logger` at line 50, but `logger` is imported at line 83. Works due to Python runtime name resolution, but is a maintenance hazard if module loading order changes.
- **browse.py:277 — f-string in logging call**: `logging.warning(f"FTS returned invalid results: {post_results}")` should use `logging.warning("FTS returned invalid results: %s", post_results)` for lazy evaluation and security.
- **api/auth.py:47 — Timing attack on legacy API_KEY**: `hmac.compare_digest(provided, API_KEY)` is used which is timing-safe. However, if `API_KEY` is empty string (default), `hmac.compare_digest("", "")` returns `True`, meaning an empty `X-API-Key` header would pass legacy auth when no API_KEY is configured. Actually, looking again: line 44 checks `if not API_KEY: return None` first, so this is safe. The early return prevents the empty-string comparison.
- **backup.py:131 — `db.engine.dispose()` before restore**: The code disposes engine connections before overwriting the SQLite database file. This is correct for SQLite but could cause issues if the database backend changes.
- **public/subscribe.py:204 — Missing rollback on commit failure**: `sub.confirmed = False; db.session.commit()` at line 203-204 doesn't have try/except for OperationalError. If the commit fails, the error propagates unhandled. Other paths in the same function properly handle this.
- **api/stats.py:31-41 — SQL injection safe but raw SQL**: Uses `text()` with parameterized queries, which is safe. But raw SQL bypasses SQLAlchemy ORM protections. If the schema changes, these queries could silently return wrong data.
- **errors.py:62-68 — 413 handler redirects to admin**: The 413 (file too large) handler redirects to `req.referrer or url_for("admin.dashboard")`. If a public user hits a 413, they'd be redirected to the admin dashboard which would then redirect to login. Should check if the referrer is an admin URL first.
- **media.py:66-97 — Redundant storage instantiation**: `_scan_media_directory` calls `get_storage()` twice (lines 68-69 and 72-73) inside the loop. The second call is redundant.
- **admin/newsletter.py:16-22 — FakeSubscriber class**: `FakeSubscriber` is used for test newsletter sending. This is functional but the class name and implementation are a code smell — could use a simple namespace/dict.

### Improvement Suggestions

- **Document ETag/Conditional GET for feeds**: rss-feeds.md should document that all feeds support `If-None-Match` / `304 Not Modified` responses for efficient caching.
- **Document rate limiting across all routes**: Create a comprehensive rate limit table covering admin login (5/min), 2FA login (5/min), forgot password (5/min), public browse (60/min), search (20/min), archive (30/min), subscribe (10/min), comment (dual-key), and all API endpoints.
- **Document error handler routes**: Add a section or separate doc covering the error handlers in errors.py (404, 500, 413).
- **Fix rss-feeds.md line number**: Change `rss.py:98` to `rss.py:90` for Cache-Control header reference.
- **Document token enumeration protection**: Note that confirm/unsubscribe routes include timing delays to prevent token enumeration.
- **Document search fallback behavior**: Document that FTS search falls back to ILIKE when FTS returns no results, and that "did you mean" suggestions are provided.
- **Document series feed ordering**: Note that series feeds preserve `order_index` ordering rather than date ordering.
- **Refactor admin/auth.py setup_2fa logic**: The condition at line 272-277 should check `user.totp_enabled` rather than verifying the token against the existing secret.
- **Fix hardcoded Expires header in rss.py:91**: Replace with dynamically calculated expiry or remove in favor of Cache-Control.
- **Replace `__import__("datetime")` in api/subscribers.py:103**: Add proper import at top of file.
- **Log webhook exceptions**: Replace bare `except Exception: pass` in api/posts.py:314 and subscribe.py:183 with logged warnings.
- **Document X-Forwarded-For trust assumption**: Note that comment rate limiting relies on trusted proxy configuration.
- **Document admin session IP binding**: Add details about enforce/warn modes and their behavioral differences.
- **Fix subscribe.py:204 missing error handling**: Wrap `db.session.commit()` in try/except for OperationalError.
- **Document backup verify JSON return format**: The verify endpoints return JSON with `valid` and `message` fields — should be documented.
- **Fix errors.py 413 redirect logic**: Avoid redirecting public users to admin dashboard on file-too-large errors.
- **Fix media.py redundant get_storage()**: Remove the duplicate `get_storage()` call inside `_scan_media_directory` loop.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Fix rss-feeds.md line number reference (98 → 90) for Cache-Control header | docs |
| 2 | high | Fix subscribe.py:204 missing OperationalError handling on unsubscribe commit | source |
| 3 | high | Fix admin/auth.py:272 setup_2fa confusing TOTP validation condition | source |
| 4 | high | Document rate limiting across all route categories (admin, API, public) | docs |
| 5 | medium | Document ETag/conditional GET (304) support for RSS/Atom/JSON feeds | docs |
| 6 | medium | Document token enumeration timing protection in subscribe routes | docs |
| 7 | medium | Document search fallback behavior and "did you mean" feature | docs |
| 8 | medium | Fix hardcoded Expires header in rss.py:91 | source |
| 9 | medium | Replace `__import__("datetime")` hack in api/subscribers.py:103 | source |
| 10 | medium | Log webhook exceptions instead of swallowing silently (posts.py:314, subscribe.py:183) | source |
| 11 | medium | Document X-Forwarded-For trust assumption for comment rate limiting | docs |
| 12 | medium | Document admin session IP binding enforce/warn modes | docs |
| 13 | low | Document error handler routes (404, 500, 413) in architecture docs | docs |
| 14 | low | Fix browse.py:277 f-string in logging call to use lazy evaluation | source |
| 15 | low | Fix media.py:66-97 redundant get_storage() call in loop | source |
| 16 | low | Fix errors.py:62-68 413 handler redirect logic for public users | source |
| 17 | low | Document series feed ordering (order_index preservation) | docs |
| 18 | low | Document backup verify JSON return format | docs |
| 19 | low | Document available syntax themes in settings route | docs |
| 20 | low | Document unschedule bulk action in admin posts | docs |
