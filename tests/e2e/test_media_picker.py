"""Browser coverage for the shared post/page media picker."""

from __future__ import annotations

import json

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def _login(page, app_server):
    page.goto(f"{app_server}/admin/login")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "test-password-123")
    page.click('button[type="submit"]')
    page.wait_for_url("**/admin/")


def _catalog_item(category, name, url, download_url=None, mime_type="application/octet-stream"):
    return {
        "name": name,
        "display_name": name,
        "category": category,
        "size": 4096,
        "mime_type": mime_type,
        "url": url,
        "download_url": download_url,
        "mtime": None,
        "delete_url": "/admin/media/delete/unused",
    }


def test_post_media_and_attachment_pickers_insert_and_track_history(page, app_server):
    _login(page, app_server)
    image = _catalog_item(
        "image",
        "meadow.png",
        "/static/uploads/meadow.png",
        "/media/download/image-key",
        "image/png",
    )
    video = _catalog_item(
        "video", "demo.mp4", "/static/uploads/demo.mp4", "/media/download/video-key", "video/mp4"
    )
    attachment = _catalog_item("other", "notes.pdf", None, "/media/download/attachment-key")

    def catalog(route):
        requested = route.request.url.split("category=", 1)[-1].split("&", 1)[0]
        items = {
            "all": [image, video, attachment],
            "image": [image],
            "video": [video],
            "other": [attachment],
        }.get(requested, [])
        route.fulfill(
            status=200, content_type="application/json", body=json.dumps({"items": items})
        )

    page.route("**/admin/media/items*", catalog)
    page.goto(f"{app_server}/admin/new")
    page.wait_for_selector(".editor-media-trigger")
    body = page.locator("#body")
    body.fill("Alpha beta")
    body.evaluate(
        """element => {
            element.setSelectionRange(6, 10);
            window.__mediaPickerEvents = { input: 0, structural: 0 };
            element.addEventListener('input', () => window.__mediaPickerEvents.input++);
            element.addEventListener('editor:structural', () => window.__mediaPickerEvents.structural++);
        }"""
    )

    page.get_by_role("button", name="Insert media").click()
    dialog = page.get_by_role("dialog", name="Choose inline media")
    dialog.wait_for(state="visible")
    assert page.locator("[data-picker-category]").input_value() == "all"
    page.get_by_role("button", name="image: meadow.png").click()
    assert body.input_value() == "Alpha ![beta](</static/uploads/meadow.png>)"
    assert page.evaluate("window.__mediaPickerEvents") == {"input": 1, "structural": 1}
    page.locator("#markdown-preview img").wait_for(state="visible")
    assert page.url.endswith("/admin/new")
    expect(page.locator("#char-count")).not_to_have_text("0 characters")

    page.locator('[data-history-action="undo"]').click()
    assert body.input_value() == "Alpha beta"
    page.locator('[data-history-action="redo"]').click()
    assert "![beta]" in body.input_value()

    page.get_by_role("button", name="Insert media").click()
    page.locator("[data-picker-category]").select_option("video")
    page.get_by_role("button", name="video: demo.mp4").click()
    assert (
        '<video controls>\n  <source src="/static/uploads/demo.mp4" type="video/mp4">\n</video>'
        in body.input_value()
    )

    page.get_by_role("button", name="Insert attachment").click()
    page.get_by_role("dialog", name="Choose an attachment").wait_for(state="visible")
    assert page.locator("[data-picker-category]").input_value() == "other"
    page.get_by_role("button", name="other: notes.pdf").click()
    assert "[notes.pdf](</media/download/attachment-key>)" in body.input_value()

    body_value = body.input_value()
    media_trigger = page.get_by_role("button", name="Insert media")
    media_trigger.click()
    page.keyboard.press("Escape")
    assert body.input_value() == body_value
    expect(media_trigger).to_be_focused()

    page.get_by_role("button", name="Insert attachment").click()
    page.locator("[data-picker-category]").select_option("image")
    page.get_by_role("button", name="image: meadow.png").click()
    assert "[meadow.png](</media/download/image-key>)" in body.input_value()

    page.fill("#title", "Picker-created post")
    page.locator(".editor-form button[type=submit]").click()
    page.wait_for_url("**/admin/")
    expect(page.get_by_text("Post created.")).to_be_visible()


def test_page_picker_upload_errors_and_successful_save(page, app_server):
    _login(page, app_server)
    upload_requests = []
    upload_mode = {"fail": True}

    def catalog(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"items": []}))

    def upload(route):
        upload_requests.append(
            {"headers": route.request.headers, "body": route.request.post_data or ""}
        )
        if upload_mode["fail"]:
            route.fulfill(
                status=400,
                content_type="application/json",
                body=json.dumps({"error": "Rejected by the test server."}),
            )
            return
        body = route.request.post_data or ""
        if 'name="category"\r\n\r\nimage' in body:
            item = {
                "name": "0123456789abcdef0123456789abcdef.png",
                "display_name": "uploaded.png",
                "category": "image",
                "url": "/static/uploads/0123456789abcdef0123456789abcdef.png",
            }
        else:
            item = {
                "name": "0123456789abcdef0123456789abcdef-report.pdf.attachment",
                "display_name": "report.pdf",
                "category": "other",
                "url": "/media/download/0123456789abcdef0123456789abcdef-report.pdf.attachment",
            }
        route.fulfill(status=201, content_type="application/json", body=json.dumps({"item": item}))

    page.route("**/admin/media/items*", catalog)
    page.route("**/admin/media/upload", upload)
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{app_server}/admin/pages/new")
    page.locator("html").evaluate("element => element.setAttribute('data-color-scheme', 'light')")
    page.wait_for_selector(".editor-media-trigger")
    body = page.locator("#body")
    body.fill("Keep this draft")
    body.evaluate("element => element.setSelectionRange(5, 9)")

    page.get_by_role("button", name="Insert media").click()
    dialog = page.get_by_role("dialog", name="Choose inline media")
    dialog.wait_for(state="visible")
    assert page.evaluate(
        """() => {
            const rect = document.querySelector('#editor-media-picker').getBoundingClientRect();
            return rect.width <= window.innerWidth && rect.height <= window.innerHeight;
        }"""
    )
    page.get_by_role("button", name="Upload file").click()
    page.locator("[data-picker-file]").set_input_files(
        {"name": "upload.png", "mimeType": "image/png", "buffer": b"test-image"}
    )
    expect(page.get_by_text("Rejected by the test server.")).to_be_visible()
    expect(page.locator("[data-picker-upload]")).to_be_enabled()
    assert body.input_value() == "Keep this draft"
    assert dialog.is_visible()

    upload_mode["fail"] = False
    page.locator("[data-picker-file]").set_input_files(
        {"name": "upload.png", "mimeType": "image/png", "buffer": b"test-image"}
    )
    expect(body).to_have_value(
        "Keep ![this](</static/uploads/0123456789abcdef0123456789abcdef.png>) draft"
    )
    assert upload_requests[-1]["headers"].get("x-csrf-token")
    assert 'name="category"\r\n\r\nimage' in upload_requests[-1]["body"]

    page.get_by_role("button", name="Insert attachment").click()
    assert page.locator("[data-picker-category]").input_value() == "other"
    assert page.locator("[data-upload-category-group]").is_hidden()
    page.locator("[data-picker-file]").set_input_files(
        {"name": "report.pdf", "mimeType": "application/pdf", "buffer": b"%PDF"}
    )
    expect(body).to_have_value(
        "Keep ![this](</static/uploads/0123456789abcdef0123456789abcdef.png>)"
        "[report.pdf](</media/download/0123456789abcdef0123456789abcdef-report.pdf.attachment>) draft"
    )
    assert 'name="category"\r\n\r\nother' in upload_requests[-1]["body"]
    assert page.url.endswith("/admin/pages/new")

    page.fill("#title", "Picker-created page")
    page.locator(".editor-form button[type=submit]").click()
    page.wait_for_url("**/admin/pages")
    expect(page.get_by_role("link", name="Picker-created page")).to_be_visible()
