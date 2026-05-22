# Admin Routes (`app/routes/admin/`)

The admin module provides the dashboard and management interfaces.

## Module Structure

```
admin/
├── __init__.py          # Blueprint registration
├── auth.py              # Login, logout, 2FA
├── posts/               # Post management
│   ├── __init__.py      # Route registration + dashboard/list
│   ├── editor.py        # Post editor
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
├── series.py            # Post series management
├── audit.py             # Audit log viewer
└── comments.py          # Comment moderation
```

## Auth Routes (`auth.py`)

### Login
- **Route**: `GET /admin/login`
- **Route**: `POST /admin/login`
- **Purpose**: Admin authentication
- **Features**: Account lockout, failed login tracking

### Logout
- **Route**: `POST /admin/logout`
- **Purpose**: End admin session
- **Auth**: CSRF protection required

### 2FA Setup
- **Route**: `GET /admin/2fa/setup` (POST for setup confirmation)
- **Purpose**: Setup TOTP 2FA

### 2FA Verify
- **Route**: `GET /admin/2fa/verify` (POST for verification)
- **Purpose**: Verify 2FA code

### Login 2FA
- **Route**: `GET /admin/login-2fa` (POST for verification)
- **Purpose**: TOTP verification during login flow

### 2FA Backup Codes
- **Route**: `GET /admin/2fa/backup-codes`
- **Purpose**: Display backup codes

### 2FA Disable
- **Route**: `GET /admin/2fa/disable` (POST to confirm disable)
- **Purpose**: Disable 2FA for account

### Forgot Password
- **Route**: `GET /admin/forgot-password`
- **Route**: `POST /admin/forgot-password`
- **Purpose**: Request password reset

### Reset Password
- **Route**: `GET /admin/reset/<token>`
- **Route**: `POST /admin/reset/<token>`
- **Purpose**: Reset password with token

### Newsletter Reset
- **Route**: `POST /admin/newsletter-reset/<int:post_id>`
- **Purpose**: Reset newsletter status for a post

## Post Management (`posts/`)

### Post Editor (`editor.py`)
- **Route**: `GET /admin/new`
- **Route**: `GET /admin/edit/<int:post_id>`
- **Purpose**: Create/edit posts
- **Features**: Markdown editor, tag selection, image upload, series assignment

### Post Delete (`manage.py`)
- **Route**: `POST /admin/delete/<int:post_id>`
- **Purpose**: Delete a post

### Post Preview (`manage.py`)
- **Route**: `GET /admin/preview/<int:post_id>`
- **Route**: `GET /admin/preview/<int:post_id>?share=1`
- **Purpose**: Preview post before publishing, with optional shareable URL

### Post List (`list.py`)
- **Route**: `GET /admin/`
- **Route**: `GET /admin/<int:page>`
- **Route**: `POST /admin/bulk`
- **Purpose**: List all posts with filtering
- **Filters**: Published, drafts, scheduled
- **Bulk Ops**: Publish, unpublish, delete, unschedule selected posts

### Post Revisions (`revisions.py`)
- **Route**: `GET /admin/posts/<int:post_id>/revisions`
- **Route**: `GET /admin/posts/<int:post_id>/revisions/<int:rev_id>`
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
- **Route**: `POST /admin/users/<int:user_id>/password`
- **Purpose**: Manage admin users

## Session Monitoring (`sessions.py`)

- **Route**: `GET /admin/sessions`
- **Purpose**: View active admin sessions
- **Features**: IP binding, session termination

## Media Management (`media.py`)

- **Route**: `GET /admin/media`
- **Route**: `POST /admin/media/upload`
- **Route**: `POST /admin/media/delete/<filename>`
- **Purpose**: Upload and manage images
- **Features**: Responsive variant generation

## Backup Management (`backup.py`)

- **Route**: `GET /admin/backup`
- **Route**: `POST /admin/backup/create`
- **Route**: `POST /admin/backup/restore/`
- **Route**: `GET /admin/backup/download/`
- **Route**: `POST /admin/backup/delete/`
- **Route**: `GET /admin/backup/verify/`
- **Route**: `GET /admin/backup/verify-all`
- **Purpose**: Database backup/restore
- **Features**: Compression, encryption (AES-256-GCM), integrity verification

## Analytics (`analytics.py`)

- **Route**: `GET /admin/analytics`
- **Purpose**: Dashboard charts and statistics
- **Data**: Page views, popular posts, traffic sources

## Newsletter (`newsletter.py`)

- **Route**: `GET /admin/newsletter/preview`
- **Route**: `POST /admin/newsletter-test`
- **Purpose**: Preview and send newsletters

## Settings (`settings.py`)

- **Route**: `GET /admin/settings`
- **Route**: `POST /admin/settings/theme`
- **Purpose**: View and update theme, syntax theme, custom CSS

## Audit Log (`audit.py`)

- **Route**: `GET /admin/audit`
- **Purpose**: View admin action audit trail

## Static Page Management (`pages.py`)

- **Route**: `GET /admin/pages`
- **Route**: `GET /admin/pages/new`
- **Route**: `POST /admin/pages/new`
- **Route**: `GET /admin/pages/edit/<int:page_id>`
- **Route**: `POST /admin/pages/edit/<int:page_id>`
- **Route**: `POST /admin/pages/delete/<int:page_id>`
- **Purpose**: Create and manage static pages

## Comment Moderation (`comments.py`)

- **Route**: `GET /admin/comments`
- **Route**: `POST /admin/comments/<int:comment_id>/approve`
- **Route**: `POST /admin/comments/<int:comment_id>/delete`
- **Purpose**: Moderate comments

## See Also
- [Public Routes](routes/public-routes.md) - Public blog routes
- [API Routes](routes/api-routes.md) - REST API
- [RSS/Feeds](routes/rss-feeds.md) - Feeds
