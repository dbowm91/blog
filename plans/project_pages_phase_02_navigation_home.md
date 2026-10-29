# Project Pages Phase 02 — Unified Navigation and Configurable Homepage

> **Plan status: IMPLEMENTED.** See the completion record below for current verification evidence.

**Date:** 2026-10-28
**Plan ID:** PROJ-02
**Status:** Implemented; verification recorded below
**Prerequisite:** Phase 01 merged.

## Objective

Extend existing configurable Page navigation to support an optional customizable Projects dropdown and individually promoted projects, with deterministic duplicate suppression. Allow the homepage at `/` to be the blog index, one published ordinary Page, or one published Project. Maintain an accessible post index and canonical URLs in every configuration.

## Database and site settings

Add settings, with backward-compatible defaults, in a single reversible Alembic revision:

- `show_projects_in_menu`: false, so upgrading existing sites does not add new nav elements without operator action.
- `projects_menu_label`: `Projects`, validated nonblank bounded plain text, never HTML.
- `homepage_kind`: enum `blog|page|project`, default `blog`.
- `homepage_target_id`: nullable integer; always null when `kind=blog`. For other kinds validate target type/existence/**publication** at write time, not solely at template rendering time.

Site homepage selection must be atomic. Because the target spans two tables, implement application-level validation, deletion/unpublication fallback and comprehensive tests, rather than pretending a cross-table foreign key exists. On deleting, unpublishing or invalidating the selected target, reset to `blog` in the same mutation when possible; at render time fail closed to the blog if the database is inconsistent.

Project menu choices use the Phase 01 fields `Project.show_in_nav` and `Project.nav_label`. Direct navigation links do not depend on the global Projects-dropdown switch.

## Navigation contract

`app/services/navigation.py` is the **single** producer for all rendered public nav models. Keep `resolve_page_menu()` as compatibility entry point if needed, but introduce a unified structured resolution output with page links, direct project links, optional Projects directory link and dropdown entries. Templates should iterate the resolved result, never repeat selection logic.

- A direct project link is displayed only if published and `show_in_nav=true`; label is `nav_label` if nonempty, otherwise title.
- The dropdown contains all published projects **not** promoted directly, in configured stable project order, only when the global switch is on. Never duplicate a promoted project in the dropdown.
- The `Projects` (or custom label) anchor opens `/projects` even when no dropdown exists. Its disclosure control is separate and keyboard-operable, with `aria-expanded` and `aria-controls`, focus handling, Escape dismissal, and proper mobile behavior.
- `/projects` always lists all published projects, including direct navbar projects; the Projects menu switch has no effect on discoverability by direct URL.
- Keep existing `SiteSettings.menu_pages` semantics. Existing ordinary Page links retain their order and visibility rules. Do not silently merge project IDs into page IDs.
- Preserve no-JS link access, visible focus state and mobile scroll/overflow behavior. `shared/nav-dropdown.js` must be initialized from `app/static/js/main.js` on public routes; coordinate with the mobile-menu module and avoid duplicated initialization.

Define and test a deterministic ordering between Posts, existing Pages and direct Projects, the grouped Projects entry, and account/admin actions. Do not accidentally hide page links when a project is promoted.

## Homepage and routing contract

Extract the existing post-index renderer from `public.index` into a reusable function and expose `GET /posts`. Make `GET /` a resolver that dispatches to blog/page/project **without** an HTTP redirect for the intended root homepage. It must share the ordinary Page/Project rendering service and publication checks, avoiding a second Markdown or theme path.

When home is not blog, the logo points to `/` and the Posts link points to `/posts`. Blog pagination, search, search suggestions, feeds, tags, series, post short links and archive remain reachable. If blog is home, decide between an HTTP redirect from `/posts` to `/` or a single canonical metadata URL; pagination queries must be preserved and not loop. The `index.html` pagination macro currently targets `public.index`, so update that contract deliberately.

For a selected Page/Project rendered at `/`, choose a consistent canonical policy (root is canonical for the selected target; original canonical route stays addressable or explicitly redirects with a tested rule). Update `app/context_processors.py` canonical URL producer, OpenGraph tags, sitemap and breadcrumbs. Do not create duplicate `<link rel=canonical>` values. Only published pages/projects can appear in the sitemap and nav.

## Admin and API surface

Extend the existing Site settings form and `POST /admin/settings/site` rather than creating competing settings ownership. Add Projects menu switch/label and a homepage picker populated only with published eligible targets. Use `app/services/site_settings.py` for parsing/validation and `app/services/navigation.py` for projection; invalidate settings/navigation caches after publication, target deletion, or settings change.

If providing site-settings API mutations, give them a specific admin-only scope; never let arbitrary `pages:write` or `projects:write` redirect the site homepage.

## Tests and acceptance

1. Default upgrade leaves `/` showing posts, original menu unchanged, `/posts` reachable.
2. Publish three projects, promote one with a custom title. Global Projects enabled: dropdown contains exactly the other two; directory has all three. Disable Projects menu: no dropdown/directories tab, promoted project stays in navbar and `/projects` remains reachable.
3. Renaming a project slug/title does not corrupt nav placement; direct label override survives. Unpublish/delete projects and pages: no stale menu links; invalid homepage falls back to posts.
4. Homepage supports all three modes, preserves post pagination and canonical URLs, includes correct sitemap/OG/breadcrumbs, and has no redirect loops.
5. Accessible disclosure behavior works with keyboard, touch, mouse, Escape and screen reader names; mobile viewport at 390 and tablet at 768 have no off-screen menu entries. Without JS `/projects` remains linked.
6. No unbounded per-request menu queries; reuse request-scoped SiteSettings read. No regressions in tests/test_page_navigation.py and existing public E2E.

**Likely files:** `app/models.py` (`SiteSettings`), Alembic migration, `app/services/navigation.py`, `app/services/site_settings.py`, `app/routes/public/browse.py`, `app/routes/admin/settings.py`, `app/context_processors.py`, `app/templates/base.html`, `app/templates/admin/settings.html`, `app/templates/index.html`, `app/static/js/main.js` and `shared/nav-dropdown.js`, layout CSS, sitemap code and tests.

## Completion

**Status:** Implemented.

- Added the backward-compatible `SiteSettings` fields and reversible migration; validated project/page homepage targets on settings writes and reset selected targets to the blog when removed or unpublished.
- Added the unified navigation projection for ordered page links, promoted projects, and the optional Projects dropdown; linked the public directory independently of its visibility switch. Added keyboard-operable disclosure behavior and mobile styling.
- Added `/posts` and the root blog/page/project dispatcher, canonical metadata behavior, sitemap handling, breadcrumbs, and admin settings controls. Defaults remain `show_projects_in_menu=false` and `homepage_kind=blog`.
- Verification: focused project, existing page-navigation, and migration-chain suite: **122 passed**; responsive project-page and keyboard-disclosure browser E2E: **1 passed**; the bounded homepage-query benchmark after its budget update: **1 passed**. The existing page-navigation regression suite is included in the 122 passing tests. `ruff check .` and `ruff format --check .` passed; `npm run build` passed; `docs/openapi.yaml` parsed successfully.
- Full suite: **4,922 passed, 21 skipped, 74 failed**. One failure was the old homepage query budget (`<=10`) not allowing the new single bounded project-navigation query; the budget is now `<=11` and the isolated benchmark passes. Other failures included macOS `/private` path expectations, nginx config validation, 2FA encryption, task/database fixture issues, and theme/logging tests. The run is not a clean release gate; these failures were not all independently classified as pre-existing.
- `mypy app/ devlog_cli/` reported **17 errors in 7 unrelated existing files**; it reported no error in the new project route/service code. The project-route typing issue found during implementation was fixed before this run.
