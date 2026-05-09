# Routes Architecture Review

## Summary

Reviewed 4 architecture documents against actual implementation in `app/routes/`. Found significant discrepancies including non-existent routes, incorrect HTTP methods, security issues, and undocumented features.

---

## Verified Claims

### API Routes (`app/routes/api/`)

| Documented | Actual | Status |
|-----------|--------|--------|
| `GET /api/posts` | Implemented at `app/routes/api/posts.py:50-84` | ✓ |
| `POST /api/posts` | Implemented at `app/routes/api/posts.py:105-204` | ✓ |
| `PUT /api/posts/<id>` | Implemented at `app/routes/api/posts.py:207-304` | ✓ |
| `DELETE /api/posts/<id>` | Implemented at `app/routes/api/posts.py:307-342` | ✓ |
| `GET /api/subscribers` | Implemented at `app/routes/api/subscribers.py:39-73` | ✓ |
| `POST /api/subscribers/export` | Implemented at `app/routes/api/subscribers.py:83-118` (admin) | ✓ |
| `GET /api/stats` | Implemented at `app/routes/api/stats.py:17-63` | ✓ |
| `POST /api/auth` | Implemented at `app/routes/api/auth.py:13-27` | ✓ |

### Admin Routes (`app/routes/admin/`)

| Documented | Actual | Status |
|-----------|--------|--------|
| `GET /admin/login`, `POST /admin/login` | `app/routes/admin/auth.py:32-96` | ✓ |
| `GET /admin/new`, `GET /admin/edit/<int:post_id>` | `app/routes/admin/posts/editor.py:137,215` | ✓ |
| `GET /admin/subscribers` | `app/routes/admin/subscribers.py:18-53` | ✓ |
| `GET /admin/tags` | `app/routes/admin/tags.py:15-37` | ✓ |
| `GET /admin/users` | `app/routes/admin/users.py:17-38` | ✓ |
| `GET /admin/sessions` | `app/routes/admin/sessions.py:15-40` | ✓ |
| `GET /admin/analytics` | `app/routes/admin/analytics.py` | ✓ |
| `GET /admin/settings` | `app/routes/admin/settings.py:14-38` | ✓ |
| `GET /admin/audit` | `app/routes/admin/audit.py:13-49` | ✓ |
| `GET /admin/comments` | `app/routes/admin/comments.py:15-48` | ✓ |
| `GET /admin/backup` | `app/routes/admin/backup.py:23-50` | ✓ |

### Public Routes (`app/routes/public/`)

| Documented | Actual | Status |
|-----------|--------|--------|
| `GET /` | `app/routes/public/browse.py:96-117` | ✓ |
| `GET /tag/<slug>` | `app/routes/public/browse.py:221-248` | ✓ |
| `GET /search` | `app/routes/public/browse.py:250-312` | ✓ |
| `GET /post/<slug>` | `app/routes/public/posts.py:46-92` | ✓ |
| `POST /subscribe` | `app/routes/public/subscribe.py:55-115` | ✓ |
| `GET /confirm/<token>` | `app/routes/public/subscribe.py:117-157` | ✓ |
| `GET /unsubscribe/<token>` | `app/routes/public/subscribe.py:159-180` | ✓ |
| `GET /sitemap.xml` | `app/routes/public/meta.py:177-181` | ✓ |
| `GET /robots.txt` | `app/routes/public/meta.py:95-175` | ✓ |
| `GET /health` | `app/routes/public/meta.py:191-313` | ✓ |
| `POST /post/<slug>/comment` | Implemented but route is actually at `app/routes/admin/comments.py` for admin approval | ✓ |

### RSS/Feeds

| Documented | Actual | Status |
|-----------|--------|--------|
| `GET /atom` | `app/routes/rss.py:102-164` | ✓ |
| `GET /rss` | `app/routes/rss.py:186-234` | ✓ |
| `GET /json` | `app/routes/rss.py:237-281` | ✓ |

---

## Discrepancies

### API Routes Discrepancies

1. **`POST /api/posts/<id>/publish` does not exist**
   - **Doc**: `api-routes.md:67-70` documents `POST /api/posts/<id>/publish`
   - **Actual**: Publishing is done via `PUT /api/posts/<id>` with `published` field body
   - **Reference**: `app/routes/api/posts.py:263-268`
   - **Fix**: Remove from docs or clarify that publish uses PUT with `published` field

2. **`DELETE /api/subscribers/<id>` exists but is undocumented**
   - **Doc**: Not documented
   - **Actual**: `app/routes/api/subscribers.py:132-152`
   - **Fix**: Add to documentation

3. **Rate limits documented incorrectly**
   - **Doc**: "Authenticated reads 500/min", "Authenticated writes 100/min"
   - **Actual**: `DEFAULT_LIMIT = "20 per minute"` and `WRITE_LIMIT = "10 per minute"` in code
   - **Reference**: `app/routes/api/posts.py:18-19`
   - **Fix**: Update docs to reflect actual limits (20/min read, 10/min write)

### Admin Routes Discrepancies

4. **`/admin/logout` is POST, not GET**
   - **Doc**: `admin-routes.md:40` says `GET /admin/logout`
   - **Actual**: `POST /admin/logout` at `app/routes/admin/auth.py:99-122`
   - **Fix**: Change to `POST /admin/logout`

5. **Tag routes documented incorrectly**
   - **Doc**: `POST /admin/tags`, `POST /admin/tags/delete/<int:tag_id>`
   - **Actual**:
     - `GET /admin/tags` - list (`app/routes/admin/tags.py:15`)
     - `POST /admin/tags/create` - create (`app/routes/admin/tags.py:115`)
     - `POST /admin/tags/rename/<int:tag_id>` - rename (`app/routes/admin/tags.py:40`)
     - `POST /admin/tags/delete/<int:tag_id>` - delete (`app/routes/admin/tags.py:87`)
   - **Fix**: Update to reflect actual routes

6. **Backup routes missing filename parameters**
   - **Doc**: `POST /admin/backup/restore/`, `GET /admin/backup/download/`, `POST /admin/backup/delete/`
   - **Actual**:
     - `POST /admin/backup/restore/<filename>` (`app/routes/admin/backup.py:107`)
     - `GET /admin/backup/download/<filename>` (`app/routes/admin/backup.py:84`)
     - `POST /admin/backup/delete/<filename>` (`app/routes/admin/backup.py:171`)
   - **Fix**: Add `<filename>` parameter to all backup route paths

7. **Newsletter routes are different**
   - **Doc**: `POST /admin/newsletter/preview`, `POST /admin/newsletter/send`
   - **Actual**:
     - `GET /admin/newsletter/preview` - preview newsletter (`app/routes/admin/newsletter.py:70`)
     - `POST /admin/newsletter-test` - send test newsletter (`app/routes/admin/newsletter.py:24`)
   - **Note**: There's no `POST /admin/newsletter/send` - actual newsletter sending is via Celery task
   - **Fix**: Correct documented routes and note that sending is async via task

8. **Posts list route doesn't exist as `/admin/posts`**
   - **Doc**: `GET /admin/posts`, `GET /admin/posts/<int:page>`
   - **Actual**: Dashboard is at `GET /admin/` with post list, not `/admin/posts`
   - **Reference**: `app/routes/admin/posts/__init__.py:51`
   - **Fix**: Document that post listing is part of dashboard at `/admin`

9. **Revisions routes incomplete/missing**
   - **Doc**: `GET /admin/posts/<int:post_id>/revisions/<int:rev_id>`
   - **Actual**: 
     - `GET /admin/posts/<int:post_id>/revisions` - list revisions (`app/routes/admin/posts/revisions.py:49`)
     - `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore` - restore (`app/routes/admin/posts/revisions.py:75`)
   - **Fix**: Document the actual restore endpoint; there's no direct `GET` for a single revision

10. **2FA routes have wrong paths**
    - **Doc**: `/admin/2fa-setup`, `/admin/2fa-verify`
    - **Actual**: `/admin/2fa/setup`, `/admin/2fa/verify` (with slashes)
    - **Reference**: `app/routes/admin/auth.py:263,312`
    - **Fix**: Update paths to `/admin/2fa/setup` and `/admin/2fa/verify`

### Public Routes Discrepancies

11. **Preview route is completely different**
    - **Doc**: `GET /post/<slug>/preview/<token>` (token-based by slug)
    - **Actual**: `GET /preview/<int:post_id>?token=<hmac>&expires=<timestamp>` (token-based by post ID)
    - **Reference**: `app/routes/public/posts.py:94-140`
    - **Fix**: Update documentation to reflect actual preview mechanism

12. **Archive route undocumented**
    - **Doc**: Doesn't mention `/archive`
    - **Actual**: `GET /archive` at `app/routes/public/browse.py:121-206`
    - **Fix**: Add to documentation

13. **Static pages route undocumented**
    - **Doc**: Only lists `/`, `/tag/<tag>`, `/search`, `/post/<slug>`
    - **Actual**: `GET /page/<slug>` at `app/routes/public/browse.py:208-219`
    - **Fix**: Add to documentation

14. **Series route undocumented**
    - **Doc**: No mention of `/series/<slug>`
    - **Actual**: `GET /series/<slug>` at `app/routes/public/browse.py:314-342`
    - **Fix**: Add to documentation

---

## Bugs Found

### BUG-1: Public Preview Route - Authorization Bypass (HIGH)

**Issue**: The admin preview route at `GET /preview/<int:post_id>` in `app/routes/public/posts.py:94-140` does not verify that the user has any relationship to the post being previewed. Any HMAC-signed URL with a valid token and post ID grants access to view ANY post, including draft/scheduled posts.

**Code reference**: `app/routes/public/posts.py:94-140`

```python
@public.route("/preview/<int:post_id>")
@limiter.limit("30 per minute")
def public_preview(post_id: int) -> ResponseReturnValue:
    # Token validation passes → ANY post can be viewed
    post_obj = db.session.execute(
        select(Post).options(...).filter(Post.id == post_id)
    ).unique().scalar_one_or_none()
```

**Impact**: Unauthorized access to unpublished content. Anyone with a valid HMAC signature can view draft posts.

**Recommendation**: Add admin session verification OR store preview tokens in database with post association. Alternatively, require the user to be authenticated via session when accessing preview URLs generated from admin panel.

---

## Security Issues

### SEC-1: HMAC-based Preview URLs Could Be Enumerated

**Issue**: The preview URL uses HMAC with timestamp expiry. While the token is HMAC-signed, an attacker could enumerate post IDs and generate valid tokens if they know the SECRET_KEY and expiry timestamp format.

**Reference**: `app/routes/public/posts.py:117-123`

**Note**: The HMAC secret is the app's SECRET_KEY which is not publicly known. However, if an attacker could determine the app's SECRET_KEY through other means, they could generate preview URLs for any post.

---

## Improvements Needed

### High Priority

1. **Fix preview route security** - Add proper authorization check
2. **Correct route paths in admin-routes.md** - 2FA routes, logout method, backup routes with filename params
3. **Remove non-existent `/api/posts/<id>/publish` endpoint** from documentation

### Medium Priority

4. **Add missing public routes** - archive, series, static pages
5. **Document actual preview mechanism** - token-based by post ID, not slug
6. **Fix rate limit documentation** - actual limits are 20/min read, 10/min write
7. **Add undocumented API endpoint** - `DELETE /api/subscribers/<id>`
8. **Document newsletter test route** - `/admin/newsletter-test` (POST)
9. **Fix tag management routes** - include rename, correct paths

### Low Priority

10. **Add `/admin/posts/<int:post_id>/revisions/<int:revision_id>/restore` to documentation**
11. **Document `/admin/users/<int:user_id>/make-owner` route** - exists but not documented
12. **Document `/admin/users/<int:user_id>/password` route** - exists but not documented

---

## Files Needing Updates

| File | Changes Needed |
|------|----------------|
| `architecture/routes/api-routes.md` | Remove publish endpoint, fix rate limits, add DELETE subscribers |
| `architecture/routes/admin-routes.md` | Fix 2FA paths, logout method, backup routes, tag routes, newsletter routes, posts list |
| `architecture/routes/public-routes.md` | Fix preview route, add archive, series, static pages |
| `architecture/routes/rss-feeds.md` | No changes needed |

---

## Implementation Notes

- Admin routes use `admin_required` decorator for authentication (`app/routes/admin/__init__.py:16-58`)
- API routes use `require_api_key` decorator with `X-API-Key` header (`app/routes/api/auth.py:13-27`)
- Public routes do not require authentication except for admin functions
- Webhook events are triggered on post publish/unpublish (`app/routes/api/posts.py:292-302`) and subscriber confirmation (`app/routes/public/subscribe.py:146-155`)