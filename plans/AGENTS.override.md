# Plans Module Override

Specialized handling for project planning and roadmap execution.

## Plan Execution Pattern

When executing multi-wave implementation plans:

1. **Create separate branches** for each parallel wave to avoid conflicts
2. **Use subagents** with separate branches to parallelize work
3. **Merge to master** after each wave completes
4. **Update plan status** in plan.md after each phase
5. **Commit** at each logical step

### Branch Naming Convention
```
wave-a-frontend-core-docs
wave-a-routes-docs
wave-a-testing-docs
wave-b-code-improvements
wave-c-configuration
```

### Subagent Usage
- Launch subagents in parallel for independent wave items
- Each subagent works on its own branch
- Review completed work before merging
- Do not let subagents overwrite each other's changes

## Plan Structure

Plans are organized into:
- **Phases**: Logical groupings of related changes
- **Waves**: Items that can be parallelized
- **Status**: Pending, In Progress, Completed, Deferred

## Deferred Items

Items deferred due to scope are tracked in plan.md with:
- Reason deferred
- Original phase reference
