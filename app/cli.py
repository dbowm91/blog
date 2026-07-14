"""CLI commands for the Flask application."""

import json
import os
import uuid
from datetime import datetime
from typing import Any

import click
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User, Post, Tag, Subscriber, Page
from app.utils import utc_now
from app.transaction import commit_with_rollback


def register_cli_commands(app: Any) -> None:
    """Register CLI commands with the Flask app."""

    @app.cli.command("rebuild-search")
    def rebuild_search_command() -> None:
        """Rebuild the FTS5 search index."""
        from app.search import rebuild_fts

        rebuild_fts()
        click.echo("Search index rebuilt.")

    @app.cli.command("cleanup-orphaned-images")
    def cleanup_orphaned_images_command() -> None:
        """Clean up image files not associated with any post."""
        from app.routes.admin.media import cleanup_orphaned_images

        orphaned, missing = cleanup_orphaned_images(app)
        click.echo(f"Cleaned up {orphaned} orphaned image file(s).")
        if missing > 0:
            click.echo(f"Cleared {missing} missing image reference(s) from posts.")

    @app.cli.command("create-admin")
    def create_admin_command() -> None:
        """Create a new admin user or promote an existing user."""
        username = click.prompt("Username")
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)

        from app.routes.admin.helpers import _check_password_complexity

        if not _check_password_complexity(password):
            click.echo(
                "Password must be at least 8 characters and contain at least 3 of 4: "
                "lowercase, uppercase, digit, special."
            )
            return

        existing = db.session.execute(
            select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if existing:
            existing.is_admin = True
            existing.set_password(password)
            commit_with_rollback()
            click.echo(f"User '{username}' promoted to admin.")
        else:
            user = User(username=username, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            try:
                commit_with_rollback()
            except IntegrityError:
                db.session.rollback()
                click.echo(f"User '{username}' already exists.")
                return
            click.echo(f"Admin user '{username}' created.")

    @app.cli.command("promote-admin")
    @click.argument("username")
    def promote_admin_command(username: str) -> None:
        """Promote an existing user to admin (non-interactive)."""
        user = db.session.execute(select(User).filter_by(username=username)).scalar_one_or_none()
        if not user:
            click.echo(f"User '{username}' not found.")
            return
        if user.is_admin:
            click.echo(f"User '{username}' is already an admin.")
            return
        user.is_admin = True
        commit_with_rollback()
        click.echo(f"User '{username}' promoted to admin.")

    @app.cli.command("check-integrity")
    def check_integrity_command() -> None:
        """Run database integrity check."""
        result = db.session.execute(text("PRAGMA integrity_check"))
        row = result.scalar()
        if row != "ok":
            click.echo(f"Database integrity check failed: {row}")
            click.echo("Consider restoring from a backup.")
        else:
            click.echo("Database integrity check passed: ok")

    @app.cli.command("export-data")
    @click.argument("output_file")
    def export_data_command(output_file: str) -> None:
        """Export all posts and subscribers as JSON."""
        from app.services.serialization import export_data_to_dict

        posts = db.session.execute(select(Post).order_by(Post.created_at)).scalars().all()

        subscribers = (
            db.session.execute(select(Subscriber).order_by(Subscriber.created_at)).scalars().all()
        )

        tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()

        pages = db.session.execute(select(Page).order_by(Page.created_at)).scalars().all()

        data = export_data_to_dict(posts, subscribers, tags, pages)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        click.echo(
            f"Exported {len(posts)} posts, {len(subscribers)} subscribers, "
            f"{len(tags)} tags, and {len(pages)} pages to '{output_file}'."
        )

    @app.cli.command("import-data")
    @click.argument("input_file")
    @click.option(
        "--skip-confirmed/--include-confirmed",
        default=True,
        help="Skip already-confirmed subscribers (default: skip)",
    )
    def import_data_command(input_file: str, skip_confirmed: bool) -> None:
        """Import posts, subscribers, tags, and pages from JSON."""
        with open(input_file, encoding="utf-8") as f:
            data = json.load(f)

        version = data.get("version", 1)
        if version != 1:
            click.echo(f"Unsupported export version: {version}")
            return

        imported_posts = 0
        imported_tags = 0
        imported_subscribers = 0
        imported_pages = 0

        for tag_data in data.get("tags", []):
            existing = db.session.execute(
                select(Tag).filter_by(slug=tag_data["slug"])
            ).scalar_one_or_none()
            if not existing:
                tag = Tag(name=tag_data["name"], slug=tag_data["slug"])
                db.session.add(tag)
                imported_tags += 1
        if imported_tags > 0:
            commit_with_rollback()

        tag_cache = {t.slug: t for t in db.session.execute(select(Tag)).scalars().all()}

        for post_data in data.get("posts", []):
            existing = db.session.execute(
                select(Post).filter_by(slug=post_data["slug"])
            ).scalar_one_or_none()
            if existing:
                continue

            post = Post(
                title=post_data["title"],
                slug=post_data["slug"],
                body=post_data["body"],
                summary=post_data.get("summary", ""),
                image=post_data.get("image"),
                published=post_data.get("published", False),
            )
            if post_data.get("published_at"):
                post.published_at = datetime.fromisoformat(post_data["published_at"])
            if post_data.get("scheduled_publish_at"):
                post.scheduled_publish_at = datetime.fromisoformat(
                    post_data["scheduled_publish_at"]
                )

            for tag_name in post_data.get("tags", []):
                existing_tag: Tag | None = tag_cache.get(Tag.generate_slug(tag_name))
                if existing_tag:
                    post.tags.append(existing_tag)

            db.session.add(post)
            imported_posts += 1
        if imported_posts > 0:
            commit_with_rollback()
            from app.search import sync_fts

            for post_data in data.get("posts", []):
                existing = db.session.execute(
                    select(Post).filter_by(slug=post_data["slug"])
                ).scalar_one_or_none()
                if existing and post_data.get("tags"):
                    sync_fts(
                        existing.id,
                        existing.title,
                        existing.body,
                        existing.summary,
                        existing.published,
                    )

        for subscriber_data in data.get("subscribers", []):
            if skip_confirmed and subscriber_data.get("confirmed"):
                continue

            existing = db.session.execute(
                select(Subscriber).filter_by(email=subscriber_data["email"])
            ).scalar_one_or_none()
            if existing:
                continue

            subscriber = Subscriber(
                email=subscriber_data["email"],
                token=uuid.uuid4().hex,
                confirmed=subscriber_data.get("confirmed", False),
            )
            if subscriber_data.get("created_at"):
                subscriber.created_at = datetime.fromisoformat(subscriber_data["created_at"])
            if subscriber_data.get("expires_at"):
                subscriber.expires_at = datetime.fromisoformat(subscriber_data["expires_at"])
            if subscriber_data.get("unsubscribed_at"):
                subscriber.unsubscribed_at = datetime.fromisoformat(
                    subscriber_data["unsubscribed_at"]
                )

            db.session.add(subscriber)
            imported_subscribers += 1
        if imported_subscribers > 0:
            commit_with_rollback()

        for page_data in data.get("pages", []):
            existing = db.session.execute(
                select(Page).filter_by(slug=page_data["slug"])
            ).scalar_one_or_none()
            if existing:
                continue

            page = Page(
                title=page_data["title"],
                slug=page_data["slug"],
                body=page_data["body"],
                published=page_data.get("published", False),
            )
            if page_data.get("created_at"):
                page.created_at = datetime.fromisoformat(page_data["created_at"])
            if page_data.get("updated_at"):
                page.updated_at = datetime.fromisoformat(page_data["updated_at"])

            db.session.add(page)
            imported_pages += 1
        if imported_pages > 0:
            commit_with_rollback()

        click.echo(
            f"Imported {imported_posts} posts, {imported_subscribers} subscribers, "
            f"{imported_tags} tags, and {imported_pages} pages."
        )

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
        from app.themes.service import get_theme_service

        service = get_theme_service()
        registry = service.get_registry()
        all_themes = registry.list_themes()

        if source == "bundled":
            all_themes = [t for t in all_themes if t.source.value == "bundled"]
        elif source == "external":
            all_themes = [t for t in all_themes if t.source.value == "external"]

        if as_json:
            import json as json_mod

            from app.config import THEME_EXTERNAL_DIR

            rows = []
            for theme in all_themes:
                if theme.source.value == "bundled":
                    theme_path = f"app/themes/bundled/{theme.canonical_name}.toml"
                elif THEME_EXTERNAL_DIR:
                    theme_path = f"{THEME_EXTERNAL_DIR}/{theme.canonical_name}.toml"
                else:
                    theme_path = ""
                row: dict[str, Any] = {
                    "canonical_name": theme.canonical_name,
                    "display_name": theme.display_name,
                    "source": theme.source.value,
                    "overrides_bundled": theme.overrides_bundled,
                    "is_dark": theme.is_dark,
                    "status": theme.status,
                    "path": theme_path,
                }
                if show_warnings and theme.warnings:
                    row["warnings"] = list(theme.warnings)
                rows.append(row)
            click.echo(json_mod.dumps(rows, indent=2))
            return

        if not all_themes:
            click.echo("No themes found.")
            return

        external_dir = ""
        if verbose:
            from app.config import THEME_EXTERNAL_DIR

            external_dir = THEME_EXTERNAL_DIR or ""

        header = f"{'Name':<30} {'Source':<10} {'Type':<10} {'Status':<10} {'Warns':<7}"
        if verbose:
            header += f" {'Path':<50}"
        click.echo(header)
        click.echo("-" * len(header))
        for theme in all_themes:
            theme_type = (
                "dark" if theme.is_dark else ("light" if theme.is_dark is False else "unknown")
            )
            overrides = " (overrides)" if theme.overrides_bundled else ""
            warns = str(len(theme.warnings)) if theme.warnings else "-"
            row = (
                f"{theme.display_name:<30} {theme.source.value:<10} {theme_type:<10} "
                f"{theme.status}{overrides} {warns:<7}"
            )
            if verbose:
                if theme.source.value == "bundled":
                    path = f"app/themes/bundled/{theme.canonical_name}.toml"
                else:
                    path = f"{external_dir}/{theme.canonical_name}.toml" if external_dir else "-"
                row += f" {path}"
            click.echo(row)
            if show_warnings and theme.warnings:
                for w in theme.warnings:
                    click.echo(f"  WARNING: {w}")

        click.echo(f"\nTotal: {len(all_themes)} themes")

    @themes_group.command("validate")
    @click.argument("path")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    def themes_validate(path: str, as_json: bool) -> None:
        """Validate a Halloy TOML theme file or a registered theme name.

        When PATH is a file on disk, validates the file directly (for pre-installation checks).
        When PATH is a registered theme name, loads and validates via the registry.
        """
        from pathlib import Path as P

        file_path = P(path)
        is_file = file_path.is_file()

        if is_file:
            _validate_theme_file(file_path, as_json)
        else:
            _validate_theme_name(path, as_json)

    @themes_group.command("inspect")
    @click.argument("name")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    @click.option("--css", "as_css", is_flag=True, help="Output generated CSS variables.")
    def themes_inspect(name: str, as_json: bool, as_css: bool) -> None:
        """Inspect a theme's full details."""
        from app.themes.service import get_theme_service
        from app.themes.registry import ThemeNotFoundError

        service = get_theme_service()
        registry = service.get_registry()

        try:
            loaded = registry.load(name)
        except ThemeNotFoundError:
            click.echo(f"Theme '{name}' not found.", err=True)
            raise SystemExit(1)

        if as_css:
            click.echo(loaded.css)
            return

        if as_json:
            import json as json_mod

            data: dict[str, Any] = {
                "canonical_name": loaded.descriptor.canonical_name,
                "display_name": loaded.descriptor.display_name,
                "source": loaded.descriptor.source.value,
                "is_dark": loaded.is_dark,
                "status": loaded.descriptor.status,
                "overrides_bundled": loaded.descriptor.overrides_bundled,
                "css_vars": loaded.css_vars,
            }
            if loaded.descriptor.warnings:
                data["descriptor_warnings"] = list(loaded.descriptor.warnings)
            if loaded.diagnostics.warnings:
                data["contrast_warnings"] = [
                    {
                        "token": w.token,
                        "description": w.description,
                        "foreground": w.foreground,
                        "background": w.background,
                        "ratio": w.ratio,
                        "wcag": w.wcag,
                    }
                    for w in loaded.diagnostics.warnings
                ]
            from app.themes.diagnostics import validate_theme_accessibility

            filename_dark = None
            if loaded.descriptor.is_dark is not None:
                filename_dark = loaded.descriptor.is_dark
            acc_report = validate_theme_accessibility(
                loaded.blog_theme,
                theme_name=loaded.descriptor.canonical_name,
                filename_dark=filename_dark,
            )
            data["accessibility"] = {
                "passed": acc_report.passed,
                "mandatory_failures": len(acc_report.mandatory_failures),
                "advisory_warnings": len(acc_report.advisory_warnings),
                "findings": [f.to_dict() for f in acc_report.findings],
            }
            if acc_report.classification:
                data["classification"] = {
                    "filename_dark": acc_report.classification.filename_dark,
                    "computed_dark": acc_report.classification.computed_dark,
                    "page_luminance": acc_report.classification.page_luminance,
                    "mismatch": acc_report.classification.mismatch,
                }
            click.echo(json_mod.dumps(data, indent=2))
            return

        click.echo(f"Theme: {loaded.descriptor.display_name}")
        click.echo(f"Canonical name: {loaded.descriptor.canonical_name}")
        click.echo(f"Source: {loaded.descriptor.source.value}")
        click.echo(f"Is dark: {loaded.is_dark}")
        click.echo(f"Status: {loaded.descriptor.status}")
        click.echo(f"Overrides bundled: {loaded.descriptor.overrides_bundled}")
        if loaded.descriptor.warnings:
            click.echo(f"Descriptor warnings: {loaded.descriptor.warnings}")
        if loaded.diagnostics.warnings:
            click.echo("Translation warnings:")
            for w in loaded.diagnostics.warnings:
                click.echo(f"  - {w}")

        from app.themes.diagnostics import validate_theme_accessibility

        filename_dark = None
        if loaded.descriptor.is_dark is not None:
            filename_dark = loaded.descriptor.is_dark
        acc_report = validate_theme_accessibility(
            loaded.blog_theme,
            theme_name=loaded.descriptor.canonical_name,
            filename_dark=filename_dark,
        )
        if acc_report.findings:
            click.echo("Accessibility findings:")
            for f in acc_report.findings:
                if f.severity.value == "mandatory":
                    if f.is_expected:
                        severity_tag = "EXCEPT"
                    else:
                        severity_tag = "FAIL"
                else:
                    severity_tag = "WARN"
                click.echo(
                    f"  [{severity_tag}] {f.description} ({f.ratio}:1, required {f.required}:1, WCAG {f.wcag})"
                )
                if f.exception_reason:
                    click.echo(f"          reason: {f.exception_reason}")
        if acc_report.classification:
            c = acc_report.classification
            click.echo(
                f"Classification: computed_luminance={c.page_luminance} computed_dark={c.computed_dark}"
            )
            if c.mismatch:
                click.echo(
                    f"  WARNING: Filename dark={c.filename_dark} disagrees with computed dark={c.computed_dark}"
                )

        from app.config import THEME_EXTERNAL_DIR

        if loaded.descriptor.source.value == "bundled":
            file_path = f"app/themes/bundled/{loaded.descriptor.canonical_name}.toml"
            source_detail = "app/themes/bundled/"
        elif THEME_EXTERNAL_DIR:
            file_path = f"{THEME_EXTERNAL_DIR}/{loaded.descriptor.canonical_name}.toml"
            source_detail = f"{THEME_EXTERNAL_DIR}/"
        else:
            file_path = ""
            source_detail = ""
        if file_path:
            click.echo(f"File path: {file_path}")
        click.echo(f"Source detail: {source_detail}")

        if loaded.descriptor.source.value == "bundled":
            provenance = f"bundled ({source_detail})"
        else:
            provenance = f"external ({source_detail})"
        click.echo(f"Translation provenance: {provenance}")

        try:
            from app.models import SiteSettings

            settings = SiteSettings.get_instance()
            dark_name = settings.theme_dark_name
            light_name = settings.theme_light_name
            canonical = loaded.descriptor.canonical_name
            active_as = []
            if canonical == dark_name:
                active_as.append("dark")
            if canonical == light_name:
                active_as.append("light")
            if active_as:
                click.echo(f"Active as: {'/'.join(active_as)}")
            else:
                click.echo("Active as: neither")
            fallback_registry = service.get_registry()
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
        click.echo(f"\nCSS variables ({len(loaded.css_vars)}):")
        for key, value in sorted(loaded.css_vars.items()):
            click.echo(f"  {key}: {value}")

    @themes_group.command("refresh")
    def themes_refresh() -> None:
        """Refresh the theme registry.

        Invalidates the cache, rebuilds the catalog, and reports changes.
        """
        from app.themes.service import get_theme_service

        service = get_theme_service()
        registry = service.get_registry()

        old_themes = {t.canonical_name for t in registry.list_themes()}
        old_count = len(old_themes)

        service.refresh_registry()

        new_registry = service.get_registry()
        new_themes = {t.canonical_name for t in new_registry.list_themes()}
        new_count = len(new_themes)

        added = sorted(new_themes - old_themes)
        removed = sorted(old_themes - new_themes)

        click.echo("Theme registry refreshed.")
        click.echo(f"  Catalog: {old_count} -> {new_count} themes")

        if added:
            click.echo(f"  Added: {', '.join(added)}")
        if removed:
            click.echo(f"  Removed: {', '.join(removed)}")

        external = [t for t in new_registry.list_themes() if t.source.value == "external"]
        if external:
            click.echo(f"  External overrides: {len(external)}")

        try:
            from app.models import SiteSettings

            settings = SiteSettings.get_instance()
            dark_name = settings.theme_dark_name
            light_name = settings.theme_light_name
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
        from pathlib import Path as P
        from app.config import THEME_EXTERNAL_DIR, THEME_ALLOW_EXTERNAL, THEME_STRICT_VALIDATION

        bundled_dir = P(__file__).resolve().parent / "themes" / "bundled"
        bundled_exists = bundled_dir.is_dir()

        click.echo("Theme paths:")
        manifest_path = bundled_dir / "catalog_manifest.json"
        if manifest_path.is_file():
            try:
                import json as json_mod

                manifest = json_mod.loads(manifest_path.read_text(encoding="utf-8"))
                pkg_name = manifest.get("name", "devlog-themes")
                pkg_version = manifest.get("version", "unknown")
                pkg_count = manifest.get("theme_count", "?")
                click.echo(f"  Bundled package: {pkg_name} v{pkg_version} ({pkg_count} themes)")
            except (OSError, ValueError):
                click.echo("  Bundled package: app/themes/bundled/ (manifest unreadable)")
        else:
            click.echo("  Bundled package: app/themes/bundled/")
        if bundled_exists:
            toml_count = len(list(bundled_dir.glob("*.toml")))
            click.echo(f"  Bundled themes: {toml_count} files")
        else:
            click.echo("  Bundled themes: directory not found")

        click.echo("")
        click.echo("External theme directory:")
        if THEME_EXTERNAL_DIR:
            ext_path = P(THEME_EXTERNAL_DIR)
            click.echo(f"  Configured: {THEME_EXTERNAL_DIR}")
            if ext_path.is_dir():
                click.echo("  Exists: yes")
                if os.access(ext_path, os.R_OK | os.X_OK):
                    click.echo("  Readable: yes")
                    toml_count = len(list(ext_path.glob("*.toml")))
                    click.echo(f"  Theme files: {toml_count}")
                else:
                    click.echo("  Readable: no (permission denied)")
            else:
                click.echo("  Exists: no")
        else:
            click.echo("  Configured: (none)")
            click.echo("  External themes are disabled")

        click.echo("")
        click.echo("Configuration:")
        click.echo(f"  THEME_ALLOW_EXTERNAL: {THEME_ALLOW_EXTERNAL}")
        click.echo(f"  THEME_STRICT_VALIDATION: {THEME_STRICT_VALIDATION}")
        from app.themes.resources import _MAX_EXTERNAL_FILE_SIZE

        size_mb = _MAX_EXTERNAL_FILE_SIZE / (1024 * 1024)
        click.echo(f"  Maximum file size: {_MAX_EXTERNAL_FILE_SIZE} bytes ({size_mb:.1f} MB)")
        click.echo("")
        click.echo("Precedence: external themes override bundled themes with the same name.")

    @themes_group.command("accessibility")
    @click.option("--source", type=click.Choice(["all", "bundled", "external"]), default="all")
    @click.option("--strict", is_flag=True, help="Reject external themes with mandatory failures.")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    def themes_accessibility(source: str, strict: bool, as_json: bool) -> None:
        """Run WCAG contrast checks over all themes with severity classification."""
        import json as json_mod
        from app.themes.service import get_theme_service
        from app.themes.diagnostics import (
            validate_theme_accessibility,
            validate_catalog_accessibility,
        )

        service = get_theme_service()
        registry = service.get_registry()
        all_themes = registry.list_themes()

        if source == "bundled":
            all_themes = [t for t in all_themes if t.source.value == "bundled"]
        elif source == "external":
            all_themes = [t for t in all_themes if t.source.value == "external"]

        reports = []
        for descriptor in all_themes:
            try:
                loaded = registry.load(descriptor.canonical_name)
                filename_dark = None
                if descriptor.is_dark is not None:
                    filename_dark = descriptor.is_dark
                report = validate_theme_accessibility(
                    loaded.blog_theme,
                    theme_name=descriptor.canonical_name,
                    filename_dark=filename_dark,
                )
                report = report.__class__(
                    theme_name=report.theme_name,
                    source=descriptor.source.value,
                    is_dark=report.is_dark,
                    findings=report.findings,
                    classification=report.classification,
                )
                reports.append(report)
            except Exception as e:
                click.echo(f"\n{descriptor.display_name}: ERROR - {e}", err=True)

        catalog_report = validate_catalog_accessibility(reports)

        if as_json:
            click.echo(json_mod.dumps(catalog_report.to_dict(), indent=2))
            return

        for report in reports:
            if report.findings:
                click.echo(f"\n{report.theme_name} ({report.source}):")
                for f in report.findings:
                    if f.severity.value == "mandatory":
                        if f.is_expected:
                            severity_tag = "EXCEPT"
                        else:
                            severity_tag = "FAIL"
                    else:
                        severity_tag = "WARN"
                    click.echo(
                        f"  [{severity_tag}] {f.description} ({f.ratio}:1, required {f.required}:1, WCAG {f.wcag})"
                    )
                    click.echo(f"          fg={f.foreground} bg={f.background}")
                    if f.exception_reason:
                        click.echo(f"          reason: {f.exception_reason}")
            if report.classification and report.classification.mismatch:
                click.echo(
                    f"  [CLASS] Classification mismatch: filename_dark={report.classification.filename_dark} computed_dark={report.classification.computed_dark}"
                )

        click.echo(f"\n{'=' * 60}")
        click.echo(f"Checked {catalog_report.total_themes} themes")
        passed_exact = sum(1 for r in reports if r.passed)
        passed_except = sum(1 for r in reports if r.passed_with_exceptions and not r.passed)
        failed = sum(1 for r in reports if not r.passed_with_exceptions)
        click.echo(f"Passed (exact): {passed_exact}")
        click.echo(f"Passed (with exceptions): {passed_except}")
        click.echo(f"Failed (unexpected): {failed}")
        click.echo(f"Mandatory failures: {catalog_report.total_mandatory}")
        click.echo(f"Advisory warnings: {catalog_report.total_advisory}")
        if catalog_report.classification_mismatches:
            click.echo(
                f"Classification mismatches: {len(catalog_report.classification_mismatches)}"
            )

        if strict:
            external_failed = [
                r for r in reports if r.source == "external" and not r.passed_with_exceptions
            ]
            if external_failed:
                click.echo(
                    f"\nStrict mode: {len(external_failed)} external theme(s) rejected due to unexpected mandatory failures."
                )
                for r in external_failed:
                    click.echo(
                        f"  REJECTED: {r.theme_name} ({len(r.unexpected_mandatory_failures)} unexpected failures)"
                    )
                raise SystemExit(1)

        if failed == 0:
            click.echo(
                "\nAll themes pass mandatory accessibility gates (with documented exceptions)."
            )
        else:
            click.echo(f"\n{failed} theme(s) have unexpected mandatory accessibility failures.")


def _validate_theme_file(file_path: Any, as_json: bool) -> None:
    """Validate a Halloy TOML theme file on disk."""
    from app.themes.halloy import parse_halloy_theme, ThemeParseError, ThemeSchemaError
    from app.themes.translate import translate_halloy_theme
    from app.themes.resources import _MAX_EXTERNAL_FILE_SIZE
    from app.themes.diagnostics import check_blog_theme_contrast
    from app.themes.registry import _THEME_ALIASES

    errors: list[str] = []
    warnings_list: list[str] = []
    result_data: dict[str, Any] = {"path": str(file_path), "valid": False}

    if not file_path.exists():
        msg = f"File not found: {file_path}"
        if as_json:
            result_data["error"] = msg
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(msg, err=True)
        raise SystemExit(1)

    if not file_path.is_file():
        msg = f"Not a regular file: {file_path}"
        if as_json:
            result_data["error"] = msg
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(msg, err=True)
        raise SystemExit(1)

    try:
        size = file_path.stat().st_size
    except OSError as e:
        msg = f"Cannot stat file: {e}"
        if as_json:
            result_data["error"] = msg
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(msg, err=True)
        raise SystemExit(1)

    if size > _MAX_EXTERNAL_FILE_SIZE:
        msg = f"File too large: {size} bytes (max {_MAX_EXTERNAL_FILE_SIZE})"
        if as_json:
            result_data["error"] = msg
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(msg, err=True)
        raise SystemExit(1)

    if size == 0:
        msg = "File is empty"
        if as_json:
            result_data["error"] = msg
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(msg, err=True)
        raise SystemExit(1)

    try:
        data = file_path.read_bytes()
    except OSError as e:
        msg = f"Cannot read file: {e}"
        if as_json:
            result_data["error"] = msg
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(msg, err=True)
        raise SystemExit(1)

    try:
        halloy_theme = parse_halloy_theme(data)
    except ThemeParseError as e:
        errors.append(str(e))
        if as_json:
            result_data["errors"] = errors
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(f"Parse error: {e}", err=True)
        raise SystemExit(1)
    except ThemeSchemaError as e:
        errors.append(str(e))
        if as_json:
            result_data["errors"] = errors
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(f"Schema error: {e}", err=True)
        raise SystemExit(1)

    result_data["normalized_name"] = file_path.stem
    result_data["schema_version"] = halloy_theme.schema_version
    result_data["extra_sections"] = (
        list(halloy_theme.extra_top_sections.keys())
        if hasattr(halloy_theme, "extra_top_sections")
        else []
    )

    try:
        translation = translate_halloy_theme(halloy_theme)
    except Exception as e:
        errors.append(f"Translation failed: {e}")
        if as_json:
            result_data["errors"] = errors
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(f"Translation error: {e}", err=True)
        raise SystemExit(1)

    result_data["valid"] = True
    result_data["is_dark"] = translation.is_dark
    result_data["warnings"] = warnings_list

    canonical_lower = file_path.stem.lower()
    alias_match = None
    for alias, canonical in _THEME_ALIASES.items():
        if canonical.lower() == canonical_lower or alias == canonical_lower:
            alias_match = canonical
            break
    if alias_match:
        warnings_list.append(f"Filename overrides bundled theme: {alias_match}")

    contrast_warnings = check_blog_theme_contrast(translation.theme)
    if contrast_warnings:
        result_data["contrast_warnings"] = [
            {
                "token": w.token,
                "description": w.description,
                "foreground": w.foreground,
                "background": w.background,
                "ratio": w.ratio,
                "wcag": w.wcag,
            }
            for w in contrast_warnings
        ]
        warnings_list.extend(f"{w.description} ({w.ratio}:1)" for w in contrast_warnings)

    if as_json:
        click.echo(json.dumps(result_data, indent=2))
    else:
        click.echo(f"Theme file is valid: {file_path}")
        click.echo(f"  Normalized name: {file_path.stem}")
        click.echo(f"  Schema version: {halloy_theme.schema_version}")
        click.echo(f"  Is dark: {translation.is_dark}")
        if result_data.get("extra_sections"):
            click.echo(f"  Extra sections: {', '.join(result_data['extra_sections'])}")
        if warnings_list:
            click.echo("  Warnings:")
            for w in warnings_list:
                click.echo(f"    - {w}")
        field_names = list(translation.theme.__dataclass_fields__)
        token_list = ", ".join(f"--blog-{f.replace('_', '-')}" for f in field_names)
        click.echo(f"  Translated tokens: {token_list} ({len(field_names)} total)")


def _validate_theme_name(name: str, as_json: bool) -> None:
    """Validate a registered theme name via the registry."""
    from app.themes.service import get_theme_service
    from app.themes.registry import ThemeNotFoundError, ThemeParseFailure, ThemeLoadError

    service = get_theme_service()
    registry = service.get_registry()

    try:
        loaded = registry.load(name)
    except ThemeNotFoundError:
        if as_json:
            click.echo(json.dumps({"valid": False, "name": name, "error": "not found"}, indent=2))
        else:
            click.echo(f"Theme '{name}' not found.", err=True)
        raise SystemExit(1)
    except ThemeParseFailure as e:
        if as_json:
            click.echo(json.dumps({"valid": False, "name": name, "error": str(e)}, indent=2))
        else:
            click.echo(f"Theme '{name}' failed to parse: {e}", err=True)
        raise SystemExit(1)
    except ThemeLoadError as e:
        if as_json:
            click.echo(json.dumps({"valid": False, "name": name, "error": str(e)}, indent=2))
        else:
            click.echo(f"Theme '{name}' failed to load: {e}", err=True)
        raise SystemExit(1)

    if as_json:
        data: dict[str, Any] = {
            "valid": True,
            "name": name,
            "canonical_name": loaded.descriptor.canonical_name,
            "source": loaded.descriptor.source.value,
            "is_dark": loaded.is_dark,
        }
        if loaded.descriptor.warnings:
            data["warnings"] = list(loaded.descriptor.warnings)
        if loaded.diagnostics.warnings:
            data["contrast_warnings"] = [
                {"token": w.token, "description": w.description, "ratio": w.ratio}
                for w in loaded.diagnostics.warnings
            ]
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Theme '{name}' is valid.")
        click.echo(f"  Canonical name: {loaded.descriptor.canonical_name}")
        click.echo(f"  Source: {loaded.descriptor.source.value}")
        click.echo(f"  Is dark: {loaded.is_dark}")
        if loaded.descriptor.warnings:
            click.echo("  Warnings:")
            for w in loaded.descriptor.warnings:
                click.echo(f"    - {w}")
        if loaded.diagnostics.warnings:
            click.echo("  Translation warnings:")
            for w in loaded.diagnostics.warnings:
                click.echo(f"    - {w}")
