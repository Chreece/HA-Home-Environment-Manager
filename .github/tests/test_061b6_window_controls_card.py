"""Operate real per-device airing controls, including two devices in one room."""
from copy import deepcopy
import os
from pathlib import Path
import runpy
import shutil

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = runpy.run_path(str(ROOT / ".github/tests/test_beta110_device_option_browser.py"))
LABELS = runpy.run_path(str(ROOT / "window_option_catalog.py"))["WINDOW_OPTION_LABELS"]


def fixture():
    states = BASE["states_for_test"]()
    for i in (0, 1):
        provenance = {"area_id": "room0", "source_device_id": f"hardware{i}",
                      "source_entity_ids": [f"climate.physical_0_{i}"]}
        states[f"switch.airing_{i}"] = {"state": "off" if i == 0 else "on",
            "attributes": {**provenance, "window_announcement_role": "policy"}}
        states[f"number.airing_{i}"] = {"state": "5" if i == 0 else "12",
            "attributes": {**provenance, "window_announcement_role": "timeout",
                           "min": 0, "max": 30, "step": 1, "unit_of_measurement": "min"}}
    return states


def run():
    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or shutil.which("chromium") or shutil.which("google-chrome")
    shots = Path(os.environ["HEM_TEST_SCREENSHOT_DIR"]) if os.environ.get("HEM_TEST_SCREENSHOT_DIR") else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    states = fixture()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 390, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content('<style>*{box-sizing:border-box}body{margin:0;background:#111;color:#eee;font:14px Arial}'
                         ':root{--primary-text-color:#eee;--secondary-text-color:#bbb;--primary-color:#03a9f4;'
                         '--card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}</style>')
        page.evaluate(BASE["PREVIOUS"]["icon_fixture"]())
        page.add_script_tag(path=str(ROOT / "frontend/air-quality-advisor-card.js"))
        page.evaluate("""states=>{
          window.calls=[]; window.card=document.createElement('home-environment-manager-card');
          document.body.appendChild(card);
          card._hass={language:'en',states,localize:()=>undefined,
            callService:(...args)=>{calls.push(args);return Promise.resolve();}};
          card._config={entity:'sensor.hem'};
          card._roomsExpanded87=new Set(['room0']);
          card._devicesExpanded87=new Set([0,1,2].map(i=>'climate.managed_0_'+i));
          window.refresh6=(s,language='en')=>{
            card._hass={...card._hass,states:structuredClone(s),language}; card._renderContent(true);
          }; refresh6(states);
        }""", states)
        def toggle(i):
            return page.locator(f'[data-window-announce-switch="switch.airing_{i}"]')
        def timeout(i):
            return page.locator(f'[data-window-wait-input="number.airing_{i}"]')
        def save(i):
            return page.locator(f'[data-save-window-wait="number.airing_{i}"]')
        assert page.locator('[data-window-announce-switch]').count() == 2
        assert timeout(0).count() == 0 and timeout(1).input_value() == "12"
        for language in ("en", "el", "de"):
            page.evaluate("([s,l])=>refresh6(s,l)", [states, language])
            assert LABELS[language][0] in toggle(0).inner_text()
            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                for box in page.locator('.hem-window-settings6').all():
                    bounds = box.evaluate("e=>({width:e.clientWidth,scroll:e.scrollWidth,left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right})")
                    assert bounds["scroll"] <= bounds["width"] + 1, (language, bounds)
                    assert bounds["left"] >= -1 and bounds["right"] <= width + 1, (language, bounds)
            if shots:
                page.locator('[data-device-fold87="climate.managed_0_1"]').screenshot(
                    path=str(shots / f"061b6-window-controls-{language}.png"), animations="disabled")
        toggle(0).click()
        page.wait_for_function("calls.length===1")
        assert page.evaluate("calls") == [["switch", "turn_on", {"entity_id": "switch.airing_0"}]]
        updated = deepcopy(states)
        updated["switch.airing_0"]["state"] = "on"
        page.evaluate("s=>refresh6(s)", updated)
        timeout(0).fill("31")
        save(0).click()
        assert page.evaluate("calls.length") == 1
        timeout(0).fill("0")
        save(0).click()
        page.wait_for_function("calls.length===2")
        assert page.evaluate("calls[1]") == ["number", "set_value", {"entity_id": "number.airing_0", "value": 0}]
        timeout(1).fill("7")
        save(1).click()
        page.wait_for_function("calls.length===3")
        assert page.evaluate("calls[2]") == ["number", "set_value", {"entity_id": "number.airing_1", "value": 7}]
        # Forging another device's data attribute must not send any service.
        save(0).evaluate("e=>{e.dataset.saveWindowWait='number.airing_1';e.click();}")
        assert page.evaluate("calls.length") == 3
        updated["climate.physical_0_0"]["state"] = "unavailable"
        updated["climate.managed_0_0"]["state"] = "unavailable"
        page.evaluate("s=>refresh6(s)", updated)
        assert toggle(0).is_enabled() and timeout(0).is_enabled()
        updated["switch.airing_0"]["state"] = "off"
        page.evaluate("s=>refresh6(s)", updated)
        assert timeout(0).count() == 0 and timeout(1).count() == 1
        updated["switch.duplicate"] = deepcopy(updated["switch.airing_0"])
        page.evaluate("s=>refresh6(s)", updated)
        assert toggle(0).count() == 0 and toggle(1).count() == 1
        assert not errors, errors
        browser.close()
    print("HEM_061B6_SCOPED_DEVICE_WINDOW_CONTROLS=PASS")


if __name__ == "__main__":
    run()
