from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

import pytest

DIST_DIR = Path(__file__).resolve().parents[2] / "app" / "static" / "dist"
MANIFEST_PATH = DIST_DIR / ".vite" / "manifest.json"
requires_frontend_build = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="frontend bundle not built (run `npm run build`)",
)


@requires_frontend_build
def test_ai_suggestions_require_review_and_merge_tags(browser, app_server, app) -> None:
    from app.config.model import AiConfig

    typed_config = app.config["DEVLOG_CONFIG"]
    app.config["DEVLOG_CONFIG"] = replace(
        typed_config,
        ai=AiConfig(api_key="e2e-only-not-a-real-provider-key"),
    )
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    requests: list[dict] = []
    response_mode = {"error": False}
    try:
        page.goto(f"{app_server}/admin/login")
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "test-password-123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/admin/")

        def fulfill_suggestion(route):
            requests.append(
                {
                    "payload": route.request.post_data_json,
                    "headers": route.request.headers,
                }
            )
            if response_mode["error"]:
                route.fulfill(
                    status=502,
                    content_type="application/json",
                    body=json.dumps({"error": "The AI service is temporarily unavailable."}),
                )
                return
            if requests[-1]["payload"]["action"] == "summary":
                result = {"suggestion": "A concise factual summary."}
            else:
                result = {
                    "suggestions": ["Python", "Flask", "Web Security"],
                    "reused": ["Python"],
                    "new": ["Flask", "Web Security"],
                }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(result))

        page.route("**/admin/ai-assist", fulfill_suggestion)
        page.goto(f"{app_server}/admin/new")
        page.evaluate(
            """() => localStorage.setItem('draft-post-new', JSON.stringify({
                title: 'Restored title', body: 'Restored body', summary: 'Restored summary',
                tags: 'Restored tag', timestamp: Date.now()
            }))"""
        )
        page.once("dialog", lambda dialog: dialog.accept())
        page.reload()
        assert page.locator("#tags").input_value() == "Restored tag"
        page.fill("#title", "Current unsaved headline")
        page.fill("#body", "Current unsaved Markdown body.")
        page.fill("#summary", "Hand-written summary")
        page.fill("#tags", "Python, manually-added")

        page.get_by_role("button", name="Suggest TL;DR").click()
        page.get_by_text("Suggestion: A concise factual summary.").wait_for()
        assert page.locator("#summary").input_value() == "Hand-written summary"
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.get_by_role("button", name="Use this summary").click()
        assert page.locator("#summary").input_value() == "Hand-written summary"
        page.get_by_role("button", name="Suggest TL;DR").click()
        page.get_by_text("Suggestion: A concise factual summary.").wait_for()
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Use this summary").click()
        assert page.locator("#summary").input_value() == "A concise factual summary."

        page.emulate_media(color_scheme="dark")
        page.get_by_role("button", name="Suggest tags").click()
        page.get_by_text("Suggestions: Python, Flask, Web Security.").wait_for()
        assert page.locator("#tags").input_value() == "Python, manually-added"
        page.get_by_role("button", name="Add these tags").click()
        assert page.locator("#tags").input_value() == "Python, manually-added, Flask, Web Security"

        page.evaluate(
            """() => {
                const nativeFetch = window.fetch.bind(window);
                window.fetch = (...args) => new Promise((resolve, reject) => {
                    window.setTimeout(() => nativeFetch(...args).then(resolve, reject), 300);
                });
            }"""
        )
        page.get_by_role("button", name="Suggest TL;DR").click()
        page.fill("#title", "A newer title entered during inference")
        page.get_by_text("Suggestion: A concise factual summary.").wait_for()
        page.get_by_role("button", name="Use this summary").click()
        assert "draft changed" in page.locator("#ai-summary-result").inner_text().lower()
        assert page.locator("#title").input_value() == "A newer title entered during inference"
        assert page.locator("#summary").input_value() == "A concise factual summary."

        response_mode["error"] = True
        page.get_by_role("button", name="Suggest TL;DR").click()
        page.get_by_text("The AI service is temporarily unavailable.").wait_for()
        assert page.locator("#title").input_value() == "A newer title entered during inference"
        assert page.locator("#summary").input_value() == "A concise factual summary."
        deadline = time.monotonic() + 7
        stored_draft = page.evaluate("localStorage.getItem('draft-post-new')")
        while time.monotonic() < deadline:
            if (
                json.loads(stored_draft or "{}").get("tags")
                == "Python, manually-added, Flask, Web Security"
            ):
                break
            page.wait_for_timeout(100)
            stored_draft = page.evaluate("localStorage.getItem('draft-post-new')")
        assert json.loads(stored_draft or "{}").get("tags") == (
            "Python, manually-added, Flask, Web Security"
        )
        assert "test-private-key" not in stored_draft
        beforeunload_dialogs: list[str] = []

        def dismiss_beforeunload(dialog):
            beforeunload_dialogs.append(dialog.type)
            dialog.dismiss()

        page.on("dialog", dismiss_beforeunload)
        from playwright.sync_api import Error as PlaywrightError

        with pytest.raises(PlaywrightError, match="ERR_ABORTED"):
            page.goto(f"{app_server}/admin/pages/new")
        assert "beforeunload" in beforeunload_dialogs
        assert page.url.endswith("/admin/new")
        assert len(requests) == 5
        assert requests[0]["payload"]["title"] == "Current unsaved headline"
        assert requests[0]["payload"]["body"] == "Current unsaved Markdown body."
        assert requests[3]["payload"]["title"] == "Current unsaved headline"
        assert "x-csrf-token" in requests[0]["headers"]
        assert "e2e-only-not-a-real-provider-key" not in str(requests[0])
        assert page.locator("#autosave-status").count() == 1
    finally:
        app.config["DEVLOG_CONFIG"] = typed_config
        context.close()
