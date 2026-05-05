# Planning Override Rules

When working in the `plans/` directory, adhere to the following rules:

1. **Living Document**: The primary source of truth for upcoming work is `plans/plan.md`. When tasks are completed, they should be checked off (e.g. `- [x]`) and/or moved to a completed section within the file.
2. **Parallel Execution**: The plan is organized into "Waves" (e.g., Wave 4, Wave 5). Tasks within a wave, and sometimes entire waves, may be executed in parallel by subagents. 
3. **No Fragmented Plans**: Do not create fragmented plan files (like `plan2.md`, `plan3.md`). All strategic roadmap items must be consolidated into `plan.md`.
4. **Actionable Detail**: Any new task added to `plan.md` must be specific enough that a future agent can execute it without needing external context. Include specific file paths, class/function names, and clear success criteria.