# Release 1 Phase B — Typed Configuration Core, Validation, and Path Resolution

## Objective

Create one authoritative, typed, versioned configuration system used by the Flask application, standalone CLI, tests, and all later onboarding/deployment work.

This phase must eliminate configuration ambiguity without prematurely implementing the installer or onboarding wizard. The central deliverable is a trustworthy configuration pipeline with explicit precedence, path resolution, validation, provenance, secret handling, and stable CLI commands.

## Current problems addressed

- Configuration is split across `config.toml`, `.env`, Flask defaults, Docker environment, and database-backed site settings.
- Several values, especially SMTP credentials, appear in more than one configuration surface.
- The precedence of duplicate values is not sufficiently explicit.
- Example defaults can form incoherent combinations, such as local HTTP URLs with secure-cookie behavior intended for HTTPS production.
- There is no comprehensive `check-config` equivalent that validates production invariants before startup.
- Unknown TOML keys and misspellings can be difficult to detect.
- Path discovery is implicit and repository-oriented.
- Later installer, doctor, service, and update commands need one shared loader rather than independent parsing.

## Non-goals

- Do not implement interactive onboarding in this phase.
- Do not create systemd or Docker deployment artifacts.
- Do not move production data to new filesystem locations yet; define and test path resolution so Release 2 can perform migration safely.
- Do not remove database-backed editable site settings unless the existing application contract requires it.
- Do not add live configuration reloading.
- Do not silently reinterpret unsupported PostgreSQL or S3 behavior as production-ready.

## Proposed module structure

```text
app/config/
    __init__.py
    model.py
    loader.py
    paths.py
    validation.py
    provenance.py
    secrets.py
    profiles.py
    migration.py
    serialization.py
```

Exact naming may follow repository conventions, but responsibilities must remain separated. Avoid a single monolithic configuration module.

## Workstream B1 — inventory and classify every setting

Create a configuration inventory before changing behavior. Audit:

- `config.toml.example`
- `.env.example`
- Flask configuration classes/defaults
- app factory environment reads
- `docker-compose.yml` and profiles
- Celery and scheduler setup
- Redis/cache/rate-limit configuration
- storage backends
- backup and webhook encryption
- theme configuration
- health/metrics configuration
- test fixtures and CI environment
- database-backed `SiteSettings`

For each setting, record:

- canonical field name
- type
- current default
- source locations
- whether secret
- allowed environment override
- startup/reload semantics
- production validation rules
- whether user-editable through admin UI
- deprecation or migration requirement

The inventory should be represented in code/tests or a maintained configuration reference, not only in implementation notes.

## Workstream B2 — define configuration ownership and precedence

Establish the following contract:

```text
explicit CLI override
  > process environment
  > selected config.toml
  > built-in defaults
```

Secrets should be sourced only from process environment, selected environment file, or supported secret-file references. Remove secret values from TOML examples where they create ambiguous ownership.

Clarify database-backed site settings. Recommended policy:

- operational and security settings remain file/environment owned
- presentation/content settings may remain database owned
- database settings must not override server bind, security, storage, database, Redis, scheduler, or secret configuration
- where both layers can affect appearance, document exact precedence and retain backwards compatibility

Do not allow arbitrary environment-variable expansion inside TOML unless implemented deliberately with escaping and clear security semantics.

## Workstream B3 — typed model

Implement typed sections corresponding to the application's actual domains, for example:

```text
AppConfig
AdminConfig
ServerConfig
SiteConfig
EmailConfig
NewsletterConfig
CommentsConfig
ThemesConfig
DatabaseConfig
RedisConfig
CeleryConfig
SchedulerConfig
StorageConfig
HealthConfig
MetricsConfig
BackupConfig
SecurityConfig
LoggingConfig
```

Use dataclasses, Pydantic, attrs, or an equivalent library already acceptable to the project. The chosen approach must support:

- strict type validation
- defaults
- nested sections
- unknown-key detection
- cross-field validation
- redacted representation
- canonical serialization
- useful error locations

Do not expose raw secret values through `repr`, model dumps, log messages, or JSON output.

## Workstream B4 — versioning and migrations

Add a top-level configuration version:

```toml
config_version = 1
```

Implement a migration registry even if only version 1 exists initially. The registry should support:

- detecting missing/legacy version
- generating a migration plan
- dry-run output
- atomic replacement
- bounded backup of prior configuration
- explicit failure for future unsupported versions

Provide:

```bash
devlog config migrate --dry-run
devlog config migrate
```

Do not auto-rewrite configuration during ordinary application startup. Startup may report that migration is needed, but mutation should be explicit except during a controlled installer/update workflow in later releases.

## Workstream B5 — path resolution

Implement deterministic path resolution with source tracking.

Configuration path precedence:

```text
--config PATH
DEVLOG_CONFIG
/etc/devlog/config.toml for system mode
$XDG_CONFIG_HOME/devlog/config.toml
~/.config/devlog/config.toml
./config.toml
```

Environment file precedence:

```text
--env-file PATH
DEVLOG_ENV_FILE
/etc/devlog/devlog.env
$XDG_CONFIG_HOME/devlog/devlog.env
~/.config/devlog/devlog.env
./.env
```

Because installation mode is not fully implemented until Release 2, avoid blindly preferring `/etc/devlog` for ordinary developer commands. Resolution should account for explicit mode or existence and should be documented/tested to prevent surprising selection of stale files.

The resolver should report:

- selected path
- why it was selected
- other candidates considered
- existence
- file type
- ownership and permissions where available
- readability/writability

Add `devlog config paths` with human and JSON output.

## Workstream B6 — environment-file loading

Replace ad hoc shell sourcing semantics with a predictable parser suitable for the application.

Requirements:

- no shell execution
- no command substitution
- support standard `KEY=value` syntax used by the repository
- preserve process-environment precedence over environment-file values
- identify duplicate keys
- report malformed entries
- never print secret values
- permit explicit disabling of environment-file loading when needed for tests/automation

The setup script's current `source .env` behavior must not become the application's parser contract.

## Workstream B7 — configuration profiles

Implement profiles that produce coherent initial configuration without embedding secrets:

- `development`
- `native-production`
- `docker-production`
- `minimal`
- `full`

Profiles should define only non-secret values and required-secret declarations. Examples:

Development:

- loopback bind by default
- `http://localhost:5000`
- secure cookies disabled
- debug explicit and limited to development
- scheduler disabled unless selected

Native production:

- loopback bind behind reverse proxy
- HTTPS public URL required or placeholder marked invalid
- secure cookies enabled
- debug disabled
- one proxy by default only when reverse proxy selected

Docker production:

- container bind may use `0.0.0.0`
- host publication remains loopback by deployment template
- secure cookies enabled for HTTPS public URL
- scheduler ownership explicit

Add:

```bash
devlog config init --profile development
devlog config init --profile native-production
devlog config init --profile docker-production
```

`config init` must refuse to overwrite existing files unless `--force` is explicit, and even then should preserve a backup and perform an atomic write.

## Workstream B8 — validation layers

Implement validation in distinct layers so errors are actionable.

### Schema validation

- valid TOML
- expected sections
- known fields
- correct types
- range and enum checks

### Filesystem validation

- config/environment file permissions
- required directories exist or can be created
- database parent writable
- uploads/logs/backups writable where configured
- external theme directory validity
- frontend manifest availability when production mode requires it

### Security validation

- required secrets present
- no obvious placeholder values
- minimum secret strength/length
- debug disabled in production
- public bind explicitly acknowledged
- secure cookies consistent with public URL
- metrics enabled only with dedicated secret
- detailed health protected in production
- proxy count coherent with deployment mode

### Dependency validation

- Redis required only when selected features need it
- Celery configuration complete when enabled
- S3 fields complete when S3 backend selected
- SMTP fields complete when email enabled
- scheduler enabled on exactly one intended process/container

### Compatibility validation

- SQLite-supported features not represented as healthy on unsupported database backends
- theme names resolve
- config version supported
- migration revision compatibility where available

Categorize findings as errors, warnings, and informational notes. Production-strict mode should elevate specific unsafe warnings to errors.

## Workstream B9 — CLI commands

Implement:

```text
devlog config init
devlog config check
devlog config show
devlog config explain FIELD
devlog config paths
devlog config migrate
```

### `config check`

Options:

```text
--production
--json
--config PATH
--env-file PATH
--no-filesystem
```

JSON should use stable finding identifiers:

```json
{
  "ok": false,
  "status": "failure",
  "code": "config.invalid",
  "summary": "Configuration validation failed",
  "details": {
    "config_path": "/etc/devlog/config.toml",
    "findings": [
      {
        "severity": "error",
        "code": "session.secure_cookie_http_url",
        "field": "site.base_url",
        "message": "Secure cookies are enabled but the public URL uses HTTP.",
        "remediation": "Use an HTTPS public URL or disable secure cookies only for local development."
      }
    ]
  },
  "warnings": []
}
```

### `config show`

Default output must redact secrets. `--effective` should show resolved values and sources. There should be no general-purpose `--show-secrets` option.

### `config explain`

Show type, default, effective value where non-secret, source, environment override, production notes, and restart requirement.

## Workstream B10 — application integration

Refactor the app factory to consume the typed effective configuration rather than independently reading TOML/environment values.

Requirements:

- one loader path for CLI and web application
- tests may inject a typed configuration or explicit overrides
- no import-time global loading
- startup errors are structured and actionable
- legacy environment names remain supported through an explicit compatibility map where required
- deprecated keys produce warnings and migration guidance

Do not break Flask-Migrate invocation or test fixtures. The implementation should include compatibility adapters until Phase C command migration is complete.

## Expected files

Likely additions/modifications:

```text
app/config/__init__.py
app/config/model.py
app/config/loader.py
app/config/paths.py
app/config/validation.py
app/config/provenance.py
app/config/secrets.py
app/config/profiles.py
app/config/migration.py
app/config/serialization.py
app/__init__.py or app factory module
config.toml.example
.env.example
devlog_cli/commands/config.py
tests/config/*
tests/cli/test_config_commands.py
```

## Testing plan

### Loader tests

- explicit path wins
- process environment wins over environment file
- environment file wins over TOML only for mapped fields
- TOML wins over built-in defaults
- unknown keys fail
- malformed TOML reports location
- secret values remain redacted
- config loading has no filesystem mutation

### Path tests

- explicit paths
- XDG paths
- system-mode paths
- local development fallback
- nonexistent candidates
- symlink/file-type handling
- permission reporting

### Validation tests

- HTTP URL plus secure cookies
- public bind in production
- missing/placeholder secrets
- metrics without secret
- detailed health without secret
- SMTP partial configuration
- S3 partial configuration
- Redis/Celery contradictions
- multiple scheduler ownership indicators
- missing frontend manifest
- invalid external theme directory/theme name
- unsupported database feature warnings

### CLI tests

- human and JSON `config check`
- production-strict exit status
- `config show` redaction
- `config explain`
- `config init` no-overwrite and atomic force behavior
- migration dry run
- no ANSI under `--no-color`

### Regression tests

- existing development startup
- Docker configuration startup
- Flask app factory tests
- migration commands
- theme tests
- scheduler/Celery initialization tests

## Acceptance criteria

Phase B is complete when:

1. The web application and standalone CLI use the same typed loader.
2. Configuration precedence is explicit, documented, and test-covered.
3. Unknown TOML keys are rejected or surfaced as errors.
4. Secret values are never emitted by config show, validation, exceptions, logs, or JSON.
5. `devlog config check` detects schema, filesystem, security, dependency, and compatibility failures.
6. `--production` converts unsafe production states into nonzero failures.
7. `devlog config paths` explains selected and candidate paths.
8. `devlog config init` creates coherent profiles atomically without secrets.
9. Configuration has an explicit version and migration scaffold.
10. Legacy configuration remains loadable through documented compatibility behavior.
11. `.env.example` and `config.toml.example` no longer present ambiguous secret ownership.
12. Existing Docker and local development tests remain green.

## Handoff notes

Treat this phase as the single source of truth for all later work. The implementation agent should resist creating onboarding-specific or deployment-specific parsers. Any setting that cannot be cleanly classified should be documented as an explicit unresolved compatibility decision rather than hidden in loader conditionals. Include a generated or maintained configuration inventory in the implementation so future fields cannot bypass schema and documentation review.
