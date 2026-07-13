# Halloy Theme Phase 01 — Catalog Inventory and Semantic Token Contract

## Objective

Establish the authoritative input catalog, supported Halloy subset, frontend color-token surface, packaging direction, and compatibility constraints before runtime code changes begin.

This phase is intentionally investigative but must produce committed, testable artifacts. Later phases should not invent token mappings or packaging locations independently.

## Baseline to inspect

Primary inputs:

- top-level `themes/*.toml` catalog;
- `app/static/css/base.css`;
- `app/static/css/critical.css`;
- `app/static/css/layout.css`;
- `app/static/css/public.css`;
- `app/static/css/forms.css`;
- `app/static/css/admin.css`;
- `app/static/js/shared/dark-mode.js`;
- `app/templates/base.html` and admin base templates;
- `SiteSettings`, `THEME_PRESETS`, and theme-related admin forms/routes;
- packaging files, Docker files, and deployment documentation.

## Required implementation work

### 1. Build a deterministic catalog inventory

Add a development/test utility that scans only the checked-in top-level `themes/` directory and records:

- filename and stem;
- file size;
- top-level TOML sections;
- missing expected sections;
- color formats used;
- names containing spaces, parentheses, mixed case, Unicode, or other special characters;
- duplicate names under case-insensitive comparison;
- invalid TOML;
- files that differ only by case or punctuation;
- attribution or license metadata if present.

The utility should not become the final runtime registry. It exists to characterize source material and can live under `scripts/`, `tools/`, or tests according to repository convention.

Add a test asserting that every checked-in theme is included in the inventory and that unexpected invalid TOML fails CI with a useful filename.

### 2. Document the supported Halloy schema subset

Inspect all catalog files and define which fields the first implementation supports. Expected sections include:

- `[general]`;
- `[text]`;
- `[buffer]`;
- `[buttons.*]`.

Document optional fields, defaults, ignored sections, accepted color representations, and behavior for unknown fields. The contract should explicitly state that extra Halloy fields are tolerated but not necessarily translated.

### 3. Audit frontend theme-sensitive literals

Search all CSS, templates, JavaScript-generated markup, SVG, and server-rendered HTML for literal colors and classify each occurrence:

- replace with a semantic theme token;
- retain as an invariant brand or structural value;
- syntax-highlighting-only;
- temporary compatibility value;
- false positive.

Do not perform broad CSS replacement in this phase. Produce a committed audit table or structured document that later phases can execute against.

The audit must include first-paint behavior in `critical.css`, because a theme that applies only after deferred styles load will cause a visible flash.

### 4. Define `BlogTheme`

Create or document the authoritative semantic token contract. At minimum include:

- page and surface backgrounds;
- elevated and hover surfaces;
- borders and dividers;
- primary, secondary, muted, and dim text;
- text rendered on accent/state fills;
- accent, link, hover, and focus colors;
- success, error, warning, and info colors plus subtle backgrounds;
- input, code, selection, overlay, navbar, and shadow colors.

Preserve compatibility aliases for existing CSS names only where necessary. The target contract should favor semantic names over hue names such as `green` or `purple`.

For every token, record:

- semantic purpose;
- current CSS variable or source;
- Halloy source candidate;
- whether it is direct or derived;
- required contrast relationship;
- fallback value.

### 5. Decide packaged-resource layout

Confirm the final bundled theme location. Preferred shape:

```text
app/themes/
  bundled/
    *.toml
```

The phase must document how the top-level `themes/` directory relates to packaged resources. Preferred policy:

- top-level `themes/` is the source catalog or development copy;
- bundled resources live inside the Python package;
- external operator themes live outside the package at runtime;
- installed applications never depend on the repository root.

Check current `pyproject.toml`, `MANIFEST.in`, Docker configuration, and package conventions before finalizing the exact path.

### 6. Define compatibility rules

Record migration mappings for existing presets:

- `github-dark`;
- `github-light`;
- `solarized-dark`;
- `monokai`.

Determine whether equivalent Halloy files exist and whether exact visual preservation is possible. Record any expected visual differences.

Also confirm that Prism syntax themes and custom CSS remain separate systems.

## Files expected to change

Likely additions or changes:

- `plans/` or `docs/architecture/` theme contract document;
- `scripts/` or `tests/` inventory utility;
- catalog inventory test;
- optional machine-readable token matrix fixture.

Avoid adding runtime parser/registry code in this phase unless a tiny helper is necessary for inventory generation.

## Testing requirements

- Every `themes/*.toml` file is discovered exactly once.
- Invalid TOML produces a filename-specific failure.
- Case-insensitive collisions are detected.
- The token contract contains every currently emitted `theme_vars` key.
- The hardcoded CSS color audit is reproducible rather than a one-time manual note.

## Acceptance criteria

- The exact number and shape of source themes is documented from repository data.
- The supported Halloy subset and ignored fields are explicit.
- Every theme-sensitive frontend literal is classified.
- `BlogTheme` has a complete token matrix with fallback and contrast intent.
- The packaged-resource location and top-level catalog policy are decided.
- Legacy preset mappings are documented.
- No runtime behavior changes and the existing test suite remains green.

## Handoff notes

Phase 02 should consume the supported-schema document directly. Phase 03 should consume the token matrix directly. If either later phase needs an unmapped field or token, update the contract rather than adding an undocumented special case.
