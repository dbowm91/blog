from flask import Blueprint, Response, request, make_response, current_app
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.models import Post
from app.extensions import db
from app import cache as flask_cache
from app.config import APP_TITLE, APP_DESCRIPTION, BASE_URL, AUTHOR_NAME
from app.utils import xml_escape, utc_now
from app.markdown_config import MARKDOWN_ALLOWED_TAGS, MARKDOWN_ALLOWED_ATTRIBUTES
import re
import hashlib
import json
import markdown
import nh3

_MARKDOWN_RE = re.compile(r"[#*_`~\[\]\(\)!>|]+")

rss = Blueprint("rss", __name__)


def _strip_markdown(text: str) -> str:
    return _MARKDOWN_RE.sub("", text)


def _generate_etag(posts: list, feed_type: str = "rss") -> str:
    """Generate ETag from post IDs and timestamps."""
    content = ",".join(
        f"{p.id}:{int((p.updated_at or p.created_at).timestamp())}"
        for p in posts
    )
    return hashlib.md5(content.encode()).hexdigest() + f"_{feed_type}"


def _get_feed_posts(limit: int = 20):
    """Get posts for feed with conditional GET support.

    Returns (posts, etag) tuple.
    """
    posts = (
        db.session.execute(
            select(Post)
            .options(joinedload(Post.tags))
            .filter_by(published=True)
            .order_by(Post.published_at.desc().nullslast(), Post.created_at.desc())
            .limit(limit)
        ).scalars().unique().all()
    )
    etag = _generate_etag(posts)
    return posts, etag


def _get_cached_feed_posts(limit: int = 20):
    """Get cached feed posts - uses cache unless in testing mode."""
    if current_app.testing:
        return _get_feed_posts()[0]
    return _get_cached_feed_posts_cached(limit)


@flask_cache.cached(timeout=300, key_prefix="rss_feed_posts")
def _get_cached_feed_posts_cached(limit: int = 20):
    """Cached version - only called when not testing."""
    posts, _ = _get_feed_posts(limit)
    return posts


def invalidate_rss_cache():
    """Invalidate RSS feed cache."""
    flask_cache.delete("rss_feed_posts")


def _add_cache_headers(response: Response, etag: str, is_feed: bool = True) -> Response:
    """Add cache headers to feed response."""
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Expires"] = "Thu, 01 Jan 2027 00:00:00 GMT"
    return response


def invalidate_rss_cache():
    """Stub for cache invalidation - RSS uses ETag-based caching."""
    pass


@rss.route("/rss")
def feed() -> Response:
    posts = _get_cached_feed_posts()
    etag = _generate_etag(posts, "rss")

    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status=304)

    items = []
    for post in posts:
        pub_date = (post.published_at or post.created_at).strftime("%a, %d %b %Y %H:%M:%S +0000")
        link = xml_escape(f"{BASE_URL}/post/{post.slug}")
        if post.summary:
            summary = post.summary
        else:
            summary = _strip_markdown(post.body[:200])

        categories = "".join(
            f"      <category>{xml_escape(tag.name)}</category>\n"
            for tag in post.tags
        )

        items.append(f"""    <item>
      <title>{xml_escape(post.title)}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <description>{xml_escape(summary)}</description>
      <pubDate>{pub_date}</pubDate>
      <author>{xml_escape(AUTHOR_NAME or "admin")}</author>
{categories}  </item>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{xml_escape(APP_TITLE)}</title>
    <link>{xml_escape(BASE_URL)}</link>
    <description>{xml_escape(APP_DESCRIPTION)}</description>
    <language>en-us</language>
    <lastBuildDate>{utc_now().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
    <atom:link href="{xml_escape(BASE_URL)}/rss" rel="self" type="application/rss+xml"/>
{"".join(items)}
  </channel>
</rss>"""

    response = Response(xml, mimetype="application/rss+xml")
    return _add_cache_headers(response, etag)


@rss.route("/json")
def json_feed() -> Response:
    """JSON Feed implementation (https://jsonfeed.org/)"""
    posts = _get_cached_feed_posts()
    etag = _generate_etag(posts, "json")

    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status=304)

    items = []
    for post in posts:
        pub_date = (post.published_at or post.created_at).isoformat() + "Z"
        link = f"{BASE_URL}/post/{post.slug}"

        if post.summary:
            summary = post.summary
        else:
            summary = _strip_markdown(post.body[:200])

        item = {
            "id": link,
            "url": link,
            "title": post.title,
            "summary": summary,
            "date_published": pub_date,
            "date_modified": (post.updated_at or post.created_at).isoformat() + "Z",
            "tags": [tag.name for tag in post.tags],
        }

        if post.image:
            item["image"] = f"{BASE_URL}/static/uploads/{post.image}"

        item["content_html"] = nh3.clean(
            markdown.markdown(post.body, extensions=["fenced_code", "tables"]),
            tags=MARKDOWN_ALLOWED_TAGS,
            attributes=MARKDOWN_ALLOWED_ATTRIBUTES,
        )

        items.append(item)

    feed_data = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": APP_TITLE,
        "home_page_url": BASE_URL,
        "feed_url": f"{BASE_URL}/json",
        "description": APP_DESCRIPTION,
        "items": items,
    }

    if AUTHOR_NAME:
        feed_data["authors"] = [{"name": AUTHOR_NAME}]

    response = make_response(json.dumps(feed_data, indent=2))
    response.headers["Content-Type"] = "application/feed+json; charset=utf-8"
    return _add_cache_headers(response, etag, is_feed=False)


@flask_cache.cached(timeout=300, key_prefix="atom_feed_posts")
def _get_cached_atom_posts(limit: int = 20):
    """Cached version for Atom feed."""
    posts, _ = _get_feed_posts(limit)
    return posts


def _get_atom_feed_posts(limit: int = 20):
    """Get posts for Atom feed with caching."""
    if current_app.testing:
        return _get_feed_posts()[0]
    return _get_cached_atom_posts(limit)


@rss.route("/atom")
def atom_feed() -> Response:
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
            for tag in post.tags
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
