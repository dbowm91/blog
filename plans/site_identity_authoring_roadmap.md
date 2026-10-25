# Site Identity, Authorship and Layout Roadmap

> **Plan status: ACTIVE — the series is open.** Phases 01–05 shipped; Phase 06 has not started. See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Date:** 2026-10-24
**Status:** Open — Phases 01 (both parts), 02, 03, 04 and 05 shipped; Phase 06 planned
**Origin:** operator review of the running instance (2026-10-24)
**Series prefix:** `SIA-`

## Context

The operator reviewed the running application and reported eight gaps: the theme
preview sits below the theme selector, there is no login page for ordinary users,
`/admin/users` has no profile editor, authors are not linked to anything, pages
created in `/admin/pages` are unreachable, the footer is not editable, comments
cannot be switched off, and the comment column does not align with the post
column.

Every item below was verified against the running instance before the plan was
written. The verification harness and its output are recorded in each phase file;
no finding is based on reading alone.

## Operator clarification (2026-10-24)

After the series was written, the operator corrected one item: the theme
selector and preview **mechanism works**, and the complaint is placement only —
the preview should sit above the control it previews so the operator does not
have to keep travelling up and down to see it. Phase 01 was rewritten around
that: the mechanism is untouched, and only the position of the panel, its
reserved footprint, the clear action and the scroll-into-view changed. Phase 01
Part A has since shipped.

## Verification method

Findings were confirmed by rendering `http://localhost:5050` in headless
Chromium and measuring the DOM, not by reading templates. The harness lives at
`/tmp/devlog_review_stubs/review_round2.py` (not committed — it is a scratch
harness, not a test).

| Check | Result |
|---|---|
| Anonymous visitor nav links | `['× -> ', 'Search -> ', 'Posts -> /']` — no login affordance |
| `/page/...` links in nav and footer | none (2 published pages exist in the database) |
| `GET /page/about` | 200 — the route works, the page is simply undiscoverable |
| `.post-body` box @1280px | left 260, right 1020, width 760 |
| `.comments` box @1280px | left 84, right 1196, width 1112 |
| `.comments` border-top / padding-left | `0px` / `0px` — the block has no rules of its own |
| `.author-card` links | 0 — the author name is not a link |
| Listing `.post-author` links | 0 — plain text |
| Admin settings section order (before) | Theme (0), Theme Preview (1), Theme Registry (2) |
| Admin settings section order (after Phase 01 Part A) | Theme Preview (0), Theme (1), Theme Registry (2) |
| Theme preview computed display | `none` before — now visible, with a reserved, non-resizing box |
| Admin nav entries containing "profile" | none |
| `/admin/settings` body text | no "comment", no "footer" |
| `/admin/users` body text | no "bio", no "avatar" |

## Database reality

Read directly from `data/devlog.sqlite3` **before the series shipped**. The
columns and accounts listed below are the state the phases were planned
against; each phase's Completion section records what the schema looks like
now.

- `users` columns: `id, username, email, password_hash, is_admin, reset_token,
  reset_token_expires_at, failed_login_count, locked_until,
  totp_secret_encrypted, totp_enabled, backup_codes_hashed` — **no profile
  fields**.
- `posts` columns: `id, title, slug, body, summary, image, image_alt_text,
  created_at, updated_at, published, published_at, scheduled_publish_at,
  newsletter_sent_at, newsletter_attempts` — **no `author_id`**.
- `site_settings` columns: `id, syntax_theme, custom_css_enabled, custom_css,
  logo_text, theme_dark_name, theme_light_name, theme_default_scheme,
  updated_at` — **no comments flag, no footer text**.
- Users present: `admin` (`is_admin=1`), `author1`, `author2`, `author3`
  (`is_admin=0`). The three non-admin accounts **cannot authenticate at all** —
  `app/routes/admin/auth.py` admits only `user.is_admin`, and no public login
  route exists.
- Pages present: `About` (`/page/about`), `Contact` (`/page/contact`), both
  published and both absent from every navigation surface.

## Phases

| Phase | File | Area | Status |
|---|---|---|---|
| 01 | `site_identity_phase_01_admin_settings.md` | Settings reorganisation, theme preview placement, comments toggle, editable footer | Complete — Part A (theme preview placement) and Part B (comments switch, editable footer, page menu) |
| 02 | `site_identity_phase_02_user_profiles.md` | Profile fields, avatar, short/full bio, admin profile editor | Complete |
| 03 | `site_identity_phase_03_public_auth.md` | Public login, account page, nav affordance | Complete |
| 04 | `site_identity_phase_04_authorship_and_author_pages.md` | Post → author, author page, author links | Complete |
| 05 | `site_identity_phase_05_page_navigation.md` | Making published pages reachable | Complete |
| 06 | `site_identity_phase_06_comments_layout.md` | Comment measure, comment styling, mobile | Planned |

## Execution order

The series is **strictly sequential**. The phases share these files:

- `app/models.py` — 01 (`SiteSettings`), 02 (`User`), 04 (`Post`), 05 (`Page`)
- `app/templates/base.html` — 01 (footer), 03 (nav), 05 (nav + footer)
- `app/routes/admin/settings.py` and `app/templates/admin/settings.html` —
  01 (Site section), 05 (page menu fields)
- `app/templates/post.html` — 04 (author JSON-LD), 06 (comment measure)
- `app/static/css/public.css` — 05 (nav), 06 (comment block)

Phases 02 and 06 touch disjoint files and may be developed in parallel, but the
merge order must still be 01 → 02 → 03 → 04 → 05 → 06 so that the model
migrations chain in one direction.

## Single-owner rules

| Value | Owner | Other phases |
|---|---|---|
| `SiteSettings.comments_enabled` | 01 | 06 reads it to hide the block; 03 does not touch it |
| `SiteSettings.footer_text` | 01 | 05 adds a *separate* page-menu field |
| `SiteSettings.menu_pages` / `show_pages_in_menu` | 05 | 01 does not own page links |
| `User.display_name`, `bio_short`, `bio_full`, `avatar_path` | 02 | 04 reads them |
| `Post.author_id` | 04 | 02 does not write it |
| Comment CSS block (`.comments`, `.comment*`) | 06 | 01 only toggles visibility |

No value may be produced by two producers. The settings page grows a **Site**
section in Phase 01; Phase 05 adds its page-menu fields to that same section and
to the same `POST /admin/settings/site` endpoint rather than creating a second
settings form.

## Cross-cutting constraints

1. **Theme tokens only.** New CSS consumes `var(--text-dim)`,
   `var(--bg-surface)`, `var(--border)`, `var(--text-secondary)`, `var(--radius)`,
   `var(--space-*)` and friends. No colour literals, no new theme tokens, no
   renames.
2. **One markdown producer.** Bios and any new rich-text field render through
   `app/markdown_renderer.py` (`render_markdown`), which is the single sanitised
   pipeline. No second markdown path.
3. **No CSP weakening.** No new inline scripts, no `unsafe-inline`, no injected
   `<style>` without a nonce.
4. **Migrations are additive.** New columns are nullable or carry a default.
   The Alembic head moved from `drop_theme_preset_column` to
   `add_page_menu_fields`; the series added four migrations in chain order —
   `add_site_settings_content_flags`, `add_user_profile_fields`,
   `add_post_author`, `add_page_menu_fields`.
5. **Export/import.** `app/services/serialization.py` enumerates fields
   explicitly. `serialize_post` does not include an author and `users` are not
   exported at all, so `Post.author_id` is intentionally **not** added to the
   export payload — an exported post keeps its author only implicitly, and the
   import assigns the importing admin. This is recorded in Phase 04.
6. **Browser tests belong in `tests/e2e/`.** The e2e application owns its own
   database; a live server thread sharing the session database corrupts the
   migration tests.
7. **Verification is by rendering.** A change is not done until the running
   instance shows it.

## Out of scope

These are adjacent defects found during the review. They are recorded, not
planned, and each needs its own change:

- `nh3` strips `class` from `<code>` (no `code` entry in
  `MARKDOWN_ALLOWED_ATTRIBUTES`), so `pre[class*="language-"]` never matches and
  Prism never activates. The copy button in `app/static/js/public/code-copy.js`
  therefore never appears.
- `base.css`'s mobile `@media (max-width: 768px) .prose pre` rules are
  overridden by the later, equal-specificity `.prose pre` rules in `public.css`.
  Mobile code blocks keep the desktop font size and scroll horizontally.
- `.related-posts` and `.series-navigation` are siblings of `.post-full` and so
  sit outside the 760px measure. They are a card grid and a prev/next pair
  rather than running text, so they are not part of the comment-measure work
  in Phase 06. They need their own decision about the reading width.

## Closure

The roadmap closes when every phase file carries a `## Completion` section with
the verification evidence, and `plans/AGENTS.override.md` lists the series under
**Active Plans** → then **Historical Plans**.

Phases 01–05 carry their Completion sections. Phase 06 remains planned, so the
series stays open until the comment-measure work ships.

## Verification of Phases 01–05

All five phases were verified by rendering the running instance at
`http://localhost:5050` in headless Chromium, not by reading templates. The
combined harness is at `/tmp/devlog_review_stubs/identity_verify.py` (scratch
harness, not committed) and reported **29/29 checks passed** against the four
operator questions — can users log in, is there a page to edit their own
information, can the admin edit their display information, does it attach to
the posts they create — plus the page-menu requirement.

| Operator question | Resolution | Phase |
|---|---|---|
| Can users log in? | Yes. `/login` accepts a non-admin account; the nav shows Log in, and Account, Write and Log out once signed in. | 03 |
| Is there a page to edit their own info? | Yes. `/account` shows the profile and doubles as the editor for display name, short bio, full bio and avatar. | 02, 03 |
| Can the admin edit their display information? | Yes. `/admin/users` carries a Profile action per user, and `/admin/profile` edits the signed-in admin's own profile. | 02 |
| Does this attach to posts they create? | Yes. `Post.author_id` records the creator; the author is named and linked on the post, in the listing, in the JSON-LD and on `/author/<username>`. An author's own posts are forced to drafts — publishing stays an admin decision. | 04 |
| Pages should create links in the nav bar as well | Yes. Published pages appear in the nav through the Site section of the settings page, and in the footer's Pages column, with `/pages` as the full index. | 05 |
