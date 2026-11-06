"""Beta116: truthful compact pollutant labels survive real sensor names.

Uses the production card in Chromium with deterministic sensor fixtures. Checks
320/390/590px cards, full source names, units and native/average navigation.
--logic-only runs the actual production markup in Node without a browser.
No Home Assistant services, real devices or network requests are involved.
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


def fixture_helpers():
    """Share the established icon/geometry harness without running its suite."""
    path = ROOT / ".github/tests/test_beta107_room_metrics.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = {"baseline_fixture", "evidence", "px", "assert_layout"}
    constants = {"ICON_FIXTURE", "LAYOUT_REPORT"}
    nodes = [node for node in tree.body if (
        isinstance(node, ast.FunctionDef) and node.name in functions
    ) or (
        isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in constants
            for target in node.targets)
    )]
    namespace = {"ROOT": ROOT, "ast": ast, "deepcopy": deepcopy}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    assert functions | constants <= namespace.keys()
    return namespace


helpers = fixture_helpers()
data = helpers["baseline_fixture"]()
states = {"sensor.hem": {"state": "ready", "attributes": {"dashboard": data}}}
long_name = "Gästezimmer Multisensor Luftgüte flüchtige organische Verbindungen – obere Fensterseite"
# The long and unfamiliar metric verifies the bounded fallback without guessing
# what a sensor measures from its friendly name.
unknown_metric = "manufacturer_specific_air_quality_measurement"
room_specs = [
    ("Badezimmer", 19.8, 57.2, [("illuminance", 49, "lx", "Lux", False)]),
    ("Gästezimmer", 19.8, 56.7, [("pm25", 1, "µg/m³", "PM2.5", False),
                               ("voc_parts", 505, "ppb", "VOC", False)]),
    ("Küche", 21.4, 52.4, [("voc", 80, None, "VOC", True)]),
    ("Schlafzimmer", 17.4, 58.5, [("voc_index", 110, "", "VOC index", False)]),
    ("Wohnzimmer", 20.0, 54.2, [("tvoc", 65, "µg/m³", "TVOC", False),
                               (unknown_metric, 12, "", unknown_metric.replace("_", " ").upper(), False)]),
]
expected = []
for room, (name, temperature, humidity, extras) in zip(data["rooms"], room_specs):
    area = room["area_id"]
    room.update(name=name, status="safe", action=None)
    room["windows"] = []
    room["readings"] = []
    room["environment"]["measurement_evidence"] = measurements = {}
    for metric, value, unit, short, average in [
        ("temperature", temperature, "°C", None, False),
        ("humidity", humidity, "%", None, False), *extras,
    ]:
        ids = [f"sensor.{area}_{metric}"]
        if average:
            ids.append(f"sensor.{area}_{metric}_second")
        friendly = f"{long_name} ({metric})"
        item = {"metric": metric, "value": value, "available": True, "name": friendly}
        if unit is not None:
            item["unit"] = unit
        if not average:
            item["entity_id"] = ids[0]
        room["readings"].append(item)
        measurements[metric] = helpers["evidence"](value, ids)
        for index, entity_id in enumerate(ids):
            states[entity_id] = {"state": str(value), "attributes": {
                "friendly_name": friendly + (f" {index + 1}" if average else ""),
                "unit_of_measurement": unit if unit is not None else "µg/m³"}}
        if short:
            expected.append((area, metric, short, friendly, ids))
data["summary"] = {"safe": 5, "attention": 0, "unknown": 0}
data["outdoor"].update(status="safe", blockers=[], warnings=[])

def logic_checks():
    script = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');
const card=Object.create(Card.prototype);
card._hass={language:'de',states:input.states,localize:()=>undefined,
  callService:()=>{throw Error('Display logic sent a service call')}};
card._interactions66=true;card._detailsExpanded66=new Set();
card._windowSwitchPending66=new Set();card._calibrationExpanded65=new Set();
card._expanded=new Set();card._areaDeviceIds=new Map();card._config={entity:'sensor.hem'};
const before=JSON.stringify(input.states);
const rooms=input.states['sensor.hem'].attributes.dashboard.rooms;
for(const [area,metric,short,friendly,ids] of input.expected){
  const room=rooms.find(r=>r.area_id===area);
  const markup=card._room(room).split('</summary>')[0];
  const badge=[...markup.matchAll(/<button[^>]*>[\s\S]*?<\/button>/g)]
    .map(match=>match[0]).find(html=>html.includes(ids.length>1?
      `data-hem-average105="${metric}"`:`data-hem-source105="${ids[0]}"`));
  assert.ok(badge,`${area}/${metric}: no source button`);
  assert.ok(badge.includes(`class="hem-room-metric-label107">${short}</span>`),`${metric}: wrong label`);
  assert.ok(badge.includes(friendly),`${metric}: full sensor name lost`);
  assert.ok(!badge.replace(/<[^>]*>/g,'').includes(input.long_name),`${metric}: friendly name in compact text`);
  if(metric==='voc')assert.ok(badge.includes('µg/m³'), 'VOC mass unit lost');
  if(metric==='voc_parts')assert.ok(badge.includes('ppb'), 'VOC parts unit lost');
}
// Native source IDs and the incoming room evidence are never rewritten.
assert.equal(JSON.stringify(input.states),before);
console.log('BETA116_COMPACT_METRIC_LABELS_RENDER_UNITS_SOURCE_IDS=PASS');
"""
    result = subprocess.run([shutil.which("node") or "node", "-e", script, str(CARD)],
        input=json.dumps({"states": states, "expected": expected, "long_name": long_name}),
        text=True, capture_output=True, check=True)
    print(result.stdout.strip())


logic_checks()
if "--logic-only" in sys.argv:
    raise SystemExit(0)

from playwright.sync_api import sync_playwright


chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
    shutil.which("chromium") or shutil.which("google-chrome"))
assert chrome and Path(chrome).is_file(), "Chromium required"
screenshot_dir = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
if screenshot_dir:
    screenshot_dir = Path(screenshot_dir)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=chrome, headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 590, "height": 990})
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
    page.evaluate("""({states}) => {
      window.info=[];window.calls=[];
      window.card=document.createElement('home-environment-manager-card');
      document.getElementById('card-frame').append(card);
      card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
      card._hass={language:'de',states,localize:()=>undefined,callWS:async()=>({}),
        callService:(...args)=>{calls.push(args);return Promise.resolve()}};
      card._config={entity:'sensor.hem'};card._renderContent(true);
    }""", {"states": states})

    def trigger(area, metric, ids):
        attribute = (f'data-hem-average105="{metric}"' if len(ids) > 1
                     else f'data-hem-source105="{ids[0]}"')
        return page.locator(f'[data-room-fold87="{area}"] .hem-room-glance87 [{attribute}]')

    # Canonical kinds must remain compact while names and original entity IDs
    # stay intact for assistive descriptions and native history navigation.
    for area, metric, short, friendly, ids in expected:
        badge = trigger(area, metric, ids)
        assert badge.count() == 1, (area, metric)
        assert badge.locator('.hem-room-metric-label107').text_content() == short, (area, metric)
        assert long_name not in badge.text_content(), (area, metric)
        assert friendly in badge.get_attribute('title'), (area, metric)
        assert friendly in badge.get_attribute('aria-label'), (area, metric)
        if metric != unknown_metric:
            label = badge.locator('.hem-room-metric-label107')
            assert label.evaluate('el=>el.scrollWidth<=el.clientWidth+1'), (metric, "known label clipped")
    assert trigger('room1', 'voc_parts', ['sensor.room1_voc_parts']).locator(
        '.hem-room-metric-unit107').text_content() == 'ppb'
    assert trigger('room2', 'voc', ['sensor.room2_voc', 'sensor.room2_voc_second']).locator(
        '.hem-room-metric-unit107').text_content() == 'µg/m³'
    assert trigger('room3', 'voc_index', ['sensor.room3_voc_index']).locator(
        '.hem-room-metric-unit107').count() == 0

    for width in (590, 390, 320):
        page.set_viewport_size({"width": width, "height": 990})
        page.evaluate("document.getElementById('card-frame').style.width='100%'")
        if screenshot_dir:
            page.locator('#card-frame').screenshot(path=str(screenshot_dir / f"beta116-metrics-{width}.png"))
        helpers["assert_layout"](page.evaluate(helpers["LAYOUT_REPORT"]), f"long names / {width}px")
    page.set_viewport_size({"width": 1280, "height": 990})
    for width in (320, 390, 590):
        page.evaluate("width=>document.getElementById('card-frame').style.width=width+'px'", width)
        helpers["assert_layout"](page.evaluate(helpers["LAYOUT_REPORT"]), f"desktop column / {width}px")

    page.set_viewport_size({"width": 590, "height": 990})
    page.evaluate("document.getElementById('card-frame').style.width='100%'")
    guest = page.locator('[data-room-fold87="room1"]')
    trigger('room1', 'voc_parts', ['sensor.room1_voc_parts']).click()
    assert page.evaluate('info') == []
    assert page.evaluate('card._averageDialog105.entity122') == 'sensor.room1_voc_parts'
    page.locator('.hem-avg-dialog105 [data-open-entity122="sensor.room1_voc_parts"]').click()
    assert page.evaluate('info') == ['sensor.room1_voc_parts']
    assert guest.get_attribute('open') is None, "metric click expanded room"
    assert page.locator('.hem-avg-dialog105').count() == 0

    # Reuse the exact kind, rather than aliasing voc_parts into another kind,
    # when multiple native sources are presented through the average popup.
    page.evaluate("""() => {
      const room=card._hass.states['sensor.hem'].attributes.dashboard.rooms[1];
      const extra='sensor.room1_voc_parts_second';
      card._hass.states[extra]={state:'505',attributes:{friendly_name:'Gästezimmer VOC second',unit_of_measurement:'ppb'}};
      room.environment.measurement_evidence.voc_parts.source_ids.push(extra);
      room.environment.measurement_evidence.voc_parts.source_count=2;
      card._renderContent(true);
    }""")
    average = trigger('room1', 'voc_parts', ['sensor.room1_voc_parts', 'sensor.room1_voc_parts_second'])
    assert average.locator('.hem-room-metric-label107').text_content() == 'VOC'
    average.click()
    popup = page.locator('.hem-avg-dialog105')
    popup.wait_for(state='visible')
    assert popup.locator('.hem-avg-line105').count() == 1
    actual = popup.locator('[data-hem-source105]').evaluate_all(
        "nodes=>nodes.map(node=>node.getAttribute('data-hem-source105'))")
    assert actual == ['sensor.room1_voc_parts', 'sensor.room1_voc_parts_second'], actual
    assert long_name in popup.text_content(), "average details lost full native name"
    assert guest.get_attribute('open') is None
    popup.locator('[data-hem-source105="sensor.room1_voc_parts"]').click()
    assert page.evaluate('info') == ['sensor.room1_voc_parts']
    assert page.evaluate('card._averageDialog105.entity122') == 'sensor.room1_voc_parts'
    popup.locator('[data-open-entity122="sensor.room1_voc_parts"]').click()
    assert page.evaluate('info') == ['sensor.room1_voc_parts', 'sensor.room1_voc_parts']
    assert popup.count() == 0
    assert page.evaluate('calls') == [], "read-only metric interaction sent a service call"
    assert not errors, errors
    browser.close()

print('BETA116_COMPACT_METRIC_LABELS_UNITS_RESPONSIVE_NATIVE_AVERAGES=PASS')
