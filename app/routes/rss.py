from flask import Blueprint, Response
from app.models import Post
from app.config import APP_TITLE, APP_DESCRIPTION, BASE_URL
from app.utils import xml_escape
from datetime import datetime, timezone

rss = Blueprint("rss", __name__)


@rss.route("/rss")
def feed():
    posts = (
        Post.query.filter_by(published=True)
        .order_by(Post.created_at.desc())
        .limit(20)
        .all()
    )

    items = []
    for post in posts:
        pub_date = post.created_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
        link = f"{BASE_URL}/post/{post.slug}"
        summary = post.summary or post.body[:200]
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
    <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
    <atom:link href="{BASE_URL}/rss" rel="self" type="application/rss+xml"/>
{"".join(items)}
  </channel>
</rss>"""

    return Response(xml, mimetype="application/rss+xml")
