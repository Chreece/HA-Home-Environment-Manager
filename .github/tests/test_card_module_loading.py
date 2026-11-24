"""Exercise HA's custom-element wait with real module failures and an app resume."""
from __future__ import annotations

from pathlib import Path
import shutil
import sys
from time import monotonic
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright

FRONTEND = Path(__file__).resolve().parents[2] / "custom_components/environment_manager/frontend"
TAG = "home-environment-manager-card"
CARD = TAG + ".js"
LOADER = "home-environment-manager-loader.js"
ORIGIN = "https://hem.test"
# Model the Lovelace two-second error and its whenDefined-driven rebuild.
HTML = """<!doctype html><main></main><script>
const tag = 'home-environment-manager-card';
const root = document.querySelector('main');
const timeout = setTimeout(() => {root.textContent = "Custom element doesn't exist"}, 2000);
customElements.whenDefined(tag).then(() => {
  clearTimeout(timeout);
  const card = document.createElement(tag);
  card.setConfig({type:'custom:' + tag});
  root.replaceChildren(card);
});
</script><script type="module" src="/environment_manager/RESOURCE?v=fixture"></script>"""


def exercise(browser, resource, failures, *, resume=False, reported_offline=False):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    if reported_offline:
        page.add_init_script("Object.defineProperty(navigator, 'onLine', {get: () => false})")
    urls = []
    documents = []
    held = []
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def route(request):
        url = urlsplit(request.request.url)
        if url.path == "/dashboard":
            documents.append(url.path)
            request.fulfill(content_type="text/html", body=HTML.replace("RESOURCE", resource))
        elif url.path == "/environment_manager/" + LOADER:
            request.fulfill(content_type="text/javascript", path=FRONTEND / LOADER)
        elif url.path == "/environment_manager/" + CARD:
            urls.append(parse_qs(url.query))
            if len(urls) <= failures:
                request.fulfill(status=503, content_type="text/plain", body="Offline")
            else:
                held.append(request)
        else:
            request.fulfill(status=404)

    page.route(ORIGIN + "/**", route)
    try:
        page.goto(ORIGIN + "/dashboard", wait_until="commit")
        if resource == CARD:
            expect(page.locator("main")).to_have_text("Custom element doesn't exist")
            page.evaluate("window.dispatchEvent(new Event('online'))")
            assert len(urls) == 1 and not held
            assert not page.evaluate("!!customElements.get('home-environment-manager-card')")
            return
        if resume:
            # Allow the three automatic retries to finish. The app stays on this page.
            message = page.expect_console_message(predicate=lambda msg: "Waiting for the app" in msg.text,
                                                  timeout=20_000)
            with message:
                expect(page.locator("main")).to_have_text("Custom element doesn't exist")
            assert len(urls) == 4
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}))")
        deadline = monotonic() + 8
        while not held and monotonic() < deadline:
            page.wait_for_timeout(30)
        assert len(held) == 1
        expect(page.locator("main")).to_have_text("Custom element doesn't exist")
        page.evaluate("""() => {
          window.dispatchEvent(new Event('online'));
          window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}));
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        held[0].fulfill(content_type="text/javascript", path=FRONTEND / CARD)
        expect(page.locator("main > " + TAG)).to_have_count(1)
        assert page.evaluate("!!customElements.get('home-environment-manager-card-editor')")
        assert page.evaluate("customCards.filter(c=>c.type==='home-environment-manager-card').length") == 1
        assert len(urls) == failures + 1
        assert all(query.get("v") == ["fixture"] for query in urls)
        assert [q.get("hem_retry") for q in urls] == [None] + [[str(i)] for i in range(1, len(urls))]
        assert documents == ["/dashboard"] and not errors, (documents, errors)
    finally:
        page.close()


def run(engine):
    with sync_playwright() as playwright:
        options = {"executable_path": shutil.which("chromium") or shutil.which("google-chrome")} if engine == "chromium" else {}
        with getattr(playwright, engine).launch(**options) as browser:
            exercise(browser, CARD, 1)
            exercise(browser, LOADER, 0, reported_offline=True)
            exercise(browser, LOADER, 1)
            exercise(browser, LOADER, 4, resume=True)
    print(f"PASS {engine}: cold-load failure, delayed download, automatic retry and foreground recovery")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "chromium")
