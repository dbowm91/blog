# User Guide

Detailed documentation for blog administration and content management.

## Contents

- [Post Writing Guide](#post-writing-guide)
- [Tags](#tags)
- [Post Series Guide](#post-series-guide)
- [Preview Links](#preview-links)
- [Syntax Highlighting](#syntax-highlighting)
- [Feeds (RSS and JSON)](#feeds-rss-and-json)
- [Newsletter Management](#newsletter-management)
- [Admin Tasks](#admin-tasks)
- [Analytics](#analytics)
- [User Management](#user-management)
- [Media Library](#media-library)
- [S3 Storage](#s3-storage)
- [Page View Buffer](#page-view-buffer)
- [Search](#search)
- [Short URLs](#short-urls)

---

## Post Writing Guide

### Creating a New Post

1. Navigate to `/admin/` (Dashboard)
2. Click **New Post** button
3. Fill in the post fields:

| Field | Description |
|-------|-------------|
| Title | Post title (shown in browser tab, social shares) |
| Body | Markdown content (see Markdown Tips below) |
| Tags | Comma-separated tag names |
| Summary | Optional excerpt (if not set, auto-generated from body) |
| Image | Featured image filename |
| Publish At | Schedule for future publishing (leave empty to publish immediately) |

4. Click **Publish** to publish immediately, or **Save Draft** to save without publishing.

### Markdown Tips

**Headers for Table of Contents:**
```markdown
## Main Section      → H2 heading (appears in TOC)
### Subsection        → H3 heading (appears in TOC)
#### Sub-subsection   → H4 heading (not in TOC)
```

**Summary Divider:**
```markdown
First paragraph (summary shown in listings).

---

Rest of content (only shown on post page).
```

**Code Blocks:**
````markdown
```python
def hello():
    print("Hello, world!")
```
````

**Links and Images:**
```markdown
[Link text](https://example.com)
![Alt text](/static/uploads/image.png)
```

**Blockquotes:**
```markdown
> This is a blockquote.
```

### Previewing Posts

Click the **Preview** button to see how your post will look. The preview:

- Renders Markdown to HTML
- Sanitizes HTML via nh3 (strips dangerous tags/attributes)
- Shows table of contents from h2/h3 headings
- Uses current theme styling

### Editing Posts

1. Go to `/admin/`
2. Find your post and click **Edit**
3. Make changes
4. Click **Save Changes** to save changes

**Note:** If you see an "IntegrityError" message, a slug collision occurred. The system will auto-generate a new unique slug.

### Post Revisions

Every time you publish a post, a revision is saved:

1. While editing, click **Revisions** tab
2. View previous versions with author and timestamp
3. Click a revision to preview it
4. Click **Restore** to revert to that version

### Bulk Operations

From `/admin/`:

1. Check the box next to each post you want to modify
2. Select a bulk action from the dropdown:
   - **Publish** — Publish selected drafts
   - **Unpublish** — Take selected posts offline
   - **Delete** — Permanently remove (with confirmation)
3. Click **Apply**

### Scheduled Publishing

To schedule a post for future publication:

1. While creating/editing a post, find **Schedule publication** field
2. Select a future date and time
3. Click **Create Post** / **Save Changes** without checking **Publish immediately**

The scheduler checks every 5 minutes for posts with `scheduled_publish_at` in the past. When triggered, the post is automatically published and the scheduled time is cleared.

**Status indicators on `/admin/`:**
- Clock icon = Scheduled
- Green dot = Published
- Gray dot = Draft

### Short URLs

Each post gets a short URL: `/s/<code>` where `<code>` is a base62-encoded post ID.

- Find the short URL in the post edit page
- Useful for sharing on Twitter/character-limited platforms
- Short codes never change, even if the slug does

---

## Tags

Tags organize posts by topic and appear in the sidebar for filtering.

### Viewing Tags

Go to `/admin/tags` to see all tags with post counts.

### Creating Tags

1. Go to `/admin/tags`
2. Click **New Tag**
3. Enter:
   - **Name** — Display name (e.g., "Python")
   - **Slug** — URL-friendly version (auto-generated from name)
4. Click **Save**

### Editing Tags

1. Go to `/admin/tags`
2. Click on a tag name
3. Modify name or slug
4. Click **Save**

**Note:** Changing a tag's slug may break existing links to posts filtered by that tag.

### Deleting Tags

1. Go to `/admin/tags`
2. Click **Delete** next to the tag
3. Confirm deletion

**Warning:** Deleting a tag removes it from all posts. This cannot be undone.

### Tag Sidebar

The sidebar shows all tags with post counts. Click a tag to filter posts.

**Sidebar Configuration:**
In `config.toml`:
```toml
[app]
show_tags = true              # Show tags in sidebar (default: true)
tags_per_sidebar = 20         # Maximum tags to show (default: 20)
```

### Tag Cloud

Tags are displayed as a simple list sorted by name. No weighted tag cloud by default.

---

## Post Series Guide

Post series let you group related posts into ordered collections with sequential navigation.

### Workflow
1. Go to `/admin/series`
2. Click **New Series**
3. Enter:
   - **Name** — Display name (e.g., "Flask Tutorials")
   - **Slug** — URL-friendly version (auto-generated from name)
   - **Description** — Optional summary
4. Click **Save**
5. Add posts to a series:
   - Edit a post, select the series from the **Series** dropdown
   - Or go to the series page, click **Add Post** to select posts and set order

### Example
Create a "Python Basics" series, add 3 posts in order: "Variables", "Loops", "Functions". The series page at `/series/python-basics` shows all posts in order with previous/next navigation.

### Comparison with Tags
| Feature | Tags | Post Series |
|---------|------|-------------|
| Organization | Unordered many-to-many | Ordered one-to-many (post belongs to 0-1 series) |
| Purpose | Filter posts by topic | Group sequential/related content |
| Display | Sidebar filter, post tags | Series badge on posts, dedicated series page |
| Navigation | None | Previous/next post links in series |

---

## Preview Links

Shareable preview links let you share unpublished posts with reviewers without publishing them.

### HMAC Security
Preview links use HMAC-SHA256 signed tokens to prevent unauthorized access:
- Token includes post ID and expiry timestamp
- Signed with `SECRET_KEY` to prevent tampering
- Tokens are validated on every access

### Expiry
Tokens expire after 24 hours by default. Configure `PREVIEW_LINK_EXPIRY_HOURS` in `config.toml` to customize expiry time.

### Programmatic Generation
Generate preview links via the admin panel or code:
1. **Admin panel**: Edit a post, click the **Preview** button to open the preview
2. **Code**:
```python
import hmac
import hashlib
import time
from flask import current_app

def generate_preview_link(post_id):
    expires = int(time.time()) + 86400  # 24 hours
    message = f"{post_id}:{expires}".encode()
    token = hmac.new(
        current_app.config["SECRET_KEY"].encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return f"/preview/{post_id}?token={token}&expires={expires}"
```

---

## Syntax Highlighting

The blog uses Prism.js for syntax highlighting of code blocks in posts.

### Available Themes
| Theme | Description |
|-------|-------------|
| GitHub Dark | Default dark theme |
| GitHub Light | Light theme matching GitHub's style |
| Solarized Dark | Low-contrast dark theme for reduced eye strain |
| Monokai | High-contrast colorful theme |
| Atom One Dark | Inspired by Atom editor's dark theme |
| VS Code Light | Light theme matching VS Code's default |

Change themes in `/admin/settings` under **Syntax Highlighting Theme**.

### Main.js Hardcoding Bug & Fix
**Bug:** Previously, `app/static/js/main.js` used variable-based dynamic imports (`import(moduleName)`) to load syntax highlighting themes, which Vite could not bundle correctly.

**Fix:** Replaced with `import.meta.glob()` to explicitly pre-declare theme modules, making them compatible with Vite's build system:
```javascript
const themeModules = import.meta.glob('/node_modules/prismjs/themes/*.css', { import: 'default' });
// Load theme by name
function loadTheme(themeName) {
  const path = `/node_modules/prismjs/themes/prism-${themeName}.css`;
  return themeModules[path]();
}
```

---

## Feeds (RSS and JSON)

The blog provides RSS and JSON feeds for subscribers and feed readers.

### RSS Feed

**URL:** `/rss`

RSS 2.0 compliant feed with:
- Post title, link, description (summary or body excerpt)
- Publication date
- Category tags
- Author name

**Parameters:**
- `?limit=N` — Number of items (default: all published posts)

**Usage:**
```xml
<!-- Example RSS feed item -->
<item>
  <title>My Blog Post</title>
  <link>https://blog.example.com/post/my-blog-post</link>
  <description>Summary of the post...</description>
  <pubDate>Wed, 29 Apr 2026 12:00:00 GMT</pubDate>
  <guid isPermaLink="true">/s/abc123</guid>
</item>
```

### JSON Feed

**URL:** `/json`

JSON Feed 1.1 compliant feed with:
- Title, description, URL
- Post items with `content_html` (full rendered content)
- Author information
- Tags as categories

**Parameters:**
- `?limit=N` — Number of items (default: all published posts)

**Usage:**
```json
{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "DevLog",
  "items": [
    {
      "id": "/s/abc123",
      "url": "/post/my-blog-post",
      "title": "My Blog Post",
      "content_html": "<p>Full rendered content...</p>",
      "date_published": "2026-04-29T12:00:00Z",
      "tags": ["python", "flask"]
    }
  ]
}
```

### Feed Discovery

Add feed links to your `<head>` for automatic feed reader detection:

```html
<link rel="alternate" type="application/rss+xml" title="RSS Feed" href="/rss">
<link rel="alternate" type="application/json" title="JSON Feed" href="/json">
```

### Conditional GET (ETag Support)

Both feeds support conditional GET:
- Request with `If-None-Match` header
- Returns `304 Not Modified` if feed hasn't changed
- Reduces bandwidth for frequent feed readers

### Cache-Control Headers

Feeds include cache headers to control caching:
- `Cache-Control: private, max-age=300` (5 minutes)
- Varies on `Accept-Encoding` for compression

### Feed Validation

Validate your feeds at:
- RSS: https://validator.w3.org/feed/
- JSON: https://jsonfeed.org/validator/

---

## Newsletter Management

### How Newsletter Works

1. You publish a post with `newsletter_sent_at = NULL`
2. You click **Send Newsletter** in the admin
3. The scheduler sends emails to all **confirmed** subscribers
4. Each subscriber gets an email with:
   - Post title and summary
   - Link to full post
   - One-click unsubscribe link

### Configuring Newsletter

Edit `config.toml`:

```toml
[newsletter]
send_time = "08:00"              # HH:MM (24h) - time to send daily digest
confirmation_expiry_hours = 48   # Hours until confirmation link expires
max_retry_attempts = 5           # Retry attempts on failure
```

Edit SMTP settings:

```toml
[email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = "your-email@gmail.com"
smtp_password = "your-app-password"  # Use App Password for Gmail
from_address = "blog@example.com"
smtp_timeout = 30
```

Or set via environment variables: `SMTP_USER`, `SMTP_PASSWORD`.

### Sending a Newsletter

1. Publish your post
2. Go to `/admin/subscribers`
3. Click **Send Newsletter**
4. Confirm the action

The newsletter sends asynchronously. Check `logs/blog.log` for progress.

### Subscriber Confirmation Flow

1. Visitor subscribes at `/subscribe`
2. Receives confirmation email with link
3. Clicks link → `/confirm/<token>`
4. Email marked as **Confirmed**

Unconfirmed subscribers don't receive newsletters.

### Resending Confirmation Emails

1. Go to `/admin/subscribers`
2. Select unconfirmed subscribers
3. Choose **Resend Confirmation** from bulk actions
4. Click **Apply**

### Unsubscribe Flow

Every newsletter email includes:
```
To unsubscribe, click here: /unsubscribe/<subscriber-token>
```

Clicking the link:
- Marks subscriber as unsubscribed
- Shows success message (same message for valid/invalid tokens—prevents enumeration)

### Newsletter Templates

The newsletter email template is in `app/templates/email/newsletter.html`. Customize by editing this file.

---

## Admin Tasks

### Dashboard

The dashboard at `/admin/` shows:

- **Traffic Chart** — Page views over the last 30 days
- **Top Shares** — Most-shared posts this week
- **Trending** — Posts with most views this week
- **Recent Posts** — Latest published posts
- **Stats** — Total views, posts, shares, subscribers

### Backup and Restore

1. Go to `/admin/backup`
2. Click **Create Backup**
3. Optionally enable compression
4. Optionally enable encryption (requires `BACKUP_ENCRYPTION_KEY` env var)
5. Backups appear in the list below

**To restore:**
1. Find your backup in the list
2. Click **Restore**
3. Confirm the action

**Warning:** Restoring overwrites all current data.

**Backup location:** `instance/backups/`

**Backup encryption:**
```bash
export BACKUP_ENCRYPTION_KEY="your-secure-passphrase"
```

Encrypted backups use AES-256-GCM encryption with PBKDF2 key derivation.

### Database Integrity Check

1. Go to `/admin/backup`
2. Click **Check Integrity**

Or run via CLI:
```bash
flask check-integrity
```

### Static Pages

Create static pages (accessible at `/page/<slug>`):

1. Go to `/admin/pages`
2. Click **New Page**
3. Enter:
   - **Title** — Page title
   - **Slug** — URL slug (auto-generated if empty)
   - **Content** — Markdown content
4. Toggle **Published** as needed
5. Click **Save**

**Built-in pages:**
- `/about` — Created automatically if a page with slug "about" exists

### Settings

Navigate to `/admin/settings` for:

| Setting | Description |
|---------|-------------|
| Theme Preset | Visual theme (GitHub Dark, GitHub Light, Solarized Dark, Monokai) |
| Logo Text | Text to display as logo (uses site title if empty) |
| Logo Type | Image logo or text logo |
| Custom CSS | Additional CSS (sanitized before saving) |
| Footer HTML | HTML to show in footer |

**CSS Custom Properties:**
```css
:root {
    --bg: #0d1117;
    --bg-surface: #161b22;
    --text: #c9d1d9;
    --text-muted: #8b949e;
    --accent: #58a6ff;
    --accent-hover: #79c0ff;
    --border: #30363d;
}
```

### API Key Management

The REST API uses API key authentication. Set via environment variable:
```bash
export API_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

Use as `X-API-Key` header in requests. See `docs/openapi.yaml` for API documentation.

### CLI Commands

```bash
# Export all data
flask export-data data.json

# Import data
flask import-data data.json

# Rebuild search index
flask rebuild-search

# Clean unused images
flask cleanup-orphaned-images

# Check database integrity
flask check-integrity

# Create admin user
flask create-admin username

# Promote to admin
flask promote-admin username

# Generate sample data
flask seed

# Shell access
flask shell
```

---

## Analytics

### Page Views

The blog tracks page views for each published post.

**How it works:**
- When a post is viewed, `PageViewBuffer.record_page_view()` is called
- By default, views are recorded directly to the database
- For high-traffic sites, enable the **Page View Buffer** (see below)

**Viewing analytics:**
1. Go to `/admin/analytics`
2. See charts for:
   - Page views over time (last 30 days)
   - Top posts by views
   - Traffic sources (referrers)

**Manual view recording:**
```python
from app.page_view_buffer import record_page_view
record_page_view(post_id=1, referrer="https://twitter.com/")
```

### Share Events

When a visitor shares a post via the share buttons, a `ShareEvent` is recorded.

**Share platforms:**
- `twitter` — Twitter/X
- `facebook` — Facebook
- `linkedin` — LinkedIn
- `hackernews` — Hacker News
- `reddit` — Reddit
- `copy` — Copy link

**Viewing share data:**
Top shares appear on the dashboard at `/admin/`.

### Interpreting Analytics

#### Traffic Sources
Traffic sources are captured from the `referrer` header of page views:
- **Direct**: No referrer (user typed URL or used bookmark)
- **Search Engines**: Google, Bing, DuckDuckGo (referrer contains `google.com`, `bing.com`, etc.)
- **Social**: Twitter/X, Facebook, LinkedIn, Reddit, Hacker News (referrer matches share platforms)
- **Other**: All other referrers

Use traffic sources to identify which channels drive the most engagement.

#### Share Events
- **Count**: Total shares per platform
- **Trend**: Compare week-over-week share counts
- **Top Shared Posts**: Appear on the dashboard, indicating popular content worth promoting

High share counts correlate with increased traffic from social channels.

### Analytics API

```bash
# Get posts with view counts
GET /api/posts?sort=views

# View counts included in post response
```

---

## User Management

### User Roles

| Role | Description |
|------|-------------|
| User | Can view dashboard stats only |
| Admin | Full access to admin panel |
| Owner | Admin + can manage other admins |

Only owners can promote/demote users and transfer ownership.

### Creating Users

**Via CLI:**
```bash
flask create-admin username
```
Prompts for password.

**Via Admin Panel:**
1. Go to `/admin/users`
2. Click **Add User**
3. Enter username and password

### Password Requirements

- Minimum 8 characters
- At least 3 of: uppercase, lowercase, digits, special characters

### Promoting/Demoting Admins

1. Go to `/admin/users`
2. Find the user
3. Click **Promote** to make admin, or **Demote** to remove admin

**Note:** You cannot demote yourself if you're the only admin.

### Transferring Ownership

1. Go to `/admin/users`
2. Find the new owner
3. Click **Make Owner**

This demotes all other admins and promotes the selected user to owner.

### Password Reset

1. Go to `/admin/forgot-password`
2. Enter your username
3. Check email for reset link (valid 1 hour)
4. Click link → `/admin/reset/<token>`
5. Enter new password

**Security:** Invalid tokens show success (prevents enumeration). Tokens are hashed with SHA-256 before storage.

### Session Management

View active sessions at `/admin/sessions`:

- Shows username, IP address, user agent, last activity
- Current session highlighted
- Click **Revoke** to force logout

Sessions auto-expire after 24 hours of inactivity (configurable via `SESSION_LIFETIME_HOURS`).

**IP Binding:** If your IP changes, a warning is logged. The session isn't invalidated (allows for mobile users switching networks).

---

## Media Library

### Accessing Media Library

Go to `/admin/media`

### Uploading Images

1. Click **Upload** button
2. Select file (JPEG, PNG, GIF, WebP, SVG)
3. Wait for upload to complete

**Limits:**
- Max file size: 16 MB
- Allowed types: image/jpeg, image/png, image/gif, image/webp, image/svg+xml

### Responsive Images

On upload, images are automatically resized to create variants:
- 400w, 800w, 1200w widths
- WebP format when supported

Templates use `srcset` for responsive loading:
```html
<img src="/static/uploads/image.jpg"
     srcset="/static/uploads/400w/image.jpg 400w,
             /static/uploads/800w/image.jpg 800w,
             /static/uploads/1200w/image.jpg 1200w"
     sizes="(max-width: 600px) 400px, (max-width: 1200px) 800px, 1200px">
```

### Using Images in Posts

1. Copy the image URL from the media library
2. In your post, use Markdown:
   ```markdown
   ![Alt text](/static/uploads/filename.png)
   ```

Or drag and drop directly into the post editor.

### Deleting Images

1. Go to `/admin/media`
2. Click on the image
3. Click **Delete**
4. Confirm

**Warning:** Deleted images are permanently removed. If an image is in use by a post, the post will show a broken image.

### Image Storage

**Local storage (default):**
Images are stored in `app/static/uploads/`. This directory should be included in backups.

**S3 storage:**
Images are stored in S3-compatible storage. See [S3 Storage](#s3-storage) section.

### Cleaning unused images

```bash
flask cleanup-orphaned-images
```

This removes images not referenced by any post.

### How Image Uploads Work

1. File uploaded to storage
2. Magic bytes detected to verify file type
3. Extension set based on detected type (not user-provided)
4. Filename: `YYYYMMDD_HHMMSS_<random>.<ext>`

---

## S3 Storage

The blog supports storing media files in S3-compatible storage instead of local filesystem.

### Configuration

Set environment variables:

```bash
export STORAGE_BACKEND=s3
export S3_BUCKET=my-blog-uploads
export S3_REGION=us-east-1
export S3_ACCESS_KEY=AKIA...
export S3_SECRET_KEY=...
```

**Optional:**
```bash
export S3_ENDPOINT=https://s3.amazonaws.com    # For S3-compatible services
export S3_PUBLIC_URL=https://cdn.example.com      # Custom CDN URL
```

### Supported S3-Compatible Services

- Amazon S3
- Cloudflare R2
- MinIO
- Wasabi
- Any S3-compatible API

### How S3 Storage Works

1. Image uploaded via admin panel
2. Saved to temp directory locally
3. Responsive variants generated
4. All variants uploaded to S3
5. Local temp files deleted

**Reading images:**
- The `post_image_url` filter uses `storage.url()` to generate URLs
- For private buckets, signed URLs are generated

### Storage Backend Detection

The app auto-detects storage backend from `STORAGE_BACKEND`:
- `local` (default) — Local filesystem
- `s3` — S3-compatible storage

### Local Storage Fallback

If S3 is unavailable, the app falls back to local storage at `app/static/uploads/`.

### Migration from Local to S3

1. Configure S3 environment variables
2. Restart the app
3. New uploads go to S3
4. Existing local uploads remain in place

---

## Page View Buffer

For high-traffic sites, page views can be buffered and batch-written to reduce database load.

### Enabling the Buffer

```bash
# Enable buffer (flush when buffer reaches 100 views)
export PAGE_VIEW_BUFFER_SIZE=100

# Flush interval in seconds (default: 5)
export PAGE_VIEW_FLUSH_INTERVAL=10
```

Set `PAGE_VIEW_BUFFER_SIZE=0` to disable buffering (default behavior).

### How It Works

1. Visitor views a post
2. `record_page_view()` adds to buffer (thread-safe)
3. Background thread flushes buffer when:
   - Buffer reaches `PAGE_VIEW_BUFFER_SIZE`, OR
   - `PAGE_VIEW_FLUSH_INTERVAL` seconds elapsed since last flush
4. All buffered views written in single batch insert

### Benefits

- Reduces database writes for high-traffic sites
- Thread-safe (works with multiple workers)
- Graceful shutdown (flushes remaining buffer)

### Monitoring

Check logs for buffer activity:
```
PageViewBuffer: flushed 100 views to database
PageViewBuffer: shutdown - flushed 23 remaining views
```

### Manual Flush

```python
from app.page_view_buffer import shutdown_page_view_buffer
shutdown_page_view_buffer()  # Flushes and stops background thread
```

### Integration with Analytics

The analytics system (page views, share events) works identically with or without buffering. No code changes required.

---

## Search

### Using Search

1. Use the search bar in the header
2. Results show as you type (debounced)
3. Use arrow keys to navigate, Enter to select, Escape to close

### Search Features

- **Full-text search** via SQLite FTS5
- **Prefix matching** — searching "Py" matches "Python"
- **Did you mean?** — suggestions for typos
- **Highlighted matches** — search terms highlighted in results

### Rebuilding the Search Index

If search results seem wrong:

```bash
flask rebuild-search
```

This recreates the FTS5 table and reindexes all posts.

### Search API

```bash
# Get search suggestions
GET /api/posts?q=search+term

# Search with pagination
GET /api/posts?q=search+term&page=1&per_page=20
```

### FTS5 Limitations

- FTS5 is SQLite-specific (PostgreSQL migration requires different search implementation)
- Prefix search limited to 2-4 character prefixes
- Very long documents may not be fully indexed

---

## Short URLs

Each post has a short URL at `/s/<code>` where `<code>` is a base62-encoded post ID.

**Examples:**
- Post ID 1 → `/s/1`
- Post ID 100 → `/s/1K`
- Post ID 1000 → `/s/S0`

**Benefits:**
- Never changes (even if slug changes)
- Short for sharing on Twitter
- Always works regardless of slug

Find the short URL in the post edit page.

**Encoding:**
```python
from app.base62 import encode
code = encode(post_id)  # e.g., 1000 -> "S0"
```

**Decoding:**
```python
from app.base62 import decode
post_id = decode(code)  # e.g., "S0" -> 1000
```
