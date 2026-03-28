from flask import Blueprint, Response
from app.models import Post
from app.config import APP_TITLE, APP_DESCRIPTION, BASE_URL
from app.utils import xml_escape, utc_now
import re

_MARKDOWN_RE = re.compile(r"[#*_`~\[\]\(\)!>|]+")

rss = Blueprint("rss", __name__)


def _strip_markdown(text: str) -> str:
    return _MARKDOWN_RE.sub("", text)


@rss.route("/rss")
def feed():
    posts = (
        Post.query.filter_by(published=True)
        .order_by(Post.published_at.desc().nullslast(), Post.created_at.desc())
        .limit(20)
        .all()
    )

    items = []
    for post in posts:
        pub_date = (post.published_at or post.created_at).strftime("%a, %d %b %Y %H:%M:%S +0000")
        link = f"{BASE_URL}/post/{post.slug}"
        if post.summary:
            summary = post.summary
        else:
            summary = _strip_markdown(post.body[:200])
        items.append(f"""    <item>
      <title>{xml_escape(post.title)}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <description>{xml_escape(summary)}</description>
      <pubDate>{pub_date}</pubDate>
    </item>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{xml_escape(APP_TITLE)}</title>
    <link>{BASE_URL}</link>
    <description>{xml_escape(APP_DESCRIPTION)}</description>
    <language>en-us</language>
    <lastBuildDate>{utc_now().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
    <atom:link href="{BASE_URL}/rss" rel="self" type="application/rss+xml"/>
{"".join(items)}
  </channel>
</rss>"""

    return Response(xml, mimetype="application/rss+xml")
