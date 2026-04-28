# Frontend Usability Improvement Plan (Plan 7)

**Status:** Draft  
**Created:** 2026-04-28  
**Scope:** Frontend usability enhancements for Blog CMS  
**Total Items:** 12 (4 High, 4 Medium, 4 Low Priority)

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [High Priority Items](#high-priority-h)
3. [Medium Priority Items](#medium-priority-m)
4. [Low Priority Items](#low-priority-l)
5. [Implementation Order](#implementation-order)
6. [Dependencies](#dependencies)
7. [Testing Strategy](#testing-strategy)

---

## Executive Summary

This plan addresses 12 frontend usability gaps identified during a comprehensive code review. Items are grouped by priority based on user impact and implementation effort.

**Key Outcomes:**
- Enhanced search experience with autocomplete and recent searches
- Client-side form validation to reduce server round-trips
- Eliminated editor preview latency via client-side markdown rendering
- Improved bulk operation feedback on admin dashboard
- Fixed accessibility gaps (SVG icons, color contrast)
- Enhanced keyboard shortcut discoverability
- 5 quick CSS/JS fixes requiring < 10 lines each

---

## High Priority (H)

### H1: Search Experience Enhancements
**Files:** `app/search.py`, `app/routes/public.py`, `app/templates/base.html`, `app/templates/search.html`, `app/static/js/public/search.js` (new)  
**Priority:** High | **Effort:** Medium | **Impact:** High

#### Current State
- Search form in `base.html:62-65` uses native GET form (Enter key works ✓)
- No autocomplete, no recent searches, no loading state
- FTS5 table (`app/search.py:58-61`) lacks prefix index
- No JavaScript handling search interactions

#### Problem
Users receive no feedback while typing and must type full queries without suggestions. No history of recent searches is preserved.

#### Solution
1. **Add FTS5 prefix index** for fast prefix-based suggestions
2. **Create `/api/search/suggestions` endpoint** returning JSON array of matching post titles
3. **Self-host autocomplete library** (~800 bytes gzip): `knadh/autocomp.js`
4. **Add recent searches** via `localStorage` (max 5 entries)
5. **Use ARIA combobox pattern** for accessibility

#### Code Changes

**`app/search.py:58-61`** - Add prefix index:
```python
# Add prefix=2 3 4 for autocomplete (2, 3, 4 character prefixes)
"CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5("
"title, body, summary, prefix=2 3 4"
")"
```

**`app/routes/public.py`** - Add suggestions endpoint:
```python
@public.route("/api/search/suggestions")
def search_suggestions():
    query = request.args.get("q", "").strip()[:50]
    if len(query) < 2:
        return jsonify([])
    # FTS5 prefix search: match queries starting with the typed text
    results = db.session.execute(
        text("SELECT title FROM posts_fts WHERE posts_fts MATCH :q LIMIT 10"),
        {"q": f"{query}*"}
    ).fetchall()
    return jsonify([row[0] for row in results])
```

**New file `app/static/js/public/search.js`**:
```javascript
import { announce } from '../shared/utils.js';

const KEY = 'recentSearches', MAX = 5;

function saveRecent(q) {
    let r = JSON.parse(localStorage.getItem(KEY) || '[]');
    r = r.filter(x => x !== q);
    r.unshift(q);
    localStorage.setItem(KEY, JSON.stringify(r.slice(0, MAX)));
}

// Initialize autocomplete on search input
export function initSearch() {
    const input = document.querySelector('input[name="q"]');
    if (!input) return;
    
    // Load autocomp.js (self-hosted)
    // ... autocomplete initialization with ARIA combobox pattern
}
```

#### Verification
- [ ] Type 2+ characters in search → suggestions appear
- [ ] Click suggestion → navigates to search results
- [ ] Submit search → saved to recent searches
- [ ] Refresh page → recent searches persist in localStorage

---

### H2: Client-Side Form Validation
**Files:** Multiple templates, `app/static/js/lib/formageddon.js` (new), `app/static/js/shared/validation.js` (new)  
**Priority:** High | **Effort:** Medium | **Impact:** High

#### Current State
- 12+ forms lack HTML5 validation attributes (`minlength`, `pattern`)
- No centralized validation library
- Password complexity ("3 of 4 classes") only validated server-side
- Flash messages used for errors (requires page reload)

#### Problem
Users submit invalid forms and wait for server response to see errors. No inline validation feedback.

#### Solution
1. **Self-host `formageddon`** (4.2KB, zero deps) to `app/static/js/lib/`
2. **Add `data-validate` attribute** to forms for auto-initialization
3. **Add missing HTML5 attributes** to all forms
4. **Integrate with existing `showToast()`** from `shared/toast.js`

#### Code Changes

**Download formageddon:**
```bash
curl -o app/static/js/lib/formageddon.js \
  https://raw.githubusercontent.com/dimmerz92/formageddon/master/formageddon.js
```

**`app/templates/admin/reset-password.html:12`** - Add password pattern:
```html
<input type="password" ... required minlength="8" 
       pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*\d)|(?=.*[a-z])(?=.*[A-Z])(?=.*[^\w\s])|(?=.*[a-z])(?=.*\d)(?=.*[^\w\s])|(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s])" 
       title="Must contain 3 of: lowercase, uppercase, digit, special char">
```

**`admin/editor.html:21`** - Add title validation:
```html
<input type="text" ... required minlength="3" maxlength="200">
```

**New file `app/static/js/shared/validation.js`**:
```javascript
import { showToast } from './toast.js';

export function initValidation() {
    document.querySelectorAll('form[data-validate]').forEach(form => {
        new Formageddon(form, {
            errorCallback: (field, message) => {
                showToast(message, 'error');
                field.closest('.form-group')?.classList.add('error');
            }
        });
    });
}
```

#### Forms to Update
| Form | File | Attributes to Add |
|------|------|-------------------|
| Reset Password | `admin/reset-password.html:12` | `pattern`, `title` |
| Post Editor Title | `admin/editor.html:21` | `minlength="3"` |
| Search | `base.html:63` | `required` |
| Media Upload | `admin/media.html:28` | `data-max-size` (JS check) |

#### Verification
- [ ] Submit invalid form → inline toast error (no page reload)
- [ ] Password without 3 char classes → validation error
- [ ] Empty required field → HTML5 validation message

---

### H3: Editor Preview Latency Reduction
**Files:** `app/static/js/admin/editor.js`, `app/static/js/lib/minigfm.min.js` (new)  
**Priority:** High | **Effort:** Low | **Impact:** Medium

#### Current State
- Preview uses server round-trip with 300ms debounce (`editor.js:58`)
- Server processes markdown + nh3 sanitization per request
- No client-side markdown library exists

#### Problem
Preview lags behind typing, especially on slow connections. Server processes redundant requests for draft previews.

#### Solution
1. **Self-host MiniGFM** (~3KB, zero deps, GFM-compatible) to `app/static/js/lib/`
2. **Replace fetch preview with client-side parsing**
3. **Reduce debounce to 150ms** (no network delay)
4. Keep server-side `/admin/preview-markdown` as fallback

#### Code Changes

**Download MiniGFM:**
```bash
curl -o app/static/js/lib/minigfm.min.js \
  https://unpkg.com/@oblivionocean/minigfm@latest/dist/index.min.js
```

**`app/static/js/admin/editor.js:30-57`** - Update preview function:
```javascript
import MiniGFM from '../lib/minigfm.min.js';

export function initEditor() {
    // ... existing code ...
    
    if (bodyTextarea && previewDiv) {
        let debounceTimer;
        const md = new MiniGFM(); // Initialize client-side parser
        
        const updatePreview = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const text = bodyTextarea.value;
                if (!text.trim()) {
                    previewDiv.innerHTML = '<p class="empty-state">Live preview will appear here...</p>';
                    return;
                }
                previewDiv.classList.add('preview-loading');
                try {
                    const html = md.parse(text); // Client-side parsing
                    previewDiv.classList.remove('preview-loading');
                    previewDiv.innerHTML = html;
                } catch (e) {
                    previewDiv.classList.remove('preview-loading');
                    previewDiv.innerHTML = '<p class="form-error">Preview unavailable</p>';
                }
            }, 150); // Reduced from 300ms
        };
        
        // ... rest of existing code ...
    }
}
```

#### Verification
- [ ] Type in editor → preview updates within 150ms
- [ ] No network request for preview (check DevTools Network tab)
- [ ] Markdown features (tables, code blocks) render correctly

---

### H4: Bulk Operation Feedback Enhancement
**Files:** `app/static/js/admin/bulk.js`, `app/templates/admin/dashboard.html`  
**Priority:** High | **Effort:** Low | **Impact:** Medium

#### Current State
- Form submits natively with full page reload
- Overlay shows generic "Processing..." without context
- No indication of which action or how many items

#### Problem
Users see generic spinner without knowing what action is running or how many items are being processed.

#### Solution
1. **Update overlay text** based on clicked action button
2. **Show count of selected items** in overlay
3. No server changes needed (simplest approach)

#### Code Changes

**`app/static/js/admin/bulk.js`** - Add action-specific feedback:
```javascript
const bulkForm = document.getElementById('bulk-form');
const bulkOverlay = document.getElementById('bulk-loading-overlay');
const bulkOverlayText = bulkOverlay?.querySelector('p');

if (bulkForm && bulkOverlay) {
    const submitButtons = bulkForm.querySelectorAll('button[type="submit"]');
    
    submitButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const checkedCount = document.querySelectorAll('.bulk-checkbox:checked').length;
            if (checkedCount === 0) return;
            
            let actionText = 'Processing';
            if (btn.value === 'delete') actionText = 'Deleting';
            else if (btn.value === 'publish') actionText = 'Publishing';
            else if (btn.value === 'unpublish') actionText = 'Unpublishing';
            else if (btn.value === 'unschedule') actionText = 'Unscheduling';
            
            if (bulkOverlayText) {
                bulkOverlayText.textContent = `${actionText} ${checkedCount} post(s)...`;
            }
        });
    });
    
    bulkForm.addEventListener('submit', () => {
        bulkOverlay.classList.add('visible');
    });
}
```

#### Verification
- [ ] Select 3 posts → click Publish → overlay shows "Publishing 3 post(s)..."
- [ ] Select 2 posts → click Delete → overlay shows "Deleting 2 post(s)..."

---

## Medium Priority (M)

### M1: Public Toast Notifications
**Files:** `app/static/js/public/share.js`  
**Priority:** Medium | **Effort:** Very Low | **Impact:** Medium

#### Current State
- Toast system already loads on public pages (`main.js:51`)
- Share buttons use screen reader announcer only (no visual toast)
- Subscribe form uses page reload + flash→toast conversion (works ✓)

#### Problem
Share actions ("Link copied!") only announced to screen readers, not visible to sighted users.

#### Solution
- **1-line change** in `share.js` to call `showToast()` after successful copy

#### Code Changes

**`app/static/js/public/share.js:37-46`**:
```javascript
import { showToast } from '../shared/toast.js'; // Add this import

copyToClipboard(shareUrl).then(() => {
    showToast('Link copied to clipboard!', 'success'); // Add this line
    // existing icon change code...
});
```

#### Verification
- [ ] Click copy link button → success toast appears
- [ ] Toast auto-dismisses after 5 seconds

---

### M2: SVG Icon Accessibility
**Files:** `app/templates/_post_content.html`, `_sidebar.html`, `admin/editor.html`, `admin/dashboard.html`, `admin/media.html`  
**Priority:** Medium | **Effort:** Low | **Impact:** High (accessibility)

#### Current State
- **12 SVGs across 5 templates** - ALL missing accessibility attributes
- No `<title>`, `aria-label`, `role="img"`, or `aria-hidden="true"`

#### Problem
Screen readers cannot identify the purpose of SVG icons. Decorative icons pollute accessibility tree.

#### Solution
- Add `aria-hidden="true"` to SVGs inside already-labeled buttons/links
- Add `role="img"` + `aria-label` to standalone informative icons

#### Code Changes

**`_post_content.html:24-44`** - Share icons (inside labeled links):
```html
<a href="..." class="share-btn share-twitter" aria-label="Share on Twitter">
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
        <path d="..."/>
    </svg>
</a>
<!-- Repeat aria-hidden="true" for all share SVGs -->
```

**`_sidebar.html:26`** - RSS icon:
```html
<a href="{{ url_for('rss.feed') }}" class="rss-link" aria-label="RSS Feed">
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
        <path d="M6.18 15.64a2.18..."/>
    </svg>
    RSS Feed
</a>
```

**`admin/editor.html:54`** - Preview toggle:
```html
<button type="button" id="toggle-preview-btn" class="btn btn-small btn-ghost" aria-label="Toggle preview">
    <svg ... aria-hidden="true"> <!-- Add aria-hidden -->
        <path d="..."/>
    </svg>
</button>
```

#### Verification
- [ ] Run axe DevTools → no SVG accessibility violations
- [ ] Screen reader navigates share buttons → announces "Share on Twitter"
- [ ] Decorative icons skipped by screen reader

---

### M3: Color Contrast Fixes (Light Mode)
**Files:** `app/static/css/style.css`  
**Priority:** Medium | **Effort:** Very Low | **Impact:** High (accessibility)

#### Current State
| Combination | Ratio | WCAG AA (4.5:1) |
|-------------|-------|-----------------|
| Badge text on badge bg (all 4) | ~4.1:1 | ❌ FAIL |
| `--border` `#d0d7de` on white | 1.45:1 | ❌ FAIL (needs 3:1 for UI) |

#### Problem
Badge text and borders fail minimum contrast requirements for accessibility compliance.

#### Solution
1. **Increase badge background alpha** from 0.15 to 0.25
2. **Darken border color** to `#b0b8c2` (improves to ~2.4:1, still not 3:1)

#### Code Changes

**`app/static/css/style.css:1582-1604`** - Update light theme variables:
```css
[data-theme="light"] {
    /* ... existing variables ... */
    --border: #b0b8c2; /* was #d0d7de (improves contrast) */
}
```

**`style.css:2820-2831`** - Update badge backgrounds:
```css
.badge-published {
    color: var(--green);
    background: rgba(26, 127, 55, 0.25); /* was 0.15 */
}

.badge-draft {
    color: var(--yellow);
    background: rgba(210, 153, 34, 0.25); /* was 0.15 */
}

.badge-scheduled {
    color: var(--purple);
    background: rgba(88, 86, 214, 0.25); /* was 0.15 */
}
```

#### Verification
- [ ] Run WebAIM contrast checker → all badges pass 4.5:1
- [ ] Border on white passes 3:1 for UI elements

---

### M4: Keyboard Shortcut Discoverability
**Files:** `app/static/js/admin/shortcuts.js`, `app/templates/admin/base.html`  
**Priority:** Medium | **Effort:** Low | **Impact:** Medium

#### Current State
- 8 shortcuts registered in `shortcuts.js`
- Help modal exists, triggered by `?` button or keypress
- **No first-visit hint**, no tooltip badges on buttons

#### Problem
New admin users don't know keyboard shortcuts exist until they discover the `?` button.

#### Solution
1. **Add `title` attribute** to `?` button (zero JS)
2. **Add first-visit toast hint** using localStorage flag
3. **Add `data-shortcut` attributes** to editor buttons

#### Code Changes

**`app/templates/admin/base.html:52`** - Add title:
```html
<button class="nav-shortcut-btn" id="shortcut-trigger" 
        aria-label="Keyboard shortcuts" 
        title="Keyboard shortcuts (press ?)">?</button>
```

**`app/static/js/admin/shortcuts.js`** - Add first-visit hint:
```javascript
function showShortcutHint() {
    const dismissed = localStorage.getItem('keyboardHintDismissed');
    if (dismissed) return;
    
    const hint = document.createElement('div');
    hint.className = 'shortcut-hint-toast';
    hint.innerHTML = `
        <span>Press <kbd>?</kbd> for keyboard shortcuts</span>
        <button class="hint-dismiss" aria-label="Dismiss">×</button>
    `;
    document.body.appendChild(hint);
    
    hint.querySelector('.hint-dismiss').addEventListener('click', () => {
        hint.remove();
        localStorage.setItem('keyboardHintDismissed', 'true');
    });
    
    setTimeout(() => hint.classList.add('show'), 100);
    setTimeout(() => {
        hint.remove();
        localStorage.setItem('keyboardHintDismissed', 'true');
    }, 8000);
}

// Call at end of initShortcuts():
if (document.body.classList.contains('admin-body')) {
    setTimeout(showShortcutHint, 1500);
}
```

**Add CSS for hint toast** to `style.css`:
```css
.shortcut-hint-toast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: var(--shadow-lg);
    transform: translateY(100px);
    opacity: 0;
    transition: all 0.3s ease;
    z-index: 1000;
}
.shortcut-hint-toast.show {
    transform: translateY(0);
    opacity: 1;
}
```

#### Verification
- [ ] First admin login → sees hint toast after 1.5s
- [ ] Click dismiss → hint doesn't reappear
- [ ] Hover `?` button → shows "Keyboard shortcuts (press ?)" tooltip

---

## Low Priority (L)

### L1: Remove Stat Card Hover Effects
**Files:** `app/static/css/style.css`  
**Priority:** Low | **Effort:** Very Low | **Impact:** Low

#### Current State
Stat cards have hover transform + box-shadow (`style.css:2229-2233`) but are **non-interactive** (no click handler, no `cursor:pointer`).

#### Problem
Hover effects create false affordance (users expect clickable elements).

#### Solution
**Delete the `.stat-card:hover` block** and remove `transition` from `.stat-card`.

#### Code Changes

**`style.css:2220-2233`** - Simplify:
```css
.stat-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    text-align: center;
    /* Removed: transition and hover effect */
}
/* DELETE: .stat-card:hover block entirely */
```

#### Verification
- [ ] Hover stat cards → no visual change (no false affordance)

---

### L2: Reading Progress Bar Toggle
**Files:** `app/static/js/shared/reading-progress-toggle.js` (new), `app/static/css/style.css`, `app/templates/base.html`  
**Priority:** Low | **Effort:** Low | **Impact:** Low

#### Current State
Reading progress bar is always visible on post pages (`utils.js:142-147`, `post.html:50`). ~15-20% of users find it distracting.

#### Solution
Add toggle button (next to dark mode toggle) using localStorage preference.

#### Code Changes

**New file `app/static/js/shared/reading-progress-toggle.js`**:
```javascript
export function initReadingProgressToggle() {
    const toggle = document.createElement('button');
    toggle.className = 'progress-toggle btn btn-ghost btn-small';
    toggle.setAttribute('aria-label', 'Toggle reading progress bar');
    toggle.innerHTML = '📊'; // Or SVG icon
    
    const saved = localStorage.getItem('readingProgressEnabled');
    const isEnabled = saved ? saved === 'true' : true; // Default: enabled
    
    const progressBar = document.getElementById('reading-progress');
    if (progressBar && !isEnabled) {
        progressBar.classList.add('hidden');
    }
    
    toggle.addEventListener('click', () => {
        const enabled = !progressBar.classList.contains('hidden');
        progressBar.classList.toggle('hidden');
        localStorage.setItem('readingProgressEnabled', String(!enabled));
    });
    
    // Insert next to dark mode toggle
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) navLinks.appendChild(toggle);
}
```

**`style.css`** - Add hide class:
```css
.reading-progress.hidden { display: none; }
```

#### Verification
- [ ] Click toggle → progress bar hides/shows
- [ ] Refresh page → preference persists via localStorage

---

### L3: Fix Flash Message Flicker
**Files:** `app/static/css/style.css`  
**Priority:** Low | **Effort:** Very Low | **Impact:** Medium

#### Current State
Flash messages render as visible HTML, then JS hides them and converts to toasts. Brief flicker occurs.

#### Solution
Hide `.flash-container` immediately when JS is enabled using CSS.

#### Code Changes

**`style.css:1415`** - Add after `.flash-container` rule:
```css
/* Hide flashes immediately when JS is enabled to prevent flicker */
html.js .flash-container {
    display: none;
}

@media (scripting: enabled) {
    .flash-container {
        display: none;
    }
}
```

#### Verification
- [ ] With JS enabled → no flash message flicker
- [ ] Without JS → flash messages display correctly (fallback)

---

### L4: Mobile Share Button "More" Menu
**Files:** `app/static/js/public/share.js`, `app/templates/_post_content.html`, `app/static/css/style.css`  
**Priority:** Low | **Effort:** Medium | **Impact:** Low

#### Current State
LinkedIn, HN, Reddit buttons hidden on mobile (`style.css:3418-3420`) with no alternative.

#### Solution
Replace hidden buttons with "More" button showing dropdown panel. Consider Web Share API.

#### Code Changes

**`style.css:3418-3420`** - Update mobile rules:
```css
@media (max-width: 768px) {
    .share-btn-linkedin, .share-btn-hn, 
    .share-btn-reddit, .share-btn-pinterest {
        display: none;
    }
    .share-more { display: inline-flex; } /* New "More" button */
}
```

**`_post_content.html`** - Add "More" button:
```html
<button class="share-btn share-more" aria-label="More sharing options">
    <svg ... aria-hidden="true"><!-- More icon --></svg>
</button>
<div class="share-more-panel" hidden>
    <!-- LinkedIn, HN, Reddit buttons here -->
</div>
```

#### Verification
- [ ] Mobile view → "More" button visible
- [ ] Click "More" → dropdown shows hidden platforms
- [ ] If Web Share API available → native share dialog opens

---

## Implementation Order

Recommended sequence based on effort vs. impact:

1. **L3: Flash Message Flicker** (2 lines CSS, 5 min)
2. **L1: Stat Card Hover** (delete CSS block, 5 min)
3. **M2: SVG Accessibility** (add aria-hidden, 15 min)
4. **M3: Color Contrast** (update CSS vars, 10 min)
5. **M1: Public Toasts** (1-line change, 5 min)
6. **M4: Keyboard Hint** (add toast hint, 20 min)
7. **H4: Bulk Feedback** (update JS, 15 min)
8. **H2: Form Validation** (download lib + update forms, 45 min)
9. **H3: Editor Preview** (download lib + update JS, 30 min)
10. **H1: Search Enhancements** (new endpoint + JS, 60 min)
11. **L2: Progress Bar Toggle** (new JS module, 30 min)
12. **L4: Mobile Share Menu** (new dropdown, 45 min)

---

## Dependencies

| Item | Depends On | Blocks |
|------|-----------|--------|
| H2 (Form Validation) | None | - |
| H3 (Editor Preview) | None | - |
| H1 (Search) | FTS5 prefix index first | - |
| M4 (Keyboard Hint) | None | - |
| L2 (Progress Toggle) | None | - |

---

## Testing Strategy

### Automated Tests
- Run existing test suite after each change:
  ```bash
  ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
  ```

### Manual Testing Checklist
Each item includes verification steps (see individual sections above).

### Accessibility Testing
- Run axe DevTools on all modified pages
- Test with screen reader (NVDA/VoiceOver)
- Verify keyboard navigation works

### Browser Testing
- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest version)
- Mobile: iOS Safari, Chrome Android

---

**Plan Status:** Ready for Review
