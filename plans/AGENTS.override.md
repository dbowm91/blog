# Plans Module Override

## Overview

This module contains implementation plans and historical records of completed architecture improvements.

## Active Plans

No plan series is currently open.

### Frontend Corrective (complete — 2026-10-23)

Roadmap: `frontend_corrective_roadmap.md`

| Phase | File | Status |
|---|---|---|
| 01 | `frontend_corrective_phase_01_image_pipeline.md` | Complete |
| 02 | `frontend_corrective_phase_02_public_interaction_and_build.md` | Complete |
| 03 | `frontend_corrective_phase_03_admin_form_contracts.md` | Complete |
| 04 | `frontend_corrective_phase_04_css_cascade_and_theme_tokens.md` | Complete |
| 05 | `frontend_corrective_phase_05_accessibility_and_seo.md` | Complete |

All 50 findings were resolved; none were deferred. Each phase file carries a
`## Completion` section recording what changed and how it was verified.

## Historical Plans

All implementation plans have been completed and merged. The detailed task lists are preserved in git history for reference.

The **Frontend Corrective** series (2026-10-23) closed 50 findings across the public
site, admin dashboard, stylesheet layer, and JavaScript module layer. It is the
first plan series to carry per-phase `## Completion` sections with verification
evidence — use that format for future series.

Four defects were found during implementation that were not in the original scope,
and they are recorded in the roadmap's closure section: the newsletter email
template carried the same image double-prefix, `mobile-menu.jsx` detached its click
target when swapping icons so the mobile menu could not open, `.lightbox-caption`
painted `--text-on-accent` on a dark scrim, and the new browser tests broke the
migration round-trip tests until they were moved to `tests/e2e/`.

Browser-level tests belong under `tests/e2e/`, on the e2e application's own
database. A live server thread on the session-scoped application shares its
database with the migration tests and corrupts their DDL.

For current architecture documentation, see the `architecture/` directory.

## Maintenance Notes

When updating code that affects documented behavior:
1. Update the relevant AGENTS.override.md for that module
2. If adding new behavior, consider updating AGENTS.md Important Notes
3. If documentation becomes stale, update architecture docs or add a note in agent-maintainer-notes.md
4. Prefer symbolic references (function names) over line numbers to reduce maintenance burden