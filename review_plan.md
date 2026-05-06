# Architecture Review Plan

Review each architecture module by having subagents verify document claims against actual code, identify bugs, and propose improvements.

## Modules and Subagents

| Module | Docs | Subagent Task |
|--------|------|---------------|
| [Core](core/) | app-factory.md, models.md, configuration.md | Review core app architecture |
| [Routes](routes/) | admin-routes.md, public-routes.md, api-routes.md, rss-feeds.md | Review route handlers |
| [Services](services/) | backup.md, slug.md, serialization.md, tag.md | Review service layer |
| [Tasks](tasks/) | celery-tasks.md, scheduler.md | Review background task system |
| [Infrastructure](infrastructure/) | email.md, search.md, storage.md, webhooks.md | Review infrastructure services |
| [Frontend](frontend/) | templates.md, static-assets.md | Review frontend architecture |
| [Deployment](deployment/) | docker.md, cicd.md, security.md, overview.md | Review deployment setup |
| [Testing](testing/) | test-suite.md | Review testing infrastructure |

## Review Instructions for Subagents

Each subagent will:
1. Read all documents in their designated module
2. Identify claims and assertions in the documents
3. Locate relevant source code files
4. Verify each claim against the actual implementation
5. Identify discrepancies, bugs, or outdated information
6. Propose code improvements
7. Write findings to `plans/{module}_review.md`

## Execution

```bash
# Launch all module reviews in parallel via Task tool
```

## Output

Each subagent writes an improvement plan to `plans/{module}_review.md` containing:
- Verified claims
- Discrepancies found
- Bugs identified
- Improvement recommendations
- Priority (high/medium/low)