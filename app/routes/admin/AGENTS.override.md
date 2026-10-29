# Admin Routes Agent Override

Specialized handling for the admin dashboard and management routes.

## Key Files

### Sub-packages
- `helpers/` - Helper modules: `analytics.py`, `dashboard.py`, `posts.py`, `slug.py`, `tags.py`, `images.py`, `shared.py`
- `posts/` - Post management sub-package: `editor.py`, `manage.py`, `revisions.py`

### Main Files

- `__init__.py` - Blueprint registration (type: `admin: Blueprint`), shared helpers, admin_required decorator
- `auth.py` - login, logout, password reset
- `posts.py` - **DEPRECATED**: Routes moved to `posts/` sub-package
- `subscribers.py` - subscriber management (incl. bulk resend)
- `tags.py` - tag management
- `users.py` - user management
- `sessions.py` - session management
- `media.py` - media library
- `backup.py` - backup/restore
- `analytics.py` - analytics page
- `newsletter.py` - newsletter test
- `settings.py` - theme, appearance, navigation, and homepage settings
- `pages.py` - static pages CRUD
- `projects.py` - project CRUD and authenticated draft preview
- `series.py` - post series/collections

## Routes

- `/admin/` - Dashboard with widgets (traffic chart, top shares, trending, scheduled posts count) and post listing/CRUD with bulk operations
- `/admin/new` - New post editor
- `/admin/edit/<id>` - Edit post
- `/admin/posts/<id>/revisions` - Post revision history
- `/admin/subscribers` - Subscriber management with bulk resend
- `/admin/users` - User management with promote/demote/make-owner
- `/admin/sessions` - Active session viewing/revocation
- `/admin/media` - Media library with upload/delete
- `/admin/backup` - Database backup/restore with encryption support
- `/admin/settings` - Theme presets, custom CSS, logo
- `/admin/pages` - Static pages CRUD
- `/admin/projects` - Project CRUD; `/admin/projects/preview/<id>` - authenticated draft preview
- `/admin/series` - Post series/collections management
- `/admin/newsletter` - Newsletter with preview feature

## Admin Authentication

All admin routes (except `login()` and `logout()`) use `@admin_required`, which combines `@login_required` with `is_admin` check.

## Admin Sessions

- Login creates an `AdminSession` record (tracks `session_id`, `ip_address`, `user_agent`); logout deletes it
- Session IP binding logs warning on address change (detects potential hijacking, does not invalidate)
- **Cascade delete**: Deleting a User automatically deletes their AdminSession records

## Multi-Admin

- `flask create-admin <username>` CLI command
- User management UI at `/admin/users`
- Password complexity: 3 of 4 character classes, min 8 chars
- Promote/Demote via `POST /admin/users/<id>/promote` or `POST /admin/users/<id>/demote`
- Ownership transfer via `POST /admin/users/<id>/make-owner`

## make_owner() Race Condition

The `make_owner()` function demotes ALL admins first, then promotes the target. If commit fails between these operations, there would be zero admins. Fix: promote target first (so at least one admin always exists), then demote others. Use `db.session.flush()` after promoting.

## Slug Generation

- `Post.slug` must be unique—use `_generate_unique_slug()` in `helpers/slug.py`
- `Page.slug` must be unique—use `_generate_unique_slug()` in `helpers/slug.py` (same function)
- Empty string and whitespace-only input both fall back to `"untitled"`
- Slug generation is centralized in `app/utils.py` (`generate_slug()`). All models (Tag, Page, Post, Series) use this shared function.

## IntegrityError Rollback Gotcha

In `edit_post()`, `db.session.rollback()` reverts ALL session changes. After rollback, SQLAlchemy marks all attributes as expired. If you only re-set one field and commit, all other edits are silently lost. Always reapply all field changes after rollback.

## IntegrityError Rollback in pages.py

The `new_page()` function in `pages.py` implements a retry loop with `max_attempts=100`. On `IntegrityError`, it rolls back, regenerates the slug, and retries the commit.

## Optional AI Post Authoring

`POST /admin/ai-assist` is an authenticated editor route, not a public API endpoint. Keep `@author_required` and global CSRF validation; AI rate limiting is unlimited by default with optional per-user configuration (`ai.rate_limit_per_user`). The model is blank by default, so controls stay hidden and the endpoint fails closed until explicitly configured. A local OpenAI-compatible model may be used without an API key. For edits, verify post ownership before inference; use only submitted unsaved text and never load a stored draft as model input. Suggestions must not save posts, create tags, alter revisions, or bypass the normal post Save path. Keep provider errors sanitized and do not log title/body or credentials. See `app/services/ai_assist.py` and `architecture/services/overview.md` for provider and rate-limit decisions.

## CSRF Token Rotation on Privilege Change

When promoting/demoting users or making an owner, the code sets `session["csrf_token"]` (singular) but the sliding window uses `session["csrf_tokens"]` (list). Must reset the list `session["csrf_tokens"]` = `[generate_csrf_token()]` not the singular token.

## File Deletion Timing

Old image files are deleted *after* `db.session.commit()` to prevent dangling file references on rollback. Use `safe_delete_file()` from `app/utils.py`.

## Media Cache Invalidation

When uploading images via post create/edit, the media cache must be invalidated:
```python
from app.routes.admin.media import _invalidate_media_cache
_invalidate_media_cache()
```
The cache is in `media.py` and uses 30-second TTL. Invalidate after successful image/video/other upload or delete. The `/admin/media` manager and delete route remain admin-only; `/admin/media/items` and `/admin/media/upload` use `@author_required` for both editor authors and admins. The library and picker catalog classify objects as image, video, or other; server-side signature checks, not client MIME or extension alone, decide inline types. Image variants are image-only. Other uploads must use the public forced-download endpoint, never a direct active-content URL. See `app/routes/admin/helpers/media.py`, `app/routes/public/media.py` and `architecture/infrastructure/storage.md`.

## nh3 Config

The `nh3.clean()` allowed tags/attributes are defined in `app/markdown_config.py` and shared by `app/__init__.py` (markdown_safe filter) and admin preview endpoint.

## Custom CSS Sanitization

`sanitize_css()` strips dangerous properties (`url()`, `expression()`, `content`, etc.) — must be applied BEFORE saving custom_css in settings.py.

## PostRevision Eager Loading

Always use `.options(joinedload(PostRevision.author))` when querying revisions to avoid N+1 queries in templates that display the author.

## Scheduled Post Notifications

Dashboard widgets show scheduled posts count: `scheduled_posts_count` added to dashboard metrics.

## Newsletter Preview

`/admin/newsletter/preview` route shows exactly what subscribers receive.