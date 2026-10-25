# Halloy Theme Phase 14 — Documentation, Migration, and Operator Guidance

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/themes.md](../architecture/core/themes.md); this file is the historical record.

## Objective

Complete the user, operator, contributor, and release documentation for the Halloy-compatible theme system so that deployment, migration, customization, troubleshooting, and extension do not require reading implementation code.

This phase should reconcile documentation with actual behavior. Do not document planned features as already available.

## Documentation set

Update or add:

- README theme overview;
- configuration reference;
- deployment guide;
- Docker/external volume examples;
- admin appearance guide;
- operator CLI guide;
- theme authoring guide;
- architecture and data-flow documentation;
- migration notes from legacy presets;
- release notes/changelog;
- Halloy attribution and redistribution notices;
- troubleshooting guide.

## Configuration reference

Document every supported setting and precedence rule:

- bundled dark and light defaults;
- persisted `SiteSettings` values;
- site default scheme;
- visitor local-storage preference;
- external theme directory;
- strict validation mode if implemented;
- file-size and name restrictions;
- refresh requirements;
- syntax-theme independence;
- custom CSS ordering.

Include exact examples for source checkout, installed package, and container deployment.

## Migration guide

Document:

- database migration command;
- legacy preset mapping;
- whether visual mode is preserved as dark/light/system;
- rollback behavior;
- custom CSS preservation;
- syntax theme preservation;
- behavior when a selected theme is unavailable;
- backup recommendations before migration.

Include a table for `github-dark`, `github-light`, `solarized-dark`, and `monokai` mappings.

## External theme authoring guide

Explain the supported Halloy TOML subset and translation behavior:

- required and optional sections;
- accepted color formats;
- ignored fields;
- direct versus derived blog tokens;
- dark/light classification;
- contrast validation;
- safe filename rules;
- override semantics;
- validation and inspection commands.

Provide:

- a minimal valid theme;
- a complete example;
- a low-contrast warning example;
- an external override walkthrough.

## Admin and visitor behavior

Document the separation between:

- administrator-selected dark/light theme pair;
- site default color scheme;
- visitor `system`/`dark`/`light` preference;
- Prism syntax theme;
- administrator custom CSS.

Explain how visitors reset their preference and how system changes are followed.

## Operational troubleshooting

Cover:

- theme not appearing after copying a file;
- malformed TOML;
- theme disappears after refresh;
- external override masking bundled theme;
- contrast warnings;
- multi-worker refresh behavior;
- database migration mismatch;
- emergency fallback activation;
- CSP/custom CSS issues;
- wheel missing resources.

Tie each problem to CLI/admin diagnostics and relevant logs.

## Architecture documentation

Update diagrams and ownership boundaries:

```text
SiteSettings/config + visitor preference
        -> app-scoped ThemeService
        -> ThemeRegistry
        -> bundled/external resource
        -> parser -> translator -> BlogTheme
        -> CSP-nonced template variables
```

Document cache lifetime, refresh semantics, fallback hierarchy, and security boundaries.

## Documentation tests

Add lightweight validation where practical:

- configuration examples parse;
- CLI command names/options match implementation;
- sample TOML themes validate;
- internal links resolve;
- referenced paths exist;
- migration revision names are correct.

## Acceptance criteria

- a new operator can install, select, override, validate, refresh, and troubleshoot themes from documentation alone;
- migration semantics are explicit and match code/tests;
- theme authors have a precise supported-schema reference;
- deployment examples cover package and container installs;
- docs accurately describe cache, multi-worker, CSP, syntax-theme, and custom-CSS behavior;
- attribution and release notes are complete.
