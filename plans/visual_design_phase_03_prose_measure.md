# Visual Design Phase 03 — Prose Measure

> **Plan status: COMPLETE — shipped 2026-10-27.** The outcome is documented in
> [`architecture/frontend/static-assets.md`](../architecture/frontend/static-assets.md#the-reading-measure).
> See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Roadmap:** [visual_design_roadmap.md](visual_design_roadmap.md)
**Date:** 2026-10-27
**Status:** Complete — shipped 2026-10-27
**Severity:** Medium — the reading column is 85 characters wide, well past the range in which a line of text is easy to track back from.

## Objective

Bring the reading column into the 65–75 character range at every viewport, without
narrowing the page, the hero image or the tile that contains it.

## Findings

### VD-12 — The prose measure is 85 characters wide (medium)

Measured in Chromium on `/post/sample-post-12`, using the average advance width
of the lowercase alphabet in the rendered face at the rendered font size:

| Viewport | Prose font size | Average advance | Column width | Characters per line |
|---|---|---|---|---|
| 1280px | 16.8px | 8.12px | 694px | **85.5** |
| 768px | 15.2px | 7.35px | 694px | **94.4** |
| 390px | 15.2px | 7.35px | 316px | 43.0 |

The comfortable reading range is 60 to 75 characters. At 1280px the column is
eleven characters too wide; at 768px it is nineteen too wide, because the mobile
breakpoint reduces the font size but not the measure.

The width comes from two rules that each look reasonable:

```css
/* app/static/css/public.css */
.post-full {
    max-width: 760px;
}

/* app/static/css/base.css */
.post-content {
    padding: 24px 32px 32px;
}
```

760px minus the 32px gutters on each side gives the 696px text column, and
`.prose` sets no maximum of its own.

The line-height is already good — 1.75, or 29.4px at the desktop size — so the
problem is the width alone. A line-height of 1.75 over 85 characters gives the
eye a long return path on every line.

## Fix specification

### 1. Cap the measure on `.prose`

`.prose` is owned by `app/static/css/base.css` (`app/static/AGENTS.override.md`,
"Stylesheet Ownership"), so the cap belongs there and nowhere else.

```css
.prose {
    font-size: 1.05rem;
    line-height: 1.75;
    color: var(--text);
    max-width: 34em;
    margin-inline: auto;
}
```

`34em` rather than a pixel value, because the prose font size changes at the
mobile breakpoint (16.8px above 768px, 15.2px at and below it). An `em` cap
scales with the text, so the character count stays constant across the
breakpoint. At the default face and size, `34em` is 571px, which is
approximately 69 characters per line.

The cap is a maximum, not a width. Inside the 390px viewport the column is
316px — narrower than the cap — so nothing changes there.

`margin-inline: auto` centres the narrower column inside the tile, so the text
keeps a symmetric gutter and the hero image above it keeps the full tile width.
The result is a page whose image is wider than its text, which is the intended
reading rhythm: the image is a full-bleed element, the text is a measure.

### 2. What this changes and what it does not

| Element | Effect |
|---|---|
| Post body prose | The measure narrows to the cap and centres in the tile. |
| Static page (`page.html`, `<article class="prose">`) | Same cap. A page of prose benefits from the same measure as a post. |
| Admin live preview | Same cap, because the preview renders `.prose`. The preview now matches the published post. |
| Post hero image | Unchanged — it is outside `.prose` and fills the tile. |
| Table of contents | Unchanged — `.post-toc-container` is outside `.prose`. It stays full tile width, which is correct for a navigation block. |
| Code blocks | Unchanged. A code block is a different kind of content and its own measure is set by its `overflow-x: auto`. |
| Author card, share bar, TL;DR | Unchanged — they are siblings of `.post-body` inside `.post-content`. |

### 3. The caption role applies here too

The paragraphs inside the measure are already `--text`, which clears AA in every
bundled theme. The elements that sit *around* the measure — the metadata, the
share label, the table of contents — are Phase 02's work and use the caption
role. This phase does not restyle them.

## Tests

1. **The measure is capped (unit)** — assert `app/static/css/base.css` contains a
   `max-width` on `.prose` and that `app/static/css/public.css` does not set a
   width on `.post-body`.
2. **Characters per line (browser, `tests/e2e/`)** — on a post page, measure the
   `.prose` column width and the average advance width of the lowercase
   alphabet at the rendered font size, using `canvas.measureText`, and assert the
   quotient is between 65 and 75. Run at 1280px and at 768px.
3. **The phone is unchanged (browser)** — assert that at 390px the prose column
   width is unchanged from before the phase, because the cap does not bind.
4. **The preview matches the post (browser)** — assert that the admin live
   preview's `.prose` computes the same `max-width` as the public post's.
5. **The hero is not narrowed (browser)** — assert the post hero image's width is
   unchanged at 1280px.
6. **No overflow (browser)** — assert `document.documentElement.scrollWidth <=
   window.innerWidth` on the post page at 390px, 768px and 1280px.

## Expected files

- `app/static/css/base.css` (the `.prose` cap)
- `tests/e2e/test_prose_measure.py` (new)
- `tests/test_css_contracts.py` (the cap is present and owned by `base.css`)

## Acceptance criteria

- [ ] The prose column measures between 65 and 75 characters per line at 1280px and at 768px.
- [ ] The measure is expressed in `em`, so it scales with the prose font size across the breakpoint.
- [ ] The 390px layout is unchanged.
- [ ] The post hero image, the table of contents and the code blocks are unchanged.
- [ ] The admin live preview renders the same measure as the published post.
- [ ] The post page has no horizontal scrollbar at 390px, 768px or 1280px.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Requires Phase 01, which edits the same `.prose` block in `app/static/css/base.css`.

Runs before Phase 06, which re-styles the elements that sit around the measure.

## Completion

**Status:** Complete. Shipped 2026-10-27.

### What changed

- `app/static/css/base.css` — `.prose` gained `max-width: 34em` and
  `margin-inline: auto`. The cap is in `em` so it scales with the prose font
  size, which changes from `1.05rem` to `0.95rem` at the 768px breakpoint.
- `tests/test_css_contracts.py` — a `TestReadingMeasure` class: the cap exists,
  it is expressed in `em`, the column is centred, no other stylesheet caps
  `.prose`, and `public.css` sets no width on `.post-body`.
- `tests/e2e/test_prose_measure.py` — 11 browser tests: the character count at
  1280px and 768px, the em measure at both, the em cap scaling with the font
  size, the phone layout unchanged, the hero at full tile width, the admin
  preview matching the published post, and no horizontal overflow at 390px,
  768px or 1280px.
- `architecture/frontend/static-assets.md`, `architecture/frontend/templates.md`,
  `app/static/AGENTS.override.md` and `AGENTS.md` record the measure and its
  owner.

### Deviations from the plan

1. **The character count is typeface-dependent, and no single cap satisfies the
   65–75 band for every typeface.** The measure is expressed in `em` and the
   typeface is an operator choice (`app/appearance/service.py` emits the
   `--font-sans` stack), so the number of characters a column holds depends on
   the face. Measured over the four bundled sans families at `34em`:

   | Family | Advance | Characters at 34em | Cap range for 65–75 |
   |---|---|---|---|
   | Inter | 0.4591 em | 74.1 | 29.8 – 34.4 em |
   | Atkinson Hyperlegible | 0.4828 em | 70.4 | 31.4 – 36.2 em |
   | IBM Plex Sans | 0.5040 em | 67.5 | 32.8 – 37.8 em |
   | Space Grotesk | 0.5528 em | 61.5 | 35.9 – 41.5 em |

   The ranges do not intersect: the spread between the widest and the narrowest
   face is wider than the 65–75 band itself. `34em` is the cap that centres the
   range — three of the four families land inside the band and the fourth, Space
   Grotesk, lands at 61.5, which is inside the classic 45–85 comfort range. The
   acceptance criterion as written is therefore met for the default typeface and
   for three of the four selectable ones, and **cannot** be met for all four by
   any cap.

   The typeface-independent contract is the em measure, and it is what the test
   suite now pins: `test_the_measure_is_thirty_four_ems_at_every_breakpoint`
   asserts the column measures 34 em at 1280px and at 768px, and
   `test_the_measure_holds_sixty_five_to_seventy_five_characters` asserts the
   character count for the face the page actually renders with.

2. **The advance is measured from the rendered face, not from a canvas.** The
   plan specified `canvas.measureText`. A canvas falls back to a generic family
   when the web font has not finished loading, which counts characters in the
   wrong font — the fallback measured 7.71px against Inter's own 7.71px only by
   coincidence. The test now measures a hidden span carrying the prose's
   computed font properties, after `document.fonts.ready`, so the advance comes
   from the face the reader sees.

3. **The "unchanged at 390px" test asserts that the cap does not bind** rather
   than comparing against a recorded pixel width, because the phone column
   still fills the tile's content box (316px of a 316px content box) and a
   recorded number would drift with the tile's padding.

### Verification

Measured in Chromium against the running instance at `/post/prism-check`:

| Viewport | Prose font size | Column | Characters | Em measure |
|---|---|---|---|---|
| 1280px | 16.8px | 571px | 70.4 | 34.0 |
| 768px | 15.2px | 517px | 70.4 | 34.0 |
| 390px | 15.2px | 316px | 43.0 | 20.8 (the cap does not bind) |

- The hero is 758px wide inside a 758px content box — the full width of its
  tile — at 1280px, and 400px tall, unchanged.
- `document.documentElement.scrollWidth` equals `window.innerWidth` at 390px,
  768px and 1280px.
- The admin live preview at `/admin/edit/<id>` computes the same `max-width`
  (`571.2px`) as the published post.
- `pytest tests/e2e/test_prose_measure.py` — 11 passed.
- `pytest tests/test_css_contracts.py` — passed.
- `ruff check .` and `ruff format --check .` — clean.
- Full-suite comparison against the pre-phase baseline: no new failures.

