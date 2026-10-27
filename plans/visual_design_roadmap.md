# Visual Design and Readability Roadmap

> **Plan status: ACTIVE — phases 01 and 02 shipped 2026-10-27.** Phases 03 to 06 are open. See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Date:** 2026-10-27
**Status:** In progress — phases 01 and 02 shipped, 4 phases open, 18 findings recorded
**Scope:** Public site rendering — markdown output, code blocks, text roles, prose measure, imagery, index and article furniture
**Origin:** an operator review of the running instance on 2026-10-27. Every finding was confirmed by rendering the application in Chromium and measuring computed styles, not by reading templates. The measurement tables are in the phase files.

## Problem statement

A visual review of the running instance, measured in Chromium in both colour schemes
at 390px, 768px and 1280px, found **18 findings**: 2 critical, 7 high, 7 medium and
2 low. Three of them compound into a single user-visible failure:

1. `app/markdown_config.py` permits the `class` attribute on `span` and `div` only.
   Python-Markdown's `fenced_code` extension puts `class="language-python"` on the
   `<code>` element of a fenced block, and `nh3.clean()` strips it.
2. Every consumer of that class is gated on it. `loadPrismIfNeeded()` in
   `app/static/js/main.js` and `initCodeCopy()` in
   `app/static/js/public/code-copy.js` both select `pre[class*="language-"]`.
3. The grammar bundle is not valid JavaScript. `app/static/js/prism-languages.js`
   has a missing parenthesis at line 16 and a malformed character class in the
   `yaml` grammar at line 23, so the whole file fails to parse and none of its
   twenty grammars ever register. `app/static/js/prism.min.js` is the Prism
   *core*, which carries no grammars of its own.

Net effect: **no code block on the site is ever syntax-highlighted, and no code
block ever gets a copy button.** The `syntax_theme` setting in
`SiteSettings` selects between six vendored Prism palettes and has no visible
effect at all. Measured on `/post/sample-post-12`: `window.Prism` is undefined,
the document contains zero `.token` elements, and both `<pre>` and `<code>`
render with an empty `class` attribute.

Each of the three is on its own sufficient to kill the feature, and each one
would have been invisible to the others. That is the shape of the failure, and
it is why the phase fixes all three rather than the first one it finds.

The next finding is systemic rather than local: **muted grey is doing content
work.** `--text-muted` styles 12.8px–14px content — table-of-contents entries,
share labels, post metadata, footer links, navigation links — and measures
**2.47:1** (TOC, share) and **2.91:1** (nav, footer, breadcrumb) against the
active dark theme's own surfaces. WCAG AA requires 4.5:1 for body-size text.

This is not one bad palette. Across the 50 bundled themes, `--text-muted` falls
below 4.5:1 against its own surface in **26 of 43 dark themes** and **6 of 7 light
themes**, and below 3.0:1 in 14 dark themes (worst: `vik` 1.92, `Nord` 1.96,
`Cyber Red` 2.13, `Oxocarbon` 2.18). The reason is a contract mismatch:
`scripts/theme_accessibility_report.py` classifies muted and dim text as
*advisory* "decorative" text at a 3.0:1 floor, while the stylesheets use those
same tokens for real content. The gate's model of the token and the
stylesheets' model of the token disagree, and neither is checked against the
other.

Two further failures are CSS defects rather than policy gaps:

- `[data-color-scheme="light"] .prose code` (specificity 0,2,1) outranks
  `.prose pre code` (0,1,2), so the inline-code chip background leaks onto every
  line inside a `<pre>` in the light scheme. Measured: `code` background
  `rgb(230,226,224)` inside a `pre` of `rgb(241,239,238)`.
- `.prose pre` paints `--bg-surface`, which in the active light theme equals the
  page background exactly, and in the active dark theme differs from the post
  tile's composited surface by one unit in the blue channel. In both schemes the
  block has no separation from its container.

## Why these survived

Each layer validates independently, so the seams are unguarded. This is the same
failure shape as the [Frontend Corrective series](frontend_corrective_roadmap.md),
which found the same class of defect in the image and lightbox pipelines.

| Seam | Failure mode | Guard today |
|---|---|---|
| Markdown → sanitiser | The sanitiser removes the one attribute a downstream consumer depends on | none |
| Sanitiser → JavaScript | Two independent modules select on a class that can never be present | none |
| JavaScript → JavaScript | The grammar bundle does not parse, and no build step checks it | none |
| JavaScript → stylesheet | A `Copy` button is created but styled only by one of six vendored palettes | none |
| Stylesheet → stylesheet | A scheme override at a higher specificity wins over the rule it meant to refine | none |
| Theme runtime → stylesheet | A token is classified as decorative by the gate and as content by the CSS | none |
| Theme catalogue → gate | The gate checks `text_muted` only against `surface_default`, never against `bg_page` | none |
| Template → stylesheet | A fixed pixel image height crops a 16:9 source to a 4:1 band | none |

The deeper cause of the first two rows is a general one: **a feature that no
input can reach is not shipped.** `initCodeCopy()` is correct, complete, and
unreachable. It reads like a working feature in the source tree and in every
code review, which is exactly why it survived.

## Operator decisions

Three decisions were taken on 2026-10-27 and are binding for this series.

1. **Code blocks are theme-aware.** Prism's token classes are remapped onto the
   active theme's own palette. The `syntax_theme` setting and the six vendored
   Prism palettes are retired. The theme runtime stays the single owner of
   colour, including inside code blocks.
2. **The share bar moves below the article.** It stays a full set of networks
   and keeps its current behaviour; only its position changes.
3. **The index sidebar's "Recent posts" block is dropped.** "Tags" stays, and
   the main column widens into the reclaimed space.

## Guiding principles

These extend the [Frontend Corrective principles](frontend_corrective_roadmap.md#guiding-principles).

1. **Fix contracts, not symptoms.** Each defect is a disagreement between two layers. Change the layer that owns the contract, and add a test that fails if the disagreement returns.
2. **One owner per value.** A URL is produced by the storage layer, an image URL by the filter, a heading id by exactly one module, colour by the theme runtime. Two producers for one value is the root cause of the anchor and heading-id defects.
3. **Prefer deletion over repair.** The six vendored Prism palettes are deleted, not maintained. A retired setting that keeps a column is a setting that will be re-implemented by the next agent who finds it.
4. **Verify by rendering.** Every defect in this roadmap was confirmed against a running instance, and every fix must be confirmed the same way — rendered HTML, computed styles, or a real interaction. A fix that is only asserted by inspection is not closed.
5. **Keep the cascade explicit.** The stylesheet that owns an element's base rule owns its breakpoint override, because a media query adds no specificity.
6. **Preserve the theme system.** The theme runtime owns colour. Static CSS consumes theme tokens, never literals, and never depends on a token the runtime does not emit.
7. **A rendered feature is not a shipped feature.** Any module that no input can reach must be proven reachable by a test, or deleted.
8. **Measure outcomes, not declarations.** "Raise the contrast" is not an acceptance criterion. "The TOC entry measures at least 4.5:1 against its own surface in every bundled theme" is.

## Phases

| Phase | Title | Findings | Severity band | Status |
|---|---|---|---|---|
| 01 | [Code blocks](visual_design_phase_01_code_blocks.md) | 7 | 2 critical, 4 high, 1 medium | Complete |
| 02 | [Text roles and the contrast floor](visual_design_phase_02_text_roles_and_contrast.md) | 4 | 4 high | Complete |
| 03 | [Prose measure](visual_design_phase_03_prose_measure.md) | 1 | 1 medium | Not started |
| 04 | [Imagery](visual_design_phase_04_imagery.md) | 2 | 2 medium | Not started |
| 05 | [Index layout](visual_design_phase_05_index_layout.md) | 2 | 1 medium, 1 low | Not started |
| 06 | [Article furniture](visual_design_phase_06_article_furniture.md) | 2 | 1 medium, 1 low | Not started |

The finding identifiers are `VD-01` through `VD-18` and are unique across the
series. Phase 01 owns `VD-01` to `VD-07`, phase 02 owns `VD-08` to `VD-11`,
phase 03 owns `VD-12`, phase 04 owns `VD-13` and `VD-14`, phase 05 owns `VD-15`
and `VD-16`, and phase 06 owns `VD-17` and `VD-18`.

Phase 02 repairs the eight themes that Phase 01's VD-07 identifies. The finding
is recorded once, in the phase that discovers it; the repair is owned by the
phase that owns the theme catalogue.

### Sequencing

Phase 01 is first and independent of everything else in the series. It restores
the feature a developer audience notices first, and it is the only phase that
retires a setting, so it carries the only migration.

Phase 02 must land before Phases 03 to 06. Every later phase introduces or
re-styles text at content size, and they must all use the caption token that
Phase 02 introduces. Introducing the token late would mean touching the same
stylesheet rules twice.

Phase 03 is independent of Phase 04 and Phase 05, but it edits
`app/static/css/base.css` at `.prose`, which Phase 01 also edits. It therefore
runs after Phase 01.

Phase 04 edits `app/static/css/public.css` at `.post-card-img`, which Phase 05
also edits. It runs before Phase 05.

Phase 06 is last. It restyles the share bar and the section furniture, both of
which Phase 02 changes the colour of.

### Cross-cutting constraints

- **One migration only.** Phase 01 drops the `syntax_theme` column from
  `site_settings`. It chains onto the current head,
  `add_appearance_settings_to_sitesettings`. Phases 02 to 06 need no migration.
- **The theme runtime is touched only in Phase 02**, and only to add one derived
  field. No token is renamed or removed. The `BlogTheme` field count, the
  `CSS_VARS` count and the `ALIASES` count all change in that phase; every
  document that states those counts must be updated in the same change.
- **No colour literals** are introduced into any stylesheet, with the single
  exception of the replacement placeholder SVG, which is an image asset and not
  a stylesheet.
- **`app/static/dist/` is a build artifact and is not committed.** `npm run build`
  must succeed in every phase that touches JavaScript or CSS, and the Flask
  server must be restarted after each build because `app/vite.py` caches the
  manifest process-wide.
- **The CSP in `app/__init__.py` is not weakened by any phase.** Phase 01 adds a
  `class` attribute to a `<pre>` and a `<code>` element in server-rendered
  markup; it does not relax the sanitiser for user-authored attributes.
- **Browser-level tests belong under `tests/e2e/`**, on the e2e application's own
  database. A live server thread on the session-scoped application shares its
  database with the migration tests and corrupts their DDL.

## Verification baseline

Every phase must pass the full gate before it is marked complete:

```bash
# Frontend
npm run build

# Backend / template correctness
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python3 -m pytest tests/
ruff check .
ruff format --check .
arch -arm64 python3 mypy app/ devlog_cli/
```

Phase-specific browser verification is specified per phase and is reproducible
with Playwright, which `tests/e2e/` already uses.

**Contrast is measured, never asserted by inspection.** A ratio is only accepted
when it is computed from composited rendered colours — the foreground over the
actual painted background, including any alpha — using the same method as
`app/themes/colors.py:contrast_ratio`. A ratio computed from two token values
in isolation is not a measurement of the page.

## Closure criteria

The roadmap is complete when:

- every finding in this roadmap is either fixed or explicitly deferred with a recorded rationale;
- the findings that are visible on every public page are covered by automated tests;
- `architecture/frontend/static-assets.md`, `architecture/frontend/overview.md` and `architecture/core/themes.md` reflect the corrected contracts;
- `app/static/AGENTS.override.md` records the code-block contract and the text-role rule;
- `AGENTS.md` reflects the new token counts and no longer describes the retired `syntax_theme` setting;
- the `theme-policy` CI job still passes with the tightened gate.

## Completion

**Status:** In progress. Phases 01 and 02 shipped on 2026-10-27; phases 03 to 06 are open.
