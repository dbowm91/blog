"""Contract tests for the admin dashboard form and control contracts.

Covers the findings of plans/frontend_corrective_phase_03_admin_form_contracts.md:
media upload body, CSRF header name, preview sanitisation, theme error rendering,
analytics/audit filter contracts, preview toggle, page editor parity, series
reorder/remove, form loading states, admin titles, editor draft keys and bulk
action guards.
"""

from __future__ import annotations

import base64
import io
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = APP_DIR / "app" / "templates"
ADMIN_TEMPLATES_DIR = TEMPLATES_DIR / "admin"
STATIC_DIR = APP_DIR / "app" / "static"
JS_DIR = STATIC_DIR / "js"

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.S)
    assert match, "rendered page has no <title> element"
    return match.group(1).strip()


def _inline_scripts(html: str) -> str:
    return "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html, re.S))


def _node_available() -> bool:
    return shutil.which("node") is not None


def _run_node_esm(tmp_path: Path, script: str) -> dict:
    """Run an ES module snippet against the real admin JS sources."""
    package = tmp_path / "package.json"
    package.write_text(json.dumps({"type": "module"}), encoding="utf-8")
    (tmp_path / "admin").mkdir()
    (tmp_path / "shared").mkdir()
    shutil.copy2(JS_DIR / "admin" / "editor.js", tmp_path / "admin" / "editor.js")
    shutil.copy2(
        JS_DIR / "admin" / "markdown-toolbar.js",
        tmp_path / "admin" / "markdown-toolbar.js",
    )
    shutil.copy2(
        JS_DIR / "admin" / "editor-history.js",
        tmp_path / "admin" / "editor-history.js",
    )
    shutil.copy2(JS_DIR / "shared" / "utils.js", tmp_path / "shared" / "utils.js")
    shutil.copy2(JS_DIR / "shared" / "filter-select.js", tmp_path / "shared" / "filter-select.js")
    driver = tmp_path / "driver.mjs"
    driver.write_text(script, encoding="utf-8")
    result = subprocess.run(
        ["node", str(driver)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=60,
    )
    assert result.returncode == 0, f"node failed: {result.stderr}"
    return json.loads(result.stdout)


# --- FE-ADM-01: media upload -------------------------------------------------


def test_media_upload_with_single_file_part_succeeds(authenticated_client, app):
    """A multipart body with one file part is stored, not rejected."""
    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    before = set(upload_dir.glob("*"))

    response = authenticated_client.post(
        "/admin/media/upload",
        data={"file": (io.BytesIO(PNG_1X1), "pixel.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302

    listing = authenticated_client.get("/admin/media")
    body = listing.get_data(as_text=True)
    assert "Uploaded" in body

    created = sorted(set(upload_dir.glob("*")) - before)
    try:
        assert created, "uploaded file was not written to the upload folder"
    finally:
        for path in created:
            path.unlink(missing_ok=True)


def test_media_page_declares_exactly_one_file_input(authenticated_client):
    """The media page must not declare a second, empty file input named file."""
    html = authenticated_client.get("/admin/media").get_data(as_text=True)
    file_inputs = re.findall(r"<input[^>]*type=\"file\"[^>]*>", html)
    assert len(file_inputs) == 1
    assert 'id="file-input"' in file_inputs[0]
    assert 'name="file"' not in file_inputs[0]
    assert "file-input-hidden" not in html


def test_upload_js_builds_multipart_body_explicitly():
    """The upload body is assembled in JS, not serialised from the template."""
    source = _read(JS_DIR / "upload.js")
    assert "new FormData(uploadForm)" not in source
    assert "formData.append('file', file)" in source
    assert "formData.append('csrf_token', csrfToken)" in source
    assert "'X-CSRF-Token'" not in source
    assert "getCsrfHeaderName()" in source


# --- FE-ADM-02: CSRF header name ---------------------------------------------


def test_csrf_header_name_matches_server_definition():
    """The header name is defined once, in app/csrf.py."""
    csrf_source = _read(APP_DIR / "app" / "csrf.py")
    assert 'CSRF_HEADER_NAME = "X-CSRF-Token"' in csrf_source

    offenders = []
    for path in list(TEMPLATES_DIR.rglob("*.html")) + list(JS_DIR.rglob("*.js")):
        if "X-CSRFToken" in _read(path):
            offenders.append(str(path.relative_to(APP_DIR)))
    assert offenders == [], f"misspelled CSRF header still in use: {offenders}"


def test_admin_pages_publish_the_csrf_header_name(authenticated_client):
    """The header name reaches the browser through the root element."""
    html = authenticated_client.get("/admin/settings").get_data(as_text=True)
    assert 'data-csrf-header="X-CSRF-Token"' in html
    assert "document.documentElement.dataset.csrfHeader" in _inline_scripts(html)


def test_editor_preview_uses_shared_csrf_header_helper():
    """Module code uses the shared helper instead of a hard-coded name."""
    source = _read(JS_DIR / "admin" / "editor.js")
    assert "csrfHeaders()" in source
    assert '"X-CSRF-Token"' not in source


# --- FE-ADM-03: preview sanitisation -----------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        '<img src=x onerror="window.__xss=1">',
        "<script>window.__xss=1</script>",
        '<a href="javascript:window.__xss=1">x</a>',
        '<iframe src="javascript:window.__xss=1"></iframe>',
        "<style>body{background:url(javascript:1)}</style>",
    ],
)
def test_preview_markdown_strips_executable_markup(authenticated_client, payload):
    """The sanitised preview carries no executable handlers."""
    response = authenticated_client.post("/admin/preview-markdown", json={"text": payload})
    assert response.status_code == 200
    html = response.get_json()["html"]
    assert "onerror" not in html
    assert "__xss" not in html
    assert "<script" not in html.lower()
    assert "<iframe" not in html.lower()
    assert "<style" not in html.lower()
    assert "javascript:" not in html.lower()


def test_editor_js_does_not_render_unsanitised_client_markdown():
    """The client preview renders the server-sanitised payload only."""
    source = _read(JS_DIR / "admin" / "editor.js")
    assert "marked.parse" not in source
    assert "previewDiv.innerHTML = data.html" in source
    assert "innerHTML = marked" not in source


# --- FE-ADM-04: theme preview error rendering --------------------------------


def test_theme_preview_error_reflects_user_input(authenticated_client):
    """The server reflects the submitted theme name in the error payload."""
    payload = "<img src=x onerror=alert(1)>"
    response = authenticated_client.post(
        "/admin/settings/theme/preview",
        data={"theme_dark_name": payload, "theme_light_name": payload},
    )
    assert response.status_code == 400
    body = response.get_json()
    assert payload in body["error"]


def test_theme_preview_error_is_rendered_as_text():
    """The error is written with textContent, never as markup."""
    script = _inline_scripts(_read(ADMIN_TEMPLATES_DIR / "settings.html"))
    inner_html_exprs = re.findall(r"\.innerHTML\s*=\s*([^;]+);", script)
    assert inner_html_exprs, "expected the settings script to render preview markup"
    for expr in inner_html_exprs:
        assert "error" not in expr.lower(), f"error rendered as markup: {expr}"
    assert re.search(r"\.textContent\s*=\s*'Error: ' \+ message;", script)
    assert "data.error" in script


# --- FE-ADM-05 / FE-ADM-06: filter contracts ---------------------------------


def test_analytics_and_audit_filters_use_distinct_hooks(authenticated_client):
    """The day filter and the audit filter do not share an attribute hook."""
    analytics = authenticated_client.get("/admin/analytics").get_data(as_text=True)
    audit = authenticated_client.get("/admin/audit").get_data(as_text=True)

    assert "data-auto-submit" in analytics
    assert "data-audit-filter" not in analytics
    assert "data-audit-filter" in audit
    assert "data-auto-submit" not in audit


def test_day_filter_navigates_without_looking_up_a_form():
    """The day-count branch must not dereference closest('form')."""
    source = _read(JS_DIR / "shared" / "filter-select.js")
    day_branch = source.split("isDayCount(value)")[1].split("return;")[0]
    assert "closest('form')" not in day_branch

    for match in re.finditer(r"closest\('form'\)", source):
        tail = source[match.end() : match.end() + 60]
        assert "if (!form) return;" in tail

    assert "data-audit-filter" in source
    assert "data-auto-submit" in source


@pytest.mark.skipif(not _node_available(), reason="node runtime is not available")
def test_day_filter_rejects_action_names(tmp_path):
    """Audit action names are not day counts."""
    result = _run_node_esm(
        tmp_path,
        """
        import { isDayCount } from './shared/filter-select.js';
        console.log(JSON.stringify({
            day7: isDayCount('7'),
            day365: isDayCount('365'),
            action: isDayCount('user.created'),
        }));
        """,
    )
    assert result["day7"] is True
    assert result["day365"] is True
    assert result["action"] is False


# --- FE-ADM-07 / FE-ADM-08: preview toggle contract --------------------------


def test_preview_toggle_manages_revealing_class_and_state():
    """preview-visible is the revealing class and the state stays in sync."""
    source = _read(JS_DIR / "admin" / "editor.js")
    assert "classList.toggle('preview-visible', visible)" in source
    assert "classList.toggle('preview-hidden', !visible)" in source
    assert "togglePreviewBtn.setAttribute('aria-expanded', String(visible))" in source
    assert "'Hide Preview' : 'Show Preview'" in source

    css = _read(STATIC_DIR / "css" / "admin.css")
    assert ".editor-split.preview-hidden .markdown-preview" in css


def test_editor_stacks_the_preview_below_a_full_width_textarea():
    """The editor is a single column: the preview sits under the textarea."""
    css = _read(STATIC_DIR / "css" / "admin.css")
    split = css.split(".editor-split {", 1)[1].split("}", 1)[0]
    assert "flex-direction: column" in split
    assert "grid-template-columns" not in split
    assert ".editor-split textarea" in css
    assert "width: 100%" in css.split(".editor-split textarea {", 1)[1].split("}", 1)[0]


def test_markdown_toolbar_exposes_every_formatting_action():
    """The toolbar offers the full set of common markdown insertions."""
    html = _read(ADMIN_TEMPLATES_DIR / "_editor_body.html")
    for action in (
        "bold",
        "italic",
        "underline",
        "strikethrough",
        "code",
        "codeblock",
        "link",
        "heading",
        "quote",
        "bulletlist",
        "numberedlist",
    ):
        assert f'data-md-action="{action}"' in html
    assert 'role="toolbar"' in html

    source = _read(JS_DIR / "admin" / "markdown-toolbar.js")
    for action in (
        "bold",
        "italic",
        "underline",
        "strikethrough",
        "code",
        "codeblock",
        "link",
        "heading",
        "quote",
        "bulletlist",
        "numberedlist",
    ):
        assert f"    {action}:" in source


def test_post_editor_exposes_preview_toggle_contract(authenticated_client):
    """The post editor renders the toggle button and its state hook."""
    html = authenticated_client.get("/admin/new").get_data(as_text=True)
    assert 'id="editor-split"' in html
    assert 'id="toggle-preview-btn"' in html
    assert "toggle-preview-text" in html
    assert 'aria-controls="markdown-preview"' in html
    assert 'aria-expanded="true"' in html


def test_page_editor_exposes_preview_toggle_contract(authenticated_client):
    """The page editor exposes the same contract as the post editor."""
    html = authenticated_client.get("/admin/pages/new").get_data(as_text=True)
    assert 'id="editor-split"' in html
    assert 'id="toggle-preview-btn"' in html
    assert "toggle-preview-text" in html
    assert 'aria-controls="markdown-preview"' in html
    assert 'aria-expanded="true"' in html


def test_page_editor_attaches_the_body_error_to_the_field(authenticated_client):
    """A missing body re-renders the editor with the error wired to the field."""
    response = authenticated_client.post(
        "/admin/pages/new",
        data={"title": "", "slug": "", "body": ""},
    )

    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert 'id="body-error"' in html
    assert "Content is required." in html
    assert 'aria-describedby="body-hint body-error"' in html
    assert 'aria-invalid="true"' in html


# --- Editor undo/redo history ------------------------------------------------


def test_editor_exposes_undo_and_redo_controls(authenticated_client):
    """Both editors carry the undo and redo buttons."""
    for path in ("/admin/new", "/admin/pages/new"):
        html = authenticated_client.get(path).get_data(as_text=True)
        assert 'data-history-action="undo"' in html
        assert 'data-history-action="redo"' in html
        assert 'aria-keyshortcuts="Control+Z Meta+Z"' in html
        assert 'aria-label="Editing history"' in html


def test_editor_wires_the_history_module():
    """The editor loads the history and the toolbar marks its edits structural."""
    source = _read(JS_DIR / "admin" / "editor.js")
    assert "initEditorHistory" in source

    history = _read(JS_DIR / "admin" / "editor-history.js")
    assert "editor:structural" in history
    assert "event.preventDefault()" in history
    assert "history.undo()" in history
    assert "history.redo()" in history

    toolbar = _read(JS_DIR / "admin" / "markdown-toolbar.js")
    assert "editor:structural" in toolbar


@pytest.mark.skipif(not _node_available(), reason="node runtime is not available")
def test_editor_history_undoes_and_redoes(tmp_path):
    """The history core walks backwards and forwards through the edits."""
    result = _run_node_esm(
        tmp_path,
        """
        import { createHistory } from './admin/editor-history.js';

        let value = '';
        const history = createHistory({
            read: () => ({ value, start: 0, end: 0 }),
            write: (entry) => { value = entry.value; },
            coalesceMs: 0,
        });

        history.seed();
        const seeded = { canUndo: history.canUndo(), canRedo: history.canRedo() };

        value = 'first';
        history.record(true);
        value = 'second';
        history.record(true);

        const undone = history.undo();
        const afterUndo = value;
        const redone = history.redo();
        const afterRedo = value;

        console.log(JSON.stringify({
            seeded,
            undone,
            afterUndo,
            redone,
            afterRedo,
            canUndo: history.canUndo(),
            canRedo: history.canRedo(),
        }));
        """,
    )
    assert result["seeded"] == {"canUndo": False, "canRedo": False}
    assert result["undone"] is True
    assert result["afterUndo"] == "first"
    assert result["redone"] is True
    assert result["afterRedo"] == "second"
    assert result["canUndo"] is True
    assert result["canRedo"] is False


@pytest.mark.skipif(not _node_available(), reason="node runtime is not available")
def test_editor_history_coalesces_a_typing_burst(tmp_path):
    """Consecutive keystrokes collapse into one undo step."""
    result = _run_node_esm(
        tmp_path,
        """
        import { createHistory } from './admin/editor-history.js';

        let value = '';
        const history = createHistory({
            read: () => ({ value, start: 0, end: 0 }),
            write: (entry) => { value = entry.value; },
            coalesceMs: 60000,
        });

        history.seed();
        value = 'a';
        history.record();
        value = 'ab';
        history.record();
        history.undo();

        console.log(JSON.stringify({ value }));
        """,
    )
    assert result["value"] == ""


@pytest.mark.skipif(not _node_available(), reason="node runtime is not available")
def test_editor_history_drops_the_redo_tail_after_a_new_edit(tmp_path):
    """Editing after an undo discards the branch that was undone."""
    result = _run_node_esm(
        tmp_path,
        """
        import { createHistory } from './admin/editor-history.js';

        let value = '';
        const history = createHistory({
            read: () => ({ value, start: 0, end: 0 }),
            write: (entry) => { value = entry.value; },
            coalesceMs: 0,
        });

        history.seed();
        value = 'first';
        history.record(true);
        value = 'second';
        history.record(true);

        history.undo();
        value = 'third';
        history.record(true);

        console.log(JSON.stringify({
            value,
            canRedo: history.canRedo(),
            canUndo: history.canUndo(),
        }));
        """,
    )
    assert result["value"] == "third"
    assert result["canRedo"] is False
    assert result["canUndo"] is True


# --- FE-ADM-09 / FE-ADM-10: series reorder and remove -----------------------


@pytest.fixture
def series_with_post(db, sample_post):
    from app.models import PostSeries, Series

    series = Series(name="Test Series", slug="test-series")
    db.session.add(series)
    db.session.flush()
    link = PostSeries(series_id=series.id, post_id=sample_post.id, order_index=1)
    db.session.add(link)
    db.session.commit()
    return series


def test_series_reorder_form_has_submit_control(authenticated_client, series_with_post):
    """The reorder form can be submitted."""
    html = authenticated_client.get(f"/admin/series/{series_with_post.id}/posts").get_data(
        as_text=True
    )
    reorder_form = re.search(r"<form[^>]*id=\"series-reorder-form\".*?</form>", html, re.S)
    assert reorder_form, "reorder form is missing"
    form_html = reorder_form.group(0)
    assert re.search(r"<button[^>]*type=\"submit\"", form_html)
    assert "Save order" in form_html
    assert form_html.count('name="post_order[]"') == 1


def test_series_remove_path_carries_confirm_on_the_form(authenticated_client, series_with_post):
    """data-confirm lives on the form the shared helper binds to."""
    html = authenticated_client.get(f"/admin/series/{series_with_post.id}/posts").get_data(
        as_text=True
    )
    remove_form = re.search(r"<form[^>]*id=\"series-remove-\d+\".*?</form>", html, re.S)
    assert remove_form, "remove form is missing"
    assert "data-confirm=" in remove_form.group(0)

    remove_button = re.search(r"<button[^>]*form=\"series-remove-\d+\"[^>]*>Remove</button>", html)
    assert remove_button, "remove button is missing"
    assert "data-confirm" not in remove_button.group(0)


def test_series_reorder_submission_updates_order(authenticated_client, db, series_with_post):
    """Submitting the reorder form updates the stored order."""
    from app.models import Post, PostSeries
    from app.utils import utc_now

    second = Post(
        title="Second Post",
        slug="second-post",
        body="second",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(second)
    db.session.flush()
    link = PostSeries(series_id=series_with_post.id, post_id=second.id, order_index=2)
    db.session.add(link)
    db.session.commit()

    links = (
        db.session.execute(
            db.select(PostSeries)
            .filter_by(series_id=series_with_post.id)
            .order_by(PostSeries.order_index)
        )
        .scalars()
        .all()
    )
    reversed_ids = [str(link.id) for link in reversed(links)]

    response = authenticated_client.post(
        f"/admin/series/{series_with_post.id}/posts",
        data={"action": "reorder", "post_order[]": reversed_ids},
    )
    assert response.status_code == 302

    db.session.expire_all()
    updated = (
        db.session.execute(
            db.select(PostSeries)
            .filter_by(series_id=series_with_post.id)
            .order_by(PostSeries.order_index)
        )
        .scalars()
        .all()
    )
    assert [str(link.id) for link in updated] == reversed_ids
    assert [link.order_index for link in updated] == [1, 2]


# --- FE-ADM-11: form loading states ------------------------------------------


def test_admin_forms_declare_loading_state(authenticated_client):
    """Loading forms declare the text shown while the request is pending."""
    html = authenticated_client.get("/admin/settings").get_data(as_text=True)
    assert "data-loading" in html
    assert "data-loading-text=" in html


def test_shared_form_loading_helper_disables_submit_and_sets_text():
    """initFormLoading disables the submit button and shows the pending text."""
    source = _read(JS_DIR / "shared" / "utils.js")
    assert "export function initFormLoading()" in source
    assert "form[data-loading]" in source
    assert "submit.disabled = true" in source
    assert "form.dataset.loadingText" in source
    assert "initFormLoading();" in source


# --- FE-ADM-12: admin titles -------------------------------------------------


ADMIN_PAGE_URLS = [
    "/admin/",
    "/admin/new",
    "/admin/media",
    "/admin/settings",
    "/admin/analytics",
    "/admin/audit",
    "/admin/tags",
    "/admin/users",
    "/admin/subscribers",
    "/admin/comments",
    "/admin/pages",
    "/admin/pages/new",
    "/admin/series",
    "/admin/sessions",
    "/admin/backup",
]


def _admin_titles(client, sample_post, series) -> dict:
    urls = list(ADMIN_PAGE_URLS)
    urls.append(f"/admin/edit/{sample_post.id}")
    urls.append(f"/admin/series/{series.id}/posts")
    titles = {}
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200, f"{url} returned {response.status_code}"
        titles[url] = _title(response.get_data(as_text=True))
        assert titles[url], f"{url} rendered an empty title"
    return titles


def test_admin_pages_render_distinct_titles(authenticated_client, sample_post, series_with_post):
    """Every admin page renders its own title."""
    titles = _admin_titles(authenticated_client, sample_post, series_with_post)
    assert len(set(titles.values())) == len(titles), f"duplicate titles: {titles}"


def test_login_page_renders_its_own_title(client, admin_user, sample_post, series_with_post):
    """The login page has its own title, distinct from the admin pages."""
    from tests.conftest import TEST_PASSWORD

    response = client.get("/admin/login")
    assert response.status_code == 200
    login_title = _title(response.get_data(as_text=True))
    assert login_title

    client.post(
        "/admin/login",
        data={"username": "admin", "password": TEST_PASSWORD},
    )
    titles = _admin_titles(client, sample_post, series_with_post)
    assert login_title not in titles.values()
    assert len(set(titles.values())) == len(titles)


def test_admin_base_templates_expose_a_title_block():
    """Both admin root templates provide a working title block."""
    for name in ("base.html", "login_base.html"):
        source = _read(ADMIN_TEMPLATES_DIR / name)
        assert "{% block title %}" in source


# --- FE-ADM-13: editor draft keys --------------------------------------------


@pytest.mark.skipif(not _node_available(), reason="node runtime is not available")
def test_post_and_page_editors_use_different_draft_keys(tmp_path):
    """Draft keys are scoped by editor type."""
    result = _run_node_esm(
        tmp_path,
        """
        import { deriveDraftKey } from './admin/editor.js';
        console.log(JSON.stringify({
            postEdit: deriveDraftKey('/admin/edit/5'),
            pageEdit: deriveDraftKey('/admin/pages/edit/5'),
            postNew: deriveDraftKey('/admin/new'),
            pageNew: deriveDraftKey('/admin/pages/new'),
        }));
        """,
    )
    assert result["postEdit"] != result["pageEdit"]
    assert result["postNew"] != result["pageNew"]
    assert result["postEdit"] != result["postNew"]
    assert result["pageEdit"] != result["pageNew"]


def test_draft_key_includes_editor_type():
    """The key template keeps the editor type in scope."""
    source = _read(JS_DIR / "admin" / "editor.js")
    assert "draft-${editorType}-" in source


# --- FE-ADM-14: bulk action guards -------------------------------------------


def test_bulk_js_guards_absent_bulk_actions():
    """bulk.js must not dereference a missing actions bar."""
    source = _read(JS_DIR / "admin" / "bulk.js")
    assert re.search(r"if \(bulkActions\)\s*\{\s*bulkActions\.classList\.toggle", source), (
        "bulk actions bar is dereferenced without a null guard"
    )
    assert "getCheckboxes" in source
    assert "document.querySelectorAll('.bulk-checkbox')" in source


def test_bulk_confirm_button_keeps_its_original_text():
    """The bulk confirm button restores the label it captured."""
    source = _read(JS_DIR / "shared" / "utils.js")
    assert "delete btn.dataset.originalText" not in source
    assert "let originalText = btn.textContent;" in source
