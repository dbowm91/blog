# Syndication Improvements Plan

## Executive Summary

This plan outlines enhancements to the blog's syndication capabilities. Based on deep-dive investigations across 8 areas, we recommend implementing **JSON Feed**, **RSS Enhancements**, **Conditional GET**, and **Cache Headers** as high-priority items. **Atom Feed** and **Tag-Specific RSS** are optional medium-priority items. **WebSub** and **Ping Services** should be skipped due to low adoption and obsolescence.

### Recommended Implementation Order
1. **JSON Feed (`/feed.json`)** — Quick win, modern format
2. **RSS Enhancements + Conditional GET + Cache Headers** — Combine into single `rss.py` refactor
3. **Atom Feed (`/atom`)** — Optional, low-effort compatibility
4. **Tag-Specific RSS Feeds** — Optional, refactors RSS generation

---

## Priority: HIGH

### 1. JSON Feed (`/feed.json`)

**Background**: JSON Feed (jsonfeed.org, version 1.1) is a modern alternative to XML-based RSS/Atom. It uses JSON format, widely supported by modern feed readers. MIME type: `application/feed+json`.

**Current State**: No JSON Feed exists. Only RSS 2.0 at `/rss`.

**Specification (v1.1)**:
- Required: `version` (`https://jsonfeed.org/version/1.1`), `title`, `items` (array)
- Recommended: `home_page_url`, `feed_url`, `description`, `authors` (array, new in 1.1), `language`
- Item required: `id` (URL recommended)
- Item optional: `url`, `title`, `content_html`, `content_text`, `summary`, `image`, `date_published` (ISO 8601), `date_modified`, `tags` (array of strings), `attachments`

**Implementation Steps**:

1. Add new route `/feed.json` to `app/routes/rss.py` (or create separate blueprint)
2. Create `_post_to_jsonfeed_item(post)` helper function
3. Render markdown to HTML using existing pattern (`markdown.markdown()` + `nh3.clean()`)
4. Map Post model fields:
   - `id` → `{BASE_URL}/post/{post.slug}` (canonical URL)
   - `title` → `post.title`
   - `content_html` → rendered `post.body` (full content)
   - `summary` → `post.summary` (if exists)
   - `date_published` → `(post.published_at or post.created_at).isoformat()`
   - `date_modified` → `post.updated_at.isoformat()`
   - `tags` → `[tag.name for tag in post.tags]`
   - `image` → `{BASE_URL}/static/uploads/{post.image}` (if exists)
5. Add feed-level metadata: `authors` array with `AUTHOR_NAME` from config
6. Add autodiscovery link to `app/templates/base.html`:
   ```html
   <link rel="alternate" type="application/feed+json" href="/feed.json" title="JSON Feed">
   ```

**Dependencies**: None (can implement standalone)

**Testing**:
- Validate feed at https://validator.jsonfeed.org/
- Test endpoint returns correct MIME type
- Verify all Post fields map correctly

---

### 2. RSS Feed Enhancements

**Background**: Current RSS feed (`app/routes/rss.py`) is functional but missing key elements for full compliance and richer content delivery.

**Current State**: Basic RSS 2.0 with title, link, guid, description (stripped markdown), pubDate. Missing: full content, author, tags, image enclosures.

**Enhancements Required**:

#### 2.1 Add `content:encoded` (Full HTML Content)
- **Namespace**: Add `xmlns:content="http://purl.org/rss/1.0/modules/content/"` to `<rss>` tag
- **Content**: Render `post.body` markdown to HTML using `markdown.markdown()` + `nh3.clean()` (matching `app/__init__.py:185-189` pattern)
- **CDATA**: Wrap in `<![CDATA[...]]>` to preserve HTML tags
- **Element**: `<content:encoded>` per item

#### 2.2 Add Author Information
- **Config Sources**: `AUTHOR_NAME` (`app/config.py:85`), `FROM_ADDRESS` (`config.py:96`)
- **Item-level**: `<author>email (name)</author>` (RSS 2.0 format)
- **Channel-level**: `<managingEditor>email (name)</managingEditor>`
- **Note**: Post model has no per-post author relationship; all posts use global author

#### 2.3 Add Categories/Tags
- **Element**: `<category>` per tag (RSS 2.0 supports simple text categories)
- **Source**: `post.tags` relationship (many-to-many with Tag model)
- **Implementation**: Loop through `post.tags`, add `<category>{xml_escape(tag.name)}</category>`

#### 2.4 Add Image Enclosures
- **Element**: `<enclosure url="..." length="..." type="..." />`
- **Source**: `post.image` field (filename stored in `static/uploads/`)
- **Requirements**:
  - Construct full URL: `{BASE_URL}/static/uploads/{post.image}`
  - Get file size: `os.path.getsize()` on file path
  - Get MIME type: `mimetypes.guess_type()`
  - Only add if file exists on disk

**Implementation Steps**:

1. Modify `<rss>` tag to include content namespace:
   ```xml
   <rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
   ```

2. Add `_render_content_html(body)` helper using existing markdown/nh3 pattern

3. Update `feed()` function to include new elements per item

4. Add `managingEditor` to channel element

**Dependencies**: Enhancement #3 (Conditional GET) and #6 (Cache Headers) should be integrated in same refactor

---

### 3. Conditional GET Support

**Background**: Conditional GET allows clients to avoid re-downloading unchanged feeds by sending `If-Modified-Since` or `If-None-Match` headers. Server returns `304 Not Modified` if content hasn't changed.

**Current State**: No conditional GET support. Feeds always return full content.

**Implementation Details**:

#### 3.1 Last-Modified Calculation
- **Query**: `select(func.max(Post.updated_at)).filter_by(published=True)`
- **Index**: Uses existing `ix_posts_published_updated` index (efficient)
- **Fallback**: `utc_now()` if no published posts exist
- **Format**: RFC 2822 (`%a, %d %b %Y %H:%M:%S +0000`) matching existing RSS pubDate format

#### 3.2 If-Modified-Since Handling
- **Request header**: `request.if_modified_since` (Werkzeug parses automatically to timezone-aware UTC datetime)
- **Check**: Compare `last_modified <= request.if_modified_since`
- **Response**: Return `Response(status=304)` with appropriate headers

#### 3.3 ETag Handling
- **Generation**: Timestamp-based recommended: `f'"{int(last_modified.timestamp())}"'` (strong ETag)
- **Alternative**: Content-based hash (requires generating feed first, not recommended)
- **Request header**: `If-None-Match`
- **Check**: Compare with stored ETag

#### 3.4 Response Headers
```python
response.last_modified = last_modified
response.headers["ETag"] = f'"{int(last_modified.timestamp())}"'
```

**Implementation Steps**:

1. Add `from sqlalchemy import func` import
2. Query `last_modified` before generating feed
3. Check `request.if_modified_since` early (return 304 if unchanged)
4. Generate feed XML
5. Set `response.last_modified` and `response.headers["ETag"]`
6. Optionally use `response.make_conditional(request)` (Werkzeug helper)

**Dependencies**: None, but should be combined with #2 (RSS Enhancements) and #6 (Cache Headers)

**Testing**:
```bash
# Test If-Modified-Since
curl -I -H "If-Modified-Since: $(date -u +'%a, %d %b %Y %H:%M:%S GMT')" http://localhost:5000/rss

# Test ETag
curl -I -H 'If-None-Match: "<etag>"' http://localhost:5000/rss
```

---

## Priority: MEDIUM

### 4. Atom Feed (`/atom`)

**Background**: Atom (RFC 4287) is a more standardized alternative to RSS 2.0 (which is a de facto standard). MIME type: `application/atom+xml`.

**Current State**: No Atom feed exists.

**Specification (RFC 4287)**:
- Feed required: `id` (tag URI), `title`, `updated` (ISO 8601)
- Feed optional: `author`, `category`, `link`, `subtitle`, `rights`, `generator`, `icon`, `logo`
- Entry required: `id`, `title`, `updated`
- Entry optional: `author`, `content` (with `type` attribute), `link`, `published`, `summary`, `category`

**Key Differences from RSS**:
| Feature | RSS 2.0 | Atom 1.0 |
|---------|----------|-----------|
| Date format | RFC 822 | ISO 8601 |
| Unique ID | `<guid>` (URL) | `<id>` (tag URI) |
| Author | `<author>` (email-based) | `<author>` (name-based) |
| Content | `<description>` + `<content:encoded>` | `<content type="html">` |
| Timestamps | `<pubDate>` only | `<published>` + `<updated>` |

**Implementation Steps**:

1. Add route `/atom` to `app/routes/rss.py` (same blueprint)
2. Generate tag URI for IDs: `tag:{domain},2024:post/{post.id}`
3. Map Post fields:
   - `id` → tag URI
   - `title` → `post.title`
   - `published` → `atom:published` (ISO 8601)
   - `updated` → `atom:updated` (ISO 8601)
   - `content` → `post.summary` or stripped markdown (type="text")
   - `category` → `term="{tag.name}" scheme="{BASE_URL}/tags/{tag.slug}"`
4. Add feed-level `author` with `AUTHOR_NAME`
5. Add autodiscovery link to `base.html`

**Verdict**: Low-effort (~50 lines) but marginal benefit since RSS + JSON Feed cover most readers. Optional implementation.

---

### 5. Tag-Specific RSS Feeds

**Background**: Allow users to subscribe to RSS feeds filtered by specific tags (e.g., `/tag/python/rss`).

**Current State**: Tag pages exist at `/tag/<slug>` (route in `app/routes/public.py:286`). No tag-specific RSS feeds.

**Implementation Steps**:

1. **Refactor RSS Generation**: Extract reusable helper `_generate_rss_xml(posts, title, description, link_override)` from `feed()` function

2. **Add Tag Feed Route**: Add to `app/routes/rss.py`:
   ```python
   @rss.route("/tag/<slug>")
   def tag_feed(slug) -> Response:
       tag = db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()
       if not tag:
           abort(404)
       posts = (db.session.execute(
           select(Post)
           .filter(Post.published == True, Post.tags.any(Tag.id == tag.id))
           .order_by(Post.published_at.desc().nullslast(), Post.created_at.desc())
           .limit(20)
       ).scalars().all())
       xml = _generate_rss_xml(
           posts,
           title=f"{APP_TITLE} - Tag: {tag.name}",
           description=f"Posts tagged with '{tag.name}'",
           link_override=f"{BASE_URL}/tag/{slug}/rss",
       )
       return Response(xml, mimetype="application/rss+xml")
   ```

3. **URL Structure**: `/tag/<slug>` on same `rss` blueprint (no `url_prefix` currently)

4. **Add Autodiscovery**: In `app/templates/tag.html`:
   ```jinja2
   {% block head_extra %}
   <link rel="alternate" type="application/rss+xml" 
         title="{{ site_title }} - {{ tag.name }}" 
         href="{{ url_for('rss.tag_feed', slug=tag.slug) }}">
   {% endblock %}
   ```

**Dependencies**: Requires refactoring RSS generation first (combine with #2)

---

### 6. Cache Headers for Feeds

**Background**: Proper cache headers reduce bandwidth and server load by allowing clients/proxies to cache feeds.

**Current State**: No cache headers on feeds. Global `after_request` handler (`app/__init__.py:272-315`) only sets cache headers for `/static/` paths.

**Recommended Headers**:

| Header | Value | Explanation |
|--------|-------|-------------|
| `Cache-Control` | `public, max-age=86400, s-maxage=604800, stale-while-revalidate=3600` | Browser: 1 day, CDN: 7 days, stale revalidation: 1 hour |
| `Last-Modified` | RFC 2822 date | Most recent post's `updated_at` |
| `ETag` | `"<timestamp>"` | Strong ETag based on last modified |

**Adjust `max-age` based on posting frequency**:
- Weekly+ posts: `max-age=604800` (7 days)
- Daily posts: `max-age=86400` (1 day)
- Multiple/day: `max-age=3600` (1 hour)

**CDN-Specific**:
- Cloudflare respects `s-maxage` override
- Nginx: `gzip_types` already includes `application/rss+xml` (DEPLOY.md:600)

**Implementation**: Combine with #3 (Conditional GET) in same refactor of `rss.py`

---

## Priority: LOW (Skip)

### 7. WebSub/PubSubHubbub Support

**Background**: WebSub (W3C Recommendation 2018) is a real-time content distribution protocol. Publishers notify a hub, which pushes updates to subscribers.

**Findings**:
- **Hub Options**: Superfeedr (free tier: 100 subs; paid $99/mo+), self-hosted
- **Required Changes**:
  - Add `<atom:link rel="hub" href="...">` to RSS/Atom feeds
  - Create `/websub/callback` endpoint for subscription verification
  - Ping hub on post publish via `POST /hub` with `hub.mode=publish`
- **Adoption**: Very few RSS readers support WebSub in 2026
- **Verdict**: **Skip** — low adoption, adds complexity. JSON Feed + RSS + Conditional GET cover modern use cases better.

**If Implementing Later**:
- Use Superfeedr free tier
- Make opt-in via `config.toml [websub]` section
- Add `app/routes/websub.py` for callback handling

---

### 8. Ping Services (Ping-O-Matic)

**Background**: XML-RPC ping services notify blog directories of new content. Popular in mid-2000s.

**Findings**:
- **Alive Services in 2026**: Ping-O-Matic (`http://rpc.pingomatic.com/`), Twingly (`https://rpc.twingly.com/`)
- **Dead Services**: Most legacy services return 403/NXDomain
- **Protocol**: XML-RPC `weblogUpdates.ping` or `weblogUpdates.extendedPing`
- **Integration**: Call after post publish in `app/routes/admin/posts.py`
- **Adoption**: Obsolete protocol (WordPress marked it obsolete)
- **Verdict**: **Skip** — obsolete, minimal SEO benefit. Search engines use sitemap.xml (blog already has `/sitemap.xml`).

**Security Concern**: XML-RPC endpoints historically abused for DDoS reflection attacks.

**Better Alternatives**:
- Submit sitemap to Google Search Console / Bing Webmaster Tools
- WebSub for real-time subscribers
- JSON Feed for modern feed readers

---

## File Changes Summary

| File | Change | Priority |
|------|--------|----------|
| `app/routes/rss.py` | Add JSON Feed route, enhance RSS (content:encoded, author, tags, enclosures), add Conditional GET, add Cache Headers, refactor for tag feeds, add Atom feed (optional) | High/Medium |
| `app/templates/base.html` | Add JSON Feed autodiscovery link, Atom autodiscovery link (optional) | High/Medium |
| `app/templates/tag.html` | Add tag-specific RSS autodiscovery link (optional) | Medium |
| `app/routes/admin/posts.py` | No changes needed (skip WebSub/ping) | - |
| `app/config.py` | No changes needed (JSON Feed uses existing config vars) | - |
| `config.toml` | No changes needed (skip WebSub/ping) | - |

---

## Testing Strategy

1. **JSON Feed**:
   - Validate at https://validator.jsonfeed.org/
   - Test with `curl http://localhost:5000/feed.json`
   - Verify MIME type `application/feed+json`

2. **RSS Enhancements**:
   - Validate at https://validator.w3.org/feed/
   - Check `content:encoded` has full HTML
   - Verify author, categories, enclosures present

3. **Conditional GET**:
   - Test with `curl -I -H "If-Modified-Since: ..." http://localhost:5000/rss`
   - Verify 304 response when unchanged
   - Verify 200 with full content when modified

4. **Cache Headers**:
   - Test with `curl -I http://localhost:5000/rss`
   - Verify `Cache-Control`, `Last-Modified`, `ETag` headers present

5. **Atom Feed** (optional):
   - Validate at https://validator.w3.org/feed/
   - Verify tag URI format for IDs

6. **Tag-Specific RSS** (optional):
   - Test with `curl http://localhost:5000/tag/<slug>`
   - Verify filtered posts only

---

## Rollout Plan

### Phase 1: High Priority (Implement First)
1. Implement JSON Feed (`/feed.json`)
2. Refactor `rss.py`:
   - Add RSS enhancements (content:encoded, author, tags, enclosures)
   - Add Conditional GET support
   - Add Cache Headers
3. Update `base.html` with autodiscovery links
4. Test all changes thoroughly

### Phase 2: Medium Priority (Optional)
1. Add Atom Feed (`/atom`) if desired
2. Refactor RSS generation for reusability
3. Add Tag-Specific RSS Feeds
4. Update `tag.html` with autodiscovery link

### Phase 3: Skip
- Do not implement WebSub
- Do not implement Ping Services

---

## References

- JSON Feed Spec: https://jsonfeed.org/version/1.1
- RSS 2.0 Spec: https://www.rssboard.org/rss-specification
- Atom RFC 4287: https://tools.ietf.org/html/rfc4287
- WebSub W3C: https://www.w3.org/TR/websub/
- HTTP Conditional Requests: https://tools.ietf.org/html/rfc7232
- Existing Code: `app/routes/rss.py`, `app/models.py`, `app/config.py`
