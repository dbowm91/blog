# Halloy-Compatible Theme System Roadmap

## Purpose

Replace the blog's manually maintained theme preset system with a Halloy-compatible theme subsystem. The finished system must package the Halloy themes currently present in the repository, translate Halloy TOML palettes into the blog's semantic CSS variables, and allow operators to add or override themes from an external directory without modifying application code.

This roadmap is an implementation handoff. Agents should work phase-by-phase, preserve existing behavior unless a phase explicitly changes it, and avoid coupling theme identity to syntax highlighting or arbitrary custom CSS.

## Current repository baseline

The repository already contains most of the frontend foundation needed for this work:

- `app/static/css/base.css` defines semantic CSS custom properties such as `--bg`, `--bg-surface`, `--text`, `--accent`, and status colors.
- `app/templates/base.html` injects `theme_vars` in a CSP-nonced inline style block.
- `SiteSettings` persists `theme_preset`, `syntax_theme`, custom CSS enablement, and custom CSS.
- `THEME_PRESETS` provides a small hardcoded palette catalog.
- `app/static/js/shared/dark-mode.js` implements a visitor dark/light preference with local storage and `data-theme`.
- the repository now contains a top-level `themes/` directory with 50 Halloy theme files.

The migration is therefore not a frontend rewrite. It is a replacement of the palette source, discovery model, persistence contract, and dark/light coordination.

## Target architecture

```text
packaged Halloy TOML themes + external operator theme directory
                              |
                    safe theme registry
                              |
                      Halloy parser/model
                              |
                  blog translation layer
                              |
                   semantic BlogTheme tokens
                              |
                 CSP-nonced CSS custom properties
                              |
                    existing CSS components
```

Bundled themes must be loaded through `importlib.resources` so wheels and installed deployments do not depend on the repository root. An optional external themes directory extends the bundled catalog. An external theme with the same name as a bundled theme takes precedence.

## Core design decisions

### Theme identity versus color scheme

A named theme and a dark/light preference are different concepts. The initial production model should use an administrator-configured Halloy theme pair:

- `dark_theme`
- `light_theme`
- visitor preference: `system`, `dark`, or `light`

This retains the existing visitor toggle while allowing arbitrary Halloy palettes. The browser must not store a Halloy filename as an unrestricted filesystem selector.

### Syntax highlighting

Prism syntax themes remain independent. Halloy files do not define a complete syntax palette. Existing `syntax_theme` behavior should continue unchanged.

### Custom CSS

Custom CSS remains a separate privileged administrator feature. Generated theme CSS must be emitted before custom CSS so intentional operator overrides continue to work.

### Failure policy

Theme errors must not take down public pages. Resolution order is:

1. requested configured theme;
2. configured default theme;
3. known-good bundled fallback;
4. hardcoded emergency `BlogTheme`.

Malformed external files are isolated and reported through logs, admin metadata, and CLI validation.

## Milestone A — Theme contract and parser foundation

### Phase 01: inventory and semantic token contract

Inspect all 50 files under `themes/`, document schema variation, validate filenames, identify alpha colors and missing fields, and audit the frontend for hardcoded theme-sensitive colors. Define the authoritative `BlogTheme` token contract and decide the packaged resource path.

Deliverables:

- catalog inventory and compatibility findings;
- semantic token matrix;
- bundled-resource layout decision;
- licensing/attribution notes;
- tests or scripts that enumerate and classify every source theme.

### Phase 02: Halloy parser and color primitives

**Status: Complete (parser + color primitives)**

Implement typed Halloy models and deterministic color utilities. Parsing should tolerate extra Halloy fields, provide documented defaults for optional fields, reject invalid structures and colors, and distinguish parse failures from resolution failures.

Deliverables:

- Halloy parser module;
- color conversion, mixing, luminance, and contrast helpers;
- representative fixtures;
- catalog-wide parse tests.

### Phase 03: blog translation layer

**Status: Complete (BlogTheme model + translator + diagnostics + CSS serialization)**

Implement `BlogTheme`, Halloy-to-blog translation, CSS serialization, dark/light classification, and translation warnings. Generated colors must cover all existing CSS tokens and new semantic tokens needed to eliminate hardcoded foreground/background assumptions.

Deliverables:

- `app/themes/model.py` — `BlogTheme` frozen dataclass (50 fields), `CSS_VARS`, `ALIASES`, `EMERGENCY_DEFAULT`
- `app/themes/translate.py` — `translate_halloy_theme()`, `to_css_variables()`, `to_theme_vars()`, `to_legacy_vars()`
- `app/themes/diagnostics.py` — `check_blog_theme_contrast()`, `ContrastWarning`, `TranslationDiagnostics`
- `tests/themes/test_translation.py` — 91 tests covering translation, derivations, foreground selection, catalog-wide
- `tests/themes/test_theme_css.py` — 78 tests covering CSS serialization, ordering, selectors, legacy vars
- 373 total theme tests passing; all 50 catalog themes translate and serialize deterministically

## Milestone B — Registry and packaged resources

### Phase 04: safe registry and external override model

**Status: Complete (corrective closure + small closure pass complete)**

Implement theme listing, safe name validation, path containment, bundled-resource lookup, external directory precedence, cache keys, cache invalidation, and fallback semantics. Reject path traversal, absolute paths, separators, and symlink escapes.

Corrective closure (plan: `plans/halloy_theme_phase_04_05_corrective_closure.md`) addressed: catalog entry pairing (`_CatalogEntry` binds `ThemeDescriptor` + `ThemeFileInfo`), cache freshness validation against current source state, named invalidation rebuilding catalog deterministically, canonical-name normalization with case-insensitive lookup, `importlib.resources` as default bundled discovery, and structured exceptions (`ThemeNotFoundError`, `ThemeParseFailure`, `ThemeLoadError`, `ThemeValidationError`).

Small closure pass (plan: `plans/halloy_theme_phase_04_05_small_closure_pass.md`) completed: explicit cache freshness contract (external theme changes require explicit `invalidate()` or `invalidate(name)`), SHA-256 fingerprinting for bundled resources (`_compute_fingerprint()` uses `hashlib.sha256()`), CI gate for theme package verification (`theme-package-verification` job builds wheel/sdist and runs `scripts/verify_theme_package.py`), comprehensive invalidation tests.

Deliverables:

- `app/themes/resources.py` — `ThemeSource`, `ThemeFileInfo`, `ThemeResource` protocol (`read_bytes()`), `validate_theme_name()`, `discover_bundled()`, `discover_external()`
- `app/themes/cache.py` — `ThemeCache` in-process cache, `ThemeCacheEntry` with current-source-state validation
- `app/themes/registry.py` — `ThemeRegistry`, `ThemeDescriptor`, `LoadedTheme`, `_CatalogEntry` internal pairing
- `tests/themes/test_registry.py` — 50 tests: bundled listing, external overrides, invalidation, fallback, cache behavior
- `tests/themes/test_theme_resolution_security.py` — 44 tests: name validation, symlink escape, traversal attacks, encoded separators
- 94 new tests passing; all 467 theme tests passing

### Phase 05: package the Halloy catalog

**Status: Complete (corrective closure + small closure pass complete)**

Move or mirror the approved top-level theme collection into the Python package, update package-data and container configuration, preserve attribution, and add a wheel-install smoke test proving theme enumeration and loading outside a source checkout.

Corrective closure (plan: `plans/halloy_theme_phase_04_05_corrective_closure.md`) validated: wheel build and isolated install, sdist content verification, `importlib.resources`-based discovery as default path, and external theme override against installed bundled resources.

Small closure pass (plan: `plans/halloy_theme_phase_04_05_small_closure_pass.md`) validated: `TestWheelAndSdistCatalogContents` proves package contents match source catalog, CI `theme-package-verification` job gates on wheel/sdist correctness.

Deliverables:

- `app/themes/bundled/` — packaged Halloy theme files with `__init__.py`, `catalog_manifest.json`, `ATTRIBUTION.md`
- `pyproject.toml` — `[tool.setuptools.package-data]` for `app.themes.bundled`
- `MANIFEST.in` — sdist inclusion of bundled theme files
- wheel and sdist verification

## Milestone C — Runtime integration and migration

### Phase 06: configuration and database migration

Expand or replace `SiteSettings.theme_preset` with sufficiently long named-theme fields, migrate legacy names, add dark/light theme pair settings, add an external directory configuration key, and validate configured names with safe fallbacks.

### Phase 07: Flask and Jinja integration

**Status: Complete (centralized ThemeService, dual-scheme CSS emission, context processor overhaul)**

Make the registry the sole runtime palette source. Centralize theme context creation, preserve CSP nonces, emit generated variables before custom CSS, and remove route-level duplicate loading.

### Phase 08: visitor color-scheme behavior

**Status: Complete (3-state scheme, bootstrap script, CSS selector migration, static light palette removed)**

Replace the ambiguous local-storage key with `blog-color-scheme`, support `system`/`dark`/`light`, and apply the selected scheme before first paint using a nonce-bearing bootstrap. Replace static `[data-theme="light"]` palette ownership with generated scoped variables. The static 23-literal `[data-color-scheme="light"]` palette block in `base.css` has been removed; light-theme variables are now provided entirely by inline `<style>` from Halloy themes.

## Milestone D — Frontend token completion

### Phase 09: CSS and generated-markup audit

**Status: Complete (legacy aliases added, hardcoded literals replaced with CSS custom properties)**

Replace remaining theme-sensitive literals in public, admin, form, critical, responsive, modal, toast, badge, code, and SVG styling. Retain only documented invariant colors.

### Phase 10: admin selection and preview

**Status: Complete (registry-based theme selector, dark/light/scheme selection, refresh action)**

Generate theme selectors from the registry, group bundled and external themes, identify overrides, show translation/contrast warnings, support non-persistent preview, and provide a CSRF-protected refresh action.

### Phase 11: operator CLI and external-theme workflow

**Status: Complete (flask themes list/validate/inspect/refresh commands)**

Add commands such as `flask themes list`, `validate`, `inspect`, and `refresh`. Document external theme installation, override behavior, validation output, and deployment paths.

## Milestone E — Hardening and release closure

### Phase 12: accessibility validation

**Status: Complete (flask themes accessibility command, WCAG contrast checks over all bundled themes)**

Run WCAG contrast checks over every bundled theme for primary text, muted text, links, accent foregrounds, forms, states, and focus rings. Bundled themes must satisfy mandatory thresholds; external themes may load with actionable warnings unless strict mode is enabled.

### Phase 13: performance and reliability

**Status: Complete (theme benchmarks, cache validation, malformed file isolation tests)**

Cache parsed and translated themes, avoid filesystem reads on warm requests, isolate malformed external files, benchmark catalog listing and rendering, and verify cache invalidation after external edits.

### Phase 14: documentation and legacy removal

**Status: Complete (documentation updated, THEME_PRESETS marked deprecated)**

Update configuration, architecture, deployment, theme-author, attribution, and migration documentation. Remove `THEME_PRESETS`, static option lists, obsolete light-palette authority, and stale references after compatibility is proven.

## Cross-cutting security requirements

- Theme names use a strict allowlist and may not contain path separators or `..`.
- Resolved external paths must remain inside the configured directory.
- Do not recursively scan external directories.
- Accept only `.toml` regular files under a documented size limit.
- Validate all emitted CSS color values; never mark raw theme file text as safe.
- Do not weaken CSP or require `unsafe-inline`.
- Public request parameters may select only names already present in the registry.
- Public errors and HTML must not expose absolute filesystem paths.

## Testing strategy

Each phase must add tests at its boundary. The final suite must include:

- parser and color utility unit tests;
- catalog-wide parse and translation tests;
- bundled/external resolution and precedence tests;
- traversal and symlink-escape tests;
- Flask/Jinja/CSP integration tests;
- database migration tests;
- wheel-install and container-resource checks;
- browser coverage for no-flash scheme initialization;
- accessibility checks over all bundled themes;
- fallback and malformed-file resilience tests.

## Recommended implementation order

1. Phase 01 token and catalog contract.
2. Phase 02 parser and color utilities.
3. Phase 03 translator and CSS serialization.
4. Phase 04 registry and external overrides.
5. Phase 05 packaging.
6. Phase 06 persistence/config migration.
7. Phase 07 server integration.
8. Phase 08 visitor scheme behavior.
9. Phase 09 CSS completion.
10. Phase 10 admin UX.
11. Phase 11 CLI/operator workflow.
12. Phases 12–14 hardening, documentation, and cleanup.

Do not begin with the admin selector. The parser, semantic contract, registry, and packaged resource behavior must stabilize first.

## Definition of done

This line of work is complete when all approved Halloy themes are included in wheel and container artifacts; bundled themes load without relying on the repository root; operators can add Halloy-compatible themes through a configured external directory; same-name external themes safely override bundled themes; Halloy colors are translated into a complete blog-specific semantic token set; public and admin pages use one centralized theme service; legacy preset names migrate; dark/light visitor preference works with administrator-selected Halloy theme pairs without first-paint flashing; syntax highlighting and custom CSS retain their separate behavior; malformed themes fall back without public 500 errors; traversal and CSS injection are prevented; all bundled themes pass parser, translation, packaging, and mandatory accessibility checks; and the hardcoded preset dictionary is no longer a runtime authority.
