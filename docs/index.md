# DevLog Documentation

Operator and user documentation for DevLog, the Flask blog CMS. For system design and
component internals, see [the architecture index](../architecture/overview.md).

## Getting Started

| Document | Covers |
|----------|--------|
| [Installation](installation.md) | Release install, Docker, local development, CLI, configuration, database, themes |
| [Migration from a repository-local layout](migration-from-checkout.md) | Moving development checkout state to a production layout |
| [Filesystem layout](filesystem-layout.md) | The four install modes, path resolution, lifecycle policy |
| [API reference](api/posts.md) | REST API endpoints, authentication and scopes |
| [OpenAPI specification](openapi.yaml) | Machine-readable spec served at `/api/docs` |
| [Theme operator guide](themes/operator-guide.md) | Installing, validating and selecting themes |

## Themes

| Document | Covers |
|----------|--------|
| [Theme operator guide](themes/operator-guide.md) | Admin selection, external theme workflow, CLI commands |
| [Supported theme schema](themes/supported-schema.md) | The Halloy TOML input contract for theme authors |
| [BlogTheme token contract](themes/blog-theme-contract.md) | The 50 semantic tokens and 38 legacy aliases the translator emits |
| [Cache freshness contract](themes/cache-contract.md) | Invalidation semantics and multi-worker behaviour |
| [Accessibility policy](themes/accessibility-policy.md) | Exception classes and the three eligibility tiers |
| [Legacy compatibility](themes/legacy-compatibility.md) | What changed when the legacy preset system was removed |
| [Migration boundary](themes/migration-boundary.md) | The theme-related Alembic migrations and their rollback |
| [Frontend literal audit](themes/frontend-literal-audit.md) | Which hardcoded colours were replaced with tokens, and which were kept |
| [Release verification](themes/release-verification.md) | How the theme system is verified before a release |

## Maintainer Notes

[Agent maintainer notes](internals/agent-maintainer-notes.md) record implementation
caveats, route corrections and gotchas that are not obvious from the code alone.

## Root-Level Documents

- [README](../README.md) — project overview and feature list
- [Usage guide](../USAGE.md) — day-to-day admin usage
- [Deployment guide](../DEPLOY.md) — production deployment
- [Architecture](../ARCHITECTURE.md) — architecture index (see also [`architecture/`](../architecture/overview.md))
- [Security policy](../SECURITY.md) — vulnerability reporting
- [Contributing](../CONTRIBUTING.md) — development workflow
- [Release checklist](../RELEASE.md) — release process
- [Changelog](../CHANGELOG.md) — release history

## See Also

- [Architecture overview](../architecture/overview.md) — the authoritative system design index
- [Operator CLI reference](../architecture/deployment/cli.md) — every `devlog` command
- [API routes](../architecture/routes/api-routes.md) — API blueprint internals
