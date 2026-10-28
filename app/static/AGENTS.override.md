# Frontend Agent Override

Specialized handling for JavaScript, CSS, and Vite build system.

## Directory Structure

```
app/static/
├── js/
│   ├── main.js           # Route-based dynamic imports loader
│   ├── prism.js          # Second Vite entry: Prism core + 18 grammars
│   ├── lib/              # Third-party JS libraries (marked.js for markdown preview)
│   ├── shared/           # Shared JS modules (utils, dark-mode, modal, mobile-menu, toast, etc.)
│   ├── public/           # Public-facing JS modules (share, lightbox, toc, search, etc.)
│   └── admin/            # Admin JS modules (editor, editor-history, markdown-toolbar, bulk, shortcuts)
├── css/
│   ├── critical.css       # Above-the-fold CSS for fast initial paint
│   ├── base.css          # CSS variables, reset, typography
│   ├── layout.css        # Grid layout, navbar, sidebar, footer
│   ├── forms.css         # Form elements, buttons, validation
│   ├── admin.css         # Admin-specific styles
│   ├── public.css        # Public-facing page styles
│   ├── utilities.css     # Helper classes
│   └── prism.css         # Prism token colours, mapped onto the theme tokens
├── fonts/                # Self-hosted fonts (Inter, IBM Plex Sans, Space Grotesk,
│                         # Atkinson Hyperlegible, JetBrains Mono, IBM Plex Mono,
│                         # Fira Code, Cascadia Code, Spline Sans Mono, Meslo Nerd Font)
├── img/                  # Static images
└── dist/                 # Vite build output
```

## Vite Build System

```bash
# Install dependencies
npm install --registry https://registry.npmjs.org/

# Development with HMR
npm run dev

# Build for production (with content hashing)
npm run build
```

Configuration: `vite.config.js`.

## Content Hashing

- Vite generates content-hashed filenames (e.g., `main-BVtPp-ke.js`)
- Manifest file generated at `app/static/dist/.vite/manifest.json`
- Flask helper `vite_asset()` in `app/vite.py`:
  - JS files: Looks up hashed filename from manifest
  - CSS/other: Appends MD5 content hash as query string (e.g., `base.css?v=3544ab62`)
- Templates use `{{ vite_asset('path/to/file') }}` instead of `{{ url_for('static', ...) }}`
- Enables aggressive caching with `Cache-Control: max-age=31536000, immutable`

## JS Module Initialization (CRITICAL)

All JavaScript modules must export a default function for initialization. When adding new modules to `shared/` or `public/`, you **must** add `export default initXxx;` where `initXxx` is the initialization function. The main.js loader calls `module.default()` to invoke the exported function. Modules without this export will not be called on page load.

**Dynamic Imports**: Vite requires static analysis for bundling. ALWAYS use `import.meta.glob(['./path/*.js'])` for dynamic route-based module loading in `main.js`. Never use variable-based `import(path)`.

## Route-Based Code Splitting

`app/static/js/main.js` uses route-based dynamic imports. Admin pages get utils, modal, shortcuts, bulk. Public pages get utils, dark-mode, mobile-menu, lazy-load, share, lightbox, toc.

## Mobile Menu Toggle

The mobile hamburger menu button is **created dynamically in JavaScript** (`shared/mobile-menu.jsx`), not in HTML templates.

The scrim that dims the page behind an open menu is a **body-level element**
created by the same module (`.mobile-menu-backdrop`), not a pseudo-element of
`.nav-links`. The menu panel sits inside the navbar's stacking context, so a
scrim declared on the panel would paint over the menu links, and a tap on it
would count as a click inside the menu, leaving the menu impossible to dismiss
by tapping away from it. The backdrop sits at z-index 99, under the navbar's
100, so it dims the page but leaves the panel and the toggle clickable.

## Admin Page Detection in JS

Use `document.body.classList.contains('admin-body')` to scope admin-only JS handlers.

## Lazy Image Progressive Enhancement

Images use `opacity: 0` by default and JS adds `.loaded` class. Pattern: add `document.documentElement.classList.add('js')` first, prefix CSS rules with `.js`.

See [Lazy Image Loading](#lazy-image-loading) under Cross-Layer Contracts for the
restoration-path rule that makes this safe.

## Responsive Images

Post images support responsive srcset via the `post_image_srcset` filter. Variants are generated at 400w, 800w, and 1200w widths on upload. Templates use `srcset` with `sizes` attribute.

The filter returns `None` when no variants exist, so the `srcset` attribute must be
guarded — see [Image URLs](#image-urls).

## GPU Acceleration for Blur Effects

For `backdrop-filter: blur()`, use `will-change: backdrop-filter` in CSS:
```css
.navbar, .nav-links, .modal-overlay {
    will-change: backdrop-filter;
}
```

## CSS Architecture

- Dark mode is default; light theme toggled via `data-color-scheme` attribute (migrated from `data-theme` in Phase 08)
- Self-hosted fonts (Inter, IBM Plex Sans, Space Grotesk, Atkinson Hyperlegible, JetBrains Mono, IBM Plex Mono, Fira Code, Cascadia Code, Spline Sans Mono, Meslo Nerd Font) via `@font-face`
- No external font CDNs
- The page background is three layers: the theme `bg` on the canvas, a gradient mixed from `bg` and `bg-surface` (`body::before`), and the backdrop shape (`body::after`, masked by `--backdrop-image`)
- Panels are translucent via `color-mix(in srgb, var(--bg-surface) 94%, transparent)` with a plain `var(--bg-surface)` fallback first
- The Markdown prose rules live in `base.css`, not `public.css`: the admin shell does not load `public.css`, and the admin live preview renders `.prose` content

## Syntax Highlighting

There is no syntax theme setting. `SiteSettings.syntax_theme` was retired and
the six vendored Prism palettes are gone; `prism.css` maps every Prism token
onto a theme token, so the syntax colours follow the selected theme.

Prism itself is an npm devDependency (`prismjs` 1.30.0), not a vendored file.
`app/static/js/prism.js` is a second Vite entry that imports the core, imports
18 grammars and calls `highlightCodeBlocks(Prism)`, so a syntax error in the
bundle fails `npm run build` rather than reaching the browser. `main.js`
injects that one module script only when the page contains
`pre[class*="language-"]`.

## Assets Policy

- **No external assets**—all fonts are self-hosted in `app/static/fonts/`
- **Prism.js** ships from the npm package and is bundled by Vite — no CDN
- Do not add external CDN links (Google Fonts, CDNs, etc.)

## Cross-Layer Contracts

These are the seams where a template, a stylesheet, a module, and the server each make
an assumption about the other. Every one of them has caused a defect before, so each
now has a single owner and a named rule. Do not reintroduce a second producer for any
of these values.

### Image URLs

`post_image_url` returns a **URL**, not a filename: `/static/uploads/<file>` for the
local backend and an absolute `https://…` URL for S3. Templates must use the filter
output directly.

```jinja
{# correct #}
<img src="{{ img }}"{% if srcset %} srcset="{{ srcset }}" sizes="…"{% endif %}>

{# wrong — produces /static/uploads//static/uploads/<file> #}
<img src="{{ url_for('static', filename='uploads/' + img) }}">
```

`app/templates/admin/media.html` is the one exception: it renders `f.name` from
`storage.list_files()`, which **is** a bare filename.

`post_image_srcset` returns `None` when no responsive variants exist. Jinja renders
`None` as the literal string `"None"`, and a `srcset` candidate list overrides `src`
entirely — so the attribute must be guarded, never emitted unguarded.

### Lazy Image Loading

`.js img[loading="lazy"] { opacity: 0 }` is only safe because a restoration path is
guaranteed. `shared/lazy-load.js` attaches the `load` **and** `error` handlers
*before* the native-support early return, so the `.loaded` class is applied on every
browser. The `error` listener is required: a broken image must not stay invisible.
Any new rule that hides an element must have a matching restoration selector.

### Lightbox Visibility

`hidden` is the source of truth for the dialog's visibility; `open` is the animation
state. `.lightbox.hidden { display: none !important }` and `.lightbox:not(.hidden)
{ display: flex }` therefore need no JavaScript to open the dialog — the JS only
removes and re-adds `hidden`. Restore `document.body.style.overflow` to the value it
had before opening, not to `''`.

### CSRF Header Name

The header name is defined **once**, in `app/csrf.py` as `CSRF_HEADER_NAME`
(`X-CSRF-Token`). It is published to the browser as `data-csrf-header` on the root
element and read by `csrfHeaders()` in `shared/utils.js`. No template or module may
hard-code the name — HTTP header names are case-insensitive but not hyphen-
insensitive, so `X-CSRFToken` does not match `X-CSRF-Token`.

### Route → Module Mapping

`getModulesForPath()` in `main.js` matches on a **path-segment boundary**
(`path === route || path.startsWith(route + '/')`), preferring the longest match,
with `/admin/` as the catch-all. Plain `startsWith` is not sufficient: `/admin/new`
is a literal prefix of `/admin/newsletter/preview`.

### Heading IDs

Exactly one module produces heading IDs: `shared/heading-slug.js`. `public/toc.js`
and `public/anchor-links.js` both import it. Do not add a second slugger.

### Heading Anchors

`public/anchor-links.js` appends the anchor to the heading itself — the heading
is its containing block, so the `#` sits in the left gutter and is revealed on
hover or focus. It must not be wrapped in a span: the wrapper made the anchor a
sibling of the wrapper rather than a descendant, the positioning rule stopped
matching, and the `#` was painted inline at the end of every title.

The anchor is transparent until the heading is hovered or the anchor is
focused, on every breakpoint.

### Markdown Prose

The `.prose` typography is owned by `base.css`. The admin live preview renders
`.prose` content and the admin shell does not load `public.css`, so prose rules
in `public.css` are missing in the preview. `tests/test_css_contracts.py`
enforces that `base.css` owns them and `public.css` does not.

### Reading Measure

The prose column's measure is `max-width: 34em` on `.prose`, owned by `base.css`
for the same reason the prose typography is: the admin live preview renders
`.prose`. The cap is in `em` because the prose font size changes at the mobile
breakpoint; a pixel cap would change the character count with it.

`public.css` must not set a width or a max-width on `.post-body`. The measure
narrows the text, never the page: the hero image keeps the full width of the
tile and the table of contents stays full tile width.

### Placeholder Image

`app/static/img/default-post.svg` is the mark shown where a post has no cover
image, and it has exactly one owner: the `.img-placeholder` rule in
`public.css`, which applies it as a CSS mask and paints the ink with
`var(--text-dim)`.

An SVG loaded through `<img>` cannot read the page's colour, so the placeholder
is a `<span role="img" aria-label="…">`, not an `<img>`. Do not load the mark as
an image: it would render in black on a dark theme. The social preview and the
newsletter cover use `app/static/img/default-post-social.png`, a separate
self-contained raster, because those renderers execute no CSS.

### Default Profile Image

The "no profile picture" portrait is one macro in
`app/templates/_default_avatar.html`. The account page, the author page, the
post footer and the admin profile page all use it. Do not draw a second
placeholder, and do not fall back to the first letter of the name.

### Flash Messages

The server renders flashes as `.flash-container > .flash > .flash-message`.
`shared/toast.js` converts them into toasts and removes the container on load, so
the final DOM may contain either representation. Tests must assert the
user-visible message, not one specific node.

### Theme Tokens

The theme runtime owns colour. Static CSS consumes theme tokens and must not use
literals for themed surfaces. Every `var(--x)` referenced by a stylesheet must be
either emitted by the theme runtime or defined in a stylesheet — this is enforced by
`tests/test_css_contracts.py`. Tokens that the runtime emits but no stylesheet
consumes are dead weight.

### Admin Theme Preview

The preview panel on `/admin/settings` is a seam between the template, the
inline script in that template, and the admin stylesheet (which owns none of
it). The section order — Theme Preview, Theme, Theme Registry — is a contract,
not an arrangement, and four invariants keep the panel working:

- The `.theme-preview-btn` triggers stay with the two theme `<select>`
  controls. `fetchPreview()` reads the current, possibly unsaved, select
  values and posts them to `admin.settings_theme_preview`; the buttons are
  `type="button"` and never submit the form.
- `.theme-preview-container` sets `min-height` equal to `max-height` (380px,
  300px under the 768px breakpoint), so replacing the placeholder with
  preview content cannot change the box height and cannot move the controls
  below it.
- "Clear Preview" restores the placeholder node; it must not hide the section.
- `applyPreviewCss()` scopes the injected stylesheet to
  `#theme-preview-container[data-color-scheme="…"]`, so previewing a theme
  never repaints the rest of the admin panel.

All preview CSS is inline in the template's `<style nonce="{{ csp_nonce }}">`
block. No preview rule belongs in `app/static/css/`.

### Code Block Line Numbers

Line numbers are produced by a CSS counter, and the markup has to carry the
structure a counter needs. `app/markdown_renderer.py` wraps every code line in
`<span class="code-line">`; `base.css` owns `counter-reset: code-line` on
`.prose pre`, `counter-increment: code-line` on `.code-line` and
`content: counter(code-line)` on its `::before`.

`base.css` owns those rules because the admin shell does not load
`public.css` — the admin live preview renders `.prose` code blocks too. No
stylesheet may own the numbering a second time, and no JavaScript may take
part in it.

Prism is the one thing that would break the contract: `highlightElement()`
replaces the `<code>` element's `innerHTML`, which removes the `code-line`
spans. `shared/prism-blocks.js` is the repair: it reads the existing line spans
from `code.children`, splits the highlighted markup into one fragment per line
(`splitHighlightedLines`), and rebalances the tags so a token that spans lines
keeps its colour on every line. It deliberately does not name the `code-line`
class — the renderer remains the only producer of those spans.

### Stylesheet Ownership

Exactly one stylesheet owns a given element's visibility at each breakpoint.
`layout.css` and `base.css` both setting `.nav-links { display }` is a cascade tie
resolved by document order, not by intent — scope the rule instead.

**A media query adds no specificity.** An `@media (max-width: 768px)` rule ties
with the unconditional rule for the same element in a later stylesheet and loses
on document order, so the breakpoint has no effect at all. The sheet that owns an
element's base rule therefore owns its breakpoint override too:

| Sheet | Owns |
|---|---|
| `base.css` | tokens, reset, `.prose`, `.btn`, `.theme-toggle`, `.back-to-top`, `.reading-progress`, `.mobile-menu-toggle`, the code block's layout and `.copy-code-btn` |
| `layout.css` | `.container`, `.content-layout`, `.sidebar`, `.sidebar-title`, the navbar and `.nav-links` |
| `public.css` | `.hero`, `.posts-list`, `.post-card`, `.post-full`, `.post-hero`, `.post-toc`, `.share-bar`, `.tldr`, `.tag`, `.tag-more`, `.post-footer-tags`, `.author-card`, `.related-*`, `.archive-*`, `.search-form` |
| `projects.css` | `.projects-*` directory and `.project-*` landing page structures |
| `forms.css` | the form controls, including their iOS-zoom font sizes |
| `admin.css` | the admin surfaces, including `.post-list-*` and `.editor-form` |
| `prism.css` | the Prism `.token.*` colours, and nothing else |

`base.css` loads before all of them, so it may only override a rule for an
element it owns outright.

`prism.css` is a theme-token stylesheet owned by itself: it carries only the
`.token.*` colour rules and no colour literal of any kind, so every Prism
token resolves to a theme token. It does not own the code block's appearance —
`base.css` owns that, including the `position: relative` on `.prose pre`, the
line-number counter and the `.copy-code-btn`.

### Text Roles

`--text-caption` and `--accent-text` are the two text roles the theme runtime
derives (`app/themes/translate.py`); no theme file declares them. Text a
reader must read uses `--text-caption`, and the accent used as text uses
`--accent-text`. The accent keeps its non-text uses — fills, focus rings,
borders.

Seven uses of `var(--text-muted)` are deliberately left in place, because that
text is decorative rather than read:

| Stylesheet | Selector |
|---|---|
| `admin.css` | `.md-tool` |
| `admin.css` | `.md-tool:disabled:hover` |
| `admin.css` | `.preset-card:hover` (a `border-color`) |
| `base.css` | `.theme-toggle` |
| `base.css` | `.back-to-top` |
| `base.css` | `.mobile-menu-toggle` |
| `public.css` | `.search-clear` |

Do not convert these to `--text-caption`, and do not add a new one without
deciding whether the text is read.

### Post Tile

`.post-full` is the article tile: a translucent `--bg-surface` with a border and
a radius, with the hero image flush against its top edge and everything below
the image inside `.post-content`, which supplies the tile's inner gutter. The
panels inside the tile — the table of contents, the share bar, the TL;DR and the
author card — use `--bg-elevated`, not `--bg-surface`; on the tile's own surface
they would be the same colour as the tile and would read as nothing at all.

The `.post-toc-container` lives inside the article, directly under the hero
image, so the contents list shares the post's width and reads as part of the
post. It is rendered by `public/toc.js`.

### Post List Grid

`.posts-list` is a grid, not a column, and `public.css` owns it. One track on
a narrow viewport and two from 1024px:

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

The tracks are `minmax(0, 1fr)` rather than `1fr` because a `1fr` track has an
automatic minimum: a card whose title is one long unbroken word sets that
minimum, and the grid grows wider than the container holding it. `minmax(0, 1fr)`
lets the title shrink its own column and wrap instead.

The breakpoint belongs to the same sheet as the base rule — a media query adds
no specificity, so a breakpoint override in another sheet ties with the base
rule and loses on document order.

### Card Tag Row

`app/templates/macros.html` holds `post_tag_row(post, max_tags=4)`, the single
owner of a post card's tag cap. It renders at most four tag links and, when
the post carries more, a `<span class="tag tag-more">` label whose `aria-label`
says how many tags were hidden, how many the post has in total, and that the
full list is on the post page.

The count chip is a **label, not a link**. The hover lift therefore belongs to
`a.tag:hover`, not to `.tag:hover` — a chip that rises under the pointer
implies a destination it does not have, and it is the only element in the row
that is not clickable. `public.css` owns `.tag-more`: a muted surface, the
caption role, and no lift.

The cap is the card's, not the post's. `_post_content.html` renders every tag
in the post's footer, so a card never holds the only copy of a tag.

### Structural Voice

Three labels share one voice — the mono face, an uppercase treatment, the
caption role:

```css
font-family: var(--font-mono);
font-size: 0.72rem;
letter-spacing: 0.08em;
text-transform: uppercase;
color: var(--text-caption);
```

They are not one shared class. Each label is declared in exactly one
stylesheet, and that stylesheet owns it:

| Label | Owner |
|---|---|
| `.post-toc-title` | `app/static/css/public.css` |
| `.share-label` | `app/static/css/public.css` |
| `.sidebar-title` | `app/static/css/layout.css` |

A structural label names the group beneath it — a list of contents, a row of
controls, a section of a page. It is not a heading in the page's hierarchy,
and it must not take the body face.

### First Paint

`app/static/css/critical.css` paints the same `.posts-list` grid, because
`base.html` loads that sheet with `media="screen"` and it is the first paint.
A column of cards that is visible for a moment and then becomes a grid is a
visible reflow. `critical.css` deliberately duplicates a small subset of the
layout; it is a documented exception, not a second owner — the full sheet
still owns the rule.

### Vite Build

`main.js` must **not** import a stylesheet. Flask links the stylesheets in
`app/templates/base.html` so that the dev server and production share one cascade
order. `shared/utils.js` is assigned to the `shared` chunk explicitly so a failure
inside an admin-only module cannot abort a shared module on a public page.

### Optional AI Post Authoring

The post editor template owns conditional AI controls and the server-provided `admin.ai_assist` URL; `app/static/js/admin/editor.js` owns click-only requests and explicit review/apply behavior. Never trigger inference during load, preview, focus, typing, or save. Treat every response as untrusted plain text; use `textContent` and form values only, never HTML insertion. Snapshot source and destination values at request start and refuse stale applies. Tags append only after author approval, preserving existing entries and deduplicating. Applied tags and summary dispatch bubbling `input` and `change` so ordinary draft autosave and dirty-state paths stay authoritative; normal Post Save remains the only persistence path. Never place keys, prompts, catalogs or AI responses in localStorage.