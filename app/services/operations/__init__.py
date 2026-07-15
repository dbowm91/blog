"""Operational service layer for CLI and Flask command compatibility.

Extracted business logic from CLI handlers into reusable, testable services.
No service function depends on Click, terminal output, or process exit.
"""

__all__: list[str] = []

try:
    from app.services.operations.admin import (
        create_admin,
        promote_admin,
        reset_admin_password,
        list_admins,
    )

    __all__ += ["create_admin", "promote_admin", "reset_admin_password", "list_admins"]
except ImportError:
    pass

try:
    from app.services.operations.database import (
        check_database_integrity,
        rebuild_search_index,
    )

    __all__ += ["check_database_integrity", "rebuild_search_index"]
except ImportError:
    pass

try:
    from app.services.operations.media import (
        scan_orphaned_media,
        apply_orphaned_media_cleanup,
    )

    __all__ += ["scan_orphaned_media", "apply_orphaned_media_cleanup"]
except ImportError:
    pass

try:
    from app.services.operations.transfer import (
        export_site_data,
        validate_import,
        import_site_data,
    )

    __all__ += ["export_site_data", "validate_import", "import_site_data"]
except ImportError:
    pass

try:
    from app.services.operations.themes import (
        list_theme_descriptors,
        validate_theme,
        inspect_theme,
        refresh_theme_registry,
        get_theme_paths,
        run_accessibility_check,
    )

    __all__ += [
        "list_theme_descriptors",
        "validate_theme",
        "inspect_theme",
        "refresh_theme_registry",
        "get_theme_paths",
        "run_accessibility_check",
    ]
except ImportError:
    pass

try:
    from app.services.operations.backup import (
        create_backup_operation,
        verify_backup,
    )

    __all__ += ["create_backup_operation", "verify_backup"]
except ImportError:
    pass
