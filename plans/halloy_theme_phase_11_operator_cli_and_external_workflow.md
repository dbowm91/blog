# Halloy Theme Phase 11 — Operator CLI and External Theme Workflow

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/themes.md](../architecture/core/themes.md); this file is the historical record.

## Objective

Provide a complete command-line workflow for listing, validating, inspecting, refreshing, and troubleshooting bundled and external Halloy-compatible themes without requiring direct Python use or admin UI access.

The CLI must use the same registry, parser, translator, diagnostics, and configuration paths as the running application. It must not implement an independent theme loader.

## Required commands

Implement a coherent Flask CLI group, for example:

```text
flask themes list
flask themes validate PATH
flask themes inspect NAME
flask themes refresh
flask themes paths
```

Use existing CLI registration conventions in `app/cli.py`.

## Command A — `themes list`

Display the effective merged catalog with columns or structured output for:

- canonical name;
- display name;
- source (`bundled` or `external`);
- override state;
- dark/light classification where known;
- validation status;
- warning count.

Options:

- `--source bundled|external|all`;
- `--json` for automation;
- `--warnings` to include diagnostic summaries;
- deterministic ordering.

The command must not expose absolute external paths unless an explicit operator-only verbose flag is supplied.

## Command B — `themes validate PATH`

Validate a Halloy TOML file before installation or selection.

The command must report:

- file readability and size;
- TOML/schema status;
- unsupported or ignored sections;
- normalized theme name;
- all translated blog tokens;
- dark/light classification;
- contrast warnings;
- whether the filename would override a bundled theme;
- exit status suitable for CI/scripts.

Exit codes:

- `0`: valid;
- nonzero: unreadable, invalid, unsafe name, oversized, parse failure, or translation failure.

Do not copy the file into the external directory automatically in this phase.

## Command C — `themes inspect NAME`

Resolve a registry name and display:

- canonical/display name;
- source and override status;
- selected resource metadata;
- dark/light classification;
- translation provenance;
- generated semantic token values;
- contrast diagnostics;
- fallback status.

Support `--json` and `--css` output. CSS output must come from the validated serializer.

## Command D — `themes refresh`

Invalidate and rebuild the app-scoped theme service registry.

Report:

- catalog count before and after;
- added and removed names;
- active external overrides;
- currently configured themes that disappeared;
- effective fallback names.

The command must return nonzero only when refresh itself fails, not merely because warnings exist.

## Command E — `themes paths`

Display:

- bundled resource package identity;
- configured external theme directory;
- whether the external directory exists/readable;
- maximum file size;
- precedence rules.

Avoid implying bundled resources are writable.

## External theme workflow documentation

Document the recommended operator sequence:

1. create or obtain a Halloy-compatible TOML file;
2. run `flask themes validate FILE`;
3. copy it into the configured external directory;
4. run `flask themes refresh` or use the admin refresh action;
5. inspect and select it;
6. remove the file and refresh to restore a bundled override.

Document development, container, and XDG-style paths consistent with current deployment conventions.

## Security requirements

- validation accepts a direct path only for the explicit operator command;
- runtime selection remains registry-name-only;
- reject oversized and non-regular files;
- do not recursively discover directories;
- do not emit raw unvalidated CSS;
- redact sensitive paths from default output;
- use typed registry/parser errors for user-facing failures.

## Testing

Add CLI runner tests for:

- bundled and external listing;
- JSON output validity;
- valid/invalid/malicious files;
- same-name override reporting;
- inspect by alias and canonical name;
- refresh added/removed detection;
- missing external directory;
- nonzero exit codes;
- app-specific configuration isolation.

## Acceptance criteria

- operators can diagnose and manage external themes without source edits;
- CLI results match admin/registry behavior exactly;
- JSON modes are stable and documented;
- invalid themes are rejected with actionable messages and exit codes;
- refresh behavior is shared with the running service;
- external customization workflow is documented end-to-end.
