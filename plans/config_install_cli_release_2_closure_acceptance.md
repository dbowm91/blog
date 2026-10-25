# Release 2 Closure and Acceptance Pass

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/deployment/installation.md](../architecture/deployment/installation.md); this file is the historical record.

## Objective

Close Release 2 by proving that onboarding, release artifacts, the installer, filesystem layouts, legacy migration, and runtime path resolution work together from clean published artifacts outside the source checkout.

This is an integration and evidence-gathering pass. It should not expand scope into Release 3 service deployment or Release 4 update/restore lifecycle work. Correct only defects that prevent the documented Release 2 installation and migration paths from meeting their contracts.

## Release 2 scope under test

Release 2 consists of:

- Phase D: first-run and reconfiguration onboarding
- Phase E: native and Docker installer plus release artifacts
- Phase F: system, user, Docker, and development filesystem layouts and migration

The implementation already contains these subsystems. Closure requires external evidence that they compose correctly.

## Primary risks to close

1. Installer and onboarding may duplicate or disagree on installation ownership.
2. Native system and native user modes may resolve different paths than documented.
3. Docker UID/GID and volume behavior may work in unit tests but fail on a real host.
4. Onboarding may retain stale direct path logic after RuntimePaths integration.
5. Legacy migration may mishandle SQLite WAL/SHM files or interruption/resume.
6. Release workflows may build artifacts that differ from installer-smoke artifacts.
7. Published wheels may omit runtime assets despite repository-local tests passing.
8. Existing hard-coded path allowlist entries may conceal production runtime debt.
9. Installation mode terminology may remain ambiguous between native/system/user.
10. Clean installations may still depend accidentally on the repository, Node.js, or development files.

## Workstream R2C1 — freeze the installation contract

Document and test the exact ownership boundary:

- `scripts/install.sh` installs verified code artifacts and creates only minimal release/bundle scaffolding.
- `devlog onboard` creates and validates configuration, secrets, state directories, database schema, administrator state, and installation metadata.
- `RuntimePaths` is the sole authority for runtime path resolution.
- Filesystem migration moves existing mutable state but does not install application code.
- The installer must not maintain a parallel configuration schema, secret generator, profile system, or database migration implementation.

Add a focused contract test or source-level guard that fails if installer code begins generating application configuration values beyond bootstrap metadata needed to invoke onboarding.

## Workstream R2C2 — native system installation evidence

Use a clean Ubuntu LTS VM or equivalent isolated system environment with no repository checkout and no preinstalled DevLog package.

Build or download the exact release artifacts produced by the release workflow, then run the native system installer.

Required flow:

```bash
scripts/install.sh --native --system --version <version>
devlog onboard plan --mode native --scope system
devlog onboard run --mode native --scope system
devlog paths check --production
devlog config check --production
devlog db status
devlog themes list
```

If the current CLI uses different option names, align the documentation and command surface so system versus user scope is explicit.

Verify:

- versioned release under `/opt/devlog/releases/<version>`
- current release symlink points to the installed version
- executable resolves without repository paths
- `/etc/devlog`, `/var/lib/devlog`, `/var/log/devlog`, and `/run/devlog` are created with expected ownership/modes
- configuration and secret files are distinct and secret file mode is restrictive
- migrations complete on a fresh database
- administrator is created exactly once
- re-running onboarding preserves secrets and administrator state
- frontend manifest and packaged assets are present
- no Node.js or npm dependency exists at runtime
- no source checkout is required
- detailed path provenance reports metadata/system sources correctly
- production validation succeeds

Capture command output, filesystem metadata, installed version, and health/readiness results as CI artifacts or committed test fixtures where practical.

## Workstream R2C3 — native user installation evidence

Use an unprivileged user in a clean environment with isolated XDG directories.

Required flow:

```bash
export XDG_CONFIG_HOME="$TMPDIR/config"
export XDG_DATA_HOME="$TMPDIR/data"
export XDG_STATE_HOME="$TMPDIR/state"
export XDG_RUNTIME_DIR="$TMPDIR/runtime"

scripts/install.sh --native --user --version <version>
devlog onboard run --mode native --scope user --non-interactive ...
devlog paths check
devlog config check
```

Verify:

- no writes occur under `/etc`, `/var`, or `/opt`
- no root-owned files are created
- config, state, logs, runtime, uploads, themes, backups, and database resolve through XDG paths
- package executable remains available after changing working directory
- onboarding can be rerun idempotently
- user installation and system installation metadata cannot be confused
- path detection reports ambiguity if both installations exist and no mode/scope is specified

## Workstream R2C4 — Docker installation evidence

Use an empty host directory and the exact Docker bundle/image produced by the release workflow.

Required flow:

```bash
scripts/install.sh --docker --version <version>
# follow the documented onboarding command for the Docker bundle
docker compose up -d
```

Verify:

- image digest/tag matches release metadata
- Compose uses the documented `/etc/devlog`, `/data`, `/var/log/devlog`, and `/run/devlog` layout
- database, uploads, themes, backups, and exports persist after container replacement
- application starts as the documented non-root UID/GID
- named volumes work without manual host chown
- bind mounts either work under documented ownership requirements or fail with actionable diagnostics
- health endpoint becomes ready
- configuration and secret files are not baked into the image
- container replacement does not rerun destructive onboarding steps
- Redis/Celery/scheduler profiles remain coherent where selected
- Docker onboarding is non-interactive-capable

Add an installer-smoke job that consumes the release workflow's actual output artifacts or a reusable workflow artifact, rather than rebuilding semantically similar artifacts independently.

## Workstream R2C5 — release artifact identity and verification

Ensure the release workflow produces one internally consistent set:

- wheel
- source distribution
- checksum manifest
- Docker image/tag or image metadata
- Docker bundle/templates
- installer script

The installer-smoke workflow must use those artifacts unchanged.

Verify:

- checksum manifest covers every downloadable artifact
- installer rejects altered artifacts
- wheel version, CLI version, release directory, image label/tag, and metadata version agree
- wheel contains migrations, templates, static distribution assets, bundled themes, and accessibility metadata
- wheel excludes secrets, local config, databases, uploads, logs, plans, and caches
- installation from wheel works outside the repository

## Workstream R2C6 — legacy checkout migration evidence

Create a realistic legacy fixture containing:

- config.toml and `.env`
- SQLite database plus WAL and SHM files
- uploads
- external themes
- backups and exports
- logs
- an existing administrator and representative content

Run:

```bash
devlog paths discover-legacy
devlog paths migrate --dry-run
devlog paths migrate
devlog paths check --production
```

Verify:

- dry-run reports every planned action without mutation
- SQLite is checkpointed or safely quiesced before copy
- source state remains recoverable
- destination files are verified before completion metadata is written
- interruption after each migration stage can resume or fail safely
- rerun is idempotent
- existing backups are preserved and not recursively copied into themselves
- secrets retain restrictive permissions
- content, uploads, themes, and administrator login remain intact
- source cleanup is never automatic unless explicitly requested by a later lifecycle phase

Add failure injection for insufficient disk space, unwritable destination, corrupted SQLite database, missing WAL checkpoint support, and interrupted metadata write.

## Workstream R2C7 — path-system closure

Audit all allowlisted hard-coded path findings.

Classify each as:

- legitimate packaging constant
- documented development-only path
- test fixture
- remaining production runtime debt

Remove any allowlist entry representing production runtime debt. No production code should independently construct mutable-state paths where RuntimePaths provides the value.

Audit especially:

- app factory database URI
- health and metrics disk checks
- backup defaults
- upload/storage roots
- theme directories
- export/import defaults
- scheduler state
- onboarding metadata
- installer metadata

## Workstream R2C8 — mode terminology and CLI clarity

Make the relationship explicit:

```text
installation mode: native | docker
native scope: system | user
time/runtime layout: system | user | docker | development
```

Commands must not silently infer system scope when an unprivileged user intends a user install. Help, JSON plans, metadata, and docs should use consistent terms.

Add tests for:

- native system selection
- native user selection
- Docker selection
- development fallback
- ambiguous existing installations
- explicit override precedence

## Workstream R2C9 — assembled end-to-end tests

Add release-level tests that exercise the complete product rather than isolated modules.

Minimum matrix:

| Scenario | Required |
|---|---|
| clean native system install | yes |
| clean native user install | yes |
| clean Docker install | yes |
| onboarding rerun | yes |
| release artifact tamper rejection | yes |
| container replacement persistence | yes |
| legacy checkout migration | yes |
| interrupted migration resume | yes |
| install from outside repository | yes |
| runtime without Node.js | yes |

These may use containers or disposable VMs, but systemd-specific behavior is reserved for Release 3. Release 2 only needs installed artifact, path, onboarding, and application readiness evidence.

## Explicit acceptance criteria

Release 2 is closed only when all criteria below are satisfied.

1. Native system installation succeeds from verified release artifacts in a clean environment with no repository checkout.
2. Native user installation succeeds without root privileges and writes only to the selected user/XDG locations.
3. Docker installation succeeds from the published image/bundle and survives container replacement with data intact.
4. Installer-smoke tests consume the same artifacts produced by the release workflow.
5. Wheel, CLI, image, release directory, checksum manifest, and installation metadata report the same version.
6. Native runtime requires neither Node.js nor npm.
7. All required frontend assets, migrations, templates, themes, and metadata are present in installed artifacts.
8. `devlog onboard` is the sole owner of configuration, secrets, database initialization, and administrator bootstrap.
9. `RuntimePaths` is the sole owner of mutable runtime path resolution.
10. Native system versus native user scope is explicit in CLI help, plans, metadata, and docs.
11. Re-running onboarding preserves existing secrets, content, and administrator state.
12. Production configuration and path validation pass after native system and Docker onboarding.
13. Secret files have restrictive permissions and secrets do not appear in logs or JSON output.
14. Legacy migration handles SQLite WAL/SHM state safely and preserves source recoverability.
15. Legacy migration dry-run is non-mutating, rerun is idempotent, and interruption is recoverable.
16. No production runtime hard-coded path remains hidden behind the allowlist.
17. Named Docker volumes work under the documented UID/GID policy; bind-mount limitations are detected and documented.
18. Artifact tampering causes installer failure before installation mutation.
19. The full unit/integration suite, release artifact checks, installer smoke matrix, and assembled Release 2 tests pass in CI.
20. Documentation contains copy-pasteable, tested flows for native system, native user, Docker, and legacy migration.
21. Any unsupported platform or deployment limitation is stated explicitly rather than silently degraded.
22. Release 2 status documentation records the exact evidence and workflow run identifiers used for closure.

## Definition of done

Release 2 is complete when a new operator can install DevLog from published artifacts in native system, native user, or Docker mode; complete onboarding without manual configuration editing; run from packaged assets outside the source checkout; migrate an existing repository-local installation safely; and reproduce all of those paths through automated acceptance jobs.
