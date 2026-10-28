from __future__ import annotations

import ast
from pathlib import Path


class TestLegacyDocstring:
    def test_config_legacy_has_deprecation_docstring(self) -> None:
        module_path = Path(__file__).resolve().parents[2] / "app" / "config_legacy.py"
        source = module_path.read_text()
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree)
        assert docstring is not None
        assert "DEPRECATED" in docstring
        assert "compatibility" in docstring.lower()

    def test_config_init_has_backward_compat_docstring(self) -> None:
        module_path = Path(__file__).resolve().parents[2] / "app" / "config" / "__init__.py"
        source = module_path.read_text()
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree)
        assert docstring is not None
        assert "backward" in docstring.lower()


class TestLegacyNoFrameworkImports:
    def test_config_legacy_does_not_import_flask(self) -> None:
        module_path = Path(__file__).resolve().parents[2] / "app" / "config_legacy.py"
        source = module_path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "flask" not in alias.name.lower()
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    assert "flask" not in node.module.lower()

    def test_config_legacy_does_not_import_sqlalchemy(self) -> None:
        module_path = Path(__file__).resolve().parents[2] / "app" / "config_legacy.py"
        source = module_path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "sqlalchemy" not in alias.name.lower()
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    assert "sqlalchemy" not in node.module.lower()


class TestLegacyGlobalsExist:
    def test_config_legacy_globals_are_set(self) -> None:
        from app import config_legacy

        expected_globals = [
            "APP_TITLE",
            "APP_DESCRIPTION",
            "POSTS_PER_PAGE",
            "SECRET_KEY",
            "MAX_VIEWED_POSTS",
            "SESSION_LIFETIME_HOURS",
            "SESSION_IP_BINDING",
            "ADMIN_USERNAME",
            "ADMIN_PASSWORD",
            "SERVER_HOST",
            "SERVER_PORT",
            "DEBUG",
            "AUTHOR_NAME",
            "AUTHOR_ROLE",
            "AUTHOR_AVATAR",
            "BASE_URL",
            "CDN_URL",
            "RELATED_POSTS_COUNT",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "FROM_ADDRESS",
            "SMTP_TIMEOUT",
            "NEWSLETTER_SEND_TIME",
            "CONFIRMATION_EXPIRY_HOURS",
            "TAG_CACHE_TTL_SECONDS",
            "NEWSLETTER_MAX_RETRY_ATTEMPTS",
            "DASHBOARD_PER_PAGE",
            "SUBSCRIBERS_PER_PAGE",
            "MEDIA_PER_PAGE",
            "MEDIA_MAX_FILES",
            "MAX_UPLOAD_SIZE",
            "EXPORT_BATCH_SIZE",
            "FTS_RESULT_LIMIT",
            "PAGE_VIEW_BUFFER_SIZE",
            "ANALYTICS_DAYS_MIN",
            "ANALYTICS_DAYS_MAX",
            "TOKEN_ENUMERATION_DELAY",
            "LOGIN_FAILURE_DELAY",
            "PREVIEW_TOKEN_EXPIRY_DAYS",
            "HEALTH_CHECK_SECRET",
            "METRICS_SECRET",
            "ENABLE_METRICS",
            "RATE_LIMIT_STORAGE_URI",
            "REDIS_URL",
            "DATA_BACKUP_DIR",
            "WEBHOOK_TIMEOUT",
            "WEBHOOK_ENCRYPTION_KEY",
            "COMMENT_MIN_LENGTH",
            "COMMENT_MAX_LENGTH",
            "COMMENT_RATE_LIMIT_PER_IP",
            "COMMENT_RATE_LIMIT_PER_POST",
            "COMMENT_NOTIFY_PENDING",
            "COMMENT_SPAM_WORDS",
            "SEARCH_PROVIDER",
            "SEARCH_CONFIG",
            "ENABLE_SCHEDULER",
            "THEME_EXTERNAL_DIR",
            "THEME_ALLOW_EXTERNAL",
            "THEME_STRICT_VALIDATION",
            "THEME_DEFAULT_DARK",
            "THEME_DEFAULT_LIGHT",
            "THEME_DEFAULT_SCHEME",
        ]
        for name in expected_globals:
            assert hasattr(config_legacy, name), f"config_legacy missing global: {name}"
            value = getattr(config_legacy, name)
            assert value is not None or name in ("CDN_URL",), f"config_legacy.{name} is None"


class TestConfigInitReexports:
    def test_config_init_reexports_legacy(self) -> None:
        from app import config as cfg

        assert hasattr(cfg, "APP_TITLE")
        assert hasattr(cfg, "SECRET_KEY")
        assert hasattr(cfg, "ADMIN_PASSWORD")
        assert hasattr(cfg, "BASE_URL")
        assert hasattr(cfg, "POSTS_PER_PAGE")

    def test_config_init_values_match_legacy(self) -> None:
        from app import config as cfg
        from app import config_legacy

        assert cfg.APP_TITLE == config_legacy.APP_TITLE
        assert cfg.SECRET_KEY == config_legacy.SECRET_KEY
        assert cfg.POSTS_PER_PAGE == config_legacy.POSTS_PER_PAGE


class TestNoNewLegacyImports:
    def test_no_new_config_legacy_imports(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        allowlist = {
            (project_root / "app" / "config" / "__init__.py").resolve(),
            (project_root / "app" / "__init__.py").resolve(),
        }
        skip_dirs = {
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            ".venv",
            ".worktrees",
            "build",
            "dist",
            "node_modules",
            "venv",
        }
        violations = []
        for py_file in project_root.rglob("*.py"):
            if skip_dirs & set(py_file.relative_to(project_root).parts):
                continue
            resolved = py_file.resolve()
            if resolved in allowlist:
                continue
            source = py_file.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "config_legacy" in alias.name:
                            violations.append(f"{py_file}:{node.lineno} imports {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and "config_legacy" in node.module:
                        violations.append(f"{py_file}:{node.lineno} imports from {node.module}")
        assert violations == [], f"Unauthorized config_legacy imports: {violations}"
