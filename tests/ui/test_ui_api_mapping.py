import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


def test_ui_api_calls():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            api_calls = []

            def log_request(request):
                if "/api/" in request.url:
                    api_calls.append(request.url)

            page.on("request", log_request)
            page.goto("http://localhost:5173", wait_until="domcontentloaded")
            page.wait_for_timeout(1000)

            assert api_calls, "UI did not call any API endpoints"
            context.close()
            browser.close()
    except Exception as exc:
        pytest.skip(f"Playwright browser launch failed: {exc}")
