# Theme System Release Verification Record

Template for recording release verification of the Halloy-compatible theme system.

## Release Information

- **Release version**: 
- **Verification date**: 
- **Verified by**: 
- **Commit SHA**: 

## Build Environment

- **Python version**: 
- **Node.js version**: 
- **OS / architecture**: 

## Test Results

| Metric | Count |
|--------|-------|
| Total theme tests |  |
| Parser tests |  |
| Color primitive tests |  |
| Translation tests |  |
| CSS serialization tests |  |
| Registry tests |  |
| Security tests |  |
| Accessibility tests |  |
| Integration tests |  |
| **Total tests passed** |  |

- **Coverage**: 
- **Linter (ruff)**: pass / fail
- **Type checker (mypy)**: pass / fail

## Accessibility Results

| Tier | Theme count |
|------|-------------|
| recommended |  |
| compatible-with-exceptions |  |
| experimental |  |
| **Total themes** |  |

- **Mandatory failures (unexpected)**: 
- **Advisory warnings**: 
- **Exception manifest version**: 
- **Exception manifest reviewed date**: 

## Migration Scenarios Tested

- [ ] Fresh install (no existing database)
- [ ] Upgrade from legacy preset system (THEME_PRESETS)
- [ ] Upgrade with custom themes in external directory
- [ ] Docker build and container startup
- [ ] Wheel/sdist install with bundled themes
- [ ] `flask themes list` output correct
- [ ] `flask themes validate` on bundled catalog
- [ ] `flask themes accessibility --strict` passes
- [ ] `flask themes refresh` after external theme add/remove
- [ ] Theme save/load round-trip via admin settings

## Artifact Hashes

| Artifact | SHA-256 |
|----------|---------|
| Wheel (.whl) |  |
| Source dist (.tar.gz) |  |
| Docker image |  |

## Known Deviations

List any known deviations, regressions, or accepted risks:

| Item | Severity | Rationale |
|------|----------|-----------|
|  |  |  |

## Sign-off

- [ ] All tests pass
- [ ] Accessibility check passes (or exceptions documented)
- [ ] Migration scenarios verified
- [ ] Artifact hashes recorded
- [ ] Known deviations documented and accepted
