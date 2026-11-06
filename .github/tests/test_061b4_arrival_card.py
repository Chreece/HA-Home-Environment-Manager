"""0.6.1b4: arrival controls, exact-home routing, and compact warning spacing.

Uses the production card in Chromium with local HA transport. Reuses b3's
actual text Range checks so fixing the gap cannot reintroduce clipped values.
No real Home Assistant or physical equipment is contacted.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import runpy
import shutil

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
BOUNDS = runpy.run_path(str(ROOT / ".github/tests/test_061b3_text_boundaries.py"))
PREPARE = "button.renamed_arrival_a"
CANCEL = "button.renamed_stop_a"
TIMEOUT = "number.renamed_timeout_a"
PREPARE_B = "button.renamed_arrival_b"


def fixture(language):
    data = BOUNDS["fixture"](language)
    data["entities"], data["devices"] = {}, []
    data["states"]["sensor.another_home"] = deepcopy(data["states"]["sensor.hem"])
    for suffix, sensor in (("a", "sensor.hem"), ("b", "sensor.another_home")):
        entry, device = f"home_{suffix}", f"home-device-{suffix}"
        ids = {"prepare": f"button.renamed_arrival_{suffix}",
               "cancel": f"button.renamed_stop_{suffix}",
               "timeout": f"number.renamed_timeout_{suffix}"}
        data["states"][sensor]["attributes"]["dashboard"]["arrival_preparation"] = {
            "entry_id": entry, "active": False, "can_start": True,
            "expires_at": None, "remaining_seconds": 0, "timeout_minutes": 60,
            "home_status": "away", "entity_ids": ids}
        data["entities"][sensor] = {"config_entry_id": entry, "device_id": device}
        data["devices"].append({"id": device, "identifiers": [["environment_manager", entry]]})
        for role, entity in ids.items():
            # A never-pressed native Button legitimately starts as unknown.
            data["states"][entity] = {"state": "60" if role == "timeout" else "unavailable" if role == "cancel" else "unknown",
                "attributes": {"entry_id": entry, "arrival_preparation_role": role}}
            data["entities"][entity] = {"config_entry_id": entry, "device_id": device}
    return data


SETUP = r"""data => {
  window.calls=[];window.info=[];
  window.nativeService124=(...args)=>{calls.push(args);return Promise.resolve();};
  window.createCard124=(hass,entity='sensor.hem')=>{
    const node=document.createElement('home-environment-manager-card');
    document.querySelector('main').append(node);
    node.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
    node.setConfig({entity});node.hass=hass;return node;
  };
  window.card=createCard124({language:data.language,states:data.states,entities:data.entities,
    localize:()=>undefined,config:{time_zone:'UTC'},connection:{},
    callService:(...args)=>nativeService124(...args),callWS:async request=>{
      if(request.type==='config/device_registry/list')return data.devices;
      throw Error('Unexpected mocked HA request: '+request.type);
    }});
  window.patchArrival124=(patch,entity=card._state()[0])=>{
    const states=structuredClone(card._hass.states);
    const payload=states[entity].attributes.dashboard.arrival_preparation;
    Object.assign(payload,patch);
    for(const state of Object.values(states)){
      if(state?.attributes?.entry_id!==payload.entry_id)continue;
      if(state.attributes.arrival_preparation_role==='prepare')
        state.state=payload.can_start&&!payload.active&&payload.home_status==='away'?'unknown':'unavailable';
      if(state.attributes.arrival_preparation_role==='cancel')
        state.state=payload.active?'unknown':'unavailable';
    }
    card.hass={...card._hass,states};
  };
  window.setNative124=(entity,state)=>{
    // Keep the dashboard sensor object identical: native Number changes
    // must still invalidate the card's render signature.
    const states={...card._hass.states};
    if(state===undefined)delete states[entity];else states[entity]=state;
    card.hass={...card._hass,states};
  };
}"""


GEOMETRY = r"""() => {
  const root=card.shadowRoot,box=node=>{
    const r=node.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};};
  const glyph=node=>{const range=document.createRange();range.selectNodeContents(node);return box(range);};
  const label=root.querySelector('.hem-outside-blocker-label123');
  const value=root.querySelector('.hem-outside-blocker-value123');
  const head=root.querySelector('.card-heading'),actions=root.querySelector('.header-actions');
  const buttons=[...root.querySelectorAll('.hem-arrival124>button,[data-edit-home]')];
  return {gap:glyph(value).left-glyph(label).right,labelFits:label.scrollWidth<=label.clientWidth+1,
    header:box(head),title:box(head.querySelector('h2')),actions:box(actions),
    buttons:buttons.map(button=>({box:box(button),client:button.clientWidth,scroll:button.scrollWidth,
      accessible:button.getAttribute('aria-label'),title:button.title})),
    minutes:glyph(root.querySelector('.hem-arrival-minutes124')),
    duration:box(root.querySelector('.hem-arrival-duration124'))};
}"""


def settle(page):
    page.wait_for_function("card._lastState===card._hass.states[card._state()[0]]")
    page.evaluate("async()=>{await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));}")


def assert_geometry(page, *, roomy=False):
    BOUNDS["assert_layout"](page.evaluate(BOUNDS["REPORT"]))
    report = page.evaluate(GEOMETRY)
    if roomy:
        assert report["labelFits"] and 0 <= report["gap"] <= 7, report
    assert report["title"]["right"] <= report["actions"]["left"] + 1, report
    assert report["actions"]["right"] <= report["header"]["right"] + 1, report
    for button in report["buttons"]:
        assert button["accessible"] and button["title"], report
        assert button["scroll"] <= button["client"] + 1, report
        assert button["box"]["left"] >= report["header"]["left"] - 1, report
        assert button["box"]["right"] <= report["header"]["right"] + 1, report
    assert report["minutes"]["left"] >= report["duration"]["left"] - 1, report
    assert report["minutes"]["right"] <= report["duration"]["right"] + 1, report
    return report


def actions(page, expect):
    action = page.locator(".hem-arrival-action124")
    duration = page.locator(".hem-arrival-duration124")
    rooms = page.evaluate("JSON.stringify(card._dashboard105().rooms)")
    expect(action).to_be_enabled()
    action.focus()
    action.press("Enter")
    page.wait_for_function("calls.length===1&&!card._arrivalRequest124")
    assert page.evaluate("calls") == [["button", "press", {"entity_id": PREPARE}]]
    assert page.evaluate("card._dashboard105().arrival_preparation.active") is False
    assert page.evaluate("card._dashboard105().arrival_preparation.home_status") == "away"
    assert page.evaluate("JSON.stringify(card._dashboard105().rooms)") == rooms
    duration.click()
    assert page.evaluate("info") == [TIMEOUT]

    page.evaluate("patchArrival124({active:true,can_start:false,expires_at:Date.now()/1000+1800})")
    settle(page)
    expect(page.locator('.hem-arrival124')).to_have_attribute("data-arrival-status124", "active")
    expect(action).to_have_attribute("data-arrival-action124", "cancel")
    expect(duration).to_contain_text("30")
    page.evaluate("""() => {window.savedRoot124=card._hass.states['sensor.hem'];
      const state=structuredClone(card._hass.states['number.renamed_timeout_a']);
      state.state='1440';setNative124('number.renamed_timeout_a',state);}""")
    expect(duration).to_have_attribute("title", re.compile("1[., ]?440"))
    assert page.evaluate("savedRoot124===card._hass.states['sensor.hem']")
    expect(duration).to_contain_text("30")
    assert_geometry(page)
    action.click()
    page.wait_for_function("calls.length===2&&!card._arrivalRequest124")
    assert page.evaluate("calls.at(-1)") == ["button", "press", {"entity_id": CANCEL}]

    for presence in ("home", "unknown"):
        page.evaluate("status=>patchArrival124({active:false,can_start:false,expires_at:null,home_status:status})", presence)
        settle(page)
        expect(action).to_be_disabled()
        expected = "only while away" if presence == "unknown" else "confirmed away"
        assert expected in action.get_attribute("title")
        # The delegated handler also guards synthetic/stale disabled clicks.
        action.evaluate("node=>node.dispatchEvent(new MouseEvent('click',{bubbles:true,composed:true}))")
        assert page.evaluate("calls.length") == 2
        expect(duration).to_be_enabled()
    page.evaluate("patchArrival124({active:true,can_start:false,expires_at:Date.now()/1000+120,home_status:'unknown'})")
    settle(page)
    expect(page.locator('.hem-arrival124')).to_have_attribute("data-arrival-status124", "paused")
    expect(action).to_be_enabled()

    # Restored snapshots keep the original deadline on a new card instance.
    page.evaluate("""() => {
      patchArrival124({active:true,can_start:false,expires_at:Date.now()/1000+1.5,home_status:'away'});
      window.savedDeadline124=card._dashboard105().arrival_preparation.expires_at;
      const old=card,hass=card._hass;old.remove();window.detached124=old;
      card=createCard124(hass);
    }""")
    settle(page)
    assert page.evaluate("detached124._arrivalTick124") is None
    assert page.evaluate("card._dashboard105().arrival_preparation.expires_at===savedDeadline124")
    expect(page.locator('.hem-arrival124')).to_have_attribute("data-arrival-status124", "expired", timeout=5000)
    expect(duration).to_contain_text("0")
    assert page.evaluate("calls.length") == 2, "Countdown must never press a device button"
    page.evaluate("patchArrival124({active:false,can_start:true,expires_at:null,home_status:'away'})")
    settle(page)

    # A missing/foreign role never silently falls back to another home's button.
    page.evaluate("""() => {window.savedPrepare124=card._hass.states['button.renamed_arrival_a'];
      setNative124('button.renamed_arrival_a',undefined);}""")
    expect(action).to_be_disabled()
    assert "unavailable" in action.get_attribute("title").lower()
    page.evaluate("setNative124('button.renamed_arrival_a',savedPrepare124)")
    expect(action).to_be_enabled()
    page.evaluate("""patchArrival124({entity_ids:{prepare:'button.renamed_arrival_b',
      cancel:'button.renamed_stop_a',timeout:'number.renamed_timeout_a'}})""")
    settle(page)
    expect(action).to_be_disabled()
    action.evaluate("node=>node.dispatchEvent(new MouseEvent('click',{bubbles:true,composed:true}))")
    assert page.evaluate("calls.length") == 2
    expect(page.locator('.hem-arrival-error124')).to_be_visible()
    page.evaluate("""patchArrival124({entity_ids:{prepare:'button.renamed_arrival_a',
      cancel:'button.renamed_stop_a',timeout:'number.renamed_timeout_a'}})""")
    settle(page)

    # Older HA summaries may omit config_entry_id. Require an exact device
    # registry match; absence of both forms of ownership remains disabled.
    page.evaluate("""() => {const entities=structuredClone(card._hass.entities);
      delete entities['sensor.hem'].config_entry_id;card.hass={...card._hass,entities};}""")
    expect(action).to_be_enabled()
    page.evaluate("""() => {const entities=structuredClone(card._hass.entities);
      delete entities['sensor.hem'].device_id;card.hass={...card._hass,entities};}""")
    expect(action).to_be_disabled()
    page.evaluate("""() => {const entities=structuredClone(card._hass.entities);
      entities['sensor.hem']={device_id:'home-device-a',config_entry_id:'home_a'};
      card.hass={...card._hass,entities};
      nativeService124=(...args)=>{calls.push(args);return new Promise((resolve,reject)=>{
        window.rejectRequest124=reject;});};}""")
    expect(action).to_be_enabled()
    action.click()
    page.wait_for_function("calls.length===3&&Boolean(card._arrivalRequest124)")
    # Source changes before the next frame leave an old visible node briefly.
    page.evaluate("""() => {const stale=card.shadowRoot.querySelector('.hem-arrival-action124');
      card.setConfig({entity:'sensor.another_home'});
      stale.dispatchEvent(new MouseEvent('click',{bubbles:true,composed:true}));
      rejectRequest124(Error('Previous home request failed'));
    }""")
    settle(page)
    expect(action).to_be_enabled()
    expect(action).to_have_attribute("data-arrival-entity124", PREPARE_B)
    expect(page.locator('.hem-arrival-error124')).to_have_count(0)
    assert page.evaluate("calls.length") == 3
    page.evaluate("nativeService124=(...args)=>{calls.push(args);return Promise.resolve();}")
    action.click()
    page.wait_for_function("calls.length===4&&!card._arrivalRequest124")
    assert page.evaluate("calls.at(-1)") == ["button", "press", {"entity_id": PREPARE_B}]
    duration.click()
    assert page.evaluate("info.at(-1)") == "number.renamed_timeout_b"
    page.evaluate("nativeService124=(...args)=>{calls.push(args);return Promise.reject(Error('Rejected'));}")
    action.click()
    expect(page.locator('.hem-arrival-error124')).to_contain_text("failed")
    expect(action).to_be_enabled()
    assert page.evaluate("calls.length") == 5


def run():
    from playwright.sync_api import expect, sync_playwright
    executable = os.environ.get("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert executable, "Chromium required for arrival card regression"
    shots = Path(os.environ["HEM_TEST_SCREENSHOT_DIR"]) if os.environ.get("HEM_TEST_SCREENSHOT_DIR") else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    icons = runpy.run_path(str(ROOT / ".github/tests/test_061b1_room_fold.py"))["icon_fixture"]()
    icons = icons.replace("const glyphs = {", """const glyphs = {
      'mdi:home-clock-outline':'<path d="m3 10 8-7 8 7M5 9v11h6M10 20v-7h4"/><circle cx="17" cy="17" r="5"/><path d="M17 14v3l2 1"/>',
      'mdi:timer-outline':'<circle cx="12" cy="14" r="8"/><path d="M9 2h6m-3 0v4m0 4v5m6-8 2-2"/>',""")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page, current, report = None, "setup", None
        try:
            for language in ("el", "de", "en"):
                page = browser.new_page(viewport={"width": 665, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.set_content("""<!doctype html><html><head><style>
                  *{box-sizing:border-box}body{margin:8px;background:#111;color:#eee;font-family:Arial,sans-serif;
                    --primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;
                    --card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}
                  main{width:625px;max-width:100%;margin:0 auto}home-environment-manager-card{display:block}
                  </style></head><body><main></main></body></html>""")
                page.evaluate(icons)
                page.add_script_tag(path=str(CARD))
                page.evaluate(SETUP, fixture(language))
                labels = page.evaluate("['preparing_for_arrival','arrival_preparation_changed'].map(code=>card._controllerStatusLabel(code))")
                assert all(label and "_" not in label for label in labels), labels
                for viewport, width, label in ((665, 625, "reported"), (375, 359, "mobile"),
                        (320, 304, "narrow"), (1024, 760, "desktop"), (1024, 320, "narrow-column")):
                    current = f"{language}-{label}"
                    page.set_viewport_size({"width": viewport, "height": 1000})
                    page.locator("main").evaluate("(node,width)=>node.style.width=width+'px'", width)
                    settle(page)
                    report = assert_geometry(page, roomy=width >= 625)
                    if shots:
                        page.screenshot(path=str(shots / f"061b4-arrival-{current}.png"), full_page=True)
                    page.evaluate("patchArrival124({active:true,can_start:false,expires_at:Date.now()/1000+86390})")
                    settle(page)
                    assert_geometry(page, roomy=width >= 625)
                    if shots:
                        page.screenshot(path=str(shots / f"061b4-arrival-active-{current}.png"), full_page=True)
                    page.evaluate("patchArrival124({active:false,can_start:true,expires_at:null})")
                    settle(page)
                if language == "en":
                    current = "arrival-actions"
                    actions(page, expect)
                assert not errors, errors
                print(f"PASS: {language} adjacent outdoor value and bounded arrival controls in five layouts")
                page.close()
        except Exception:
            if page and shots:
                page.screenshot(path=str(shots / f"061b4-failure-{current}.png"), full_page=True)
                (shots / f"061b4-failure-{current}.json").write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            raise
        finally:
            browser.close()
    print("HEM_061B4_ARRIVAL_CARD_AND_WARNING_GAP=PASS")


if __name__ == "__main__":
    run()
