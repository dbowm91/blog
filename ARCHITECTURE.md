# Architecture

The architecture documentation for DevLog lives in the [`architecture/`](architecture/)
directory. **`architecture/overview.md` is the index** — it names every discrete
module, explains how they fit together, and links each one to a deep-dive
document.

```markdown
[Architecture Overview](architecture/overview.md) — the module map and index
```

| Area | Directory | Covers |
|---|---|---|
| Core | `architecture/core/` | App factory, configuration, models, filesystem layout, onboarding, theme system |
| Routes | `architecture/routes/` | Public, admin, API and feed handlers |
| Services | `architecture/services/` | Business-logic services, operations services, doctor |
| Tasks | `architecture/tasks/` | Celery queues and APScheduler jobs |
| Infrastructure | `architecture/infrastructure/` | Search, email, storage, webhooks, health |
| Frontend | `architecture/frontend/` | Templates, static assets, the appearance layer |
| Deployment | `architecture/deployment/` | Operator CLI, managed deployment, security, install, Docker, CI/CD |
| Testing | `architecture/testing/` | The pytest, E2E and benchmark suites |

For the review workflow that keeps these documents accurate, see
`.skills/architecture_review/skill.md`.
