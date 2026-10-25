# Site Identity Phase 02 — User Profiles

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/models.md](../architecture/core/models.md); this file is the historical record.

**Roadmap:** [site_identity_authoring_roadmap.md](site_identity_authoring_roadmap.md)
**Date:** 2026-10-24
**Status:** Complete
**Severity:** High — `users` has no profile fields, so there is nothing for a profile page to edit.

## Objective

Give every user a profile — a display name, a profile picture, a short bio and a
full bio — and give the admin a page to edit it, reachable from
`/admin/users`.

## Findings

### SIA-06 — The `users` table has no profile fields (high)

`PRAGMA table_info(users)` on the running instance:

```
id, username, email, password_hash, is_admin, reset_token,
reset_token_expires_at, failed_login_count, locked_until,
totp_secret_encrypted, totp_enabled, backup_codes_hashed
```

There is no display name, no avatar, and no bio of any length. The only
human-readable identifier is `username`, which is also the login identifier.

### SIA-07 — `/admin/users` has no profile editor (high)

`app/templates/admin/users.html` lists users and offers only
edit-password / make-admin / delete actions. There is no route, and no
template, for editing a user's profile. Measured: the `/admin/users` body text
contains no "bio" and no "avatar".

The user's instruction was specific: *"admin/users should have a profile
settings page, where they can change a profile picture and add a bio."* So the
editor is reached **from the users list**, not only from a personal account
page.

### SIA-08 — The admin's own profile is not editable anywhere (medium)

`app/routes/admin/users.py` can change a password and the admin flag, but not a
name, avatar or bio. The admin nav has no "Profile" entry.

### SIA-09 — The avatar needs a safe storage path (medium)

An avatar is a user-supplied file. The repository already has the correct
primitive: `app/routes/admin/helpers/images.py:_save_image()` performs
extension allow-listing, a magic-byte check (`png`, `jpeg`, `gif`, `webp`), a
size check against `MAX_UPLOAD_SIZE`, and writes through
`app/storage.py:upload_with_processing()` so local and S3 backends both work.
It must be reused rather than reimplemented, and the previous avatar must be
deleted from storage when it is replaced — otherwise every profile edit leaks
a file.

The stored value must be a **storage-relative filename**, never a URL supplied
by the client. The rendered `src` is built from the storage backend, so an
admin cannot point a profile picture at an arbitrary origin.

## Fix specification

### 1. Model

`app/models.py`, `User`:

```python
display_name = db.Column(db.String(120), default="", nullable=False)
bio_short = db.Column(db.String(300), default="", nullable=False)
bio_full = db.Column(db.Text, default="", nullable=False)
avatar_path = db.Column(db.String(255), nullable=True)
```

Helpers on `User`:

- `profile_name` → `display_name` if set, else `username`. One producer for the
  display name; templates must not re-derive it.
- `profile_bio_short` → `bio_short`.
- `avatar_url` → the storage URL for `avatar_path`, or `None` when unset.
  Built from `app/storage.py:get_storage().url(path)`.

`username` stays the login identifier and the author URL slug. It is unique and
already indexed, so a separate public slug column is unnecessary.

### 2. Migration

New file `migrations/versions/<rev>_add_user_profile_fields.py`:

- `users.display_name` — String(120), `server_default=""`, `nullable=False`.
- `users.bio_short` — String(300), `server_default=""`, `nullable=False`.
- `users.bio_full` — Text, `server_default=""`, `nullable=False`.
- `users.avatar_path` — String(255), nullable=True.

`down_revision` chains from the head produced by Phase 01.

Existing users keep working: `profile_name` falls back to `username`, and an
empty avatar renders the existing avatar placeholder.

### 3. Admin profile editor

New route in `app/routes/admin/users.py`:

- `GET /admin/users/<int:user_id>/profile` — render the editor.
- `POST /admin/users/<int:user_id>/profile` — persist.

Form fields:

| Field | Rule |
|---|---|
| `display_name` | trimmed, max 120 characters |
| `bio_short` | trimmed, max 300 characters, plain text (may contain newlines) |
| `bio_full` | markdown, rendered through `app/markdown_renderer.py` |
| `avatar` | optional file input; accepts the same image types as the media library |

The `bio_full` field is the only markdown field. It renders through
`render_markdown()` — the single producer in `app/markdown_renderer.py`, which
already applies `nh3` sanitisation with the project's allow-lists. No second
markdown path and no client-side `marked` for this field.

Avatar handling:

- Reuse `_save_image()` from `app/routes/admin/helpers/images.py`.
- Store the returned filename in `avatar_path`.
- On replacement, delete the previous file through the storage backend
  (`get_storage().delete(old_path)`), tolerating a missing file.
- A form submission with no file leaves the existing avatar untouched (the
  `_save_image` helper already returns `(None, None)` for an empty upload).
- Provide an explicit "Remove picture" checkbox so an avatar can be cleared
  without uploading a replacement.

Validation lives in a service, not inline in the route. Add
`validate_profile_payload()` to `app/services/site_settings.py` (created in
Phase 01) or a new `app/services/profile.py` — the choice must be made once
and used consistently. Prefer a new `app/services/profile.py` so the profile
rules are not coupled to the site-settings form.

Audit: the profile edit writes an `AdminAuditLog` entry recording the admin's
user id and the target user id. Never log the bio content.

### 4. Navigation

- `app/templates/admin/users.html` — add a **Profile** action per user row
  linking to `admin.user_profile`.
- `app/templates/admin/base.html` — add a **Profile** nav entry linking to the
  admin's own profile editor (`/admin/users/<own id>/profile`). The nav is
  shared by every admin page, so this must render for every admin.
- The admin row for the currently logged-in admin should link to the same
  page.

### 5. Rendering the profile

Where the profile is displayed:

- The avatar: `<img src="{{ user.avatar_url }}" alt="{{ user.profile_name }}">`,
  with the existing avatar-placeholder markup when `avatar_url` is `None`.
- The short bio: plain text, escaped, in the author card.
- The full bio: `{{ user.bio_full | markdown_safe | safe }}` — the same filter
  the post body uses, so the sanitisation contract is identical.

Phase 04 owns the *public* author page; this phase owns the data and the
admin editor. The public rendering of these fields belongs to Phase 04.

## Tests

1. **Model (unit)** — assert `profile_name` returns `display_name` when set and
   `username` when not. Assert `avatar_url` is `None` when `avatar_path` is
   unset.
2. **Migration (unit)** — assert the four columns exist after upgrade and are
   dropped on downgrade.
3. **Profile save (unit)** — POST a valid payload with a CSRF token; assert
   `display_name`, `bio_short` and `bio_full` persisted. Assert `display_name`
   is truncated at 120 characters and `bio_short` at 300.
4. **Markdown sanitisation (unit)** — post a `bio_full` containing
   `<script>alert(1)</script>` and an `onerror` attribute; assert the rendered
   editor page contains no executable markup. The bio must go through the same
   sanitiser as post bodies.
5. **Avatar upload (unit)** — post a multipart body with a real PNG; assert
   `avatar_path` is set, the file exists in storage, and the rendered URL
   points at the storage backend.
6. **Avatar rejection (unit)** — post a file with a `.txt` extension and a
   non-image magic header; assert it is rejected and `avatar_path` is
   unchanged.
7. **Avatar replacement (unit)** — upload twice; assert the first file is
   deleted from storage and `avatar_path` points at the second.
8. **Avatar removal (unit)** — submit with the remove flag; assert
   `avatar_path` is `None` and the stored file is deleted.
9. **Avatar is not a client-supplied URL (unit)** — assert no code path writes
   a value from the request body into `avatar_path`; the field is only ever set
   from `_save_image`'s return value.
10. **Access control (unit)** — assert a non-admin cannot reach
    `/admin/users/<id>/profile`.
11. **Navigation (unit)** — assert the admin nav contains a Profile link and
    the users list contains a Profile action.
12. **Audit (unit)** — assert a profile edit writes an `AdminAuditLog` row.

## Expected files

- `app/models.py` (`User` columns and helpers)
- `app/services/profile.py` (new)
- `app/routes/admin/users.py` (profile routes)
- `app/templates/admin/users.html` (Profile action)
- `app/templates/admin/base.html` (Profile nav entry)
- `app/templates/admin/user_profile.html` (new)
- `migrations/versions/<rev>_add_user_profile_fields.py` (new)
- `tests/test_user_profiles.py` (new)
- `tests/e2e/test_user_profiles.py` (new)

## Acceptance criteria

- [ ] A user row in `/admin/users` opens a profile editor.
- [ ] The editor can set a display name, a short bio and a full bio.
- [ ] The editor can upload, replace and remove a profile picture.
- [ ] Replacing a picture deletes the previous file from storage.
- [ ] The full bio renders as sanitised markdown; no payload executes.
- [ ] The display name and the short bio are plain text and are escaped on render.
- [ ] The avatar is served from the configured storage backend, never from a client-supplied URL.
- [ ] The admin can reach their own profile from the admin nav.
- [ ] Every profile edit is written to the admin audit log.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Requires Phase 01 (the `app/services/site_settings.py` module and the settings
page shell). Phase 04 reads the fields added here and must land after it.

## Completion

**Status:** Complete.

| Item | Resolution |
|---|---|
| Profile fields | `users` gained `display_name`, `bio_short`, `bio_full` and `avatar_path` through migration `add_user_profile_fields`. All are nullable or defaulted, so existing deployments keep working. |
| Model helpers | `User.profile_name` falls back to the username when no display name is set; `User.avatar_url` resolves the stored avatar path against the media root and returns `None` when there is no avatar. |
| Service | `app/services/profile.py` owns validation and persistence (`ProfilePayload`, `validate_profile_payload`, `save_profile`). The routes never interpret raw form values. |
| Admin editor | `GET/POST /admin/users/<user_id>/profile` (`admin.user_profile`) edits any user's profile. `/admin/profile` (`admin.own_profile`) edits the signed-in admin's own profile and redirects there. |
| Reachability | `/admin/users` carries a **Profile** action per user, and the admin nav carries a **Profile** link. |
| Avatar | Uploaded through the existing media path; the stored value is a path, not a URL, so the media root can move without breaking the profile. |
| User deletion | Deleting a user nulls `posts.author_id` for that user's posts rather than orphaning them. SQLite does not enforce the foreign key here, so this is done in code. |

**Verification** — headless Chromium against the live instance at
`http://localhost:5050`, harness at `/tmp/devlog_review_stubs/identity_verify.py`:

```
PASS users_list_has_profile_action
PASS account_page_shows_display_name
PASS account_page_shows_short_bio
PASS own_profile_editor_present
PASS own_profile_editor_has_no_password_field
PASS own_profile_editor_has_no_admin_field
```

Unit coverage: `tests/test_user_profiles.py` (22 tests).
