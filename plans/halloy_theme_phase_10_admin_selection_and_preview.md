# Halloy Theme Phase 10 — Admin Theme Selection, Preview, and Refresh

## Objective

Provide a safe administrative workflow for selecting Halloy dark/light themes, previewing changes, viewing warnings, and refreshing external themes without exposing filesystem details or allowing arbitrary theme paths.

## Dependencies

Requires Phases 06–09. The registry, persistence model, runtime integration, scheme behavior, and CSS token coverage must already be stable.

## Admin settings model

Extend the appearance settings surface to manage:

- dark Halloy theme;
- light Halloy theme;
- default visitor scheme (`system`, `dark`, `light`);
- syntax highlighting theme;
- custom CSS enablement/content;
- external theme directory status, read-only;
- theme refresh action;
- validation and contrast warnings.

Do not allow the browser to submit arbitrary filesystem paths. Theme values must be validated against the current registry catalog.

## Dynamic selectors

Populate selectors from `ThemeRegistry.list_themes()`.

Group entries by source:

- Bundled themes;
- External themes.

For each option expose safe metadata:

- canonical/display name;
- source;
- dark/light classification;
- external override status;
- validation status;
- warning count.

Mark same-name external overrides clearly. Do not expose absolute paths, exception traces, or internal resource identifiers.

Prevent accidental selection of an obviously dark theme for the light slot or vice versa by warning or filtering, but permit an explicit override if product requirements favor operator control.

## Preview architecture

Implement non-persistent preview before save.

Preferred approach:

- server loads selected registry names through the normal translation path;
- returns only validated semantic variable mappings or scoped CSS;
- preview is applied to a bounded preview container or temporary document-level attributes;
- cancel restores persisted settings;
- save uses normal CSRF-protected form submission and server validation.

Do not parse TOML in the browser. Do not inject raw external theme text.

Preview should include representative elements:

- headings and body text;
- links;
- primary/secondary/destructive buttons;
- inputs and validation states;
- status badges;
- code block container;
- elevated surface and border;
- focus indicator.

## Refresh action

Add a dedicated CSRF-protected admin action to invalidate and rebuild the registry.

Refresh behavior:

- rescan external directory;
- clear theme caches;
- preserve persisted selections;
- report added, removed, overridden, malformed, and restored bundled themes;
- if a selected external theme disappears, warn and show the effective fallback;
- do not restart the process;
- do not write into bundled resources.

Follow the explicit refresh contract established in the small closure pass.

## Validation and warnings

On selection and save, display actionable warnings for:

- missing theme;
- malformed external theme;
- dark/light classification mismatch;
- low contrast;
- use of fallback/defaulted Halloy fields;
- external override of a bundled theme;
- selected theme disappearing after refresh.

Warnings should not expose raw file paths. Fatal validation should block save; advisory contrast warnings may require acknowledgement or remain visible after save according to existing admin UX conventions.

## Persistence behavior

Saving must be atomic with normal settings updates.

Requirements:

- validate both names before commit;
- rollback on failure;
- preserve syntax theme and custom CSS unless explicitly edited;
- invalidate relevant runtime theme caches after successful save;
- make new values visible on the next request;
- log administrator-visible changes without sensitive path data.

## Authorization and security

- existing admin authentication required;
- CSRF protection on save and refresh;
- no public theme-management endpoints;
- registry names only, never paths;
- response CSS generated through trusted serializer;
- bounded preview payload size;
- rate-limit refresh if existing admin action conventions require it.

## Tests

Add tests for:

- selectors list bundled and external themes;
- override labeling;
- safe metadata contains no absolute paths;
- valid dark/light selection persists;
- invalid or missing names are rejected;
- classification mismatch warning;
- preview does not persist settings;
- preview output contains only serializer-controlled variables;
- cancel restores current appearance;
- refresh discovers additions and removals;
- refresh restores bundled theme after override deletion;
- selected missing external theme falls back visibly;
- CSRF and admin authorization enforcement;
- syntax theme/custom CSS preservation;
- cache invalidation after save.

## Expected files

Likely:

- admin settings routes/forms;
- appearance settings templates;
- preview endpoint or server-rendered partial;
- theme service refresh method;
- admin JavaScript for preview state;
- admin CSS using semantic tokens;
- route, security, and browser tests;
- operator documentation.

## Acceptance criteria

- Administrators can select any valid bundled or external Halloy theme for dark and light slots.
- External overrides are visible and correctly labeled.
- Preview is non-persistent, bounded, and based only on validated translated tokens.
- Refresh applies external file changes without process restart.
- Missing/malformed selected themes fall back safely with clear warnings.
- Save and refresh are authenticated and CSRF-protected.
- Syntax theme and custom CSS behavior remain independent.
- No filesystem paths or raw TOML content reach the browser.
