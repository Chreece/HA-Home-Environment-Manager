"""Conditional window advice exposes every caution and the bounded device wait.

Runs the production card with mock HA data in Chromium. No devices are called.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import shutil
import time


ROOT = Path(__file__).resolve().parents[2]
BOUNDS = runpy.run_path(str(ROOT / ".github/tests/test_061b3_text_boundaries.py"))
SETUP = BOUNDS["SETUP"].replace(
    "localize:()=>undefined", "localize:key=>data.labels[key.split('.').at(-1)]")


def fixture(language):
    data = BOUNDS["fixture"](language)
    dashboard = data["states"]["sensor.hem"]["attributes"]["dashboard"]
    dashboard["outdoor"]["conditional_open"] = True
    dashboard["rooms"][0].update(
        action="open", action_window_ids=["binary_sensor.room_window"],
        windows=[{"entity_id": "binary_sensor.room_window", "name": "Window", "opened": False}],
        cautions=[{"code": "weather_cold", "value": "3 °C"},
                  {"code": "weather_wind", "value": "38 km/h"},
                  {"code": "outside_pm25", "value": "42 µg/m³"}],
        window_open_wait={"status": "window_open_wait", "expires_at": time.time() + 300,
                          "remaining_seconds": 300},
    )
    data["states"]["binary_sensor.room_window"] = {"state": "off", "attributes": {}}
    data["labels"] = json.loads((ROOT / f"translations/{language}.json").read_text(
        encoding="utf-8"))["entity"]["sensor"]["equipment_control_status"]["state"]
    return data


def run():
    from playwright.sync_api import expect, sync_playwright

    executable = os.environ.get("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert executable, "Chromium required for conditional window advice regression"
    shots = Path(os.environ["HEM_TEST_SCREENSHOT_DIR"]) if os.environ.get("HEM_TEST_SCREENSHOT_DIR") else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    icons = runpy.run_path(str(ROOT / ".github/tests/test_061b1_room_fold.py"))["icon_fixture"]()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page, language = None, "setup"
        try:
            for language in ("en", "el", "de"):
                page = browser.new_page(viewport={"width": 375, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.set_content("""<!doctype html><html><head><style>
                  *{box-sizing:border-box}body{margin:8px;background:#111;color:#eee;font-family:Arial,sans-serif;
                    --primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;
                    --card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}
                  main{width:625px;max-width:100%;margin:0 auto}home-environment-manager-card{display:block}
                  </style></head><body><main></main></body></html>""")
                page.evaluate(icons)
                page.add_script_tag(path=str(ROOT / "frontend/air-quality-advisor-card.js"))
                data = fixture(language)
                page.evaluate(SETUP, data)
                BOUNDS["settle"](page)
                outside_title = page.locator(".outside-title")
                expect(outside_title).not_to_contain_text(page.evaluate("card._t('badOutside')"))
                button = page.locator('[data-room-issue114="advice"][data-issue-area114="room0"]')
                expect(button).to_have_attribute("title", data["labels"]["window_open_wait"])
                button.click()
                panel = page.locator('[data-room-fold87="room0"] [data-room-issue-detail114="advice"]')
                expect(panel).to_be_visible()
                for value in ("3 °C", "38 km/h", "42 µg/m³", "5 min", data["labels"]["window_open_wait"]):
                    expect(panel).to_contain_text(value)
                for width in (375, 320):
                    page.set_viewport_size({"width": width, "height": 1000})
                    BOUNDS["settle"](page)
                    report = panel.evaluate("""node => {
                      const box=node.getBoundingClientRect();
                      return {left:box.left,right:box.right,viewport:innerWidth,
                        client:node.clientWidth,scroll:node.scrollWidth};
                    }""")
                    assert report["left"] >= -1 and report["right"] <= report["viewport"] + 1, report
                    assert report["scroll"] <= report["client"] + 1, report
                if shots:
                    page.screenshot(path=str(shots / f"061b5-window-advice-{language}.png"), full_page=True)
                button.click()
                expect(panel).to_have_count(0)
                fallback = page.evaluate("""() => {
                  card.hass={...card._hass,localize:()=>undefined};
                  return ['window_request_pending','window_open_wait'].map(
                    code=>card._controllerStatusLabel(code));
                }""")
                assert fallback == [data["labels"][code] for code in
                                    ("window_request_pending", "window_open_wait")], fallback
                assert page.evaluate("calls") == [], "Advice navigation must never operate equipment"
                assert not errors, errors
                page.close()
                print(f"PASS: {language} conditional cautions, localized wait and mobile advice navigation")
        except Exception:
            if page and not page.is_closed() and shots:
                page.screenshot(path=str(shots / f"061b5-window-advice-failure-{language}.png"), full_page=True)
            raise
        finally:
            browser.close()
    print("HEM_061B5_WINDOW_ADVICE_CARD=PASS")


if __name__ == "__main__":
    run()
