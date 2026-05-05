from flask import Blueprint, Response, request, current_app
from typing import Any, cast
from sqlalchemy import select
from sqlalchemy.orm import joinedload, QueryableAttribute
from app.models import Post
from app.extensions import db
from app import cache as flask_cache
from app.config import APP_TITLE, APP_DESCRIPTION, BASE_URL, AUTHOR_NAME
from app.utils import xml_escape, utc_now
from app.markdown_config import MARKDOWN_ALLOWED_TAGS, MARKDOWN_ALLOWED_ATTRIBUTES
import re
import hashlib
import markdown
import nh3

_MARKDOWN_RE = re.compile(r"[#*_`~\[\]|]+")

rss = Blueprint("rss", __name__)


def _strip_markdown(text: str) -> str:
    return _MARKDOWN_RE.sub("", text)


def _generate_etag(posts: list[Any], feed_type: str = "rss") -> str:
    """Generate ETag from post IDs and timestamps."""
    content = ",".join(
        f"{p.id}:{int((p.updated_at or p.created_at).timestamp())}"
        for p in posts
    )
    return hashlib.md5(content.encode()).hexdigest() + f"_{feed_type}"


def _get_feed_posts(limit: int = 20) -> tuple[list[Post], str]:
    """Get posts for feed with conditional GET support.

    Returns (posts, etag) tuple.
    """
    posts = (
        db.session.execute(
            select(Post)
            .options(joinedload(cast(QueryableAttribute, Post.tags)))
            .filter_by(published=True)
            .order_by(Post.published_at.desc().nullslast(), Post.created_at.desc())
            .limit(limit)
        ).scalars().unique().all()
    )
    etag = _generate_etag(list(posts))
    return list(posts), etag


def _get_cached_feed_posts(limit: int = 20) -> list[Post]:
    """Get cached feed posts - uses cache unless in testing mode."""
    if current_app.testing:
        posts, _ = _get_feed_posts(limit)
        return posts
    return _get_cached_atom_posts(limit)

@flask_cache.cached(timeout=300, key_prefix="atom_feed_posts")
def _get_cached_atom_posts(limit: int = 20) -> list[Post]:
    """Cached version for Atom feed."""
    posts, _ = _get_feed_posts(limit)
    return posts

def _get_atom_feed_posts(limit: int = 20) -> list[Post]:
    """Get posts for Atom feed with caching."""
    if current_app.testing:
        return _get_feed_posts()[0]
    return _get_cached_atom_posts(limit)


def _add_cache_headers(response: Any, etag: str, is_feed: bool = True) -> Any:
    """Add cache headers to feed response."""
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Expires"] = "Thu, 01 Jan 2027 00:00:00 GMT"
    return response

def invalidate_rss_cache() -> None:
    """Invalidate RSS feed cache."""
    flask_cache.delete("rss_feed_posts")


@rss.route("/atom")
def atom_feed() -> Any:
    """Atom 1.0 feed implementation."""
    posts = _get_atom_feed_posts()
    etag = _generate_etag(posts, "atom")

    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status=304)

    feed_id = xml_escape(f"{BASE_URL}/atom")
    feed_updated = utc_now().isoformat() + "Z"
    if posts:
        latest = max(post.updated_at or post.created_at for post in posts)
        feed_updated = latest.isoformat() + "Z"

    entries = []
    for post in posts:
        post_link = f"{BASE_URL}/post/{post.slug}"
        post_id = xml_escape(post_link)
        post_title = xml_escape(post.title)
        post_updated = (post.updated_at or post.created_at).isoformat() + "Z"
        post_published = (post.published_at or post.created_at).isoformat() + "Z"

        content_html = nh3.clean(
            markdown.markdown(post.body, extensions=["fenced_code", "tables"]),
            tags=MARKDOWN_ALLOWED_TAGS,
            attributes=MARKDOWN_ALLOWED_ATTRIBUTES,
        )

        categories = "".join(
            f'    <category term="{xml_escape(tag.name)}"/>\n'
            for tag in cast(list[Any], post.tags)
        )

        entries.append(f"""    <entry>
      <id>{post_id}</id>
      <title>{post_title}</title>
      <link href="{xml_escape(post_link)}"/>
      <updated>{post_updated}</updated>
      <published>{post_published}</published>
      <author>
        <name>{xml_escape(AUTHOR_NAME or "admin")}</name>
      </author>
{categories}      <content type="html">{xml_escape(content_html)}</content>
    </entry>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>{feed_id}</id>
  <title>{xml_escape(APP_TITLE)}</title>
  <subtitle>{xml_escape(APP_DESCRIPTION)}</subtitle>
  <updated>{feed_updated}</updated>
  <link href="{xml_escape(BASE_URL)}" rel="alternate"/>
  <link href="{feed_id}" rel="self" type="application/atom+xml"/>
  <author>
    <name>{xml_escape(AUTHOR_NAME or "admin")}</name>
  </author>
{"".join(entries)}
</feed>"""

    response = Response(xml, mimetype="application/atom+xml")
    return _add_cache_headers(response, etag, is_feed=False)
