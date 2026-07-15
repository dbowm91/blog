"""CLI commands for the Flask application.

All business logic is delegated to app.services.operations.*.
This module handles only Flask-specific concerns: prompts, output, Click integration.
"""

import json
import uuid
from typing import Any

import click
from sqlalchemy import select

from app.extensions import db
from app.models import User, Post, Tag, Subscriber, Page
from app.utils import utc_now
from app.transaction import commit_with_rollback


def register_cli_commands(app: Any) -> None:
    """Register CLI commands with the Flask app."""

    @app.cli.command("rebuild-search")
    def rebuild_search_command() -> None:
        """Rebuild the FTS5 search index."""
        from app.services.operations.database import rebuild_search_index

        result = rebuild_search_index()
        click.echo(result.summary)

    @app.cli.command("cleanup-orphaned-images")
    def cleanup_orphaned_images_command() -> None:
        """Clean up image files not associated with any post."""
        from app.services.operations.media import apply_orphaned_media_cleanup

        result = apply_orphaned_media_cleanup()
        click.echo(f"Cleaned up {result.orphaned_deleted} orphaned image file(s).")
        if result.missing_cleared > 0:
            click.echo(f"Cleared {result.missing_cleared} missing image reference(s) from posts.")

    @app.cli.command("create-admin")
    def create_admin_command() -> None:
        """Create a new admin user or promote an existing user."""
        from app.services.operations.admin import create_admin, ConflictError

        username = click.prompt("Username")
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)

        try:
            result = create_admin(username, password, update_existing=True)
            click.echo(result.summary)
        except ValueError as e:
            click.echo(str(e))
        except ConflictError as e:
            click.echo(str(e))

    @app.cli.command("promote-admin")
    @click.argument("username")
    def promote_admin_command(username: str) -> None:
        """Promote an existing user to admin (non-interactive)."""
        from app.services.operations.admin import promote_admin, ConflictError

        try:
            result = promote_admin(username)
            click.echo(result.summary)
        except ValueError as e:
            click.echo(str(e))
        except ConflictError as e:
            click.echo(str(e))

    @app.cli.command("check-integrity")
    def check_integrity_command() -> None:
        """Run database integrity check."""
        from app.services.operations.database import check_database_integrity

        result = check_database_integrity()
        if result.ok:
            click.echo(result.summary)
        else:
            click.echo(
                f"Database integrity check failed: {result.details.get('result', 'unknown')}"
            )
            if result.remediation:
                for r in result.remediation:
                    click.echo(r)

    @app.cli.command("export-data")
    @click.argument("output_file")
    def export_data_command(output_file: str) -> None:
        """Export all posts and subscribers as JSON."""
        from app.services.operations.transfer import export_site_data

        try:
            result = export_site_data(output_file, force=True)
            click.echo(result.summary)
        except FileExistsError as e:
            click.echo(str(e))

    @app.cli.command("import-data")
    @click.argument("input_file")
    @click.option(
        "--skip-confirmed/--include-confirmed",
        default=True,
        help="Skip already-confirmed subscribers (default: skip)",
    )
    def import_data_command(input_file: str, skip_confirmed: bool) -> None:
        """Import posts, subscribers, tags, and pages from JSON."""
        from app.services.operations.transfer import import_site_data

        result = import_site_data(input_file, skip_confirmed=skip_confirmed)
        click.echo(result.summary)

    @app.cli.command("seed")
    @click.option("--posts", default=10, help="Number of sample posts to create")
    @click.option("--subscribers", default=20, help="Number of sample subscribers")
    @click.option("--published/--draft", default=False, help="Set posts as published")
    def seed_command(posts: int, subscribers: int, published: bool) -> None:
        """Generate sample data for testing."""
        existing_tags = db.session.execute(select(Tag)).scalars().all()
        if existing_tags:
            click.echo("Database already contains data. Use --clear to reset.")
            return

        sample_tags = []
        tag_names = ["python", "flask", "testing", "web-dev", "database", "api"]
        for name in tag_names:
            tag = Tag(name=name, slug=Tag.generate_slug(name))
            db.session.add(tag)
            sample_tags.append(tag)
        commit_with_rollback()
        click.echo(f"Created {len(sample_tags)} tags.")

        sample_users = []
        for i in range(3):
            user = User(username=f"author{i + 1}", is_admin=False)
            user.set_password("Password123!")
            db.session.add(user)
            sample_users.append(user)
        commit_with_rollback()
        click.echo(f"Created {len(sample_users)} users.")

        for i in range(posts):
            post = Post(
                title=f"Sample Post {i + 1}: Testing the Blog",
                slug=f"sample-post-{i + 1}",
                body=f"# Sample Post {i + 1}\n\nThis is sample content for post {i + 1}. "
                f"It contains multiple paragraphs to simulate real content.\n\n"
                f"## Section {i + 1}.1\n\n"
                f"Here is some more content with a code example:\n\n"
                f"```python\nprint('Hello, World!')\n```\n\n"
                f"## Section {i + 1}.2\n\n"
                f"More content here with a list:\n\n"
                f"- Item 1\n- Item 2\n- Item 3\n",
                summary=f"This is a summary for sample post {i + 1}",
                published=published,
                published_at=utc_now() if published else None,
            )
            for tag in sample_tags[: (i % len(sample_tags)) + 1]:
                post.tags.append(tag)
            db.session.add(post)
        commit_with_rollback()

        from app.search import sync_fts

        all_posts = db.session.execute(select(Post)).scalars().all()
        for post in all_posts:
            sync_fts(post.id, post.title, post.body, post.summary, post.published)
        click.echo(f"Created {posts} posts.")

        for i in range(subscribers):
            subscriber = Subscriber(
                email=f"subscriber{i + 1}@example.com",
                token=uuid.uuid4().hex,
                confirmed=True,
            )
            db.session.add(subscriber)
        commit_with_rollback()
        click.echo(f"Created {subscribers} subscribers.")

        sample_pages = [
            {"title": "About", "slug": "about", "body": "# About\n\nThis is the about page."},
            {"title": "Contact", "slug": "contact", "body": "# Contact\n\nGet in touch with us."},
        ]
        for page_data in sample_pages:
            page = Page(**page_data, published=True)
            db.session.add(page)
        commit_with_rollback()
        click.echo(f"Created {len(sample_pages)} pages.")

        click.echo("Seed complete!")

    @app.cli.group("themes")
    def themes_group() -> None:
        """Theme management commands."""

    @themes_group.command("list")
    @click.option("--source", type=click.Choice(["all", "bundled", "external"]), default="all")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    @click.option("--warnings", "show_warnings", is_flag=True, help="Include diagnostic summaries.")
    @click.option("--verbose", is_flag=True, help="Show absolute paths (operator only).")
    def themes_list(source: str, as_json: bool, show_warnings: bool, verbose: bool) -> None:
        """List all available themes."""
        from app.services.operations.themes import list_theme_descriptors

        result = list_theme_descriptors(source=source)

        if as_json:
            rows = result.themes
            if not show_warnings:
                for row in rows:
                    row.pop("warnings", None)
            click.echo(json.dumps(rows, indent=2))
            return

        if not result.themes:
            click.echo("No themes found.")
            return

        header = f"{'Name':<30} {'Source':<10} {'Type':<10} {'Status':<10} {'Warns':<7}"
        if verbose:
            header += f" {'Path':<50}"
        click.echo(header)
        click.echo("-" * len(header))
        for theme in result.themes:
            is_dark = theme.get("is_dark")
            theme_type = "dark" if is_dark else ("light" if is_dark is False else "unknown")
            overrides = " (overrides)" if theme.get("overrides_bundled") else ""
            warns = str(len(theme.get("warnings", []))) if theme.get("warnings") else "-"
            row = (
                f"{theme['display_name']:<30} {theme['source']:<10} {theme_type:<10} "
                f"{theme['status']}{overrides} {warns:<7}"
            )
            if verbose:
                path = theme.get("path", "-") or "-"
                row += f" {path}"
            click.echo(row)
            if show_warnings and theme.get("warnings"):
                for w in theme["warnings"]:
                    click.echo(f"  WARNING: {w}")

        click.echo(f"\nTotal: {result.total} themes")

    @themes_group.command("validate")
    @click.argument("path")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    def themes_validate(path: str, as_json: bool) -> None:
        """Validate a Halloy TOML theme file or a registered theme name."""
        from app.services.operations.themes import validate_theme

        result = validate_theme(path)

        if as_json:
            data: dict[str, Any] = {
                "valid": result.valid,
                "name": result.theme_name,
            }
            if result.details:
                data.update(result.details)
            if result.warnings:
                data["warnings"] = list(result.warnings)
            if not result.ok:
                data["error"] = result.summary
            click.echo(json.dumps(data, indent=2))
            if not result.ok:
                raise SystemExit(1)
            return

        if result.ok:
            click.echo(f"Theme file is valid: {path}")
            if result.details:
                if "normalized_name" in result.details:
                    click.echo(f"  Normalized name: {result.details['normalized_name']}")
                if "schema_version" in result.details:
                    click.echo(f"  Schema version: {result.details['schema_version']}")
                if "is_dark" in result.details:
                    click.echo(f"  Is dark: {result.details['is_dark']}")
                if "token_count" in result.details:
                    field_names = list(range(result.details["token_count"]))
                    click.echo(f"  Translated tokens: {len(field_names)} total")
            if result.warnings:
                click.echo("  Warnings:")
                for w in result.warnings:
                    click.echo(f"    - {w}")
        else:
            click.echo(result.summary, err=True)
            raise SystemExit(1)

    @themes_group.command("inspect")
    @click.argument("name")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    @click.option("--css", "as_css", is_flag=True, help="Output generated CSS variables.")
    def themes_inspect(name: str, as_json: bool, as_css: bool) -> None:
        """Inspect a theme's full details."""
        from app.services.operations.themes import inspect_theme

        result = inspect_theme(name)

        if not result.ok:
            click.echo(result.summary, err=True)
            raise SystemExit(1)

        if as_css:
            from app.themes.service import get_theme_service

            service = get_theme_service()
            registry = service.get_registry()
            loaded = registry.load(name)
            click.echo(loaded.css)
            return

        if as_json:
            data = {
                "canonical_name": result.details.get("canonical_name"),
                "display_name": result.details.get("display_name"),
                "source": result.details.get("source"),
                "is_dark": result.details.get("is_dark"),
                "status": result.details.get("status"),
                "overrides_bundled": result.details.get("overrides_bundled"),
                "css_vars": result.css_vars,
            }
            if result.details.get("accessibility"):
                data["accessibility"] = result.details["accessibility"]
            if result.details.get("classification"):
                data["classification"] = result.details["classification"]
            if result.warnings:
                data["contrast_warnings"] = result.warnings
            click.echo(json.dumps(data, indent=2))
            return

        click.echo(f"Theme: {result.details.get('display_name')}")
        click.echo(f"Canonical name: {result.details.get('canonical_name')}")
        click.echo(f"Source: {result.details.get('source')}")
        click.echo(f"Is dark: {result.details.get('is_dark')}")
        click.echo(f"Status: {result.details.get('status')}")
        click.echo(f"Overrides bundled: {result.details.get('overrides_bundled')}")
        if result.warnings:
            for w in result.warnings:
                click.echo(f"  - {w}")

        if result.details.get("accessibility", {}).get("findings"):
            click.echo("Accessibility findings:")
            for f in result.details["accessibility"]["findings"]:
                if f.get("severity") == "mandatory":
                    if f.get("is_expected"):
                        severity_tag = "EXCEPT"
                    else:
                        severity_tag = "FAIL"
                else:
                    severity_tag = "WARN"
                click.echo(
                    f"  [{severity_tag}] {f.get('description', '')} "
                    f"({f.get('ratio', 0)}:1, required {f.get('required', 0)}:1, WCAG {f.get('wcag', '')})"
                )
                if f.get("exception_reason"):
                    click.echo(f"          reason: {f['exception_reason']}")
        if result.details.get("classification"):
            c = result.details["classification"]
            click.echo(
                f"Classification: computed_luminance={c.get('page_luminance')} computed_dark={c.get('computed_dark')}"
            )
            if c.get("mismatch"):
                click.echo(
                    f"  WARNING: Filename dark={c.get('filename_dark')} disagrees with computed dark={c.get('computed_dark')}"
                )

        file_path = result.details.get("file_path", "")
        source_detail = result.details.get("source_detail", "")
        if file_path:
            click.echo(f"File path: {file_path}")
        click.echo(f"Source detail: {source_detail}")

        if result.details.get("source") == "bundled":
            provenance = f"bundled ({source_detail})"
        else:
            provenance = f"external ({source_detail})"
        click.echo(f"Translation provenance: {provenance}")

        try:
            from app.models import SiteSettings

            settings = SiteSettings.get_instance()
            dark_name = settings.theme_dark_name
            light_name = settings.theme_light_name
            canonical = result.details.get("canonical_name")
            active_as = []
            if canonical == dark_name:
                active_as.append("dark")
            if canonical == light_name:
                active_as.append("light")
            if active_as:
                click.echo(f"Active as: {'/'.join(active_as)}")
            else:
                click.echo("Active as: neither")
            from app.themes.service import get_theme_service

            fallback_registry = get_theme_service().get_registry()
            fallback_theme = fallback_registry.get_fallback()
            fb_name = fallback_theme.descriptor.canonical_name
            fb_roles = []
            if fb_name == dark_name:
                fb_roles.append("dark")
            if fb_name == light_name:
                fb_roles.append("light")
            if fb_roles:
                click.echo(f"Fallback for: {'/'.join(fb_roles)}")
            else:
                click.echo("Fallback for: neither")
        except Exception:
            pass
        click.echo(f"\nCSS variables ({len(result.css_vars)}):")
        for key, value in sorted(result.css_vars.items()):
            click.echo(f"  {key}: {value}")

    @themes_group.command("refresh")
    def themes_refresh() -> None:
        """Refresh the theme registry."""
        from app.services.operations.themes import refresh_theme_registry

        result = refresh_theme_registry()
        click.echo("Theme registry refreshed.")
        click.echo(f"  Catalog: {result.old_count} -> {result.new_count} themes")
        if result.added:
            click.echo(f"  Added: {', '.join(result.added)}")
        if result.removed:
            click.echo(f"  Removed: {', '.join(result.removed)}")

        try:
            from app.models import SiteSettings
            from app.themes.service import get_theme_service

            settings = SiteSettings.get_instance()
            dark_name = settings.theme_dark_name
            light_name = settings.theme_light_name
            new_registry = get_theme_service().get_registry()
            new_themes = {t.canonical_name for t in new_registry.list_themes()}
            if dark_name and dark_name not in new_themes:
                click.echo(f"  WARNING: Dark theme '{dark_name}' no longer available.")
            if light_name and light_name not in new_themes:
                click.echo(f"  WARNING: Light theme '{light_name}' no longer available.")
            fallback = new_registry.get_fallback()
            click.echo(f"  Fallback: {fallback.descriptor.canonical_name}")
        except Exception:
            pass

    @themes_group.command("paths")
    def themes_paths() -> None:
        """Display theme resource paths and configuration."""
        from app.services.operations.themes import get_theme_paths

        result = get_theme_paths()
        paths = result.paths

        click.echo("Theme paths:")
        bundled = paths.get("bundled", {})
        if bundled.get("package_name"):
            click.echo(
                f"  Bundled package: {bundled['package_name']} "
                f"v{bundled.get('package_version', 'unknown')} "
                f"({bundled.get('theme_count', '?')} themes)"
            )
        else:
            click.echo("  Bundled package: app/themes/bundled/")
        if bundled.get("toml_count") is not None:
            click.echo(f"  Bundled themes: {bundled['toml_count']} files")
        else:
            click.echo("  Bundled themes: directory not found")

        click.echo("")
        click.echo("External theme directory:")
        external = paths.get("external", {})
        if external.get("configured"):
            click.echo(f"  Configured: {external['configured']}")
            click.echo(f"  Exists: {'yes' if external.get('exists') else 'no'}")
            if external.get("exists"):
                click.echo(
                    f"  Readable: {'yes' if external.get('readable') else 'no (permission denied)'}"
                )
                if external.get("toml_count") is not None:
                    click.echo(f"  Theme files: {external['toml_count']}")
        else:
            click.echo("  Configured: (none)")
            click.echo("  External themes are disabled")

        click.echo("")
        click.echo("Configuration:")
        config = paths.get("config", {})
        click.echo(f"  THEME_ALLOW_EXTERNAL: {config.get('THEME_ALLOW_EXTERNAL')}")
        click.echo(f"  THEME_STRICT_VALIDATION: {config.get('THEME_STRICT_VALIDATION')}")
        max_size = config.get("max_file_size", 0)
        size_mb = max_size / (1024 * 1024)
        click.echo(f"  Maximum file size: {max_size} bytes ({size_mb:.1f} MB)")
        click.echo("")
        click.echo("Precedence: external themes override bundled themes with the same name.")

    @themes_group.command("accessibility")
    @click.option("--source", type=click.Choice(["all", "bundled", "external"]), default="all")
    @click.option("--strict", is_flag=True, help="Reject external themes with mandatory failures.")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    def themes_accessibility(source: str, strict: bool, as_json: bool) -> None:
        """Run WCAG contrast checks over all themes with severity classification."""
        from app.services.operations.themes import run_accessibility_check

        result = run_accessibility_check(source=source, strict=strict)

        if as_json:
            click.echo(json.dumps(result.to_dict(), indent=2))
            return

        for report in result.reports:
            findings = report.get("findings", [])
            if findings:
                click.echo(f"\n{report['theme_name']} ({report['source']}):")
                for f in findings:
                    if f.get("severity") == "mandatory":
                        if f.get("is_expected"):
                            severity_tag = "EXCEPT"
                        else:
                            severity_tag = "FAIL"
                    else:
                        severity_tag = "WARN"
                    click.echo(
                        f"  [{severity_tag}] {f.get('description', '')} "
                        f"({f.get('ratio', 0)}:1, required {f.get('required', 0)}:1, WCAG {f.get('wcag', '')})"
                    )
                    click.echo(
                        f"          fg={f.get('foreground', '')} bg={f.get('background', '')}"
                    )
                    if f.get("exception_reason"):
                        click.echo(f"          reason: {f['exception_reason']}")

        click.echo(f"\n{'=' * 60}")
        click.echo(f"Checked {result.total_themes} themes")
        click.echo(f"Passed (exact): {result.passed_exact}")
        click.echo(f"Passed (with exceptions): {result.passed_with_exceptions}")
        click.echo(f"Failed (unexpected): {result.failed}")
        click.echo(f"Mandatory failures: {result.details.get('total_mandatory_failures', 0)}")
        click.echo(f"Advisory warnings: {result.details.get('total_advisory_warnings', 0)}")
        if result.details.get("strict_rejected"):
            click.echo(
                f"\nStrict mode: {len(result.details['strict_rejected'])} external theme(s) rejected due to unexpected mandatory failures."
            )
            for name in result.details["strict_rejected"]:
                click.echo(f"  REJECTED: {name}")
            raise SystemExit(1)

        if result.failed == 0:
            click.echo(
                "\nAll themes pass mandatory accessibility gates (with documented exceptions)."
            )
        else:
            click.echo(
                f"\n{result.failed} theme(s) have unexpected mandatory accessibility failures."
            )


def _validate_theme_file(file_path: Any, as_json: bool) -> None:
    """Validate a Halloy TOML theme file on disk."""
    from app.services.operations.themes import validate_theme

    result = validate_theme(str(file_path))

    if as_json:
        data: dict[str, Any] = {
            "path": str(file_path),
            "valid": result.valid,
        }
        if result.details:
            data.update(result.details)
        if result.warnings:
            data["warnings"] = list(result.warnings)
        if not result.ok:
            data["error"] = result.summary
        click.echo(json.dumps(data, indent=2))
    else:
        if result.ok:
            click.echo(f"Theme file is valid: {file_path}")
        else:
            click.echo(result.summary, err=True)
    if not result.ok:
        raise SystemExit(1)


def _validate_theme_name(name: str, as_json: bool) -> None:
    """Validate a registered theme name via the registry."""
    from app.services.operations.themes import validate_theme

    result = validate_theme(name)

    if as_json:
        data = {
            "valid": result.valid,
            "name": result.theme_name,
        }
        if result.details:
            data.update(result.details)
        if result.warnings:
            data["warnings"] = list(result.warnings)
        if not result.ok:
            data["error"] = result.summary
        click.echo(json.dumps(data, indent=2))
    else:
        if result.ok:
            click.echo(f"Theme '{name}' is valid.")
            if result.details:
                if "canonical_name" in result.details:
                    click.echo(f"  Canonical name: {result.details['canonical_name']}")
                if "source" in result.details:
                    click.echo(f"  Source: {result.details['source']}")
                if "is_dark" in result.details:
                    click.echo(f"  Is dark: {result.details['is_dark']}")
            if result.warnings:
                click.echo("  Warnings:")
                for w in result.warnings:
                    click.echo(f"    - {w}")
        else:
            click.echo(result.summary, err=True)
    if not result.ok:
        raise SystemExit(1)
