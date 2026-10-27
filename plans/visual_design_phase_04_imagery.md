# Visual Design Phase 04 — Imagery

> **Plan status: COMPLETE — shipped 2026-10-27.** The outcome is documented in
> [`architecture/frontend/static-assets.md`](../architecture/frontend/static-assets.md#the-post-placeholder).
> See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Roadmap:** [visual_design_roadmap.md](visual_design_roadmap.md)
**Date:** 2026-10-27
**Status:** Complete — shipped 2026-10-27
**Severity:** Medium — the post placeholder belongs to no theme, and the card image band crops a fifth off every source image.

## Objective

Make the placeholder belong to the theme, and stop the card from cropping the
top and the bottom off the images a technical blog is made of.

## Findings

### VD-13 — The post placeholder belongs to no theme (medium)

`app/static/img/default-post.svg` hard-codes the GitHub dark palette:

```svg
<rect width="1200" height="630" fill="#0d1117"/>
...
<path d="M 60 0 L 0 0 0 60" fill="none" stroke="#161b22" stroke-width="1"/>
...
<stop offset="0%" style="stop-color:#58a6ff;stop-opacity:0.15"/>
...
<text ... fill="#1c2128">{ }</text>
<text ... fill="#30363d">DevLog</text>
```

None of those five colours is related to any of the 50 bundled themes. The
active dark theme's page background is `#112028`; the placeholder's is `#0d1117`.

In the light scheme the placeholder is a dark rectangle sitting behind a light
`--bg-surface` gradient wash. The review screenshot shows it as a black band
across the top of the post.

The placeholder is used in five places: the post hero
(`app/templates/_post_content.html`), the index card
(`app/templates/index.html`), the search result card
(`app/templates/search.html`), the related-post thumbnail
(`app/templates/post.html`), and the social preview metadata
(`app/templates/base.html`, `app/templates/post.html`, `app/templates/page.html`).

### VD-14 — The card image band crops a fifth off every source image (medium)

`app/static/css/public.css`:

```css
.post-card-img {
    width: 100%;
    height: 200px;
    object-fit: cover;
    display: block;
}
```

At the 1280px viewport the card is 804px wide, so the band is **4:1** against a
source image that is usually 16:9. `object-fit: cover` scales the source to
cover the box and crops the overflow, which for a 16:9 source in a 4:1 box
removes roughly 25% of the height — the top and the bottom.

For a technical blog that is the wrong thing to crop. A terminal screenshot has
its prompt at the top and its output at the bottom; a graph has its axis labels
at the edges.

The placeholder is hit twice as hard. Its own artwork is 1200×630, which is
1.9:1, so forcing it into the 4:1 band crops its top and bottom as well, and
leaves the `{ }` mark floating in a large empty gutter.

## Fix specification

### 1. A placeholder with no palette of its own

The placeholder becomes a monochrome mark that takes its colour from the
element that displays it.

An SVG loaded through `<img>` cannot see the theme's `data-color-scheme`
attribute, but it **can** resolve `currentColor` against the `<img>` element's
own `color` property. That is the whole mechanism: the mark has no palette, and
the stylesheet supplies the colour.

- `app/static/img/default-post.svg` is replaced with a line-art mark on a
  transparent background. Every `fill` and `stroke` is `currentColor`, or
  `none`. The artwork is a small window-and-bracket motif that reads as "a post
  with no image" at card size and at hero size.
- The artwork is redrawn at 1200×675, which is 16:9, matching the card band this
  phase introduces.
- `app/static/css/public.css` sets the colour on the elements that display it:

  ```css
  .post-card-img,
  .post-hero-img,
  .related-card-img {
      color: var(--text-dim);
  }
  ```

  `--text-dim` is the decorative role Phase 02 keeps for decoration. The
  placeholder is decoration.

The mark must stay legible against both the page background and the tile
background. If the tile and the page differ in lightness, the mark is drawn on
the tile, so `--text-dim` against `surface_default` is the relevant pair, and
the theme gate already checks it at 3.0:1.

The social-preview metadata (`og:image`, `twitter:image`) must keep pointing at
a **real raster image**, because a social platform does not render an SVG and
`currentColor` has no meaning there. The placeholder SVG stays as the metadata
target, and the replacement SVG must therefore be legible against a dark
background on its own. The simplest resolution is to give the metadata target a
distinct, self-contained file — `app/static/img/default-post-social.png`, a
1200×630 PNG in the GitHub-dark palette that already reads correctly on any
social card — and leave the metadata pointing at that.

### 2. An aspect ratio instead of a fixed height

```css
.post-card-img {
    width: 100%;
    aspect-ratio: 16 / 9;
    height: auto;
    object-fit: cover;
    display: block;
}
```

`aspect-ratio` replaces the fixed `height: 200px`. The band is now 16:9 at
every width, so a 16:9 screenshot fills it without a crop.

The same treatment applies to the related-post thumbnail, which is currently a
fixed `400×120` band:

```css
.related-card-img {
    aspect-ratio: 16 / 9;
    height: auto;
}
```

The post hero is already 760×400, which is 1.9:1 — close to the placeholder's
own ratio and not a crop of anything, because a hero is a banner by
convention. It is **not** changed by this phase.

### 3. What this phase deliberately does not change

- **The post hero.** A hero is a banner. A 400px hero on a 760px tile is
  deliberate, and the mobile block already reduces it at 390px.
- **The storage layer.** Nothing here touches `post_image_url`,
  `post_image_srcset` or the upload pipeline. Those contracts were fixed by the
  Frontend Corrective series and are not reopened.
- **The `img-skeleton` class.** The lazy-loading contract — an image restores
  its opacity on load and on error — is unchanged.

## Tests

1. **The placeholder has no palette (unit)** — assert
   `app/static/img/default-post.svg` contains no hex colour literal and no
   `rgb(`/`hsl(` literal, and that every `fill` and `stroke` is `currentColor`
   or `none`.
2. **The placeholder is transparent (unit)** — assert the SVG has no `rect` with
   a background fill covering the viewport.
3. **The social target still exists (unit)** — assert the file the `og:image`
   metadata points at exists and is a raster image.
4. **The band is 16:9 (browser, `tests/e2e/`)** — assert the rendered
   `.post-card-img` box has a width-to-height ratio between 1.76 and 1.80.
5. **No crop (browser)** — render an index card whose post has a 16:9 image and
   assert the rendered image's natural ratio matches the box's ratio within
   2%, which proves `cover` is not cropping.
6. **The placeholder resolves (browser)** — assert that the computed `color` of
   a `.post-card-img` differs between the dark and the light scheme, proving the
   mark takes its colour from the theme rather than from the file.
7. **The placeholder is visible (browser)** — assert the rendered placeholder is
   not invisible in either scheme: it has a non-zero rendered box and its
   computed colour is not equal to its background.
8. **The hero is unchanged (browser)** — assert the post hero image's rendered
   height is unchanged at 1280px.

## Expected files

- `app/static/img/default-post.svg` (rewritten)
- `app/static/img/default-post-social.png` (new, for the social metadata)
- `app/static/css/public.css` (the aspect ratios and the placeholder colour)
- `app/templates/base.html`, `app/templates/post.html`, `app/templates/page.html`
  (the social metadata target)
- `tests/test_image_rendering.py` (the placeholder contract)
- `tests/e2e/test_card_imagery.py` (new)

## Acceptance criteria

- [ ] The placeholder contains no colour literal and takes its colour from the theme.
- [ ] The placeholder is legible in both schemes and in both the card and the hero.
- [ ] The social preview metadata points at a raster image that renders on a social card.
- [ ] The card image band is 16:9 at every viewport width.
- [ ] A 16:9 source image is not cropped by the card band.
- [ ] The related-post thumbnail is 16:9.
- [ ] The post hero's rendered height is unchanged.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Independent of Phases 01 to 03. Runs before Phase 05, which changes the width of
the card and therefore the height of its 16:9 band.

## Completion

**Status:** Complete. Shipped 2026-10-27.

### What changed

- `app/static/img/default-post.svg` — rewritten. A 1200×675 (16:9) line-art
  mark of a window and a pair of brackets, on a transparent background, with
  every `fill` and `stroke` either `currentColor` or `none` and no colour
  literal of any kind.
- `app/static/img/default-post-social.png` — new. A 1200×630 raster in the
  GitHub-dark palette carrying the same mark, for the social preview metadata
  and the newsletter cover.
- `app/static/css/public.css` — `.post-card-img` and `.related-card-img` now
  use `aspect-ratio: 16 / 9; height: auto` instead of a fixed height, the
  mobile `height: 160px` override is gone, and a new `.img-placeholder` rule
  applies the mark as a CSS mask with `background-color: var(--text-dim)`.
- `app/templates/index.html`, `tag.html`, `search.html`, `post.html` and
  `_post_content.html` — the placeholder is now a
  `<span class="… img-placeholder" role="img" aria-label="…">` rather than an
  `<img>`, and the real images carry `width="400" height="225"`.
- `app/templates/base.html`, `post.html`, `page.html` and
  `app/templates/email/newsletter.html` — the social preview and the newsletter
  cover point at `default-post-social.png`.
- `tests/test_image_rendering.py` — six new or updated tests: the mark has no
  palette, it is transparent, the social target is a PNG, the placeholder is
  themed by the stylesheet, the card renders the themed placeholder, and the
  social metadata defaults to the raster.
- `tests/test_css_contracts.py` — a `TestImageBands` class: the bands declare
  a 16:9 ratio, no breakpoint reintroduces a fixed height, and the placeholder
  takes its ink from the theme.
- `tests/e2e/test_card_imagery.py` — 12 browser tests: the band is 16:9 at
  1280px, 768px and 390px, a 16:9 source is not cropped, the placeholder is
  masked and coloured by the theme, the colour differs between the two
  schemes, the placeholder is visible against its tile, the hero height is
  unchanged, and the related thumbnail is 16:9.
- `architecture/frontend/static-assets.md`, `architecture/frontend/templates.md`,
  `app/static/AGENTS.override.md`, `app/routes/AGENTS.override.md` and
  `AGENTS.md` record the placeholder contract and the bands.

### Deviations from the plan

1. **The plan's colour mechanism does not work in a browser.** The plan states
   that an SVG loaded through `<img>` "can resolve `currentColor` against the
   `<img>` element's own `color` property". It cannot. An SVG loaded as an
   image is an isolated document with no access to the host page's cascade, and
   `currentColor` inside it resolves against the SVG document's own root
   element. Measured in Chromium: a page whose `<img>` sets `color: rgb(255, 0,
   0)` and whose SVG fills with `currentColor` renders **black**, both read
   back through a canvas and sampled from a screenshot. Under the plan's
   mechanism the placeholder would have rendered black in every theme.

   The mark is therefore applied as a **CSS mask**, which is the mechanism the
   page backdrops already use: `public.css` sets `mask-image:
   url("../img/default-post.svg")` on `.img-placeholder` and paints the
   element's background with `var(--text-dim)`. Only the mark's alpha is read
   and the ink comes from the theme.

   The consequence is that the placeholder is not an `<img>`. The colour of an
   `<img>`'s content cannot be changed by CSS, so the element is a `<span
   role="img" aria-label="…">`, which reproduces what `alt` gave the old image.
   The plan's `color: var(--text-dim)` on `.post-card-img`, `.post-hero-img` and
   `.related-card-img` becomes `background-color` on the placeholder element
   only; the real images are unaffected.

2. **The mobile `height: 160px` override on `.post-card-img` was removed.** The
   plan does not list it, but the acceptance criterion is that the band is
   16:9 "at every viewport width", and a fixed height at the breakpoint would
   have broken the ratio on the phone.

3. **The newsletter cover points at the raster as well.** The plan mentions
   only the social metadata, but the newsletter template used the same SVG, and
   most mail clients block SVG — the cover was already broken there.

4. **The lightbox's fallback `src` points at the raster.** The lightbox shows
   raster images; its placeholder `src` is replaced the moment it opens, but it
   should not be the mask asset.

5. **The social raster renders the new mark, not a copy of the old artwork.**
   The plan asks for "a 1200×630 PNG in the GitHub-dark palette"; it does not
   say which artwork. Using the new mark keeps the social card and the on-page
   placeholder the same picture, and the old `{ }` artwork was invisible on its
   own background in the first place (`#1c2128` on `#0d1117` is 1.2:1).

6. **`tests/test_frontend_contracts.py` was updated.** It asserted the old
   social default and would otherwise have failed.

### Verification

Measured in Chromium against the running instance, in the dark and the light
scheme:

| Property | Before | After |
|---|---|---|
| Placeholder ink, dark scheme | `#0d1117` — the asset's own opaque fill | `rgb(40, 104, 134)`, the theme's `--text-dim` |
| Placeholder ink, light scheme | `#0d1117` — a black band on a light tile | `rgb(104, 97, 94)`, the theme's `--text-dim` |
| Card band at 1280px | `height: 200px` on an 804px card — 4:1 | 802×451, ratio 1.778 |
| Card band at ≤768px | `height: 160px` — a fixed band that is not 16:9 | 16:9 at 768px and at 390px |
| Hero at 1280px | 758×400 | 758×400, unchanged |

- The placeholder's ink differs between the dark and the light scheme, which
  is the observable consequence of the theme supplying it.
- A 16:9 source image in a 16:9 band: the rendered box ratio and the source's
  natural ratio agree within 2%, so `object-fit: cover` does not crop it.
- `pytest tests/e2e/test_card_imagery.py` — 12 passed.
- `pytest tests/test_image_rendering.py tests/test_css_contracts.py` — passed.
- `ruff check .` and `ruff format --check .` — clean.
- Full-suite comparison against the pre-phase baseline: no new failures.

