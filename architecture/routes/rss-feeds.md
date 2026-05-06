# RSS/Feeds (`app/routes/rss.py`)

Provides RSS 2.0, Atom, and JSON feed formats.

## Endpoints

| Format | Route | Purpose |
|--------|-------|---------|
| RSS 2.0 | `/rss` | RSS 2.0 feed |
| Atom | `/atom` | Atom feed |
| JSON | `/json` | JSON Feed format |

## RSS 2.0 (`/rss`)

Standard RSS 2.0 feed with channel information:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>DevLog</title>
    <link>http://example.com</link>
    <description>A developer's blog</description>
    <language>en-us</language>
    <lastBuildDate>Wed, 06 May 2026 10:00:00 GMT</lastBuildDate>
    <item>
      <title>Post Title</title>
      <link>http://example.com/post/post-slug</link>
      <guid>http://example.com/post/post-slug</guid>
      <pubDate>Wed, 06 May 2026 10:00:00 GMT</pubDate>
      <description>Post summary...</description>
    </item>
  </channel>
</rss>
```

## Atom (`/atom`)

Atom feed format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>DevLog</title>
  <id>http://example.com</id>
  <updated>2026-05-06T10:00:00Z</updated>
  <entry>
    <title>Post Title</title>
    <id>http://example.com/post/post-slug</id>
    <updated>2026-05-06T10:00:00Z</updated>
    <summary>Post summary...</summary>
    <link href="http://example.com/post/post-slug"/>
  </entry>
</feed>
```

## JSON Feed (`/json`)

[JSON Feed](https://jsonfeed.org/) format:

```json
{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "DevLog",
  "home_page_url": "http://example.com",
  "feed_url": "http://example.com/json",
  "items": [
    {
      "id": "http://example.com/post/post-slug",
      "url": "http://example.com/post/post-slug",
      "title": "Post Title",
      "summary": "Post summary...",
      "date_published": "2026-05-06T10:00:00Z"
    }
  ]
}
```

## Caching

All feeds are cached for 5 minutes.

## See Also
- [Public Routes](routes/public-routes.md) - Public blog routes
- [API Routes](routes/api-routes.md) - REST API
