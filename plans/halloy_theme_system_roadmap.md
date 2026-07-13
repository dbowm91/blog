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

Implement typed Halloy models and deterministic color utilities. Parsing should tolerate extra Halloy fields, provide documented defaults for optional fields, reject invalid structures and colors, and distinguish parse failures from resolution failures.

Deliverables:

- Halloy parser module;
- color conversion, mixing, luminance, and contrast helpers;
- representative fixtures;
- catalog-wide parse tests.

### Phase 03: blog translation layer

Implement `BlogTheme`, Halloy-to-blog translation, CSS serialization, dark/light classification, and translation warnings. Generated colors must cover all existing CSS tokens and new semantic tokens needed to eliminate hardcoded foreground/background assumptions.

Deliverables:

- deterministic translator;
- complete CSS variable output;
- contrast diagnostics;
- representative dark/light/unusual theme tests.

## Milestone B — Registry and packaged resources

### Phase 04: safe registry and external override model

Implement theme listing, safe name validation, path containment, bundled-resource lookup, external directory precedence, cache keys, cache invalidation, and fallback semantics. Reject path traversal, absolute paths, separators, and symlink escapes.

Deliverables:

- registry API;
- safe resolver;
- bundled plus external catalog merging;
- user override precedence;
- caching and resilience tests.

### Phase 05: package the Halloy catalog

Move or mirror the approved top-level theme collection into the Python package, update package-data and container configuration, preserve attribution, and add a wheel-install smoke test proving theme enumeration and loading outside a source checkout.

Deliverables:

- packaged resources;
- package metadata updates;
- wheel/container verification;
- source-to-bundled catalog consistency check.

## Milestone C — Runtime integration and migration

### Phase 06: configuration and database migration

Expand or replace `SiteSettings.theme_preset` with sufficiently long named-theme fields, migrate legacy names, add dark/light theme pair settings, add an external directory configuration key, and validate configured names with safe fallbacks.

### Phase 07: Flask and Jinja integration

Make the registry the sole runtime palette source. Centralize theme context creation, preserve CSP nonces, emit generated variables before custom CSS, and remove route-level duplicate loading.

### Phase 08: visitor color-scheme behavior

Replace the ambiguous local-storage key with `blog-color-scheme`, support `system`/`dark`/`light`, and apply the selected scheme before first paint using a nonce-bearing bootstrap. Replace static `[data-theme="light"]` palette ownership with generated scoped variables.

## Milestone D — Frontend token completion

### Phase 09: CSS and generated-markup audit

Replace remaining theme-sensitive literals in public, admin, form, critical, responsive, modal, toast, badge, code, and SVG styling. Retain only documented invariant colors.

### Phase 10: admin selection and preview

Generate theme selectors from the registry, group bundled and external themes, identify overrides, show translation/contrast warnings, support non-persistent preview, and provide a CSRF-protected refresh action.

### Phase 11: operator CLI and external-theme workflow

Add commands such as `flask themes list`, `validate`, `inspect`, and `refresh`. Document external theme installation, override behavior, validation output, and deployment paths.

## Milestone E — Hardening and release closure

### Phase 12: accessibility validation

Run WCAG contrast checks over every bundled theme for primary text, muted text, links, accent foregrounds, forms, states, and focus rings. Bundled themes must satisfy mandatory thresholds; external themes may load with actionable warnings unless strict mode is enabled.

### Phase 13: performance and reliability

Cache parsed and translated themes, avoid filesystem reads on warm requests, isolate malformed external files, benchmark catalog listing and rendering, and verify cache invalidation after external edits.

### Phase 14: documentation and legacy removal

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
