# Halloy Theme Phase 03 — Blog Translation Layer

## Objective

Translate normalized Halloy themes into a complete, blog-specific semantic palette and deterministic CSS custom-property output.

This phase creates the design-system boundary between Halloy's IRC-oriented schema and the blog frontend. The frontend must never depend directly on Halloy field names.

## Dependencies

Requires Phase 01's token contract and Phase 02's parser/color primitives.

## Proposed module shape

```text
app/themes/
  model.py
  translate.py
  diagnostics.py
```

The implementation may combine files where repository conventions favor fewer modules, but the responsibilities must remain separable:

- semantic theme model;
- translation logic;
- diagnostics and contrast warnings;
- CSS serialization.

## Required implementation work

### 1. Implement `BlogTheme`

Create an immutable typed model containing every required semantic token from Phase 01. Expected categories:

- page background;
- content surface;
- elevated surface;
- hover/active surface;
- primary and subtle borders;
- primary, secondary, muted, and dim text;
- text on accent and state fills;
- accent, accent hover, accent subtle, link, and focus colors;
- success, error, warning, and info foreground/background pairs;
- input background and border;
- code background and border;
- selection background;
- navbar background and border;
- overlay and shadow colors.

Where existing CSS still expects hue-based names, provide explicit compatibility aliases in one place rather than duplicating fields throughout the translator.

### 2. Implement deterministic Halloy mapping

Create:

```python
def translate_halloy_theme(theme: HalloyTheme) -> ThemeTranslationResult: ...
```

`ThemeTranslationResult` should include:

- translated `BlogTheme`;
- dark/light classification;
- warnings;
- optional mapping provenance useful for CLI/admin inspection.

Use Phase 01's mapping table as the source of truth. Typical mappings include:

- Halloy primary background to page or chrome background;
- buffer background to content surfaces;
- title-bar/highlight colors to elevated and hover surfaces;
- primary/secondary/topic text to blog text hierarchy;
- URL color to accent/link;
- success/error/action colors to semantic states;
- code or tertiary colors to secondary accents only where needed.

Do not infer semantics from filenames.

### 3. Derive missing semantic colors

Halloy does not contain all blog tokens. Derive missing colors from validated inputs using Phase 02 utilities.

Derived colors should include:

- subtle accent backgrounds;
- state backgrounds;
- hover surfaces;
- active surfaces;
- code and input surfaces;
- focus rings;
- overlays;
- shadows;
- foreground text on filled buttons or badges.

Derivation must account for light and dark palettes. Avoid hardcoded assumptions that white text belongs on every accent.

### 4. Add contrast-aware foreground selection

Choose `text_on_accent` and related filled-state foregrounds by comparing candidate contrast ratios. Prefer theme-native primary/background colors where sufficient; fall back to black or white only when needed and document that fallback in diagnostics.

Define mandatory contrast checks for at least:

- primary text on page background;
- primary text on surface;
- muted text on surface;
- link on page and surface;
- text on accent;
- form text on input background;
- focus ring against page and surface.

This phase may emit warnings rather than reject low-contrast custom themes. Later hardening decides bundled-theme policy.

### 5. Serialize CSS safely

Implement a serializer that owns both property names and validated values:

```python
def to_css_variables(theme: BlogTheme, selector: str = ":root") -> str: ...
```

Requirements:

- stable ordering;
- no arbitrary property names;
- no raw Halloy text;
- normalized CSS color output;
- support for scoped selectors needed by future dark/light pairing;
- deterministic trailing newline and formatting for tests.

The serializer should support returning a mapping for existing Jinja `theme_vars` compatibility as well as a complete CSS block if useful.

### 6. Create an emergency default

Define a hardcoded known-good `BlogTheme` independent of TOML resources. It should approximate the current GitHub-dark appearance and serve only as the terminal fallback when packaged resources cannot be loaded.

### 7. Run catalog-wide translation tests

For every approved source theme:

- parse;
- translate;
- assert all required tokens exist;
- serialize;
- verify no invalid CSS values;
- classify dark/light;
- collect warnings;
- ensure deterministic repeated output.

Commit a reviewed allowlist for known warnings only if necessary. Do not blanket-disable contrast diagnostics.

## Files expected to change

Likely:

- `app/themes/model.py`;
- `app/themes/translate.py`;
- `app/themes/diagnostics.py`;
- `tests/themes/test_translation.py`;
- `tests/themes/test_theme_css.py`;
- optional catalog diagnostic snapshot.

Do not alter templates or runtime theme selection in this phase.

## Testing requirements

Include focused tests for:

- representative dark theme;
- representative light theme;
- low-contrast theme;
- alpha-bearing theme;
- missing optional fields;
- foreground selection on light and dark accents;
- stable CSS ordering;
- selector scoping;
- emergency default completeness.

## Acceptance criteria

- `BlogTheme` covers the complete Phase 01 token contract.
- Every approved Halloy theme translates and serializes deterministically.
- No frontend CSS variable is sourced directly from unvalidated Halloy text.
- Light and dark themes receive appropriate derived surfaces and foregrounds.
- Contrast warnings are structured and testable.
- A known-good emergency theme exists without filesystem dependencies.
- No request-rendering behavior changes yet.

## Non-goals

- filesystem discovery;
- external overrides;
- packaging resources;
- database settings;
- admin UI;
- visitor theme persistence.

## Handoff notes

Phase 04 should treat the translator as a pure function and cache its result. It must not add registry-specific behavior to `translate_halloy_theme()`.
