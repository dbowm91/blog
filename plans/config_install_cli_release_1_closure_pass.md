# Release 1 Closure Pass — Packaging, CI, and Legacy Configuration Containment

## Objective

Close the remaining Release 1 gaps before beginning onboarding and installation work. The implementation is architecturally complete, but the package boundary, CI verification, unknown-key policy, and legacy configuration compatibility layer still need explicit closure.

This pass should be narrow. It must verify and harden the existing Release 1 implementation without introducing Release 2 onboarding, installer, service deployment, or filesystem migration behavior.

## Current state

Release 1 has delivered:

- a first-class `devlog` console entry point
- package metadata and wheel/sdist support
- typed configuration loading, validation, profiles, provenance, and migration scaffolding
- app-factory integration with typed configuration
- extracted operational services for admin, database, search, media, transfer, themes, and backup primitives
- standalone CLI commands and transitional Flask wrappers
- broad unit, CLI, parity, configuration, and packaging tests

The remaining risks are operational rather than architectural:

1. CI still installs primarily from `requirements*.txt`, while package installation is defined by `pyproject.toml`.
2. The latest clean-wheel acceptance path is not a dedicated release-gating workflow.
3. `devlog_cli` is not clearly included in type-check coverage.
4. Unknown configuration keys are surfaced, but production severity needs to be explicit and test-covered.
5. `app/config_legacy.py` remains available without a documented containment/removal contract.
6. Clean-wheel tests should prove at least one real application-context operation, not only root CLI startup.
7. GitHub status reporting for direct commits is not sufficient evidence of a full closure run; CI should emit explicit jobs for this boundary.

## Non-goals

- Do not implement `devlog onboard`.
- Do not add the remote installer.
- Do not change production filesystem layout.
- Do not add systemd, Caddy, nginx, or Compose generators.
- Do not remove all requirements files unless every consumer is migrated in the same change.
- Do not remove `config_legacy.py` if remaining compatibility imports still require it; contain it instead.
- Do not redesign the typed configuration model.

## Workstream 1 — make package installation authoritative in CI

Add a dedicated CI path that installs DevLog through project metadata rather than only through `requirements-dev.txt`.

Recommended commands:

```bash
python -m pip install --upgrade pip
pip install -e '.[dev]'
```

or, for artifact verification:

```bash
python -m pip install build
python -m build
python -m venv /tmp/devlog-wheel
/tmp/devlog-wheel/bin/pip install dist/devlog-*.whl
```

Requirements:

- Keep requirements-based jobs temporarily where they validate Docker or historical deployment compatibility.
- Add `pyproject.toml` to dependency cache keys.
- Add a consistency test or script that compares direct runtime requirements with package metadata if both manifests remain.
- Document which file is authoritative.
- Fail CI if requirements files and `pyproject.toml` drift in package names or incompatible version bounds.

Suggested utility:

```text
scripts/check_dependency_manifest_consistency.py
```

The script should normalize package names, extras, and version ranges sufficiently to catch meaningful drift without pretending different syntaxes are byte-equivalent.

## Workstream 2 — dedicated clean-wheel Release 1 job

Create a separate CI job such as `release1-package-smoke` that:

1. Builds wheel and sdist.
2. Creates an isolated virtual environment outside the repository.
3. Installs the wheel.
4. Changes working directory outside the checkout.
5. Runs root CLI checks.
6. Initializes a development configuration.
7. Validates it.
8. Lists themes from packaged data.
9. Initializes a temporary database or application instance.
10. Runs at least one real app-context command.

Suggested sequence:

```bash
python -m build
python -m venv /tmp/devlog-r1
/tmp/devlog-r1/bin/pip install dist/devlog-*.whl
cd /tmp
/tmp/devlog-r1/bin/devlog --version
/tmp/devlog-r1/bin/devlog config init \
  --profile development \
  --config /tmp/devlog-config.toml
/tmp/devlog-r1/bin/devlog \
  --config /tmp/devlog-config.toml \
  config check
/tmp/devlog-r1/bin/devlog \
  --config /tmp/devlog-config.toml \
  themes list
```

Then run an application-context operation using isolated state. Acceptable examples:

- `devlog db status`
- `devlog db migrate`
- `devlog db check`
- `devlog admin list`

The test must not accidentally import code from the checkout. Explicitly clear `PYTHONPATH` and run from `/tmp` or an equivalent isolated directory.

## Workstream 3 — include the CLI in static analysis

Update lint/type jobs to cover both application and CLI packages.

At minimum:

```bash
ruff check app devlog_cli tests
ruff format --check app devlog_cli tests
mypy app devlog_cli
```

If `devlog_cli` cannot immediately pass the same mypy policy as `app`, define an explicit temporary configuration section with a bounded list of suppressions. Do not omit the package silently.

Add tests for:

- command registration import safety
- absence of import-time app construction
- typed result serialization
- no secret-bearing values in CLI context or rendered output

## Workstream 4 — finalize unknown-key policy

Define severity by configuration generation/version and validation mode.

Recommended policy:

- Unversioned legacy config: unknown keys are warnings with migration guidance.
- `config_version = 1` config: unknown keys are errors.
- `--production`: unknown sections/fields/top-level keys are always errors.
- `config init` output must pass strict unknown-key validation.

Implement stable finding codes such as:

```text
schema.unknown_section
schema.unknown_field
schema.unknown_top_level_key
```

Add tests proving:

- typo in a versioned production config fails.
- typo in a versioned development config fails or follows the explicitly chosen policy.
- legacy config reports warnings but remains loadable during the compatibility window.
- unknown keys never silently influence defaults.

Update the configuration reference to state this behavior.

## Workstream 5 — contain `config_legacy.py`

Audit all remaining imports of `app.config_legacy` and classify them:

- unavoidable compatibility consumer
- test-only consumer
- stale consumer that should migrate immediately
- dead code

Add a document or module-level table recording the remaining consumers and their removal condition.

Requirements:

1. Add a prominent module docstring declaring the file compatibility-only.
2. Forbid new imports outside an explicit allowlist test.
3. Add a test that searches the repository for `config_legacy` imports and fails when new consumers appear.
4. Ensure the module does not independently parse configuration if it can project values from the typed loader.
5. Ensure missing `config.toml` remains safe for clean installs.
6. Emit deprecation warnings only where they do not pollute normal CLI output or tests.
7. Define deletion criteria for a future release.

Preferred direction:

```text
typed loader -> compatibility projection -> legacy consumers
```

Avoid:

```text
typed loader and legacy loader independently parse the same files
```

## Workstream 6 — verify package data completeness

Extend wheel-content tests to confirm inclusion of all runtime data needed outside the repository:

- bundled themes and catalog manifest
- accessibility exception metadata
- templates
- static CSS/JS required for non-Vite fallback
- migration scripts and Alembic configuration if package execution requires them
- default/profile templates if shipped as files
- OpenAPI documentation if runtime routes serve it

Explicitly verify exclusion of:

- `.env`
- `config.toml`
- local databases and WAL/SHM files
- uploads
- logs
- backups
- plans
- test fixtures containing credentials
- caches and build artifacts

If migration files are not currently packaged but wheel-based `db migrate` needs them, fix packaging before declaring closure.

## Workstream 7 — full Release 1 acceptance run

Run and record:

- all unit tests
- configuration tests
- CLI tests
- service tests
- parity tests
- packaging tests
- migration tests
- theme policy tests
- Docker build
- clean-wheel smoke test
- type/lint/format checks

Add a short closure document or update plan status with:

- commands executed
- CI job names
- remaining known limitations
- legacy compatibility boundary
- explicit Release 2 readiness statement

## Expected files

Likely changes:

```text
.github/workflows/ci.yml
pyproject.toml
requirements.txt
requirements-dev.txt
scripts/check_dependency_manifest_consistency.py
app/config_legacy.py
app/config/validation.py
tests/packaging/test_wheel_contents.py
tests/packaging/test_clean_install.py
tests/config/test_unknown_key_policy.py
tests/config/test_legacy_import_boundary.py
docs or architecture configuration reference
```

## Acceptance criteria

Release 1 is closed when:

1. A dedicated CI job builds and installs the wheel in an isolated environment.
2. Root CLI, config initialization, config validation, theme listing, and at least one app-context operation work outside the repository.
3. `devlog_cli` is linted and type-checked.
4. Package and requirements manifests cannot silently drift.
5. Unknown keys fail in production and follow a documented version-aware policy.
6. `config_legacy.py` is compatibility-only, import-contained, and no longer an independent configuration authority.
7. Required migrations and package data are present in the wheel.
8. Sensitive/local files are excluded from artifacts.
9. All Release 1 focused and full test suites pass.
10. The repository has an explicit recorded statement that Release 2 may begin.

## Handoff sequencing

Implement in this order:

1. CI/package install authority.
2. Clean-wheel smoke job.
3. Static-analysis coverage.
4. Unknown-key severity policy.
5. Legacy configuration containment.
6. Package-data verification.
7. Full closure run and documentation.

Do not begin Release 2 onboarding until the clean-wheel application-context smoke test passes. Release 2 should build on the installed artifact, not repository-local execution assumptions.
