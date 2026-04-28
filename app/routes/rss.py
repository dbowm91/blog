from flask import Blueprint, Response, request, make_response
from sqlalchemy import select
from app.models import Post
from app.extensions import db
from app.config import APP_TITLE, APP_DESCRIPTION, BASE_URL, AUTHOR_NAME
from app.utils import xml_escape, utc_now
import re
import hashlib
import json

_MARKDOWN_RE = re.compile(r"[#*_`~\[\]\(\)!>|]+")

rss = Blueprint("rss", __name__)


def _strip_markdown(text: str) -> str:
    return _MARKDOWN_RE.sub("", text)


def _generate_etag(posts: list, use_json: bool = False) -> str:
    """Generate ETag from post IDs and timestamps."""
    content = ",".join(
        f"{p.id}:{int((p.updated_at or p.created_at).timestamp())}"
        for p in posts
    )
    suffix = "_json" if use_json else "_rss"
    return hashlib.md5(content.encode()).hexdigest() + suffix


def _get_feed_posts(limit: int = 20) -> tuple[list, str]:
    """Get posts for feed with conditional GET support.

    Returns (posts, etag) tuple.
    """
    posts = (
        db.session.execute(
            select(Post)
            .filter_by(published=True)
            .order_by(Post.published_at.desc().nullslast(), Post.created_at.desc())
            .limit(limit)
        ).scalars().all()
    )
    etag = _generate_etag(posts)
    return posts, etag


def _add_cache_headers(response: Response, etag: str, is_feed: bool = True) -> Response:
    """Add cache headers to feed response."""
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Expires"] = "Thu, 01 Jan 2027 00:00:00 GMT"
    return response


@rss.route("/rss")
def feed() -> Response:
    posts, etag = _get_feed_posts()

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
    posts, etag = _get_feed_posts()

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
