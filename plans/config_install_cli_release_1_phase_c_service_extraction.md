# Release 1 Phase C — Operational Service Extraction and Flask CLI Migration

## Objective

Extract operational business logic from the existing large Flask CLI module into reusable, testable services, then expose the highest-value maintenance operations through the new standalone `devlog` CLI while preserving transitional Flask command compatibility.

This phase completes Release 1 by ensuring later onboarding, diagnostics, backup, deployment, and update work can compose stable service APIs rather than shelling out to Flask commands or duplicating database logic.

## Current problems addressed

- `app/cli.py` combines unrelated administrative, database, import/export, cleanup, backup, and theme-management responsibilities.
- Command handlers perform business logic directly inside Click-decorated functions.
- Several operations assume Flask CLI application context and are difficult to invoke from a standalone product CLI.
- Output strings and failure behavior are coupled to command implementations rather than typed results.
- Later `onboard`, `doctor`, `update`, and deployment commands would otherwise have to invoke subprocesses or reimplement existing operations.
- Existing commands have inconsistent argument styles, confirmation behavior, and exit-status semantics.

## Non-goals

- Do not remove existing Flask commands in Release 1.
- Do not complete the full backup/update/deployment lifecycle; only extract primitives needed for later releases.
- Do not redesign application models or database schemas unless required to make an operation correct and reusable.
- Do not move web-route business logic indiscriminately. Extract only logic shared with operational commands or required for clean layering.
- Do not expose dangerous maintenance operations without confirmation and structured failure semantics.
- Do not create subprocess wrappers around `flask` as the new architecture.

## Architectural target

Command flow should become:

```text
CLI handler
  -> resolve typed configuration
  -> create application context only when required
  -> call service function
  -> receive typed result/domain data
  -> render human or JSON output
  -> map typed failure to stable exit code
```

Flask compatibility command flow should become:

```text
Flask command wrapper
  -> call the same service function
  -> render compatibility output
```

No service function should depend on Click, terminal output, or process exit.

## Proposed service organization

Adapt exact names to repository conventions, but separate domains clearly:

```text
app/services/operations/
    __init__.py
    results.py
    admin.py
    database.py
    search.py
    media.py
    transfer.py
    themes.py
    backup.py
    runtime.py
```

Alternatively, use domain-specific existing service packages if they already exist. Avoid introducing parallel service modules where mature domain services are already present; in those cases, add a thin operational facade over the existing implementation.

## Workstream C1 — inventory current commands and dependencies

Before extraction, enumerate every registered Flask command and record:

- command name and aliases
- arguments/options
- whether application context is required
- database session behavior
- direct imports from routes or private helpers
- output and failure behavior
- whether it mutates state
- confirmation requirements
- automation/JSON suitability
- service module target
- compatibility requirements

At minimum, include:

- `create-admin`
- `promote-admin`
- database integrity check
- search rebuild
- orphaned-image cleanup
- import/export
- seed/sample data
- theme list/validate/inspect/refresh/paths/accessibility
- backup/restore-related commands present elsewhere in the CLI module
- any maintenance commands not visible in the README command list

Use this inventory to prevent command loss during decomposition.

## Workstream C2 — define shared operational result types

Use or extend Phase A's result model with domain payloads rather than returning formatted strings.

Examples:

```text
AdminOperationResult
DatabaseCheckResult
SearchRebuildResult
MediaCleanupResult
ExportResult
ImportResult
ThemeValidationResult
BackupOperationResult
```

Common fields should include:

- stable operation code
- success/degraded/failure status
- counts and identifiers
- warnings
- remediation
- safe details

Domain objects should remain serializable without leaking passwords, API keys, encryption keys, tokens, or absolute paths unless verbose/operator output explicitly permits safe paths.

## Workstream C3 — administrator services

Extract administrator creation and promotion logic from Click handlers.

Recommended service operations:

```python
create_admin(username, password, *, update_existing=False)
promote_admin(username)
reset_admin_password(username, password)
list_admins()
```

Requirements:

- centralize password-complexity validation in a non-route-private service or policy module
- do not import a private helper from `app.routes.admin.helpers` in operational services
- define explicit behavior when a user already exists
- distinguish create, promote, password reset, and no-op outcomes
- ensure transaction rollback on integrity or commit failure
- never return or log passwords
- maintain ownership/super-admin invariants if the model has them
- use stable domain exceptions for not found, conflict, validation, and database failure

Expose initial standalone commands:

```text
devlog admin create
devlog admin promote USERNAME
devlog admin reset-password USERNAME
devlog admin list
```

Password input requirements:

- interactive hidden prompt by default
- support `--password-file` or stdin for automation
- avoid normal password command-line arguments
- confirmation prompt for interactive creation/reset
- JSON output must not reveal credential material

Keep `flask create-admin` and `flask promote-admin` as wrappers.

## Workstream C4 — database and search services

Extract:

```python
check_database_integrity()
get_migration_status()
run_migrations()
rebuild_search_index()
```

Requirements:

- SQLite integrity checks must clearly report unsupported/not-applicable behavior for non-SQLite databases
- use typed status rather than matching output strings
- remove sessions/connections predictably
- preserve transaction boundaries
- avoid rebuilding search inside unrelated operations unless required and documented
- distinguish healthy, degraded, unsupported, and failed states
- avoid reporting a successful migration when no app/migration context was established

Expose:

```text
devlog db check
devlog db status
devlog db migrate
devlog db rebuild-search
```

`db migrate` should remain conservative in Release 1: it runs existing migration machinery and reports status. Automated backup-before-migration policy belongs to the later update lifecycle, but this command should emit a production warning when appropriate.

Keep Flask migration tooling compatible, including `flask db upgrade`.

## Workstream C5 — media cleanup service

The current CLI imports cleanup logic from an admin route module. Reverse that dependency.

Move orphaned-image detection and cleanup into a domain service used by both the route and CLI.

Required service separation:

```python
scan_orphaned_media() -> report
apply_orphaned_media_cleanup(report or policy) -> result
```

Support dry run in the standalone CLI:

```text
devlog media cleanup --dry-run
devlog media cleanup --apply
```

If introducing a new `media` command group is too broad for Release 1, expose the service and retain only Flask compatibility until a later release. The route must not remain the source of truth.

Safety requirements:

- identify database references missing on disk separately from unreferenced files
- avoid deleting unknown files outside configured media roots
- handle symlinks and path traversal defensively
- preserve race-safe behavior where uploads may occur concurrently
- report exact counts and partial failures

## Workstream C6 — import/export services

Extract serialization and database orchestration from command handlers.

Recommended operations:

```python
export_site_data(destination, options)
validate_import(source)
import_site_data(source, options)
```

Requirements:

- validate input structure and export version before mutation
- define duplicate policy explicitly
- preserve transaction boundaries and rollback behavior
- avoid partial commits where practical; if batching is necessary, document resumability and report partial state accurately
- perform FTS synchronization through a reusable search service
- use atomic destination writes for export
- avoid overwriting output files without explicit `--force`
- provide dry-run import validation
- redact subscriber or token-sensitive details from summaries

Expose:

```text
devlog data export PATH
devlog data import PATH --dry-run
devlog data import PATH --apply
```

A `data` group is preferable to leaving these commands under `db`, because content transfer is not equivalent to database maintenance.

Preserve `flask export-data` and `flask import-data` wrappers.

## Workstream C7 — theme operational facade

Theme management already has a richer internal service architecture than several other domains. Avoid duplicating it.

Create a CLI-facing facade that normalizes:

- list
- validate
- inspect
- refresh
- resource paths
- accessibility checks

Expose:

```text
devlog themes list
devlog themes validate TARGET
devlog themes inspect NAME
devlog themes refresh
devlog themes paths
devlog themes accessibility
```

Preserve current options such as source filtering, strict validation, warnings, verbose paths, and JSON output where applicable. Route all JSON output through the root renderer rather than command-local `json.dumps` calls.

Requirements:

- retain path redaction/verbosity policy
- distinguish bundled and external sources
- preserve accessibility severity semantics
- stable exit status for invalid themes and strict accessibility failures
- no registry mutation during list/inspect unless refresh is explicit
- maintain zero-I/O warm paths and caching guarantees established by the Halloy roadmap

Keep existing `flask themes ...` commands as wrappers around the same facade.

## Workstream C8 — backup primitive extraction

Audit existing backup CLI/service behavior and ensure core operations are callable without terminal coupling.

For Release 1, extract or normalize:

```python
create_backup(options)
inspect_backup(path)
verify_backup(path)
```

Full restore orchestration, retention, service quiescing, and update integration belong to Release 4, but primitives should already return manifests and verification results suitable for composition.

Requirements:

- never print encryption keys/passphrases
- verify produced archives before reporting success where existing format permits
- preserve compatibility with encrypted and compressed backup formats
- represent missing optional encryption support as dependency/configuration failure, not an unhandled import error
- distinguish archive creation from successful verification

Do not expose an unsafe new restore command merely to complete symmetry. A later dedicated restore plan will add atomic replacement and pre-restore safety.

## Workstream C9 — Flask compatibility wrappers

Reduce `app/cli.py` to command registration and adapters.

Each wrapper should:

1. collect arguments/prompts using existing compatible behavior
2. call a service
3. render concise compatibility output
4. raise or return a nonzero Click failure on actual failure

Avoid keeping duplicate legacy implementations behind the wrappers. Once a command is migrated, there should be one business-logic path.

Document command mapping:

```text
flask create-admin        -> devlog admin create
flask promote-admin       -> devlog admin promote
flask check-integrity     -> devlog db check
flask rebuild-search      -> devlog db rebuild-search
flask export-data         -> devlog data export
flask import-data         -> devlog data import
flask themes ...          -> devlog themes ...
```

Do not mark Flask commands deprecated until parity is demonstrated and docs are updated, but note that the standalone CLI is the future public surface.

## Workstream C10 — transaction and application-context discipline

Every extracted operation must specify:

- whether it needs application context
- whether it opens a transaction
- commit boundary
- rollback behavior
- session cleanup
- filesystem mutation order relative to database mutation
- retry/idempotency characteristics

Do not use the current `commit_with_rollback()` helper blindly where the caller needs structured error information or multi-step atomicity. Extend service transaction helpers as necessary while preserving existing behavior.

For operations combining filesystem and database changes, define compensation or partial-failure reporting. Never report full success when one side failed.

## Workstream C11 — command parity and structured output

For each migrated command, write parity tests comparing service outcomes through:

- direct service call
- standalone `devlog` CLI
- Flask compatibility command

The exact human wording need not be byte-identical, but semantic outcomes, database effects, exit status, and warnings must agree.

JSON schemas should use stable operation codes, for example:

```text
admin.created
admin.promoted
admin.password_reset
db.integrity_ok
db.integrity_failed
db.backend_unsupported
search.rebuilt
data.exported
data.import_valid
themes.valid
themes.invalid
backup.created_verified
```

## Expected files

Likely additions/modifications:

```text
app/cli.py
app/services/operations/__init__.py
app/services/operations/results.py
app/services/operations/admin.py
app/services/operations/database.py
app/services/operations/search.py
app/services/operations/media.py
app/services/operations/transfer.py
app/services/operations/themes.py
app/services/operations/backup.py
app/routes/admin/media.py
app/routes/admin/helpers.py or new password policy module
devlog_cli/commands/admin.py
devlog_cli/commands/db.py
devlog_cli/commands/data.py
devlog_cli/commands/themes.py
devlog_cli/commands/backup.py
tests/services/operations/*
tests/cli/test_admin_commands.py
tests/cli/test_db_commands.py
tests/cli/test_data_commands.py
tests/cli/test_theme_commands.py
tests/cli/test_command_parity.py
```

Exact paths should reuse existing service modules where possible.

## Testing plan

### Service unit tests

Administrator:

- create new admin
- existing user conflict/update policy
- promote existing user
- missing user
- password complexity failure
- commit/integrity failure rollback
- secret non-disclosure

Database/search:

- SQLite integrity success/failure
- unsupported backend state
- migration status and failure
- search rebuild success/failure
- session cleanup

Data transfer:

- atomic export
- unsupported export version
- duplicate policy
- import dry run
- import rollback/partial failure
- FTS synchronization

Themes:

- bundled/external filters
- validation success/failure
- strict accessibility failure
- path verbosity/redaction
- JSON schema

Backup:

- archive creation
- verification success/failure
- encryption dependency unavailable
- no success before verification

### CLI tests

- hidden password prompts
- password-file/stdin automation
- human and JSON output
- stable exit codes
- confirmation and dry-run behavior
- config path/global option propagation
- no secret output
- no unhandled tracebacks in normal mode

### Parity tests

For every migrated Flask command:

- direct service and both CLI surfaces produce equivalent state changes
- failures return nonzero status
- old command names remain registered
- command help remains accurate

### Regression tests

Run focused existing suites for:

- admin authentication and password policy
- migrations and database integrity
- FTS/search
- media upload/cleanup
- import/export serialization
- Halloy theme registry/accessibility
- backup/encryption

Then run the full suite.

## Acceptance criteria

Phase C and Release 1 are complete when:

1. Operational business logic is no longer embedded directly in major Flask Click handlers.
2. Existing Flask commands delegate to shared service functions.
3. The standalone CLI exposes admin, database, data-transfer, and theme commands with stable output and exit codes.
4. Passwords and other secrets are accepted safely and never returned or logged.
5. Database transactions and session cleanup are explicit and test-covered.
6. Media cleanup no longer depends on importing a route-private implementation.
7. Import/export validates before mutation and exports atomically.
8. Theme commands preserve current Halloy validation, accessibility, caching, and source semantics.
9. Backup creation and verification primitives are reusable by later update/restore work.
10. Direct service, standalone CLI, and Flask compatibility paths have parity tests.
11. Existing documented Flask commands remain functional during transition.
12. `app/cli.py` is materially reduced to registration/adaptation rather than remaining a monolith.
13. Full CI remains green under the packaged CLI/configuration architecture from Phases A and B.

## Release 1 closure verification

After all three Release 1 phases land, perform a combined clean-environment pass:

```bash
python -m build
python -m venv /tmp/devlog-r1
/tmp/devlog-r1/bin/pip install dist/devlog-*.whl
cd /tmp
/tmp/devlog-r1/bin/devlog --version
/tmp/devlog-r1/bin/devlog config init --profile development --config /tmp/devlog-config.toml
/tmp/devlog-r1/bin/devlog --config /tmp/devlog-config.toml config check
/tmp/devlog-r1/bin/devlog --config /tmp/devlog-config.toml themes list
```

Also verify repository development and Docker startup paths, Flask command compatibility, wheel package data, JSON redaction, and invalid-production-config failures.

## Handoff notes

Implement this phase domain by domain, with each extraction preserving behavior before the standalone command is added. Avoid a single high-risk rewrite of `app/cli.py`. The preferred sequence is administrator services, database/search, data transfer, themes, media cleanup, then backup primitives. Every migrated command should delete or replace its old embedded implementation in the same change so duplicate logic cannot drift.
