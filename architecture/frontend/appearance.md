# Appearance Layer (`app/appearance/`)

Typefaces and the page backdrop. The theme system owns colour; the appearance
layer owns everything the theme does not decide.

## Why It Is Separate From The Theme

The theme registry answers "which palette?". The appearance registry answers
"which typeface?" and "which graphic sits behind the page?". They follow the
same shape so there is one mechanism to learn, not two:

| Layer | Registry | Service | Settings | Runtime |
|---|---|---|---|---|
| Theme | `app/themes/registry.py` | `app/themes/service.py` | `theme_dark_name`, `theme_light_name` | `theme_dark_vars`, `theme_light_vars` |
| Appearance | `app/appearance/fonts.py`, `app/appearance/backdrops.py` | `app/appearance/service.py` | `font_sans`, `font_mono`, `backdrop` | `--font-sans`, `--font-mono`, `--backdrop-tint`, `--backdrop-image` |

## Components

| File | Purpose |
|---|---|
| `app/appearance/model.py` | `FontFamily` and `BackdropDescriptor` records |
| `app/appearance/fonts.py` | `FontRegistry` — bundled families plus operator uploads |
| `app/appearance/backdrops.py` | `BackdropRegistry` — bundled graphics plus operator uploads |
| `app/appearance/service.py` | `AppearanceService` — resolves the choice and emits the CSS |
| `app/appearance/svg.py` | `sanitize_svg()` — makes an uploaded backdrop inert |
| `app/appearance/uploads.py` | Validates and stores uploaded fonts and backdrops |
| `app/services/appearance_settings.py` | Form parsing and key resolution for the admin form |

The service is per-process, registered as `app.extensions["appearance_service"]`
by `init_appearance_service()` in the app factory, and cached for 300 seconds
exactly like the theme service. `invalidate_settings_cache()` clears both.

## The Font Catalog

Ten families ship with the site, all served from `app/static/fonts/`:

| Key | Family | Slot | Files |
|---|---|---|---|
| `inter` | Inter | sans | `inter-300…700-latin.woff2` |
| `ibm-plex-sans` | IBM Plex Sans | sans | `ibm-plex-sans-latin.woff2` (variable) |
| `space-grotesk` | Space Grotesk | sans | `space-grotesk-latin.woff2` (variable) |
| `atkinson-hyperlegible` | Atkinson Hyperlegible | sans | `atkinson-hyperlegible-400/700-latin.woff2` |
| `jetbrains-mono` | JetBrains Mono | mono | `jetbrains-mono-400/500-latin.woff2` |
| `ibm-plex-mono` | IBM Plex Mono | mono | `ibm-plex-mono-400/600-latin.woff2` |
| `fira-code` | Fira Code | mono | `fira-code-latin.woff2` (variable) |
| `cascadia-code` | Cascadia Code | mono | `cascadia-code-latin.woff2` (variable) |
| `spline-sans-mono` | Spline Sans Mono | mono | `spline-sans-mono-latin.woff2` (variable) |
| `meslo-nerd-font` | Meslo Nerd Font | mono | `meslo-nerd-font-latin.woff2` |

Nothing is fetched from a third party. The `@font-face` rules live in
`app/static/css/base.css`; the service only emits the `--font-sans` and
`--font-mono` stacks that name the chosen family.

Variable families are stored once rather than once per weight. `app/static/fonts/LICENSES.md`
records the SIL Open Font License 1.1 terms and the upstream sources.

### The Nerd Font

`meslo-nerd-font` is a real Nerd Font: the Latin range plus the Private Use
Area blocks that carry the powerline and devicons glyphs
(`U+E0A0-E0A3`, `U+E0B0-E0C8`, `U+E0CA`, `U+E0CC-E0D2`, `U+E0D4`,
`U+E0D6-E0D7`, `U+E5FA-E6BB`). Its `unicode-range` names those blocks, so a
devicon in a code block is drawn by the font rather than by the last-resort
fallback. The other families are ordinary text faces — they are shipped for
their shape, not for glyph coverage.

### A Choice That No Longer Exists

A stored custom font or backdrop whose file has been removed from storage is
reported as missing by the registries, and the service falls back to a bundled
family. Without that check the runtime would emit a stack whose first entry
never loads, and the page would silently fall back to the default face while
the settings still claimed otherwise.

### Custom Fonts

An operator can upload a `.woff2` or `.woff` file per slot. The file is
checked by magic bytes (`wOF2` / `wOFF`), capped at 5 MB, written through the
storage backend as `custom-font-<slug>-<hash>.woff2` and served from
`/static/uploads/`. Because it is a custom family, the service emits an
`@font-face` rule for it at runtime.

The stored key *is* the family key, so `SiteSettings.font_sans` holds either
`inter` or `custom-font-<slug>-<hash>.woff2`. No second column is needed.

## The Backdrop

A backdrop is a large, single-colour graphic behind the page. Three ship with
the site in `app/static/img/backdrops/`: `default` (a disc and a concentric
ring), `grid` (blueprint grid) and `waves` (flowing bands).

The graphic supplies only a shape. The colour comes from the theme at runtime:

```
body::before   fixed layer, the page gradient
body::after    fixed layer, the backdrop shape, masked by --backdrop-image
```

`mask-image` means the SVG's own fill is irrelevant — only its alpha is used.
That is what lets an operator upload an SVG of any colour and have it still
match the theme. The service derives the tint from the theme's `bg` and
`accent` for each scheme, so the backdrop is a shade off the background rather
than a fixed colour.

The page background is therefore three layers: the theme's `bg` on the canvas,
a subtle gradient mixed from `bg` and `bg-surface`, and the backdrop shape on
top of it.

A backdrop is drawn with `mask-size: cover`, so the shape has to survive being
cropped. The bundled graphics keep their forms inside the central 1600×1000
viewBox and away from the edges.

### Custom Backdrops

An uploaded SVG is sanitised by `sanitize_svg()` before it is stored. The
sanitiser parses the document and removes scripting elements, event handler
attributes, `javascript:` links, external references, embedded styles and
doctype declarations. The stored file is the sanitised one, so serving it
cannot execute anything.

The file is capped at 1 MB and must be a `.svg`.

## Panels Are Translucent

Card and panel surfaces use:

```css
background: var(--bg-surface);
background: color-mix(in srgb, var(--bg-surface) 94%, transparent);
```

The first declaration is the fallback for engines without `color-mix()`, the
second is what modern engines use. Only surfaces that hold content are
translucent: cards, admin panels, sidebars and the footer. Form inputs, code
blocks and dropdowns stay opaque because they carry text.

## Admin Surface

`/admin/settings` has a **Typography & Background** section that posts to
`admin.settings_appearance` (`POST /admin/settings/appearance`). The form is
multipart so it can carry an upload. Choosing `Custom` reveals the file input;
the rest of the form is unchanged.

A **Preview** block under the three choices renders a sample of the selected
sans and monospace faces and follows the selects as they change, so the
operator can see the difference before saving. The specimen applies the family
name from `font_family_map`, which the route builds from the registry, so it
always names the same family the runtime will use.

`app/services/appearance_settings.py` owns the parsing and the resolution, so
the route never interprets a raw form value on its own.

## See Also
- [Static Assets](static-assets.md) - Fonts, backdrops and the CSS cascade
- [Themes](../../docs/themes/README.md) - The theme system that owns colour
