# Halloy Theme Phase 02 — Parser and Color Primitives

## Objective

Implement a typed, deterministic, and security-conscious parser for the supported Halloy TOML subset plus the color utilities required by the later translation and accessibility phases.

This phase must not integrate themes into request rendering. Its output is a reusable parser boundary with catalog-wide tests.

## Dependencies

Complete Phase 01 first. Use its supported-field contract, accepted color formats, file-size expectations, and catalog findings as authoritative inputs.

## Proposed module shape

Adapt to repository conventions, but prefer a cohesive package:

```text
app/themes/
  __init__.py
  halloy.py
  colors.py
```

The parser must not depend on Flask request state, SQLAlchemy, templates, or filesystem discovery policy.

## Required implementation work

### 1. Define normalized Halloy models

Implement typed models for:

- `HalloyGeneral`;
- `HalloyText`;
- `HalloyBuffer`;
- `HalloyButtons`;
- `HalloyTheme`.

Use dataclasses or Pydantic according to existing dependencies and project style. Do not add Pydantic solely for themes if it is not already a runtime dependency.

Behavior requirements:

- tolerate unknown Halloy fields;
- apply documented defaults only to optional fields;
- reject invalid root structures and invalid section types;
- preserve enough source metadata for useful diagnostics;
- normalize nested button sections without assuming only one button type;
- ignore unsupported nested sections deliberately and test that behavior.

Expose a narrow API such as:

```python
def parse_halloy_theme_bytes(data: bytes, *, source_name: str) -> HalloyTheme: ...
def parse_halloy_theme(path_or_resource) -> HalloyTheme: ...
```

Keep byte parsing separately testable from filesystem/resource access.

### 2. Implement strict color parsing

Support only formats confirmed by Phase 01, expected to include:

- `#RRGGBB`;
- `#RRGGBBAA` where present.

Normalize colors into an immutable representation rather than passing arbitrary strings through to CSS. The representation should preserve alpha where needed and expose RGB/RGBA components.

Reject:

- CSS functions;
- named colors;
- malformed hex;
- embedded delimiters or declarations;
- whitespace-obscured injection attempts;
- unsupported lengths.

Error messages should identify the semantic field and source theme without exposing sensitive runtime paths in public-facing contexts.

### 3. Add color derivation primitives

Implement and test:

- hex/RGB/RGBA conversion;
- alpha compositing against a background;
- deterministic color mixing;
- HSL or perceptual lightness adjustment;
- relative luminance;
- WCAG contrast ratio;
- dark/light background classification;
- serialization to validated CSS color text.

Clamp inputs and avoid silent integer overflow or invalid output. Define rounding behavior so snapshots remain deterministic across Python versions.

### 4. Define exception taxonomy

Use explicit errors, for example:

- `ThemeParseError`;
- `ThemeSchemaError`;
- `ThemeColorError`.

Errors should carry structured context such as source name and field path. They should not force callers to parse exception strings.

### 5. Validate the full source catalog

Add a parameterized test over every checked-in source theme. The test should:

- read each file under the approved catalog location;
- enforce a reasonable maximum size;
- parse it successfully or match an explicitly documented exclusion;
- validate every supported color field;
- assert deterministic re-serialization or normalized model equality.

Do not silently skip malformed files.

### 6. Add focused fixtures

Create fixtures for:

- minimal valid theme;
- full representative theme;
- light theme;
- dark theme;
- theme with alpha colors;
- extra unknown sections;
- wrong section type;
- malformed TOML;
- invalid color;
- malicious CSS-like color value.

## Files expected to change

Likely:

- `app/themes/__init__.py`;
- `app/themes/halloy.py`;
- `app/themes/colors.py`;
- `tests/themes/test_halloy_parser.py`;
- `tests/themes/test_colors.py`;
- `tests/themes/fixtures/*`.

## Testing requirements

Unit tests must cover normal and boundary behavior. Catalog tests must prove every bundled-source file parses. Include exact tests for six- and eight-digit colors, alpha compositing, contrast ratios for known pairs, and dark/light classification near the chosen threshold.

Run the repository's full lint, type-check, and test commands. Do not weaken typing or lint configuration to accommodate the new code.

## Acceptance criteria

- The parser consumes every approved Halloy source theme.
- Unknown fields are tolerated but unsupported invalid structures are rejected.
- No raw theme color string can become CSS without validation.
- Color utilities produce deterministic, tested outputs.
- Error classes provide structured source and field context.
- Parser code has no Flask, template, database, or registry coupling.
- Existing application behavior remains unchanged.

## Non-goals

- theme discovery;
- external directory resolution;
- CSS variable generation;
- admin selection;
- database migration;
- request-time theme rendering.

## Handoff notes

Phase 03 should accept only `HalloyTheme` and validated color objects from this phase. It should not reopen TOML files or reimplement color parsing.
