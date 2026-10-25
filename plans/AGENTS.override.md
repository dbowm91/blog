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

Two series still have work outstanding, plus a short residual list. Everything
else in `plans/` is history.

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

**Migration chain.** The current single Alembic head is
`add_appearance_settings_to_sitesettings`. The series' four migrations sit in
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
