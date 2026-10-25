# Release 2 Phase E — One-Shot Installer and Production Release Artifacts

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/deployment/installation.md](../architecture/deployment/installation.md); this file is the historical record.

## Objective

Provide a small, auditable one-shot installer for native and Docker modes, backed by versioned release artifacts that contain all runtime code and frontend assets required for production.

The installer must install DevLog and its launcher, verify what it installs, and hand control to `devlog onboard`. It must not become a second onboarding/configuration implementation.

## Dependencies

- Release 1 closure pass complete
- isolated wheel installation and app-context smoke tests passing
- `devlog onboard` implemented or available on the target release artifact
- package data includes migrations, templates, themes, and production frontend assets
- typed path/configuration APIs available

## Non-goals

- Do not embed configuration prompts in shell.
- Do not manually create database/admin state from the installer.
- Do not install reverse proxies or systemd units; later deployment commands own that.
- Do not silently modify firewall, DNS, TLS, or package repositories.
- Do not support every Linux distribution in the initial release.
- Do not use a cloned source tree as the native production installation.

## Supported installation modes

### Native system install

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native
```

Preferred backend order should be explicit and tested. A reasonable default is:

1. install a versioned wheel into an application-managed virtual environment under `/opt/devlog/venv`, with a stable launcher in `/usr/local/bin/devlog`; or
2. use `uv tool install`/`pipx` only if system deployment semantics and service paths remain predictable.

Do not depend on the current source checkout.

### Native user install

```bash
curl -fsSL .../scripts/install.sh | bash -s -- --native --user
```

Install beneath XDG/user paths and ensure the launcher location is communicated clearly.

### Docker install

```bash
curl -fsSL .../scripts/install.sh | bash -s -- --docker
```

Install a lightweight host-side DevLog management wrapper plus versioned Compose/templates or create an installation directory containing verified deployment assets. Docker mode must not require host Python.

## Workstream E1 — artifact strategy

Define release artifacts:

- Python wheel
- source distribution
- container image
- checksums manifest
- installer script
- optional Compose/template bundle
- optional SBOM/provenance attestation

All artifacts must be versioned consistently.

The wheel must contain:

- application and `devlog_cli`
- migrations
- templates
- bundled Halloy themes and metadata
- built frontend assets and Vite manifest
- runtime static files
- any configuration/profile templates loaded at runtime

The container image must contain the same application version and frontend build.

## Workstream E2 — production frontend packaging

Native production installation must not invoke npm.

Release build pipeline:

1. install pinned Node dependencies with `npm ci`
2. run production asset build
3. verify manifest and expected entrypoints
4. build wheel after assets exist
5. inspect wheel contents
6. install wheel in a clean environment and create the application

Do not allow source fallback paths to mask a missing production bundle in release artifacts.

Add a build-time or package-time failure when expected production assets are absent.

## Workstream E3 — installer design

Create `scripts/install.sh` with strict shell behavior:

```bash
set -euo pipefail
```

Supported options:

```text
--native
--docker
--user
--system
--version VERSION
--prefix PATH
--channel stable|prerelease
--non-interactive
--dry-run
--yes
--no-onboard
--help
```

Installer phases:

1. Parse options.
2. Detect OS/architecture.
3. Select supported backend.
4. Check prerequisites.
5. Resolve target version.
6. Download artifacts and checksum manifest.
7. Verify checksums/signatures where provided.
8. Install into a temporary/versioned target.
9. Verify `devlog --version`.
10. Atomically update stable launcher/symlink.
11. Print or invoke onboarding according to explicit policy.

The remote bootstrap script should remain small. Complex logic may be delegated to a versioned installer artifact after verification.

## Workstream E4 — prerequisite policy

Initial supported native environment should be narrow and documented, likely Ubuntu LTS/Debian stable with Python 3.12+.

The installer may detect missing prerequisites, but should not aggressively modify the system without explicit approval.

Native checks:

- supported OS and architecture
- Python version
- venv support
- curl or equivalent downloader
- CA certificates
- permissions for selected prefix
- SQLite runtime features if relevant

Docker checks:

- Docker Engine
- Compose plugin
- daemon availability
- permission to communicate with Docker
- supported Compose version

Unsupported environments should fail with actionable manual installation instructions.

## Workstream E5 — artifact verification and supply-chain safety

Requirements:

- fetch versioned artifacts over HTTPS
- download checksum manifest separately
- verify SHA-256 before extraction/install
- reject partial downloads
- avoid executing unverified downloaded shell/Python
- pin exact target version once resolved
- do not silently fall back from a requested version
- record installed version and artifact digest

Optional later hardening may add Sigstore/GitHub attestations, but checksum verification is mandatory for initial release.

## Workstream E6 — native installation layout

Install application code atomically into versioned directories, for example:

```text
/opt/devlog/releases/1.1.0/venv/
/opt/devlog/current -> /opt/devlog/releases/1.1.0
/usr/local/bin/devlog -> /opt/devlog/current/venv/bin/devlog
```

User equivalent should use XDG/local paths.

Rules:

- never mix mutable user data into release directories
- do not overwrite an existing release in place
- verify new release before moving `current`
- preserve at least the prior release for future rollback logic
- set sane ownership and permissions
- avoid running the service as root

Full update/rollback orchestration belongs to Release 4, but installation layout should make it possible.

## Workstream E7 — Docker installation bundle

Docker mode should create a predictable installation root containing:

```text
compose.yaml
.env or devlog.env
config/config.toml
data/
uploads/
themes/
backups/
installation metadata
```

At install time, only deployment templates and launcher/wrapper should be created. `devlog onboard --mode docker` should populate configuration and secrets.

Use immutable/versioned image tags. Do not default production deployments to `latest`.

Host publication should remain loopback-only by default until a reverse proxy is configured.

## Workstream E8 — installer/onboarding boundary

Default successful installer output:

```text
DevLog <version> installed successfully.
Next: devlog onboard --mode native
```

An optional explicit flag may run onboarding immediately when a TTY is present:

```bash
... | bash -s -- --native --onboard
```

Do not auto-run interactive onboarding when stdin is occupied by a pipe unless the implementation reopens `/dev/tty` safely and explicitly. The default should be install-only plus next-step output.

## Workstream E9 — development setup separation

Rename/reposition the current repository setup script:

```text
setup.sh -> scripts/setup-dev.sh
```

Update contributor docs to use the development script. It may:

- create `.venv`
- install `.[dev]`
- install npm dependencies
- build frontend assets
- prepare local development config

Production docs must not direct users to the development script.

Keep a temporary compatibility wrapper at `setup.sh` if needed, with a deprecation message.

## Workstream E10 — release CI

Add release jobs for:

- frontend build
- wheel/sdist build
- container build
- artifact content verification
- clean native installation test
- Docker installation bundle test
- checksums generation
- version consistency
- installer shellcheck
- installer dry run
- supported-platform smoke tests

Installer tests should use local test artifacts rather than downloading from an unreleased public URL.

Test version selection, checksum failure, unsupported platform, interrupted installation, existing installation, permissions failure, and idempotent re-run.

## Workstream E11 — failure and recovery semantics

If installation fails before activation:

- remove temporary release files
- preserve current installation
- return nonzero
- print exact failure stage

If activation fails after installing a release:

- restore previous launcher/current pointer
- preserve failed release for diagnostics or remove only when safe
- never delete config/data

Installer re-run should detect:

- same version already installed
- newer version installed
- partial temporary install
- existing unmanaged install

Do not silently take ownership of an unmanaged install without confirmation.

## Expected files

```text
scripts/install.sh
scripts/setup-dev.sh
scripts/check_release_artifacts.py
scripts/generate_checksums.py
pyproject.toml
MANIFEST/package data configuration
Dockerfile
compose templates
.github/workflows/release.yml
.github/workflows/installer-smoke.yml
tests/installer/*
docs/installation.md
```

## Acceptance criteria

Phase E is complete when:

1. A supported clean native host can install DevLog from verified release artifacts with one command.
2. A supported Docker host can install the Docker management bundle without host Python.
3. The native installation does not require Node.js.
4. Wheel and container include built frontend assets, migrations, templates, and themes.
5. Installer verifies checksums before execution/install.
6. Installation is atomic and preserves an existing working version on failure.
7. Installer does not create or overwrite user configuration independently of onboarding.
8. Development setup is clearly separated from production installation.
9. Installer behavior is covered by local-artifact CI smoke tests.
10. Installed `devlog --version` matches the selected artifact version.

## Handoff sequencing

Implement in this order:

1. production frontend-in-wheel build
2. release artifact and version consistency
3. native versioned layout
4. native installer
5. Docker bundle installer
6. checksum verification
7. development-script separation
8. CI smoke/failure tests
9. documentation

Do not publish the remote curl command until local-artifact installation tests are stable and the target release actually contains `devlog onboard`.
