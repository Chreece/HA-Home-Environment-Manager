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
                 if isinstance(n, ast.Assign) and isinstance(n.value, ast.BoolOp)
                 and 'observed_rooms.get(' in ast.unparse(n.value))
    end = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign)
               and any("['room_presence']" in ast.unparse(t) for t in n.targets))
    code = compile(ast.Module(body=loop.body[start:end + 1], type_ignores=[]), 'manager.py', 'exec')
    calls = []
    # Existing snapshots and newly seen climate-only rooms share the same
    # observed presence. Climate's comfort or vacancy assumptions never
    # override the header, even when its cached value is contradictory.
    for climate, home, current, cached in (
        ({'status': 'disabled'}, 'home', ('occupied','verified_room_occupied',[]), False),
        ({'status': 'disabled'}, 'away', ('unoccupied','verified_home_away',[]), True),
        ({'status': 'ready', 'occupancy': 'occupied', 'occupancy_evidence': 'assumed_occupied'},
         'home', ('unoccupied','no_room_presence_sensors',[]), True),
        ({'status': 'ready', 'occupancy': 'occupied'}, 'home',
         ('unknown','room_occupancy_source_unknown',[]), False),
    ):
        def room_presence(*args, **kwargs):
            calls.append(kwargs['home_status'])
            return current
        scope = dict(climate=climate, local_settings={}, area_id='room', environment={},
            shared={}, known_areas={'room'}, self=SimpleNamespace(hass=SimpleNamespace(
                config=SimpleNamespace(time_zone='UTC'))),
            home_status=home, observed_rooms={'room':current} if cached else {},
            room_presence=room_presence, scheduled_sleep=lambda *a: (False, 'outside_sleep'),
            controlled_sleep_presence=lambda *a, **k: (False, 'outside_sleep'), time=lambda: 0)
        exec(code, scope)
        actual = scope['environment']['room']['room_presence']
        assert actual['occupancy'] == current[0] and actual['occupancy_evidence'] == current[1]
        assert actual['home'] == home
    assert calls == ['home', 'home'], calls
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
        ("mold", "occupied", "home", "unknown"),
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
    rooms[3]["readings"].append({"metric": "pm10", "entity_id": "sensor.missing_pm10",
        "available": False, "value": None, "unit": "µg/m³", "name": "PM10 sensor offline"})
    states["sensor.missing_pm10"] = {"state": "unavailable", "attributes": {}}
    rooms[-1]["status_detail"] = "mold_not_calibrated"
    rooms[-1]["mold_warnings"] = ["calibration"]
    rooms[-1]["readings"].append({"metric": "mold", "entity_id": "mold:mold",
        "available": False, "value": None, "unit": "%", "name": "Mold indication",
        "details": {"status": "needs_calibration", "calibration_readiness": "difference_suitable",
            "calibration_recommended_difference_c": 10.0, "calibration_stability": "not_verified",
            "indoor_temperature_c": 21.4, "outdoor_temperature_c": 4.2,
            "calibration_temperature_difference_c": 17.2}})
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
  const header=html.slice(0,html.indexOf('</summary>'));
  assert.ok(!header.includes('hem-room-icon112'));
  assert.ok(!header.includes('mdi:home-outline'));
  assert.ok(!header.includes('aria-expanded="undefined"'));
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
assert.ok(details.includes('PM10 sensor offline'));
assert.ok(details.includes('data-hem-source105="sensor.missing_pm10"'));
const recovered=structuredClone(rooms.find(r=>r.area_id==='missing'));
recovered.readings.at(-1).available=true;recovered.readings.at(-1).value=12.3;
recovered.status='safe';
assert.equal(card._roomIssueDetail114(recovered),'','stale missing-data warning after recovery');
card._roomIssues114.set('climate_only','windows');
const contactDetail=card._roomIssueDetail114(rooms.find(r=>r.area_id==='climate_only'));
assert.ok(contactDetail.includes('data-hem-source105="binary_sensor.climate_only_window"'));
const moldRoom=rooms.find(r=>r.area_id==='mold');
card._roomIssues114.set('mold','missing');
let moldHelp=card._roomIssueDetail114(moldRoom);
assert.ok(moldHelp.includes('data-mold-readiness115="difference_suitable"'));
assert.ok(moldHelp.includes('Stable conditions are not verified'));
assert.ok(moldHelp.includes('17.2 °C'));
for(const language of ['en','de','el']){
  card._hass.language=language;
  assert.equal(card._metricName('temperature'),
    ({en:'Temperature',de:'Temperatur',el:'Θερμοκρασία'})[language]);
  const title=({en:'Mold indication measurement',de:'Messung der Schimmelindikation',
    el:'Μέτρηση ένδειξης μούχλας'})[language];
  for(const [state,outside,difference,tone] of [
    ['temperatures_unavailable',null,null,'unavailable'],
    ['outdoors_not_colder',22.4,-1,'not-ready'],
    ['outdoors_not_colder',21.4,0,'not-ready'],
    ['difference_too_small',19.4,2,'not-ready'],
    ['difference_too_small',11.401,9.999,'not-ready'],
    ['difference_suitable',11.4,10,'ready'],
    ['difference_suitable',4.2,17.2,'ready'],
  ]){
    const reading=structuredClone(moldRoom.readings.at(-1));
    Object.assign(reading.details,{calibration_readiness:state,
      outdoor_temperature_c:outside,calibration_temperature_difference_c:difference});
    const help=card._moldMeasurementGuidance115(reading);
    assert.ok(help.includes('data-mold-readiness115="'+state+'"'));
    assert.ok(help.includes('data-mold-tone117="'+tone+'"'));
    assert.ok(help.includes('<strong>'+title+'</strong>'));
    assert.ok(help.includes('aria-label="'+title+'"'));
    assert.ok(help.includes('10 °C'));
    assert.ok(help.includes(({en:'minimum recommended',de:'mindestens 10 °C',
      el:'ελάχιστη συνιστώμενη'})[language]));
    assert.ok(help.includes(({en:'Stable conditions are not verified',
      de:'Stabile Bedingungen sind nicht bestätigt',
      el:'Οι σταθερές συνθήκες δεν έχουν επιβεβαιωθεί'})[language]));
    assert.ok(!help.includes('undefined'));
  }
}
const invalid=structuredClone(moldRoom.readings.at(-1));
invalid.details.outdoor_temperature_c=NaN;
assert.ok(card._moldMeasurementGuidance115(invalid).includes('data-mold-tone117="unavailable"'));
const calibrated=structuredClone(moldRoom.readings.at(-1));
calibrated.details.status='ready';calibrated.available=true;calibrated.value=62;
assert.equal(card._moldMeasurementGuidance115(calibrated),'');
console.log('BETA114_ROOM_PRESENCE_AND_ALERT_TARGETS=PASS');
console.log('BETA115_MOLD_GUIDANCE_MARKUP_AND_LOCALES=PASS');
console.log('BETA117_MOLD_MEASUREMENT_TITLES_MINIMUM_AND_VALUE_TONES=PASS');
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
                  left:el.querySelector('.hem-room-name87').previousElementSibling.hasAttribute('data-room-settings114'),
                  first:el.firstElementChild.hasAttribute('data-room-settings114'),
                  homes:el.querySelectorAll('.hem-room-icon112,[icon="mdi:home-outline"]').length})""")
                assert result["scroll"] <= result["width"] + 1, (width, result)
                assert result["height"] <= 52, (width, result)
                assert result["left"], result
                assert result["first"] and result["homes"] == 0, result
        name = lambda area: page.locator(f'[data-room-fold87="{area}"] .hem-room-name87')
        colors = [name(area).evaluate("el=>getComputedStyle(el).color")
                  for area in ("occupied", "empty", "missing")]
        assert len(set(colors)) == 3, colors
        missing = page.locator('[data-room-fold87="missing"]')
        missing.locator('[data-room-issue114="missing"]').click()
        detail = missing.locator('.hem-room-issue-detail114')
        assert detail.is_visible()
        assert detail.evaluate('el=>el.getRootNode().activeElement===el')
        assert "PM10 sensor offline" in detail.inner_text()
        # A repeated press closes its generated panel, including after an HA
        # render; the room returns to its previously folded state.
        page.evaluate('card._renderContent(true)')
        missing.locator('[data-room-issue114="missing"]').click()
        assert not detail.is_visible()
        assert missing.get_attribute('open') is None
        assert missing.locator('[data-room-issue114="missing"]').get_attribute('aria-expanded') == 'false'
        assert missing.locator('[data-room-issue114="missing"]').evaluate('el=>el.getRootNode().activeElement===el')
        missing.locator('[data-room-issue114="missing"]').click()
        assert detail.is_visible()
        detail.locator('[data-hem-source105="sensor.missing_pm10"]').click()
        assert page.evaluate('info')[-1] == 'sensor.missing_pm10'
        warning = page.locator('[data-room-fold87="warning"]')
        warning.locator('[data-room-issue114="attention"]').click()
        metric = warning.locator('[data-room-metric114="co2"]')
        assert metric.is_visible()
        assert metric.evaluate('el=>el.getRootNode().activeElement===el')
        warning.locator('[data-room-issue114="attention"]').click()
        assert warning.get_attribute('open') is None
        warning.locator('[data-room-issue114="attention"]').click()
        warning.locator('[data-room-issue114="windows"]').click()
        assert warning.locator('.window-section').evaluate('el=>el.getRootNode().activeElement===el')
        warning.locator('[data-room-issue114="windows"]').click()
        assert warning.get_attribute('open') is None
        warning.locator('[data-room-issue114="windows"]').click()
        fault = page.locator('[data-room-fold87="fault"]')
        fault.locator('[data-room-issue114="faults"]').click()
        error = fault.locator('.hem-device-error')
        assert error.is_visible() and "E24" in error.inner_text()
        assert error.evaluate('el=>el.getRootNode().activeElement===el')
        assert fault.locator('[data-device-fold87="climate.managed_fault"]').get_attribute('open') is not None
        fault.locator('[data-room-issue114="faults"]').click()
        assert fault.get_attribute('open') is None
        assert not error.is_visible()
        # If the room was already open, dismissing an error closes only the
        # device disclosure that the error button itself opened.
        fault.locator('.hem-room-name87').click()
        fault.locator('[data-room-issue114="faults"]').click()
        assert error.is_visible()
        # Manually hiding the problem makes the next warning press reveal
        # it again, even though the room itself is still expanded.
        fault.locator('[data-device-fold87="climate.managed_fault"] > summary').evaluate('(el)=>el.click()')
        assert not error.is_visible()
        fault.locator('[data-room-issue114="faults"]').click()
        assert error.is_visible()
        fault.locator('[data-room-issue114="faults"]').click()
        assert fault.get_attribute('open') is not None
        assert fault.locator('[data-device-fold87="climate.managed_fault"]').get_attribute('open') is None
        fault.locator('[data-room-issue114="faults"]').click()
        fault.locator('[data-room-issue114="controllers"]').click()
        problem = fault.locator('[data-detail-id="device-info:climate.managed_fault"]')
        assert problem.get_attribute('open') is not None
        popup = page.locator('.hem-floating-info87')
        assert popup.is_visible()
        assert 'Reason' in popup.inner_text()
        try:
            page.wait_for_function("card.shadowRoot.activeElement?.matches('.hem-floating-info87')", timeout=5000)
        except Exception:
            print('PROBLEM_FOCUS_DIAGNOSTIC', page.evaluate("""()=>({
                active:card.shadowRoot.activeElement?.outerHTML,
                requested:card._roomIssueInfo114,
                explanation:card._floatingInfo87?.outerHTML,
                details:[...card.shadowRoot.querySelectorAll('details.hem-context76[open]')].map(n=>n.outerHTML)
            })"""))
            output = os.environ.get('HEM_TEST_SCREENSHOT_DIR')
            if output:
                Path(output).mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(Path(output) / 'beta114-focus-failure.png'), full_page=True)
            raise
        previous_reason = popup.inner_text()
        page.evaluate("""()=>{
          const states=structuredClone(card._hass.states);
          states['sensor.fault_status'].attributes.status_reason_code='minimum_off_hold';
          card._hass={...card._hass,states};card._renderContent(true);
        }""")
        assert popup.inner_text() != previous_reason, 'open controller explanation did not refresh'
        assert popup.inner_html() == problem.locator('.hem-context-body76').inner_html()
        other_info = page.locator('[data-room-fold87="mold"] [data-room-issue114="missing"]')
        other_info.focus()
        page.keyboard.press('Enter')
        assert not popup.is_visible(), 'keyboard navigation left the previous room popup open'
        assert page.locator('[data-room-fold87="mold"] .hem-mold-measurement115').is_visible()
        other_info.focus()
        page.keyboard.press('Enter')
        fault.locator('[data-room-issue114="controllers"]').click()
        assert popup.is_visible()
        # Real pointer activation also closes the top-layer popup; native
        # light-dismiss must not make the same click reopen it immediately.
        fault.locator('[data-room-issue114="controllers"]').click()
        assert not popup.is_visible()
        assert problem.get_attribute('open') is None
        assert fault.get_attribute('open') is not None
        assert fault.locator('[data-room-issue114="controllers"]').get_attribute('aria-expanded') == 'false'
        fault.locator('[data-room-issue114="controllers"]').click()
        assert popup.is_visible()
        # Escape followed by one press must open again, not consume a click
        # clearing a stale selected-warning record. Repeat this sequence to
        # exercise the native popover/disclosure event-ordering regression.
        for attempt in range(5):
            page.keyboard.press('Escape')
            fault.locator('[data-room-issue114="controllers"]').click()
            assert popup.is_visible(), page.evaluate("""attempt=>({attempt,
                detailOpen:card.shadowRoot.querySelector('[data-detail-id="device-info:climate.managed_fault"]')?.open,
                popConnected:card._floatingInfo87?.isConnected,
                popShown:card._floatingInfo87?.matches(':popover-open'),
                selected:card._roomIssueInfo114,
                pointer:card._roomIssuePointer115,
                active:card.shadowRoot.activeElement?.outerHTML
            })""", attempt)
        page.keyboard.press('Escape')
        page.evaluate('card._renderContent(true)')
        assert fault.locator('[data-device-fold87="climate.managed_fault"]').get_attribute('open') is not None
        assert detail.is_visible(), 'open problem details were lost on update'
        assert page.evaluate('calls') == [], 'navigation issued a physical command'
        # Native button keyboard activation takes the same guarded path.
        missing.locator('[data-room-issue114="missing"]').focus()
        page.keyboard.press('Enter')
        assert not detail.is_visible()
        page.keyboard.press('Enter')
        assert detail.evaluate('el=>el.getRootNode().activeElement===el')
        page.evaluate("""()=>{
          const states=structuredClone(card._hass.states);
          const room=states['sensor.hem'].attributes.dashboard.rooms.find(r=>r.area_id==='missing');
          room.status='safe';room.readings.at(-1).available=true;room.readings.at(-1).value=12.3;
          card._hass={...card._hass,states};card._renderContent(true);
        }""")
        assert missing.locator('.hem-room-issue-detail114').count() == 0
        climate_only = page.locator('[data-room-fold87="climate_only"]')
        climate_only.locator('[data-room-issue114="windows"]').click()
        mold = page.locator('[data-room-fold87="mold"]')
        mold.locator('[data-room-issue114="missing"]').click()
        guidance = mold.locator('.hem-mold-measurement115')
        assert guidance.is_visible()
        assert guidance.get_attribute('data-mold-readiness115') == 'difference_suitable'
        assert '17.2 °C' in guidance.inner_text()
        assert 'Stable conditions are not verified' in guidance.inner_text()
        assert guidance.locator(':scope > strong').inner_text() == 'Mold indication measurement'
        assert '10 °C is the minimum recommended indoor-minus-outdoor temperature difference' in guidance.inner_text()
        values = guidance.locator('[data-mold-value117]')
        assert values.evaluate_all('nodes=>nodes.map(el=>getComputedStyle(el).color)') == ['rgb(31, 157, 119)'] * 3
        output = os.environ.get('HEM_TEST_SCREENSHOT_DIR')
        if output:
            Path(output).mkdir(parents=True, exist_ok=True)
            page.set_viewport_size({"width": 390, "height": 960})
            guidance.scroll_into_view_if_needed()
            page.screenshot(path=str(Path(output) / 'beta117-mold-measurement-ready-390.png'))
            page.set_viewport_size({"width": 590, "height": 960})
        page.evaluate("""()=>{
          const states=structuredClone(card._hass.states);
          const room=states['sensor.hem'].attributes.dashboard.rooms.find(r=>r.area_id==='mold');
          Object.assign(room.readings.at(-1).details,{
            calibration_readiness:'difference_too_small',outdoor_temperature_c:19.4,
            calibration_temperature_difference_c:2.0});
          card._hass={...card._hass,states};card._renderContent(true);
        }""")
        assert guidance.get_attribute('data-mold-readiness115') == 'difference_too_small'
        assert 'Wait for a larger temperature difference' in guidance.inner_text()
        assert values.evaluate_all('nodes=>nodes.map(el=>getComputedStyle(el).color)') == ['rgb(223, 109, 85)'] * 3
        if output:
            page.set_viewport_size({"width": 390, "height": 960})
            guidance.scroll_into_view_if_needed()
            page.screenshot(path=str(Path(output) / 'beta117-mold-measurement-not-ready-390.png'))
            page.set_viewport_size({"width": 590, "height": 960})
        # Use the backend readiness, including a sub-threshold value that
        # rounds to 10 °C, reverse contrast, and an unavailable outside source.
        for readiness, outside, difference, colour, count in (
            ('difference_too_small', 11.401, 9.999, 'rgb(223, 109, 85)', 3),
            ('outdoors_not_colder', 23.4, -2.0, 'rgb(223, 109, 85)', 3),
            ('temperatures_unavailable', None, None, 'rgb(154, 169, 186)', 2),
        ):
            page.evaluate("""({readiness,outside,difference})=>{
              const states=structuredClone(card._hass.states);
              const room=states['sensor.hem'].attributes.dashboard.rooms.find(r=>r.area_id==='mold');
              Object.assign(room.readings.at(-1).details,{
                calibration_readiness:readiness,outdoor_temperature_c:outside,
                calibration_temperature_difference_c:difference});
              card._hass={...card._hass,states};card._renderContent(true);
            }""", {'readiness': readiness, 'outside': outside, 'difference': difference})
            assert values.evaluate_all('nodes=>nodes.map(el=>getComputedStyle(el).color)') == [colour] * count
            if difference == 9.999:
                assert guidance.locator('[data-mold-value117="difference"]').inner_text() == '10 °C'
        assert guidance.locator('[data-mold-value117="outdoor"]').inner_text() == 'Unavailable'
        mold.locator('[data-room-issue114="missing"]').click()
        assert not guidance.is_visible()
        contact_detail = climate_only.locator('.hem-room-issue-detail114')
        assert contact_detail.is_visible()
        contact_detail.locator('[data-hem-source105="binary_sensor.climate_only_window"]').click()
        assert page.evaluate('info')[-1] == 'binary_sensor.climate_only_window'
        climate_only.locator('[data-room-issue114="windows"]').click()
        assert not contact_detail.is_visible()
        assert climate_only.get_attribute('open') is None
        climate_only.locator('[data-room-issue114="windows"]').click()
        output = os.environ.get('HEM_TEST_SCREENSHOT_DIR')
        if output:
            Path(output).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(Path(output) / 'beta114-room-navigation.png'), full_page=True)
        assert not errors, errors
        browser.close()
    print('BETA114_ROOM_NAVIGATION_BROWSER=PASS')
    print('BETA115_ROOM_HEADER_AND_ERROR_INFO_TOGGLES=PASS')


if __name__ == '__main__':
    backend_checks()
    fixture_states = fixture()
    logic_checks(fixture_states)
    if '--logic-only' not in sys.argv:
        browser_checks(fixture_states)
