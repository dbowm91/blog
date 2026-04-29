# User Guide

Detailed documentation for blog administration and content management.

## Contents

- [Post Writing Guide](#post-writing-guide)
- [Newsletter Management](#newsletter-management)
- [Admin Tasks](#admin-tasks)
- [User Management](#user-management)
- [Media Library](#media-library)

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

1. Go to `/admin/posts`
2. Find your post and click **Edit**
3. Make changes
4. Click **Update** to save changes

**Note:** If you see an "IntegrityError" message, a slug collision occurred. The system will auto-generate a new unique slug.

### Post Revisions

Every time you publish a post, a revision is saved:

1. While editing, click **Revisions** tab
2. View previous versions with author and timestamp
3. Click a revision to preview it
4. Click **Restore** to revert to that version

### Bulk Operations

From `/admin/posts`:

1. Check the box next to each post you want to modify
2. Select a bulk action from the dropdown:
   - **Publish** — Publish selected drafts
   - **Unpublish** — Take selected posts offline
   - **Delete** — Permanently remove (with confirmation)
3. Click **Apply**

### Scheduled Publishing

To schedule a post for future publication:

1. While creating/editing a post, find **Publish At** field
2. Select a future date and time
3. Click **Save Draft** (not Publish)

The scheduler checks every 5 minutes for posts with `scheduled_publish_at` in the past. When triggered, the post is automatically published and the scheduled time is cleared.

**Status indicators on `/admin/posts`:**
- Clock icon = Scheduled
- Green dot = Published
- Gray dot = Draft

### Short URLs

Each post gets a short URL: `/s/<code>` where `<code>` is a base62-encoded post ID.

- Find the short URL in the post edit page
- Useful for sharing on Twitter/character-limited platforms
- Short codes never change, even if the slug does

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
4. Backups appear in the list below

**To restore:**
1. Find your backup in the list
2. Click **Restore**
3. Confirm the action

**Warning:** Restoring overwrites all current data.

**Backup location:** `instance/backups/` (included in off-site backup scripts)

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
    --bg: #0d1117;          /* page background */
    --bg-surface: #161b22;   /* card/surface background */
    --text: #c9d1d9;         /* primary text */
    --text-muted: #8b949e;   /* secondary text */
    --accent: #58a6ff;       /* links, buttons */
    --accent-hover: #79c0ff; /* hover state */
    --border: #30363d;       /* borders */
}
```

### API Key Management

The REST API uses API key authentication. Set via environment variable:
```bash
export API_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

See `docs/openapi.yaml` for API documentation.

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

Images are stored in `app/static/uploads/`. This directory should be included in backups.

**Cleaning unused images:**
```bash
flask cleanup-orphaned-images
```

This removes images not referenced by any post.

### How Image Uploads Work

1. File uploaded to `app/static/uploads/`
2. Magic bytes detected to verify file type
3. Extension set based on detected type (not user-provided)
4. Filename: `YYYYMMDD_HHMMSS_<random>.ext`

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
