"""Beta114: room presence, exact problem navigation and compact headers.

The production card runs against deterministic HA snapshots. No physical
services are used. --logic-only checks the rendered data and click targets in
Node; the full suite also checks focus, disclosure and geometry in Chromium.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"


def backend_checks():
    """Run the actual metadata assembly for enabled and climate-free rooms."""
    tree = ast.parse((ROOT / 'manager.py').read_text())
    loop = next(n for n in ast.walk(tree) if isinstance(n, ast.For)
                and isinstance(n.target, ast.Name) and n.target.id == 'monitored_room')
    start = next(i for i, n in enumerate(loop.body)
                 if isinstance(n, ast.If) and 'isinstance(climate, dict)' in ast.unparse(n.test))
    end = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign)
               and any('room_presence' in ast.unparse(t) for t in n.targets))
    code = compile(ast.Module(body=loop.body[start:end + 1], type_ignores=[]), 'manager.py', 'exec')
    calls = []
    for climate, home, room_state, expected in (
        ({'status': 'disabled'}, 'home', 'occupied', 'occupied'),
        ({'status': 'disabled'}, 'away', 'unoccupied', 'unoccupied'),
        ({'status': 'ready', 'occupancy': 'occupied', 'occupancy_evidence': 'assumed_occupied'},
         'home', 'occupied', 'unknown'),
        ({'status': 'ready', 'occupancy': 'unoccupied', 'away': 'away',
          'occupancy_evidence': 'verified_home_away'}, 'away', 'unoccupied', 'unoccupied'),
    ):
        def room_presence(*args, **kwargs):
            calls.append(kwargs['home_status'])
            return room_state, 'verified_home_away' if home == 'away' else 'verified_room_occupied', []
        scope = dict(climate=climate, local_settings={}, area_id='room', environment={},
            shared={}, known_areas={'room'}, self=SimpleNamespace(hass=SimpleNamespace(
                config=SimpleNamespace(time_zone='UTC'))),
            home_presence=lambda *a: (home, 'configured_home_source', []),
            room_presence=room_presence, scheduled_sleep=lambda *a: (False, 'outside_sleep'),
            controlled_sleep_presence=lambda *a, **k: (False, 'outside_sleep'), time=lambda: 0)
        exec(code, scope)
        assert scope['environment']['room']['room_presence']['occupancy'] == expected
    assert calls == ['home', 'away'], calls
    print('BETA114_ALL_ROOMS_VERIFIED_PRESENCE_SNAPSHOT=PASS')


def fixture():
    rooms = []
    states = {}
    for area, occupancy, home, status in (
        ("occupied", "occupied", "home", "safe"),
        ("empty", "unoccupied", "home", "safe"),
        ("away", "occupied", "away", "safe"),
        ("missing", "unknown", "home", "unknown"),
        ("warning", "occupied", "home", "attention"),
        ("fault", "occupied", "home", "safe"),
        ("climate_only", "occupied", "home", "unknown"),
    ):
        readings = []
        for metric, value, unit in (("temperature", 21.4, "°C"),
                                     ("humidity", 54.2, "%"),
                                     ("co2", 718, "ppm"),
                                     ("pm25", 6.2, "µg/m³")):
            entity = f"sensor.{area}_{metric}"
            states[entity] = {"state": str(value), "attributes": {"friendly_name": metric}}
            readings.append({"metric": metric, "entity_id": entity,
                "available": True, "value": value, "unit": unit, "name": metric,
                "exceeded": area == "warning" and metric == "co2"})
        window = f"binary_sensor.{area}_window"
        states[window] = {"state": "on" if area in ("warning", "climate_only") else "off", "attributes": {}}
        rooms.append({"area_id": area, "name": area.title(), "status": status,
            "action": "close" if area == "warning" else None,
            "climate_only": area == "climate_only",
            "windows": [{"entity_id": window, "name": "Window", "opened": area in ("warning", "climate_only")}],
            "readings": readings, "environment": {"climate_plan": {
                "status": "ready", "controller": "environment", "profile": "home",
                "occupancy": occupancy, "away": home, "temperature_c": 21.4,
                "equipment_plan": {"humidity": {"status": "advisory", "measured_rh": 54.2}},
                "actuation": {"status": "advisory_only"}}}})
    rooms[3]["readings"].append({"metric": "pressure", "entity_id": "sensor.missing_pressure",
        "available": False, "value": None, "unit": "hPa", "name": "Pressure sensor offline"})
    states["sensor.missing_pressure"] = {"state": "unavailable", "attributes": {}}
    source = "climate.physical_fault"
    common = {"area_id": "fault", "source_entity_ids": [source]}
    states[source] = {"state": "off", "attributes": {"friendly_name": "Physical appliance"}}
    states["climate.managed_fault"] = {"state": "off", "attributes": {
        **common, "control_mode": "pid", "friendly_name": "HEM appliance",
        "physical_source_state": "off", "physical_primary_entity_id": source,
        "controller_status": {"status": "paused"}, "hvac_modes": ["dry", "off"]}}
    states["sensor.fault_status"] = {"state": "paused", "attributes": {
        **common, "status_code": "paused", "paused_reason": "physical_acknowledgement_missing",
        "status_reason_code": "physical_acknowledgement_missing"}}
    states["switch.fault_announce"] = {"state": "on", "attributes": {
        **common, "device_fault_role": "announce", "native_error": {
            "status": "error", "code": "E24", "description": "Tank sensor fault",
            "source_entity_id": source, "native_error_entities": [source]}}}
    states["sensor.hem"] = {"state": "ready", "attributes": {"dashboard": {
        "version": 1, "summary": {"safe": 4, "unknown": 1, "attention": 1},
        "outdoor": {"status": "safe", "readings": [], "weather": []}, "rooms": rooms}}}
    return states


def logic_checks(states):
    script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const classes=new Map();
const noop=()=>{};
class Element {attachShadow(){this.shadowRoot={addEventListener:noop};}}
const box={HTMLElement:Element,customElements:{get:n=>classes.get(n),define:(n,c)=>classes.set(n,c)},
  window:{},console,setTimeout,clearTimeout,requestAnimationFrame:noop,cancelAnimationFrame:noop};
vm.createContext(box);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),box);
const card=new (classes.get('home-environment-manager-card'))();
card._hass={language:'en',states:JSON.parse(process.argv[2]),localize:()=>undefined};
card._config={entity:'sensor.hem'};
const rooms=card._hass.states['sensor.hem'].attributes.dashboard.rooms;
for(const room of rooms) {
  const expected=room.area_id==='away'?'unoccupied':room.environment.climate_plan.occupancy;
  assert.equal(card._roomPresence114(room).state,expected);
  const html=card._room(room);
  assert.ok(html.includes('data-room-presence114="'+expected+'"'));
  assert.ok(html.includes('data-room-settings114="'+room.area_id+'"'));
  assert.ok(!html.includes('mdi:home-export-outline'));
}
const away=card._room(rooms.find(r=>r.area_id==='away'));
assert.ok(away.includes('Nobody home · room empty'));
assert.ok(!away.includes('mdi:account-check-outline'));
assert.equal((away.match(/mdi:account-off-outline/g)||[]).length,1);
const disabled=structuredClone(rooms[0]);
disabled.environment.climate_plan={status:'disabled'};
disabled.environment.room_presence={occupancy:'occupied',home:'home'};
assert.equal(card._roomPresence114(disabled).state,'occupied');
disabled.environment.room_presence={occupancy:'unknown',home:'unknown'};
disabled.environment.climate_plan={occupancy:'occupied',away:'home'};
assert.equal(card._roomPresence114(disabled).state,'unknown','comfort assumption replaced actual evidence');
assert.ok(card._room(rooms.find(r=>r.area_id==='missing')).includes('data-room-issue114="missing"'));
const fault=card._room(rooms.find(r=>r.area_id==='fault'));
assert.ok(fault.includes('data-room-issue114="faults"'));
assert.ok(fault.includes('data-room-issue114="controllers"'));
card._roomIssues114=new Map([['missing','missing']]);
const details=card._roomIssueDetail114(rooms.find(r=>r.area_id==='missing'));
assert.ok(details.includes('Pressure sensor offline'));
assert.ok(details.includes('data-hem-source105="sensor.missing_pressure"'));
const recovered=structuredClone(rooms.find(r=>r.area_id==='missing'));
recovered.readings.at(-1).available=true;recovered.readings.at(-1).value=1013;
recovered.status='safe';
assert.equal(card._roomIssueDetail114(recovered),'','stale missing-data warning after recovery');
card._roomIssues114.set('climate_only','windows');
const contactDetail=card._roomIssueDetail114(rooms.find(r=>r.area_id==='climate_only'));
assert.ok(contactDetail.includes('data-hem-source105="binary_sensor.climate_only_window"'));
console.log('BETA114_ROOM_PRESENCE_AND_ALERT_TARGETS=PASS');
"""
    subprocess.run(["node", "-e", script, str(CARD), json.dumps(states)], check=True)


def browser_checks(states):
    from playwright.sync_api import sync_playwright

    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
        shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome, "Chromium required"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 590, "height": 960})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content("""<html><head><style>
          body{margin:0;background:#14191f;font-family:Arial}
          :root{--primary-text-color:#eef2f6;--secondary-text-color:#9aa9ba;
            --card-background-color:#202832;--secondary-background-color:#26313e;
            --divider-color:#3b4858}
          </style></head><body></body></html>""")
        page.add_script_tag(path=str(CARD))
        page.evaluate("""states=>{
          window.card=document.createElement('home-environment-manager-card');
          document.body.append(card);window.info=[];window.calls=[];
          card.addEventListener('hass-more-info',e=>info.push(e.detail.entityId));
          card._hass={states,language:'en',user:{is_admin:true},localize:()=>undefined,
            callService:(...args)=>{calls.push(args);return Promise.resolve();}};
          card._config={entity:'sensor.hem'};card._renderContent(true);
        }""", states)
        for width in (320, 390, 590):
            page.set_viewport_size({"width": width, "height": 960})
            for header in page.locator(".hem-room-glance87").all():
                result = header.evaluate("""el=>({width:el.clientWidth,scroll:el.scrollWidth,
                  height:el.getBoundingClientRect().height,
                  left:el.querySelector('.hem-room-name87').previousElementSibling.hasAttribute('data-room-settings114')})""")
                assert result["scroll"] <= result["width"] + 1, (width, result)
                assert result["height"] <= 52, (width, result)
                assert result["left"], result
        name = lambda area: page.locator(f'[data-room-fold87="{area}"] .hem-room-name87')
        colors = [name(area).evaluate("el=>getComputedStyle(el).color")
                  for area in ("occupied", "empty", "missing")]
        assert len(set(colors)) == 3, colors
        missing = page.locator('[data-room-fold87="missing"]')
        missing.locator('[data-room-issue114="missing"]').click()
        detail = missing.locator('.hem-room-issue-detail114')
        assert detail.is_visible()
        assert detail.evaluate('el=>el.getRootNode().activeElement===el')
        assert "Pressure sensor offline" in detail.inner_text()
        detail.locator('[data-hem-source105="sensor.missing_pressure"]').click()
        assert page.evaluate('info')[-1] == 'sensor.missing_pressure'
        warning = page.locator('[data-room-fold87="warning"]')
        warning.locator('[data-room-issue114="attention"]').click()
        metric = warning.locator('[data-room-metric114="co2"]')
        assert metric.is_visible()
        assert metric.evaluate('el=>el.getRootNode().activeElement===el')
        warning.locator('[data-room-issue114="windows"]').click()
        assert warning.locator('.window-section').evaluate('el=>el.getRootNode().activeElement===el')
        fault = page.locator('[data-room-fold87="fault"]')
        fault.locator('[data-room-issue114="faults"]').click()
        error = fault.locator('.hem-device-error')
        assert error.is_visible() and "E24" in error.inner_text()
        assert error.evaluate('el=>el.getRootNode().activeElement===el')
        assert fault.locator('[data-device-fold87="climate.managed_fault"]').get_attribute('open') is not None
        fault.locator('[data-room-issue114="controllers"]').click()
        problem = fault.locator('[data-detail-id="device-info:climate.managed_fault"]')
        assert problem.get_attribute('open') is not None
        popup = page.locator('.hem-floating-info87')
        assert popup.is_visible()
        assert 'Reason' in popup.inner_text()
        page.wait_for_function("card.shadowRoot.activeElement?.matches('.hem-floating-info87')")
        page.keyboard.press('Escape')
        page.evaluate('card._renderContent(true)')
        assert fault.locator('[data-device-fold87="climate.managed_fault"]').get_attribute('open') is not None
        assert detail.is_visible(), 'open problem details were lost on update'
        assert page.evaluate('calls') == [], 'navigation issued a physical command'
        # Native button keyboard activation takes the same guarded path.
        missing.locator('[data-room-issue114="missing"]').focus()
        page.keyboard.press('Enter')
        assert detail.evaluate('el=>el.getRootNode().activeElement===el')
        page.evaluate("""()=>{
          const states=structuredClone(card._hass.states);
          const room=states['sensor.hem'].attributes.dashboard.rooms.find(r=>r.area_id==='missing');
          room.status='safe';room.readings.at(-1).available=true;room.readings.at(-1).value=1013;
          card._hass={...card._hass,states};card._renderContent(true);
        }""")
        assert missing.locator('.hem-room-issue-detail114').count() == 0
        climate_only = page.locator('[data-room-fold87="climate_only"]')
        climate_only.locator('[data-room-issue114="windows"]').click()
        contact_detail = climate_only.locator('.hem-room-issue-detail114')
        assert contact_detail.is_visible()
        contact_detail.locator('[data-hem-source105="binary_sensor.climate_only_window"]').click()
        assert page.evaluate('info')[-1] == 'binary_sensor.climate_only_window'
        output = os.environ.get('HEM_TEST_SCREENSHOT_DIR')
        if output:
            Path(output).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(Path(output) / 'beta114-room-navigation.png'), full_page=True)
        assert not errors, errors
        browser.close()
    print('BETA114_ROOM_NAVIGATION_BROWSER=PASS')


if __name__ == '__main__':
    backend_checks()
    fixture_states = fixture()
    logic_checks(fixture_states)
    if '--logic-only' not in sys.argv:
        browser_checks(fixture_states)
