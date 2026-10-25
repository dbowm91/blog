# Theme System (`app/themes/`)

The theme system owns colour. Every colour the frontend paints is derived from a
Halloy-compatible `.toml` theme file: the file is parsed into a typed
`HalloyTheme`, translated into a typed `BlogTheme`, validated for contrast, and
emitted as CSS custom properties. Static stylesheets consume tokens and never
name a colour directly. The module is deliberately narrow — it parses,
translates, validates and caches palettes, and it does nothing else. Typeface
and backdrop belong to the appearance layer; the database-facing half of the
feature lives in `app/services/theme_settings.py`.

## Module Files

| File | Owns |
|---|---|
| `app/themes/__init__.py` | Public API re-exports (`BlogTheme`, `ThemeRegistry`, `ThemeService`, the colour primitives, the diagnostics helpers) |
| `app/themes/colors.py` | `RGB` / `RGBA` value types, hex parsing, WCAG relative luminance and contrast, alpha compositing, mixing, lightness adjustment |
| `app/themes/halloy.py` | Typed Halloy TOML parser (`parse_halloy_theme()`, `parse_halloy_theme_bytes()`) and the `ThemeParseError` → `ThemeSchemaError` / `ThemeColorError` hierarchy |
| `app/themes/model.py` | `BlogTheme` frozen dataclass, `CSS_VARS` (semantic layer), `ALIASES` (legacy compatibility layer), `EMERGENCY_DEFAULT` |
| `app/themes/translate.py` | `translate_halloy_theme()` plus the serialisers `to_css_variables()`, `to_theme_vars()`, `to_legacy_vars()`, `to_legacy_css()` |
| `app/themes/diagnostics.py` | Contrast checks, severity classification, structured findings, the accessibility exception manifest reader, translation provenance |
| `app/themes/resources.py` | `ThemeFileInfo`, the `ThemeResource` protocol, bundled (package) and external (directory) discovery, theme-name validation |
| `app/themes/cache.py` | `ThemeCache` and `ThemeCacheEntry` — the in-process load cache and its freshness check |
| `app/themes/registry.py` | `ThemeRegistry` (catalogue, resolution, loading, invalidation, fallback) and the `ThemeNotFoundError` / `ThemeParseFailure` / `ThemeLoadError` / `ThemeValidationError` hierarchy |
| `app/themes/service.py` | `ThemeService` — per-process registry owner, settings resolution and the Jinja context builder |
| `app/themes/bundled/` | 50 packaged Halloy themes, `catalog_manifest.json` (`theme_count: 50`), `ATTRIBUTION.md` |
| `app/themes/ACCESSIBILITY_EXCEPTIONS.json` | Accessibility exception manifest (schema version 2) |
| `app/services/theme_settings.py` | The database-facing half: `validate_theme_settings()` and `get_effective_theme_names()` |

## The Pipeline

```
themes/*.toml  or  app/themes/bundled/*.toml
        │  resources.discover_bundled_package() / discover_external()
        ▼
  ThemeFileInfo ──── read_bytes() ────▶ bytes
        │  halloy.parse_halloy_theme_bytes()
        ▼
  HalloyTheme            (general / text / buffer / buttons)
        │  translate.translate_halloy_theme()
        ▼
  ThemeTranslationResult (theme=BlogTheme, is_dark, diagnostics)
        │  translate.to_css_variables() / to_theme_vars() / to_legacy_vars()
        ▼
  LoadedTheme            (registry.load(), memoised in ThemeCache)
        │  ThemeService.get_context()
        ▼
  context dict: theme_dark_vars / theme_light_vars
        │  app/context_processors.py → inject_theme
        ▼
  base.html / admin/base.html → :root, [data-color-scheme="dark"|"light"]
```

| Stage | Entry point | Input | Output |
|---|---|---|---|
| Discovery | `discover_bundled_package()`, `discover_bundled()`, `discover_external()` | package directory or filesystem directory | `list[ThemeFileInfo]` |
| Parsing | `parse_halloy_theme_bytes(data, source_name=...)` | raw TOML bytes | `HalloyTheme` |
| Translation | `translate_halloy_theme(theme)` | `HalloyTheme` | `ThemeTranslationResult` |
| Serialisation | `to_css_variables()`, `to_theme_vars()`, `to_legacy_vars()` | `BlogTheme` | CSS text / `dict[str, str]` |
| Loading | `ThemeRegistry.load(name)` | theme name | `LoadedTheme` |
| Fallback | `ThemeRegistry.get_fallback(configured)` | theme name | `LoadedTheme` (possibly emergency) |
| Runtime | `ThemeService.get_context()` | `SiteSettings` | Jinja context dict |
| Rendering | `inject_theme()` context processor | context dict | template variables |

## The Token Model

`BlogTheme` is a frozen, slotted dataclass with **50 fields**: 41 `RGB` values and
9 `RGBA` values. `CSS_VARS` maps every one of those field names to a `--blog-*`
custom property, so the two are exactly parallel — there is no token that has no
field and no field that has no token.

### Token groups

| Group | Fields | CSS properties |
|---|---|---|
| Backgrounds and surfaces | `bg_page`, `surface_default`, `surface_elevated`, `surface_hover`, `surface_active`, `navbar_bg`, `overlay_bg` | `--blog-bg-page`, `--blog-surface-default`, `--blog-surface-elevated`, `--blog-surface-hover`, `--blog-surface-active`, `--blog-navbar-bg`, `--blog-overlay-bg` |
| Borders | `border_primary`, `border_subtle`, `border_strong`, `border_focus`, `navbar_border` | `--blog-border-primary`, `--blog-border-subtle`, `--blog-border-strong`, `--blog-border-focus`, `--blog-navbar-border` |
| Text | `text_primary`, `text_secondary`, `text_muted`, `text_dim`, `text_on_accent`, `text_on_success`, `text_on_error`, `text_on_warning`, `text_on_info`, `text_link`, `text_link_hover` | `--blog-text-primary` … `--blog-text-link-hover` |
| Accent | `accent`, `accent_hover`, `accent_dim`, `accent_link`, `accent_focus_ring` | `--blog-accent`, `--blog-accent-hover`, `--blog-accent-dim`, `--blog-accent-link`, `--blog-accent-focus-ring` |
| Status | `success_fg`, `success_bg`, `error_fg`, `error_bg`, `warning_fg`, `warning_bg`, `info_fg`, `info_bg` | `--blog-success-fg` … `--blog-info-bg` |
| Inputs and code | `input_bg`, `input_border`, `input_text`, `code_bg`, `code_border`, `code_text` | `--blog-input-bg` … `--blog-code-text` |
| Chrome and misc | `selection_bg`, `navbar_text`, `navbar_text_muted`, `shadow_color`, `noscript_bg`, `noscript_text`, `coral`, `coral_dim` | `--blog-selection-bg` … `--blog-coral-dim` |

The nine alpha-bearing fields are `navbar_bg`, `overlay_bg`, `accent_dim`,
`success_bg`, `error_bg`, `warning_bg`, `info_bg`, `shadow_color` and
`coral_dim`. `to_css_variables()` serialises an `RGBA` with `alpha < 1.0` as an
8-digit hex value (`#rrggbbaa`) and otherwise as a 6-digit hex value.

### Where each token comes from

`translate_halloy_theme()` maps Halloy sections onto the token model:

| Halloy source | Tokens |
|---|---|
| `[general].background` | `bg_page`; `navbar_bg` is the same colour at 0.85 alpha |
| `[general].border`, `[general].horizontal_rule` | `border_primary`, `border_subtle`; `border_strong` is derived by lightness shift |
| `[text].primary` / `.secondary` / `.tertiary` / `.success` / `.error` | `text_primary`, `text_muted`, `accent`, `success_fg`, `error_fg` |
| `[buffer].background` / `.background_title_bar` / `.background_text_input` / `.selection` | `surface_default`, `surface_elevated`, `input_bg` and `code_bg`, `selection_bg` |
| `[buffer].topic` / `.timestamp` / `.url` | `text_secondary`, `text_dim`, `text_link` |
| Derived in the translator | `surface_hover`, `surface_active`, `accent_hover`, `text_link_hover`, `accent_dim`, `border_strong`, `text_on_*`, `success_bg`, `error_bg`, `warning_*`, `info_*`, `shadow_color` |

Dark/light polarity is decided once, by `is_dark_background(general.background)`
— relative luminance below 0.5 means dark — and it drives the sign of every
lightness shift and the shadow alpha.

### The Two Compatibility Layers

`CSS_VARS` is the semantic layer (`--blog-*`). `ALIASES` is the backward
compatibility layer: 38 legacy variable names mapped onto the semantic
properties, used by `to_legacy_vars()` and therefore by every runtime
stylesheet.

| Alias family | Legacy names | Count |
|---|---|---|
| Surfaces and backgrounds | `bg`, `bg-surface`, `bg-elevated`, `bg-hover`, `navbar-bg`, `overlay-bg` | 6 |
| Borders | `border` | 1 |
| Text | `text`, `text-secondary`, `text-muted`, `text-dim`, `text-dim-strong`, `text-on-accent` | 6 |
| Accent and coral | `accent`, `accent-hover`, `accent-dim`, `coral`, `coral-dim` | 5 |
| Status colours | `green`, `green-dim`, `success-bg`, `red`, `red-dim`, `error-bg`, `yellow`, `yellow-dim`, `warning-fg`, `warning-bg`, `purple`, `purple-dim`, `amber`, `amber-dim`, `info-fg`, `info-bg` | 16 |
| Chrome and code | `noscript-bg`, `noscript-text`, `shadow-color`, `code-bg` | 4 |

Every alias target resolves to a property that exists in `CSS_VARS`; no alias
points at a missing token.

## The Registry

`ThemeRegistry` is the catalogue and the loader. It is constructed with an
optional `bundled_root`, an optional `external_root` and a `default_theme`
(`"Catppuccin Mocha"`).

### Catalogue discovery

`_rebuild_catalog()` runs once per process unless invalidated, and merges two
sources in that order:

| Source | Function | Notes |
|---|---|---|
| Bundled | `discover_bundled_package()` | Uses `importlib.resources.files("app.themes").joinpath("bundled")`; works from an installed wheel. `discover_bundled(root)` is the filesystem fallback used when an explicit `bundled_root` is passed (tests, tooling). |
| External | `discover_external(root)` | Reads a configured directory. Returns `[]` when the directory is missing or unreadable. |

Merging rules:

- An external file whose stem matches a bundled theme **overrides** it; the
  resulting descriptor sets `overrides_bundled=True` and its `source` becomes
  `ThemeSource.EXTERNAL`.
- A case collision between two different canonical names (for example
  `Foo.toml` and `foo.toml`) rejects **both** entries and logs a warning.
- Discovery skips dotfiles, non-`.toml` files, non-regular files, files outside
  the external root (symlink escape, checked with `_is_inside()`), and external
  files larger than 1 MiB (`_MAX_EXTERNAL_FILE_SIZE`).

Each catalogue entry is a `_CatalogEntry`, which pairs the public
`ThemeDescriptor` with the `ThemeFileInfo` (path, size, mtime, resource handle)
needed to read and re-stat the file.

### Resolution

`resolve(name)` normalises, aliases and matches:

1. `normalize_theme_name(name)` → `validate_theme_name()` rejects an empty
   name, path separators, `..` segments, absolute paths, control characters and
   names over 200 characters, then reduces the name to its file stem. A failure
   raises `ThemeValidationError`.
2. `_resolve_alias()` maps a legacy slug onto a canonical name through
   `_THEME_ALIASES` (for example `catppuccin-mocha` → `Catppuccin Mocha`).
3. The canonical name is looked up exactly, then case-insensitively. A miss
   returns `None`.

`list_themes()` returns the descriptors sorted by canonical name and logs the
refresh duration and theme count.

### Loading and invalidation

`load(name)` resolves the name, computes the cache key
`ThemeCache.make_key(canonical_name, source_type)` (`"bundled:Catppuccin Mocha"`),
and returns the cached `LoadedTheme` when the cached entry's `file_mtime` and
`file_size` still match the catalogue's current metadata. Otherwise it reads
the bytes, parses, translates, serialises and stores a new entry.

| Method | Effect |
|---|---|
| `invalidate()` | Clears every cache entry and drops the catalogue; the next access rebuilds it. |
| `invalidate(name)` | Normalises and alias-resolves the name, evicts matching cache entries via `invalidate_prefix()`, and drops the catalogue so it is rebuilt. |

A named invalidation therefore rebuilds the whole catalogue, not just the one
entry: the catalogue is a single dictionary and there is no per-theme catalogue
slice.

### Exception hierarchy

All four are `ValueError` subclasses and are raised by the registry, not the
parser:

| Exception | Raised when |
|---|---|
| `ThemeValidationError` | The theme name failed `validate_theme_name()` |
| `ThemeNotFoundError` | The name is valid but no catalogue entry matches |
| `ThemeParseFailure` | The file was read but is not valid Halloy TOML (wraps `ThemeParseError`) |
| `ThemeLoadError` | The file could not be read (`OSError`) |

`ThemeService._load_with_fallback()` catches exactly these three load-time
exceptions (`ThemeNotFoundError`, `ThemeParseFailure`, `ThemeLoadError`) and
falls back; `ThemeValidationError` is not caught there.

## The Cache

`ThemeCache` is a plain in-process dictionary of `ThemeCacheEntry` objects
keyed by `"{source_type}:{canonical_name}"`. A miss is a full read → parse →
translate → serialise cycle; a hit is a dictionary lookup plus a metadata
comparison, with no filesystem read and no parsing.

An entry stores everything a request needs: `halloy_theme`, `blog_theme`,
`css`, `is_dark`, `source_name`, `source_type`, `file_mtime`, `file_size`,
`translation_schema`, `diagnostics`, `css_vars`, `legacy_vars` and
`source_fingerprint`.

### Freshness

| Source | Fingerprint (`_compute_fingerprint()`) | Freshness check |
|---|---|---|
| Bundled | SHA-256 hex digest of the file content | Content-addressed; changes only with the bytes |
| External | `"{mtime}:{size}"` | Metadata-addressed; a change is visible only after the catalogue is rebuilt |

`ThemeCache.validate_entry(key, current_mtime, current_size, current_fingerprint)`
compares the stored `source_fingerprint` when a fingerprint is supplied and
falls back to the mtime/size pair when it is `None`.

The registry does not poll the filesystem. An external file that is edited,
added or deleted is invisible until `invalidate()` or `invalidate(name)` is
called — this is the documented freshness boundary, not an oversight.

### Multi-Worker Caveat

`ThemeService`, `ThemeRegistry` and `ThemeCache` are all process-local. Each
WSGI worker, each Celery worker and each CLI invocation owns an independent
catalogue and cache. Invalidating on one worker leaves every other worker's
cache untouched; there is no IPC, shared memory or message bus. Propagating a
theme change across a deployment means restarting the processes.

## Accessibility Validation

`app/themes/diagnostics.py` holds two related but distinct mechanisms.

### Translation-Time Warnings

`check_blog_theme_contrast(blog_theme)` runs inside `translate_halloy_theme()`
and returns `list[ContrastWarning]` — token, description, foreground,
background, ratio and WCAG level. These warnings ride along in
`TranslationDiagnostics.warnings` and are surfaced by the CLI and the
accessibility report. They are informational: a theme with contrast warnings
still loads and still renders.

### Policy Validation

`validate_theme_accessibility(blog_theme, theme_name, filename_dark)` returns a
`ThemeAccessibilityReport` built from the `_CONTRAST_PAIRS` table — 29 token
pairs (18 mandatory, 11 advisory), each with a required ratio, a severity and a
remediation hint. Findings
are `AccessibilityFinding` records carrying the token, the two colours, the
measured and required ratios, the WCAG level, the severity, the remediation
text and, when applicable, an exception reason.

| Severity | Meaning |
|---|---|
| `Severity.MANDATORY` | A real accessibility failure. Blocks "recommended" classification. |
| `Severity.ADVISORY` | A deviation that does not impair comprehension or operation. |

### Exception Manifest

`app/themes/ACCESSIBILITY_EXCEPTIONS.json` (schema version 2) records the
documented exceptions per theme and pair. `is_expected_exception(theme_name,
description)` looks a pair up in the manifest and returns the recorded reason.
A mandatory finding with a reason is "expected"; without one it is an
unexpected failure.

`ThemeAccessibilityReport` separates the two sets through
`mandatory_failures`, `unexpected_mandatory_failures`, `expected_exceptions`
and `advisory_warnings`, and exposes `passed` (no mandatory failures) and
`passed_with_exceptions` (no *unexpected* mandatory failures).

`classify_theme_eligibility()` maps a report onto the three tiers, and
`classify_catalog_eligibility()` aggregates a whole catalogue:

| Tier | Gate |
|---|---|
| `recommended` | Zero mandatory failures and zero expected exceptions |
| `compatible-with-exceptions` | No unexpected mandatory failures |
| `experimental` | At least one unexpected mandatory failure |

The manifest's current summary for the bundled catalogue: 50 themes, 45 with
exceptions, 5 recommended, 33 compatible-with-exceptions, 12 experimental.

### The Automated Policy Gate

`scripts/theme_accessibility_report.py` validates a catalogue against this
policy, and the `theme-policy` CI job runs it in strict mode:

```bash
python scripts/theme_accessibility_report.py --strict
```

Strict mode exits non-zero when either of these holds:

- A theme's computed eligibility is **worse** than the class the manifest
  declares for it. That covers both a theme with undocumented mandatory
  failures and a theme that has regressed below a previously recorded class.
- A theme's classification disagrees with the darkness implied by its filename.

`find_policy_violations()` implements the comparison; the classes are ranked
`recommended` < `compatible-with-exceptions` < `experimental`. A theme with no
manifest entry is treated as `recommended`, so any mandatory failure it has is
a violation.

Running without `--strict` prints the same report and always exits 0.

### How a Failing Theme Surfaces

Accessibility findings are **not** load failures. A theme that fails a
mandatory contrast check still loads, still renders and is still selectable —
the failure is reported by the CLI (`themes accessibility`) and by
`scripts/theme_accessibility_report.py`, not by the request path.

The emergency fallback is for *load* failures only. `ThemeRegistry.get_fallback()`
walks a three-step chain:

```
configured theme → registry default ("Catppuccin Mocha") → emergency-default
```

Each step catches `ThemeNotFoundError`, `ThemeParseFailure` and
`ThemeLoadError` before advancing. If all three fail, the registry logs
`fallback activation: …`, increments `fallback_count`, and returns a
`LoadedTheme` built from `EMERGENCY_DEFAULT` with `status="fallback"` and
`canonical_name="emergency-default"`.

`EMERGENCY_DEFAULT` in `app/themes/model.py` is the hardcoded, GitHub-dark-like
palette used as the last resort. `ThemeService._emergency_context()` uses it
when the settings read itself fails, and `app/context_processors.py`
`_get_cached_settings()` uses it when the theme service is unavailable.

## Runtime Integration

### The Service

`ThemeService` is the per-process owner of the registry.

| Symbol | Role |
|---|---|
| `init_theme_service(default_dark, default_light, default_scheme, external_root, app)` | Creates the service and, when `app` is given, stores it at `app.extensions["theme_service"]` |
| `get_theme_service()` | Returns `current_app.extensions["theme_service"]`, falling back to a fresh `ThemeService()` outside an application context |
| `ThemeService.get_context()` | Returns the template context dict, cached for `_SETTINGS_CACHE_TTL` (300 s) |
| `ThemeService.invalidate_settings_cache()` | Drops the settings cache |
| `ThemeService.invalidate_registry(name=None)` | Delegates to `ThemeRegistry.invalidate()` |
| `ThemeService.refresh_registry()` | Atomically replaces the registry under `_registry_lock` |

The app factory calls `init_theme_service()` during startup with the
configuration values `cfg.themes.default_dark`, `cfg.themes.default_light`,
`cfg.themes.default_scheme` and `external_root = Path(cfg.themes.external_dir)
if cfg.themes.external_dir else None`. The external directory therefore comes
from `THEME_EXTERNAL_DIR` or the `[themes]` section of `config.toml`, and
external themes are disabled when it is empty.

### Settings Resolution

`SiteSettings` stores `theme_dark_name`, `theme_light_name` and
`theme_default_scheme`. `get_effective_theme_names()` in
`app/services/theme_settings.py` applies the configuration defaults, and
`validate_theme_settings()` then resolves the names against the registry:
an unknown name falls back to `"Catppuccin Mocha"` / `"Catppuccin Latte"`, and
an invalid scheme falls back to `"system"`.

### The Context Processor

`register_context_processors()` in `app/context_processors.py` registers
`inject_theme`, which returns `get_theme_service().get_context()`. If the theme
service raises, it logs a warning and falls back to `_get_cached_settings()`,
which renders `EMERGENCY_DEFAULT` through `to_legacy_vars()`.

The context dict contains:

| Key | Contents |
|---|---|
| `theme_dark_name`, `theme_light_name`, `theme_default_scheme` | The resolved names and the scheme (`system`, `dark`, `light`) |
| `theme_dark_vars`, `theme_light_vars` | The **legacy alias** dictionaries, produced by `to_legacy_vars()` |
| `theme_dark_css`, `theme_light_css` | The same values serialised as CSS declaration lines by `to_legacy_css()` |
| `theme_vars` | The dark alias dictionary under its historical name |
| `theme_warnings` | Warning strings collected from the two descriptors |
| `syntax_theme`, `custom_css_enabled`, `custom_css`, `logo_text` | Site settings the templates need |

### Into the Templates

`base.html`, `admin/base.html` and `admin/login_base.html` each emit an inline
`<style>` block:

```html
:root,
[data-color-scheme="dark"] { {% for key, value in theme_dark_vars.items() %}--{{ key }}: {{ value }};{% endfor %} }

[data-color-scheme="light"] { {% for key, value in theme_light_vars.items() %}--{{ key }}: {{ value }};{% endfor %} }
```

Because the emitted names are the legacy aliases (`--bg`, `--text`,
`--accent`, …), the stylesheets in `app/static/css/` consume those names.
`app/static/css/` contains 725 `var(--…)` references and **zero**
`var(--blog-*)` references: the semantic `--blog-*` layer is produced for
inspection and tooling (`LoadedTheme.css`, `themes inspect --css`), while the
runtime consumes the alias layer.

The active scheme is chosen by an inline bootstrap script in `base.html`: it
reads `theme_default_scheme`, honours a stored `blog-color-scheme` value in
`localStorage`, resolves `system` through
`prefers-color-scheme: dark`, and sets the `data-color-scheme` attribute on the
document element.

## The Theme / Appearance Boundary

| Concern | Owner | Mechanism |
|---|---|---|
| Colour | `app/themes/` | `--bg`, `--text`, `--accent`, … |
| Typeface | `app/appearance/` | `--font-sans`, `--font-mono` |
| Backdrop | `app/appearance/` | `--backdrop-image`, `--backdrop-tint` |

Both layers follow the same shape — registry, service, settings, per-process
cache — so there is one mechanism to learn rather than two. The appearance
service derives its backdrop tint from the theme's `bg` and `accent`, so the
two layers compose without the theme knowing that backdrops exist.

## Operator Surface

Both CLIs expose the same operations, backed by `app/services/operations/themes.py`:

| Command | Purpose |
|---|---|
| `flask themes list` / `devlog themes list` | Catalogue listing, filterable by `--source` |
| `flask themes validate <path>` | Validate a file or a registered name |
| `flask themes inspect <name>` | Full detail for one theme, including findings and CSS variables |
| `flask themes refresh` | Rebuild the registry |
| `flask themes paths` | Show bundled and external theme locations |
| `flask themes accessibility` | Run the accessibility policy over a source, with `--strict` |

## Notes and Gotchas

- **Token and alias counts in the surrounding docs were stale, and have been
  corrected.** `AGENTS.md` and `docs/themes/blog-theme-contract.md` used to
  describe the model as "44 semantic tokens + 6 RGBA fields" and "26 aliases".
  The code has 50 fields (41 `RGB` + 9 `RGBA`), 50 entries in `CSS_VARS`, and 38
  entries in `ALIASES`. The contract's own Section A table lists all 50 tokens
  even though its summary line said 44, and its Section E lists 27 alias keys
  including a `name` metadata key that `ALIASES` no longer contains; the code
  instead adds 12 aliases the contract does not mention (`code-bg`, `error-bg`,
  `info-bg`, `info-fg`, `navbar-bg`, `overlay-bg`, `shadow-color`, `success-bg`,
  `text-on-accent`, `warning-bg`, `warning-fg`, `yellow-dim`). Both documents now
  report the code values.

- **The bundled Catppuccin Latte link colour failed WCAG AA.** `buffer.url`
  maps to the `text_link` token, and the upstream Catppuccin blue `#1E66F5`
  reaches only 3.71:1 against the theme's own page background and 4.04:1 against
  its surface background, against a mandatory requirement of 4.5:1 for link
  text. Because Catppuccin Latte is the default *light* theme, the project
  policy does not allow the failure to be documented as a manifest exception —
  `tests/themes/test_accessibility.py` asserts that the default themes carry no
  `mandatory_defect` entries. The token is therefore `#0A52E1` in both
  `themes/Catppuccin Latte.toml` and `app/themes/bundled/Catppuccin Latte.toml`
  — the same hue as upstream, darkened to 4.80:1 on the page background and
  5.22:1 on the surface background. `buffer.url` feeds nothing else, so the
  change is confined to link text. Catppuccin Mocha, the default dark theme,
  was already compliant at 7.79:1.

- **`shift_lightness()` diverges from a reference HSL conversion for dark
  colours.** In `app/themes/colors.py`, `_hsl_to_rgb()` computes `q` with the
  same expression in both branches of the `lightness < 0.5` test, so the
  light-colour branch is used for dark colours too. For a surface of
  `#161b22` shifted by `+0.06` the function returns `#002459` where a
  reference HSL implementation returns `#222a35`; `#161b22` shifted by `+0.12`
  returns `#113465` instead of `#2e3947`. The affected derived tokens are
  `surface_hover`, `surface_active`, `border_strong` and, when the accent is
  itself dark, `accent_hover` / `text_link_hover`. The existing colour tests
  only exercise grey, white and black, which all take the unaffected path, so
  the defect is not covered.

- **The emergency fallback's palette and its emitted CSS are not the same
  object.** `get_fallback()` sets `LoadedTheme.blog_theme` to
  `EMERGENCY_DEFAULT` but derives `css`, `css_vars` and `legacy_vars` from
  `translate_halloy_theme(_emergency_halloy_theme())`. The two disagree on 17
  of the 50 fields (for example `text_muted`, `text_on_accent`,
  `text_on_warning`, `text_on_info`, `code_bg` and every `*_bg` state colour),
  so the values that reach the browser are the translated ones, not
  `EMERGENCY_DEFAULT`.

- **`theme_warnings` is never populated.** `ThemeService._build_for_themes()`
  builds the warning list from `descriptor.warnings`, and every descriptor is
  created by `_make_descriptor()` with `warnings=()`. The contrast warnings
  that actually matter live in `LoadedTheme.diagnostics.warnings`.

- **`ThemeDescriptor.is_dark` is always `None`.** The descriptor factory sets
  `is_dark=None`; the computed classification is on `LoadedTheme.is_dark`.
  Catalogue listings therefore report `null` for dark/light.

- **`ThemeCache.validate_entry()` is not on the load path.** `ThemeRegistry.load()`
  compares `file_mtime` and `file_size` inline and never calls
  `validate_entry()`. The `source_fingerprint` is stored on every entry but is
  only consulted through that method, so in practice the SHA-256 fingerprint
  is recorded rather than compared.

- **The repository-root `themes/` directory is the authoring catalogue, not the
  runtime external directory.** It holds the same 50 `.toml` files as
  `app/themes/bundled/` and they are currently byte-identical, but the two
  trees are used for different things: `scripts/theme_inventory.py` defaults to
  `themes`, `scripts/theme_accessibility_report.py` reads
  `<repo>/themes`, and the runtime loads `app/themes/bundled/` through
  `importlib.resources`. The runtime external directory is a different path
  entirely — `THEME_EXTERNAL_DIR` or `[themes] external_dir`, empty by default.
  `MANIFEST.in` and `pyproject.toml` package only `app/themes/bundled`, so the
  root directory is not shipped. `docs/themes/blog-theme-contract.md` states
  that a CI check verifies the two trees are byte-identical; no such check
  exists — the `theme-package-verification` CI job asserts the *built package*
  contains 50 themes, that the registry lists 50, and that the manifest and
  attribution file are present, but it never compares the two directories.

- **A malformed theme file is a warning, not a crash.** A bundled theme that
  fails to parse is logged at `error` level, an external one at `warning`, and
  both raise `ThemeParseFailure`, which the service converts into a fallback
  to the default theme and then to the emergency palette.

- **A deleted theme stays in the catalogue until invalidation.** The catalogue
  records file metadata at discovery time, so a file removed from the external
  directory is still listed until `invalidate()` runs; after that
  `resolve()` returns `None` and loading falls back.

- **Theme names are validated against path traversal.** `validate_theme_name()`
  rejects separators, `..` segments, absolute paths, control characters and
  names longer than 200 characters, and `discover_external()` additionally
  refuses files that resolve outside the external root.

- **The `name` key filter is vestigial.** `to_legacy_css()` and the three
  templates skip a key called `name`, but `ALIASES` contains no such key —
  the legacy `name` metadata entry was removed with the rest of the preset
  system.

## See Also

- [App Factory](app-factory.md) - Where `init_theme_service()` is called at startup
- [Configuration](configuration.md) - The `[themes]` config section and `THEME_EXTERNAL_DIR`
- [Models](models.md) - `SiteSettings` columns for the theme names and scheme
- [Appearance Layer](../frontend/appearance.md) - The sibling layer that owns typeface and backdrop
- [Static Assets](../frontend/static-assets.md) - The CSS that consumes the emitted tokens
- [Templates](../frontend/templates.md) - Where `theme_dark_vars` and `theme_light_vars` are rendered
- [BlogTheme Semantic Token Contract](../../docs/themes/blog-theme-contract.md) - Token-by-token contract for the model
- [Supported Halloy Theme Schema](../../docs/themes/supported-schema.md) - The parser input contract
- [Cache Freshness Contract](../../docs/themes/cache-contract.md) - Invalidation semantics in detail
- [Accessibility Policy](../../docs/themes/accessibility-policy.md) - The exception classes and eligibility tiers
- [Theme Operator Guide](../../docs/themes/operator-guide.md) - Installing and configuring external themes
