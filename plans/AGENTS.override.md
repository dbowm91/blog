# Plans Module Override

## Overview

`plans/` holds two different kinds of document, and the distinction matters:

- **Plan work** — a specification for work that has not shipped yet.
- **Historical records** — the design, acceptance criteria and verification
  evidence for work that has shipped.

This file is the index. It says which is which, and it says where the *outcome*
of every completed plan is documented today.

**The outcome of completed work lives in `architecture/`, not in `plans/`.**
[`architecture/overview.md`](../architecture/overview.md) is the index of the
system as it is now; each of its 18 sections links to a deep-dive document. The
plan files here are the *history* — they carry the reasoning, the acceptance
criteria and the verification evidence that the architecture docs deliberately do
not repeat. **Never treat a plan file as a description of current behaviour.**

Every plan file carries a one-line status banner directly under its title. Read
that banner first; it names the authoritative document for that work.

## Active Plans

This index tracks open series, a residual backlog, and recently completed work.
Use the per-phase status banners and tables below to distinguish work from history.

### 1. Site Identity, Authorship and Layout — Phase 06 open

Roadmap: [`site_identity_authoring_roadmap.md`](site_identity_authoring_roadmap.md)

Origin: an operator review of the running instance on 2026-10-24. Every finding
was confirmed by rendering the application in Chromium and measuring the DOM, not
by reading templates. The measurement table is in the roadmap.

| Phase | File | Status |
|---|---|---|
| 01 | `site_identity_phase_01_admin_settings.md` | Complete — Part A (theme preview placement) and Part B (comments switch, editable footer, page menu) |
| 02 | `site_identity_phase_02_user_profiles.md` | Complete — profile fields, avatar, short/full bio, admin profile editor |
| 03 | `site_identity_phase_03_public_auth.md` | Complete — public login, account page, nav affordance |
| 04 | `site_identity_phase_04_authorship_and_author_pages.md` | Complete — `Post.author_id`, author page, author links |
| 05 | `site_identity_phase_05_page_navigation.md` | Complete — published pages reachable from the nav and footer |
| 06 | `site_identity_phase_06_comments_layout.md` | **Open — not started.** The file's own `## Completion` section records `**Status:** Not started.` Nothing in it has shipped. |

Phases 01–05 shipped and carry their verification evidence in their own
`## Completion` sections. **Phase 06 is the only outstanding work in this
series**: comment measure, comment styling, reply hierarchy, reply form, mobile.
It is CSS and template work only — it needs no migration.

Shipped outcome: [`architecture/frontend/templates.md`](../architecture/frontend/templates.md),
[`architecture/routes/public-routes.md`](../architecture/routes/public-routes.md),
[`architecture/routes/admin-routes.md`](../architecture/routes/admin-routes.md),
[`architecture/core/models.md`](../architecture/core/models.md).

**Run the phases in order.** They share `app/models.py`,
`app/templates/base.html`, `app/routes/admin/settings.py`,
`app/templates/admin/settings.html`, `app/templates/post.html` and
`app/static/css/public.css`. Phases 02 and 06 touch disjoint files and may be
developed in parallel, but the merge order stays 01 → 02 → 03 → 04 → 05 → 06 so
the migrations chain in one direction.

**Single-owner rules for this series** (one value, one producer):

| Value | Owner |
|---|---|
| `SiteSettings.comments_enabled` | Phase 01 |
| `SiteSettings.footer_text` | Phase 01 |
| `SiteSettings.show_pages_in_menu`, `menu_pages` | Phase 05 |
| `User.display_name`, `bio_short`, `bio_full`, `avatar_path` | Phase 02 |
| `Post.author_id` | Phase 04 |
| The `.comments` / `.comment*` CSS block | Phase 06 |

Phase 05 adds its page-menu fields to the **Site** settings section and the
same `POST /admin/settings/site` endpoint that Phase 01 creates. It must not
create a second settings form for the same page.

**Migration chain.** The single Alembic head at the 2026-10-28 planning baseline is
`drop_syntax_theme_column` (which follows `add_appearance_settings_to_sitesettings`). The series' four migrations sit in
the chain in order — `add_site_settings_content_flags`, `add_user_profile_fields`,
`add_post_author`, `add_page_menu_fields` — and are followed by
`reconcile_schema_with_models` and the current head. Any new phase adds one
migration with `down_revision` pointing at the current head. Phase 06 needs
none.

**Rendering rule for this series.** New CSS consumes theme tokens only
(`var(--text-dim)`, `var(--bg-surface)`, `var(--border)`, `var(--radius)`,
`var(--space-*)`). No colour literals, no new tokens, no renames. Bios and any
new rich-text field render through `app/markdown_renderer.py` — the single
sanitised markdown producer. No second markdown path.

**What the review confirmed**, so the next reader does not re-derive it: the
theme preview sat *below* the theme selector it previews, so the operator had
to keep travelling up and down the page to see a result — the preview
**mechanism itself works** and was deliberately not redesigned, only the
placement changed; there was no public login, so the three non-admin accounts
in the database could not authenticate at all; `users` had no profile fields
and `/admin/users` had no profile editor; `posts` had no `author_id` and the
rendered author was a single config-level value that was empty by default and
never a link; published pages worked at `/page/<slug>` but nothing on the site
linked to them; the footer was hardcoded; there was no comments switch; and
the comment block had no styling at all and sat 176px to the left of the post
column on desktop.

### 2. Configuration, Installation and Operator CLI — Release 4 open

Roadmap: [`config_install_cli_roadmap.md`](config_install_cli_roadmap.md)

Releases 1–3 shipped (see Historical Plans). **Release 4 did not.**

| Phase | File | Status |
|---|---|---|
| I | `config_install_cli_release_4_phase_i_backup_and_recovery.md` | **Partially implemented.** Shipped: `devlog backup create` / `verify` / `inspect`, WAL-safe `sqlite3.backup()` capture, AES-256-GCM encryption, retention in the scheduler, and the doctor backup-directory check. **Not shipped:** the versioned backup manifest (I1), backup listing / index / status (I10), the safe restore planner and restore transaction (I7–I9), and the `devlog backup list`, `devlog backup restore` and `devlog backup prune` commands. |
| J | `config_install_cli_release_4_phase_j_update_and_uninstall.md` | **Not started.** There is no `devlog update` and no `devlog uninstall` command, and no update-planner, rollback or uninstall service anywhere in `app/` or `devlog_cli/`. |

The roadmap's own `## Status` section still reads "Proposed implementation
roadmap". That line predates Releases 1–3 and is stale; the table above plus the
shipped outcome documents are authoritative.

Phase I is a prerequisite for Phase J — the update flow depends on a trustworthy
pre-update backup and restore path — so close the restore gap first.

Shipped outcome so far: [`architecture/services/backup.md`](../architecture/services/backup.md),
[`architecture/services/doctor.md`](../architecture/services/doctor.md).

### 3. Residual items from the 2026-05-01 consolidated backlog

[`plan.md`](plan.md) was written on 2026-05-01, before any of the series above.
**Its checkboxes were never maintained, so an unchecked box there does not mean
the work is open.** Almost everything in it shipped under a later series. The
items that genuinely remain unimplemented are:

| Item | Description |
|---|---|
| STRAT-1 | Celery vs APScheduler — decide whether to stabilise Celery or remove it in favour of APScheduler and drop the Redis dependency. Celery is still present (`app/celery_app.py`). |
| STRAT-2 | Codebase reduction — conditional on STRAT-1. `app/webhooks.py`, `app/celery_app.py`, `app/page_view_buffer.py`, `app/backup_encryption.py` and `app/tag_cache.py` all still exist. |
| STRAT-3 | Python 3.14 compatibility — `pyproject.toml` still declares `requires-python = ">=3.12"`. |
| FE-5 | Critical CSS automation — `vite-plugin-beasties` is not in the Vite build. |

Everything else in `plan.md` is implemented. Do not re-open those items, and do
not treat the file's file paths as current — several have since been renamed or
split into packages (`app/config.py` → `app/config_legacy.py` plus the
`app/config/` package; `app/routes/public.py` → `app/routes/public/`;
`app/routes/admin/posts.py` → `app/routes/admin/posts/`).

### 4. Visual Design and Readability — 2026-10-27

Roadmap: [`visual_design_roadmap.md`](visual_design_roadmap.md)

Origin: an operator review of the running instance on 2026-10-27, measured in
Chromium in both colour schemes at 390px, 768px and 1280px. **18 findings**:
2 critical, 7 high, 7 medium, 2 low. **All six phases have shipped.**

| Phase | File | Status |
|---|---|---|
| 01 | `visual_design_phase_01_code_blocks.md` | **Complete.** Code blocks are syntax-highlighted, copyable, and coloured by the active theme. The fence language survives sanitisation, Prism is a built npm dependency, the `syntax_theme` setting and the six vendored palettes are gone. |
| 02 | `visual_design_phase_02_text_roles_and_contrast.md` | **Complete.** Two derived roles — `--text-caption` and `--accent-text` — carry the text a reader must read and hold 4.5:1 in every bundled theme. The decorative allowlist is documented; eight themes were given a distinguishable code surface. |
| 03 | `visual_design_phase_03_prose_measure.md` | **Complete.** The prose column is capped at 34 em and centred, so it carries 70 characters per line at 1280px and at 768px, and the phone layout is unchanged. |
| 04 | `visual_design_phase_04_imagery.md` | **Complete.** The placeholder is a themed mark with no palette of its own, and the card and related bands are 16:9, so a 16:9 screenshot is no longer cropped. |
| 05 | `visual_design_phase_05_index_layout.md` | **Complete.** The index is a two-column grid from 1024px, the sidebar's duplicate "Recent posts" block and the query behind it are gone, and a card shows four tags and names the count it hides. |
| 06 | `visual_design_phase_06_article_furniture.md` | **Complete.** The share panel stands below the article, and the structural elements take one shared voice — the mono face, an uppercase treatment and the caption role. |

**Run the phases in order.** Phases 01, 02, 03 and 06 all edit
`app/static/css/base.css`, and phases 04 and 05 both edit
`app/static/css/public.css` at `.post-card-img`. Phase 01 is also the only
phase that retires a setting and the only one that carries a migration.

**Operator decisions of 2026-10-27**, binding on this series: code blocks are
theme-aware and the `syntax_theme` setting is retired; the share bar moves
below the article; the index sidebar's "Recent posts" block is dropped.

**Single-owner rules for this series** (one value, one producer):

| Value | Owner |
|---|---|
| The fence language on a code block | `app/markdown_renderer.py` |
| The code block's surface | `app/static/css/base.css` |
| The syntax token colours | `app/static/css/prism.css` |
| The caption colour and the accent-text colour | The theme runtime (`app/themes/translate.py`) |
| The prose measure | `app/static/css/base.css` |
| The post placeholder mark | `app/static/css/public.css` — the `.img-placeholder` mask rule; the SVG is never loaded as an image |
| The post list grid | `app/static/css/public.css` — `.posts-list`; `app/static/css/critical.css` paints the same grid because it is the first paint |
| The card's tag row and its cap | `app/templates/macros.html` — `post_tag_row`; the chip's styling is `app/static/css/public.css` (`.tag-more`) |
| The structural voice | the stylesheet that owns each label — `app/static/css/public.css` for `.post-toc-title` and `.share-label`, `app/static/css/layout.css` for `.sidebar-title` |
| The share panel's position | `app/templates/_post_content.html` |
| The post's own tag list | `app/templates/_post_content.html` — the footer row; a card never hides the only copy of a tag |

**The sanitiser does not move.** `MARKDOWN_ALLOWED_ATTRIBUTES` keeps `class` on
`span` and `div` only. The renderer re-attaches the fence language *after*
`nh3.clean()`, and a test asserts the allowlist is unchanged.

Shipped outcome: [`architecture/frontend/static-assets.md`](../architecture/frontend/static-assets.md),
[`architecture/frontend/templates.md`](../architecture/frontend/templates.md),
[`architecture/core/themes.md`](../architecture/core/themes.md) and
[`architecture/frontend/overview.md`](../architecture/frontend/overview.md), which
carries the series' cross-layer contracts.

**The text roles established by Phase 02.** `--text-muted` is decoration — icon
strokes, separators, disabled states — and its allowlist is seven rules across
three stylesheets. `--text-caption` is the text a reader must read, and
`--accent-text` is the accent on a tinted chip. Both are derived by the theme
runtime, so no theme file declares them and the gate holds them at 4.5:1.
Phases 05 and 06 style text at content size: they use these roles and did not
reintroduce `--text-muted` for content.

### 5. Project Pages, Documentation and Distribution — roadmap and current worktree status

Roadmap: [project_pages_roadmap.md](project_pages_roadmap.md).

Origin: repository source review of the current Pages, navigation, themes, Markdown, storage, public/admin/API routes and migration chain. Phases 01–02 are implemented; Phases 03–05 are partially implemented in this worktree with open acceptance gates recorded in their plans. GitHub stays canonical for releases; Phase 06 binary mirrors and any eggpack/eggup support remain gated optional work.

| Phase | File | Status |
|---|---|---|
| 01 | [Project foundation and landing](project_pages_phase_01_foundation.md) | **Implemented**; Project ORM/admin, `/projects`, themed layout presets |
| 02 | [Navigation and home selection](project_pages_phase_02_navigation_home.md) | **Implemented**; configurable Projects menu, direct-link deduplication, Page/Project homepage, `/posts` |
| 03 | [Local documentation](project_pages_phase_03_local_docs.md) | **Partial**; local authoring/viewer and assets implemented; browser/accessibility gates open |
| 04 | [Repository documentation sync](project_pages_phase_04_repository_docs.md) | **Partial**; bounded snapshot sync implemented with a database-backed cross-worker lease; scheduler/image import gates open |
| 05 | [Canonical release catalog](project_pages_phase_05_releases.md) | **Partial**; cached metadata and public catalog implemented; operational/API tests remain |
| 06 | [Optional distribution](project_pages_phase_06_distribution.md) | **Manifest-only**; versioned DevLog JSON is implemented; binary mirrors deferred, no eggpack/eggup claim |

**Order:** 01 → 02 → 03 → 04 → 05 → 06; 05 logically depends on 01 but merges after 04 to preserve a single migration chain. 06 may be deferred indefinitely. Each phase records its own `## Completion` evidence before status changes. Add the shipped architectural outcome to `architecture/` only as phases land.

**Ownership:** `app/services/navigation.py` remains the single site-navigation producer (do not build a separate project nav resolver); `app/markdown_renderer.py` remains the Markdown sanitization producer; `app/themes/` owns colors and named theme resolution; `app/static/js/main.js` owns route module registration; a new GitHub client owns source reads; a distinct streaming artifact backend, **not** image media upload/storage byte-buffer methods, would own future binary mirrors.

**Compatibility:** blog remains the default homepage, Projects navbar is off by default, all existing Pages/Post URLs remain functional, all external integrations are optional. Page menu ownership stays with Site Identity Phase 05. New Alembic revisions must use the **actual current head** when coded, not a revision copied from this date.

### 6. Optional AI-Assisted Post Authoring — 2026-10-28

Roadmap: [`ai_authoring_roadmap.md`](ai_authoring_roadmap.md)

Operator request: optional **AI write TL;DR** and **AI suggest tags** on the post new/edit editor, with candidate generation followed by conditional existing-tag semantic reconciliation. A third action, **AI suggest title**, was added later to the same editor; the shipped behaviour is in `architecture/`, not here. The code and deterministic/browser acceptance tests are implemented; no migrations, automatic publishing, public AI, or AI calls unless an operator explicitly configures a model. The default is off; a local OpenAI-compatible model works without an API key.

| Phase | File | Status |
|---|---|---|
| 01 | `ai_authoring_phase_01_provider_summary.md` | **Implemented; default-off/local-compatible opt-in.** Env-only secrets, bounded authenticated endpoint, summary; OpenCode Go usage remains adapter-gated |
| 02 | `ai_authoring_phase_02_tag_reconciliation.md` | **Implemented; focused suite passed.** Candidate tags, exact reuse, conditional second pass, bounded privacy-safe catalog; full suite baseline failures documented separately |
| 03 | `ai_authoring_phase_03_editor_acceptance.md` | **Implemented; default-off/local-compatible opt-in.** Conditional buttons, explicit review/apply, drafts, E2E |

**Implementation order: 01 → 02 → 03.** Blank model means absent buttons and no provider requests; explicitly configured local compatible models need no key. Post Save remains the sole persistence step. The current [OpenCode Go documentation](https://opencode.ai/v2/docs/console/go/) says Go is designed for coding agents making similar requests; editorial summarization/classification is not shown as an allowed use. Do not enable that adapter for editorial drafts unless OpenCode explicitly permits it. This Go-specific gate does not block the local-compatible provider. Rate limiting remains unlimited by default, with optional per-user configuration; the rationale is in `architecture/services/overview.md`. Hosted AI CI and unrelated general-CI baseline failures are tracked separately in the roadmap. Keep this entry Active only while the OpenCode Go usage restriction needs follow-up.

### Media Library and Inline Authoring — Phase 03 open

Roadmap: [`media_authoring_roadmap.md`](media_authoring_roadmap.md)

Origin: operator request on 2026-10-28 to categorize all media, support inline image/video insertion and arbitrary-file attachments from the editors, and add safe Markdown HTML/embed blocks.

| Phase | File | Status |
|---|---|---|
| 01 | [`media_authoring_phase_01_library_and_uploads.md`](media_authoring_phase_01_library_and_uploads.md) | **Implemented.** Categorized inventory, type-specific uploads, author/admin media APIs, and forced downloads. |
| 02 | [`media_authoring_phase_02_markdown_and_embeds.md`](media_authoring_phase_02_markdown_and_embeds.md) | **Implemented.** Safe inline video/YouTube embed block, shared sanitizer, aligned CSP, and shared feed renderer. |
| 03 | [`media_authoring_phase_03_editor_pickers.md`](media_authoring_phase_03_editor_pickers.md) | **Open — not started.** Separate Media and Attachment controls with upload and Markdown insertion. |

Run phases in order: Phase 01 establishes trustworthy media classification, upload APIs, and download URLs; Phase 02 defines what the shared Markdown renderer can safely emit; Phase 03 consumes those contracts in both post and page editors. The series must remain Active until each phase has an evidence-backed completion record and the shipped behavior is documented in `architecture/`.

## Historical Plans

The **Frontend Corrective** series (2026-10-23) closed 50 findings across the public
site, admin dashboard, stylesheet layer, and JavaScript module layer. It is the
first plan series to carry per-phase `## Completion` sections with verification
evidence — use that format for future series. The **Site Identity, Authorship and
Layout** series (2026-10-24) follows the same format.

### Configuration, Installation and Operator CLI — Releases 1–3 (2026-07-16)

| File | Status | Shipped outcome |
|---|---|---|
| `config_install_cli_roadmap.md` | The series' design of record. Releases 1–3 shipped; Release 4 is open (see Active Plans). | [`architecture/overview.md`](../architecture/overview.md) |
| `config_install_cli_release_1_phase_a_cli_packaging.md` | Implemented — standalone `devlog` console script, output/error/exit-code model, package data | [`architecture/deployment/cli.md`](../architecture/deployment/cli.md) |
| `config_install_cli_release_1_phase_b_configuration_core.md` | Implemented — typed config dataclasses, loader, validation layers, provenance, profiles | [`architecture/core/configuration.md`](../architecture/core/configuration.md) |
| `config_install_cli_release_1_phase_c_service_extraction.md` | Implemented — operational logic moved out of `app/cli.py` into `app/services/operations/` | [`architecture/services/operations.md`](../architecture/services/operations.md) |
| `config_install_cli_release_1_closure_pass.md` | Implemented — CI authority, clean-wheel job, static-analysis coverage, unknown-key policy, `config_legacy.py` containment | [`architecture/deployment/cicd.md`](../architecture/deployment/cicd.md) |
| `release_1_closure.md` | **Release 1 closure record (2026-07-16)** — the only dated closure evidence in this series | [`architecture/overview.md`](../architecture/overview.md) |
| `config_install_cli_release_2_phase_d_onboarding.md` | Implemented — `devlog onboard detect/plan/run/resume` | [`architecture/core/onboarding.md`](../architecture/core/onboarding.md) |
| `config_install_cli_release_2_phase_e_installer_and_artifacts.md` | Implemented — `scripts/install.sh`, release artifacts, checksum verification | [`architecture/deployment/installation.md`](../architecture/deployment/installation.md) |
| `config_install_cli_release_2_phase_f_filesystem_layout.md` | Implemented — `RuntimePaths`, `devlog paths status/discover-legacy/migrate/check` | [`architecture/core/filesystem.md`](../architecture/core/filesystem.md) |
| `config_install_cli_release_2_closure_acceptance.md` | Acceptance pass — the acceptance criteria were met by the shipped onboarding, installer and paths work | [`architecture/deployment/installation.md`](../architecture/deployment/installation.md) |
| `config_install_cli_release_3_phase_g_deployment_and_lifecycle.md` | Implemented — `devlog deploy render/install/check`, systemd/Compose/proxy rendering, drift detection | [`architecture/deployment/managed-deployment.md`](../architecture/deployment/managed-deployment.md) |
| `config_install_cli_release_3_phase_h_diagnostics.md` | Implemented — `devlog doctor`, shared diagnostic registry, safe fixes | [`architecture/services/doctor.md`](../architecture/services/doctor.md) |

Releases 2 and 3 never adopted the `## Completion` convention, so they carry no
in-file closure record; their status was established from the shipped
implementation, not from the plan text.

### Frontend Corrective (2026-10-23)

| Phase | File | Status |
|---|---|---|
| 01 | `frontend_corrective_phase_01_image_pipeline.md` | Complete — 4 findings closed |
| 02 | `frontend_corrective_phase_02_public_interaction_and_build.md` | Complete — 13 findings closed |
| 03 | `frontend_corrective_phase_03_admin_form_contracts.md` | Complete — 14 findings closed |
| 04 | `frontend_corrective_phase_04_css_cascade_and_theme_tokens.md` | Complete — 9 findings closed |
| 05 | `frontend_corrective_phase_05_accessibility_and_seo.md` | Complete — 10 findings closed |

All 50 findings were resolved; none were deferred. Each phase file carries a
`## Completion` section recording what changed and how it was verified, and the
roadmap records 125 new automated tests, 55 passing `tests/e2e/` tests and 17/17
browser checks.

Four defects were found during implementation that were not in the original scope,
and they are recorded in the roadmap's closure section: the newsletter email
template carried the same image double-prefix, `mobile-menu.jsx` detached its click
target when swapping icons so the mobile menu could not open, `.lightbox-caption`
painted `--text-on-accent` on a dark scrim, and the new browser tests broke the
migration round-trip tests until they were moved to `tests/e2e/`.

Browser-level tests belong under `tests/e2e/`, on the e2e application's own
database. A live server thread on the session-scoped application shares its
database with the migration tests and corrupts their DDL.

Shipped outcome: [`architecture/frontend/overview.md`](../architecture/frontend/overview.md),
[`architecture/frontend/templates.md`](../architecture/frontend/templates.md),
[`architecture/frontend/static-assets.md`](../architecture/frontend/static-assets.md).

### Halloy Theme System (2026-07-13)

The roadmap records `Status: Complete` against every one of its fifteen phases,
plus a `## Final verification pass` section marked `Status: Complete`.

| File | Status |
|---|---|
| `halloy_theme_system_roadmap.md` | Closed — per-phase `Status: Complete` for 01–15 and a completed final verification pass |
| `halloy_theme_phase_01_inventory_and_token_contract.md` … `halloy_theme_phase_15_legacy_removal_and_release_closure.md` (15 files) | Complete — recorded per phase in the roadmap |
| `halloy_theme_phase_04_05_corrective_closure.md` | Complete — `## Completion Status`, COMPLETE 2026-07-13, 1110 theme tests passing, `ruff` and `mypy` clean |
| `halloy_theme_phase_04_05_small_closure_pass.md` | Complete — explicit cache freshness contract, SHA-256 resource fingerprinting, CI theme-package gate, invalidation tests |
| `halloy_theme_phase_06_10_corrective_pass.md` | Complete — recorded at the Phase 06–10 entry in the roadmap |
| `halloy_theme_final_verification_and_policy_pass.md` | Complete — the roadmap's `## Final verification pass` section records the pass as done. The roadmap does not name this file, which is why it is listed here. |

Shipped outcome: [`architecture/core/themes.md`](../architecture/core/themes.md),
plus the operator-facing guides under `../docs/themes/`.

### Standalone records

| File | Status |
|---|---|
| `plan.md` | Historical — the 2026-05-01 consolidated backlog. Superseded; see Active Plans §3 for the residual items. |
| `release_1_closure.md` | Historical — the Release 1 closure record (2026-07-16): CI job list, test results, known limitations and gap closure. The only dated closure record in this directory. |

## Evidence Convention

A plan file may call itself complete only if **the file itself says so**. Two
forms are accepted, both in use here:

- a `## Completion` section carrying `**Status:** Complete`, what changed, and
  how it was verified — the Frontend Corrective and Site Identity series;
- a `## Completion Status` section, or a dated closure record — the Halloy
  corrective closure and `release_1_closure.md`.

The Configuration/CLI phase files never adopted this convention: they carry
forward-looking acceptance criteria and no completion section. Their status was
established from the shipped implementation, not from the plan text. If you
extend one of those files, **add** a `## Completion` section — do not rewrite the
acceptance criteria.

When you close a phase:

1. Add a `## Completion` section to the phase file: the status, what changed,
   and the verification that was actually run.
2. Move the series from Active Plans to Historical Plans in this file, and point
   it at the architecture document that now describes the outcome.
3. Leave the rest of the phase file alone. The body is the historical record of
   what was planned and why.

## Maintenance Notes

When updating code that affects documented behavior:
1. Update the relevant AGENTS.override.md for that module
2. If adding new behavior, consider updating AGENTS.md Important Notes
3. If documentation becomes stale, update architecture docs or add a note in agent-maintainer-notes.md
4. Prefer symbolic references (function names) over line numbers to reduce maintenance burden
5. Update this file's tables in the same change that closes a plan phase. A plan
   file with a stale status banner is worse than no banner at all.
6. Keep this file's Active/Historical split honest. A plan listed under
   Historical that still has open work will be skipped; a plan listed under
   Active that has shipped will be re-implemented.
