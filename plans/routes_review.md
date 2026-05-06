# Routes Architecture Review

## Summary

This review compares the architecture documents in `/home/sugarwookie/projects/blog/architecture/routes/` against the actual route implementations in the codebase. The documents provide a good high-level overview but contain several discrepancies in exact route paths, HTTP methods, and response formats. Most critically, the RSS/Feeds document claims endpoints (`/rss`, `/json`) that do not exist in the codebase.

---

## Verified Claims

### Admin Routes - Auth (`auth.py`)
- **Login/Logout**: Routes exist with correct methods. Login at `/admin/login` (GET/POST), Logout at `/admin/logout` (POST only). `app/routes/admin/auth.py:32,99`
- **2FA Setup/Verify**: Routes exist at `/admin/2fa/setup` and `/admin/2fa/verify`. `app/routes/admin/auth.py:263,311`
- **Password Reset**: Routes exist at `/admin/forgot-password` and `/admin/reset/<token>`. `app/routes/admin/auth.py:155,198`

### Admin Routes - Subscribers
- Routes exist as documented: `GET /admin/subscribers` and `POST /admin/subscribers/export`. `app/routes/admin/subscribers.py:18,83`

### Admin Routes - Sessions
- `GET /admin/sessions` exists. `app/routes/admin/sessions.py:15`

### Admin Routes - Media
- Routes exist as documented: `GET /admin/media`, `POST /admin/media/upload`, `DELETE /admin/media/<filename>`. `app/routes/admin/media.py:93,130,160`

### Admin Routes - Backup (Core)
- `GET /admin/backup`, `POST /admin/backup/create`, `POST /admin/backup/restore` exist. `app/routes/admin/backup.py:23,53,107`

### Admin Routes - Analytics
- `GET /admin/analytics` exists. `app/routes/admin/analytics.py:9`

### Admin Routes - Newsletter
- `POST /admin/newsletter-test` and `GET /admin/newsletter/preview` exist (note: route is `/newsletter-test` not `/newsletter/send`). `app/routes/admin/newsletter.py:24,70`

### Admin Routes - Settings
- `GET /admin/settings` and `POST /admin/settings/theme` exist. `app/routes/admin/settings.py:14,41`

### Admin Routes - Audit
- `GET /admin/audit` exists. `app/routes/admin/audit.py:13`

### Admin Routes - Comments
- Routes exist: `GET /admin/comments`, `POST /admin/comments/<int:comment_id>/approve`, `POST /admin/comments/<int:comment_id>/delete`. `app/routes/admin/comments.py:15,51,70`

### Public Routes - Browse
- Home page `/` exists. `app/routes/public/browse.py:96`
- Tag pages `/tag/<slug>` exist. `app/routes/public/browse.py:221`
- Search `/search` exists. `app/routes/public/browse.py:250`
- Archive `/archive` exists. `app/routes/public/browse.py:121`
- Static pages `/page/<slug>` exist. `app/routes/public/browse.py:208`

### Public Routes - Posts
- Post page `/post/<slug>` exists. `app/routes/public/posts.py:46`
- Preview `/preview/<int:post_id>` exists. `app/routes/public/posts.py:94`
- Short URL `/s/<code>` exists. `app/routes/public/posts.py:142`

### Public Routes - Meta
- `/robots.txt` exists. `app/routes/public/meta.py:95`
- `/sitemap.xml` exists. `app/routes/public/meta.py:177`
- `/health` exists. `app/routes/public/meta.py:191`

### API Routes - Posts
- All CRUD endpoints exist with correct paths and methods. `app/routes/api/posts.py:50,87,105,207,294`

### API Routes - Authentication
- `POST /api/auth` exists with `X-API-Key` header. `app/routes/api/auth.py:10-25`

---

## Discrepancies Found

### 1. Admin Routes - Post Editor Routes (BUG)
**Document says:**
- `GET /admin/posts/new`
- `GET /admin/posts/<int:post_id>/edit`

**Actual routes:**
- `GET /admin/new` (line 137 of `app/routes/admin/posts/editor.py`)
- `GET /admin/edit/<int:post_id>` (line 215 of `app/routes/admin/posts/editor.py`)

**Priority: HIGH** - Routes are non-functional as documented.

### 2. Admin Routes - Post Revisions Route Path
**Document says:**
- `GET /admin/posts/<int:post_id>/revisions/<int:rev_id>`

**Actual route:**
- `GET /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore` (line 75 of `app/routes/admin/posts/revisions.py`)
- Uses `revision_id` not `rev_id`
- Includes `/restore` suffix

**Priority: HIGH** - Restoration endpoint has wrong path.

### 3. Admin Routes - Tag Delete Method
**Document says:**
- `DELETE /admin/tags/<int:tag_id>`

**Actual route:**
- `POST /admin/tags/delete/<int:tag_id>` (line 87 of `app/routes/admin/tags.py`)

**Priority: MEDIUM** - HTTP method and path both incorrect.

### 4. Admin Routes - User Management Paths
**Document says:**
- `POST /admin/users`, `PUT /admin/users/<int:user_id>`, `DELETE /admin/users/<int:user_id>`

**Actual routes:**
- `POST /admin/users/create` (line 41 of `app/routes/admin/users.py`)
- `POST /admin/users/delete/<int:user_id>` (line 91)
- `POST /admin/users/<int:user_id>/promote` (line 125)
- `POST /admin/users/<int:user_id>/demote` (line 155)
- `POST /admin/users/<int:user_id>/make-owner` (line 192)
- `POST /admin/users/password/<int:user_id>` (line 242)
- No `PUT` route exists

**Priority: HIGH** - None of the documented user routes match actual implementation.

### 5. Admin Routes - Backup Missing Routes
**Document lists only:**
- `GET /admin/backup`
- `POST /admin/backup/create`
- `POST /admin/backup/restore`

**Actual routes (also exist):**
- `GET /admin/backup/download/<filename>` (line 84 of `app/routes/admin/backup.py`)
- `POST /admin/backup/delete/<filename>` (line 171)
- `GET /admin/backup/verify/<filename>` (line 199)
- `GET /admin/backup/verify-all` (line 227)

**Priority: LOW** - Documentation is incomplete, not incorrect.

### 6. Public Routes - Comment Submission Path
**Document says:**
- `POST /comment/<int:post_id>`

**Actual route:**
- `POST /post/<slug>/comment` (line 12 of `app/routes/public/comments.py`)

**Priority: HIGH** - Route uses slug not post_id.

### 7. Public Routes - Subscribe Form
**Document says:**
- `GET /subscribe` - Show subscription form
- `POST /subscribe` - Handle new subscription

**Actual implementation:**
- Only `POST /subscribe` exists (line 55 of `app/routes/public/subscribe.py`)
- No `GET /subscribe` route for showing the form

**Priority: MEDIUM** - Missing GET handler for subscription form.

### 8. RSS/Feeds - `/rss` Does Not Exist (BUG)
**Document says:** Route `/rss` provides RSS 2.0 feed.

**Actual implementation:**
- Only `@rss.route("/atom")` exists in `app/routes/rss.py` (line 84)
- No `/rss` route exists anywhere in codebase

**Priority: CRITICAL** - Documented endpoint does not exist.

### 9. RSS/Feeds - `/json` Does Not Exist (BUG)
**Document says:** Route `/json` provides JSON Feed format.

**Actual implementation:**
- No `/json` route exists anywhere in codebase

**Priority: CRITICAL** - Documented endpoint does not exist.

### 10. RSS/Feeds - Cache Duration Mismatch
**Document says:** "All feeds are cached for 5 minutes."

**Actual implementation:**
- Atom feed is cached for 5 minutes (300 seconds) via `@flask_cache.cached(timeout=300,...)` at line 59 of `app/routes/rss.py`
- But `/rss` and `/json` don't exist, so cache duration claim is moot

**Priority: LOW** - Claim is correct for existing Atom feed only.

---

## Bugs Identified

### BUG-1: Missing RSS 2.0 Feed Endpoint
**File:** `app/routes/rss.py`
**Severity:** CRITICAL
**Description:** The architecture document claims an RSS 2.0 feed exists at `/rss`, but this endpoint does not exist in the codebase. Only the Atom feed at `/atom` is implemented.

### BUG-2: Missing JSON Feed Endpoint
**File:** `app/routes/rss.py`
**Severity:** CRITICAL
**Description:** The architecture document claims a JSON Feed exists at `/json`, but this endpoint does not exist in the codebase.

### BUG-3: Comment Route Path Mismatch
**File:** `app/routes/public/comments.py:12`
**Severity:** HIGH
**Description:** Public comment submission uses `/post/<slug>/comment` but the architecture document claims `/comment/<int:post_id>`. The document should use slug not post_id for consistency with other post routes.

### BUG-4: Post Editor Routes Completely Mismatched
**File:** `app/routes/admin/posts/editor.py:137,215`
**Severity:** HIGH
**Description:** The architecture document claims admin post editor routes are `/admin/posts/new` and `/admin/posts/<id>/edit`, but actual routes are `/admin/new` and `/admin/edit/<id>/edit`. This is a complete path mismatch that would confuse any developer relying on the documentation.

### BUG-5: User Management Routes Mismatched
**File:** `app/routes/admin/users.py`
**Severity:** HIGH
**Description:** Documented REST-style user routes (`PUT /admin/users/<id>`) don't exist. Actual implementation uses action-based routes like `/promote`, `/demote`, `/make-owner`, etc.

---

## Improvement Recommendations

### REC-1: Add RSS 2.0 Feed Endpoint
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Description:** Implement the missing `/rss` endpoint to match documentation. Use the existing Atom feed as a template.

### REC-2: Add JSON Feed Endpoint
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Description:** Implement the missing `/json` endpoint for JSON Feed format per spec.

### REC-3: Add GET /subscribe Route
**Priority:** MEDIUM
**Files:** `app/routes/public/subscribe.py`
**Description:** Add a GET handler for `/subscribe` to display the subscription form. Currently only POST is defined.

### REC-4: Update Documentation to Match Actual Routes
**Priority:** HIGH
**Files:** `architecture/routes/admin-routes.md`
**Description:** Correct all admin post routes:
- `/admin/posts/new` -> `/admin/new`
- `/admin/posts/<id>/edit` -> `/admin/edit/<id>`
- `/admin/posts/<id>/revisions/<rev_id>` -> `/admin/posts/<id>/revisions/<revision_id>/restore`

### REC-5: Update User Management Documentation
**Priority:** HIGH
**Files:** `architecture/routes/admin-routes.md`
**Description:** Document actual action-based routes instead of REST-style routes. Include all actual routes:
- `/admin/users/create` (POST)
- `/admin/users/delete/<id>` (POST)
- `/admin/users/<id>/promote` (POST)
- `/admin/users/<id>/demote` (POST)
- `/admin/users/<id>/make-owner` (POST)
- `/admin/users/password/<id>` (POST)

### REC-6: Add Missing Backup Routes to Documentation
**Priority:** LOW
**Files:** `architecture/routes/admin-routes.md`
**Description:** Document the additional backup routes:
- `GET /admin/backup/download/<filename>`
- `POST /admin/backup/delete/<filename>`
- `GET /admin/backup/verify/<filename>`
- `GET /admin/backup/verify-all`

### REC-7: Document Static Page Route
**Priority:** LOW
**Files:** `architecture/routes/public-routes.md`
**Description:** The browse.py file includes `/page/<slug>` route for static pages, but the architecture document doesn't mention this.

### REC-8: Update Stats API Response Documentation
**Priority:** MEDIUM
**Files:** `architecture/routes/api-routes.md`
**Description:** The documented response shows `total_page_views` but actual response (line 54-62 of `stats.py`) returns `total_views`, `total_shares`, `views_this_month`, `new_subscribers_this_month`.

---

## Priority Summary

| Item | Priority | Type |
|------|----------|------|
| Add `/rss` endpoint | CRITICAL | Bug |
| Add `/json` endpoint | CRITICAL | Bug |
| Fix post editor routes | HIGH | Bug |
| Fix comment route path | HIGH | Bug |
| Fix user management routes | HIGH | Bug |
| Add GET /subscribe | MEDIUM | Discrepancy |
| Fix tag delete route | MEDIUM | Discrepancy |
| Update Stats API docs | MEDIUM | Discrepancy |
| Document missing backup routes | LOW | Gap |
| Document static page route | LOW | Gap |
| Cache duration note | LOW | Gap |

---

## Files Referenced

| File | Purpose |
|------|---------|
| `app/routes/admin/__init__.py` | Blueprint registration |
| `app/routes/admin/auth.py` | Login, logout, 2FA, password reset |
| `app/routes/admin/posts/editor.py` | New/edit post routes |
| `app/routes/admin/posts/manage.py` | Delete, preview routes |
| `app/routes/admin/posts/revisions.py` | Revision history and restore |
| `app/routes/admin/posts/__init__.py` | Dashboard |
| `app/routes/admin/subscribers.py` | Subscriber management |
| `app/routes/admin/tags.py` | Tag CRUD |
| `app/routes/admin/users.py` | User management |
| `app/routes/admin/sessions.py` | Session monitoring |
| `app/routes/admin/media.py` | Media library |
| `app/routes/admin/backup.py` | Backup/restore |
| `app/routes/admin/analytics.py` | Dashboard analytics |
| `app/routes/admin/newsletter.py` | Newsletter test/preview |
| `app/routes/admin/settings.py` | Theme settings |
| `app/routes/admin/pages.py` | Static pages |
| `app/routes/admin/series.py` | Post series |
| `app/routes/admin/audit.py` | Audit log |
| `app/routes/admin/comments.py` | Comment moderation |
| `app/routes/public/browse.py` | Home, archive, tags, search |
| `app/routes/public/posts.py` | Post view, preview |
| `app/routes/public/subscribe.py` | Newsletter subscription |
| `app/routes/public/meta.py` | robots.txt, sitemap, health |
| `app/routes/public/comments.py` | Comment submission |
| `app/routes/api/posts.py` | Posts API |
| `app/routes/api/subscribers.py` | Subscribers API |
| `app/routes/api/stats.py` | Stats API |
| `app/routes/api/auth.py` | API authentication |
| `app/routes/rss.py` | Atom feed (only) |
