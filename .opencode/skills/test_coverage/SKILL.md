# Test Coverage Improvement Skill

## Triggers
- Test coverage, increase coverage, coverage goal, pytest-cov, coverage report
- Low coverage files, missing statements, cover modules

## Description
Guidelines for increasing test coverage in the Blog CMS codebase.

## Workflow
1. **Check Current Coverage**
   ```bash
   source venv/bin/activate && pytest tests/ -m "not e2e" --cov=app --cov-report=term-missing -q --timeout=300
   ```

2. **Identify Low-Coverage Files**
   - Look for files with < 80% coverage in the report
   - Focus on high-impact files first (many missing statements)

3. **Create Test Files**
   - Follow naming convention: `tests/test_<module>.py`
   - Use `pytest` with `unittest.mock` for mocking
   - Use `Flask.test_client()` or `authenticated_client` fixture for routes
   - Use `CliRunner` for CLI commands

4. **Common Patterns**
   - **Route Tests**: Use `authenticated_client` fixture, check status codes and response data
   - **Function Tests**: Mock dependencies, check return values and side effects
   - **Database Tests**: Use `db` fixture, create model instances, verify changes

5. **Fix Common Issues**
   - **404 Errors**: Check route prefixes (e.g., `/admin` for admin routes)
   - **CSRF Errors**: Disable CSRF in tests via `app.config["CSRF_ENABLED"] = False`
   - **Session Issues**: Re-query objects instead of using `db.session.refresh()`
   - **Mock Errors**: Patch at the correct module level (where the function is used, not where it's defined)

6. **Commit Progress**
   - Commit after each module's tests are added
   - Update `plans/plan.md` with new coverage numbers
   - Run full test suite to verify no regressions

## Examples
- Increased `app/routes/admin/series.py` from 17% → 74%
- Increased `app/tasks.py` from 18% → 67%
- Increased `app/utils.py` from 46% → 67%
- Increased total coverage from 53% → ~75%

## Tools
- `pytest` with `--cov=app` for coverage reports
- `unittest.mock.patch` for mocking
- `Flask.test_client()` for route tests
- `CliRunner` for CLI tests
