# Static Assets (`app/static/`)

Frontend JavaScript and CSS assets.

## Directory Structure

```
app/static/
├── js/
│   ├── admin/          # Admin dashboard JS
│   │   ├── bulk.js
│   │   ├── editor-history.js
│   │   ├── editor.js
│   │   ├── markdown-toolbar.js
│   │   └── shortcuts.js
│   ├── public/         # Public site JS
│   │   ├── anchor-links.js
│   │   ├── code-copy.js
│   │   ├── lightbox.js
│   │   ├── media-copy.js
│   │   ├── search.js
│   │   ├── share.js
│   │   └── toc.js
│   ├── shared/         # Shared components
│   │   ├── dark-mode.js
│   │   ├── filter-select.js
│   │   ├── lazy-load.js
│   │   ├── mobile-menu.jsx  # JSX file (Vite handles via esbuildOptions)
│   │   ├── modal.js
│   │   ├── nav-dropdown.js
│   │   ├── prefetch.js
│   │   ├── prism-blocks.js  # Restores per-line structure after Prism highlighting
│   │   ├── toast.js
│   │   └── utils.js
│   ├── lib/            # Third-party libraries
│   │   ├── marked-wrapper.js
│   │   └── marked.min.js
│   ├── prism.js        # Second Vite entry: Prism core + 18 grammars
│   ├── image-preview.js
│   ├── main.js         # Entry point with route-based code splitting
│   └── upload.js
├── css/                # CSS files
├── fonts/              # Web fonts (woff2)
├── img/                # Static images (favicon, default-post, default-post-social, backdrops/)
├── uploads/            # User-uploaded media (local fallback; production may use S3)
└── dist/               # Vite build output
```

## JavaScript

### Module Initialization Pattern

JavaScript modules must export a default initialization function named `initXxx` (e.g., `export default initDarkMode`). The module loader in `main.js` calls `module.default()` if it exists:

```javascript
// Correct - default export named initXxx
export default function initMyModule() { ... }

// Incorrect - named export without default
export function setup() { ... }
```

### Route-Based Code Splitting

Code splitting is implemented in `main.js` using `import.meta.glob()`. Modules are loaded dynamically based on the current route:

```javascript
const ROUTE_MODULES = {
    '/admin/new': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
        './image-preview.js',
    ],
    '/admin/edit': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
        './image-preview.js',
    ],
    '/admin/pages/new': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
    ],
    '/admin/pages/edit': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
    ],
    '/admin/media': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './upload.js',
        './image-preview.js',
    ],
    '/admin/': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
    ],
};

function getModulesForPath(path) {
    // Returns route-specific modules or default public modules.
    // Matching is on a path-segment boundary, preferring the longest route:
    //   path === route || path.startsWith(route + '/')
    // Plain startsWith is not sufficient — '/admin/new' is a literal prefix
    // of '/admin/newsletter/preview'.
}
```

This allows Vite to create optimized chunks that are only loaded when needed.

### Lazy Image Loading

The progressive image loading pattern in `app/static/css/public.css` is:
- Default: `opacity: 0` on `img[loading="lazy"]` (requires `.js` class on `<html>`)
- `.loaded` class: `opacity: 1` with 0.4s ease transition
- JavaScript adds `document.documentElement.classList.add('js')` first to enable progressive enhancement

#### Image Skeleton Shimmer

`.img-skeleton` class provides a loading placeholder animation:
- Background: `linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-elevated) 50%, var(--bg-surface) 75%)` with `background-size: 200% 100%`
- Animation: `shimmer` keyframe moves background position from `200%` to `-200%` over 1.5s (infinite loop)
- When `.loaded` is added: animation stops, background clears

#### JavaScript Fallback Behavior

The `lazy-load.js` module attaches the `load` and `error` listeners **before** the
native-support early return, so the `.loaded` class is applied on every browser:

1. **Class contract (always)**: every `img[loading="lazy"]` gets a `load` listener
   that adds `.loaded`, and an `error` listener that also adds it — a broken image
   must not be left at `opacity: 0` forever. An image that is already complete is
   marked immediately.
2. **Native lazy loading**: If `'loading' in HTMLImageElement.prototype`, the
   browser handles the deferred fetching and the module stops there.
3. **IntersectionObserver polyfill**: If native is not supported but
   IntersectionObserver exists, observe images with `rootMargin: '200px 0px'` and
   swap `dataset.src` into `src` when intersecting.
4. **Immediate load fallback**: If no IntersectionObserver support, load all
   `loading="lazy"]` images immediately by copying `dataset.src` to `src`.

Step 1 is what makes the `opacity: 0` rule safe. Any new rule that hides an element
must have an equivalent guaranteed restoration path.

### Admin Body Class Detection

Admin pages can be detected via `document.body.classList.contains('admin-body')`.

### marked.min.js Loading Pattern

`marked.min.js` is loaded through Vite's asset pipeline via `vite_asset()` in both `base.html` and `admin/base.html`, receiving content hashing and CDN support like other JS assets:

```html
<script src="{{ vite_asset('js/lib/marked.min.js') }}"></script>
```

The adapter layer `marked-wrapper.js` is also loaded via `vite_asset()`.

### JSX Support

JSX files (like `mobile-menu.jsx`) are handled via Vite's esbuild options in `vite.config.js`:

```javascript
optimizeDeps: {
    esbuildOptions: {
        loader: {
            '.js': 'js',
            '.jsx': 'jsx',
            '.svg': 'text',
        },
        target: ['chrome100', 'edge100', 'firefox100', 'safari15'],
    },
}
```

### Admin JS
- Dashboard analytics and charts
- Post editor enhancements
- Markdown formatting toolbar (`markdown-toolbar.js`) — inserts markdown at the caret; loaded through `editor.js`
- Editor undo/redo history (`editor-history.js`) — loaded through `editor.js`
- Media upload management
- Settings and theme forms
- Bulk operations

### Public JS
- Anchor link handling (`anchor-links.js`)
- Code block copy buttons (`code-copy.js`)
- Image lightbox (`lightbox.js`)
- Search functionality (`search.js`)
- Social share buttons (`share.js`)
- Table of contents generation (`toc.js`)

`media-copy.js` lives under `public/` but belongs to the admin media library — it is
loaded only for the `/admin/media` route.

## CSS

Stylesheets in `app/static/css/`:
- `base.css` — Base styles
- `layout.css` — Page layout
- `public.css` — Public site styles
- `forms.css` — Form styles
- `utilities.css` — Utility classes
- `critical.css` — Above-the-fold CSS for fast initial paint
- `admin.css` — Admin dashboard styles
- `prism.css` — Prism token colours, mapped onto the theme tokens

`prism.css` contains only `.token.*` colour rules and no colour literal of any
kind: every Prism token resolves to a theme token, so the syntax colours follow
the selected theme. `base.css` owns the code block's own layout and the copy
button.

### Cascade Ownership

The stylesheets are linked in DOM order: `critical.css` → `base.css` →
`layout.css` → `public.css` → `forms.css` → `utilities.css` → `prism.css`. At
equal specificity the later stylesheet wins, so **exactly one stylesheet may own
an element's visibility at a given breakpoint**.

`.nav-links` is the worked example: `base.css` hid it below 769px while
`layout.css` set `display: flex` unconditionally. Both declarations had equal
specificity, so document order decided the outcome and the mobile navigation could
never collapse. `layout.css` now scopes its rule to `@media (min-width: 769px)`.

The same defect has a second form, and it is the more common one. **A media query
adds no specificity.** A `@media (max-width: 768px)` rule in `base.css` therefore
ties with the unconditional rule for the same element in `layout.css` or
`public.css`, and loses on document order — the breakpoint silently has no effect.
`base.css` carried the whole mobile breakpoint for the public site while every
rule it touched was declared again, unconditionally, further down `layout.css` or
`public.css`; the phone layout inherited the desktop one.

The rule that follows from this: **the stylesheet that owns an element's base rule
also owns that element's breakpoint override.**

| Sheet | Owns |
|---|---|
| `base.css` | tokens, reset, `.prose`, `.btn`, `.theme-toggle`, `.back-to-top`, `.reading-progress`, `.mobile-menu-toggle` |
| `layout.css` | `.container`, `.content-layout`, `.sidebar`, `.sidebar-title`, the navbar and `.nav-links` |
| `public.css` | `.hero`, `.posts-list`, `.post-card`, `.post-full`, `.post-hero`, `.post-toc`, `.share-bar`, `.tldr`, `.tag`, `.tag-more`, `.post-footer-tags`, `.author-card`, `.related-*`, `.archive-*`, `.search-form` |
| `forms.css` | the form controls, including their iOS-zoom font sizes |
| `admin.css` | the admin surfaces, including `.post-list-*` and `.editor-form` |

`base.css` loads before all of them, so it may only override a rule for an
element it owns outright.

### The Post List Grid

The index, the search results and the tag archive render the same markup — a
`<section class="posts-list">` of `.post-card` tiles — so the list is laid out
once, as a grid, in `public.css`:

```css
.posts-list {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-lg);
}

@media (min-width: 1024px) {
    .posts-list {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
```

One column below 1024px, two above it. The grid replaced a flex column: a
column of full-width cards showed one headline per screen.

**The tracks are `minmax(0, 1fr)`, not `1fr`.** A `1fr` track has an automatic
minimum of `min-content`, so a long unbroken title in a card widens its track,
the grid grows past the container it sits in and the page scrolls sideways.
`minmax(0, 1fr)` lets the track shrink below its content, so the title wraps
instead. The two-column case is `repeat(2, minmax(0, 1fr))` for the same
reason — one long title must not widen the pair. The main column of
`.content-layout` is `minmax(0, 1fr)` too, for exactly the same failure.

The sidebar column of `.content-layout` is a fixed `200px`, and the main column
is `minmax(0, 1fr)`. The sidebar was `260px` while it carried a "Recent posts"
list; that block is gone, so the column it needed is gone with it. The tag
cloud is now the widest thing in the sidebar, and 200px holds it.

The card came down with the grid: `.post-card-body` is `20px 22px` rather than
`24px 28px`, and the summary is clamped to two lines with
`-webkit-line-clamp: 2` and the standard `line-clamp: 2`, keeping
`overflow: hidden`. A card is a summary of a post, not the post; the reader opens the post
for the rest of it.

Measured at 1280px the grid computes `420px 420px`, a card is 420px wide, the
sidebar column is 200px and the card's image band is 418×235 (16:9). At 768px
the list is one 736px column; at 390px the card is 358px and nothing overflows
horizontally.

**`critical.css` paints the same grid.** The critical sheet is the first
paint, and a first paint of one column followed by a two-column reflow is a
visible jump. It therefore repeats the `.posts-list` rule and its 1024px media
query. This is the documented exception to the one-owner rule:
`critical.css` duplicates a small subset of the layout by design, and the
duplicate must match the sheet it shadows.

### The Tag Row

A card shows at most **four** tags and counts the rest. The cap lives in one
place — the `post_tag_row` macro in `app/templates/macros.html` — because the
index, the search results and the tag archive render the same card, and a cap
declared three times would drift. See
[Templates](templates.md#the-card-tag-row).

The chips are `.tag` links; the count is a `.tag.tag-more` label:

```html
<span class="tag tag-more" aria-label="3 more tags; this post has 7 tags in total, and the full list is on the post page">+3</span>
```

The count is a **label, not a link**, and it is styled as one. `.tag-more`
takes `--bg-elevated` for its surface, `--text-caption` for its ink, a
`1px solid var(--border)` edge, `cursor: default`, and no lift (`transform:
none`, `box-shadow: none`).

That is why the chip's hover lift is scoped to `a.tag:hover` and not to
`.tag:hover`. The lift is a link affordance: it says "this goes somewhere". The
count chip goes nowhere, so under the pointer it must stay still.

The accessible name is not optional either. A bare "+3" tells a screen reader
three of nothing; the `aria-label` says how many tags are hidden, how many the
post has in total, and that the full list is on the post page.

### The Post's Own Tag List

A card counts the tags it does not show, so the post itself is where the whole
list is found. `_post_content.html` renders every tag of the post in the post
footer, as `<div class="post-footer-tags post-tags">`, and `public.css` gives
that block a `margin-bottom: 16px` so it is separated from the back link below
it. The card and the post therefore never disagree about a post's tags.

### The Post Tile

The article page is one tile. `.post-full` is the tile — a translucent
`--bg-surface` with a border and a radius — and the hero image is flush with its
top edge, clipped by the tile's `overflow: hidden`. Everything below the image
lives in `.post-content`, which supplies the tile's inner gutter.

The panels *inside* the tile (the table of contents, the share bar, the TL;DR and
the author card) use `--bg-elevated`, not `--bg-surface`: on the tile's own
surface they would be the same colour as the tile and would read as nothing at
all.

The table of contents is rendered by `public/toc.js` into a
`.post-toc-container` that lives **inside** the article, directly under the hero
image. It used to sit outside the article, as a sibling of it, which made it
float above the post and span the whole container width instead of the post's
own.

The share bar follows the article body: it sits after `.post-body` and before
the `.author-card`, so the reader finishes the article and is then offered
sharing. Its spacing moved with it — `margin-top: 24px` where it used to be
`margin-bottom: 24px` — because the bar is no longer the first child of
`.post-content`. The margin is the same size, so the block it occupies is
unchanged at 94px (a 70px panel plus the 24px margin); the article's first
paragraph simply starts that much higher on the page.

### The Structural Voice

Three labels name the parts of a page rather than reading as content: the
table-of-contents title, the share label and the sidebar headings. They take
one shared treatment:

```css
font-family: var(--font-mono);
font-size: 0.72rem;
letter-spacing: 0.08em;
text-transform: uppercase;
color: var(--text-caption);
```

The mono face is the point: structure on a technical page reads as
machine-facing, and the metadata already used it. The uppercase treatment with
letter-spacing makes a label read as a label rather than as a heading, and the
caption role gives it the contrast the muted role did not.

Each label is declared in **exactly one** stylesheet, and the sheet that owns
an element owns it completely:

| Label | Owner |
|---|---|
| `.post-toc-title` | `public.css` |
| `.share-label` | `public.css` |
| `.sidebar-title` | `layout.css` |

The table-of-contents **entries** (`.post-toc a`) are a different matter. They
keep the body face and their own size — they are links — but they take the
caption role for colour and they are underlined, with
`text-underline-offset: 3px`. The rule used to declare `text-decoration: none`,
and because the public sheet loads after the base sheet at equal specificity,
that declaration won over the base sheet's own link treatment: the entries
never underlined, not even on hover or focus. They are links, so they now read
as links.

### The Reading Measure

The prose column is capped at `34em` and centred in its container. `base.css` owns
the rule, because the admin live preview renders `.prose` too and the preview
must match the published post.

The cap is expressed in `em` and not in pixels on purpose. The prose font size
changes at the mobile breakpoint — `1.05rem` above 768px and `0.95rem` at and
below it — so a pixel cap would hold a fixed column width and change the number
of characters per line with it. An `em` cap scales with the text: the column
measures 34 em at 1280px and at 768px, and the character count is the same at
both.

At 390px the cap does not bind: the column is 316px, narrower than the cap, so
the phone layout is unchanged.

**The measure is a unit, not a character count.** The number of characters a
column holds depends on the typeface, and the typeface is an operator choice
(`app/appearance/service.py` emits the `--font-sans` stack). The four bundled
sans families measure 61.5 (Space Grotesk), 67.5 (IBM Plex Sans), 70.4
(Atkinson Hyperlegible) and 74.1 (Inter) characters at `34em`. No single cap
puts all four inside the 65–75 band, because the spread between the widest and
the narrowest face is wider than the band itself. `34em` is the cap that
centres the range. `tests/e2e/test_prose_measure.py` pins both contracts: the
em measure, which is typeface-independent, and the character count for the face
the page actually renders with.

The cap narrows the text, never the page. The hero image above it keeps the
full width of the tile, and the table of contents — which is a navigation block
rather than prose — stays full tile width too.

### The Post Placeholder

`app/static/img/default-post.svg` is the mark shown where a post has no cover
image. It carries **no palette of its own**: every `fill` and `stroke` is
`currentColor` or `none`, and the background is transparent.

An SVG loaded through `<img>` cannot read the page's colour — it is an isolated
document, and `currentColor` inside it resolves against the SVG's own root
element, not against the `<img>`. The mark is therefore applied as a **CSS
mask** instead: `public.css` sets `mask-image: url("../img/default-post.svg")`
on `.img-placeholder` and paints the element's background with `var(--text-dim)`,
so only the mark's alpha is used and the ink comes from the theme. This is the
same mechanism the page backdrops use.

The placeholder is not an `<img>`. It is a `<span class="post-card-img
img-placeholder" role="img" aria-label="…">`, because the colour of an
`<img>`'s content cannot be changed by CSS. The `role` and the `aria-label`
reproduce what `alt` gave the old image.

`app/static/img/default-post-social.png` is a separate, self-contained 1200×630
raster. The social preview metadata points at it, because a social platform
renders neither an SVG nor a theme. The newsletter cover points at it too: most
mail clients block SVG.

### Image Bands

The card image band and the related-post thumbnail are sized by an aspect ratio,
not by a fixed height:

```css
.post-card-img,
.related-card-img {
    width: 100%;
    aspect-ratio: 16 / 9;
    height: auto;
    object-fit: cover;
}
```

`object-fit: cover` crops whatever does not match the box. A fixed `height:
200px` on an 804px-wide card made the band 4:1, which cut roughly a quarter off
the height of a 16:9 screenshot — the prompt at the top and the output at the
bottom. The ratio removes the crop, and no breakpoint may reintroduce a fixed
height.

The band's height follows the card's width, so a narrower card has a shorter
band: in the two-column grid a 420px card carries a 235px band. That is the
ratio doing its job, not a cropped image.

The post hero keeps its own 760×400 banner. A hero is a banner by convention,
and the placeholder mark is letterboxed inside it rather than cropped.

### Code Block Line Numbers

Code blocks are numbered on the left by a CSS counter. `app/markdown_renderer.py`
wraps every code line in `<span class="code-line">` — CSS cannot enumerate the
lines of a text node, so the markup has to carry the structure the counter
counts — and `base.css` owns the counter rules:

- `counter-reset: code-line` on `.prose pre`
- `counter-increment: code-line` on `.code-line`
- `content: counter(code-line)` on `.code-line::before`, in a fixed-width gutter

The newlines stay between the spans rather than inside them, so the code text
(`textContent`) is unchanged and copy and paste still yields what the author
wrote. `base.css` owns the rules because the admin shell does not load
`public.css` and the admin live preview renders `.prose` code blocks too. No
JavaScript takes part in the numbering.

### Syntax Highlighting

Prism is an npm devDependency (`prismjs` 1.30.0), not a vendored file. The
hand-assembled grammar bundle and the vendored core are gone; `app/static/js/prism.js`
is a second Vite entry that imports the core, imports 18 grammars and calls
`highlightCodeBlocks(Prism)`. A syntax error in the bundle therefore fails
`npm run build` rather than reaching the browser. The built chunk is roughly
64 kB (about 20 kB gzipped) and is named `prism-<hash>.js`.

`loadPrismIfNeeded()` in `main.js` injects a single module script pointing at
`document.documentElement.dataset.prismJsUrl`, and only when the page contains
`pre[class*="language-"]`.

`app/static/js/shared/prism-blocks.js` restores the renderer's per-line
structure after the highlighter replaces the code element's content: it reads
the existing line spans from `code.children`, splits the highlighted markup into
one fragment per line (`splitHighlightedLines`), and rebalances the tags so a
token that spans lines keeps its colour on every line. It deliberately does not
name the `code-line` class — the renderer remains the only producer of those
spans.

### Dark Mode

Dark mode follows OS preference by default via `prefers-color-scheme: dark`. The visitor color-scheme system uses a 3-state model (system/dark/light) with the `data-color-scheme` attribute (migrated from `data-theme` in Phase 08). The `color-scheme.js` module:
- Checks `localStorage.getItem('blog-color-scheme')` for persisted preference
- Falls back to `prefers-color-scheme: dark` media query
- Toggles by setting `data-color-scheme` attribute to `light` or `dark`
- Persists choice to `localStorage` under the `blog-color-scheme` key
- Listens for OS theme changes when preference is `system`
- `dark-mode.js` re-exports from `color-scheme.js` for backward compatibility

### Critical CSS

`critical.css` provides above-the-fold styles for fast initial paint. It mirrors the actual navbar, hero, container, and post-card classes so the first paint uses the same dark theme as the full stylesheets. It is loaded immediately; the remaining stylesheets use `media="print" onload="this.media='all'"` for deferred loading.

The `.posts-list` grid is one of the mirrored rules: the first paint of the
index shows two columns at a wide viewport, not one column that reflows a
moment later. See [The Post List Grid](#the-post-list-grid).

### Design Tokens

`base.css` owns the fallback design tokens used by every theme, including spacing, typography, surfaces, borders, focus colors, and semantic colors. The inline `theme_vars` block in the base templates overrides the color tokens for the selected Halloy theme (default: "Catppuccin Mocha"). The theme system translates Halloy TOML palettes into the blog's semantic CSS variables via `BlogTheme` and `translate.py`. Keep new component rules on these variables so all bundled Halloy themes remain coherent.

Phase 09 is complete — all CSS files now use semantic variables (`var(--navbar-bg)`, `var(--overlay-bg)`, `var(--shadow-color)`, `var(--success-bg)`, `var(--error-bg)`, `var(--warning-bg)`, `var(--accent-dim)`, `var(--text-on-accent)`, etc.) instead of hardcoded color literals. The only remaining hardcoded values are: `:root` emergency fallbacks, print stylesheet, social share brand colors, lightbox backdrop, neutral shadows, and SVG/email assets. See `docs/themes/frontend-literal-audit.md` for the full audit.

**Token completeness is enforced.** `tests/test_css_contracts.py` collects every
`var(--x)` referenced by a stylesheet and asserts that each name is either emitted
by the theme runtime or defined in a stylesheet. This is what catches a token that
is referenced but never emitted — such tokens resolve to the guaranteed-invalid
value, so the declaration using them is dropped at computed-value time.

`--shadow-color` and `--code-bg` were both referenced by the stylesheets while
being emitted by no one: eight `box-shadow` declarations silently rendered as
`none`, and light-mode inline code had no background. They are now produced by the
translation layer (`app/themes/translate.py` via the `ALIASES` map in
`app/themes/model.py`), so every bundled theme supplies them without a 50-file
migration.

The runtime also emits a small number of legacy aliases that no stylesheet
consumes. They are kept because `tests/themes/test_phase09_css_tokens.py` and
`tests/themes/test_translation.py` pin the legacy alias set; the allow-list and the
per-token rationale live in `tests/test_css_contracts.py::DEAD_TOKEN_ALLOW_LIST`.

### Font Self-Hosting

Fonts are self-hosted in `app/static/fonts/` as woff2 files; nothing is fetched
from a third party. Ten families ship with the site:

- Inter (weights 300–700) for body text (`--font-sans`)
- IBM Plex Sans (variable 100–700) as an alternative sans
- Space Grotesk (variable 300–700) as an alternative sans
- Atkinson Hyperlegible (weights 400, 700) as an alternative sans
- JetBrains Mono (weights 400, 500) for code blocks (`--font-mono`)
- IBM Plex Mono (weights 400, 600) as an alternative monospace
- Fira Code (variable 300–700) as an alternative monospace
- Cascadia Code (variable 200–700) as an alternative monospace
- Spline Sans Mono (variable 300–700) as an alternative monospace
- Meslo Nerd Font (weight 400) as a monospace with Nerd Font glyphs

The `@font-face` rules live in `base.css`. Which family is actually used is a
site setting, not a stylesheet decision: `app/appearance/service.py` emits the
`--font-sans` and `--font-mono` stacks at runtime and `base.html` preloads the
files those stacks name. See [Appearance Layer](appearance.md).

`app/static/fonts/LICENSES.md` records the SIL Open Font License 1.1 terms and
the upstream sources for each family.

### Page Backdrops

`app/static/img/backdrops/` holds the bundled page graphics: `grid.svg`
(blueprint grid, the default), `neural-mesh.svg`, `circuit-bloom.svg`,
`circuit-tree.svg`, `nexus.svg`, `hex-core.svg`, `quantum-orb.svg`,
`lattice.svg` and `signal.svg`. Each one supplies a shape only, in a single
colour. The colour is a theme-derived tint emitted per scheme as
`--backdrop-tint`, and the graphic is applied through `mask-image`, so an
operator's uploaded SVG matches the theme whatever colour it was drawn in. See
[Appearance Layer](appearance.md).

### Syntax Highlighting Themes

There is no syntax theme setting any more. The `SiteSettings.syntax_theme`
column was dropped, and the admin cannot choose a highlighting palette: the
token colours in `prism.css` follow the selected theme.

## Vite Configuration

Located at `vite.config.js`:
- Entry points: `app/static/js/main.js` and `app/static/js/prism.js`
- Output: `app/static/dist/`
- Code splitting via `manualChunks` (shared, admin, public)
- JSX support via esbuildOptions for `.jsx` files
- Dev server on port 3000 with proxy to Flask on port 5000

> **⚠️ Production Build Requirement:** The `npm run build` command (or `vite build`) must be executed before production deployment. This generates the `manifest.json` at `app/static/dist/.vite/manifest.json`. Without this build, templates fall back to unbundled source paths, so the production code-splitting entry point will not work correctly.
>
> **Docker builds handle this automatically.** The Dockerfile uses a multi-stage build where the first stage (`node:20-alpine`) runs `npm ci && npm run build`, and the runtime stage copies the resulting `app/static/dist/` into the final image. No manual build step is needed for Docker deployments.
>
> **Non-Docker deployments** require running `npm ci && npm run build` manually before starting the server.

> **⚠️ Restart a running server after every frontend build.** `app/vite.py` caches the Vite manifest in a module-level global for the life of the process. A rebuild renames the hashed bundles and deletes the old ones, but a server that is already running keeps serving the stale manifest — so it points at bundle files that no longer exist, the JavaScript never loads, and every interactive control silently does nothing. Restart the Flask server before you trust a browser check of a frontend change.

### Vite Asset Helper

`vite_asset()` in `app/vite.py` resolves content-hashed asset URLs and is registered as a Jinja2 global by `init_vite()`. It is used in the base templates for CSS, JS, fonts, and images.

In production:
- JS files: looks up hashed filename from `.vite/manifest.json`
- CSS/other: appends MD5 content hash as query string
- If `CDN_URL` is configured, prepends it to the asset path

### Chunk Split

Actual chunks via `manualChunks` in `vite.config.js`:
- `shared` — `shared/utils.js`, assigned explicitly so a failure inside an
  admin-only module cannot abort a shared module on a public page
- `admin` — Admin editor (`admin/editor.js`)
- `public` — Public search (`public/search.js`)

Prism is no longer a `vendor` chunk: it is its own Vite entry
(`app/static/js/prism.js`), so the Prism core and its grammars are fetched only
when a page actually has code blocks.

`shared/utils.js` must be assigned to the `shared` chunk **before** the
`/admin/editor.js` rule. `admin/editor.js` imports it, and without the explicit
assignment Rollup emits the shared module into the admin chunk — every public page
then fetches the admin chunk to obtain `initSharedUtils`.

`main.js` must not import a stylesheet. Flask links the stylesheets in the base
templates so the dev server and production share one cascade order; an import in
`main.js` would emit an orphaned CSS asset and append the stylesheet after every
linked one in dev.

## See Also
- [Templates](templates.md) - Jinja2 templates
- [App Factory](../core/app-factory.md) - Vite initialization
