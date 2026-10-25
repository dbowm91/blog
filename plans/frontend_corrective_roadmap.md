# Frontend Corrective Roadmap

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/frontend/overview.md](../architecture/frontend/overview.md); this file is the historical record.

**Date:** 2026-10-23
**Status:** Complete — all 5 phases closed, all 50 findings resolved
**Scope:** Public + admin frontend (templates, CSS, JS, Vite build pipeline)

## Problem statement

A frontend review of the public site, admin dashboard, stylesheet layer, and JavaScript module layer found **50 findings**: 5 critical, 12 high, 25 medium, and 8 low. The failures are not cosmetic: several are broken contract seams between layers that each look correct in isolation.

The three most damaging findings compound into a single user-visible failure:

1. `post_image_url` returns a **URL** (`/static/uploads/<file>`), but every template re-wraps it with `url_for('static', filename='uploads/' + img)` — producing `/static/uploads//static/uploads/<file>`, which 404s.
2. `post_image_srcset` returns `None` when no responsive variants exist, and Jinja renders that as the literal string `srcset="None"`, which the browser parses as a valid 1× candidate.
3. `.js img[loading="lazy"] { opacity: 0 }` is restored only by a `.loaded` class that `lazy-load.js` can never add, because it returns early on browsers with native lazy-loading support.

Net effect: **no post image renders anywhere on the site.** Post cards, post hero images, related-post thumbnails, author avatars, and social preview images are all broken or invisible. The same failures exist in the admin post editor's cover-image preview.

Two further critical findings are independent feature failures:

- The image **lightbox never opens** — the template ships `class="lightbox hidden"`, the JavaScript only adds `open`, and the CSS enforces `.lightbox.hidden { display: none !important }`. The page scroll is still locked while the invisible dialog is nominally open.
- **Media uploads always fail** with "No file selected." — the upload form contains a hidden empty `name="file"` input that shadows the real file in the multipart body.

## Why these survived

Each layer validates independently, so the seams are unguarded:

| Seam | Failure mode | Guard today |
|---|---|---|
| Filter → template | URL re-wrapped as a filename | none |
| Template → CSS | class names/attributes that do not exist in the stylesheet | none |
| Template → JS | `hidden` class, `data-auto-submit`, `preview-visible`, `X-CSRFToken` | none |
| CSS → CSS | equal-specificity rules resolved by document order, not intent | none |
| Vite → Flask | entry CSS emitted into the manifest but never linked | none |
| Theme runtime → CSS | tokens referenced but never emitted | none |

## Guiding principles

1. **Fix contracts, not symptoms.** Each defect is a disagreement between two layers. Change the layer that owns the contract, and add a test that fails if the disagreement returns.
2. **One owner per value.** A URL is produced by the storage layer, an image URL is produced by the filter, a heading id is produced by exactly one module. Two producers for one value is the root cause of the anchor and heading-id defects.
3. **Prefer deletion over repair.** Dead code, duplicated widgets, and orphaned build artifacts cause drift (the `mobile-menu.js` / `mobile-menu.jsx` pair). Remove rather than maintain.
4. **Verify by rendering.** Every defect in this roadmap was confirmed against a running instance, and every fix must be confirmed the same way — rendered HTML, computed styles, or a real interaction. A fix that is only asserted by inspection is not closed.
5. **Keep the cascade explicit.** Stylesheet load order currently decides behavior. Rules that must win must either be scoped so they cannot tie, or be moved next to the rules they override.
6. **Preserve the theme system.** The Halloy theme system owns colour. Static CSS must consume theme tokens, not literal colours, and must not depend on tokens the theme runtime does not emit.

## Phases

| Phase | Title | Findings | Severity band | Status |
|---|---|---|---|---|
| 01 | [Image rendering pipeline](frontend_corrective_phase_01_image_pipeline.md) | 4 | 2 critical, 2 high | Complete |
| 02 | [Public interaction and build contracts](frontend_corrective_phase_02_public_interaction_and_build.md) | 13 | 1 critical, 3 high, 8 medium, 1 low | Complete |
| 03 | [Admin form and control contracts](frontend_corrective_phase_03_admin_form_contracts.md) | 14 | 1 critical, 4 high, 8 medium, 1 low | Complete |
| 04 | [CSS cascade, theme tokens, and contrast](frontend_corrective_phase_04_css_cascade_and_theme_tokens.md) | 9 | 3 high, 4 medium, 2 low | Complete |
| 05 | [Accessibility, SEO, and markup semantics](frontend_corrective_phase_05_accessibility_and_seo.md) | 10 | 1 critical, 5 medium, 4 low | Complete |

### Sequencing

Phase 01 is first and independent: it is the only phase whose defects are visible on every public page, and none of its fixes depend on the other phases.

Phases 02 and 03 are independent of each other and of Phase 01, but must both be complete before Phase 04, because Phase 04 changes CSS that several Phase 02/03 fixes depend on (the lightbox `hidden` contract, the editor `preview-visible` contract).

Phase 04 must land before Phase 05, since Phase 05's contrast and focus-visibility work is defined against the corrected cascade.

### Cross-cutting constraints

- No database migrations are required by any phase.
- The theme system (`app/themes/`) is touched only in Phase 04, and only to add missing token aliases — no token is renamed or removed.
- `app/static/dist/` is a build artifact and is not committed; `npm run build` must succeed in every phase that touches JS or CSS.
- The CSP in `app/__init__.py` is not weakened by any phase. Two phases (02, 03) *reduce* XSS exposure by removing `innerHTML` sinks and adding sanitisation to the client-side preview.

## Verification baseline

Every phase must pass the full gate before it is marked complete:

```bash
# Frontend
npm run build
npm run preview            # manual visual confirmation of changed surfaces

# Backend / template correctness
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/
ruff check .
ruff format --check .
mypy app/ devlog_cli/
```

Phase-specific browser verification is specified per phase. Because the headless test environment cannot rely on a system browser, the browser checks in this roadmap are written to be reproducible with either Playwright (already used by `tests/e2e/`) or `chrome --headless --screenshot`.

## Closure criteria

The roadmap is complete when:

- every finding in this roadmap is either fixed or explicitly deferred with a recorded rationale;
- the five critical findings are covered by automated tests;
- `architecture/frontend/overview.md` and `architecture/frontend/static-assets.md` reflect the corrected contracts;
- `app/static/AGENTS.override.md` records the contracts that were previously implicit (image URL ownership, lazy-image class contract, lightbox visibility class, CSRF header name, route→module mapping rules);
- `docs/internals/agent-maintainer-notes.md` records the verification technique used for the visual defects, so the next reviewer can reproduce it.

## Closure

**Status: Complete** — all 50 findings resolved across the five phases. No finding
was deferred.

### What shipped

| Area | Outcome |
|---|---|
| Images | Every post image renders. The URL double-prefix is gone across all templates (including the newsletter email, which had the same defect), `srcset` is guarded, and lazy images restore their visibility on both success and failure. |
| Lightbox | The dialog opens, closes, restores page scroll, and no longer requests the document URL as an image. |
| Media upload | The upload succeeds — one file input, and the multipart body is built explicitly in JavaScript. |
| Admin preview | The live preview goes through the server-sanitised path; the client is no weaker than the server, and the reflected theme error is rendered as text. |
| Public interaction | Heading IDs come from one module, the copy link is a valid URL, the route→module mapping matches on segment boundaries, and the colour-scheme control honours the configured default and is reachable on a phone. |
| Admin controls | `data-loading` works, the preview toggle reveals the preview in both editors, the analytics and audit filters use distinct hooks, the series reorder form submits, the Remove action confirms, and every admin page has a distinct title. |
| CSS cascade | The mobile navigation collapses and expands; exactly one stylesheet owns `.nav-links` per breakpoint; the print stylesheet drops the chrome; the search field is fluid; the anchor baseline is global. |
| Theme tokens | `--shadow-color` and `--code-bg` are emitted for every theme, so eight elevation shadows and light-mode inline code resolve instead of silently falling back. |
| Contrast | The post title went from 1.12:1 to 13.1:1 (dark) and 6.9:1 (light); the lightbox caption is now guaranteed AA across all 50 bundled themes. |
| Accessibility | The series navigation is live instead of dead markup pointing at a non-existent endpoint; every input has an associated label; social metadata has defaults; the sidebar and footer have distinct accessible names; heading order no longer skips. |
| Build | `main.js` imports no stylesheet, so the dev server and production share one cascade and no orphaned CSS asset is emitted. The shared utility module is no longer bundled into the admin chunk. |

### Verification

- **New automated tests: 125** across `tests/test_image_rendering.py` (7),
  `tests/test_admin_contracts.py` (32), `tests/test_frontend_contracts.py` (42),
  `tests/test_css_contracts.py` (29), `tests/themes/test_text_on_background_contrast.py` (10),
  `tests/e2e/test_image_visibility.py` (2), and `tests/e2e/test_frontend_interactions.py` (3).
- **`tests/e2e/` — 55 passed, 0 failed.** The suite was previously unrunnable in this
  environment: the `BaseWSGIServer` constructor had changed in Werkzeug 3.x.
- **Browser verification — 17/17 checks** against a running instance: the lightbox
  opens and restores scroll, heading IDs are unique and the table of contents
  resolves, the post title uses the text token, images paint at `opacity: 1`, no
  URL is double-prefixed, the anchor baseline holds, elevation shadows resolve, the
  mobile navigation collapses and expands, the colour-scheme control is reachable
  at 375px, the search field fits the viewport, and no page errors were raised.
- **No regressions:** the full suite matches the pre-change baseline failure set
  exactly, `ruff check` is clean, `ruff format --check` reports only the
  pre-existing `devlog_cli/commands/doctor.py`, and `mypy app/ devlog_cli/` reports
  the same 17 pre-existing errors in the same 7 files.

### Defects found during implementation

Four defects were not in the original 50:

1. **`app/templates/email/newsletter.html` had the same image double-prefix** as the
   public templates — the newsletter's cover image never loaded.
2. **`mobile-menu.jsx` detached the click target when swapping its icon**, so the
   document-level handler immediately closed the menu again. The CSS fix alone left
   the hamburger inert; the mobile navigation needed a JavaScript fix as well.
3. **`.lightbox-caption` painted `--text-on-accent` on a dark scrim**, making the
   caption black-on-black in the dark theme. There is no "text on a scrim" token, so
   the alternatives were measured across all 50 themes before choosing one.
4. **The new browser tests broke the migration round-trip tests.** A Playwright
   test that started a live server thread on the session-scoped application also
   put a live connection on the shared session database; the migration tests
   later run DDL against that same database, and SQLite's batch table rebuild
   then reflected a stale schema and failed with `duplicate column name:
   theme_preset`. The three browser tests were moved to
   `tests/e2e/test_frontend_interactions.py`, where they run against the e2e
   application's own database and the two suites no longer share one.
