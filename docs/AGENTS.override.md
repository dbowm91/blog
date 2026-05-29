# Documentation Agent Override

Specialized handling for project documentation.

## Key Files

- `DEPLOY.md` - Deployment guide (SQLite/PostgreSQL)
- `USAGE.md` - Usage documentation
- `README.md` - Project overview
- `openapi.yaml` - API documentation (Swagger/OpenAPI spec)
- `AGENTS.md` - This file (agent guidelines)
- `internals/agent-maintainer-notes.md` - Historical implementation caveats, deprecated features, route corrections

## OpenAPI/Swagger UI

API documentation available at `/api/docs` via Flask-SwaggerUI:
- OpenAPI spec: `docs/openapi.yaml`
- Interactive testing interface at `/api/docs`
- All API endpoints documented with request/response schemas