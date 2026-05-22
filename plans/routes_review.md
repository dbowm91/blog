# Routes Architecture Review

## admin-routes.md

### Verified Claims
- All auth routes: login, logout, 2FA setup/verify/disable/backup-codes, forgot-password, reset-password, login-2fa
- Post editor routes: GET /admin/new, GET /admin/edit/<int:post_id>
- Post delete/preview: POST /admin/delete, GET /admin/preview
- Bulk operations: POST /admin/bulk
- Revision routes: GET /admin/posts/<int:post_id>/revisions, GET .../revisions/<int:rev_id>, POST .../restore
- Subscriber routes: GET /admin/subscribers, export, bulk, delete
- Tag CRUD: all routes present
- User management: all routes present
- Session monitoring: GET /admin/sessions, POST /admin/sessions/revoke/<id>
- Media: GET /admin/media, POST /admin/media/upload, POST /admin/media/delete/
- Backup: all routes present with correct paths
- Analytics: GET /admin/analytics
- Newsletter: GET /admin/newsletter/preview, POST /admin/newsletter-test
- Settings: GET /admin/settings, POST /admin/settings/theme
- Audit: GET /admin/audit
- Comments: all routes present
- Series: all routes present

### Discrepancies

**1. Module Structure - `posts/list.py` does not exist (High)**
- **Doc**: `admin/posts/list.py - Post listing`
- **Actual**: Post listing is in `admin/posts/__init__.py` as `dashboard()` function
- No separate list.py file exists

**2. Page Routes - Incorrect paths (Medium)**
- **Doc**: `POST /admin/pages/create`, `POST /admin/pages/rename/<int:page_id>`
- **Actual**: Routes are `GET/POST /admin/pages/new`, `GET/POST /admin/pages/edit/<int:page_id>`, `POST /admin/pages/delete/<int:page_id>`

### Improvement Opportunities

**1. Missing route in docs: `POST /admin/series/<int:series_id>/reorder`**
- Actual code has this AJAX endpoint for reordering series posts
- Not documented

**2. Preview route documentation could be clearer**
- Doc says `GET /admin/preview/<int:post_id>?share=1`
- Actual: the share=1 parameter is processed by admin, returns JSON with preview URL - it's not passed to public preview

---

## api-routes.md

### Verified Claims
- Posts API: GET /api/posts, GET /api/posts/<id>, POST /api/posts, PUT /api/posts/<id>, DELETE /api/posts/<id>
- Stats API: GET /api/stats
- Auth API: POST /api/auth
- All query parameters documented correctly
- Response formats documented correctly
- Rate limiting for API operations (20/min reads, 10/min writes)

### Discrepancies

**1. Subscribers API - POST endpoint incorrectly documented (Medium)**
- **Doc**: Lists `POST /api/subscribers` as "Create new subscriber"
- **Actual**: `app/routes/api/subscribers.py` only has `GET /api/subscribers` and `DELETE /api/subscribers/<int:subscriber_id>`
- POST endpoint does not exist in the API

**2. Rate Limit documentation mentions `ADMIN_RATE_LIMITS` from config (Low)**
- Doc says rate limits come from `app/config.py` `ADMIN_RATE_LIMITS`
- Actual: Rate limits are hardcoded in each route file (e.g., `DEFAULT_LIMIT = "20 per minute"`)
- Minor documentation discrepancy

### Bugs Found

**1. Rate limit for `/api/track-share` not documented**
- Actual: `POST /api/track-share` in public routes has `20 per minute` limit
- Not mentioned in API rate limits table

**2. API auth uses header `X-API-Key` but docs don't specify (Low)**
- Works correctly but could be clearer

### Improvement Opportunities

**1. Document the API key header requirement more explicitly**
- Currently only implicit in the auth endpoint description

**2. Document webhook event triggers for publish/unpublish**
- API code triggers `post.published`/`post.unpublished` webhook events on status change
- Not documented

---

## public-routes.md

### Verified Claims
- Browse routes: `/`, `/page/<page>`, `/tag/<slug>`, `/tag/<slug>/<page>`, `/archive`, `/series/<slug>`, `/page/<slug>`, `/search`
- Post routes: `/post/<slug>`, `/s/<code>`, `/api/track-share`
- Subscribe: `/subscribe` (POST only), `/confirm/<token>`, `/unsubscribe/<token>`
- Meta: `/sitemap.xml`, `/robots.txt`, `/health`, `/metrics`, `/favicon.ico`
- Comments: `POST /post/<slug>/comment`
- Cache settings (5 minutes for sitemap)
- FTS5 search documented

### Discrepancies

**1. File/Route mapping table is misleading (Low)**
- **Doc**: Lists `browse.py` and `posts.py` with route assignments
- **Actual**: Routes are spread across `browse.py`, `posts.py`, `subscribe.py`, `meta.py`, `comments.py` via `register_*` functions
- The table is approximately correct but not precise about which file owns which routes

**2. Preview route auth description slightly off (Low)**
- **Doc**: "Auth: HMAC token-based AND admin session required (`session.get('admin_user_id')`)"
- **Actual**: Code checks `session.get('admin_user_id')` at line 128, but also validates HMAC token
- Description is essentially correct but the session check happens after token validation

### Improvement Opportunities

**1. Document `/preview/<int:post_id>` public preview route**
- The public preview via signed URL exists but isn't clearly documented
- Only admin preview via `/admin/preview/<id>` is documented

**2. Health check - `?detailed=true` vs `?detailed=1`**
- Code accepts `?detailed=true` (line 197: `detailed.lower() == "true"`)
- Could note both variants work

---

## rss-feeds.md

### Verified Claims
- All three feed formats: RSS 2.0 (`/rss`), Atom (`/atom`), JSON (`/json`)
- Feed caching: 5 minutes (300 seconds)
- Example XML/JSON structures correct
- ETag support implemented
- Content is HTML-cleaned before inclusion

### Discrepancies

**None found** - documentation accurately reflects implementation.

### Improvement Opportunities

**1. JSON Feed uses `id` as slug instead of full URL**
- Doc example shows `"id": "http://example.com/post/post-slug"`
- Actual code uses `"id": item["slug"]` (just the slug)
- Minor but the example is misleading

**2. RSS feed `<guid isPermaLink="false">` uses slug, not full URL**
- Doc shows `"guid isPermaLink="false">http://example.com/post/post-slug"`
- Actual: uses just the slug as guid

---

## Summary

| Priority | Issue | Document |
|----------|-------|----------|
| High | `posts/list.py` doesn't exist - post listing is in `__init__.py` | admin-routes.md |
| Medium | Subscriber API POST endpoint doesn't exist | api-routes.md |
| Medium | Page routes have wrong paths in docs | admin-routes.md |
| Low | JSON Feed `id` field uses slug, not full URL (doc example misleading) | rss-feeds.md |
| Low | Rate limit for `/api/track-share` not documented | api-routes.md |
| Low | File/route mapping in public-routes.md imprecise | public-routes.md |

## Bugs Found

1. **Minor**: Documentation example for JSON Feed `id` field shows full URL but code uses slug only
2. **Minor**: API docs list non-existent `POST /api/subscribers` endpoint

## Overall Assessment

The architecture documentation is largely accurate. The main issues are:
- Module structure in admin-routes.md includes a non-existent file (`posts/list.py`)
- Page routes use incorrect paths in admin-routes.md
- API subscriber endpoints are slightly misdocumented

All actual route implementations match the documented functionality with minor exceptions noted above.