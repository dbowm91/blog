# Halloy Theme Phase 12 — Accessibility and Theme Quality Validation

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/themes.md](../architecture/core/themes.md); this file is the historical record.

## Objective

Establish enforceable accessibility and usability quality gates for every bundled theme and actionable diagnostics for external themes.

The phase must distinguish mandatory failures from advisory warnings. Bundled themes are application-owned release artifacts and must meet the mandatory policy. External themes may remain selectable with warnings unless strict mode is enabled.

## Contrast policy

Validate WCAG contrast for at least:

- primary text on page background;
- primary text on content and elevated surfaces;
- secondary/muted text on content surfaces;
- link and link-hover colors on page and content surfaces;
- text on accent-filled controls;
- success, error, warning, and info foreground/background pairs;
- form text and placeholder text on input backgrounds;
- input borders against surrounding surfaces;
- focus indicators against page, surface, and control backgrounds;
- selection text/background;
- code text/background where controlled by theme tokens.

Define threshold categories in code and documentation:

- normal text mandatory threshold;
- large text threshold where applicable;
- non-text control/focus threshold;
- advisory muted/decorative thresholds.

Do not classify UI text as decorative merely to pass a theme.

## Catalog-wide validator

Implement a reusable validator over `BlogTheme` and translated diagnostics. It should return structured findings containing:

- token pair;
- measured ratio;
- required threshold;
- severity;
- human-readable remediation guidance;
- theme name/source.

Run it over all bundled themes in CI. Commit an explicit, reviewed exception manifest only where a requirement is genuinely non-applicable. Avoid broad warning suppression.

## External theme behavior

Expose validation results consistently through:

- admin selectors/preview;
- `flask themes validate` and `inspect`;
- logs during selection or refresh;
- optional strict-validation configuration.

Strict mode should reject themes with mandatory failures while continuing to permit advisory warnings. Default mode may allow external themes with warnings but must clearly identify the risks.

## Focus, keyboard, and state validation

Add browser-level coverage for representative dark and light themes:

- visible focus ring on links, buttons, inputs, selects, and theme toggle;
- keyboard operation of three-state scheme control;
- preview controls and admin selectors;
- hover, active, disabled, error, and success states remain distinguishable;
- selected text remains readable;
- high-contrast/forced-colors behavior does not hide controls;
- reduced-motion settings are respected.

## Theme classification quality

Audit dark/light classification for all bundled themes. Add a manifest or generated report showing:

- computed classification;
- page/background luminance;
- any theme whose filename and computed class disagree;
- paired-theme suitability.

Classification mismatch is not automatically a failure, but ambiguous themes should be surfaced in admin UX.

## Visual regression fixtures

Create deterministic representative pages or snapshots containing:

- navigation and footer;
- article typography;
- forms and validation states;
- buttons and badges;
- code blocks;
- tables;
- admin controls;
- flash/toast states.

Use a curated dark/light subset for browser snapshots and run token-level validation over the entire catalog.

## Reporting

Generate a machine-readable catalog quality report in CI or a script. Include:

- pass/fail count;
- warnings by category;
- worst contrast pairs;
- classification summary;
- schema/translation completeness.

Avoid committing unstable timestamps or environment-specific paths.

## Testing requirements

- exact contrast calculations against known reference pairs;
- severity boundary tests;
- every bundled theme evaluated;
- strict and permissive external-theme modes;
- admin/CLI diagnostics consistency;
- keyboard/focus E2E tests;
- forced-colors and reduced-motion checks where browser tooling permits.

## Acceptance criteria

- every bundled theme passes mandatory accessibility gates;
- external theme problems are visible and actionable;
- strict mode rejects mandatory failures deterministically;
- focus and keyboard behavior remain usable under representative themes;
- catalog quality report is reproducible and CI-enforced;
- no theme can make primary navigation, forms, or submission controls unreadable.
