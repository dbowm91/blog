# Project Pages Phase 03 — Locally Authored Documentation Viewer

> **Plan status: PROPOSED — not implemented.** See [project_pages_roadmap.md](project_pages_roadmap.md).

**Date:** 2026-10-28
**Plan ID:** PROJ-03
**Status:** Not started
**Prerequisite:** Phase 01 merged; merge after Phase 02.

## Objective

Each project optionally hosts structured Markdown documentation without a repository connection. The browser viewer offers a documentation home, hierarchical contents/sidebar, breadcrumbs, heading deep links, prev/next traversal, code highlighting and copy behavior. A project may be a landing page only; enabling documentation must be an explicit action.

## Data model and storage rules

Introduce `ProjectDocument` in `app/models.py` with `id`, `project_id` FK (delete cascade), normalized POSIX `path`, title, Markdown `body`, nav title/order, `published`, creation/update times and a stable `version_key` (initially `current`). Unique composite `(project_id, version_key, path)` and query indexes on project/version/publication/order. Use a reversible migration from the then-current Alembic head.

Add `Project.docs_enabled` default false and optional `docs_home_path` or a well-defined priority (`index.md` then `README.md` then first published document). Do not invent a new external-storage requirement: locally authored text lives in the database for now, using current backup semantics.

Normalize document paths in a **single resolver**: slash separators, no absolute path, no dot/dot-dot segments, no backslash, no NUL/control chars, no URL encoding ambiguity or double-decode, bounded depth/length, and required Markdown extension (`.md` or `.markdown`). Reject case/Unicode normalization collisions under the chosen canonical scheme. Do not use path joins to read arbitrary local server files.

## Routing and rendering

Implement `GET /projects/<slug>/docs` and `GET /projects/<slug>/docs/<path:doc_path>` with project/document publication gates. Disabled docs, unpublished project/document, invalid paths, and missing home document return 404 or a consistent empty-state as specified in tests; do not leak unpublished headings/sidebar entries.

Use `app/markdown_renderer.py` as the one Markdown-to-HTML producer and existing `heading-slug.js`/anchor-links/Prism behavior. Build one documentation link resolver for relative intra-document Markdown links, `#fragment` anchors, and linked images. Link rewriting must operate on parsed/sanitized links, not an unsafe regex over arbitrary HTML. Reject unsafe schemes and external script/embed content; preserve absolute external HTTPS links with safe attributes.

The viewer should have semantic navigation, a collapsible mobile sidebar, TOC derived from sanitized heading IDs, accessible skip links, and readable prose width. The shared site theme remains authoritative; the project's scoped layout styling should not change code rendering or navbar style globally.

## Authoring and API

Add an admin document list/editor/reorder surface nested under the project, using `admin/_editor_body.html` for body input. Admin authors can create draft documents and preview with authenticated routes; published docs are readable without authentication. Reordering changes only the configured nav order, not stable path identity.

If REST endpoints are added, use a `project_docs:read` / `project_docs:write` scope family or an explicitly documented `projects:docs:*` convention accepted by `scope_allows()`. Do not reuse `pages:*` scopes. Update the OpenAPI document for every added route.

## Tests and acceptance

1. A project with docs disabled has no visible docs link; docs enabled with published content exposes a home and nested document pages.
2. Nested `guide/install.md` and `reference/api.md` paths render and nav order is deterministic; an intra-doc link resolves correctly without leaving the project namespace.
3. `../`, absolute, encoded slash/backslash, double-encoded traversal, mixed separator, malformed Unicode and invalid scheme inputs cannot access another project, the filesystem or drafts.
4. XSS payloads in Markdown, raw HTML, image/link attributes, JavaScript URLs and fenced code remain sanitized. Code highlighting, copy and anchors work in actual rendered Chromium.
5. Project/document unpublish/delete changes the docs tree and sitemap immediately; version-qualified uniqueness prevents collisions.
6. 390/768/1280px layouts, keyboard controls and no-JS fallback verified; docs rendering does not add live repository requests.
7. Migration upgrade/downgrade, backup visibility of locally authored docs, API scope and admin CSRF tests pass.

**Likely files:** new `app/services/project_docs.py` (normalization, routing, TOC/navigation, link resolution), `app/models.py` and migration, `app/routes/public/project_docs.py`, `app/routes/admin/project_docs.py`, `app/templates/projects/docs*.html`, `app/static/css/public.css` and tests.

## Phase boundary

Do **not** implement GitHub fetching, external docs asset downloading, remote version synchronization, or release binaries here. Phase 04 will add an independently swappable repository-backed document source while keeping the viewer and sanitization pipeline unchanged.

## Completion

**Status:** Partially implemented and focused-tested; browser/responsive acceptance remains open.

**Implemented in this worktree:** DB-backed local documents and image assets; docs disabled by default; path normalization; published-only public routes; shared Markdown renderer and parsed project-relative link/image rewriting; admin create/edit/delete, publish state, nav order, draft preview, image upload/removal, and source settings; viewer breadcrumbs, prev/next, mobile collapsible navigation, TOC hook, and heading-anchor integration. The migration chain round-trip is covered below.

**Validation:** focused project/docs/release/GitHub tests; migration upgrade/downgrade and fresh-schema tests; Ruff and frontend build passed. See the current worktree tests. Browser E2E at 390/768/1280px, keyboard/no-JS behavior, and the complete malicious-path/sanitizer matrix remain unverified. No REST docs API or OpenAPI entries were added.
