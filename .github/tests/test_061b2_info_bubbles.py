"""0.6.1b2: readable room information and owned outside-click dismissal.

Runs the production card with Greek HA fixture data, real shadow DOM events,
portal content, live hass refreshes and mobile viewports. Service and history
transport are local fixtures; no physical device or remote HA is contacted.
--logic-only runs the lifecycle/cleanup checks without launching Chromium.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
ROOM_KEY = "room-info:living"
DEVICE_KEY = "device-info:climate.hem_heater"
HELP_KEY = "setting-help:select.hem_method"
HELP_TEXT = "Χωρίς έλεγχο παρουσίας: συνεχίζει κανονικά.\nΠαρουσία: λειτουργεί όταν υπάρχει κάποιος.\nΑπουσία: λειτουργεί όταν ο χώρος είναι άδειος."


def fixture():
    data = runpy.run_path(str(ROOT / ".github/tests/test_beta122_card_details.py"))["fixture"]()
    data["room"]["name"] = "Μπάνιο"
    plan = data["room"]["environment"]["climate_plan"]
    plan["coordination"] = {"priority": "hold_or_no_demand"}
    plan["reason"] = "environment_only_no_hvac"
    plan["equipment_plan"]["humidity"]["measured_rh"] = 56.2
    data["states"]["select.hem_method"]["attributes"]["configuration_help"] = HELP_TEXT
    # Keep the test data explicitly JSON serializable, as real HA state is.
    return json.loads(json.dumps(data, ensure_ascii=False))


SETUP = r"""data => {
  window.calls=[];window.info=[];window.requests=[];
  // Count owned capture listeners by identity, including replacements during
  // live render. Detect leaks across close, detach and reconnection.
  window.captureListeners061b2={click:new Set(),keydown:new Set()};
  const add=document.addEventListener,remove=document.removeEventListener;
  document.addEventListener=function(type,listener,options){
    if(options===true&&captureListeners061b2[type])captureListeners061b2[type].add(listener);
    return add.call(this,type,listener,options);
  };
  document.removeEventListener=function(type,listener,options){
    if(options===true&&captureListeners061b2[type])captureListeners061b2[type].delete(listener);
    return remove.call(this,type,listener,options);
  };
  window.card=document.createElement('home-environment-manager-card');
  document.body.append(card);
  card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
  const callWS=async request=>{
    requests.push(request);
    if(request.type==='config/device_registry/list')return [];
    if(request.type==='history/history_during_period'){
      const now=Date.now()/1000;
      return {[request.entity_ids[0]]:[{s:'1500',lu:now-120},{s:'1600',lu:now-60}]};
    }
    throw Error('Unexpected mocked HA request: '+request.type);
  };
  card.setConfig({entity:'sensor.hem'});
  card.hass={language:'el',states:data.states,entities:data.entities,
    localize:()=>undefined,callWS,config:{time_zone:'UTC'},connection:{},
    callService:(...args)=>{calls.push(args);return Promise.resolve();}};
  window.refresh061b2=(humidity)=>{
    const states=structuredClone(card._hass.states);
    const state=states['sensor.hem'];
    state.attributes.dashboard_revision=(state.attributes.dashboard_revision||0)+1;
    if(humidity!==undefined)state.attributes.dashboard.rooms[0].environment.climate_plan
      .equipment_plan.humidity.measured_rh=humidity;
    card.hass={...card._hass,states};
  };
  window.bubbleState061b2=key=>{
    const source=[...card.shadowRoot.querySelectorAll('details')]
      .find(node=>node.getAttribute('data-detail-id')===key);
    return {open:Boolean(source?.open),saved:card._detailsExpanded66?.has(key)||false,
      popup:Boolean(card._floatingInfo87),
      listeners:Object.fromEntries(Object.entries(captureListeners061b2).map(([type,set])=>[type,set.size]))};
  };
  window.diagnostics061b2=()=>{
    const pop=card._floatingInfo87,source=pop?._hemInfoSource87;
    const roomInfo=card.shadowRoot.querySelector('[data-detail-id="room-info:living"]');
    const state=card._hass.states['sensor.hem'];
    const humidity=state.attributes.dashboard.rooms[0].environment.climate_plan
      .equipment_plan.humidity.measured_rh;
    return {language:card._hass.language,humidity,formattedHumidity:card._format(humidity),
      renderedCurrentState:card._lastState===state,stableUpdates:card._stableDomUpdates91,
      pendingRender:card._pendingRender,pendingForce:card._pendingForceRender,
      pendingFrame:card._frameHandle68,detailPointer:card._detailPointer66,
      focusedEditor:card._focusedEditor?.outerHTML||null,
      roomInfoOpen:roomInfo?.open,roomInfoText:roomInfo?.textContent,
      popupConnected:pop?.isConnected||false,popupText:pop?.textContent||null,
      popupNodes:[...card.shadowRoot.querySelectorAll('.hem-floating-info87')].map(node=>({
        active:node===pop,connected:node.isConnected,popover:node.getAttribute('popover'),
        sourceKey:node._hemInfoKey87,text:node.textContent})),
      popupKey:pop?._hemInfoKey87,sourceKey:source?.getAttribute('data-detail-id'),
      sourceConnected:source?.isConnected,sourceOpen:source?.open,sourceText:source?.textContent,
      savedDetails:[...(card._detailsExpanded66||[])],roomIssueInfo:card._roomIssueInfo114,
      listeners:Object.fromEntries(Object.entries(captureListeners061b2).map(([type,set])=>[type,set.size])),
      calls,info};
  };
}"""


def settle(page):
    page.evaluate("async()=>{await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));}")


def assert_listeners(page, count):
    assert page.evaluate("Object.fromEntries(Object.entries(captureListeners061b2).map(([type,set])=>[type,set.size]))") == {
        "click": count, "keydown": count,
    }
    # Inspect the shadow root directly, including while its host is detached.
    assert page.evaluate("card.shadowRoot.querySelectorAll('.hem-floating-info87').length") == count, "Unexpected floating popup node count"


def assert_closed(page, key):
    page.wait_for_function("key=>!card._floatingInfo87&&!bubbleState061b2(key).open", arg=key)
    settle(page)
    assert_listeners(page, 0)
    assert page.evaluate("key=>bubbleState061b2(key)", key) == {
        "open": False, "saved": False, "popup": False,
        "listeners": {"click": 0, "keydown": 0},
    }
    # A new HA frame and an explicit full render must both respect dismissal.
    page.evaluate("refresh061b2()")
    page.wait_for_function("card._lastState===card._hass.states['sensor.hem']")
    page.evaluate("card._renderContent(true)")
    settle(page)
    assert not page.evaluate("key=>bubbleState061b2(key).popup||bubbleState061b2(key).open||bubbleState061b2(key).saved", key)
    assert_listeners(page, 0)


def open_bubble(page, key):
    source = page.locator(f'details[data-detail-id="{key}"]')
    source.locator(":scope > summary").click()
    page.wait_for_function("key=>card._floatingInfo87?._hemInfoSource87?.getAttribute('data-detail-id')===key", arg=key)
    assert source.get_attribute("open") is not None
    assert page.locator(".hem-floating-info87").is_visible()
    assert_listeners(page, 1)
    return page.locator(".hem-floating-info87")


def assert_multiline(page):
    lines = page.locator(".hem-floating-info87 > small").evaluate_all("""nodes=>nodes.map(node=>{
      const rect=node.getBoundingClientRect();return {text:node.textContent,display:getComputedStyle(node).display,
        top:rect.top,bottom:rect.bottom};})""")
    assert len(lines) >= 3, lines
    assert "Προτεραιότητα" in lines[0]["text"], lines
    assert any("υγρασίας" in line["text"].lower() for line in lines), lines
    assert any("Σύνοψη δωματίου" in line["text"] for line in lines), lines
    assert all(line["display"] == "block" for line in lines), lines
    for previous, current in zip(lines, lines[1:]):
        assert current["top"] >= previous["bottom"], lines
    rect = page.locator(".hem-floating-info87").bounding_box()
    size = page.viewport_size
    assert rect and rect["x"] >= 0 and rect["x"] + rect["width"] <= size["width"] + 1, rect
    assert rect["y"] >= 0 and rect["y"] + rect["height"] <= size["height"] + 1, rect
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")


def browser_checks(data):
    from playwright.sync_api import expect, sync_playwright
    executable = os.environ.get("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert executable, "Chromium required for 0.6.1b2 information bubble checks"
    output = Path(os.environ["HEM_TEST_SCREENSHOT_DIR"]) if os.environ.get("HEM_TEST_SCREENSHOT_DIR") else None
    if output:
        output.mkdir(parents=True, exist_ok=True)
    icons = runpy.run_path(str(ROOT / ".github/tests/test_061b1_room_fold.py"))["icon_fixture"]()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = None
        try:
            for width, label in ((1024, "desktop"), (375, "mobile"), (320, "narrow")):
                page = browser.new_page(viewport={"width": width, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.set_content("""<!doctype html><html><head><style>
                  *{box-sizing:border-box}body{margin:8px;background:#101820;color:#e8edf3;font-family:Arial;
                    --primary-text-color:#e8edf3;--secondary-text-color:#aebdcd;--primary-color:#60aaff;
                    --card-background-color:#18212b;--secondary-background-color:#22303d;--divider-color:#455463}
                  home-environment-manager-card{display:block;max-width:760px;margin:56px auto 0}
                  #outside{position:fixed;z-index:1;top:8px;left:8px;padding:7px 10px}
                  </style></head><body><button id="outside">Outside card</button></body></html>""")
                page.evaluate(icons)
                page.add_script_tag(path=str(CARD))
                page.evaluate(SETUP, data)
                room = page.locator('[data-room-fold87="living"]')
                # Headers also contain history/settings buttons. Use the
                # visible fold arrow, not the compound header's center.
                room.locator(":scope > summary > ha-icon:last-child").click()
                expect(room).to_have_attribute("open", "")
                assert page.evaluate("info") == []
                bubble = open_bubble(page, ROOM_KEY)
                assert_multiline(page)
                if output:
                    page.screenshot(path=str(output / f"061b2-greek-room-info-{label}.png"), full_page=True)
                # Document capture sees a retargeted card host; composedPath
                # must preserve a click in the floating portal's own text.
                bubble.locator("small").first.click()
                expect(bubble).to_be_visible()
                # Refresh an open bubble in place with genuinely changed data.
                page.evaluate("window.popupBeforeRefresh061b2=card._floatingInfo87;refresh061b2(57.4)")
                page.wait_for_function("card._lastState===card._hass.states['sensor.hem']")
                page.wait_for_function("card.shadowRoot.querySelector('[data-detail-id=\"room-info:living\"]')?.textContent.includes('57,4')")
                page.wait_for_function("card._floatingInfo87?.textContent.includes('57,4')")
                assert page.evaluate("card._floatingInfo87===popupBeforeRefresh061b2"), "Live refresh replaced the open portal"
                assert_multiline(page)
                assert_listeners(page, 1)
                # Inside the card, outside the popup: close without any action.
                page.locator(".card-heading h2").click()
                assert_closed(page, ROOM_KEY)
                # Outside the host entirely, including after repeated reopens.
                for _ in range(2):
                    open_bubble(page, ROOM_KEY)
                    page.locator("#outside").click()
                    assert_closed(page, ROOM_KEY)
                # Trigger click and Escape each close once; first press reopens.
                open_bubble(page, ROOM_KEY)
                page.locator(f'[data-detail-id="{ROOM_KEY}"] > summary').click()
                assert_closed(page, ROOM_KEY)
                open_bubble(page, ROOM_KEY)
                page.keyboard.press("Escape")
                assert_closed(page, ROOM_KEY)
                # Device and setting help use the same portal/dismissal path.
                device = room.locator('[data-device-fold87="climate.hem_heater"]')
                device.locator(":scope > summary > ha-icon:last-child").click()
                expect(device).to_have_attribute("open", "")
                assert page.evaluate("info") == []
                open_bubble(page, DEVICE_KEY)
                page.locator("#outside").click()
                assert_closed(page, DEVICE_KEY)
                bubble = open_bubble(page, HELP_KEY)
                help_text = bubble.locator(".hem-help-text116")
                assert help_text.text_content() == HELP_TEXT
                assert help_text.evaluate("node=>getComputedStyle(node).whiteSpace") == "pre-line"
                help_text.click()
                expect(bubble).to_be_visible()
                if output:
                    page.screenshot(path=str(output / f"061b2-greek-setting-help-{label}.png"), full_page=True)
                page.locator("#outside").click()
                assert_closed(page, HELP_KEY)
                # Metric help has no saved disclosure key. Its own open
                # state must close and stay closed across reconciliation.
                # Elevated CO2 is in the first four complementary tiles;
                # opening this room exposes it without the More control.
                metric = room.locator('[data-overview-detail122="co2"] details.metric-help')
                expect(room).to_have_attribute("open", "")
                expect(metric.locator(":scope > summary")).to_be_visible()
                metric.locator(":scope > summary").click()
                page.wait_for_function("Boolean(card._floatingInfo87)")
                page.locator(".hem-floating-info87").click()
                expect(page.locator(".hem-floating-info87")).to_be_visible()
                page.locator("#outside").click()
                page.wait_for_function("!card._floatingInfo87")
                expect(metric).not_to_have_attribute("open", "")
                assert_listeners(page, 0)
                page.evaluate("refresh061b2()")
                page.wait_for_function("card._lastState===card._hass.states['sensor.hem']")
                page.evaluate("card._renderContent(true)")
                settle(page)
                expect(metric).not_to_have_attribute("open", "")
                assert not page.evaluate("Boolean(card._floatingInfo87)")
                # This persistent sensor history is a separate dialog. Outside
                # clicks must not be reinterpreted as info-bubble dismissal.
                history = room.locator('.hem-room-glance87 [data-hem-source105="sensor.co2"]')
                expect(history).to_be_visible()
                history.click()
                expect(page.locator(".hem-avg-dialog105")).to_be_visible()
                # The narrow history dialog covers the fixed test button.
                # Its 12px inset leaves the page's outer corner available
                # for a real click outside both the dialog and card.
                assert page.evaluate("document.elementFromPoint(2,2)!==card")
                page.mouse.click(2, 2)
                expect(page.locator(".hem-avg-dialog105")).to_be_visible()
                assert_listeners(page, 0)
                page.locator("[data-close-avg105]").click()
                # Detach always releases listeners. Reconnection may restore
                # the saved disclosure, but never installs duplicate handlers.
                open_bubble(page, ROOM_KEY)
                page.evaluate("card.remove()")
                assert_listeners(page, 0)
                page.evaluate("document.body.append(card)")
                page.wait_for_function("Boolean(card._floatingInfo87)")
                assert_listeners(page, 1)
                page.locator("#outside").click()
                assert_closed(page, ROOM_KEY)
                # Fallback browsers without showPopover still get the same
                # visible content, inside-click protection and outside close.
                page.evaluate("window.savedShow061b2=HTMLElement.prototype.showPopover;HTMLElement.prototype.showPopover=undefined")
                bubble = open_bubble(page, ROOM_KEY)
                assert bubble.get_attribute("popover") is None
                assert_multiline(page)
                bubble.locator("small").first.click()
                expect(bubble).to_be_visible()
                page.locator("#outside").click()
                assert_closed(page, ROOM_KEY)
                page.evaluate("() => { HTMLElement.prototype.showPopover=window.savedShow061b2; }")
                assert page.evaluate("calls") == []
                assert page.evaluate("info") == []
                assert errors == [], errors
                page.close()
        except Exception as error:
            if page is not None and not page.is_closed():
                try:
                    diagnostics = page.evaluate("() => typeof diagnostics061b2==='function' ? diagnostics061b2() : {body:document.body.innerText}")
                    report = {"viewport": label, "error": str(error), "pageErrors": errors, "state": diagnostics}
                    rendered = json.dumps(report, ensure_ascii=False, indent=2)
                    print("061B2_INFO_BUBBLE_FAILURE_DIAGNOSTICS\n" + rendered, file=sys.stderr, flush=True)
                    if output:
                        (output / f"061b2-info-failure-{label}.json").write_text(rendered, encoding="utf-8")
                        page.screenshot(path=str(output / f"061b2-info-failure-{label}.png"), full_page=True)
                except Exception as diagnostic_error:
                    print(f"Could not capture bubble failure diagnostics: {diagnostic_error}", file=sys.stderr)
            raise
        finally:
            browser.close()
    print("061B2_GREEK_INFO_BUBBLES_DESKTOP_MOBILE_OUTSIDE_CLICK=PASS")


if __name__ == "__main__":
    data = fixture()
    subprocess.run(["node", str(Path(__file__).with_suffix(".js")), str(CARD),
                    json.dumps(data, ensure_ascii=False)], check=True)
    if "--logic-only" not in sys.argv:
        browser_checks(data)
