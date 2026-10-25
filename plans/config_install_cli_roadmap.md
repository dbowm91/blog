# DevLog Configuration, Installation, and Operator CLI Roadmap

> **Plan status: MIXED — Releases 1–3 shipped, Release 4 still open.** The `## Status` section below predates the implementation and is stale. See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

## Status

Implementation roadmap for converting DevLog from a repository-oriented Flask deployment into an installable, validated, operator-friendly self-hosted application.

Releases 1–3 have shipped; Release 4 is still open. This section was written before the implementation began and originally read "Proposed implementation roadmap". For the current position — including which Release 4 work is outstanding — see the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

## Problem statement

DevLog already has most of the underlying operational primitives required for a production self-hosted service: Docker Compose deployment, a local setup script, database migrations, Flask CLI maintenance commands, backup and restore support, theme management, health endpoints, and deployment documentation. The remaining problem is that these capabilities are exposed through several unrelated surfaces:

- repository-local `setup.sh`
- direct `python run.py` execution
- `python -m flask` commands
- Docker Compose profiles
- `.env`
- `config.toml`
- database-backed site settings
- manual reverse-proxy and service configuration

This creates avoidable setup cost and makes routine operations dependent on repository knowledge. The target is a stable product CLI and installation contract comparable to EggPool:

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash
devlog onboard
sudo devlog deploy systemd --install
devlog status
```

The roadmap preserves Docker and native installation, but both modes must share the same configuration model, validation, onboarding, migration, backup, diagnostics, and lifecycle services.

## Guiding principles

1. **One public management surface.** Operators should use `devlog`, not implementation-specific Flask, Python, npm, or Compose commands for normal administration.
2. **Thin CLI handlers.** Click handlers parse input, call service-layer functions, render output, and map failures to stable exit codes. Business logic must remain reusable.
3. **Validation before mutation.** Configuration, deployment, restore, and update commands must validate prerequisites before changing persistent state.
4. **Atomic and idempotent writes.** Configuration and secret files must be written atomically. Re-running install or onboarding must preserve existing state unless replacement is explicit.
5. **Separate code from mutable data.** Production database, uploads, themes, backups, logs, and runtime files must not depend on a writable source checkout.
6. **Secrets stay out of normal configuration output.** Secret values belong in environment files or referenced secret files and must be redacted from human and JSON output.
7. **Production packages include frontend assets.** Native production installation must not require Node.js.
8. **Docker and native are first-class, explicit modes.** Development setup remains separate from production installation.
9. **Machine-readable automation is supported.** Applicable commands provide stable JSON schemas, exit codes, non-interactive operation, and dry-run behavior.
10. **Compatibility is transitional, not permanent duplication.** Existing Flask commands should delegate to shared services while the standalone CLI becomes authoritative.

## Desired end state

### Supported installation paths

Native:

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native
devlog onboard --mode native
sudo devlog deploy systemd --install
```

Docker:

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --docker
devlog onboard --mode docker
devlog start
```

Development:

```bash
./scripts/setup-dev.sh
```

### Target command tree

```text
devlog onboard

devlog serve
devlog start
devlog stop
devlog restart
devlog status
devlog logs

devlog config init
devlog config check
devlog config show
devlog config explain
devlog config paths
devlog config migrate

devlog admin create
devlog admin reset-password
devlog admin list

devlog db migrate
devlog db status
devlog db check
devlog db rebuild-search

devlog backup create
devlog backup list
devlog backup inspect
devlog backup verify
devlog backup restore
devlog backup prune

devlog themes list
devlog themes validate
devlog themes inspect
devlog themes refresh
devlog themes accessibility

devlog deploy systemd
devlog deploy compose
devlog deploy caddy
devlog deploy nginx
devlog deploy logrotate
devlog deploy all

devlog doctor
devlog update
devlog uninstall
```

Common options should include `--config`, `--env-file`, `--json`, `--quiet`, `--verbose`, and `--no-color` where applicable.

## Configuration contract

### Ownership

`config.toml` owns non-secret behavior: site metadata, public URL, server binding, pagination, newsletter behavior, SMTP host/port/from address, scheduler policy, theme selection, storage backend selection, backup policy, logging, proxy topology, and feature flags.

Environment variables or referenced secret files own sensitive values: Flask secret key, bootstrap/admin password, SMTP password, API credentials, Redis/S3 credentials, backup and webhook encryption keys, metrics secret, and detailed-health secret.

Duplicated secret fields should be removed from TOML examples. Database-backed site settings may remain for runtime-editable presentation settings, but their precedence relative to file configuration must be explicit.

### Precedence

Effective value precedence:

```text
command-line override
  > environment variable
  > config.toml
  > built-in default
```

Configuration path precedence:

```text
--config
  > DEVLOG_CONFIG
  > /etc/devlog/config.toml for system installs
  > XDG user config path
  > ./config.toml
```

Environment file precedence follows the same pattern through `--env-file`, `DEVLOG_ENV_FILE`, system/XDG paths, then `./.env`.

### Profiles

Provide coherent profiles for `development`, `native-production`, `docker-production`, `minimal`, and `full`. Profiles must enforce internally consistent defaults rather than relying on users to reconcile HTTP URLs, secure cookies, public bind addresses, proxy counts, schedulers, Redis, Celery, and metrics authentication manually.

### Schema and migration

Introduce a typed, versioned model with unknown-key detection, cross-field validation, secret redaction, canonical serialization, and field provenance. Configuration should carry `config_version`, with explicit migrations through `devlog config migrate`.

## Release structure

### Release 1 — CLI and configuration foundation

Release 1 creates the architecture on which all later operational work depends.

- Phase A: package metadata and standalone `devlog` CLI foundation
- Phase B: typed configuration loader, path resolution, validation, profiles, and provenance
- Phase C: extract existing Flask CLI business logic into reusable services and expose initial standalone admin/database/theme commands

Exit condition: a clean wheel install provides `devlog`; configuration is loaded through one authoritative path; invalid production configuration fails before startup; and existing maintenance functions are callable through both the new CLI and transitional Flask wrappers.

Detailed handoff plans:

- `plans/config_install_cli_release_1_phase_a_cli_packaging.md`
- `plans/config_install_cli_release_1_phase_b_configuration_core.md`
- `plans/config_install_cli_release_1_phase_c_service_extraction.md`

### Release 2 — onboarding, installer, and filesystem layout

- Interactive and non-interactive `devlog onboard`
- One-shot native and Docker installer
- Production wheel/image artifacts with built frontend assets
- System, user, and Docker filesystem layouts
- Atomic creation of configuration, secret files, directories, migrations, and initial administrator
- Existing-install detection and safe resume/reconfiguration behavior

Exit condition: a new user can install and reach a working admin login without cloning the repository or manually editing multiple files.

### Release 3 — deployment and diagnostics

- systemd, Compose, Caddy, nginx, and logrotate generation/install commands
- Backend-aware `start`, `stop`, `restart`, `status`, and `logs`
- `ExecStartPre` configuration validation
- Hardened systemd unit and explicit writable paths
- `devlog doctor` with human and JSON output

Exit condition: DevLog can be deployed and diagnosed as a persistent service through the product CLI.

### Release 4 — data safety and lifecycle

- Unified backup create/list/inspect/verify/restore/prune commands
- Versioned backup manifests and restore compatibility checks
- Pre-restore backup, quiescing, temporary restore, validation, and atomic replacement
- Safe update workflow with backup, config migration, database migration, health verification, and application rollback
- Data-preserving uninstall and explicit destructive purge

Exit condition: operators can safely maintain, upgrade, recover, and remove DevLog without repository-specific procedures.

### Release 5 — documentation and release hardening

- Rewrite README around Docker, native, and development paths
- Complete CLI/configuration/filesystem/update/backup/troubleshooting references
- Clean-install, onboarding, Compose startup, systemd validation, backup/restore, upgrade, and uninstall CI matrices
- ARM64 coverage where available
- Release checklist, checksums, and artifact verification

Exit condition: all documented production paths are continuously tested and suitable for public release.

## Cross-release requirements

### Output and exit codes

Use central result types and a single exception-to-exit-code mapping. Suggested classes are success, usage error, invalid configuration, missing dependency, database/migration failure, service-management failure, backup/restore failure, and degraded/partial success. JSON output must remain stable and never serialize secret-bearing objects directly.

### Testing

Every phase must include unit tests for pure logic, CLI integration tests using isolated filesystems, and end-to-end tests where behavior crosses packaging or runtime boundaries. Failure-injection coverage should include interrupted writes, missing frontend assets, migration failures, unwritable paths, corrupt databases, invalid backups, unavailable Redis/SMTP, insufficient disk space, failed service startup, and failed post-update readiness.

### Security

Generated secret files default to mode `0600`; services run as non-root; public binding requires an explicit profile or choice; production validation rejects debug mode and unauthenticated metrics/detailed health; installers pin and verify artifacts; restore validates before replacement; uninstall preserves data unless purge is explicitly confirmed.

### Documentation

Commands and configuration fields must document defaults, overrides, secret status, restart/reload requirements, and production implications. Copy-pasteable commands should be exercised in CI where practical.

## Sequencing constraints

- Release 1 Phase A must establish the CLI context and package entry point before Phase B command integration.
- Phase B owns path resolution and configuration loading; later phases must not create parallel loaders.
- Phase C extracts service logic before onboarding, doctor, update, or deployment commands are built on top of it.
- Onboarding must use the Phase B validator and atomic writers rather than implementing private configuration logic.
- Deployment generation must consume effective typed configuration, never parse TOML independently.
- Update and restore must depend on verified backup primitives and health checks, not ad hoc subprocess sequences.

## Definition of completion

This roadmap is complete when a new operator can run:

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash
devlog onboard
sudo devlog deploy systemd --install
devlog status
devlog doctor --production
```

and when the equivalent Docker path is equally direct. The native package must not require Node.js; configuration must be typed, versioned, validated, and provenance-aware; mutable data must be outside source code; backup/restore and update paths must be verified end to end; uninstall must preserve data by default; and clean installation and upgrade paths must be release-gated in CI.
