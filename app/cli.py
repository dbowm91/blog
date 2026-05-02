"""CLI commands for the Flask application."""

import json
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
        user = db.session.execute(
            select(User).filter_by(username=username)
        ).scalar_one_or_none()
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
        from app.services.serialization import (
            export_data_to_dict
        )

        posts = db.session.execute(
            select(Post).order_by(Post.created_at)
        ).scalars().all()

        subscribers = db.session.execute(
            select(Subscriber).order_by(Subscriber.created_at)
        ).scalars().all()

        tags = db.session.execute(
            select(Tag).order_by(Tag.name)
        ).scalars().all()

        pages = db.session.execute(
            select(Page).order_by(Page.created_at)
        ).scalars().all()

        data = export_data_to_dict(posts, subscribers, tags, pages)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        click.echo(
            f"Exported {len(posts)} posts, {len(subscribers)} subscribers, "
            f"{len(tags)} tags, and {len(pages)} pages to '{output_file}'."
        )

    @app.cli.command("import-data")
    @click.argument("input_file")
    @click.option("--skip-confirmed/--include-confirmed", default=True,
                  help="Skip already-confirmed subscribers (default: skip)")
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

        tag_cache = {
            t.slug: t for t in db.session.execute(select(Tag)).scalars().all()
        }

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
                    sync_fts(existing.id, existing.title, existing.body, existing.summary, existing.published)

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
                subscriber.created_at = datetime.fromisoformat(
                    subscriber_data["created_at"]
                )
            if subscriber_data.get("expires_at"):
                subscriber.expires_at = datetime.fromisoformat(
                    subscriber_data["expires_at"]
                )
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
            user = User(username=f"author{i+1}", is_admin=False)
            user.set_password("Password123!")
            db.session.add(user)
            sample_users.append(user)
        commit_with_rollback()
        click.echo(f"Created {len(sample_users)} users.")

        for i in range(posts):
            post = Post(
                title=f"Sample Post {i+1}: Testing the Blog",
                slug=f"sample-post-{i+1}",
                body=f"# Sample Post {i+1}\n\nThis is sample content for post {i+1}. "
                f"It contains multiple paragraphs to simulate real content.\n\n"
                f"## Section {i+1}.1\n\n"
                f"Here is some more content with a code example:\n\n"
                f"```python\nprint('Hello, World!')\n```\n\n"
                f"## Section {i+1}.2\n\n"
                f"More content here with a list:\n\n"
                f"- Item 1\n- Item 2\n- Item 3\n",
                summary=f"This is a summary for sample post {i+1}",
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
                email=f"subscriber{i+1}@example.com",
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
