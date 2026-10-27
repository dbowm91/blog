# Visual Design Phase 04 — Imagery

> **Plan status: ACTIVE — not started.** Nothing in this plan has shipped. See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Roadmap:** [visual_design_roadmap.md](visual_design_roadmap.md)
**Date:** 2026-10-27
**Status:** Not started
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

**Status:** Not started.
