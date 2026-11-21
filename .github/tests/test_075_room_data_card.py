"""Room availability uses actual control requirements and consistent UI counts.

The production card renders authoritative backend availability plus an older
inline snapshot. Node verifies classification, exact-input diagnostics and
read-only output; Chromium checks the real room/floor/overview surfaces and
accessible disclosures at desktop and mobile widths in English, Greek and
German. No physical service or configuration write is permitted.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
EXPECTED = {"living": "safe", "heating": "unknown", "purifier": "safe",
            "temp_only": "safe", "rh_only": "safe", "empty": "unknown",
            "climate": "safe", "attention": "attention", "legacy": "safe"}
GROUND = ["living", "heating", "purifier", "temp_only"]


def availability(status, *, required=(), missing=(), controllers=(), basic=()):
    return {"status": status, "required_metrics": list(required),
            "missing_required_metrics": list(missing), "controllers": list(controllers),
            "missing_basic_metrics": list(basic)}


def controller(name, metric, *, missing=False):
    return {"controller_id": name.lower().replace(" ", "_"), "name": name,
            "metrics": [metric], "missing_metrics": [metric] if missing else []}


def room(area, name, values, status="safe", data=None):
    units = {"temperature": "°C", "humidity": "%", "pm25": "µg/m³", "co2": "ppm", "aqi": "AQI"}
    readings = [{"metric": metric, "value": value, "available": value is not None,
                 "unit": units[metric], "name": "Optional AQI" if metric == "aqi" else metric,
                 "entity_id": f"sensor.{area}_{metric}"}
                for metric, value in values.items()]
    result = {"area_id": area, "name": name, "status": status, "windows": [],
              "readings": readings, "action": None, "high_count": 0,
              "environment": {"measurement_evidence": {
                  r["metric"]: {"value": r["value"], "source_count": 1,
                                "source_ids": [r["entity_id"]]}
                  for r in readings if r["available"]},
                  "climate_plan": {"status": "ready", "controller": "environment",
                      "profile": "home", "temperature_c": values.get("temperature"),
                      "equipment_plan": {}, "actuation": {"status": "advisory_only"}}}}
    if data is not None:
        result["data_availability"] = data
    return result


def fixture():
    rooms = [
        room("living", "Wohnzimmer", {"temperature": 21.2, "humidity": 41.2, "aqi": None},
             data=availability("ready")),
        # A different valid room temperature must not disguise the exact
        # configured feedback input being absent from the controller.
        room("heating", "Heating room", {"temperature": 20.5, "humidity": 48}, "unknown",
             availability("missing", required=["temperature"], missing=["temperature"],
                          controllers=[controller("Radiator controller", "temperature", missing=True)])),
        room("purifier", "Purifier room", {"pm25": 8.1}, data=availability("ready",
             required=["pm25"], controllers=[controller("Air purifier", "pm25")],
             basic=["temperature", "humidity"])),
        room("temp_only", "Temperature only", {"temperature": 19.5},
             data=availability("partial", basic=["humidity"])),
        room("rh_only", "Humidity only", {"humidity": 45},
             data=availability("partial", basic=["temperature"])),
        room("empty", "Missing basics", {"co2": 700}, "unknown",
             availability("missing", basic=["temperature", "humidity"])),
        room("climate", "Climate only", {}, data=availability("partial", basic=["humidity"])),
        room("attention", "Humidity alert", {"temperature": 21, "humidity": 80}, "attention",
             availability("missing", required=["temperature"], missing=["temperature"],
                          controllers=[controller("Alert heater", "temperature", missing=True)])),
        # A rolling upgrade can still contain pre-contract inline data and
        # an unknown status caused by optional AQI or unconfigured windows.
        room("legacy", "Legacy room", {"temperature": 20.1, "humidity": 54.1, "aqi": None}, "unknown"),
    ]
    climate = next(r for r in rooms if r["area_id"] == "climate")
    climate["climate_only"] = True
    climate["environment"]["climate_plan"]["temperature_c"] = 22.1
    attention = next(r for r in rooms if r["area_id"] == "attention")
    attention["high_count"] = 1
    next(r for r in attention["readings"] if r["metric"] == "humidity").update(exceeded=True, threshold=65)
    dashboard = {"version": 1, "rooms": rooms,
                 # Deliberately stale; the rendered room set is authoritative.
                 "summary": {"safe": 0, "attention": 0, "unknown": 99},
                 "outdoor": {"status": "safe", "weather": [], "readings": [],
                             "warnings": [], "blockers": []}}
    states = {"sensor.hem": {"state": "ready", "attributes": {"dashboard": dashboard}}}
    for item in rooms:
        for reading in item["readings"]:
            states[reading["entity_id"]] = {
                "state": str(reading["value"]) if reading["available"] else "unavailable",
                "attributes": {"friendly_name": reading["name"], "unit_of_measurement": reading["unit"]}}
    return states


NODE_CHECKS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={innerWidth:760};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');
const make=()=>{
  const c=Object.create(Card.prototype);
  c._hass={language:'en',states:structuredClone(input.states),localize:()=>undefined,
    callService:()=>{throw Error('Room display sent a physical service call')}};
  c._config={entity:'sensor.hem'};c._expanded=new Set();c._roomsExpanded87=new Set();
  c._detailsExpanded66=new Set();c._interactions66=true;c._windowSwitchPending66=new Set();
  c._calibrationExpanded65=new Set();c._areaDeviceIds=new Map();c._roomIssues114=new Map();
  return c;
};
const rooms=c=>c._hass.states['sensor.hem'].attributes.dashboard.rooms;
const get=(c,id)=>rooms(c).find(r=>r.area_id===id);
const header=(c,id)=>c._room(get(c,id)).split('</summary>')[0];
const issueIcon=(c,id)=>header(c,id).match(/data-room-issue114="missing"[^>]*><ha-icon[^>]*icon="([^"]+)"/)?.[1];
const counts=html=>Object.fromEntries([['safe','good'],['attention','warn'],['unknown','neutral']].map(([key,tone])=>{
  const match=html.match(new RegExp('class="hem-overview-stat87 hem-overview-'+tone+'"[^>]*>[\\s\\S]*?<b>([0-9]+)</b>'));
  assert.ok(match,'Missing summary count '+key);return [key,Number(match[1])];
}));
const c=make(),before=JSON.stringify(c._hass.states);
assert.match(header(c,'legacy'),/\bhem-room-safe\b/,
  'Valid temperature and humidity must not become No data because optional AQI or windows are absent');
for(const [id,status] of Object.entries(input.expected)){
  assert.equal(c._roomStatus075(get(c,id)),status,id);
  assert.match(header(c,id),new RegExp('\\bhem-room-'+status+'\\b'),id);
}
assert.deepEqual(counts(c._summary({unknown:99},rooms(c))),{safe:6,attention:1,unknown:2});
assert.match(c._summary({unknown:99},rooms(c)),/<strong>9<\/strong>/,
  'The overview must include the climate-only room');
assert.deepEqual(c._roomInputs071(get(c,'heating')),{temperature:true,humidity:true});
assert.equal(issueIcon(c,'heating'),'mdi:help-circle-outline','Exact missing control input lost its required marker');
for(const id of ['living','purifier','temp_only','rh_only','climate','legacy'])
  assert.equal(issueIcon(c,id),'mdi:information-outline','Optional data gap was presented as No data: '+id);
for(const id of ['empty','attention'])assert.equal(issueIcon(c,id),'mdi:help-circle-outline',id);
const noWindows=structuredClone(get(c,'living'));
noWindows.readings=noWindows.readings.filter(r=>r.available);
assert.ok(!c._room(noWindows).split('</summary>')[0].includes('data-room-issue114="missing"'),
  'Unconfigured window contacts alone must not create a missing-measurement alert');
const evidenceOnly=structuredClone(get(c,'living'));
evidenceOnly.readings=[{metric:'mold',value:null,available:false,name:'Uncalibrated mold indication'}];
c._roomIssues114.set('living','missing');
assert.deepEqual(c._roomInputs071(evidenceOnly),{temperature:true,humidity:true});
const evidenceDetail=c._roomIssueDetail114(evidenceOnly);
assert.ok(evidenceDetail.includes('Uncalibrated mold indication'));
assert.ok(!evidenceDetail.includes('No valid indoor measurements are available'),
  'Valid shared temperature/humidity evidence was ignored by the optional diagnostic');
c._roomIssues114.set('heating','missing');
assert.match(c._roomIssueDetail114(get(c,'heating')),/Required control measurement is unavailable or outdated/,
  'Removing a blanket missing-data message must retain the actual control-input problem');
for(const language of ['en','el','de']){
  c._hass.language=language;c._roomIssues114.set('heating','missing');
  const metric={en:'Temperature',el:'Θερμοκρασία',de:'Temperatur'}[language];
  for(const html of [c._roomIssueDetail114(get(c,'heating')),c._roomMissingInfo071(get(c,'heating'))]){
    assert.ok(html.includes('Radiator controller'),language+' missing affected controller');
    assert.ok(html.includes(metric),language+' missing exact required metric');
  }
  c._roomIssues114.set('living','missing');
  const optional=c._roomIssueDetail114(get(c,'living'));
  assert.ok(optional.includes('Optional AQI'));
  assert.ok(!optional.includes('No window sensors')&&!optional.includes('Δεν έχουν επιλεγεί αισθητήρες παραθύρων'));
  assert.deepEqual(counts(c._summary({unknown:99},rooms(c))),{safe:6,attention:1,unknown:2});
}
// Fresh room RH and temperature do not establish a calibrated mold target.
// Explain the exact affected controller without inventing an indoor outage.
const unready=structuredClone(get(c,'living'));
unready.status='unknown';unready.readings=unready.readings.filter(row=>row.available);
unready.data_availability={status:'missing',required_metrics:['temperature','humidity'],
  missing_required_metrics:[],missing_basic_metrics:[],controllers:[{
    controller_id:'mold_dryer',name:'Mold dehumidifier',metrics:['temperature','humidity'],
    missing_metrics:[],target_ready:false,unavailable_reason:'needs_calibration',missing_inputs:[]}],
  unavailable_controllers:[{controller_id:'mold_dryer',name:'Mold dehumidifier',reason:'needs_calibration'}]};
const unreadyBefore=JSON.stringify(unready),control=unready.data_availability.controllers[0];
for(const language of ['en','el','de']){
  c._hass.language=language;c._roomIssues114.set('living','missing');
  assert.deepEqual(c._roomInputs071(unready),{temperature:true,humidity:true});
  assert.equal(c._roomControlMissing075(unready).length,1);
  assert.deepEqual(c._roomControlMissing075(unready)[0].metrics,[]);
  for(const html of [c._roomMissingInfo071(unready),c._roomIssueDetail114(unready)]){
    assert.ok(html.includes('Mold dehumidifier'),language+' lost unready controller');
    assert.ok(html.includes(c._t('moldNotCalibrated')),language+' missing calibration explanation');
    assert.ok(!html.includes('needs_calibration'),'Internal reason leaked into room help');
  }
}
assert.equal(JSON.stringify(unready),unreadyBefore,'Prerequisite display mutated room evidence');
control.unavailable_reason='inputs_unavailable';control.missing_inputs=['outdoor_temperature'];
for(const language of ['en','el','de']){
  c._hass.language=language;
  const html=c._roomMissingInfo071(unready);
  assert.ok(html.includes(c._t('moldInputsUnavailable')));
  assert.ok(html.includes(c._t('outside')+' · '+c._metricName('temperature')));
  assert.ok(!html.includes('inputs_unavailable')&&!html.includes('outdoor_temperature'));
  assert.deepEqual(c._roomControlMissing075(unready)[0].metrics,[]);
}
control.target_ready=true;control.missing_inputs=[];unready.data_availability.unavailable_controllers=[];
assert.equal(c._roomMissingInfo071(unready),'','Resolved prerequisites must not leave stale missing-data help');
c._hass.language='en';
c._floorRegistry140={floors:[{floor_id:'ground',name:'Ground floor'},{floor_id:'upper',name:'Upper floor'}],
  membership:new Map(rooms(c).map(r=>[r.area_id,input.ground.includes(r.area_id)?'ground':'upper']))};
const floorHTML=c._floorRooms140(rooms(c));
assert.match(floorHTML,/aria-label="Ground floor · 4 rooms · 1 unknown"/);
assert.match(floorHTML,/aria-label="Upper floor · 5 rooms · 1 need attention · 1 unknown"/);
for(const id of Object.keys(input.expected))assert.equal(
  (floorHTML.match(new RegExp('data-room-fold87="'+id+'"','g'))||[]).length,1,id+' floor membership duplicated');
// Older inline snapshots have no explicit control contract. Their fallback
// keeps one usable basic measurement, genuine attention and true absence.
for(const [source,status] of [['temp_only','safe'],['rh_only','safe'],['empty','unknown'],['attention','attention']]){
  const item=structuredClone(get(c,source));delete item.data_availability;
  if(status!=='attention')item.status='unknown';
  assert.equal(c._roomStatus075(item),status,'Legacy fallback '+source);
}
assert.equal(JSON.stringify(c._hass.states),before,'Read-only room classification mutated source evidence');
console.log('ROOM_DATA_REQUIREMENTS_OPTIONAL_GAPS_LEGACY_COUNTS_FLOORS=PASS');
"""


def icon_fixture():
    spec = importlib.util.spec_from_file_location(
        "room_data_activity_fixture", ROOT / ".github/tests/test_beta112_room_activity.py")
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    return baseline.layout_helpers()["ICON_FIXTURE"]


def browser_checks(states):
    from playwright.sync_api import expect, sync_playwright

    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
        shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome, "Chromium required"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        for language in ("en", "el", "de"):
            page = browser.new_page(viewport={"width": 760, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_content("""<!doctype html><html><head><style>
              *{box-sizing:border-box}body{margin:0;background:#111;color:#eee;font-family:Arial}
              :root{--primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;
                --card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}
            </style></head><body></body></html>""")
            page.evaluate(icon_fixture())
            page.add_script_tag(path=str(CARD))
            page.evaluate("""({language,states,ground})=>{
              window.calls=[];window.requests=[];
              const floors=[{floor_id:'ground',name:'Ground floor'},{floor_id:'upper',name:'Upper floor'}];
              const areas=states['sensor.hem'].attributes.dashboard.rooms.map(r=>({
                area_id:r.area_id,name:r.name,floor_id:ground.includes(r.area_id)?'ground':'upper'}));
              window.card=document.createElement('home-environment-manager-card');document.body.append(card);
              card._config={entity:'sensor.hem'};
              card._hass={language,states,connection:{},user:{is_admin:false},localize:()=>undefined,
                callWS:async message=>{
                  requests.push(message);
                  if(message.type==='config/floor_registry/list')return floors;
                  if(message.type==='config/area_registry/list')return areas;
                  throw Error('Unexpected write or request: '+message.type);
                },callService:(...args)=>{calls.push(args);throw Error('Room display sent a device command')}};
              card._renderContent(true);
            }""", {"language": language, "states": deepcopy(states), "ground": GROUND})
            page.wait_for_function("card._floorRegistry140?.floors.length===2")
            for width in (320, 390, 760):
                page.set_viewport_size({"width": width, "height": 1000})
                report = page.evaluate("""()=>{
                  const root=card.shadowRoot;
                  return {counts:Object.fromEntries([['safe','good'],['attention','warn'],['unknown','neutral']]
                    .map(([key,tone])=>[key,Number(root.querySelector('.hem-overview-'+tone+' b').textContent)])),
                    total:Number(root.querySelector('.hem-overview-title87 strong').textContent),
                    rows:[...root.querySelectorAll('[data-room-fold87]')].map(row=>({
                      id:row.getAttribute('data-room-fold87'),classes:row.className,
                      icon:row.querySelector(':scope>summary [data-room-issue114="missing"] ha-icon')?.getAttribute('icon'),
                      status:row.querySelector('article>.room-heading>.status-tag')?.textContent.trim(),
                      left:row.getBoundingClientRect().left,right:row.getBoundingClientRect().right})),
                    floors:[...root.querySelectorAll('.hem-floor-summary140')].map(n=>n.getAttribute('aria-label'))};
                }""")
                assert report["counts"] == {"safe": 6, "attention": 1, "unknown": 2}, report
                assert report["total"] == 9 and len(report["rows"]) == 9, report
                # The fixture's expected statuses are independent of the
                # renderer; label spelling comes from its translated UI API.
                labels = page.evaluate("()=>Object.fromEntries(['safe','attention','unknown'].map(k=>[k,card._t(k)]))")
                for row in report["rows"]:
                    status = EXPECTED[row["id"]]
                    assert "hem-room-" + status in row["classes"], (language, width, row)
                    if row["id"] != "climate":
                        assert row["status"] == labels[status], (language, row)
                    assert row["left"] >= -1 and row["right"] <= width + 1, (width, row)
                    expected_icon = "mdi:help-circle-outline" if row["id"] in ("heating", "empty", "attention") else "mdi:information-outline"
                    assert row["icon"] == expected_icon, (language, row)
                floor_words = page.evaluate("card._floorWords140()")
                assert report["floors"] == [
                    f"Ground floor · 4 {floor_words['rooms']} · 1 {floor_words['unknown']}",
                    f"Upper floor · 5 {floor_words['rooms']} · 1 {floor_words['attention']} · 1 {floor_words['unknown']}",
                ], report["floors"]
                # Click the existing compact icon. The expanded diagnostic
                # names the controller and the exact unavailable metric.
                heating = page.locator('[data-room-fold87="heating"]')
                heating.locator(':scope>summary [data-room-issue114="missing"]').click()
                detail = heating.locator('[data-room-issue-detail114="missing"]')
                expect(detail).to_be_visible()
                assert "Radiator controller" in detail.inner_text()
                assert {"en": "Temperature", "el": "Θερμοκρασία", "de": "Temperatur"}[language] in detail.inner_text()
                heating.locator(':scope>summary [data-room-issue114="missing"]').click()
                living = page.locator('[data-room-fold87="living"]')
                living.locator(':scope>summary [data-room-issue114="missing"]').click()
                optional = living.locator('[data-room-issue-detail114="missing"]')
                expect(optional).to_be_visible()
                assert "Optional AQI" in optional.inner_text()
                living.locator(':scope>summary [data-room-issue114="missing"]').click()
            # Shared measurement evidence can be usable even when the only
            # entry in readings is an unavailable optional mold indication.
            page.evaluate("""()=>{
              const state=structuredClone(card._hass.states['sensor.hem']);
              const room=state.attributes.dashboard.rooms.find(r=>r.area_id==='living');
              room.readings=[{metric:'mold',value:null,available:false,name:'Uncalibrated mold indication'}];
              state.attributes.dashboard.rooms=[room];
              card._hass={...card._hass,states:{...card._hass.states,'sensor.hem':state}};
              card._renderContent(true);
            }""")
            living = page.locator('[data-room-fold87="living"]')
            assert "hem-room-safe" in living.get_attribute("class")
            living.locator(':scope>summary [data-room-issue114="missing"]').click()
            detail = living.locator('[data-room-issue-detail114="missing"]')
            expect(detail).to_be_visible()
            assert "Uncalibrated mold indication" in detail.inner_text()
            false_missing = {"en": "No valid indoor measurements are available.",
                             "el": "Δεν υπάρχουν έγκυρες μετρήσεις εσωτερικού χώρου.",
                             "de": "Keine gültigen Innenraummesswerte verfügbar."}[language]
            assert false_missing not in detail.inner_text()
            assert page.evaluate("calls") == []
            assert page.evaluate("requests.every(r=>['config/floor_registry/list','config/area_registry/list'].includes(r.type))")
            assert not errors, errors
            page.close()
        browser.close()
    print("ROOM_DATA_CHROMIUM_COUNTS_FLOORS_DIAGNOSTICS_EN_EL_DE_MOBILE=PASS")


if __name__ == "__main__":
    states = fixture()
    result = subprocess.run(["node", "-e", NODE_CHECKS, str(CARD)],
        input=json.dumps({"states": states, "expected": EXPECTED, "ground": GROUND}), text=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    if "--logic-only" not in sys.argv:
        browser_checks(states)
