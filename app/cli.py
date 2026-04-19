"""CLI commands for the Flask application."""

import click
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User


def register_cli_commands(app):
    """Register CLI commands with the Flask app."""

    @app.cli.command("rebuild-search")
    def rebuild_search_command():
        """Rebuild the FTS5 search index."""
        from app.search import rebuild_fts

        rebuild_fts()
        click.echo("Search index rebuilt.")

    @app.cli.command("cleanup-orphaned-images")
    def cleanup_orphaned_images_command():
        """Clean up image files not associated with any post."""
        from app.routes.admin.media import cleanup_orphaned_images

        orphaned, missing = cleanup_orphaned_images(app)
        click.echo(f"Cleaned up {orphaned} orphaned image file(s).")
        if missing > 0:
            click.echo(f"Cleared {missing} missing image reference(s) from posts.")

    @app.cli.command("create-admin")
    def create_admin_command():
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
            db.session.commit()
            click.echo(f"User '{username}' promoted to admin.")
        else:
            user = User(username=username, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                click.echo(f"User '{username}' already exists.")
                return
            click.echo(f"Admin user '{username}' created.")
