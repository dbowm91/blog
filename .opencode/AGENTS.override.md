# OpenCode Config Agent Override

Specialized handling for agent tool configuration.

## Skills Directory

The canonical skills live in `.skills/`. `.opencode/skills/<name>/SKILL.md` is a
**symlink** to `.skills/<name>/skill.md`, so the opencode agent and every other
agent read the same file. Never edit a copy — edit the file in `.skills/`.

| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | The codebase map, hard rules, gotchas and known defects | Flask app, SQLAlchemy, CSRF, newsletter, APScheduler, FTS5, REST API, 2FA, comments, themes, appearance layer, `devlog` CLI, config.toml, onboarding, filesystem paths, systemd, compose, nginx |
| `release_validation` | The pre-release gate and how to diagnose a failing stage | release, tag, version bump, release check, lint, mypy, pytest, vite build, docker build, compose config |
| `e2e_testing` | Browser-level testing with Playwright | E2E tests, playwright, pytest-playwright, UI testing |
| `architecture_review` | Architecture documentation review workflow | architecture, review, documentation, verify, cross-reference |

Load a skill using the `skill` tool with the skill name (e.g. `skill: blog_cms`).

## Agent Override Convention

This codebase uses a **module-level override system** for agent context. Each module (directory with a specific purpose) may contain an `AGENTS.override.md` file that provides specialized handling instructions for that module.

When an agent operates within a module, it should:
1. Read the root `AGENTS.md` for general guidance
2. Check for `AGENTS.override.md` in the current module for specialized handling
3. Override files take precedence over root-level guidance when working within that module

## Package.json

Minimal Node.js configuration for Vite frontend build.

## Planning

Plan status is tracked in `plans/AGENTS.override.md`. Read it before planning
new work — it declares which plan series are active and which are historical,
and points at the architecture document that now holds each outcome.

Do not derive a plan from a phase file in isolation: the phase files are
historical records of work that has already shipped, and the roadmap files
supersede them.

## Known Implementation Issues

Verified against the source on 2026-10-25. These are the defects the code
review surfaced and that are **not yet fixed**:

- `app/routes/admin/series.py` — the create, update and delete handlers call
  `flash(f"Error …: {str(e)}")`, which exposes internal exception text to the
  operator.
- `app/themes/colors.py` — `shift_lightness()` computes `q` with an identical
  expression in both branches of the `lightness < 0.5` test, so dark colours
  take the light-colour path. `#161b22` shifted by `+0.06` returns `#002459`
  where a reference HSL conversion gives `#222a35`.
- `app/services/operations/deploy.py` — `_build_context()` reads
  `current_app.config["DEVLOG_CONFIG"]`, which the app factory never sets, so
  the whole `devlog deploy` group raises `KeyError` outside the test suite.
- `devlog_cli/commands/deploy.py` — `deploy render` defaults `--target` to
  `["all"]`, but the service dispatches only on concrete target names, so it
  renders zero files by default.
- `devlog_cli/commands/config.py` — `config explain` raises `TypeError` for at
  least `admin.username`, `database.pool_size` and `logging.level`.

Each has a "Notes and Gotchas" entry in the relevant document under
`architecture/`.
