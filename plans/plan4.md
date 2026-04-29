# Performance Improvement Plan (Plan 4)

**Date**: 2026-04-28  
**Status**: Draft - Pending Review  
**Scope**: Comprehensive performance optimization for Flask Blog CMS

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Investigation Results](#investigation-results)
3. [Phase 1: Security & Critical Fixes](#phase-1-security--critical-fixes)
4. [Phase 2: Frontend Performance](#phase-2-frontend-performance)
5. [Phase 3: Reliability Improvements](#phase-3-reliability-improvements)
6. [Phase 4: Scale Preparation](#phase-4-scale-preparation)
7. [Implementation Timeline](#implementation-timeline)
8. [Testing Strategy](#testing-strategy)

---

## Executive Summary

Following a comprehensive performance review of the Flask Blog CMS codebase, we identified **18 items** for investigation across database, frontend, and backend domains. Investigation revealed:

| Category | Critical Issues | Medium Issues | Non-Issues | Status |
|----------|------------------|---------------|--------------|--------|
| **Database** | 0 | 2 | 3 | ✅ Complete |
| **Frontend** | 3 | 1 | 0 | ✅ Complete |
| **Backend** | 3 | 3 | 0 | ✅ Complete |

**Key Finding**: 3 investigated items turned out to be **non-issues** in the current codebase:
- N+1 relationships are already properly handled via subqueries/joinedload
- Analytics queries don't need eager loading (tags aren't displayed)
- `get_indexed_terms()` is only called on zero-result searches

### Priority Breakdown

| Priority | Count | Items |
|----------|-------|-------|
| **HIGH** | 6 | Rate limiting, Server-side sessions, Scheduler persistence, Render-blocking CSS, Prism.js loading, Responsive images |
| **MEDIUM** | 6 | PostRevision index, Page view buffering, FTS5 vocabulary, Connection pooling, Shared cache, Email batching |

---

## Investigation Results

### Database Findings

#### ✅ Non-Issues (No Action Needed)

1. **N+1 Query Risks (models.py:122,125,128)**
   - **Finding**: Codebase already uses efficient patterns
   - `page_views`/`share_events`: Uses subqueries to batch-count (posts.py:70-95)
   - `revisions`: Queries PostRevision directly, not via relationship
   - `tags`: Properly uses `joinedload(Post.tags)` in all list queries
   - **Action**: None needed

2. **Missing Eager Loading in Analytics (analytics.py:66-70, dashboard.py:100-108)**
   - **Finding**: Tags are NOT displayed in analytics/dashboard templates
   - `analytics.html` only shows `post.title`, `post.id`
   - `dashboard.html` trending/top-shares only show title/id
   - **Action**: None needed unless templates change

3. **get_indexed_terms() Performance (search.py:210-228)**
   - **Finding**: Only called on zero-result searches (not on every search)
   - Current implementation works but could be optimized with FTS5 vocabulary
   - **Action**: Medium priority enhancement (Phase 3)

#### 🟡 Medium Priority

4. **Missing Index on PostRevision.author_id (models.py:160)**
   - **Issue**: Foreign key has no index; JOIN operations suboptimal
   - **Impact**: Low-medium (queries filter by post_id first)
   - **Fix**: Add migration for `ix_post_revisions_author_id`
   - **Files**: `app/models.py`, `migrations/versions/`

5. **Page View Frequent Writes (public.py:256-264)**
   - **Issue**: Every page view = INSERT + commit (synchronous)
   - **Impact**: Write serialization in SQLite, user request blocking
   - **Fix**: Buffer writes + batch flush (pageview_buffer.py)
   - **Files**: New `app/pageview_buffer.py`, `app/models.py` (add view_count)

---

### Frontend Findings

#### 🔴 High Priority

6. **Render-Blocking CSS (base.html:23-24, admin/base.html:9-10)**
   - **Issue**: 79KB `style.css` blocks First Contentful Paint
   - **Impact**: 200-500ms delay on slow connections
   - **Fix**: Inline critical CSS (~5-7KB) + async load remainder
   - **Files**: `app/templates/base.html`, `app/templates/admin/base.html`

7. **Prism.js Loaded on All Pages (base.html:130-132)**
   - **Issue**: 43KB loaded unnecessarily on 80% of pages
   - **Impact**: Wasted bandwidth, especially mobile
   - **Fix**: Conditional loading based on code block detection
   - **Files**: `app/templates/base.html`, `app/static/js/main.js`

8. **No Responsive Images/srcset (All Templates)**
   - **Issue**: Mobile users download desktop-sized images
   - **Impact**: Bandwidth waste, poor mobile experience
   - **Fix**: Pillow image resizing on upload + srcset attribute
   - **Files**: `app/routes/admin/helpers/images.py`, templates, new CLI command

#### 🟡 Medium Priority

9. **Login Page Blocks Rendering (login_base.html:52-53)**
   - **Issue**: Prism.js loaded WITHOUT `defer` attribute
   - **Impact**: Login page render blocking
   - **Fix**: Add `defer` or remove Prism from login page
   - **Files**: `app/templates/admin/login_base.html`

---

### Backend Findings

#### 🔴 High Priority

10. **No Application-Level Rate Limiting (api.py, admin routes)**
    - **Issue**: Relies solely on reverse proxy (nginx)
    - **Impact**: Vulnerable to brute-force, DDoS if proxy bypassed
    - **Fix**: Implement Flask-Limiter with Redis fallback
    - **Files**: `app/__init__.py`, `app/routes/api.py`, `app/routes/admin/auth.py`

11. **Cookie-Based Sessions (app/__init__.py:138-142)**
    - **Issue**: ~1KB session data visible to client, no server-side invalidation
    - **Impact**: Security risk, 4KB cookie limit, no multi-server support
    - **Fix**: Migrate to Flask-Session with Redis
    - **Files**: `app/__init__.py`, `app/config.py`, `config.toml`

12. **In-Process Scheduler No Persistence (scheduler.py:301)**
    - **Issue**: `BackgroundScheduler(daemon=True)` - all job state lost on restart
    - **Impact**: Missed newsletters, scheduled posts during downtime
    - **Fix**: Add ScheduledJobExecution model + recovery detection
    - **Files**: `app/models.py`, `app/scheduler.py`, `migrations/versions/`

#### 🟡 Medium Priority

13. **No Connection Pool Tuning (app/__init__.py:131-136)**
    - **Issue**: No `SQLALCHEMY_ENGINE_OPTIONS` configured
    - **Impact**: Only affects PostgreSQL migration (SQLite doesn't need pooling)
    - **Fix**: Add pool settings conditional on PostgreSQL URI
    - **Files**: `app/__init__.py`

14. **No Shared Cache Between Workers (cache.py)**
    - **Issue**: Each worker has own in-memory cache (2 workers = 2 caches)
    - **Impact**: 60s inconsistency window for tag counts
    - **Fix**: For 2 workers, acceptable. For 3+ workers, add Flask-Caching with Redis
    - **Files**: `app/cache.py`, `app/extensions.py` (optional)

15. **Email No Pipelining (email.py:181-194)**
    - **Issue**: MIME objects created per subscriber (not connection overhead)
    - **Impact**: Moderate for <1000 subscribers
    - **Fix**: Add RSET-based batching (already has pre-rendered templates)
    - **Files**: `app/email.py`

---

## Phase 1: Security & Critical Fixes

**Goal**: Address security vulnerabilities and critical performance issues  
**Timeline**: Week 1-2  
**Dependencies**: Redis server (for rate limiting + sessions)

### 1.1 Application-Level Rate Limiting

**Priority**: 🔴 HIGH  
**Estimated Effort**: 4-6 hours

#### Background
The codebase intentionally omits application-level rate limiting (see DEPLOY.md lines 610-612), deferring to reverse proxies. However, this creates a single point of failure if the proxy is bypassed.

#### Changes Required

**A. Install Dependencies**
```bash
pip install flask-limiter>=4.1.1,<5.0
```

**B. Update `app/__init__.py` (Add after line 136)**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import current_user

def create_app():
    # ... existing code until line 136 ...
    
    # --- Rate Limiting Setup ---
    def rate_limit_key():
        """Dynamic key: IP, user ID, or API key based on context."""
        if request.blueprint == "admin":
            if current_user.is_authenticated:
                return f"admin_user:{current_user.id}"
            return f"admin_ip:{request.remote_addr}"
        elif request.blueprint == "api":
            api_key = request.headers.get("X-API-Key", "")
            if api_key:
                return f"api_key:{api_key}"
            return f"api_ip:{request.remote_addr}"
        return f"public_ip:{request.remote_addr}"
    
    def handle_rate_limit_breach(request, limit_info):
        """Return 429 with JSON for API, HTML for others."""
        retry_after = limit_info.breach_value
        if (request.blueprint == "api" or 
            request.headers.get("Accept") == "application/json" or
            request.path.startswith("/api")):
            return jsonify({
                "error": "Rate limit exceeded",
                "retry_after": retry_after
            }), 429
        flash("Too many requests. Please wait.", "error")
        return redirect(request.referrer or "/"), 429
    
    storage_uri = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    
    limiter = Limiter(
        app=app,
        key_func=rate_limit_key,
        storage_uri=storage_uri,
        strategy="fixed-window",
        default_limits=["100 per minute"],
        on_breach=handle_rate_limit_breach,
        headers_enabled=True
    )
    app.limiter = limiter
    
    # Per-blueprint limits (matches DEPLOY.md nginx suggestions)
    limiter.limit("20 per minute", blueprint="api")
    limiter.limit("20 per minute", blueprint="admin")
```

**C. Update `app/routes/admin/auth.py`**
```python
from app import limiter  # Import from app/__init__.py

@admin.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])  # Brute-force protection
def login():
    # Remove existing time.sleep(0.05) - rate limiter handles delays
    # ... rest of login logic
```

**D. Update `app/routes/api.py`**
```python
from app import limiter

@api.route("/posts", methods=["GET", "POST"])
@require_api_key
@limiter.limit("30 per minute", methods=["GET"])
@limiter.limit("10 per minute", methods=["POST"])
def posts():
    # ... existing logic
```

**E. Environment Variables (`.env`)**
```bash
RATELIMIT_STORAGE_URI=redis://localhost:6379/0  # Production
# RATELIMIT_STORAGE_URI=memory://  # Development
```

#### Testing
```bash
# Test rate limiting
for i in {1..6}; do curl -X POST http://localhost:5000/admin/login; done
# Should see 429 on 6th request

# Test API rate limit
for i in {1..21}; do curl -H "X-API-Key: test" http://localhost:5000/api/posts; done
```

---

### 1.2 Server-Side Sessions with Redis

**Priority**: 🔴 HIGH  
**Estimated Effort**: 6-8 hours

#### Background
Current cookie-based sessions store ~1KB data (viewed_posts, CSRF tokens, admin_session_id) visible to client. No server-side invalidation possible.

#### Changes Required

**A. Install Dependencies**
```bash
pip install flask-session>=0.8.0,<1.0 redis>=5.0.0,<6.0
```

**B. Update `app/config.py` (Add to `__all__` and config)**
```python
__all__ = [
    # ... existing ...
    "SESSION_TYPE",
    "SESSION_REDIS_HOST",
    "SESSION_REDIS_PORT",
    "SESSION_REDIS_DB",
    "SESSION_KEY_PREFIX",
    "SESSION_PERMANENT",
    "PERMANENT_SESSION_LIFETIME",
    "SESSION_SERIALIZATION_FORMAT",
]

# Session config (add near line 76)
SESSION_TYPE = _env("SESSION_TYPE", "redis")
SESSION_REDIS_HOST = _env("SESSION_REDIS_HOST", "localhost")
SESSION_REDIS_PORT = int(_env("SESSION_REDIS_PORT", "6379"))
SESSION_REDIS_DB = int(_env("SESSION_REDIS_DB", "0"))
SESSION_REDIS_PASSWORD = _env("SESSION_REDIS_PASSWORD", None)
SESSION_KEY_PREFIX = _env("SESSION_KEY_PREFIX", "blog_session:")
SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = int(_env("PERMANENT_SESSION_LIFETIME", 
                                     str(SESSION_LIFETIME_HOURS * 3600)))
SESSION_SERIALIZATION_FORMAT = _env("SESSION_SERIALIZATION_FORMAT", "msgpack")
```

**C. Update `app/__init__.py` (Replace lines 138-142)**
```python
from flask_session import Session
import redis

def create_app():
    # ... existing config ...
    
    # Session configuration
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
        "SESSION_COOKIE_SECURE", "true"
    ).lower() in ("true", "1", "yes")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    
    # Flask-Session (server-side)
    app.config["SESSION_TYPE"] = "redis"
    redis_client = redis.Redis(
        host=app.config.get("SESSION_REDIS_HOST", "localhost"),
        port=app.config.get("SESSION_REDIS_PORT", 6379),
        db=app.config.get("SESSION_REDIS_DB", 0),
        password=app.config.get("SESSION_REDIS_PASSWORD"),
        decode_responses=False  # Flask-Session expects bytes
    )
    app.config["SESSION_REDIS"] = redis_client
    app.config["SESSION_KEY_PREFIX"] = app.config.get("SESSION_KEY_PREFIX", "blog_session:")
    app.config["SESSION_PERMANENT"] = app.config.get("SESSION_PERMANENT", True)
    app.config["PERMANENT_SESSION_LIFETIME"] = app.config.get("PERMANENT_SESSION_LIFETIME")
    app.config["SESSION_SERIALIZATION_FORMAT"] = app.config.get("SESSION_SERIALIZATION_FORMAT", "msgpack")
    
    Session(app)
```

**D. Update `config.toml` (Add new section)**
```toml
[session]
type = "redis"
redis_host = "localhost"
redis_port = 6379
redis_db = 0
# redis_password = ""  # Uncomment if needed
key_prefix = "blog_session:"
permanent = true
permanent_session_lifetime = 86400  # 24 hours
serialization_format = "msgpack"
```

**E. Migration Strategy**
- Deploy Flask-Session
- Old cookie sessions will be ignored (different format)
- Users must log in again (one-time inconvenience)
- New sessions stored server-side in Redis

#### Testing
```bash
# Verify Redis sessions working
redis-cli
> KEYS blog_session:*
> GET blog_session:<session-id>

# Verify session invalidation works
# Login, then from Redis: DEL blog_session:<session-id>
# Try to access admin page - should redirect to login
```

---

### 1.3 Fix Login Page Rendering

**Priority**: 🔴 HIGH  
**Estimated Effort**: 15 minutes

#### Changes Required

**File**: `app/templates/admin/login_base.html` (lines 52-53)

```html
<!-- BEFORE -->
<script src="{{ url_for('static', filename='js/prism.min.js') }}"></script>
<script src="{{ url_for('static', filename='js/prism-languages.js') }}"></script>

<!-- AFTER (add defer, or better yet, remove entirely since login doesn't need Prism) -->
<!-- REMOVE these lines entirely - login page has no code blocks -->
```

---

## Phase 2: Frontend Performance

**Goal**: Improve Core Web Vitals (FCP, LCP, CLS)  
**Timeline**: Week 2-3  
**Dependencies**: None

### 2.1 Critical CSS Inlining + Async Loading

**Priority**: 🔴 HIGH  
**Estimated Effort**: 4-6 hours

#### Background
79KB `style.css` blocks rendering. Critical CSS (~5-7KB for navbar, hero, first post card) should be inlined.

#### Changes Required

**A. Run Existing Minification**
```bash
python scripts/build_assets.py  # Creates style.min.css
```

**B. Update `app/templates/base.html` (lines 23-38)**
```html
<head>
    <!-- ... meta tags ... -->
    
    <!-- 1. Inline Critical CSS (navbar, hero, first post card) -->
    <style nonce="{{ csp_nonce }}">
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #0d1117; --bg-surface: #161b22; --border: #30363d;
            --text: #e6edf3; --text-muted: #8b949e; --accent: #58a6ff;
            --accent-hover: #79c0ff; --radius-lg: 12px;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
            --space-lg: 24px;
        }
        body { font-family: var(--font-sans); background: var(--bg); color: var(--text); }
        .container { width: 100%; max-width: 1100px; margin: 0 auto; padding: 0 24px; }
        .navbar {
            position: sticky; top: 0; z-index: 100;
            background: rgba(13, 17, 23, 0.85); backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px); border-bottom: 1px solid var(--border);
            padding: 16px 0;
        }
        .nav-container { display: flex; align-items: center; justify-content: space-between; }
        .nav-logo { font-family: var(--font-mono); font-size: 1.1rem; font-weight: 500; color: var(--text); }
        .nav-links { display: flex; gap: var(--space-lg); align-items: center; }
        .hero { padding: 64px 0 40px; text-align: center; }
        .hero-title {
            font-family: var(--font-mono); font-size: 2.5rem; font-weight: 700;
            letter-spacing: -0.03em; margin-bottom: 12px;
            background: linear-gradient(135deg, var(--accent), var(--accent-hover));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }
        .post-card {
            background: var(--bg-surface); border: 1px solid var(--border);
            border-radius: var(--radius-lg); overflow: hidden;
        }
        .post-card-body { padding: 20px; }
        .post-card-title { font-size: 1.25rem; font-weight: 600; margin-bottom: 8px; }
    </style>
    
    <!-- 2. Async load full CSS (print swap pattern) -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.min.css') }}"
          media="print" onload="this.media='all'">
    <noscript>
        <link rel="stylesheet" href="{{ url_for('static', filename='css/style.min.css') }}">
    </noscript>
    
    <!-- 3. Theme variables (keep as-is) -->
    <style nonce="{{ csp_nonce }}">
        :root {
            {% for key, value in theme_vars.items() %}
            {% if key != 'name' %}--{{ key }}: {{ value }};{% endif %}
            {% endfor %}
        }
        {% if custom_css_enabled and custom_css %}
        {{ custom_css | sanitize_css | safe }}
        {% endif %}
    </style>
    
    <!-- 4. Font preload (already exists, add fetchpriority) -->
    <link rel="preload" href="{{ url_for('static', filename='fonts/inter-400-latin.woff2') }}" 
          as="font" type="font/woff2" crossorigin fetchpriority="high">
    <link rel="preload" href="{{ url_for('static', filename='fonts/jetbrains-mono-400-latin.woff2') }}" 
          as="font" type="font/woff2" crossorigin fetchpriority="high">
</head>
```

**C. Update `app/templates/admin/base.html` similarly** (use admin-critical CSS)

---

### 2.2 Conditional Prism.js Loading

**Priority**: 🔴 HIGH  
**Estimated Effort**: 2-3 hours

#### Changes Required

**A. Update `app/static/js/main.js` (Add after line 65)**
```javascript
// Conditional Prism.js loading
function loadPrismIfNeeded() {
    if (document.querySelector('pre[class*="language-"]')) {
        const loadScript = (src) => {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = `/static/js/${src}`;
                script.defer = true;
                script.onload = resolve;
                script.onerror = reject;
                document.body.appendChild(script);
            });
        };
        
        Promise.all([
            loadScript('prism.min.js'),
            loadScript('prism-languages.js')
        ]).then(() => {
            if (window.Prism) Prism.highlightAll();
        }).catch(err => console.error('Failed to load Prism:', err));
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const modules = getModulesForPath(window.location.pathname);
    modules.forEach(m => loadModule(m, fn => fn()));
    
    // Load Prism conditionally
    loadPrismIfNeeded();
});
```

**B. Remove Prism from `app/templates/base.html`** (lines 130-132)
```html
<!-- REMOVE these lines, Prism is now loaded dynamically -->
<!-- <script defer src="{{ url_for('static', filename='js/prism.min.js') }}"></script> -->
<!-- <script defer src="{{ url_for('static', filename='js/prism-languages.js') }}"></script> -->
```

**C. Keep Prism in `app/templates/admin/base.html`** (admin editor needs it)
- But add `defer` attribute if not present

---

### 2.3 Responsive Images with srcset

**Priority**: 🔴 HIGH  
**Estimated Effort**: 8-12 hours

#### Background
Images use fixed dimensions. Mobile users download desktop-sized images. Need Pillow for server-side resizing.

#### Changes Required

**A. Install Dependencies**
```bash
pip install Pillow>=10.0.0,<11.0.0
```

**B. Update `app/routes/admin/helpers/images.py`**
```python
from PIL import Image as PILImage
from pathlib import Path

DEFAULT_IMAGE_SIZES = [400, 800, 1200, 1920]

def _generate_variants(original_path: str, sizes: list[int] = None) -> list[str]:
    """Generate resized image variants for responsive srcset."""
    if sizes is None:
        sizes = DEFAULT_IMAGE_SIZES
    
    variants = []
    try:
        with PILImage.open(original_path) as img:
            # Fix EXIF orientation
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif:
                    orientation = exif.get(274)
                    if orientation in {3, 6, 8}:
                        rotations = {3: 180, 6: 270, 8: 90}
                        img = img.rotate(rotations[orientation], expand=True)
            
            img_format = img.format.lower() if img.format else 'jpeg'
            if img_format == 'jpeg' and img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            base_name = Path(original_path).stem
            ext = Path(original_path).suffix.lstrip('.')
            upload_dir = Path(original_path).parent
            
            for size in sizes:
                if size >= img.width:
                    continue
                ratio = size / img.width
                height = int(img.height * ratio)
                resized = img.resize((size, height), PILImage.LANCZOS)
                
                variant_name = f"{base_name}_{size}w.{ext}"
                variant_path = upload_dir / variant_name
                if variant_path.exists():
                    variants.append(variant_name)
                    continue
                
                save_kwargs = {}
                if img_format == 'jpeg':
                    save_kwargs = {'quality': 85, 'progressive': True}
                elif img_format == 'webp':
                    save_kwargs = {'quality': 85}
                
                resized.save(variant_path, **save_kwargs)
                variants.append(variant_name)
    except Exception as e:
        current_app.logger.warning(f"Variant generation failed for {original_path}: {e}")
    return variants
```

**C. Update `_save_image()` to call `_generate_variants()`**
```python
def _save_image(file: FileStorage) -> tuple[str, None] | tuple[None, str]:
    # ... existing validation ...
    
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    original_path = os.path.join(upload_folder, filename)
    file.save(original_path)
    
    # Generate responsive variants
    image_sizes = current_app.config.get("IMAGE_SIZES", DEFAULT_IMAGE_SIZES)
    _generate_variants(original_path, image_sizes)
    
    return filename, None
```

**D. Add Jinja Filter in `app/__init__.py`**
```python
@app.template_filter("responsive_image")
def responsive_image_filter(post, context="default"):
    """Generate responsive image attributes (srcset/sizes)."""
    if not post or not post.image:
        return None
    
    if has_request_context():
        if not hasattr(g, "_responsive_image_cache"):
            g._responsive_image_cache = {}
        cache_key = f"{post.id}_{context}"
        if cache_key in g._responsive_image_cache:
            return g._responsive_image_cache[cache_key]
    
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    original_path = os.path.join(upload_folder, post.image)
    
    if not os.path.isfile(original_path):
        return None
    
    base_name = os.path.splitext(post.image)[0]
    ext = os.path.splitext(post.image)[1].lstrip('.')
    
    with PILImage.open(original_path) as img:
        original_width = img.width
    
    original_url = url_for('static', filename=f'uploads/{post.image}')
    
    srcset_parts = [f"{original_url} {original_width}w"]
    image_sizes = current_app.config.get("IMAGE_SIZES", DEFAULT_IMAGE_SIZES)
    
    for size in sorted(image_sizes):
        if size >= original_width:
            continue
        variant_filename = f"{base_name}_{size}w.{ext}"
        variant_path = os.path.join(upload_folder, variant_filename)
        if os.path.isfile(variant_path):
            variant_url = url_for('static', filename=f'uploads/{variant_filename}')
            srcset_parts.append(f"{variant_url} {size}w")
    
    sizes_map = {
        "card": "(max-width: 768px) 100vw, (max-width: 1100px) 50vw, 33vw",
        "hero": "(max-width: 768px) 100vw, 1100px",
        "related": "(max-width: 768px) 100vw, 400px",
        "default": "100vw"
    }
    
    result = {
        "src": original_url,
        "srcset": ", ".join(srcset_parts),
        "sizes": sizes_map.get(context, sizes_map["default"]),
        "width": original_width,
        "height": int(original_width * 0.5)
    }
    
    if has_request_context():
        g._responsive_image_cache[cache_key] = result
    
    return result
```

**E. Update Templates**

`app/templates/index.html` (post cards):
```jinja2
{% set resp_img = post|responsive_image("card") %}
{% if resp_img %}
    <img src="{{ resp_img.src }}" 
         srcset="{{ resp_img.srcset }}" 
         sizes="{{ resp_img.sizes }}" 
         alt="{{ post.title }}" 
         class="post-card-img img-skeleton" 
         loading="lazy" decoding="async" 
         width="{{ resp_img.width }}" 
         height="{{ resp_img.height }}">
{% endif %}
```

**F. Generate Variants for Existing Images (CLI Command)**
```python
# Add to app/cli.py
@click.command("generate-image-variants")
def generate_image_variants():
    """Generate responsive variants for existing uploaded images."""
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    image_sizes = current_app.config.get("IMAGE_SIZES", [400, 800, 1200, 1920])
    
    for img_path in upload_folder.iterdir():
        if img_path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
            continue
        if '_' in img_path.stem and img_path.stem.split('_')[-1].endswith('w'):
            continue  # Skip existing variants
        
        click.echo(f"Processing {img_path.name}...")
        _generate_variants(str(img_path), image_sizes)
    
    click.echo("Done.")
```

---

## Phase 3: Reliability Improvements

**Goal**: Add persistence, monitoring, and optimization  
**Timeline**: Week 3-4  
**Dependencies**: Redis (for session storage)

### 3.1 Scheduler Persistence with Job Logging

**Priority**: 🔴 HIGH  
**Estimated Effort**: 6-8 hours

#### Changes Required

**A. Add Model `app/models.py`**
```python
class ScheduledJobExecution(db.Model):
    """Track scheduled job executions for audit and recovery."""
    __tablename__ = "scheduled_job_executions"
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(100), nullable=False)
    job_name = db.Column(db.String(100), nullable=False)
    executed_at = db.Column(UTCDateTime, default=utc_now, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # success, failure, partial
    items_processed = db.Column(db.Integer, default=0)
    items_failed = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    execution_time_ms = db.Column(db.Integer, nullable=True)
    
    __table_args__ = (
        db.Index("ix_scheduled_job_executions_job_executed", "job_id", "executed_at"),
        db.Index("ix_scheduled_job_executions_executed_at", "executed_at"),
    )
```

**B. Create Migration**
```bash
ADMIN_PASSWORD=test SECRET_KEY=test flask db migrate -m "add_scheduled_job_executions"
ADMIN_PASSWORD=test SECRET_KEY=test flask db upgrade
```

**C. Update `app/scheduler.py`**
- Add `misfire_grace_time=3600` to all jobs
- Add `coalesce=True` (run only once if multiple missed)
- Add `_log_execution()` helper
- Call `_log_execution()` in each job function

---

### 3.2 PostRevision.author_id Index

**Priority**: 🟡 MEDIUM  
**Estimated Effort**: 1 hour

#### Changes Required

**A. Update `app/models.py` (line 165)**
```python
__table_args__ = (
    db.Index("ix_post_revisions_post_created", "post_id", "created_at"),
    db.Index("ix_post_revisions_author_id", "author_id"),  # ADD THIS
)
```

**B. Create Migration**
```bash
ADMIN_PASSWORD=test SECRET_KEY=test flask db migrate -m "add_post_revisions_author_index"
ADMIN_PASSWORD=test SECRET_KEY=test flask db upgrade
```

---

### 3.3 Optimize get_indexed_terms() with FTS5 Vocabulary

**Priority**: 🟡 MEDIUM  
**Estimated Effort**: 2 hours

#### Changes Required

**Update `app/search.py` (lines 210-228)**
```python
def get_indexed_terms() -> list[str]:
    """Get all unique terms from FTS5 index for 'Did you mean?' suggestions."""
    try:
        if not _check_fts_enabled():
            return []
        
        # Use FTS5's built-in vocabulary table
        db.session.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS temp.posts_fts_vocab "
            "USING fts5vocab('posts_fts', 'row')"
        ))
        
        result = db.session.execute(text("SELECT term FROM temp.posts_fts_vocab")).fetchall()
        terms = [row[0] for row in result if row[0]]
        
        return terms  # Already unique from FTS5 vocabulary
        
    except (OperationalError, ProgrammingError, DatabaseError):
        return []
```

---

### 3.4 Page View Buffer (Optional - High Traffic Only)

**Priority**: 🟡 MEDIUM  
**Estimated Effort**: 6-8 hours  
**Note**: Only implement if site has >1000 page views/day

#### Changes Required
- Create `app/pageview_buffer.py` with background thread
- Add `view_count` column to Post model
- Modify `app/routes/public.py` to use buffer
- Add shutdown handler in `app/__init__.py`

(See deep dive report for full implementation code)

---

## Phase 4: Scale Preparation

**Goal**: Prepare for multi-worker deployment  
**Timeline**: Week 5-6 (if needed)  
**Dependencies**: Redis server

### 4.1 Connection Pool Tuning (PostgreSQL Migration)

**Priority**: 🟡 MEDIUM  
**Estimated Effort**: 1 hour  
**Note**: Only needed when migrating from SQLite to PostgreSQL

#### Changes Required

**Update `app/__init__.py` (after line 136)**
```python
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }
```

---

### 4.2 Shared Cache with Flask-Caching (Optional)

**Priority**: 🟡 MEDIUM  
**Estimated Effort**: 4-6 hours  
**Note**: Only needed for 3+ workers or strong consistency requirements

#### Changes Required

**A. Install Dependencies**
```bash
pip install flask-caching>=2.0,<3.0
```

**B. Update `app/extensions.py`**
```python
from flask_caching import Cache
cache = Cache()
```

**C. Update `app/__init__.py`**
```python
from app.extensions import cache

def create_app():
    # ... config ...
    cache_config = {
        "CACHE_TYPE": app.config.get("CACHE_TYPE", "RedisCache"),
        "CACHE_REDIS_URL": app.config.get("CACHE_REDIS_URL", "redis://localhost:6379/0"),
        "CACHE_DEFAULT_TIMEOUT": 300,
    }
    cache.init_app(app, config=cache_config)
```

**D. Migrate `app/cache.py` to use `cache.get/set`**

---

### 4.3 Email Batching with RSET

**Priority**: 🟡 MEDIUM  
**Estimated Effort**: 2-3 hours  
**Note**: Only needed for >500 subscribers

#### Changes Required

**Update `app/email.py` send_newsletter()**
- Add `batch_size=50` parameter
- After each batch, call `server.rset()` to verify connection
- Reconnect if connection dropped

---

## Implementation Timeline

### Week 1: Security Foundation
- [ ] Day 1-2: Install Flask-Limiter, add rate limiting (1.1)
- [ ] Day 3-4: Install Flask-Session, migrate to Redis sessions (1.2)
- [ ] Day 5: Fix login page rendering (1.3)

### Week 2: Frontend Performance
- [ ] Day 1-2: Critical CSS inlining + minification (2.1)
- [ ] Day 3: Conditional Prism.js loading (2.2)
- [ ] Day 4-5: Responsive images - Pillow + srcset (2.3)

### Week 3: Reliability
- [ ] Day 1-2: Scheduler persistence + job logging (3.1)
- [ ] Day 3: PostRevision index migration (3.2)
- [ ] Day 4-5: FTS5 vocabulary optimization (3.3)

### Week 4: Testing & Rollout
- [ ] Day 1-2: Integration testing
- [ ] Day 3-4: Staging deployment
- [ ] Day 5: Production deployment

### Week 5-6: Scale Prep (If Needed)
- [ ] Flask-Caching with Redis (4.2)
- [ ] PostgreSQL connection pooling (4.1)
- [ ] Email batching (4.3)

---

## Testing Strategy

### Unit Tests
```bash
# Run existing tests
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v

# Run without E2E
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e
```

### Performance Tests
```bash
# Install benchmarking tools
pip install pytest-benchmark

# Test page load times
# (Manual) Run Lighthouse audit before/after changes
# (Manual) Test with 100 concurrent users using Apache Bench
ab -n 1000 -c 100 http://localhost:5000/
```

### Rate Limiting Tests
```bash
# Test rate limit breach
for i in {1..6}; do 
    curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:5000/admin/login
    echo ""
done
# Should output: 200 200 200 200 200 429
```

### Session Tests
```bash
# Verify Redis sessions
redis-cli
> KEYS blog_session:*
> GET blog_session:<id>  # Should see msgspec/msgpack data, not plaintext
```

---

## Rollback Plan

If any phase causes issues:

1. **Rate Limiting**: Set `RATELIMIT_STORAGE_URI=memory://` or remove limiter imports
2. **Sessions**: Revert to cookie sessions by commenting out `Session(app)`
3. **CSS Changes**: Revert to original `style.css` loading
4. **Images**: Disable variant generation with config flag

---

## Success Metrics

| Metric | Before | Target After |
|--------|--------|-------------|
| **First Contentful Paint** | ~1.5s | <1.0s |
| **Time to Interactive** | ~2.5s | <1.5s |
| **Page Size (Homepage)** | ~150KB | ~100KB |
| **API Rate Limit** | None | 20/minute |
| **Session Security** | Cookie-visible | Server-side (Redis) |
| **Scheduler Reliability** | Lost on restart | Job logging + recovery |

---

## Appendix: File Change Summary

| File | Phase | Change Type |
|------|-------|--------------|
| `requirements.txt` | 1, 2 | Add flask-limiter, flask-session, Pillow |
| `app/__init__.py` | 1, 2, 4 | Add Limiter, Session, responsive_image filter |
| `app/config.py` | 1 | Add session config vars |
| `config.toml` | 1 | Add [session] section |
| `app/routes/admin/auth.py` | 1 | Add login rate limits |
| `app/routes/api.py` | 1 | Add API rate limits |
| `app/templates/base.html` | 2 | Critical CSS, conditional Prism |
| `app/templates/admin/base.html` | 2 | Critical CSS |
| `app/templates/admin/login_base.html` | 1 | Fix Prism defer |
| `app/static/js/main.js` | 2 | Conditional Prism loading |
| `app/routes/admin/helpers/images.py` | 2 | Pillow variant generation |
| `app/models.py` | 3, 4 | ScheduledJobExecution, Post.view_count |
| `app/scheduler.py` | 3 | Job logging, misfire handling |
| `app/search.py` | 3 | FTS5 vocabulary |
| `migrations/versions/` | 3 | New migration files |
| `app/cache.py` | 4 | Migrate to Flask-Caching (optional) |
| `app/extensions.py` | 4 | Add Cache() (optional) |

---

**End of Plan 4**
