"""Beta112: room icon colours follow reported native activity, not PID intent.

Run --logic-only for the actual production card's rendered room markup and
update signatures in Node. The full run also verifies computed icon colours,
native-only HA updates, room isolation, compact geometry and read-only clicks
in Chromium. HEM_TEST_SCREENSHOT_DIR captures active/idle desktop and mobile.
No Home Assistant services or physical devices are contacted.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"


def fixture():
    states, rooms = {}, []
    for area, name in (
        ("heat", "Wohnzimmer"), ("cool", "Schlafzimmer"),
        ("humidify", "Gästezimmer"), ("dry", "Badezimmer"),
        ("air", "Küche"), ("mixed", "Arbeitszimmer"),
    ):
        room = {"area_id": area, "name": name, "status": "safe", "action": None,
                "windows": [], "readings": [], "environment": {
                    "measurement_evidence": {}, "climate_plan": {
                        "status": "ready", "controller": "environment", "profile": "home",
                        "temperature_c": 21.3, "equipment_plan": {
                            "humidity": {"status": "advisory", "measured_rh": 54.2, "action": "idle"}},
                        "actuation": {"status": "advisory_only"}}}}
        for metric, value, unit in (
            ("temperature", 21.3, "°C"), ("humidity", 54.2, "%"),
            ("co2", 718, "ppm"), ("pm25", 7.2, "µg/m³"),
        ):
            ids = [f"sensor.{area}_{metric}"]
            if metric == "temperature":
                ids.append(f"sensor.{area}_{metric}_b")
            for entity_id in ids:
                states[entity_id] = {"state": str(value), "attributes": {
                    "friendly_name": f"{name} {metric}", "unit_of_measurement": unit}}
            room["readings"].append({"metric": metric, "value": value,
                "unit": unit, "available": True, "name": metric.title(), "entity_id": ids[0]})
            room["environment"]["measurement_evidence"][metric] = {
                "value": value, "source_count": len(ids), "source_ids": ids, "trend": []}
        rooms.append(room)

    def device(area, native, state, *, action=None, mode="heat", purpose=None, **attrs):
        slug = native.split(".", 1)[1]
        domain = native.split(".", 1)[0]
        if action is not None:
            attrs["action" if domain == "humidifier" else "hvac_action"] = action
        states[native] = {"state": state, "attributes": {
            "friendly_name": slug.replace("_", " ").title(), **attrs}}
        common = {"area_id": area, "source_device_id": "device_" + slug,
                  "source_entity_ids": [native]}
        states[f"climate.managed_{slug}"] = {"state": mode, "attributes": {
            **common, "friendly_name": "HEM " + slug, "control_mode": "pid",
            "requested_hvac_mode": mode, "physical_primary_entity_id": native,
            "physical_source_state": state, "physical_hvac_mode": mode,
            "hvac_modes": ["off", mode], "supported_features": 1,
            "current_temperature": 21.3, "temperature": 21, "humidity": 55,
            "controller_status": {"status": "controlling", "demand_percent": 100},
            "measurements": {"temperature": 21.3, "humidity": 54.2}}}
        states[f"select.method_{slug}"] = {"state": "pid", "attributes": {
            **common, "options": ["existing", "automatic", "manual", "off", "pid"]}}
        if purpose:
            states[f"select.purpose_{slug}"] = {"state": purpose, "attributes": {
                **common, "options": ["auto", "extraction", "filtration"]}}

    device("heat", "climate.heater", "heat", action="heating")
    device("cool", "climate.cooler", "cool", action="cooling", mode="cool")
    device("humidify", "humidifier.moisture", "on", action="humidifying", device_class="humidifier")
    device("dry", "humidifier.dryer", "on", action="drying", mode="dry", device_class="dehumidifier")
    device("air", "fan.purifier", "on", mode="fan_only", purpose="filtration", percentage=50)
    device("mixed", "climate.mixed_heat", "heat", action="heating")
    device("mixed", "climate.mixed_cool", "cool", action="cooling", mode="cool")
    device("mixed", "humidifier.mixed_wet", "on", action="humidifying", device_class="humidifier")
    device("mixed", "humidifier.mixed_dry", "on", action="dehumidifying", mode="dry", device_class="dehumidifier")
    # Same-device ventilation is not inferred from a heater's companion fan.
    states["climate.managed_heater"]["attributes"]["source_entity_ids"].append("fan.heater_companion")
    states["select.method_heater"]["attributes"]["source_entity_ids"] = ["climate.heater", "fan.heater_companion"]
    states["fan.heater_companion"] = {"state": "on", "attributes": {"percentage": 60}}
    dashboard = {"version": 1, "rooms": rooms,
        "summary": {"safe": len(rooms), "attention": 0, "unknown": 0},
        "outdoor": {"status": "safe", "blockers": [], "warnings": [],
            "weather": [{"condition": "partlycloudy", "temperature_c": 8.9, "wind_kmh": 17}],
            "readings": [{"metric": "aqi", "value": 13, "unit": "US AQI", "available": True}]}}
    states["sensor.hem"] = {"state": "ready", "attributes": {"dashboard": dashboard}}
    return states


NODE_CHECKS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');
const make=()=>{
  const card=Object.create(Card.prototype);
  card._hass={language:'en',states:structuredClone(input.states),localize:()=>undefined,
    callService:()=>{throw Error('Display logic sent a service call')}};
  card._interactions66=true;card._detailsExpanded66=new Set();
  card._windowSwitchPending66=new Set();card._calibrationExpanded65=new Set();
  card._expanded=new Set();
  card._areaDeviceIds=new Map();card._config={entity:'sensor.hem'};
  return card;
};
const glance=(card,area)=>{
  const room=card._hass.states['sensor.hem'].attributes.dashboard.rooms.find(r=>r.area_id===area);
  const html=card._room(room);
  return html.slice(0,html.indexOf('</summary>'));
};
const metricTones=html=>[...html.matchAll(/class="[^"]*hem-room-metric107[^"]*hem-activity-([a-z]+)[^"]*"/g)].map(m=>m[1]);
const expect=(card,area,tones)=>assert.deepEqual(metricTones(glance(card,area)),tones,area);
const replace=(card,id,value)=>{card._hass={...card._hass,states:{...card._hass.states,[id]:value}}};
const c=make(),states=c._hass.states;
const before=JSON.stringify(states);
expect(c,'heat',['heat','neutral','neutral','neutral']);
expect(c,'cool',['cool','neutral','neutral','neutral']);
expect(c,'humidify',['neutral','humidify','neutral','neutral']);
expect(c,'dry',['neutral','dry','neutral','neutral']);
expect(c,'air',['neutral','neutral','neutral','filtration']);
expect(c,'mixed',['mixed','mixed','neutral','neutral']);
assert.ok(glance(c,'heat').includes('hem-room-icon112 hem-activity-heat'));
assert.ok(glance(c,'mixed').includes('hem-room-icon112 hem-activity-mixed'));
assert.ok(glance(c,'heat').includes('mdi:fire'));
assert.ok(glance(c,'cool').includes('mdi:snowflake'));
assert.ok(glance(c,'air').includes('Filtering air'));
assert.equal(JSON.stringify(states),before,'Rendering changed evidence');

for(const action of ['idle','off','unknown','',null]) {
  const card=make(),native=structuredClone(card._hass.states['humidifier.moisture']);
  if(action===null)delete native.attributes.action;else native.attributes.action=action;
  replace(card,'humidifier.moisture',native);
  expect(card,'humidify',['neutral','neutral','neutral','neutral']);
}
for(const state of ['off','unknown','unavailable']) {
  const card=make(),native={...card._hass.states['climate.heater'],state};
  replace(card,'climate.heater',native);
  expect(card,'heat',['neutral','neutral','neutral','neutral']);
}
for(const action of ['idle','off','unknown',null]) {
  const card=make(),native=structuredClone(card._hass.states['climate.heater']);
  if(action===null)delete native.attributes.hvac_action;else native.attributes.hvac_action=action;
  replace(card,'climate.heater',native);
  expect(card,'heat',['neutral','neutral','neutral','neutral']);
}
const sig=c._controllerSignature();
const idle=structuredClone(c._hass.states['humidifier.moisture']);idle.attributes.action='idle';
replace(c,'humidifier.moisture',idle);
assert.notEqual(c._controllerSignature(),sig,'Humidifier action change did not invalidate render');
expect(c,'humidify',['neutral','neutral','neutral','neutral']);
expect(c,'heat',['heat','neutral','neutral','neutral']);
const extract=structuredClone(c._hass.states['select.purpose_purifier']);extract.state='extraction';
replace(c,'select.purpose_purifier',extract);
expect(c,'air',['neutral','neutral','ventilation','ventilation']);
const zero=structuredClone(c._hass.states['fan.purifier']);zero.attributes.percentage=0;
replace(c,'fan.purifier',zero);
expect(c,'air',['neutral','neutral','neutral','neutral']);

for(const [id,value] of [['number.valve','50'],['input_number.valve','25'],['switch.heater','on']]) {
  const card=make(),source=card._hass.states['climate.managed_heater'];
  const attrs=structuredClone(source.attributes);
  attrs.source_entity_ids=[id];attrs.physical_primary_entity_id=id;
  attrs.physical_source_state=value;attrs.physical_hvac_mode='heat';
  replace(card,'climate.managed_heater',{...source,attributes:attrs});
  replace(card,id,{state:value,attributes:{}});
  expect(card,'heat',['heat','neutral','neutral','neutral']);
  assert.ok(glance(card,'heat').includes('Heating output on'));
  for(const bad of [
    {...attrs,physical_primary_entity_id:'climate.unrelated'},
    {...attrs,physical_hvac_mode:undefined},
    {...attrs,physical_source_state:'off'},
    {...attrs,upstream_power_switch:id},
  ]) {
    replace(card,'climate.managed_heater',{...source,attributes:bad});
    expect(card,'heat',['neutral','neutral','neutral','neutral']);
  }
  replace(card,'climate.managed_heater',{...source,attributes:attrs});
  replace(card,id,{state:id.startsWith('switch.')?'off':'0',attributes:{}});
  expect(card,'heat',['neutral','neutral','neutral','neutral']);
}
const foreign=make(),native=structuredClone(foreign._hass.states['climate.heater']);
native.attributes.area_id='cool';replace(foreign,'climate.heater',native);
expect(foreign,'heat',['neutral','neutral','neutral','neutral']);
for(const language of ['en','de','el']) {
  const card=make();card._hass.language=language;
  const expected={en:'Humidifying',de:'Befeuchtet',el:'Υγραίνει'}[language];
  assert.ok(glance(card,'humidify').includes(expected));
}
console.log('BETA112_NATIVE_ACTIVITY_MARKUP_AND_SIGNATURES=PASS');
"""


def layout_helpers():
    """Reuse Beta107 geometry checks without importing its browser side effects."""
    path = ROOT / ".github/tests/test_beta107_room_metrics.py"
    nodes = []
    for node in ast.parse(path.read_text(), filename=str(path)).body:
        if isinstance(node, ast.FunctionDef) and node.name in ("px", "assert_layout"):
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in ("ICON_FIXTURE", "LAYOUT_REPORT")
            for target in node.targets
        ):
            nodes.append(node)
    scope = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)
    return scope


COLOURS = {"heat": "rgb(242, 138, 75)", "cool": "rgb(80, 186, 255)",
    "humidify": "rgb(54, 203, 184)", "dry": "rgb(229, 173, 68)",
    "filtration": "rgb(73, 201, 139)", "ventilation": "rgb(77, 199, 217)",
    "mixed": "rgb(184, 163, 248)"}
REPORT = """area=>{
 const root=card.shadowRoot.querySelector('[data-room-fold87="'+area+'"] > summary');
 const colour=el=>getComputedStyle(el).color;
 return {home:colour(root.querySelector('.hem-room-icon112')),
   metric:[...root.querySelectorAll('.hem-room-metric107')].map(el=>({
     colour:colour(el.querySelector(':scope > ha-icon')),valueColour:colour(el.querySelector('.hem-room-metric-value107')),
     average:el.querySelector('.hem-avg-marker105 ha-icon')?colour(el.querySelector('.hem-avg-marker105 ha-icon')):null,
     title:el.title})),
   active:[...root.querySelectorAll('.hem-room-active87 .hem-hint87')].map(el=>({
     colour:colour(el.querySelector('ha-icon')),title:el.title,icon:el.querySelector('ha-icon').getAttribute('icon')}))};
}"""


def browser_checks(states):
    from playwright.sync_api import sync_playwright

    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
        shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome, "Chromium required"
    helpers = layout_helpers()
    output = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
    if output:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 590, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content("""<!doctype html><html><head><style>
          *{box-sizing:border-box}body{margin:0;background:#111;color:#ddd;font-family:Arial,sans-serif}
          :root{--primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;
          --card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}
          #card-frame{width:100%;max-width:100%}
        </style></head><body><main id="card-frame"></main></body></html>""")
        page.evaluate(helpers["ICON_FIXTURE"])
        page.add_script_tag(path=str(CARD))
        page.evaluate("""states=>{
          window.calls=[];window.info=[];
          window.card=document.createElement('home-environment-manager-card');
          document.getElementById('card-frame').append(card);
          card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
          card._hass={language:'el',states,localize:()=>undefined,
            callService:(...args)=>{calls.push(args);return Promise.resolve()}};
          card._config={entity:'sensor.hem'};card._renderContent(true);
        }""", states)
        neutral = page.evaluate(REPORT, "heat")["metric"][1]["colour"]
        for area, metric, tone in (("heat", 0, "heat"), ("cool", 0, "cool"),
                ("humidify", 1, "humidify"), ("dry", 1, "dry"), ("air", 3, "filtration")):
            report = page.evaluate(REPORT, area)
            assert report["home"] == COLOURS[tone], (area, report)
            assert report["metric"][metric]["colour"] == COLOURS[tone], (area, report)
            assert report["active"][0]["colour"] == COLOURS[tone], (area, report)
            assert report["metric"][metric]["valueColour"] != COLOURS[tone], (area, report)
        mixed = page.evaluate(REPORT, "mixed")
        assert mixed["home"] == mixed["metric"][0]["colour"] == mixed["metric"][1]["colour"] == COLOURS["mixed"]
        assert {a["colour"] for a in mixed["active"]} >= {COLOURS["heat"], COLOURS["cool"]}
        assert page.evaluate(REPORT, "air")["metric"][2]["colour"] == neutral, "Purifier implied CO2 removal"
        assert page.evaluate(REPORT, "heat")["metric"][0]["average"] not in COLOURS.values()

        for phase in ("active", "idle"):
            if phase == "idle":
                # Keep the recommendation sensor and all HEM facade objects
                # identical. Only native reports change through the HA setter.
                page.evaluate("""()=>{
                  window.previousSensor=card._hass.states['sensor.hem'];
                  window.previousRow=card.shadowRoot.querySelector('[data-room-fold87="humidify"]');
                  const states={...card._hass.states};
                  for(const [id,old] of Object.entries(states)) {
                    if(id.startsWith('climate.')&&!id.startsWith('climate.managed_'))
                      states[id]={...old,attributes:{...old.attributes,hvac_action:'idle'}};
                    if(id.startsWith('humidifier.'))states[id]={...old,attributes:{...old.attributes,action:'idle'}};
                    if(id.startsWith('fan.'))states[id]={...old,state:'off'};
                  }
                  card.hass={...card._hass,states};
                }""")
                page.wait_for_function("""()=>[...card.shadowRoot.querySelectorAll(
                  '[data-room-fold87="humidify"] .hem-room-reading87')]
                    .every(el=>el.classList.contains('hem-activity-neutral'))""")
                assert page.evaluate("card._hass.states['sensor.hem']===previousSensor")
                assert page.evaluate("card.shadowRoot.querySelector('[data-room-fold87=\"humidify\"]')===previousRow")
                for area in ("heat", "cool", "humidify", "dry", "air", "mixed"):
                    report = page.evaluate(REPORT, area)
                    assert report["home"] == neutral and not report["active"], (area, report)
                    assert all(metric["colour"] == neutral for metric in report["metric"]), (area, report)
            for width in (590, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                helpers["assert_layout"](page.evaluate(helpers["LAYOUT_REPORT"]), f"{phase} {width}")
                if output:
                    page.locator('#card-frame').screenshot(path=str(output / f"room-activity-{phase}-{width}.png"))

        # An action-only update re-colours one room without touching others.
        page.evaluate("""()=>{
          const old=card._hass.states['humidifier.moisture'];
          card.hass={...card._hass,states:{...card._hass.states,'humidifier.moisture':{
            ...old,attributes:{...old.attributes,action:'humidifying'}}}};
        }""")
        page.wait_for_function("""()=>card.shadowRoot.querySelector(
          '[data-room-fold87="humidify"] .hem-activity-humidify')!==null""")
        assert page.evaluate(REPORT, "humidify")["metric"][1]["colour"] == COLOURS["humidify"]
        assert page.evaluate(REPORT, "heat")["metric"][0]["colour"] == neutral
        # Existing single-source/average interactions remain read-only.
        page.locator('[data-room-fold87="humidify"] > .hem-room-glance87 > [data-hem-source105="sensor.humidify_humidity"]').click()
        assert page.evaluate("info") == ["sensor.humidify_humidity"]
        assert page.locator('[data-room-fold87="humidify"]').get_attribute("open") is None
        assert page.evaluate("calls") == []
        assert not errors, errors
        browser.close()
    print("BETA112_COMPUTED_ROOM_ACTIVITY_COLOURS_NATIVE_UPDATES_LAYOUT=PASS")


if __name__ == "__main__":
    states = fixture()
    subprocess.run(["node", "-e", NODE_CHECKS, str(CARD)],
        input=json.dumps({"states": states}), text=True, check=True)
    if "--logic-only" not in sys.argv:
        browser_checks(states)
