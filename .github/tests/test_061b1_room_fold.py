"""0.6.1b1: keep one right-side room chevron throughout real browser toggles.

Use the production card, its actual click handlers and HA render scheduler.
All HA transport is local fixture data; no physical device is contacted.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import runpy
import shutil

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"


def icon_fixture():
    """Reuse the existing HA icon geometry stand-in without running its tests."""
    path = ROOT / ".github/tests/test_beta107_room_metrics.py"
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "ICON_FIXTURE"
            for target in node.targets
        ):
            script = ast.literal_eval(node.value)
            return script.replace("const glyphs = {", """const glyphs = {
              'mdi:cog-outline':'<path d="m9 3-.5 2.5-2 1.2-2.4-.8-2.4 4.2L3.5 12l-1.8 1.9 2.4 4.2 2.4-.8 2 1.2L9 21h6l.5-2.5 2-1.2 2.4.8 2.4-4.2-1.8-1.9 1.8-1.9-2.4-4.2-2.4.8-2-1.2L15 3Z"/><circle cx="12" cy="12" r="3"/>',""")
    raise AssertionError("The HA icon geometry fixture is missing")


SETUP = """data => {
  window.calls=[];window.settings=[];window.info=[];window.ws=[];
  window.card=document.createElement('home-environment-manager-card');
  document.body.append(card);
  card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
  // Check the existing exact-area routing without starting an options flow.
  card._openRoomSettings114=area=>settings.push(area);
  const callWS=async request=>{
    ws.push(request);
    if(request.type==='config/device_registry/list')return [
      {id:'hem-home-device',identifiers:[['environment_manager','entry']]},
      {id:'hem-room-device',identifiers:[['environment_manager','entry_area_living']]}
    ];
    if(request.type==='history/history_during_period'){
      const now=Date.now()/1000;
      return {[request.entity_ids[0]]:[{s:'1590',lu:now-120},{s:'1600',lu:now-60}]};
    }
    throw Error('Unexpected mocked HA request: '+request.type);
  };
  card.setConfig({entity:'sensor.hem'});
  card.hass={language:'en',states:data.states,entities:{
      ...data.entities,'sensor.hem':{device_id:'hem-home-device'}},
    user:{is_admin:true},connection:{},config:{time_zone:'UTC'},
    localize:()=>undefined,callWS,
    callService:(...args)=>{calls.push(args);return Promise.resolve();}};
  window.headerState061b1=(kind='room')=>{
    const summary=card.shadowRoot.querySelector(kind==='room'
      ?'[data-room-fold87="living"] > summary'
      :'[data-device-fold87="climate.hem_heater"] > summary');
    const chevron=summary.querySelector(':scope > ha-icon:last-child');
    const settings=summary.querySelector(kind==='room'
      ?'[data-room-settings114] ha-icon':'[data-open-controller-device122] ha-icon');
    const rect=node=>{
      const box=node.getBoundingClientRect();
      return {left:box.left,right:box.right,width:box.width};
    };
    const style=getComputedStyle(summary);
    return {
      open:summary.parentElement.open,
      settings:settings?.getAttribute('icon'),
      chevrons:[...summary.querySelectorAll(
        'ha-icon[icon="mdi:chevron-up"],ha-icon[icon="mdi:chevron-down"]')]
        .map(node=>node.getAttribute('icon')),
      trailing:chevron===summary.lastElementChild,
      direct:chevron?.getAttribute('icon'),
      nested:[...summary.querySelectorAll('ha-icon')]
        .filter(node=>node!==chevron).map(node=>node.getAttribute('icon')),
      display:style.display,listStyle:style.listStyleType,
      header:rect(summary),arrow:chevron?rect(chevron):null,viewport:innerWidth,
      rendered:card._lastState===card._hass.states['sensor.hem']
    };
  };
  window.refresh061b1=()=>{
    const current=card._hass.states['sensor.hem'];
    card.hass={...card._hass,states:{...card._hass.states,
      'sensor.hem':{...current,attributes:{...current.attributes,
        dashboard_revision:(current.attributes.dashboard_revision||0)+1}}}};
  };
}"""


def assert_header(report, *, opened, nested):
    assert report["open"] is opened, report
    assert report["settings"] == "mdi:cog-outline", report
    expected = "mdi:chevron-up" if opened else "mdi:chevron-down"
    assert report["chevrons"] == [expected], report
    assert report["trailing"] and report["direct"] == expected, report
    assert report["nested"] == nested, ("Independent header icons changed", report)
    assert report["display"] == "flex" and report["listStyle"] == "none", report
    arrow, header = report["arrow"], report["header"]
    assert arrow and arrow["width"] > 0, report
    assert arrow["left"] >= header["left"] + header["width"] / 2, report
    assert -1 <= header["right"] - arrow["right"] <= 12, report
    assert arrow["right"] <= report["viewport"] + 1, report


def run():
    data = runpy.run_path(str(ROOT / ".github/tests/test_beta122_card_details.py"))["fixture"]()
    # Keep a real warning and controller in the header while focusing this
    # regression on folding; the full four-metric layouts have their own gate.
    data["room"]["readings"] = [reading for reading in data["room"]["readings"]
                                if reading["metric"] in ("temperature", "humidity", "co2")]
    executable = os.environ.get("CHROME_BIN") or os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    executable = executable or shutil.which("chromium") or shutil.which("google-chrome")
    assert executable, "Chromium is required for the room-fold regression"
    shots = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
    shots = Path(shots) if shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 1024, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.set_content("""<!doctype html><html><head><style>
              *{box-sizing:border-box}body{margin:8px;background:#101820;color:#e8edf3;font-family:Arial}
              :root{--primary-text-color:#e8edf3;--secondary-text-color:#aebbc8;
                --card-background-color:#18212b;--secondary-background-color:#22303d;--divider-color:#455463}
              home-environment-manager-card{max-width:760px;margin:0 auto}
              </style></head><body></body></html>""")
            page.evaluate(icon_fixture())
            page.add_script_tag(path=str(CARD))
            page.evaluate(SETUP, data)
            room = page.locator('[data-room-fold87="living"]')
            summary = room.locator(":scope > summary")
            expect(summary.locator("[data-room-settings114]")).to_be_enabled()
            page.wait_for_function("card._frameHandle68 == null")
            for width, label in ((1024, "desktop"), (375, "mobile"), (320, "narrow")):
                page.set_viewport_size({"width": width, "height": 1000})
                page.evaluate("card._renderContent(true)")
                initial = page.evaluate("headerState061b1()")
                nested = initial["nested"]
                assert_header(initial, opened=False, nested=nested)

                # Each snapshot is taken in the click's JS turn, before an HA
                # render can conceal an accidentally rewritten settings icon.
                for selector, opened in ((".hem-room-name87", True), (":scope > ha-icon:last-child", False)):
                    report = summary.locator(selector).evaluate(
                        "node=>{node.click();return headerState061b1()}")
                    assert_header(report, opened=opened, nested=nested)

                # Alternate name/chevron activation with real hass-setter
                # updates, checking before and after every scheduled render.
                reports = page.evaluate("""async ()=>{
                  const reports=[];
                  for(let i=0;i<8;i++){
                    const summary=card.shadowRoot.querySelector('[data-room-fold87="living"] > summary');
                    summary.querySelector(i%2?':scope > ha-icon:last-child':'.hem-room-name87').click();
                    reports.push({phase:'click',...headerState061b1()});
                    refresh061b1();
                    reports.push({phase:'queued',...headerState061b1()});
                    await new Promise(requestAnimationFrame);
                    reports.push({phase:'rendered',...headerState061b1()});
                  }
                  return reports;
                }""")
                for index, report in enumerate(reports):
                    assert_header(report, opened=(index // 3) % 2 == 0, nested=nested)
                    if report["phase"] == "rendered":
                        assert report["rendered"], report

                # Native keyboard activation still toggles only the room.
                summary.focus()
                page.keyboard.press("Enter")
                assert_header(page.evaluate("headerState061b1()"), opened=True, nested=nested)
                page.keyboard.press("Space")
                assert_header(page.evaluate("headerState061b1()"), opened=False, nested=nested)

                # Independent header actions retain their destinations and
                # must not toggle the room or replace their own icons.
                prior_settings = page.evaluate("settings.length")
                summary.locator("[data-room-settings114]").click()
                assert page.evaluate("settings.slice(-1)") == ["living"]
                assert page.evaluate("settings.length") == prior_settings + 1
                assert_header(page.evaluate("headerState061b1()"), opened=False, nested=nested)
                summary.locator('[data-hem-source105="sensor.co2"]').click()
                popup = page.locator(".hem-avg-dialog105")
                expect(popup).to_be_visible()
                assert page.evaluate("card._averageDialog105.entity122") == "sensor.co2"
                assert_header(page.evaluate("headerState061b1()"), opened=False, nested=nested)
                popup.locator('[data-open-entity122="sensor.co2"]').click()
                assert page.evaluate("info.at(-1)") == "sensor.co2"
                page.keyboard.press("Escape")
                expect(popup).to_have_count(0)
                assert_header(page.evaluate("headerState061b1()"), opened=False, nested=nested)
                if shots:
                    page.screenshot(path=str(shots / f"061b1-room-fold-{label}-closed.png"), full_page=True)

                summary.locator(".hem-room-name87").click()
                assert_header(page.evaluate("headerState061b1()"), opened=True, nested=nested)
                controller = room.locator('[data-device-fold87="climate.hem_heater"] > summary')
                controller_initial = page.evaluate("headerState061b1('controller')")
                for opened in (True, False):
                    report = controller.locator(":scope > ha-icon:last-child").evaluate(
                        "node=>{node.click();return headerState061b1('controller')}")
                    assert_header(report, opened=opened, nested=controller_initial["nested"])
                assert_header(page.evaluate("headerState061b1()"), opened=True, nested=nested)
                if shots:
                    page.screenshot(path=str(shots / f"061b1-room-fold-{label}-open.png"), full_page=True)
                summary.locator(".hem-room-name87").click()
                assert_header(page.evaluate("headerState061b1()"), opened=False, nested=nested)
            assert page.evaluate("calls") == []
            assert not errors, errors
        except Exception:
            if shots:
                try:
                    page.screenshot(path=str(shots / "061b1-room-fold-failure.png"), full_page=True)
                    (shots / "061b1-room-fold-failure.json").write_text(
                        json.dumps(page.evaluate("typeof headerState061b1==='function' ? headerState061b1() : {}"),
                                   indent=2), encoding="utf-8")
                except Exception as capture_error:
                    print(f"Could not capture room-fold failure: {capture_error}")
            raise
        finally:
            browser.close()
    print("061B1_ROOM_FOLD_SINGLE_RIGHT_CHEVRON_RAPID_HA_UPDATES_AND_MOBILE=PASS")


if __name__ == "__main__":
    run()
