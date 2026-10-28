# Project Pages, Documentation, and Distribution Roadmap

> **Plan status: PARTIALLY IMPLEMENTED.** Phases 01–02 are implemented; Phases 03–05 have substantial but incomplete implementations in this worktree; Phase 06 remains gated by operator choice and protocol evidence. See per-phase completion records and `architecture/core/project-pages.md`.

**Date:** 2026-10-28
**Repository baseline:** main at 07fafb198a31948c51ec7dee75d0fa84c45bfe36
**Status:** Proposed — phases 01–06 open
**Scope:** First-class project landing pages, navigation and home selection, documentation, optional GitHub release discovery and binary distribution.
**Plan IDs:** PROJ-01 to PROJ-06.

## Context and observed baseline

The application already has simple published Markdown `Page` records (`app/models.py`), a Markdown editor (`app/templates/admin/page_editor.html`), a `/page/<slug>` route (`app/routes/public/browse.py`), a `/pages` listing (`app/routes/public/pages.py`), a single page-menu resolver (`app/services/navigation.py`), configurable page navigation (`SiteSettings.menu_pages`), shared sanitized Markdown (`app/markdown_renderer.py`), the Halloy theme registry (`app/themes/`), and local/S3 media storage (`app/storage.py`). The public navbar lives in `app/templates/base.html`. The `/` route and post pagination currently refer to `public.index`. The public module list in `app/static/js/main.js` does not initialize `shared/nav-dropdown.js` although that module and dropdown CSS exist.

None of the above constitutes first-class project, documentation, or release support. The media storage interface uses whole-file buffers and the media uploader has an image-oriented upload limit: it is not ready for large binary mirroring. Existing project-related functionality must not be represented as shipped until verified.

The present migration chain includes `drop_syntax_theme_column` after `add_appearance_settings_to_sitesettings`; implementation must use the actual Alembic head at execution time, not copy stale head names from historical plans.

## Product contract

1. Project is a standalone first-class resource, **not** a subtype of Page. Every published project is browsable at `/projects/<slug>`; `/projects` lists all published projects with concise descriptions, irrespective of navbar placement. Projects without a repository URL remain valid.
2. Landing layouts are predefined, theme-token-based styles. A project inherits the site theme unless an administrator opts into named dark/light themes from the existing Halloy registry. Theme colors remain owned by the existing theme runtime; layout style is not a second color engine.
3. Global Projects navigation is optional (default off for existing installations), can be renamed, and offers a normal link to `/projects` plus an accessible dropdown of eligible projects. Each project may instead be promoted directly to the top-level navbar with a custom label. A directly promoted project is **excluded from the dropdown**, but not from `/projects`.
4. A site may select exactly one home target: default blog index, a published Page, or a published Project. `/posts` remains a stable post-list entry when the root renders another content type; no post URLs, feeds, or archives change. An unavailable target falls back to the blog.
5. Documentation is optional per project, with local Markdown authoring first and repository-backed snapshots later. No reader request performs a live GitHub fetch. Link resolution, content validation, and sanitized rendering have single owners.
6. Release metadata is optional. GitHub is the **canonical source** of releases and binaries; the initial release view only links to GitHub. Local/object storage mirroring and installer manifests are opt-in follow-up capabilities, not prerequisites for a useful project page.
7. All new admin mutations are admin-only and CSRF-protected; API write surfaces, if implemented in a phase, use specific scopes and documented schema. Draft content never leaks through listing, navigation, sitemap, search, or public APIs.

## Proposed public route contract

| Route | Purpose |
|---|---|
| `GET /` | Home dispatcher: blog, Page, or Project |
| `GET /posts` | Post listing, including pagination when home is not the blog |
| `GET /page/<slug>` | Existing ordinary Page, unchanged |
| `GET /projects` | Every published project, ordered and summarized |
| `GET /projects/<slug>` | Published project landing |
| `GET /projects/<slug>/docs` | Documentation home, when enabled |
| `GET /projects/<slug>/docs/<path:doc_path>` | Published document in selected version |
| `GET /projects/<slug>/releases` | Synced GitHub release metadata, when enabled |
| `GET /projects/<slug>/releases/manifest.json` | Versioned DevLog-native metadata manifest; not an installer protocol |
| `GET /projects/<slug>/releases/<release_id>` | Cached release detail keyed by local numeric release ID |
| `GET /projects/<slug>/downloads/<asset-id>` | **Phase 06 only**: verified mirrored asset or canonical fallback |

Keep `/posts` available even if `/` renders the blog; use canonical URL/redirect semantics that avoid duplicate search-engine content and redirect loops. Do not change `/post/<slug>`.

## Execution and ownership

| Phase | Plan | Scope | Depends on | State |
|---|---|---|---|---|
| 01 | [Project foundation and landing](project_pages_phase_01_foundation.md) | ORM, migration, admin, themes/layout presets, `/projects` and project landing | None | Implemented; see completion evidence |
| 02 | [Navigation and home selection](project_pages_phase_02_navigation_home.md) | Navbar resolver, Projects dropdown, direct-project links, site homepage | 01 | Implemented; see completion evidence |
| 03 | [Local documentation](project_pages_phase_03_local_docs.md) | Doc model, local authoring, viewer, safe Markdown routing | 01; merge after 02 | Partially implemented; browser/accessibility gates open |
| 04 | [Repository documentation sync](project_pages_phase_04_repository_docs.md) | GitHub snapshot ingestion, asset/link handling, sync controls | 03 | Partially implemented; lock/scheduler/image acceptance open |
| 05 | [Canonical release catalog](project_pages_phase_05_releases.md) | GitHub releases/asset metadata, direct GitHub downloads | 01; merge after 04 | Partially implemented; refresh/UI/API tests remain |
| 06 | [Optional mirrors and installer interface](project_pages_phase_06_distribution.md) | DevLog-native metadata manifest; bounded binary mirrors deferred | 05 | Manifest-only slice implemented; no installer compatibility claim |

Merge in numeric order to avoid migrations, admin settings, navigation and route-file conflicts. Phase 05 is logically independent of documentation but deliberately scheduled after 04 for predictable ownership. Phase 06 can be deferred indefinitely without weakening the first five phases.

**Single-owner boundaries:**

| Contract | Owner |
|---|---|
| Project records, visibility and validation | Project service backed by Project ORM |
| Global site/page/project navigation | `app/services/navigation.py` or a single navigation service extending it |
| Root/home resolution and canonical URL selection | Dedicated home service, called by the public index route and context processors |
| Markdown sanitization/code language | `app/markdown_renderer.py`; never another sanitizer |
| Theme colors and themes catalog | `app/themes/`; project rendering only scopes registry-resolved variables |
| Static stylesheet colors/typography | Existing theme tokens and `app/static/css/` ownership rules |
| Documentation path/link resolution | One docs resolver service, shared by admin preview and public renderer |
| GitHub data acquisition | Dedicated GitHub client with strict host and resource constraints |
| Release metadata and source identity | Release-sync service; GitHub is canonical |
| Mirror bytes and download response | Dedicated streamed artifact storage/download service; do not extend image uploader ad hoc |
| Browser route → JavaScript modules | `app/static/js/main.js` |
| Database schema changes | Alembic, linear chain from then-current head |

## Cross-cutting acceptance gates

- Preserve current defaults after migration: blog at `/`, no Projects dropdown, no project fetches, existing page menu stable. Existing `/page`, `/pages`, `/post`, feeds and admin work unchanged.
- Verify on both SQLite and PostgreSQL where supported, using migrations from empty and upgrades from existing schema; at least verify Alembic current head, upgrade and downgrade boundaries per phase. Avoid adding more Alembic heads.
- Do not create a new mandatory runtime worker, Redis service, third-party API token, or object-storage requirement. Every external feature is individually disabled or degraded cleanly when unconfigured.
- Use stable database IDs for navigation ordering and home target, never a mutable slug; normalize slugs and preserve routes/SEO behavior on rename with an explicit redirect or invalidation policy.
- Evaluate route precedence, CSP, SSRF, XSS, Markdown relative links, link safety, filename traversal, publication leaks, migration atomicity, rate limits, download integrity, and backup/restore behavior as appropriate to the phase.
- Add unit/integration tests for Flask routes, models, API scopes, migrations, service decisions; add rendered Chromium E2E accessibility/mobile tests under `tests/e2e/` using its separate database. Do not mix a live server with the shared migration-test database.
- Run project-scope tests, `ruff check .`, `ruff format --check .`, `mypy app/ devlog_cli/`, `npm run build` if assets changed, and the release gate when relevant. Record **actual** results, not expected results.
- On shipping each phase, add `## Completion` with status, changes and evidence, update `architecture/` authoritative docs and relevant module override(s), and revise the status in `plans/AGENTS.override.md`. Never mark a phase complete on code inspection alone.

## Explicit exclusions and decisions deferred

No hosted Git service, GitHub repository write access, repo source-code viewer, automated building/signing, upload of arbitrary external binaries, release publication on GitHub, private GitHub repo sync in the initial scope, installer execution, mandatory background daemon, or blanket redirects of old post URLs. Project–post relationships, project-specific changelog rendering, code search, and cross-project search are later enhancements, not gates.

Eggpack/eggup compatibility needs their exact manifest and signature/update contracts to be inspected before implementation. A generic DevLog release JSON response must **not** be advertised as a compliant installer protocol merely because it has version and SHA-256 fields.

## Delivery and closure

Each phase should be implemented on its own task branch and merge in the order above. Record test commands, behavior and risk acceptance in the phase file. A completed feature belongs in architecture docs; this roadmap and phase plans remain historical evidence. The optional mirror phase must have a separate operator go/no-go gate based on storage cost, streaming implementation, and integrity tests.

## Completion

**Status:** Phases 01–02 implemented; Phases 03–05 partially implemented; Phase 06 has the DevLog-native manifest slice, while binary mirrors remain deferred. Current checks: focused project/docs/releases/GitHub/migration tests passed (140 passed); migration head, upgrade/downgrade, and fresh-schema checks passed; Ruff passed; frontend build passed. Targeted mypy reported no issues in five selected integration files when `--follow-imports=silent` was used; broader mypy remains affected by existing repository errors. No full test suite or browser E2E was run in this continuation. Detailed gaps and evidence are listed in each phase record. No commit or push was made.
