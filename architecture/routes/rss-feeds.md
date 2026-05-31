# RSS/Feeds (`app/routes/rss.py`)

Provides RSS 2.0, Atom, and JSON feed formats.

## Endpoints

| Format | Route | Purpose |
|--------|-------|---------|
| RSS 2.0 | `/rss` | RSS 2.0 feed |
| Atom | `/atom` | Atom feed |
| JSON | `/json` | JSON Feed format |
| RSS 2.0 | `/tag/<slug>/rss` | RSS 2.0 feed for posts with a specific tag |
| Atom | `/tag/<slug>/atom` | Atom feed for posts with a specific tag |
| JSON | `/tag/<slug>/json` | JSON Feed for posts with a specific tag |
| RSS 2.0 | `/series/<slug>/rss` | RSS 2.0 feed for posts in a specific series |
| Atom | `/series/<slug>/atom` | Atom feed for posts in a specific series |
| JSON | `/series/<slug>/json` | JSON Feed for posts in a specific series |

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
  "authors": [{"name": "Author Name"}],
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

## Tag Feeds

Tag feeds filter posts by tag slug, providing the same three formats as the main feeds.

### Tag RSS 2.0 (`/tag/<slug>/rss`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>#tagname - DevLog</title>
    <link>http://example.com</link>
    <description>Posts tagged with #tagname</description>
    <language>en-us</language>
    <lastBuildDate>Wed, 06 May 2026 10:00:00 GMT</lastBuildDate>
    <atom:link href="http://example.com/tag/tagname/rss" rel="self" type="application/rss+xml"/>
    <item>
      <title>Post Title</title>
      <link>http://example.com/post/post-slug</link>
      <guid isPermaLink="false">post-slug</guid>
      <pubDate>Wed, 06 May 2026 10:00:00 GMT</pubDate>
      <category>tagname</category>
      <description>Post summary...</description>
      <content:encoded><![CDATA[Full HTML content...]]></content:encoded>
    </item>
  </channel>
</rss>
```

### Tag Atom (`/tag/<slug>/atom`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>#tagname - DevLog</title>
  <id>http://example.com/tag/tagname/atom</id>
  <updated>2026-05-06T10:00:00Z</updated>
  <link href="http://example.com"/>
  <link href="http://example.com/tag/tagname/atom" rel="self"/>
  <entry>
    <title>Post Title</title>
    <id>http://example.com/post/post-slug</id>
    <updated>2026-05-06T10:00:00Z</updated>
    <published>2026-05-06T10:00:00Z</published>
    <link href="http://example.com/post/post-slug"/>
    <category term="tagname"/>
    <content type="html">Full HTML content...</content>
  </entry>
</feed>
```

### Tag JSON Feed (`/tag/<slug>/json`)

```json
{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "#tagname - DevLog",
  "home_page_url": "http://example.com",
  "feed_url": "http://example.com/tag/tagname/json",
  "items": [
    {
      "id": "post-slug",
      "title": "Post Title",
      "url": "http://example.com/post/post-slug",
      "date_published": "2026-05-06T10:00:00Z",
      "date_modified": "2026-05-06T10:00:00Z",
      "content_html": "Full HTML content...",
      "tags": ["tagname"]
    }
  ]
}
```

## Series Feeds

Series feeds filter posts by series slug, providing the same three formats as the main feeds.

### Series RSS 2.0 (`/series/<slug>/rss`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Series Name - DevLog</title>
    <link>http://example.com</link>
    <description>Posts in the Series Name series</description>
    <language>en-us</language>
    <lastBuildDate>Wed, 06 May 2026 10:00:00 GMT</lastBuildDate>
    <atom:link href="http://example.com/series/series-slug/rss" rel="self" type="application/rss+xml"/>
    <item>
      <title>Post Title</title>
      <link>http://example.com/post/post-slug</link>
      <guid isPermaLink="false">post-slug</guid>
      <pubDate>Wed, 06 May 2026 10:00:00 GMT</pubDate>
      <category>tagname</category>
      <description>Post summary...</description>
      <content:encoded><![CDATA[Full HTML content...]]></content:encoded>
    </item>
  </channel>
</rss>
```

### Series Atom (`/series/<slug>/atom`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Series Name - DevLog</title>
  <id>http://example.com/series/series-slug/atom</id>
  <updated>2026-05-06T10:00:00Z</updated>
  <link href="http://example.com"/>
  <link href="http://example.com/series/series-slug/atom" rel="self"/>
  <entry>
    <title>Post Title</title>
    <id>http://example.com/post/post-slug</id>
    <updated>2026-05-06T10:00:00Z</updated>
    <published>2026-05-06T10:00:00Z</published>
    <link href="http://example.com/post/post-slug"/>
    <category term="tagname"/>
    <content type="html">Full HTML content...</content>
  </entry>
</feed>
```

### Series JSON Feed (`/series/<slug>/json`)

```json
{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "Series Name - DevLog",
  "home_page_url": "http://example.com",
  "feed_url": "http://example.com/series/series-slug/json",
  "items": [
    {
      "id": "post-slug",
      "title": "Post Title",
      "url": "http://example.com/post/post-slug",
      "date_published": "2026-05-06T10:00:00Z",
      "date_modified": "2026-05-06T10:00:00Z",
      "content_html": "Full HTML content...",
      "tags": ["tagname"]
    }
  ]
}
```

## Caching

Two layers of caching:
- **Server-side cache**: 5 minutes via Flask-Caching (TTL 300s)
- **HTTP Cache-Control**: `public, max-age=3600` (1 hour) set in `app/routes/rss.py:98`

## See Also
- [Public Routes](public-routes.md) - Public blog routes
- [API Routes](api-routes.md) - REST API
