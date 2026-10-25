# Documentation Agent Override

Specialized handling for project documentation.

## Key Files

- `index.md` — entry point for this directory
- `installation.md` — install, configure and operate DevLog
- `filesystem-layout.md` — install modes and path resolution
- `migration-from-checkout.md` — moving a development checkout to a production layout
- `api/posts.md` — REST API reference
- `openapi.yaml` — OpenAPI 3 specification
- `themes/` — theme system documentation (schema, token contract, cache, policy)
- `internals/agent-maintainer-notes.md` — historical implementation caveats, deprecated
  features, route corrections

The repository-root `AGENTS.md` holds the general agent guidelines; this file only
adds the module-specific overrides for `docs/`.

## OpenAPI/Swagger UI

The API documentation is available at `/api/docs` via Flask-SwaggerUI:

- OpenAPI spec: `docs/openapi.yaml`
- Interactive testing interface: `/api/docs`
- The spec must cover every endpoint registered in `app/routes/api/`

## Conventions

- Links from a file in `docs/` to the repository root are `../<file>`; to
  `architecture/` they are `../architecture/...`; to `docs/themes/` from `docs/` they
  are `themes/...`. Verify every relative link resolves before finishing.
- Prefer symbolic references (function, class, module and command names) over line
  numbers. Line numbers drift.
- The authoritative system design lives in `architecture/`. When a document here
  duplicates it, keep a short operator-facing summary and link to the architecture
  page instead of maintaining two copies.
- Verify every factual claim against the source before writing it down.
