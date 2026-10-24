# Site Identity Phase 05 — Making Static Pages Reachable

**Roadmap:** [site_identity_authoring_roadmap.md](site_identity_authoring_roadmap.md)
**Date:** 2026-10-24
**Status:** Complete
**Severity:** High — published pages work but nothing links to them, so the feature is invisible.

## Objective

Give `/admin/pages` an output. A published page must be reachable from the
site's navigation, and there must be one place where the admin decides which
pages appear where.

## Findings

### SIA-20 — Published pages are unreachable from the site (high)

The public page route exists and works:

```python
# app/routes/public/browse.py:228
select(Page).filter_by(slug=slug, published=True)
```

Measured: `GET /page/about` → **200**. The running instance holds two published
pages, `About` and `Contact`.

But measured across the whole public site:

```
page links found = []                     # nav
footer hrefs = ['/post/code-lines-demo', '/post/sample-post-12', '/post/sample-post-11',
                '/tag/api', '/tag/database', '/tag/flask', '/tag/python', '/tag/testing', '/tag/web-dev']
```

Not one `/page/...` link exists in the nav or the footer. `app/templates/base.html`
builds the nav statically (Home, Posts, Search) and the footer from posts and
tags. A visitor cannot reach `/page/about` unless they know the URL.

The pages are in `sitemap.xml` (`app/routes/public/meta.py:79`), which is the
only surface that mentions them.

### SIA-21 — There is no index of pages (medium)

`/page/<slug>` renders one page. There is no `/pages` listing, so a visitor
cannot browse the page set either.

### SIA-22 — The admin cannot choose which pages are shown (medium)

`app/routes/admin/pages.py` exposes the full create / edit / publish / delete
lifecycle — the editor has a **Published** checkbox (`app/templates/admin/page_editor.html:57`)
and the page list shows the resulting URL (`/page/{{ pg.slug }}`). So the
admin *can* publish a page. What the admin cannot do is put it in a menu.

Every navigation surface therefore has to be hardcoded in a template, which
means publishing a page does not make it visible.

## Fix specification

### 1. Model

`app/models.py`, `Page`:

```python
show_in_menu = db.Column(db.Boolean, default=False, nullable=False)
```

`SiteSettings` (extending the Phase 01 Site section):

```python
show_pages_in_menu = db.Column(db.Boolean, default=True, nullable=False)
menu_pages = db.Column(db.Text, default="", nullable=False)   # JSON array of page ids, in order
```

`menu_pages` is a JSON array of page **ids** (not slugs) so a renamed page
keeps its menu position. It is parsed and validated by
`app/services/site_settings.py` (Phase 01) — the raw form value is never
written straight to the column.

Migration `migrations/versions/<rev>_add_page_menu_fields.py`:

- `pages.show_in_menu` — Boolean, `server_default=sa.false()`, `nullable=False`.
- `site_settings.show_pages_in_menu` — Boolean, `server_default=sa.true()`, `nullable=False`.
- `site_settings.menu_pages` — Text, `server_default=""`, `nullable=False`.

The `menu_pages` default is an empty list, which means "no explicit menu" —
in that case the menu falls back to every published page that has
`show_in_menu = True`, ordered by title. That fallback keeps the feature useful
without any configuration.

### 2. The nav menu

`app/templates/base.html` gains a **Pages** entry:

- Rendered when `show_pages_in_menu` is true and the resolved menu is
  non-empty.
- The resolved menu is computed **once** by a service — `app/services/navigation.py`:

```python
def resolve_page_menu() -> list[Page]
```

It reads `SiteSettings.menu_pages`, intersects it with the pages that are
still published, drops the ids that no longer exist, and falls back to the
`show_in_menu` pages when the explicit list is empty. It must be cached
alongside the footer data (the existing `_get_footer_data()` in
`app/context_processors.py` is memoized for 45 seconds) and invalidated when a
page is published, unpublished, deleted, or when the setting changes.

Invalidation points:

- `app/routes/admin/pages.py` — after create, edit, publish/unpublish, delete.
- `app/routes/admin/settings.py` — after the Site form is saved.

The nav must not overflow on a small screen. The navbar has a mobile menu
(`app/static/js/public/mobile-menu.jsx`); the Pages entry must appear there
too, and the nav must wrap or collapse rather than pushing the search control
off-screen.

### 3. The footer

`app/templates/base.html` gains a **Pages** column in the footer grid, listing
the same resolved menu. This is a *separate column* from the "Latest from the
blog" and "Browse by tag" columns; it does not replace either.

The footer grid is `.footer-grid` in `app/static/css/public.css`. Three
columns must lay out cleanly at 1160px, at the tablet breakpoint and on
mobile — the grid must collapse to one column on narrow screens.

### 4. A pages index

New route `GET /pages` on the public blueprint, rendering
`app/templates/pages.html`: the published pages as a list of cards with their
title and a summary (the first paragraph of the body, rendered as markdown and
truncated — the same truncation the post listing uses).

The index lists **all** published pages, or only the `show_in_menu` ones?
Decision: the index lists all published pages. The menu is a *navigation*
choice; the index is a *complete* listing. That keeps the two surfaces
independent and gives an admin a way to check that a page is published.

### 5. The admin page list

`app/templates/admin/pages.html` gains:

- A **Show in menu** checkbox per page, so the admin can opt a page into the
  navigation without reordering a global list.
- A link to the page's public URL (the list already shows the slug as text).
- A warning when a page is published but `show_in_menu` is off and the page is
  not in `menu_pages`, so the admin can see why the page is not visible.

`app/routes/admin/pages.py` must persist `show_in_menu` on create and edit.

### 6. The settings page

The **Site** section created in Phase 01 gains:

- A **Show pages in the menu** toggle.
- A multi-select of pages with up/down ordering, persisted as `menu_pages`.

The ordering control must not require JavaScript to function — the existing
admin module system is available, but a plain form with an ordered
`menu_pages` payload (a hidden input holding the ordered id list) is the
simplest robust implementation and matches the existing series-reorder control
in `app/templates/admin/series_posts.html`.

## Tests

1. **Migration (unit)** — assert the new columns exist and the downgrade drops
   them. Assert the `menu_pages` default parses as an empty list.
2. **Menu resolution (unit)** — assert `resolve_page_menu()` returns the
   explicit order when `menu_pages` is set, the `show_in_menu` pages when it
   is empty, and drops unpublished or deleted ids.
3. **Nav links (unit)** — with two published pages, assert the rendered home
   page contains `/page/about` and `/page/contact` links.
4. **Unpublished page (unit)** — assert a draft page produces no link anywhere.
5. **Menu disabled (unit)** — assert no page links appear when
   `show_pages_in_menu` is false.
6. **Footer column (unit)** — assert the footer contains a Pages heading and
   the page links.
7. **Pages index (unit)** — `GET /pages` returns 200 and lists every published
   page; a draft page is absent.
8. **Admin list (unit)** — assert the pages admin list shows a "Show in menu"
   control and that toggling it persists.
9. **Invalidation (unit)** — publish a page and assert the nav reflects it
   without a restart (the cache is invalidated).
10. **Nav (browser, `tests/e2e/`)** — click a page in the nav, assert the page
    loads, assert the breadcrumb and title are right.
11. **Mobile (browser)** — at 390px, assert the mobile menu contains the Pages
    entry and that the page opens; assert no horizontal overflow.
12. **Footer grid (browser)** — assert the footer columns do not overlap or
    overflow at 1280px, 768px and 390px.

## Expected files

- `app/models.py` (`Page.show_in_menu`, `SiteSettings.show_pages_in_menu`, `SiteSettings.menu_pages`)
- `app/services/navigation.py` (new — the single menu resolver)
- `app/services/site_settings.py` (menu parsing and validation)
- `app/routes/public/browse.py` or a new `app/routes/public/pages.py` (`/pages`)
- `app/routes/public/__init__.py` (registration)
- `app/context_processors.py` (expose the resolved menu, cache invalidation)
- `app/routes/admin/pages.py` (persist `show_in_menu`)
- `app/routes/admin/settings.py` (persist the menu fields)
- `app/templates/base.html` (nav entry, footer column)
- `app/templates/pages.html` (new)
- `app/templates/admin/pages.html` (show-in-menu control)
- `app/templates/admin/settings.html` (menu configuration)
- `app/static/js/public/mobile-menu.jsx` (Pages entry)
- `app/static/css/public.css` (footer grid columns)
- `migrations/versions/<rev>_add_page_menu_fields.py` (new)
- `tests/test_page_navigation.py` (new)
- `tests/e2e/test_page_navigation.py` (new)

## Acceptance criteria

- [ ] A published page is reachable from the site navigation without knowing its URL.
- [ ] A published page appears in the footer.
- [ ] `/pages` lists every published page.
- [ ] A draft page appears nowhere.
- [ ] The admin can choose which pages are in the menu and in what order.
- [ ] Publishing, unpublishing or deleting a page updates the navigation without a restart.
- [ ] The nav and footer do not overflow at 1280px, 768px or 390px.
- [ ] The mobile menu contains the Pages entry.
- [ ] The page menu is computed by one service, not re-derived in templates.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Requires Phase 01 (the Site settings section and
`app/services/site_settings.py`). Phase 03 also edits `app/templates/base.html`
for the nav login entry, so this phase lands after Phase 03 to avoid a conflict
on the same template.

## Completion

**Status:** Complete.

| Item | Resolution |
|---|---|
| Column | `pages` gained `show_in_menu` through migration `add_page_menu_fields`. It defaults to **True**, so a published page appears without the operator configuring anything. |
| Two layers, one parser | `menu_pages` holds an explicit ordered list of page ids and wins when stored; when it is empty the menu falls back to every published page flagged `show_in_menu`, ordered by title. The parser is owned by `app/services/site_settings.py`; `app/services/navigation.py` re-exports `parse_menu_page_ids` as a thin alias so there is exactly one parser. |
| One producer | `app/services/navigation.py::resolve_page_menu` is the only producer of the menu. `app/context_processors.py` wraps it and exposes it to templates as `page_menu`. |
| Nav | The public nav carries a **Pages** link, and each menu page is listed. |
| Footer | The footer carries a **Pages** column listing the same pages. |
| Index | `GET /pages` (`public.pages_index`) renders `app/templates/pages.html` with every published page, so the nav entry has somewhere to point even when the menu is empty. |
| Admin control | The admin pages list carries a **Show in menu** control, backed by `POST /admin/pages/<id>/menu` (`admin.set_page_menu`). |
| Admin settings | The pages-in-menu switch and the ordered page list live in the **Site** section of `/admin/settings` and are saved by the same `POST /admin/settings/site` endpoint — there is no second settings form. |

**Verification** — headless Chromium against the live instance at
`http://localhost:5050`, harness at `/tmp/devlog_review_stubs/identity_verify.py`:

```
PASS nav_has_pages
PASS footer_has_page_links
PASS footer_has_pages_heading
PASS pages_index_lists_about
PASS pages_index_lists_contact
```

Unit coverage: `tests/test_page_navigation.py` (12 test functions), covering
the resolver's two layers, the explicit ordering, the published-only filter,
the admin menu toggle and the `/pages` index.
