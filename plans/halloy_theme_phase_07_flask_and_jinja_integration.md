# Halloy Theme Phase 07 — Flask and Jinja Runtime Integration

## Objective

Make the Halloy theme registry and persisted settings the sole runtime source of frontend palette variables while preserving CSP, custom CSS ordering, syntax-theme independence, and safe fallback behavior.

## Dependencies

Requires Phases 01–06 and the small closure pass. Do not begin until package verification and registry behavior are stable.

## Runtime service boundary

Introduce one application-level theme service responsible for:

- constructing `ThemeRegistry` from application configuration;
- resolving effective site dark/light theme names;
- loading translated themes;
- exposing warnings/fallback metadata;
- invalidating registry state when requested;
- generating template-ready variable mappings or CSS blocks.

Avoid constructing registries in individual routes or templates.

## Flask lifecycle

Create the registry/service once per application process, preferably through `app.extensions` or an equivalent existing extension pattern.

Requirements:

- no request-global mutable catalog construction;
- thread-safe read behavior for normal WSGI operation;
- explicit invalidation API for later admin refresh;
- no database access during module import;
- deterministic startup fallback if configuration is invalid.

## Template context

Provide a centralized context processor or helper returning at least:

```text
theme_dark_name
theme_light_name
theme_dark_vars
theme_light_vars
theme_dark_css
theme_light_css
theme_default_scheme
theme_warnings
syntax_theme
custom_css_enabled
custom_css
```

Do not load a theme separately in every route. Public, admin, authentication, preview, and error templates should receive the same effective palette source unless a deliberate exception is documented.

## CSS emission

Emit generated variables in a nonce-bearing inline style block early in `<head>`.

Recommended structure:

```css
:root,
[data-color-scheme="dark"] {
  /* translated dark variables */
}

[data-color-scheme="light"] {
  /* translated light variables */
}
```

Ordering must be:

1. static base CSS defaults;
2. generated Halloy variables;
3. scheme-specific structural CSS;
4. administrator custom CSS.

Custom CSS must remain able to override semantic variables intentionally.

## CSP and escaping

Generated CSS may be treated as safe only after serialization through the trusted `BlogTheme` serializer. Never mark raw TOML strings or arbitrary mappings as safe.

Verify:

- nonce is present on generated theme style blocks;
- no `unsafe-inline` requirement is introduced;
- public error pages and login templates also comply;
- custom CSS behavior remains governed by existing privileged settings.

## Legacy transition

Replace direct `THEME_PRESETS` lookup in runtime rendering with the theme service.

During this phase:

- retain compatibility aliases for migration and rollback;
- remove duplicate route-level `theme_vars` logic;
- do not delete `THEME_PRESETS` until all integration tests pass and Phase 14 cleanup occurs;
- log fallback activation without exposing filesystem paths.

## Error behavior

Handle registry errors distinctly:

- missing configured theme → configured fallback;
- malformed external selected theme → fallback plus operator warning;
- bundled parse failure → error log plus emergency fallback;
- resource read failure → emergency fallback;
- invalid persisted syntax → validated fallback.

No public request should fail with HTTP 500 solely because a theme cannot load.

## Tests

Add integration tests for:

- public base template receives Halloy variables;
- admin base and login templates receive the same source;
- dark and light CSS blocks are both emitted;
- CSP nonce is attached;
- custom CSS appears after generated variables;
- syntax theme stylesheet selection is unchanged;
- missing/malformed selected themes fall back without 500;
- emergency fallback emits complete variables;
- registry is constructed once per app rather than per request;
- no direct runtime access to `THEME_PRESETS` remains outside compatibility code.

## Expected files

Likely:

- app factory/extension initialization;
- new theme service module;
- context processors;
- `app/templates/base.html` and admin/login bases;
- route helpers currently building theme variables;
- integration and CSP tests;
- architecture documentation.

## Acceptance criteria

- All rendered application surfaces use Halloy-derived semantic variables.
- One centralized service owns registry and fallback behavior.
- Generated theme CSS is CSP-compliant and emitted before custom CSS.
- Syntax highlighting remains independent.
- Theme failures never cause public 500 responses under normal fallback policy.
- Legacy preset rendering is no longer the runtime authority.
