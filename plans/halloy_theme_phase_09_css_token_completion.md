# Halloy Theme Phase 09 — CSS Token Completion and Hardcoded Color Removal

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/themes.md](../architecture/core/themes.md); this file is the historical record.

## Objective

Complete the frontend migration to semantic Halloy-derived tokens so all supported bundled themes render coherently across public, admin, authentication, responsive, and interactive surfaces.

## Dependencies

Requires Phase 07 runtime integration and Phase 08 scheme behavior. Use the Phase 01 literal audit and `BlogTheme` contract as the authoritative backlog.

## Audit execution

Re-run the repository-wide literal color audit over:

- base, critical, layout, public, form, admin, and utility CSS;
- templates and inline styles;
- JavaScript-generated markup;
- SVG fills/strokes;
- charts, badges, alerts, toasts, modals, overlays, and code blocks;
- mobile and responsive rules;
- authentication and error pages.

Classify each remaining literal as:

- replace with semantic token;
- intentional invariant;
- syntax-highlighting-only;
- third-party vendored asset;
- generated Halloy output;
- false positive.

Commit an updated allowlist for intentional invariants. Do not leave unexplained color literals.

## Token mapping work

Replace theme-sensitive values with existing `BlogTheme` CSS variables. Add new semantic tokens only when a real UI role cannot be represented cleanly by the current contract.

Priority components:

- primary, secondary, destructive, and disabled buttons;
- links and visited/hover/focus states;
- navigation chrome and dropdowns;
- forms, selects, placeholders, validation states, and autofill;
- tables and pagination;
- flash messages, toasts, badges, and status chips;
- modal overlays and elevated panels;
- search UI and filters;
- article prose, blockquotes, inline code, and code containers;
- admin editors and preview panes;
- mobile menu and responsive navigation;
- selection and focus indicators.

Avoid encoding hue names into component styles. Components should depend on roles such as `--blog-status-error` or `--blog-surface-hover`.

## Critical CSS alignment

Ensure first-paint critical CSS uses the same semantic variables and selectors as deferred styles.

Requirements:

- no duplicate fallback palette that diverges from Halloy output;
- shell, navigation, text, and background render correctly before deferred styles;
- dark/light selector behavior matches Phase 08;
- no visible palette jump when full CSS loads.

## Syntax highlighting boundary

Keep Prism themes independent, but ensure the surrounding code block container, borders, toolbar, copy buttons, and inline code use semantic blog tokens.

Do not attempt to synthesize Prism token colors from Halloy in this phase.

## Browser-native controls

Verify:

- `color-scheme` behavior;
- select and input legibility;
- autofill foreground/background;
- disabled controls;
- scrollbars where customized;
- date/time controls;
- focus outlines.

## Visual validation

Create a representative theme matrix using at least:

- dark neutral theme;
- dark high-saturation theme;
- light neutral theme;
- warm/light theme;
- low-contrast-warning theme;
- external override fixture.

Capture or automate representative pages:

- homepage/listing;
- article page;
- search;
- login/reset pages;
- admin dashboard;
- editor/forms;
- modal/toast/error states;
- mobile navigation.

Visual snapshots should supplement, not replace, semantic assertions.

## Tests

Add tests for:

- every required CSS variable emitted in both schemes;
- no prohibited hardcoded palette literals outside allowlisted files;
- critical CSS uses semantic variables;
- primary controls meet contrast requirements under representative themes;
- focus indicators remain visible;
- disabled and validation states remain legible;
- no static `[data-theme="light"]` variable authority remains;
- custom CSS can still override tokens.

## Expected files

Likely broad changes across:

- `app/static/css/*.css`;
- base/admin/auth templates;
- SVG and component templates;
- frontend audit documentation;
- visual/browser tests.

Keep each commit grouped by component family to preserve reviewability.

## Acceptance criteria

- All meaningful frontend colors originate from semantic tokens or documented invariants.
- Critical and deferred CSS use one palette authority.
- Representative dark and light Halloy themes remain readable across core pages.
- Focus, form, status, and destructive states remain accessible.
- Syntax highlighting remains independently selectable.
- The literal-color audit has no unexplained findings.
