# Admin Routes Agent Override

Specialized handling for the admin dashboard and management routes.

## Key Files

- `__init__.py` - Blueprint registration (type: `admin: Blueprint`), shared helpers, admin_required decorator
- `auth.py` - login, logout, password reset
- `posts.py` - dashboard, post CRUD, bulk operations, revisions
- `subscribers.py` - subscriber management (incl. bulk resend)
- `tags.py` - tag management
- `users.py` - user management
- `sessions.py` - session management
- `media.py` - media library
- `backup.py` - backup/restore
- `analytics.py` - analytics page
- `newsletter.py` - newsletter test
- `settings.py` - theme settings (presets, custom CSS, logo)
- `pages.py` - static pages CRUD
- `helpers/slug.py` - Slug generation helper

## Routes

- `/admin/` - Dashboard with widgets (traffic chart, top shares, trending, scheduled posts count)
- `/admin/posts` - Post CRUD with bulk operations
- `/admin/posts/<id>/revisions` - Post revision history
- `/admin/subscribers` - Subscriber management with bulk resend
- `/admin/users` - User management with promote/demote/make-owner
- `/admin/sessions` - Active session viewing/revocation
- `/admin/media` - Media library with upload/delete
- `/admin/backup` - Database backup/restore with encryption support
- `/admin/settings` - Theme presets, custom CSS, logo, syntax highlighting theme
- `/admin/pages` - Static pages CRUD
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

## IntegrityError Rollback Gotcha

In `edit_post()`, `db.session.rollback()` reverts ALL session changes. After rollback, SQLAlchemy marks all attributes as expired. If you only re-set one field and commit, all other edits are silently lost. Always reapply all field changes after rollback.

## IntegrityError Rollback in pages.py

The `new_page()` function in `pages.py` implements a retry loop with `max_attempts=100`. On `IntegrityError`, it rolls back, regenerates the slug, and retries the commit.

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
The cache is in `media.py` and uses 30-second TTL. This is called automatically in `posts.py` after image save.

## nh3 Config

The `nh3.clean()` allowed tags/attributes are defined in `app/markdown_config.py` and shared by `app/__init__.py` (markdown_safe filter) and admin preview endpoint.

## Custom CSS Sanitization

`sanitize_css()` strips dangerous properties (`url()`, `expression()`, `content`, etc.) — must be applied BEFORE saving custom_css in settings.py.

## PostRevision Eager Loading

Always use `.options(joinedload(PostRevision.author))` when querying revisions to avoid N+1 queries in templates that display the author.

## Cache Invalidation

`_invalidate_all_caches()` in `__init__.py` invalidates tag, FTS, analytics, dashboard, and footer caches.

## Scheduled Post Notifications

Dashboard widgets show scheduled posts count: `scheduled_posts_count` added to dashboard metrics.

## Newsletter Preview

`/admin/newsletter/preview` route shows exactly what subscribers receive.