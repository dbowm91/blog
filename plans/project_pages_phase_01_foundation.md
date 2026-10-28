# Project Pages Phase 01 — Project Model and Themed Landing Pages

> **Plan status: PROPOSED — not implemented.** See [project_pages_roadmap.md](project_pages_roadmap.md). Shipped behavior belongs in architecture/ after verification.

**Date:** 2026-10-28
**Plan ID:** PROJ-01
**Status:** Not started
**Prerequisite:** Current main, clean Alembic migration graph.

## Objective and scope

Introduce a project as a distinct published content type with its own canonical landing URL, cards in a project directory, and preset layouts consuming the existing Halloy theme tokens. Do not alter ordinary Page or Post behavior. GitHub metadata, documentation, releases, and navigation are **not** implemented in this phase, although the data model should accommodate their later addition without a redesign.

## Model and schema

Add `Project` to `app/models.py` with, at minimum:

- `id` primary key; `title` (required), globally unique normalized `slug`, `summary` (short plain text for cards/SEO), `body` (Markdown), `published` false by default, `created_at` and `updated_at` using existing UTC helpers, `sort_order` integer, optional `repo_url` as structured GitHub repository identity (do not use as a fetch target yet).
- `landing_style` validated enum-like key: `product`, `documentation`, `minimal`, `terminal`, default `minimal`. Values are layout identifiers, not Halloy theme identifiers.
- Nullable `theme_dark_name` and `theme_light_name` registry names; null means inherit global. Do not persist arbitrary CSS declarations as a theme name.
- `show_in_nav` default false and nullable `nav_label` for Phase 02. These do not affect the first phase navbar; they should be editable with clear explanation or hidden until Phase 02 is available.
- Optional hero image and limited screenshots using existing media URL rules, with upload ownership and trusted media keys; avoid unvalidated external embed/URL fields.
- Indexes supporting `(published, sort_order, title)` and `(published, slug)`; explicit uniqueness and data-length validation on both admin and API writes.

Provide one reversible Alembic revision branched from the **actual current head** at implementation time (baseline was `drop_syntax_theme_column`). Check the real revision chain before writing. No new migration head. Project foreign-key children come in later phases.

`Page` remains a Markdown static page, not a parent class or generic table for project records. Project's external repo reference is optional: manually authored sites must work.

## Service/API/admin ownership

Create a project service, e.g. `app/services/projects.py`, owning validation, slug generation/collision checks, publication filtering, ordering, theme fallback and directory-summary projection. Routes must not duplicate these rules.

Add admin screens `/admin/projects`, `/admin/projects/new`, `/admin/projects/edit/<id>` and a CSRF-protected delete endpoint, all `admin_required`. Reuse `admin/_editor_body.html` for Markdown; honor the existing admin audit and error/rollback patterns. Provide a preview only through an authenticated admin route; ordinary `/projects/<slug>` must return 404 for drafts.

Add `GET /projects` with all published projects, even if hidden from nav; summaries are explicit project data, not costly per-card Markdown rendering. Add `GET /projects/<slug>` with a selectable preset. Keep project listing content stable and readable without JS. Publishing and unpublishing changes all public surfaces immediately or via explicit cache invalidation.

If project REST operations are added in this phase, create `app/routes/api/projects.py` with distinct `projects:read` and `projects:write` scopes, documented in `docs/openapi.yaml`. Public read endpoints must not expose drafts; admin API reads may expose drafts only under authenticated privileged scopes. Do not reuse `pages:*` to administer projects. Route handlers should be thin and delegate to service logic.

## Layout and theme implementation

Add four render modes as components/partials in `app/templates/projects/`; use the same overall site shell and explicit content blocks for title, summary, project links, optional hero, Markdown body and future docs/releases links. No arbitrary HTML templates submitted through the editor. Keep visual variations structural: hero orientation, metadata density, typography/layout, feature grid, terminal-oriented command section.

Resolve theme names only against `app/themes/registry.py`. For a project override, generate scoped dark/light variables for its container; never mutate the process-global `ThemeService._settings_cache` or the global visitor scheme. Do not duplicate Halloy TOML parsing or add colors outside the theme token contract. Reuse `app/markdown_renderer.py` and `markdown_safe`. Reuse the existing image URL producer rather than constructing upload URLs in templates.

Ensure mobile layouts and accessibility at 390, 768 and 1280px; semantic headings, focus indicators, contrast, image alt text, no critical text in decorative colors, and no unsupported CSS tokens. Route any new browser initialization through `app/static/js/main.js`.

## Tests and deliverables

1. Migration upgrades from current production schema and fresh empty schema; downgrade restores old schema; unique slug and publication indexes are present on SQLite and compatible with PostgreSQL.
2. CRUD validation, duplicate concurrent slug handling, rollback/retry semantics, lengths/invalid theme/style keys, draft preview permissions, and auth/CSRF.
3. Public `/projects` lists all and only published records, in stable order, with concise summaries; `/projects/<slug>` returns published landing and 404 for drafts/missing slugs.
4. All four preset layouts render with dark/light default, inherited/overridden theme choices, valid CSS tokens and no unexpected mutation of global theme state on subsequent post/page requests.
5. Project without GitHub URL is supported. Repo URL validation disallows credentials, fragments and arbitrary executable URL schemes.
6. No regression to existing pages/posts/theme preview or admin. E2E validates responsive rendering, keyboard focus, and usable no-JS output.

**Likely files:** `app/models.py`; Alembic revision; new `app/services/projects.py`; new `app/routes/public/projects.py` and `app/routes/admin/projects.py`; optional `app/routes/api/projects.py`; blueprint registrations; `app/templates/projects/`; `app/templates/admin/projects*.html`; token-based CSS; API spec and tests.

## Boundaries, handoff and acceptance

Phase 01 must not attempt GitHub synchronization, documentation imports, release downloads, home reassignment or global navigation changes. The acceptance bar is a fully useful project landing that can be authored and published locally and uses the existing theme registry. Before handoff, update architecture/core/models.md, relevant route and frontend architecture docs and module overrides, then record observed test evidence here.

## Completion

**Status:** Not started. No code changes or tests have been run for this phase.
