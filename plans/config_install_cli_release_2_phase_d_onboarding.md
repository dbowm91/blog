# Release 2 Phase D — Interactive and Non-Interactive Onboarding

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/onboarding.md](../architecture/core/onboarding.md); this file is the historical record.

## Objective

Implement `devlog onboard` as the authoritative first-run and reconfiguration workflow for both native and Docker installations.

The command must take a user from an installed DevLog package to a validated, initialized, runnable instance without requiring manual edits to `.env`, `config.toml`, Flask commands, or repository-local scripts. It must also support deterministic non-interactive automation for CI, configuration management, and future remote installers.

## Dependencies

This phase depends on completed Release 1 work:

- installable `devlog` package and CLI
- typed configuration loader
- configuration profiles and validation
- atomic configuration serialization
- path resolution and provenance
- reusable admin, database, theme, and backup services
- clean-wheel application-context verification

Do not implement private onboarding-specific configuration parsing. All configuration generation and validation must use the Release 1 configuration APIs.

## Non-goals

- Do not install Python, Docker, system packages, or the DevLog wheel; Phase E owns installation.
- Do not install systemd/Caddy/nginx units; Release 3 owns deployment generation.
- Do not implement application update or uninstall.
- Do not migrate arbitrary legacy production layouts automatically without a separately validated migration path.
- Do not start long-running services through ad hoc detached subprocesses.

## User journeys

### First-time native onboarding

```bash
devlog onboard --mode native
```

Expected result:

- installation mode selected
- paths resolved
- config and secret files generated
- directories created
- configuration validated
- database migrated
- first administrator created
- packaged frontend assets verified
- readiness probe run where possible
- clear next command printed

### First-time Docker onboarding

```bash
devlog onboard --mode docker
```

Expected result:

- host-side config and secret files generated
- Compose-compatible paths selected
- Docker-specific configuration profile used
- generated files validated without requiring the app container to already be running
- next `devlog start` or Compose deployment step printed

### Re-running onboarding

Re-running must detect existing state and offer only safe actions:

```text
inspect current installation
repair missing directories/permissions
update non-secret settings
rotate selected secrets explicitly
create/reset administrator explicitly
validate only
resume interrupted initialization
```

No existing secret, database, upload, theme, or backup data may be overwritten implicitly.

### Non-interactive automation

```bash
devlog onboard \
  --mode native \
  --profile native-production \
  --non-interactive \
  --site-url https://blog.example.com \
  --admin-username admin \
  --admin-password-file /run/secrets/devlog_admin_password \
  --accept-defaults
```

Missing required values must cause a structured failure rather than an interactive prompt.

## Workstream D1 — onboarding state machine

Implement onboarding as an explicit state machine or ordered step runner rather than one large command function.

Suggested steps:

```text
DetectInstallation
ResolveMode
ResolvePaths
CollectInputs
BuildProposedConfig
ResolveSecrets
PlanFilesystemChanges
ValidateProposal
WriteConfig
WriteSecrets
CreateDirectories
RunMigrations
CreateAdministrator
VerifyAssets
RunReadinessChecks
WriteInstallationMetadata
RenderCompletion
```

Each step should declare:

- inputs
- outputs
- whether it mutates state
- preconditions
- rollback/compensation behavior
- whether it is safe to repeat
- stable failure code

Persist enough installation metadata to distinguish a completed install from a partially initialized one, but do not create a second configuration authority. Metadata may include installation mode, package version, onboarding completion version, and managed path list.

## Workstream D2 — mode and profile selection

Supported modes:

- `native`
- `docker`
- optionally `user` if treated distinctly from native system installation

Default selection rules:

- explicit `--mode` wins
- existing installation metadata wins on re-run
- interactive prompt when ambiguous
- non-interactive ambiguity is an error

Map modes to profiles deliberately:

```text
native + development          -> development
native + production           -> native-production
docker + production           -> docker-production
```

Do not infer production solely from hostname. Require explicit profile or interactive choice.

## Workstream D3 — input model and prompts

Create a typed onboarding input model separate from the final configuration model.

Collect or derive:

- installation mode
- profile
- site title and description
- public base URL
- bind address and port
- reverse-proxy expectation
- admin username
- admin password source
- email/newsletter enablement
- SMTP host/port/from address and credential source
- scheduler enablement and ownership
- Redis/Celery enablement
- storage backend
- backup directory and encryption choice
- default themes/scheme

Prompt design:

- show defaults clearly
- validate at entry time where practical
- do not echo secrets
- permit back/cancel before mutation
- summarize proposed changes before apply
- use explicit confirmation for public binds, disabled secure cookies in non-development mode, or destructive replacements

## Workstream D4 — safe secret handling

Generate or accept:

- `SECRET_KEY`
- admin bootstrap password
- health secret
- metrics secret when metrics enabled
- backup encryption key when encryption selected
- webhook encryption key when required

Rules:

- prefer secret files, environment variables, stdin, or hidden prompts
- do not accept secrets as ordinary CLI options unless explicitly marked unsafe
- do not print generated secrets in normal logs
- if a generated admin password must be shown once, render it only to an interactive TTY with a clear one-time warning and never in JSON
- environment/secret file mode must be `0600`
- preserve existing secret values on re-run
- rotation must be a separate explicit action

## Workstream D5 — proposed-change planning and dry run

Support:

```bash
devlog onboard --dry-run
devlog onboard --plan --json
```

The plan should list:

- files to create/update
- directories to create
- permissions to set
- migrations to run
- administrator action
- validation findings
- service/deployment next steps

Never include secret values. Mark each action as create, preserve, update, skip, or conflict.

## Workstream D6 — atomic application of configuration

Before mutation:

1. Load existing state if present.
2. Build complete proposed typed configuration.
3. Resolve secret references.
4. Run schema and production validation against proposed paths.
5. Check filesystem feasibility.
6. Present plan/confirmation.

Apply order should minimize unrecoverable partial state:

1. Create directories with restrictive permissions.
2. Write temporary config and secret files.
3. Re-read and validate temporary files.
4. Atomically publish configuration.
5. Run migrations.
6. Create/update administrator.
7. Verify assets and app creation.
8. Write completion metadata.

If migrations or admin creation fail, preserve configuration but mark onboarding incomplete and provide an exact resume command. Do not delete an existing database.

## Workstream D7 — database initialization

Use extracted database services.

Requirements:

- detect whether database exists
- inspect migration status
- run migrations once
- handle fresh database and existing database separately
- never call `db.create_all()` as an alternative to migrations in production onboarding unless that is already the supported migration bootstrap
- report migration revision
- ensure sessions are closed
- preserve database on failure

For new installations, run a post-migration integrity and search capability check.

## Workstream D8 — administrator bootstrap

Use the admin service rather than `flask create-admin`.

Rules:

- create only when no administrator exists, unless explicit reset/promote action selected
- do not overwrite an existing password implicitly
- validate password policy before database mutation
- support password file/stdin in non-interactive mode
- remove bootstrap password from environment/config after successful creation if it is only needed for bootstrap
- record only non-secret completion metadata

## Workstream D9 — asset and runtime verification

Verify packaged runtime assets:

- Vite manifest or production frontend bundle
- templates
- bundled themes
- migrations
- OpenAPI/static resources required at runtime

For native mode, create the Flask application and run an internal readiness check without starting a persistent detached process.

For Docker mode, verify host-side files and image/Compose prerequisites where available; do not require network pulls unless explicitly requested.

## Workstream D10 — structured completion and resume

Human completion should state:

- installation mode
- config path
- data path
- public URL
- administrator username
- validation status
- next command
- warnings requiring operator action

JSON output should include stable fields and no secrets.

Interrupted onboarding should be resumable:

```bash
devlog onboard --resume
```

The command should recompute current state rather than blindly trusting stale progress metadata.

## Workstream D11 — reconfiguration policy

On existing installations, distinguish:

- non-secret safe edits
- secret rotation
- path migration
- database migration
- administrator reset
- deployment change

This phase may support safe non-secret edits and explicit admin reset, but path migration and deployment conversion should be deferred unless implemented with dedicated verification.

Do not allow changing native to Docker mode in place without an explicit migration plan.

## Expected files

```text
devlog_cli/commands/onboard.py
app/onboarding/model.py
app/onboarding/state.py
app/onboarding/steps.py
app/onboarding/planner.py
app/onboarding/secrets.py
app/onboarding/metadata.py
app/onboarding/rendering.py
tests/onboarding/*
tests/cli/test_onboard.py
docs/installation.md
```

## Testing plan

### Unit tests

- state transitions
- mode/profile mapping
- secret preservation/rotation policy
- dry-run plan generation
- atomic file staging
- resume-state detection
- completion redaction

### CLI integration tests

- interactive development onboarding
- non-interactive native production onboarding
- non-interactive Docker onboarding
- missing required non-interactive values
- existing installation re-run
- conflict handling
- dry run
- JSON output
- cancellation before mutation

### Failure injection

- unwritable config directory
- secret-file write failure
- validation failure
- migration failure
- admin creation failure
- missing packaged assets
- interrupted run after config publication
- stale/incomplete metadata

### End-to-end

From an isolated wheel installation:

1. Run non-interactive onboarding into a temporary root.
2. Verify config/secrets permissions.
3. Verify migration revision.
4. Verify administrator exists.
5. Create app and hit readiness internally or through a temporary foreground server.
6. Re-run onboarding and prove idempotency.

## Acceptance criteria

Phase D is complete when:

1. A clean installed wheel can run `devlog onboard` without repository access.
2. Native and Docker modes generate coherent validated configurations.
3. Interactive and non-interactive flows share the same planner and step runner.
4. Secrets are generated/stored safely and never exposed in JSON or logs.
5. Re-running onboarding preserves existing data and secrets by default.
6. Configuration writes are atomic.
7. Migrations and admin creation use shared services.
8. Partial failures are resumable and clearly reported.
9. Dry-run output accurately describes all planned mutations.
10. End-to-end onboarding succeeds in CI from a clean wheel installation.

## Handoff sequencing

Implement in this order:

1. onboarding state/input model
2. planner and dry-run
3. secret resolution
4. filesystem/config apply steps
5. migration/admin steps
6. verification and completion metadata
7. resume/re-run behavior
8. full end-to-end tests

Keep installer concerns out of this phase. Phase E should only ensure the package and prerequisites are installed, then invoke or direct the user to this onboarding command.
