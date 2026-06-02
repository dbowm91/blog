# Plans Module Override

## Overview

This module contains the consolidated architecture improvement plan.

## Consolidated Plan

`plans/plan.md` is the single source of truth for all pending architecture work. Items have been verified against the actual codebase.

## Wave Structure

| Wave | Focus | Items | Status |
|------|-------|-------|--------|
| 1 | Source Code Fixes | 11 | COMPLETED |
| 2 | Documentation Corrections | 12 | COMPLETED |
| 3 | Source Code Improvements | 12 | COMPLETED |
| 4 | Documentation Additions | 34 | COMPLETED |
| 5 | Additional Source Code Fixes | 10 | PENDING |
| 6 | Additional Documentation Corrections | 41 | PENDING |
| 7 | Additional Source Code Improvements | 15 | PENDING |

## Execution Notes

- All items within a wave are fully independent
- Source code changes (Wave 5) should generally land before documentation referencing corrected code (Waves 6-7)
- Each item includes file paths, line numbers, current code, and expected changes
- Subagents can execute items autonomously with minimal research
- Recommended batch size: 4-6 subagents per wave

## Maintenance Notes

When updating code that affects documented behavior:
1. Update the relevant AGENTS.override.md for that module
2. If adding new behavior, consider updating AGENTS.md Important Notes
3. If documentation becomes stale, update architecture docs or add a note in agent-maintainer-notes.md
4. Prefer symbolic references (function names) over line numbers to reduce maintenance burden

## Parallelization Guidance

Waves 5-7 can be executed in parallel since they operate on independent files:
- Wave 5: Source code fixes (app/tasks.py, app/services/*.py, app/routes/api/series.py, app/models.py)
- Wave 6: Documentation corrections (architecture/*.md files)
- Wave 7: Source code improvements (app/static/js/*.js, app/context_processors.py, tests/*.py, .github/workflows/ci.yml)