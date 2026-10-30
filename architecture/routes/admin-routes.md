# Admin Routes (`app/routes/admin/`)

The admin module provides the dashboard and management interfaces.

## Module Structure

```
admin/
├── __init__.py          # Blueprint registration, auth decorators
├── auth.py              # Login, logout, 2FA, password reset
├── posts/               # Post management
│   ├── __init__.py      # Dashboard and bulk operations
│   ├── editor.py        # Post editor, markdown preview
│   ├── manage.py        # Post delete, preview
│   └── revisions.py     # Post revisions
├── subscribers.py       # Subscriber management
├── tags.py              # Tag CRUD
├── users.py             # User management
├── sessions.py          # Admin session monitoring
├── media.py             # Media upload/management
├── backup.py            # Backup/restore
├── analytics.py         # Dashboard analytics
├── newsletter.py        # Newsletter preview/test
├── settings.py          # Theme, custom CSS
├── pages.py             # Static page management
├── projects.py          # Project management and draft preview
├── project_docs.py      # Local docs, image assets, GitHub docs sync and release refresh
├── series.py            # Post series management
├── audit.py             # Audit log viewer
├── comments.py          # Comment moderation
└── helpers/             # Shared helper modules
    ├── __init__.py
    ├── analytics.py
    ├── dashboard.py
    ├── images.py
    ├── posts.py
    ├── shared.py
    ├── slug.py
    └── tags.py
```

## Auth Routes (`auth.py`)

### Login
- **Route**: `GET/POST /admin/login`
- **Purpose**: Admin authentication
- **Features**: Account lockout, failed login tracking

### Logout
- **Route**: `POST /admin/logout`
- **Purpose**: End admin session
- **Auth**: CSRF protection required

### 2FA Setup
- **Route**: `GET/POST /admin/2fa/setup`
- **Purpose**: Setup TOTP 2FA

### 2FA Verify
- **Route**: `GET/POST /admin/2fa/verify`
- **Purpose**: Verify 2FA code

### Login 2FA
- **Route**: `GET/POST /admin/login-2fa`
- **Purpose**: TOTP verification during login flow

### 2FA Backup Codes
- **Route**: `GET /admin/2fa/backup-codes`
- **Purpose**: Display backup codes

### 2FA Disable
- **Route**: `GET/POST /admin/2fa/disable`
- **Purpose**: Disable 2FA for account

### Forgot Password
- **Route**: `GET/POST /admin/forgot-password`
- **Purpose**: Request password reset

### Reset Password
- **Route**: `GET/POST /admin/reset/<token>`
- **Purpose**: Reset password with token

### Newsletter Reset
- **Route**: `POST /admin/newsletter-reset/<int:post_id>`
- **Purpose**: Reset newsletter status for a post

## Post Management (`posts/`)

### Post Editor (`editor.py`)
- **Route**: `GET/POST /admin/new`
- **Route**: `GET/POST /admin/edit/<int:post_id>`
- **Purpose**: Create/edit posts
- **Features**: Markdown editor, tag selection, image upload, series assignment

### Markdown Preview (`editor.py`)
- **Route**: `POST /admin/preview-markdown`
- **Purpose**: Render markdown preview for live editing (AJAX endpoint)

### Optional AI Authoring (`editor.py`)
- **Route**: `POST /admin/ai-assist`
- **Purpose**: Return an unsaved-post title, TL;DR or taxonomy-aware tag suggestions on explicit editor requests
- **Access**: `@author_required`, global CSRF validation, optional per-user rate limit (`ai.rate_limit_per_user`, unlimited by default); edit requests verify post ownership
- **Availability**: AI is off by default; a blank model hides the controls and the endpoint fails closed. Setting a model opts in. Local OpenAI-compatible servers work without an API key; OpenCode Go requires `OPENCODE_GO_API_KEY`.
- **Data flow**: Current title and Markdown body are sent to the configured endpoint only after the author clicks a control. Suggestions are reviewed and applied in the browser; only normal post Save persists them.
- **Safety**: No stored post body is fetched, no provider response is persisted, and no tag rows are created by inference. See [AI authoring service](../services/overview.md#optional-ai-authoring) for bounds, provider policy, and the rationale for unlimited-by-default app throttling.

### Post Delete (`manage.py`)
- **Route**: `POST /admin/delete/<int:post_id>`
- **Purpose**: Delete a post

### Post Preview (`manage.py`)
- **Route**: `GET /admin/preview/<int:post_id>`
- **Route**: `GET /admin/preview/<int:post_id>?share=1`
- **Purpose**: Preview post before publishing, with optional shareable URL
- **Shareable Preview URL**: When `?share=1` is passed, returns a signed URL valid for `PREVIEW_TOKEN_EXPIRY_DAYS` days (default: 7)
- **Token Generation**: HMAC-SHA256 signature using `SECRET_KEY` — message is `"{post_id}:{expiry_timestamp}"`, signature is base64-urlsafe encoded (`app/routes/admin/posts/manage.py:35-47`)

### Post List (`__init__.py`)
- **Route**: `GET /admin/`
- **Route**: `POST /admin/bulk`
- **Purpose**: List all posts with filtering
- **Location**: `app/routes/admin/posts/__init__.py:dashboard()`
- **Filters**: Published, drafts, scheduled
- **Bulk Ops**: Publish, unpublish, delete, unschedule selected posts

### Post Revisions (`revisions.py`)
- **Route**: `GET /admin/posts/<int:post_id>/revisions`
- **Route**: `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore`
- **Purpose**: View post edit history, restore previous revisions
- **Diff**: Side-by-side diff view

## Subscriber Management (`subscribers.py`)

- **Route**: `GET /admin/subscribers`
- **Route**: `GET /admin/subscribers/export`
- **Route**: `POST /admin/subscribers/bulk`
- **Route**: `POST /admin/subscribers/delete/<int:sub_id>`
- **Purpose**: View, export, and manage subscribers

## Tag Management (`tags.py`)

- **Route**: `GET /admin/tags`
- **Route**: `POST /admin/tags/create`
- **Route**: `POST /admin/tags/rename/<int:tag_id>`
- **Route**: `POST /admin/tags/delete/<int:tag_id>`
- **Purpose**: CRUD operations for tags

## User Management (`users.py`)

- **Route**: `GET /admin/users`
- **Route**: `POST /admin/users/create`
- **Route**: `POST /admin/users/delete/<int:user_id>`
- **Route**: `POST /admin/users/<int:user_id>/promote`
- **Route**: `POST /admin/users/<int:user_id>/demote`
- **Route**: `POST /admin/users/<int:user_id>/make-owner`
- **Route**: `POST /admin/users/password/<int:user_id>`
- **Purpose**: Manage admin users

## Session Monitoring (`sessions.py`)

- **Route**: `GET /admin/sessions`
- **Route**: `POST /admin/sessions/revoke/<int:sess_id>`
- **Purpose**: View active admin sessions and revoke sessions
- **Features**: IP binding, session termination

## Admin Session IP Binding (`__init__.py:25-55`)

The `admin_required` decorator enforces session IP binding to detect session hijacking. Controlled by the `SESSION_IP_BINDING` config option (set via environment variable or `config.toml`).

### Mode: `enforce`

When the client IP changes mid-session:

1. Looks up the `AdminSession` record by `session_id`
2. Deletes the session record from the database
3. Calls `logout_user()` and `session.clear()`
4. Flashes an error: "Session invalidated due to IP address change."
5. Redirects to the admin login page

This is the strictest mode — any IP change (e.g., VPN reconnect, mobile network switch) immediately terminates the session.

### Mode: `warn`

When the client IP changes mid-session:

1. Logs a warning: `IP address changed for admin session <sid>: expected <old_ip>, got <new_ip>`
2. Request continues normally — the session is **not** terminated

This mode is suitable for environments where IP addresses change frequently (e.g., mobile networks, load balancers) but you still want visibility into session anomalies.

### Mode: disabled (any other value)

If `SESSION_IP_BINDING` is not set or set to any value other than `"enforce"` or `"warn"`, IP binding checks are skipped entirely.

### Implementation Notes

- IP is compared from `session["admin_session_ip"]` vs `request.remote_addr`
- The check only runs if both `stored_ip` and `current_ip` are truthy (non-None, non-empty)
- In `enforce` mode, `IntegrityError` and `OperationalError` from the session delete are caught and rolled back gracefully

## Media Management (`media.py`)

- **Route**: `GET /admin/media` — paginated media manager, filterable by type and search
- **Route**: `GET /admin/media/items` — author/admin-authenticated JSON catalog for editor pickers
- **Route**: `POST /admin/media/upload` — author/admin-authenticated, CSRF-protected image/video/other upload; form `category` selects the validation/storage policy; JSON clients send `Accept: application/json`
- **Route**: `POST /admin/media/delete/<filename>`
- **Purpose**: Manage all uploaded files as Images, Videos, or Other
- **Features**: PNG/JPEG/GIF/WebP image processing; MP4/WebM signature validation without image processing; arbitrary files in the Other category and safe download-only links. The shared post/page editor uses distinct Media and Attachment pickers over the same categorized catalog; Media inserts inline images or controlled video markup, while Attachment always inserts a forced-download Markdown link.
- **Download route**: public `GET /media/download/<key>` accepts generated attachment keys or signature-validated supported images/videos; arbitrary unknown storage keys are rejected. Every response uses attachment disposition, octet-stream content type, and `nosniff`.
- **Orphan cleanup**: `cleanup_orphaned_images` delegates to `app.services.operations.media` (Phase C service extraction)

## Backup Management (`backup.py`)

- **Route**: `GET /admin/backup`
- **Route**: `POST /admin/backup/create`
- **Route**: `POST /admin/backup/restore/<filename>`
- **Route**: `GET /admin/backup/download/<filename>`
- **Route**: `POST /admin/backup/delete/<filename>`
- **Route**: `GET /admin/backup/verify/<filename>`
- **Route**: `GET /admin/backup/verify-all`
- **Purpose**: Database backup/restore
- **Features**: Compression, encryption (AES-256-GCM), integrity verification
- **Verify endpoints return**: JSON with `valid` (boolean) and `message` (string) fields

## Analytics (`analytics.py`)

- **Route**: `GET /admin/analytics`
- **Purpose**: Dashboard charts and statistics
- **Data**: Page views, popular posts, traffic sources

## Newsletter (`newsletter.py`)

- **Route**: `GET /admin/newsletter/preview`
- **Route**: `POST /admin/newsletter-test`
- **Purpose**: Preview and send newsletters
- **Preview**: Renders the newsletter HTML in-browser (no email sent)
- **Test**: Sends an actual email to the admin's address for delivery verification

## Settings (`settings.py`)

- **Route**: `GET /admin/settings`
- **Route**: `POST /admin/settings/theme`
- **Route**: `POST /admin/settings/theme/preview`
- **Route**: `POST /admin/settings/theme/refresh`
- **Purpose**: View and update theme, custom CSS
- **Theme Selection**: Registry-based dark/light theme pair from 50+ bundled Halloy themes; external themes override bundled with same name
- **Syntax Themes (Prism-based)**: Retired — there is no syntax theme setting, and `app/routes/admin/settings.py` carries no Prism palette list. The Prism token colours follow the selected theme through `app/static/css/prism.css`.

### Theme Preview (`settings.py`)
- **Route**: `POST /admin/settings/theme/preview`
- **Purpose**: Preview theme CSS variables without persisting changes (AJAX endpoint)
- **Auth**: Admin authentication required
- **Form params**:
  - `theme_dark_name`: Dark theme name (must exist in registry)
  - `theme_light_name`: Light theme name (must exist in registry)
- **Returns**: JSON with:
  - `dark_css` / `light_css`: CSS variable declarations for each theme
  - `dark_name` / `light_name`: Canonical resolved theme names
  - `dark_is_dark` / `light_is_dark`: Boolean classification of each theme
  - `warnings`: Global warnings (e.g., both themes same classification)
  - `dark_warnings` / `light_warnings`: Per-theme WCAG contrast warnings with ratios
- **Limits**: CSS output is truncated at 50KB per theme
- **Non-persistent**: No database changes; validates against the live registry only

### Theme Refresh (`settings.py`)
- **Route**: `POST /admin/settings/theme/refresh`
- **Purpose**: Invalidate and rebuild the theme registry, report changes
- **Auth**: Admin authentication required
- **Behavior**:
  1. Snapshots current registry theme names
  2. Calls `ThemeService.refresh_registry()` to rebuild from disk
  3. Diffs old vs new theme sets and reports added/removed themes via flash messages
  4. Counts external themes that override bundled themes
  5. Warns if the currently selected dark or light theme disappeared, showing the effective fallback name
  6. Invalidates the settings cache so subsequent page loads reflect the new registry
- **Returns**: Redirect to settings page with flash messages summarizing changes

## Audit Log (`audit.py`)

- **Route**: `GET /admin/audit`
- **Purpose**: View admin action audit trail

## Static Page Management (`pages.py`)

- **Route**: `GET /admin/pages`
- **Route**: `GET/POST /admin/pages/new`
- **Route**: `GET/POST /admin/pages/edit/<int:page_id>`
- **Route**: `POST /admin/pages/delete/<int:page_id>`
- **Purpose**: Create and manage static pages

## Project Management (`projects.py`)

- **Routes**: `GET /admin/projects`, `GET/POST /admin/projects/new`, `GET/POST /admin/projects/edit/<id>`, `POST /admin/projects/delete/<id>`
- **Draft preview**: `GET /admin/projects/preview/<id>` is authenticated
- **Purpose**: Manage project metadata, Markdown content, media, layout, and scoped theme choices

## Project Documentation and Releases (`project_docs.py`)

- **Routes**: Admin project docs page, local document create/edit/delete/preview, project asset upload/removal, docs source settings and manual GitHub snapshot sync, release catalog settings and metadata refresh
- **Protection**: Admin-only handlers; POSTs receive global CSRF checks
- **Purpose**: Manage local docs and cached public GitHub metadata; sync runs only from explicit admin actions
- **Limits**: Release binaries remain on GitHub; no mirror or installer manifest is provided

## Series Management (`series.py`)

- **Route**: `GET /admin/series`
- **Route**: `GET/POST /admin/series/new`
- **Route**: `GET/POST /admin/series/<int:series_id>/edit`
- **Route**: `POST /admin/series/<int:series_id>/delete`
- **Route**: `GET/POST /admin/series/<int:series_id>/posts`
- **Route**: `POST /admin/series/<int:series_id>/reorder`
- **Purpose**: Create and manage post series (ordered collections of posts)

## Comment Moderation (`comments.py`)

- **Route**: `GET /admin/comments`
- **Route**: `POST /admin/comments/<int:comment_id>/approve`
- **Route**: `POST /admin/comments/<int:comment_id>/delete`
- **Purpose**: Moderate comments

## Helpers (`helpers/`)

Shared helper modules extracted from route files:

| Module | Purpose |
|--------|---------|
| `analytics.py` | Analytics cache invalidation |
| `dashboard.py` | Dashboard cache invalidation |
| `images.py` | Image type detection, file validation, saving |
| `posts.py` | Post query building, applying post updates |
| `shared.py` | Constants (`ALLOWED_EXTENSIONS`, `TAG_NAME_REGEX`, `BACKUP_FILENAME_RE`), referrer categorization, password complexity checks, backup directory resolution |
| `slug.py` | Unique slug generation |
| `tags.py` | Tag name validation, orphan cleanup, get-or-create tags |

All public functions are re-exported via `helpers/__init__.py` for backward compatibility.

## Rate Limits

Flask-Limiter enforces per-IP rate limits across all routes. Limits are applied via `@limiter.limit()` decorators on individual route handlers.

| Endpoint | Limit | Key | Source |
|----------|-------|-----|--------|
| Admin login | proxy | per-IP | `limit_req zone=login` in nginx, not the application |
| 2FA login | proxy | per-IP | `limit_req zone=admin` covers `/admin/` |
| Forgot password | proxy | per-IP | `limit_req zone=admin` covers `/admin/` |
| Public browse | 60/min | per-IP | `app/routes/public/browse.py` |
| Archive | 30/min | per-IP | `app/routes/public/browse.py:124` |
| Search | 20/min | per-IP | `app/routes/public/browse.py:263` |
| Subscribe | 10/min | per-IP | `app/routes/public/subscribe.py:56` |
| Unsubscribe/confirm | 5/min | per-IP | `app/routes/public/subscribe.py:143,189` |
| Comments | dual-key | per-IP + per-post | `app/routes/public/comments.py:78-79` |
| API reads | 20/min | per-IP | `DEFAULT_LIMIT` in `app/routes/api/*.py` |
| API writes | 10/min | per-IP | `WRITE_LIMIT` in `app/routes/api/*.py` |
| Public posts | 60/min | per-IP | `app/routes/public/posts.py:47,156` |
| Post search results | 30/min | per-IP | `app/routes/public/posts.py:102` |
| Post share | 20/min | per-IP | `app/routes/public/posts.py:179` |
| Sitemap/robots/health | 60/min | per-IP | `app/routes/public/meta.py` |

The login routes are **not** rate limited by the application. The deployment is expected to sit behind a reverse proxy or WAF that limits them; the shipped nginx configuration applies a `limit_req` zone to `/login` and `/admin/login`. The application keeps the per-account lockout (`MAX_FAILED_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES`) and `LOGIN_FAILURE_DELAY`.

Comment rate limits are configurable via `config.toml` (`comments.rate_limit_per_ip`, `comments.rate_limit_per_post`). Defaults: 5/min per-IP, 3/min per-post.

The `ADMIN_RATE_LIMITS` dict in `app/config_legacy.py` holds the API write/read limits. They are read only by the `AdminRateLimiter` class in `app/middleware/rate_limit.py`, whose `limit_by_type` decorator is a no-op wrapper - nothing calls it. There is no `login` key; the login routes are limited by the proxy.

## See Also
- [Public Routes](public-routes.md) - Public blog routes
- [API Routes](api-routes.md) - REST API
- [RSS/Feeds](rss-feeds.md) - Feeds
