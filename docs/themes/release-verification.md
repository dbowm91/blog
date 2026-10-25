# Theme System Release Verification

How the theme system is verified before a release, and which checks each party —
CI, the operator, the theme author — is responsible for.

## Automated Gates

Three CI jobs cover the theme system. They live in `.github/workflows/ci.yml`.

| Job | Command | What it proves |
|-----|---------|----------------|
| `theme-policy` | `python scripts/theme_accessibility_report.py --strict` | Every theme in the authoring catalogue translates, and no theme has unexpected mandatory accessibility failures |
| `migration-chain` | `python -m pytest tests/test_migration_chain.py tests/test_migration_drop_theme_preset.py` | The Halloy migration revisions apply, downgrade and re-apply cleanly |
| `theme-package-verification` | `python scripts/verify_theme_package.py dist/*.whl` | The built wheel ships all 50 bundled `.toml` files |

The theme tests live in `tests/themes/` and are also picked up by the main `test`
job, which runs the whole suite with coverage.

> The `theme-policy` job passes `--strict` to `scripts/theme_accessibility_report.py`.
> The script itself has no `--strict` option — it always exits non-zero when any
> theme has mandatory accessibility failures. Verify the flag before relying on
> the job as a gate.

## Accessibility Gate

The catalogue's accessibility state is recorded in
`app/themes/ACCESSIBILITY_EXCEPTIONS.json`.

```bash
# Report the catalogue's accessibility state
python scripts/theme_accessibility_report.py

# JSON output
python scripts/theme_accessibility_report.py --json

# The operator-facing equivalent. Note that --strict only rejects *external*
# themes with unexpected mandatory failures; it never rejects a bundled theme.
flask themes accessibility --strict
devlog themes accessibility --strict
```

The `scripts/theme_accessibility_report.py` script exits non-zero when any theme
in the catalogue has a mandatory accessibility failure, and it is the gate that
covers the bundled themes. `flask themes accessibility --strict` and
`devlog themes accessibility --strict` reject external themes that have
unexpected mandatory failures.

The manifest's `summary` block records the current classification:

| Tier | Meaning | Bundled themes |
|------|---------|----------------|
| `recommended` | Zero mandatory failures, zero expected exceptions | 5 |
| `compatible-with-exceptions` | Every mandatory failure has a documented exception | 33 |
| `experimental` | At least one mandatory failure with no matching exception | 12 |
| **Total** | | **50** |

The manifest also records `schema_version` (2), `validator_version` (`1.0`),
`policy_version` (`1.0`) and `reviewed_date`. See
[the accessibility policy](accessibility-policy.md) for the tier definitions and
the exception classes.

## Migration Scenarios Covered

`tests/test_migration_chain.py` and `tests/test_migration_drop_theme_preset.py`
cover the schema side:

| Scenario | Test |
|----------|------|
| Fresh install produces the correct schema | `test_fresh_install_creates_correct_schema` |
| Legacy preset values map to Halloy names | `test_preset_mapping_applied` |
| The visitor's colour scheme survives the upgrade | `test_preserve_legacy_scheme` |
| The `theme_preset` column is dropped | `test_drop_theme_preset_removes_column` |
| Upgrade → downgrade → re-upgrade round trip | `test_full_chain_round_trip` |

`tests/themes/test_runtime_acceptance.py` and `tests/test_admin_theme_acceptance.py`
cover the runtime side:

| Scenario | Test |
|----------|------|
| `flask themes list` emits valid JSON | `test_cli_list_outputs_json` |
| Every bundled theme translates | `test_bundled_theme_translates` |
| `flask themes accessibility --strict` passes with no external themes present | `test_cli_accessibility_strict_flag_passes_with_no_external` |
| Saving a valid theme persists it | `test_save_valid_theme_persists` |
| The settings page renders the current theme names | `test_settings_page_shows_current_theme_names` |
| An invalid theme name is rejected | `test_save_invalid_dark_theme_rejects` |
| The preview does not persist | `test_preview_does_not_persist` |
| The emergency fallback renders a complete palette | `test_emergency_fallback_renders_complete_palette` |
| A public page never 500s on a theme failure | `test_public_page_never_500s_on_theme_failure` |

## Operator Verification Checklist

Before promoting a release:

```bash
# Lint and format
ruff check .
ruff format --check .

# Type check
mypy app/ devlog_cli/

# Theme tests
ADMIN_PASSWORD=... SECRET_KEY=... python -m pytest tests/themes/ -v

# Accessibility
flask themes accessibility --strict

# Catalog inventory
python scripts/theme_inventory.py
```

## Theme Author Checklist

When adding or changing a theme in the authoring catalogue at `themes/`:

1. The file parses under the [supported schema](supported-schema.md)
2. `python scripts/theme_accessibility_report.py` reports no unexpected mandatory
   failures for it
3. The file is mirrored into `app/themes/bundled/` so it ships with the package
4. `python scripts/theme_inventory.py` reports the expected catalogue size
5. `tests/themes/test_bundled_integrity.py` passes

## Historical Record

The final verification pass of the Halloy theme system was completed on
2026-07-14 at commit `f829f5e7d21a0efd15a5fe98dd6933178a3d6808`, against
Python 3.12.3 and Node.js 22.23.1 on Linux x86_64. The results of that pass are
recorded in the git history of this file; the live gates above are the source of
truth for the current state.

## See Also

- [Accessibility policy](accessibility-policy.md) — tier definitions and exception classes
- [Theme operator guide](operator-guide.md) — the operator-facing commands
- [Theme architecture](../../architecture/core/themes.md) — the module reference for `app/themes/`
