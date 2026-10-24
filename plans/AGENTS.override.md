# Plans Module Override

## Overview

This module contains implementation plans and historical records of completed architecture improvements.

## Active Plans

### Site Identity, Authorship and Layout (open — 2026-10-24)

Roadmap: `site_identity_authoring_roadmap.md`

Origin: an operator review of the running instance on 2026-10-24. Every
finding was confirmed by rendering the application in Chromium and measuring
the DOM, not by reading templates. The measurement table is in the roadmap.

| Phase | File | Status |
|---|---|---|
| 01 | `site_identity_phase_01_admin_settings.md` | Complete — Part A (theme preview placement) and Part B (comments switch, editable footer, page menu) |
| 02 | `site_identity_phase_02_user_profiles.md` | Complete — profile fields, avatar, short/full bio, admin profile editor |
| 03 | `site_identity_phase_03_public_auth.md` | Complete — public login, account page, nav affordance |
| 04 | `site_identity_phase_04_authorship_and_author_pages.md` | Complete — `Post.author_id`, author page, author links |
| 05 | `site_identity_phase_05_page_navigation.md` | Complete — published pages reachable from the nav and footer |
| 06 | `site_identity_phase_06_comments_layout.md` | Planned — comment measure, comment styling, mobile |

Phases 01–05 shipped and carry their verification evidence in their own
`## Completion` sections. Phase 06 remains open, so the series stays in
**Active Plans**.

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

**Migration chain.** The single Alembic head is `drop_theme_preset_column`.
Each phase adds one migration with `down_revision` pointing at the previous
phase's revision, in series order.

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

## Historical Plans

The **Frontend Corrective** series (2026-10-23) closed 50 findings across the public
site, admin dashboard, stylesheet layer, and JavaScript module layer. It is the
first plan series to carry per-phase `## Completion` sections with verification
evidence — use that format for future series. The **Site Identity, Authorship and
Layout** series (2026-10-24) follows the same format.

| Phase | File | Status |
|---|---|---|
| 01 | `frontend_corrective_phase_01_image_pipeline.md` | Complete |
| 02 | `frontend_corrective_phase_02_public_interaction_and_build.md` | Complete |
| 03 | `frontend_corrective_phase_03_admin_form_contracts.md` | Complete |
| 04 | `frontend_corrective_phase_04_css_cascade_and_theme_tokens.md` | Complete |
| 05 | `frontend_corrective_phase_05_accessibility_and_seo.md` | Complete |

All 50 findings were resolved; none were deferred. Each phase file carries a
`## Completion` section recording what changed and how it was verified.

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
