# Routes Module Architecture Review

## Summary

This document reviews the Routes module documentation against actual implementation, identifying accurate claims, inaccuracies, missing documentation, and recommended improvements.

---

## Verified Accurate Claims

### Public Routes (`public-routes.md`)

1. **Home Page Route**: `GET /` and `GET /page/<int:page>` - VERIFIED
   - Actual: `app/routes/public/browse.py:96-117` via `register_browse_routes()`

2. **Tag Pages**: `GET /tag/<slug>` and `GET /tag/<slug>/<int:page>` - VERIFIED
   - Actual: `app/routes/public/browse.py:221-248`

3. **Search**: `GET /search` - VERIFIED
   - Actual: `app/routes/public/browse.py:250-312`

4. **Static Page**: `GET /page/<slug>` - VERIFIED
   - Actual: `app/routes/public/browse.py:208-219`

5. **Published Post**: `GET /post/<slug>` - VERIFIED
   - Actual: `app/routes/public/posts.py:46-92`

6. **Subscribe**: `POST /subscribe` (only POST, no GET) - VERIFIED
   - Actual: `app/routes/public/subscribe.py:55` - only `methods=["POST"]`

7. **Confirm Subscription**: `GET /confirm/<token>` - VERIFIED
   - Actual: `app/routes/public/subscribe.py:117`

8. **Unsubscribe**: `GET /unsubscribe/<token>` - VERIFIED
   - Actual: `app/routes/public/subscribe.py:159`

9. **Sitemap**: `GET /sitemap.xml` - VERIFIED
   - Actual: `app/routes/public/meta.py:177-181`

10. **Robots.txt**: `GET /robots.txt` - VERIFIED
    - Actual: `app/routes/public/meta.py:95-175`

11. **Health Check**: `GET /health` - VERIFIED
    - Actual: `app/routes/public/meta.py:191-313`

12. **Comment Submission**: `POST /post/<slug>/comment` - VERIFIED
    - Actual: `app/routes/public/comments.py:12`

### Admin Routes (`admin-routes.md`)

1. **Login**: `GET/POST /admin/login` - VERIFIED
   - Actual: `app/routes/admin/auth.py:32-96`

2. **2FA Setup**: `GET /admin/2fa-setup` - VERIFIED
   - Actual: `app/routes/admin/auth.py:263-309`

3. **2FA Verify**: `GET /admin/2fa-verify` - VERIFIED
   - Actual: `app/routes/admin/auth.py:312-346`

4. **Post Editor - New**: `GET /admin/new` - VERIFIED
   - Actual: `app/routes/admin/posts/editor.py:137-213`

5. **Post Editor - Edit**: `GET /admin/edit/<int:post_id>` - VERIFIED
   - Actual: `app/routes/admin/posts/editor.py:215-326`

6. **Post Revisions**: `GET /admin/posts/<int:post_id>/revisions` - VERIFIED
   - Actual: `app/routes/admin/posts/revisions.py:49-73`

7. **Subscribers List**: `GET /admin/subscribers` - VERIFIED
   - Actual: `app/routes/admin/subscribers.py:18-53`

8. **Tags List**: `GET /admin/tags` - VERIFIED
   - Actual: `app/routes/admin/tags.py:15-37`

9. **Tag Delete**: `POST /admin/tags/delete/<int:tag_id>` - VERIFIED
   - Actual: `app/routes/admin/tags.py:87-112`

10. **User Management Routes** - VERIFIED
    - `GET /admin/users` - Actual: `app/routes/admin/users.py:17-38`
    - `POST /admin/users/create` - Actual: `app/routes/admin/users.py:41-88`
    - `POST /admin/users/delete/<int:user_id>` - Actual: `app/routes/admin/users.py:91-122`
    - `POST /admin/users/<int:user_id>/promote` - Actual: `app/routes/admin/users.py:125-152`
    - `POST /admin/users/<int:user_id>/demote` - Actual: `app/routes/admin/users.py:155-189`

11. **Session Monitoring**: `GET /admin/sessions` - VERIFIED
    - Actual: `app/routes/admin/sessions.py:15-40`

12. **Media Library**: `GET /admin/media` - VERIFIED
    - Actual: `app/routes/admin/media.py:93-127`

13. **Media Upload**: `POST /admin/media/upload` - VERIFIED
    - Actual: `app/routes/admin/media.py:130-157`

14. **Backup Routes** - VERIFIED
    - `GET /admin/backup` - Actual: `app/routes/admin/backup.py:23-50`
    - `POST /admin/backup/create` - Actual: `app/routes/admin/backup.py:53-81`
    - `POST /admin/backup/restore/<filename>` - Actual: `app/routes/admin/backup.py:107-168`
    - `GET /admin/backup/download/<filename>` - Actual: `app/routes/admin/backup.py:84-104`
    - `POST /admin/backup/delete/<filename>` - Actual: `app/routes/admin/backup.py:171-196`
    - `GET /admin/backup/verify/<filename>` - Actual: `app/routes/admin/backup.py:199-224`
    - `GET /admin/backup/verify-all` - Actual: `app/routes/admin/backup.py:227-242`

15. **Analytics**: `GET /admin/analytics` - VERIFIED
    - Actual: `app/routes/admin/analytics.py:9-38`

16. **Audit Log**: `GET /admin/audit` - VERIFIED
    - Actual: `app/routes/admin/audit.py:14-48`

17. **Comment Moderation**: `GET /admin/comments` - VERIFIED
    - Actual: `app/routes/admin/comments.py:15-48`
    - `POST /admin/comments/<int:comment_id>/approve` - VERIFIED
    - `POST /admin/comments/<int:comment_id>/delete` - VERIFIED

### API Routes (`api-routes.md`)

1. **List Posts**: `GET /api/posts` - VERIFIED
   - Actual: `app/routes/api/posts.py:50-84`

2. **Get Post**: `GET /api/posts/<id>` - VERIFIED
   - Actual: `app/routes/api/posts.py:87-102`

3. **Create Post**: `POST /api/posts` - VERIFIED
   - Actual: `app/routes/api/posts.py:105-204`

4. **Update Post**: `PUT /api/posts/<id>` - VERIFIED
   - Actual: `app/routes/api/posts.py:207-304`

5. **Delete Post**: `DELETE /api/posts/<id>` - VERIFIED
   - Actual: `app/routes/api/posts.py:307-342`

6. **Publish via PUT with `published` field**: VERIFIED
   - Actual: `app/routes/api/posts.py:263-270` - sets `post.published = published`
   - This is the correct approach per AGENTS.md

7. **Rate Limits** - PARTIALLY VERIFIED
   - `DEFAULT_LIMIT = "20 per minute"` in posts.py
   - `WRITE_LIMIT = "10 per minute"` in posts.py
   - Note: Documentation claims 500/min for reads and 100/min for writes, which differs from actual limits

### RSS/Feeds (`rss-feeds.md`)

1. **Feed Endpoints**: `/atom`, `/rss`, `/json` - VERIFIED
   - Actual: `app/routes/rss.py:102`, `app/routes/rss.py:186`, `app/routes/rss.py:237`

2. **Caching**: 5 minutes (300 seconds) - VERIFIED
   - Actual: Multiple `@flask_cache.cached(timeout=300, ...)` decorators

---

## Inaccurate/Outdated Claims

### 1. Preview Post Route (public-routes.md)

**Documentation claims**: `GET /post/<slug>/preview/<token>`

**Actual implementation**: `GET /preview/<int:post_id>?token=<token>&expires=<timestamp>`
- Token is HMAC-based, generated from `SECRET_KEY`
- Located in `app/routes/public/posts.py:94-140`

**Correction**: Update documentation to reflect:
```
GET /preview/<int:post_id>?token=<hmac_token>&expires=<unix_timestamp>
```

### 2. Logout Method (admin-routes.md)

**Documentation claims**: `GET /admin/logout`

**Actual implementation**: `POST /admin/logout` with CSRF validation
- Located in `app/routes/admin/auth.py:99-122`

**Correction**: Change to `POST /admin/logout` with CSRF protection

### 3. Post List Route (admin-routes.md)

**Documentation claims**: `GET /admin/posts` and `GET /admin/posts/<int:page>`

**Actual implementation**: 
- Dashboard/Post list is at `GET /admin/` not `/admin/posts`
- Located in `app/routes/admin/posts/__init__.py:51-115`

**Correction**: Update to show dashboard at `/admin/` not `/admin/posts`

### 4. Subscriber Export Method (admin-routes.md)

**Documentation claims**: `POST /admin/subscribers/export`

**Actual implementation**: `GET /admin/subscribers/export`
- Returns CSV file as download
- Located in `app/routes/admin/subscribers.py:83-118`

**Correction**: Change to `GET /admin/subscribers/export`

### 5. Tag Routes (admin-routes.md)

**Documentation claims**:
- `POST /admin/tags` for creating
- `POST /admin/tags/delete/<int:tag_id>` for deletion

**Actual implementation**:
- Create is at `POST /admin/tags/create` (`app/routes/admin/tags.py:115-150`)
- Rename is at `POST /admin/tags/rename/<int:tag_id>` (`app/routes/admin/tags.py:40-84`)
- Delete is at `POST /admin/tags/delete/<int:tag_id>` (`app/routes/admin/tags.py:87-112`)
- List is at `GET /admin/tags` (`app/routes/admin/tags.py:15-37`)

**Correction**: 
- Create tag route should be `POST /admin/tags/create`
- Add `POST /admin/tags/rename/<int:tag_id>` route
- Remove claim that `POST /admin/tags` creates a tag

### 6. Media Delete Route (admin-routes.md)

**Documentation claims**: `DELETE /admin/media/<filename>`

**Actual implementation**: `POST /admin/media/delete/<filename>`
- Located in `app/routes/admin/media.py:160-183`

**Correction**: Change to `POST /admin/media/delete/<filename>`

### 7. Newsletter Routes (admin-routes.md)

**Documentation claims**: Routes are `GET/POST /admin/newsletter`

**Actual implementation**:
- `POST /admin/newsletter-test` for sending test newsletter (`app/routes/admin/newsletter.py:24-67`)
- `GET /admin/newsletter/preview` for preview (`app/routes/admin/newsletter.py:70-102`)
- No route at just `/admin/newsletter`

**Correction**: Document actual routes:
- `POST /admin/newsletter-test` - Send test newsletter
- `GET /admin/newsletter/preview` - Preview newsletter

### 8. Settings Route (admin-routes.md)

**Documentation claims**: `GET/POST /admin/settings` for theme/settings

**Actual implementation**:
- GET: `GET /admin/settings` (view settings) (`app/routes/admin/settings.py:14-38`)
- POST: `POST /admin/settings/theme` (update theme) (`app/routes/admin/settings.py:41-85`)

**Correction**: Split into:
- `GET /admin/settings` - View settings
- `POST /admin/settings/theme` - Update theme settings

### 9. API Post Publish (api-routes.md)

**Documentation shows**:
```
POST /api/posts/<id>/publish
```

**Actual implementation**: No such endpoint exists. Publishing is done via:
```
PUT /api/posts/<id> with body {"published": true}
```
- Located in `app/routes/api/posts.py:207-304`

**Correction**: Remove the `POST /api/posts/<id>/publish` endpoint entirely

---

## Missing Documentation

### 1. Series Routes
- `GET /series/<slug>` - View series and all posts in order
- Implemented in `app/routes/public/browse.py:314-342`

### 2. Archive Route
- `GET /archive` with optional `?year=<year>` and cursor-based pagination
- Implemented in `app/routes/public/browse.py:121-206`

### 3. Short URL Redirect
- `GET /s/<code>` - Redirects base62-encoded post ID to canonical URL
- Also tracks share events
- Implemented in `app/routes/public/posts.py:142-163`

### 4. Share Tracking API
- `POST /api/track-share` - Track social share events
- Implemented in `app/routes/public/posts.py:165-198`

### 5. Bulk Post Operations
- `POST /admin/bulk` - Bulk operations on selected posts (publish, unpublish, delete, unschedule)
- Implemented in `app/routes/admin/posts/__init__.py:118-230`

### 6. Post Delete Route
- `POST /admin/delete/<int:post_id>` - Delete a post
- Implemented in `app/routes/admin/posts/manage.py:72-95`

### 7. Post Preview Admin Route
- `GET /admin/preview/<int:post_id>` - Preview post before publishing
- `GET /admin/preview/<int:post_id>?share=1` - Get shareable preview URL with token
- Implemented in `app/routes/admin/posts/manage.py:97-122`

### 8. Revisions Restore Route
- `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore`
- Implemented in `app/routes/admin/posts/revisions.py:75-119`

### 9. User Ownership Transfer
- `POST /admin/users/<int:user_id>/make-owner` - Transfer ownership
- Implemented in `app/routes/admin/users.py:192-239`

### 10. Password Change Route
- `POST /admin/users/password/<int:user_id>` - Change user password
- Implemented in `app/routes/admin/users.py:242-273`

### 11. Subscriber Bulk Operations
- `POST /admin/subscribers/bulk` - Bulk delete, export, resend
- Implemented in `app/routes/admin/subscribers.py:121-204`

### 12. Subscriber Delete Route
- `POST /admin/subscribers/delete/<int:sub_id>` - Delete a subscriber
- Implemented in `app/routes/admin/subscribers.py:56-80`

### 13. Session Revoke Route
- `POST /admin/sessions/revoke/<int:sess_id>` - Revoke a session
- Implemented in `app/routes/admin/sessions.py:43-69`

### 14. Newsletter Reset Route
- `POST /admin/newsletter-reset/<int:post_id>` - Reset newsletter status
- Implemented in `app/routes/admin/auth.py:125-152`

### 15. Forgot Password Routes
- `GET/POST /admin/forgot-password` - Request password reset
- `GET/POST /admin/reset/<token>` - Reset password with token
- Implemented in `app/routes/admin/auth.py:155-260`

### 16. 2FA Routes
- `GET /admin/login-2fa` - TOTP verification during login
- `GET /admin/2fa/backup-codes` - Display backup codes
- `GET/POST /admin/2fa/disable` - Disable 2FA
- Implemented in `app/routes/admin/auth.py:349-466`

### 17. Metrics Endpoint
- `GET /metrics` - Prometheus-compatible metrics
- Implemented in `app/routes/public/meta.py:315-364`

### 18. Favicon Route
- `GET /favicon.ico` - Redirects to SVG favicon
- Implemented in `app/routes/public/meta.py:183-189`

### 19. API Stats Endpoint
- `GET /api/stats` - Dashboard statistics
- Implemented in `app/routes/api/stats.py:17-63`

### 20. API Auth Endpoint
- `POST /api/auth` - API key authentication
- Implemented in `app/routes/api/auth.py:13-26`

### 21. API Subscriber Export
- `POST /api/subscribers/export` - Export subscribers to CSV
- Implemented in `app/routes/api/subscribers.py`

---

## Potential Issues

### 1. Inconsistent Route Patterns

The codebase has inconsistent route patterns:
- Some use kebab-case (`/admin/newsletter-test`)
- Some use camelCase for path parameters (`/admin/posts/<int:post_id>/revisions/<int:rev_id>`)
- Some use snake_case for actions (`/admin/tags/delete`)

**Recommendation**: Standardize route naming conventions

### 2. Preview Token Security

The preview token uses HMAC-SHA256 but is generated with message `{post_id}:{expires_timestamp}`. While this is reasonable, the documentation should clarify:
- Token expiry is controlled by `PREVIEW_TOKEN_EXPIRY_DAYS` (default 7 days)
- Tokens are tied to post ID, not a session

### 3. CSRF on Logout

The logout route (`POST /admin/logout`) validates CSRF token, which is good. However, the documentation shows `GET /admin/logout` which would not work since the route only accepts POST.

### 4. Rate Limiting Discrepancy

API docs say:
- "Authenticated reads: 500/min"
- "Authenticated writes: 100/min"

Actual code shows:
- `DEFAULT_LIMIT = "20 per minute"` 
- `WRITE_LIMIT = "10 per minute"`

**Recommendation**: Update rate limits or documentation to match

### 5. Media Delete Route Accessibility

The documentation mentions `DELETE /admin/media/<filename>` but the actual route is `POST /admin/media/delete/<filename>`. This route may not be accessible from the admin UI, making it effectively hidden from normal use but still present in the API.

### 6. Tag Creation Route Inconsistency

The documentation shows `POST /admin/tags` for creating tags, but the actual route is `POST /admin/tags/create`. This inconsistency could cause integration issues.

---

## Recommended Improvements

### Priority 1: Fix Inaccuracies

1. **Update public-routes.md**:
   - Fix preview route to `GET /preview/<int:post_id>?token=<token>&expires=<timestamp>`
   - Add series route `GET /series/<slug>`
   - Add archive route `GET /archive`
   - Add short URL route `GET /s/<code>`
   - Add share tracking API `POST /api/track-share`
   - Add metrics endpoint `GET /metrics`
   - Add favicon redirect `GET /favicon.ico`

2. **Update admin-routes.md**:
   - Change `GET /admin/logout` to `POST /admin/logout`
   - Remove reference to `/admin/posts` as the post list is at `/admin/`
   - Change `POST /admin/subscribers/export` to `GET /admin/subscribers/export`
   - Fix tag routes: create is `/admin/tags/create`, add rename route `/admin/tags/rename/<int:tag_id>`
   - Change `DELETE /admin/media/<filename>` to `POST /admin/media/delete/<filename>`
   - Fix newsletter routes to `/admin/newsletter-test` and `/admin/newsletter/preview`
   - Split settings into GET `/admin/settings` and POST `/admin/settings/theme`
   - Add bulk operations route `POST /admin/bulk`
   - Add post delete route `POST /admin/delete/<int:post_id>`
   - Add preview route `GET /admin/preview/<int:post_id>`
   - Add revision restore route `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore`
   - Add user ownership transfer route `POST /admin/users/<int:user_id>/make-owner`
   - Add password change route `POST /admin/users/password/<int:user_id>`
   - Add subscriber bulk operations route `POST /admin/subscribers/bulk`
   - Add subscriber delete route `POST /admin/subscribers/delete/<int:sub_id>`
   - Add session revoke route `POST /admin/sessions/revoke/<int:sess_id>`
   - Add newsletter reset route `POST /admin/newsletter-reset/<int:post_id>`
   - Add forgot password and reset routes
   - Add all 2FA routes

3. **Update api-routes.md**:
   - Remove `POST /api/posts/<id>/publish` endpoint
   - Clarify that publishing is done via `PUT /api/posts/<id>` with `published` field
   - Update rate limits to match actual implementation:
     - Authenticated reads: 20/min (not 500/min)
     - Authenticated writes: 10/min (not 100/min)

### Priority 2: Add Missing Documentation

1. Add all missing routes listed in "Missing Documentation" section
2. Document the `/metrics` endpoint
3. Document favicon redirect
4. Document API stats and auth endpoints
5. Document API subscriber export

### Priority 3: Consistency Improvements

1. Standardize route naming conventions across the codebase
2. Ensure all routes that modify state use POST (not GET or DELETE where POST is used)
3. Document which routes require CSRF validation

### Priority 4: Code Improvements (Optional)

1. Consider adding `POST /admin/media/<filename>` as an alias for delete to satisfy DELETE method expectations if needed for compatibility
2. Consider adding `/admin/posts` as a redirect to `/admin/` for discoverability
3. Standardize rate limiting values between documentation and code

---

## Conclusion

The Routes module documentation has several inaccuracies that could lead developers astray. Most critically:

1. The logout method is POST not GET
2. The preview mechanism is completely different from what's documented (HMAC token based, not slug-based)
3. Tag creation is at `/admin/tags/create` not `/admin/tags`
4. The API publish endpoint doesn't exist - publishing is done via PUT with `published` field
5. Many routes are undocumented entirely (series, archive, short URLs, bulk operations, etc.)
6. Rate limits documented are significantly different from actual implementation

These should be fixed to ensure the documentation accurately reflects the implementation and serves as a reliable reference for developers working on this codebase.
