# Site Identity Phase 04 — Authorship and Author Pages

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/models.md](../architecture/core/models.md); this file is the historical record.

**Roadmap:** [site_identity_authoring_roadmap.md](site_identity_authoring_roadmap.md)
**Date:** 2026-10-24
**Status:** Complete
**Severity:** High — posts have no author at all, so "clicking on an author" cannot work.

## Objective

Attach posts to users, render the author where it is currently faked, and give
every author a public page carrying their full bio.

## Findings

### SIA-15 — `posts` has no author column (critical)

`PRAGMA table_info(posts)` on the running instance:

```
id, title, slug, body, summary, image, image_alt_text, created_at,
updated_at, published, published_at, scheduled_publish_at,
newsletter_sent_at, newsletter_attempts
```

There is no `author_id`. The `Post` model has no author relationship. A post
is authored by nobody, and the site renders a *config-level* author instead
(see SIA-16).

### SIA-16 — The rendered author is a config value, and it is usually empty (critical)

`app/context_processors.py` injects a single site-wide author:

```python
"author_name": AUTHOR_NAME,
"author_role": AUTHOR_ROLE,
"author_avatar": AUTHOR_AVATAR,
```

`AUTHOR_NAME` comes from `app/config_legacy.py` and defaults to an empty
string. On the running instance the author card renders with a **blank name** —
measured in Chromium:

```
author card: {'text': '', 'links': 0, 'isLink': 'SPAN'}
```

`app/templates/_post_content.html:75` renders `<span class="author-name">{{ author_name }}</span>`
and `app/templates/index.html:40` renders `<span class="post-author">{{ author_name }}</span>`.
Neither is a link (both measured `links: 0`).

So the current state is: one author, configured globally, usually blank, and
never clickable.

### SIA-17 — There is no author page (critical)

No route renders an author. `app/routes/public/` has browse, posts, subscribe,
meta and comments. There is no `/author/...`.

### SIA-18 — The post JSON-LD names an empty author (medium)

`app/templates/post.html:27`:

```json
"author": {
    "@type": "Person",
    "name": {{ author_name | tojson }}
}
```

With `AUTHOR_NAME` empty this emits `"name": ""` — an invalid `Person` for
every post.

### SIA-19 — The API has no author concept (medium)

`app/routes/api/posts.py:_post_to_dict` returns title/slug/body/author-less
fields. A client cannot tell who wrote a post.

## Fix specification

### 1. Model and migration

`app/models.py`, `Post`:

```python
author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

author = db.relationship("User", foreign_keys=[author_id], lazy="joined", backref="posts")
```

`ondelete="SET NULL"` so deleting a user does not delete their posts.

Migration `migrations/versions/<rev>_add_post_author.py`:

- `posts.author_id` — Integer, nullable=True, FK to `users.id`, `ondelete="SET NULL"`.
- Index `ix_posts_author_id`.

**Backfill**: assign the oldest admin user to every existing post that has no
author, so the site does not render authorless posts after the upgrade. The
backfill must be idempotent and must run in the migration, not in application
startup.

`User.posts` — the backref — is the relationship used by the author page.

### 2. Author selection

Admin post editor (`app/templates/admin/editor.html` and the editor route in
`app/routes/admin/posts/editor.py`):

- An **Author** select listing users who can author posts. The list comes from
  the `User` table, ordered by display name.
- An admin may assign any author. A non-admin signed-in user (Phase 03) may
  only assign themselves; the select is rendered with only their own entry
  and the server rejects any other value.
- When a post is created without an explicit author, it defaults to the
  signed-in user if they may author posts, otherwise to the oldest admin.
- The API (`app/routes/api/posts.py`) accepts an optional `author_id` on create
  and update, validated against the same rule.

### 3. Rendering the author

A single helper resolves the author of a post so the post page, the listing and
the author page cannot disagree:

```python
# app/services/authors.py
def resolve_author(post) -> AuthorView | None
```

`AuthorView` carries `name`, `role`, `avatar_url`, `bio_short`, `bio_full`,
`username`, `url`. Resolution order:

1. `post.author` — the assigned user. Name = `profile_name`; avatar =
   `avatar_url`; role = a role string if the model carries one, else empty.
2. Fallback: the config-level `AUTHOR_NAME` / `AUTHOR_ROLE` /
   `AUTHOR_AVATAR`, for posts whose author was cleared.
3. Final fallback: the site title, so no post renders a blank author name.

`app/templates/_post_content.html`:

- The author card renders the resolved name, role and avatar.
- The name becomes a link to the author page **when the post has a resolvable
  author URL** — that is, when `post.author` exists. When the author is the
  config fallback there is no profile to link to, so the name stays plain text
  rather than linking to a 404.
- The short bio is rendered under the name in the card, as plain text.

`app/templates/index.html`:

- `.post-author` becomes a link to the author page under the same condition.

### 4. The author page

New route `GET /author/<username>`:

- Registered on the public blueprint. 404 for an unknown username.
- A user with no published posts still gets a page (the author exists), but
  the post list is empty.
- The page shows: avatar, display name, role, the **full bio** (rendered as
  sanitised markdown through `app/markdown_renderer.py`), the short bio, and
  the author's published posts (newest first) with their summaries.
- A link back to the author from the post page and from the listing is the
  only entry point needed; no separate "authors index" is required, but
  `/authors` listing all authors with published posts is cheap and useful —
  include it only if it does not add a second producer of author data.

New template `app/templates/author.html`, extending `base.html`.

The author page must be added to `app/routes/public/meta.py` (sitemap) —
author pages are content, and the sitemap currently lists posts and pages only.

### 5. Structured data

`app/templates/post.html` JSON-LD:

```json
"author": {
    "@type": "Person",
    "name": "<resolved name>",
    "url": "<base_url>/author/<username>"
}
```

`url` is included only when the post has a real author. The publisher stays
the organisation.

### 6. API

`app/routes/api/posts.py:_post_to_dict` gains an `author` object:

```json
"author": {"username": "...", "name": "...", "url": "/author/<username>"}
```

`url` is omitted when there is no author. The API scope rules in
`app/routes/api/auth.py` are unchanged — an API token with `posts:write` may
set `author_id`; a token without it may not.

### 7. Export / import

`app/services/serialization.py:serialize_post` enumerates fields explicitly and
does **not** include an author. Users are not exported by
`app/services/operations/transfer.py` at all, so an exported post cannot carry
an author reference that the importer could resolve.

Decision: `author_id` is **not** added to the export payload. On import, posts
are assigned the importing admin. This is recorded here so that a later change
does not silently half-implement it. If a future phase adds user export, the
author reference must be added in the same change.

## Tests

1. **Migration and backfill (unit)** — assert the `author_id` column exists,
   that existing posts are assigned the oldest admin, and that the downgrade
   drops the column.
2. **Author resolution (unit)** — a post with `author_id` resolves that user; a
   post without one falls back to the config author; a post with neither falls
   back to the site title. Assert the name is never empty.
3. **Author page (unit)** — `GET /author/<username>` returns 200 and contains
   the full bio and the author's published posts. Assert an unknown username
   returns 404, and that a draft post by that author is not listed.
4. **Author link (unit)** — assert the post page contains an `<a>` to
   `/author/<username>` when the post has an author, and that it does **not**
   when the author is the config fallback.
5. **Listing link (unit)** — assert `.post-author` is an anchor to the author
   page when the post has an author.
6. **Full bio rendering (unit)** — a bio containing `<script>` renders escaped;
   a bio with `**bold**` renders as `<strong>`.
7. **JSON-LD (unit)** — assert the emitted `author.name` is non-empty and that
   `author.url` is present only for a real author.
8. **Editor (unit)** — assert the editor renders the author select; assert a
   non-admin cannot assign another user; assert a post created without an
   author defaults to the signed-in author.
9. **API (unit)** — assert `author` appears in the post payload; assert a
   token without `posts:write` cannot change `author_id`.
10. **Author page (browser, `tests/e2e/`)** — click the author name on a post
    page, assert the browser lands on the author page, assert the full bio is
    visible and the post list matches.
11. **Listing (browser)** — assert the listing author name links to the same
    page and that the two pages agree on the display name.
12. **Sitemap (unit)** — assert author pages are listed.

## Expected files

- `app/models.py` (`Post.author_id`, `Post.author`)
- `app/services/authors.py` (new — the single author resolver)
- `app/routes/public/authors.py` (new) or an addition to `app/routes/public/browse.py`
- `app/routes/public/__init__.py` (registration)
- `app/routes/public/meta.py` (sitemap)
- `app/routes/admin/posts/editor.py` (author select handling)
- `app/routes/api/posts.py` (author in payload and in create/update)
- `app/templates/author.html` (new)
- `app/templates/_post_content.html` (author card)
- `app/templates/index.html` (listing author link)
- `app/templates/post.html` (JSON-LD)
- `app/templates/admin/editor.html` (author select)
- `migrations/versions/<rev>_add_post_author.py` (new)
- `tests/test_authors.py` (new)
- `tests/e2e/test_authors.py` (new)

## Acceptance criteria

- [ ] Every post has a resolvable author, and no post renders a blank author name.
- [ ] An admin can assign an author when creating or editing a post.
- [ ] The author name on a post page is a link to that author's page.
- [ ] The author name in a listing is a link to the same page.
- [ ] The author page shows the avatar, the short bio and the **full bio**.
- [ ] The author page lists that author's published posts and no drafts.
- [ ] An unknown author URL returns 404.
- [ ] The post JSON-LD carries a non-empty author name and a URL when there is one.
- [ ] The API exposes the author and cannot be used to assign one without the right scope.
- [ ] The export/import round trip still works, with the documented author behaviour.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Requires Phase 02 (the profile fields the author page renders) and Phase 03
(the sign-in that lets a non-admin author edit their own profile). Phase 06
touches `app/templates/post.html` as well and lands after this phase.

## Completion

**Status:** Complete.

| Item | Resolution |
|---|---|
| Column | `posts` gained `author_id` through migration `add_post_author`, with an index. The foreign key is created only on non-SQLite dialects — SQLite does not enforce foreign keys in this deployment, so `app/routes/admin/users.py` nulls `posts.author_id` in code when a user is deleted. |
| Backfill | Every existing post is backfilled with the oldest admin account, so no post is left without an author after the upgrade. |
| One producer | `app/services/authors.py` owns the author: `AuthorView`, `resolve_author`, `resolve_author_id`, `list_authors` and `default_author_id`. Templates and routes never re-derive it. |
| Config-level author | `AuthorView.username is None` means the configured site author has no account. The name is then rendered as plain text — there is no profile page to link to. |
| Author page | `GET /author/<username>` (`public.author`) renders `app/templates/author.html` with the author's display name, short bio and full bio. |
| Links | The author is a link on the post page (`_post_content.html`) and on the listing (`index.html`), and appears as the JSON-LD `author` on the post page. The sitemap carries the author pages. |
| Editor | The post editor carries an **Author** select populated from `list_authors()`. |
| API | The posts API resolves the author field through the same service. |
| Export/import | `Post.author_id` is **intentionally not** in the export payload. Users are not exported, so an imported post is assigned to the importing admin. This matches the roadmap's cross-cutting constraint 5. |
| Author role | `author_required` in `app/routes/admin/__init__.py` lets any signed-in user reach the post editor and nothing else. An author may edit only their own posts (403 otherwise), and **their posts are forced to drafts** — publishing and scheduling stay an admin decision. That default was chosen deliberately, because auto-publishing is a product decision the operator did not specify. |

**Verification** — headless Chromium against the live instance at
`http://localhost:5050`, harness at `/tmp/devlog_review_stubs/identity_verify.py`:

```
PASS author_reaches_editor
PASS author_page_shows_full_bio
PASS author_page_shows_short_bio
PASS post_links_to_author
```

Unit coverage: `tests/test_authors.py` (21 tests) and `tests/test_author_role.py`
(12 tests), covering the resolver, the author page, the author links, the
editor select and the author role's ownership and draft rules.
