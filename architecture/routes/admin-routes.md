# Admin Routes (`app/routes/admin/`)

The admin module provides the dashboard and management interfaces.

## Module Structure

```
admin/
├── __init__.py          # Blueprint registration
├── auth.py              # Login, logout, 2FA
├── posts/               # Post management
│   ├── __init__.py      # Route registration
│   ├── editor.py        # Post editor
│   ├── list.py          # Post listing
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

### 2FA Setup
- **Route**: `GET /admin/2fa/setup`
- **Purpose**: Setup TOTP 2FA

### 2FA Verify
- **Route**: `GET /admin/2fa/verify`
- **Purpose**: Verify 2FA code

## Post Management (`posts/`)

### Post Editor (`editor.py`)
- **Route**: `GET /admin/new`
- **Route**: `GET /admin/edit/<int:post_id>`
- **Purpose**: Create/edit posts
- **Features**: Markdown editor, tag selection, image upload, series assignment

### Post List (`list.py`)
- **Route**: `GET /admin/`
- **Route**: `GET /admin/<int:page>`
- **Purpose**: List all posts with filtering
- **Filters**: Published, drafts, scheduled

### Post Revisions (`revisions.py`)
- **Route**: `GET /admin/posts/<int:post_id>/revisions`
- **Route**: `GET /admin/posts/<int:post_id>/revisions/<int:rev_id>`
- **Route**: `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore`
- **Purpose**: View post edit history, restore previous revisions
- **Diff**: Side-by-side diff view

## Subscriber Management (`subscribers.py`)

- **Route**: `GET /admin/subscribers`
- **Route**: `POST /admin/subscribers/export`
- **Purpose**: View and export subscribers

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
- **Route**: `DELETE /admin/media/<filename>`
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

- **Route**: `GET /admin/newsletter`
- **Route**: `POST /admin/newsletter/preview`
- **Route**: `POST /admin/newsletter/send`
- **Route**: `POST /admin/newsletter-test`
- **Purpose**: Preview and send newsletters

## Settings (`settings.py`)

- **Route**: `GET /admin/settings`
- **Route**: `POST /admin/settings`
- **Purpose**: Configure theme, syntax theme, custom CSS

## Audit Log (`audit.py`)

- **Route**: `GET /admin/audit`
- **Purpose**: View admin action audit trail

## Comment Moderation (`comments.py`)

- **Route**: `GET /admin/comments`
- **Route**: `POST /admin/comments/<int:comment_id>/approve`
- **Route**: `POST /admin/comments/<int:comment_id>/delete`
- **Purpose**: Moderate comments

## See Also
- [Public Routes](routes/public-routes.md) - Public blog routes
- [API Routes](routes/api-routes.md) - REST API
- [RSS/Feeds](routes/rss-feeds.md) - Feeds
