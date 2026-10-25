# Release 1 Phase A — CLI Packaging and Command Infrastructure

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/deployment/cli.md](../architecture/deployment/cli.md); this file is the historical record.

## Objective

Turn DevLog into a cleanly installable Python application with a first-class `devlog` executable, stable command infrastructure, centralized output/error handling, and a packaging contract suitable for later onboarding and deployment work.

This phase is foundational. It should not attempt to implement the full installer, onboarding wizard, systemd deployment, update flow, or filesystem migration. Its purpose is to establish a reliable package and CLI shell that later phases can extend without duplicating configuration, output, or process-control behavior.

## Current problems addressed

- `pyproject.toml` identifies the package but does not yet provide a complete installable application contract comparable to EggPool.
- There is no `[project.scripts]` entry point, so operators invoke Flask or Python internals directly.
- Runtime dependencies and build-system behavior need to be authoritative in package metadata.
- CLI output, JSON output, verbosity, exception handling, and exit codes are not centralized.
- Existing Flask commands are tightly coupled to application registration and cannot serve as the long-term public operator interface.
- Clean wheel installation and execution are not release-tested.

## Non-goals

- Do not move all existing Flask commands in this phase; that belongs to Phase C.
- Do not implement the typed configuration system; Phase B owns it.
- Do not add remote installer or deployment scripts.
- Do not change production filesystem defaults yet.
- Do not remove existing `requirements*.txt` files until compatibility and CI consumers are audited.
- Do not require Node.js at runtime; frontend artifact packaging may be scaffolded here but is completed in Release 2.

## Proposed structure

Create a dedicated package, preferably under the existing source/package layout chosen by the implementation agent:

```text
devlog_cli/
    __init__.py
    main.py
    context.py
    output.py
    errors.py
    exit_codes.py
    result.py
```

If the repository adopts a `src/` layout, do so deliberately and update packaging/tests atomically. Avoid a partial migration that leaves application imports dependent on repository root behavior.

## Workstream A1 — complete package metadata

Update `pyproject.toml` so it is the authoritative package definition.

Required work:

1. Add an explicit build system, preferably setuptools or Hatchling, chosen based on current package layout and package-data requirements.
2. Declare runtime dependencies currently required by a production wheel.
3. Preserve optional development/test dependencies in a dedicated extra.
4. Ensure bundled Halloy themes, accessibility metadata, templates, migrations, static files, and other required package data are included.
5. Add the script entry point:

```toml
[project.scripts]
devlog = "devlog_cli.main:main"
```

6. Confirm package version has one authoritative source. Avoid divergent version strings between `pyproject.toml`, runtime code, container labels, and CLI output.
7. Keep package metadata accurate about supported Python versions and operating systems.
8. Add build exclusions for repository-only content such as plans, caches, local databases, logs, uploads, and secret files.
9. Verify source and wheel artifacts do not include `.env`, `config.toml`, local state, or test credentials.

### Dependency migration policy

Before moving requirements into `pyproject.toml`, compare:

- `requirements.txt`
- `requirements-dev.txt`
- Docker build requirements
- test workflow installs
- optional S3/Redis/Celery dependencies

Classify each dependency as core, optional feature extra, development-only, or deployment-only. Do not silently make experimental S3 support mandatory unless that is an explicit project decision.

Suggested extras may include:

```toml
[project.optional-dependencies]
dev = [...]
s3 = [...]
production = [...]
```

Use extras only where feature detection and user-facing error messages are clear. Avoid an excessive matrix of poorly tested combinations.

## Workstream A2 — create the root CLI

Implement `devlog` using Click, reusing the project's existing Click familiarity.

Initial root behavior:

```text
devlog --help
devlog --version
devlog --config PATH
devlog --env-file PATH
devlog --json
devlog --quiet
devlog --verbose
devlog --no-color
```

The root command should create a context object containing only stable cross-command state:

- explicit config path, if supplied
- explicit environment-file path, if supplied
- output mode
- verbosity
- color policy
- non-interactive flag when later introduced
- correlation/run identifier if useful for structured diagnostics

Do not load the Flask application or database merely to render `--help` or `--version`. Startup must remain cheap and side-effect free for commands that do not need application context.

## Workstream A3 — result and rendering model

Define a typed result contract shared by commands. A practical shape includes:

- success/degraded/failure status
- stable result code
- human summary
- optional details dictionary
- warnings array
- remediation array
- secret-safe metadata

Create separate human and JSON renderers. JSON output must have a stable top-level schema and must not contain terminal formatting.

Suggested envelope:

```json
{
  "ok": true,
  "status": "success",
  "code": "cli.version",
  "summary": "DevLog 1.0.0",
  "warnings": [],
  "details": {}
}
```

Command-specific details can evolve, but top-level fields should remain consistent. Keep secrets out of result objects rather than relying only on last-minute string redaction.

Human output requirements:

- normal mode is concise and actionable
- verbose mode includes paths and diagnostic context
- quiet mode prints only errors or explicitly requested primary output
- no-color mode is deterministic for logs and tests
- non-TTY output should avoid progress animations and ANSI escapes

## Workstream A4 — centralized errors and exit codes

Create domain-specific exception classes and one root translation layer. Suggested categories:

```text
0 success
1 general operational failure
2 invalid CLI usage
3 invalid configuration
4 required dependency unavailable
5 database or migration failure
6 service-management failure
7 backup or restore failure
8 degraded or partial success
```

Click usage errors may retain Click's standard behavior, but application exceptions should not produce unhandled tracebacks by default. `--verbose` may include tracebacks or exception chains for troubleshooting; normal output should provide a stable code and remediation.

Ensure the CLI does not call `sys.exit()` deep inside service functions. Return results or raise typed exceptions and let the root boundary choose the process exit status.

## Workstream A5 — application context boundary

Provide an explicit helper for commands that need Flask application context. It should:

1. Resolve/load configuration through the future Phase B integration point.
2. Construct the Flask application only when required.
3. Enter and close application context predictably.
4. Ensure database sessions are removed on success and failure.
5. Avoid importing command modules that trigger application construction at import time.

For this phase, a minimal adapter may call the current app factory, but leave a clear seam for Phase B's typed loader.

Do not create multiple app factories or alternate configuration initialization paths.

## Workstream A6 — initial command placeholders

Register only enough command groups to stabilize the public tree:

```text
devlog config
devlog admin
devlog db
devlog themes
devlog backup
devlog deploy
```

Unimplemented commands should not falsely appear functional. Either omit them until their phase lands or expose clearly labeled help-only groups without commands. Avoid placeholder commands that return success while doing nothing.

Implement at minimum:

- `devlog --version`
- `devlog config --help`
- `devlog admin --help`
- `devlog db --help`
- `devlog themes --help`

Actual configuration and maintenance commands arrive in Phases B and C.

## Workstream A7 — build and package validation

Add CI or scripts that perform a clean artifact test:

```bash
python -m build
python -m venv /tmp/devlog-wheel-test
/tmp/devlog-wheel-test/bin/pip install dist/devlog-*.whl
cd /tmp
/tmp/devlog-wheel-test/bin/devlog --version
/tmp/devlog-wheel-test/bin/devlog --help
```

Validation must run outside the repository so accidental import-through-working-directory behavior is detected.

Inspect wheel contents and assert inclusion of required package data and exclusion of sensitive or repository-only files.

At minimum, test:

- package import outside repo
- CLI help/version outside repo
- no Flask app startup for help/version
- JSON version output
- no ANSI output under `--no-color`
- stable exit codes for known errors
- wheel metadata and package data

## Expected files

Likely modifications/additions:

```text
pyproject.toml
devlog_cli/__init__.py
devlog_cli/main.py
devlog_cli/context.py
devlog_cli/output.py
devlog_cli/errors.py
devlog_cli/exit_codes.py
devlog_cli/result.py
tests/cli/test_root_cli.py
tests/packaging/test_wheel_contents.py
.github/workflows/ci.yml or dedicated package workflow
```

The implementation agent should adapt exact paths to repository conventions rather than introducing an unnecessary source-layout migration.

## Testing plan

### Unit tests

- result serialization
- secret-safe detail handling
- exception-to-exit-code mapping
- color/verbosity mode selection
- version resolution

### CLI tests

Use `click.testing.CliRunner` or equivalent to verify:

- root help
- root version
- JSON version envelope
- quiet and verbose behavior
- unknown option behavior
- no traceback in normal mode
- traceback/diagnostic behavior in verbose mode where intended
- command groups are registered correctly

### Packaging tests

- build wheel and sdist
- install wheel in isolated environment
- invoke CLI outside repository
- inspect artifact for required Halloy theme and template data
- reject accidental inclusion of `.env`, local config, databases, logs, uploads, or plans

## Acceptance criteria

Phase A is complete when all of the following are true:

1. `python -m build` produces valid wheel and source artifacts.
2. A clean isolated installation exposes `devlog` on `PATH`.
3. `devlog --help` and `devlog --version` work outside the repository checkout.
4. Help and version do not construct the Flask application or open the database.
5. Root output modes and global options are centralized and test-covered.
6. JSON output uses a documented stable envelope.
7. Application exceptions map to stable nonzero exit codes without default tracebacks.
8. Required package data is present in the wheel.
9. Sensitive/local files are absent from release artifacts.
10. Existing development and Docker workflows continue to work.
11. No existing Flask maintenance command is removed in this phase.

## Handoff notes

Commit this phase as a coherent packaging/CLI foundation. Avoid mixing in broad configuration refactors or command migrations, because those changes make packaging failures harder to isolate. Document any dependency that cannot yet move into `pyproject.toml` and why. Record the exact clean-install commands used for verification in the implementation commit or PR description.
