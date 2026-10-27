# Visual Design Phase 03 — Prose Measure

> **Plan status: ACTIVE — not started.** Nothing in this plan has shipped. See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Roadmap:** [visual_design_roadmap.md](visual_design_roadmap.md)
**Date:** 2026-10-27
**Status:** Not started
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

**Status:** Not started.
