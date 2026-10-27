"""Frontend contract tests for public interaction and build correctness.

These are fast, deterministic assertions over the rendered markup, the module
sources and (when a build exists) the Vite manifest. Browser-level checks live
in ``tests/e2e/test_frontend_interactions.py``, where they run against the e2e
application's own database.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
JS_DIR = REPO_ROOT / "app" / "static" / "js"
TEMPLATE_DIR = REPO_ROOT / "app" / "templates"
DIST_DIR = REPO_ROOT / "app" / "static" / "dist"
MANIFEST_PATH = DIST_DIR / ".vite" / "manifest.json"

NODE = shutil.which("node")

requires_node = pytest.mark.skipif(NODE is None, reason="node is not installed")
requires_frontend_build = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="frontend bundle not built (run `npm run build`)",
)


def read_js(*parts: str) -> str:
    return JS_DIR.joinpath(*parts).read_text(encoding="utf-8")


def read_template(*parts: str) -> str:
    return TEMPLATE_DIR.joinpath(*parts).read_text(encoding="utf-8")


def run_node(script: str) -> str:
    assert NODE is not None
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, f"node failed:\n{result.stderr}"
    return result.stdout


def button_tags(html: str) -> list[str]:
    return re.findall(r"<button\b[^>]*>", html)


def heading_entries(html: str) -> list[tuple[int, str]]:
    """Return the (level, text) of every heading in document order."""
    entries: list[tuple[int, str]] = []
    for match in re.finditer(r"<h([1-6])\b[^>]*>(.*?)</h\1>", html, re.DOTALL):
        text = re.sub(r"<[^>]+>", " ", match.group(2))
        text = re.sub(r"\s+", " ", text).strip()
        entries.append((int(match.group(1)), text))
    return entries


def region_html(html: str, start_tag: str, end_tag: str) -> str:
    start = html.index(start_tag)
    end = html.index(end_tag, start) + len(end_tag)
    return html[start:end]


def sidebar_region(html: str) -> str:
    return region_html(html, "<aside", "</aside>")


def footer_region(html: str) -> str:
    start = html.rindex("<footer")
    return html[start : html.index("</footer>", start)]


def main_region(html: str) -> str:
    return region_html(html, "<main", "</main>")


def meta_content(html: str, attribute: str) -> str | None:
    """Return the content of the first <meta> carrying the given attribute."""
    match = re.search(r"<meta\b[^>]*" + re.escape(attribute) + r"[^>]*>", html)
    if not match:
        return None
    content = re.search(r'content="([^"]*)"', match.group(0))
    return content.group(1) if content else None


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# FE-INT-01 — lightbox visibility contract
# ---------------------------------------------------------------------------


def test_lightbox_markup_carries_the_visibility_contract(client, sample_post):
    html = client.get(f"/post/{sample_post.slug}").data.decode()

    assert 'class="lightbox hidden"' in html
    assert 'id="lightbox"' in html
    assert 'aria-hidden="true"' in html

    for css_class in ("lightbox-close", "lightbox-prev", "lightbox-next"):
        tags = [t for t in button_tags(html) if css_class in t]
        assert tags, f"no button with class {css_class}"
        assert all('type="button"' in tag for tag in tags), f"{css_class} missing type=button"

    img_tag = re.search(r'<img[^>]*class="lightbox-img"[^>]*>', html)
    assert img_tag, "lightbox image element missing"
    src = re.search(r'src="([^"]*)"', img_tag.group(0))
    assert src is not None, "lightbox image has no src attribute"
    assert src.group(1).strip(), "lightbox image src must not be empty"


def test_lightbox_js_uses_hidden_as_visibility_source_of_truth():
    src = read_js("public", "lightbox.js")

    open_block = src.split("const openLightbox")[1].split("const closeLightbox")[0]
    close_block = src.split("const closeLightbox")[1].split("const prevImage")[0]

    assert "classList.remove('hidden')" in open_block
    assert "classList.add('open')" in open_block
    assert "document.body.style.overflow = 'hidden'" in open_block

    assert "classList.add('hidden')" in close_block
    assert "classList.remove('open')" in close_block
    assert "previousBodyOverflow" in close_block
    assert "document.body.style.overflow = previousBodyOverflow" in close_block
    assert "document.body.style.overflow = ''" not in close_block


# ---------------------------------------------------------------------------
# FE-INT-02 — one producer for heading ids
# ---------------------------------------------------------------------------


def test_toc_and_anchor_links_import_the_shared_slug_module():
    toc = read_js("public", "toc.js")
    anchors = read_js("public", "anchor-links.js")

    assert "shared/heading-slug.js" in toc
    assert "shared/heading-slug.js" in anchors
    assert "heading-${index}" not in toc
    assert "heading-${" not in toc


def test_shared_slug_module_is_not_globbed_as_a_page_module():
    main = read_js("main.js")
    assert "heading-slug" not in main


@requires_node
def test_shared_slug_generator_is_deterministic_and_collision_safe():
    script = """
    const m = await import('./app/static/js/shared/heading-slug.js');
    const makeHeading = (text, id = '') => ({
        id,
        tagName: 'H2',
        textContent: text,
        cloneNode: () => ({ querySelectorAll: () => [], textContent: text }),
    });
    const used = new Set();
    const first = m.assignHeadingId(makeHeading('Hello World'), used);
    const second = m.assignHeadingId(makeHeading('Hello World'), used);
    const third = m.assignHeadingId(makeHeading('Hello, World!'), used);
    const blank = m.assignHeadingId(makeHeading('   '), used);
    const repeat = m.slugifyHeading('  A B  c ');
    console.log(JSON.stringify({ first, second, third, blank, repeat }));
    """
    out = json.loads(run_node(script))

    assert out["first"] == "hello-world"
    assert out["second"] == "hello-world-1"
    assert out["third"] == "hello-world-2"
    assert out["blank"] == "h2"
    assert out["repeat"] == "a-b-c"


# ---------------------------------------------------------------------------
# FE-INT-03 — copy link produces a usable URL
# ---------------------------------------------------------------------------


def test_anchor_links_does_not_concatenate_two_urls():
    src = read_js("public", "anchor-links.js")

    assert "window.location.origin + window.location.pathname" not in src
    assert "location.origin" not in src
    assert "const fullUrl = anchor.href;" in src


@requires_node
def test_anchor_href_resolves_to_an_absolute_url():
    script = """
    const base = 'https://example.test/post/a-post';
    const anchor = { href: new URL('#a-heading', base).href };
    console.log(JSON.stringify({ href: anchor.href }));
    """
    out = json.loads(run_node(script))
    assert out["href"].startswith("https://example.test/post/a-post#")
    assert out["href"].count("https://") == 1


def test_the_anchor_is_appended_to_the_heading_itself():
    src = read_js("public", "anchor-links.js")

    assert "heading.appendChild(anchor)" in src
    assert "heading-anchor" not in src


def test_the_heading_text_helper_strips_the_anchor():
    src = read_js("shared", "heading-slug.js")

    assert ".anchor-link" in src
    assert "heading-anchor" not in src


# ---------------------------------------------------------------------------
# The empty profile picture
# ---------------------------------------------------------------------------

AVATAR_TEMPLATES = ("account.html", "author.html", "_post_content.html", "admin/user_profile.html")

OLD_INLINE_ICON = "M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"


def test_the_empty_profile_picture_has_one_shared_owner():
    partial = read_template("_default_avatar.html")

    assert "macro default_avatar" in partial
    assert "<svg" in partial

    for template in AVATAR_TEMPLATES:
        source = read_template(template)
        assert "default_avatar" in source, f"{template} does not use the shared placeholder"
        assert OLD_INLINE_ICON not in source, f"{template} still draws its own avatar icon"


def test_the_empty_profile_picture_is_not_a_letter():
    source = read_template("account.html")

    assert "profile_name[:1]|upper" not in source
    assert "account-avatar-placeholder" in source


# ---------------------------------------------------------------------------
# FE-INT-04 / FE-INT-05 — module routing
# ---------------------------------------------------------------------------


MODULE_MAP_SCRIPT = """
import vm from 'node:vm';
import fs from 'node:fs';

let src = fs.readFileSync('app/static/js/main.js', 'utf8');
src = src.replace(/^export\\s+/gm, '');
src = src.replace(/const moduleGlob = import\\.meta\\.glob\\(\\[[\\s\\S]*?\\]\\);/, 'const moduleGlob = {};');
src = src.replace(/document\\.addEventListener\\("DOMContentLoaded"[\\s\\S]*$/, '');
src += '\\nglobalThis.__result = { getModulesForPath, PUBLIC_MODULES, ROUTE_MODULES };';

const sandbox = {
    console,
    document: { documentElement: { dataset: {}, classList: { add() {} } } },
    window: {},
    globalThis: null,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src, sandbox);

const { getModulesForPath, PUBLIC_MODULES, ROUTE_MODULES } = sandbox.__result;
const paths = ['/admin/newsletter/preview', '/admin/new', '/admin/', '/admin/media', '/'];
const resolved = {};
for (const p of paths) resolved[p] = getModulesForPath(p);
console.log(JSON.stringify({ resolved, publicModules: PUBLIC_MODULES, routes: Object.keys(ROUTE_MODULES) }));
"""


@pytest.fixture(scope="module")
def module_map():
    if NODE is None:
        pytest.skip("node is not installed")
    return json.loads(run_node(MODULE_MAP_SCRIPT))


def test_media_copy_module_is_routed_to_the_admin_media_page(module_map):
    media = module_map["resolved"]["/admin/media"]
    public = module_map["resolved"]["/"]

    assert "./public/media-copy.js" in media
    assert "./public/media-copy.js" not in public
    assert "./upload.js" in media


def test_route_prefix_matching_cannot_over_match(module_map):
    resolved = module_map["resolved"]

    newsletter = resolved["/admin/newsletter/preview"]
    assert "./admin/editor.js" not in newsletter
    assert "./admin/bulk.js" in newsletter

    assert "./admin/editor.js" in resolved["/admin/new"]

    admin_default = resolved["/admin/"]
    assert "./admin/editor.js" not in admin_default
    assert "./admin/bulk.js" in admin_default

    assert "./public/lightbox.js" in resolved["/"]
    assert "./shared/color-scheme.js" in resolved["/"]


# ---------------------------------------------------------------------------
# FE-INT-07 / FE-INT-09 — build output
# ---------------------------------------------------------------------------


@requires_frontend_build
def test_build_emits_no_orphaned_css_asset():
    manifest = load_manifest()

    for key, entry in manifest.items():
        assert not entry.get("css"), f"{key} still emits a css asset"

    assert not list(DIST_DIR.glob("*.css")), "an orphaned css file was emitted"

    main_src = read_js("main.js")
    assert not re.search(r"""import\s+['"][^'"]+\.css['"]""", main_src)


@requires_frontend_build
def test_shared_utils_is_not_bundled_into_the_admin_chunk():
    manifest = load_manifest()

    shared_file = manifest["js/shared/utils.js"]["file"]
    admin_entry = manifest["js/admin/editor.js"]
    admin_file = admin_entry["file"]

    assert shared_file != admin_file
    assert "js/shared/utils.js" in admin_entry.get("imports", [])

    admin_src = (DIST_DIR / admin_file).read_text(encoding="utf-8")
    assert "initSharedUtils" not in admin_src


# ---------------------------------------------------------------------------
# FE-INT-08 — bulk delete button label
# ---------------------------------------------------------------------------


def test_bulk_delete_button_keeps_original_text_in_a_closure():
    src = read_js("shared", "utils.js")

    assert "delete btn.dataset.originalText" not in src
    assert "btn.dataset.originalText" not in src
    assert "let originalText = btn.textContent" in src
    assert "btn.textContent = originalText" in src


# ---------------------------------------------------------------------------
# FE-INT-11 — public comment form
# ---------------------------------------------------------------------------


def test_comment_template_uses_the_csrf_token_variable():
    src = read_template("public", "comments.html")

    assert "{{ csrf_token }}" in src
    assert "csrf_token()" not in src


def test_post_page_renders_comment_form_with_associated_labels(client, sample_post):
    html = client.get(f"/post/{sample_post.slug}").data.decode()

    form = re.search(r'<form[^>]*action="/post/[^"]+/comment".*?</form>', html, re.DOTALL)
    assert form, "comment form not rendered on the post page"
    form_html = form.group(0)

    labels = re.findall(r'<label[^>]*for="([^"]+)"', form_html)
    ids = re.findall(r'id="([^"]+)"', form_html)
    assert labels
    for label_for in labels:
        assert label_for in ids, f"label for={label_for} has no matching control"

    assert re.search(r'name="csrf_token" value="[^"]+"', form_html)
    assert 'name="website_url"' in form_html


def test_post_route_supplies_only_approved_comments(client, db, sample_post):
    from app.models import Comment

    db.session.add(
        Comment(
            post_id=sample_post.id,
            author_name="Approved",
            author_email="approved@example.com",
            content="Approved comment body",
            approved=True,
        )
    )
    db.session.add(
        Comment(
            post_id=sample_post.id,
            author_name="Pending",
            author_email="pending@example.com",
            content="Pending comment body",
            approved=False,
        )
    )
    db.session.commit()

    html = client.get(f"/post/{sample_post.slug}").data.decode()
    assert "Approved comment body" in html
    assert "Pending comment body" not in html


def test_comment_post_redirects_and_awaits_approval(client, db, sample_post):
    from app.models import Comment

    response = client.post(
        f"/post/{sample_post.slug}/comment",
        data={
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "content": "Great post!",
        },
    )
    assert response.status_code == 302

    comment = db.session.execute(db.select(Comment).filter_by(post_id=sample_post.id)).scalar_one()
    assert comment.approved is False


# ---------------------------------------------------------------------------
# FE-INT-12 / FE-INT-13 — colour scheme controller and control placement
# ---------------------------------------------------------------------------


def test_color_scheme_toggle_is_not_placed_inside_nav_links():
    src = read_js("shared", "color-scheme.js")

    assert not re.search(r"""querySelector\(\s*['"]\.nav-links['"]""", src)
    assert ".nav-actions" in src


def test_color_scheme_controller_uses_the_configured_default():
    src = read_js("shared", "color-scheme.js")

    assert "defaultScheme" in src
    assert re.search(r"dataset\??\.defaultScheme", src)
    assert "getStoredScheme()" not in src, "default scheme dropped by an internal call"


def test_base_template_publishes_the_configured_default_scheme():
    src = read_template("base.html")
    assert 'data-default-scheme="{{ theme_default_scheme | e }}"' in src
    assert 'class="nav-actions"' in src


# ---------------------------------------------------------------------------
# FE-A11Y-01 — public series navigation
# ---------------------------------------------------------------------------


@pytest.fixture
def series_with_posts(db, sample_post):
    """A published series of three posts, ordered by PostSeries.order_index."""
    from app.models import Post, PostSeries, Series
    from app.utils import utc_now

    series = Series(name="Deep Dive", slug="deep-dive", description="A multi-part series")
    db.session.add(series)
    db.session.commit()

    second = Post(
        title="Second Part",
        slug="second-part",
        body="Second body.",
        published=True,
        published_at=utc_now(),
    )
    third = Post(
        title="Third Part",
        slug="third-part",
        body="Third body.",
        published=True,
        published_at=utc_now(),
    )
    db.session.add_all([second, third])
    db.session.commit()

    db.session.add_all(
        [
            PostSeries(series_id=series.id, post_id=sample_post.id, order_index=1),
            PostSeries(series_id=series.id, post_id=second.id, order_index=2),
            PostSeries(series_id=series.id, post_id=third.id, order_index=3),
        ]
    )
    db.session.commit()
    return series


def series_nav_html(html: str) -> str:
    """Return the rendered series navigation block."""
    match = re.search(r'<nav class="series-nav".*?</nav>', html, re.DOTALL)
    assert match, "the series navigation was not rendered"
    return match.group(0)


def test_post_in_a_series_renders_the_series_navigation(client, series_with_posts):
    response = client.get("/post/second-part")

    assert response.status_code == 200
    html = response.data.decode()
    nav = series_nav_html(html)

    assert "Deep Dive" in nav
    assert "/post/test-post" in nav
    assert "/post/third-part" in nav
    assert "/series/deep-dive" in nav


def test_series_navigation_links_resolve_to_real_pages(client, series_with_posts):
    html = client.get("/post/second-part").data.decode()
    nav = series_nav_html(html)

    hrefs = re.findall(r'href="([^"]+)"', nav)
    assert hrefs
    for href in hrefs:
        response = client.get(href)
        assert response.status_code == 200, f"{href} does not resolve"


def test_series_navigation_endpoint_name_is_pinned(app):
    """The sidebar used to build 'public.series', which raises BuildError."""
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}

    assert "public.series_view" in endpoints
    assert "public.series" not in endpoints

    source = read_template("_series_nav.html")
    assert re.search(r"url_for\(['\"]public\.series_view['\"]", source)
    assert not re.search(r"url_for\(['\"]public\.series['\"]", source)


def test_series_navigation_neighbours_come_from_the_same_series(client, db, series_with_posts):
    from app.models import Post, PostSeries, Series
    from app.utils import utc_now

    other_series = Series(name="Other Series", slug="other-series")
    db.session.add(other_series)
    db.session.commit()

    outsider = Post(
        title="Outsider",
        slug="outsider",
        body="Not part of the series.",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(outsider)
    db.session.commit()
    db.session.add(PostSeries(series_id=other_series.id, post_id=outsider.id, order_index=1))
    db.session.commit()

    nav = series_nav_html(client.get("/post/third-part").data.decode())

    assert "/post/second-part" in nav
    assert "Outsider" not in nav
    assert "/series/other-series" not in nav
    assert "/series/deep-dive" in nav


# ---------------------------------------------------------------------------
# FE-A11Y-02 — every visible form control has a label
# ---------------------------------------------------------------------------


def test_every_visible_input_on_the_homepage_has_an_associated_label(client):
    html = client.get("/").data.decode()

    label_targets = set()
    for tag in re.findall(r"<label\b[^>]*>", html):
        target = re.search(r'for="([^"]+)"', tag)
        if target:
            label_targets.add(target.group(1))

    label_blocks = re.findall(r"<label\b[^>]*>.*?</label>", html, re.DOTALL)

    for tag in re.findall(r"<input\b[^>]*>", html):
        input_type = re.search(r'type="([^"]+)"', tag)
        input_type = input_type.group(1).lower() if input_type else "text"
        if input_type in {"hidden", "submit", "button", "reset", "image"}:
            continue

        identifier = re.search(r'id="([^"]+)"', tag)
        if identifier:
            assert identifier.group(1) in label_targets, f"no label for {tag}"
        else:
            assert any(tag in block for block in label_blocks), f"unlabelled {tag}"


# ---------------------------------------------------------------------------
# FE-A11Y-03 / FE-A11Y-04 — social preview metadata
# ---------------------------------------------------------------------------


def test_listing_pages_emit_complete_social_metadata(client, sample_post, sample_tag):
    pages = [
        "/",
        "/archive",
        f"/tag/{sample_tag.slug}",
        "/search?q=hello",
    ]

    for path in pages:
        html = client.get(path).data.decode()

        for attribute in (
            'property="og:title"',
            'property="og:description"',
            'property="og:image"',
            'name="twitter:title"',
            'name="twitter:description"',
            'name="twitter:image"',
        ):
            value = meta_content(html, attribute)
            assert value, f"{attribute} is missing or empty on {path}"


def test_post_page_keeps_its_own_social_metadata(client, sample_post):
    html = client.get(f"/post/{sample_post.slug}").data.decode()

    assert meta_content(html, 'property="og:title"') == sample_post.title
    assert meta_content(html, 'name="twitter:title"') == sample_post.title
    assert meta_content(html, 'property="og:description"') == sample_post.summary
    assert meta_content(html, 'name="twitter:description"') == sample_post.summary

    og_image = meta_content(html, 'property="og:image"')
    twitter_image = meta_content(html, 'name="twitter:image"')
    assert og_image and og_image.endswith("/static/img/default-post-social.png")
    assert twitter_image == og_image


# ---------------------------------------------------------------------------
# FE-A11Y-05 — landmarks are distinguishable
# ---------------------------------------------------------------------------


def test_sidebar_and_footer_have_distinct_accessible_names(client):
    html = client.get("/").data.decode()

    aside = re.search(r"<aside\b[^>]*>", html)
    footer = re.search(r"<footer\b[^>]*\bid=\"footer\"[^>]*>", html)
    assert aside and footer

    aside_label = re.search(r'aria-label="([^"]+)"', aside.group(0))
    footer_label = re.search(r'aria-label="([^"]+)"', footer.group(0))

    assert aside_label, "the sidebar has no accessible name"
    assert footer_label, "the footer has no accessible name"
    assert aside_label.group(1) != footer_label.group(1)


def test_heading_text_is_not_duplicated_inside_a_landmark(client, sample_post, sample_tag):
    html = client.get("/").data.decode()

    for region in (main_region(html), sidebar_region(html), footer_region(html)):
        texts = [text for _, text in heading_entries(region) if text]
        duplicates = sorted({text for text in texts if texts.count(text) > 1})
        assert not duplicates, f"duplicated heading text: {duplicates}"


def test_sidebar_and_footer_do_not_repeat_the_same_heading(client):
    html = client.get("/").data.decode()

    sidebar_headings = {text for _, text in heading_entries(sidebar_region(html)) if text}
    footer_headings = {text for _, text in heading_entries(footer_region(html)) if text}

    assert sidebar_headings, "the sidebar has no headings"
    assert footer_headings, "the footer has no headings"
    assert not sidebar_headings & footer_headings


# ---------------------------------------------------------------------------
# FE-A11Y-06 / heading order
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/archive", "/search?q=hello", "/tag/python"])
def test_heading_levels_never_skip_a_level(client, sample_post, sample_tag, path):
    html = client.get(path).data.decode()

    levels = [level for level, _ in heading_entries(html)]
    assert levels, "no headings rendered"

    for previous, current in zip(levels, levels[1:]):
        assert current <= previous + 1, f"heading level skipped from h{previous} to h{current}"


def test_post_page_heading_levels_never_skip_a_level(client, db):
    from app.models import Post
    from app.utils import utc_now

    post = Post(
        title="Plain Post",
        slug="plain-post",
        body="A body without any headings.",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()

    html = client.get("/post/plain-post").data.decode()

    levels = [level for level, _ in heading_entries(html)]
    assert levels, "no headings rendered"
    for previous, current in zip(levels, levels[1:]):
        assert current <= previous + 1, f"heading level skipped from h{previous} to h{current}"


# ---------------------------------------------------------------------------
# FE-A11Y-07 — explicit button types
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/archive", "/search?q=hello", "/tag/python"])
def test_every_button_declares_an_explicit_type(client, sample_post, sample_tag, path):
    html = client.get(path).data.decode()

    tags = button_tags(html)
    assert tags, "no buttons rendered"

    for tag in tags:
        assert re.search(r'\btype="[^"]+"', tag), f"button without an explicit type: {tag}"


def test_no_button_inside_a_form_defaults_to_submit(client, sample_post):
    html = client.get(f"/post/{sample_post.slug}").data.decode()

    for form in re.findall(r"<form\b[^>]*>.*?</form>", html, re.DOTALL):
        for tag in button_tags(form):
            assert re.search(r'\btype="[^"]+"', tag), f"button without an explicit type: {tag}"


# ---------------------------------------------------------------------------
# FE-A11Y-08 — empty states
# ---------------------------------------------------------------------------


def test_index_renders_an_empty_state_when_no_post_is_published(client, db):
    from app.models import Post

    db.session.add(Post(title="Draft", slug="draft-post", body="Draft body.", published=False))
    db.session.commit()

    html = client.get("/").data.decode()

    assert 'class="empty-state"' in html
    assert "No posts yet" in html


def test_tag_and_series_pages_render_empty_states(client, db, sample_tag):
    from app.models import Series

    db.session.add(Series(name="Empty Series", slug="empty-series"))
    db.session.commit()

    tag_html = client.get(f"/tag/{sample_tag.slug}").data.decode()
    assert 'class="empty-state"' in tag_html

    series_html = client.get("/series/empty-series").data.decode()
    assert 'class="empty-state"' in series_html


# ---------------------------------------------------------------------------
# Colour scheme toggle state
# ---------------------------------------------------------------------------


COLOR_SCHEME_STATE_SCRIPT = """
const store = new Map();
globalThis.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
};

let button = null;
function makeButton() {
    const attrs = {};
    const listeners = {};
    return {
        className: '',
        type: '',
        title: '',
        innerHTML: '',
        attrs,
        listeners,
        setAttribute(name, value) { attrs[name] = String(value); },
        getAttribute(name) { return name in attrs ? attrs[name] : null; },
        addEventListener(name, handler) { listeners[name] = handler; },
    };
}

globalThis.document = {
    documentElement: { dataset: { defaultScheme: 'system' }, setAttribute() {} },
    createElement: () => { button = makeButton(); return button; },
    querySelector: (selector) => (selector === '.nav-actions' ? { appendChild() {} } : null),
};

globalThis.window = {
    matchMedia: () => ({ matches: false, addEventListener() {} }),
};

const mod = await import('./app/static/js/shared/color-scheme.js');

function snapshot() {
    return {
        pressed: button.getAttribute('aria-pressed'),
        label: button.getAttribute('aria-label'),
    };
}

function start(stored) {
    store.clear();
    if (stored) {
        store.set('blog-color-scheme', stored);
    }
    button = null;
    mod.initColorScheme();
    return snapshot();
}

const system = start(null);
button.listeners.click();
const afterDark = snapshot();
button.listeners.click();
const afterLight = snapshot();
const storedDark = start('dark');

console.log(JSON.stringify({ system, afterDark, afterLight, storedDark }));
"""


@requires_node
def test_color_scheme_toggle_exposes_its_state():
    out = json.loads(run_node(COLOR_SCHEME_STATE_SCRIPT))

    assert out["system"]["pressed"] == "false"
    assert out["system"]["label"], "the toggle must carry an accessible name"

    assert out["afterDark"]["pressed"] == "true"
    assert out["afterDark"]["label"] != out["system"]["label"]

    assert out["afterLight"]["pressed"] == "true"
    assert out["afterLight"]["label"] != out["afterDark"]["label"]

    assert out["storedDark"]["pressed"] == "true"
