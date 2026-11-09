"""Beta122 device navigation, compact announcements and complementary room tiles.

The real card runs in Node for deterministic provenance/markup assertions and
in Chromium for actual DOM events, layout and mobile screenshots. All HA data,
navigation and service transport are local fixtures; no physical device is used.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"


def fixture():
    area, physical, controller = "living", "climate.native_heater", "climate.hem_heater"
    def managed(state, **attributes):
        return {"state": state, "attributes": {
            "area_id": area, "source_entity_ids": [physical],
            "source_device_id": "physical-heater-device", **attributes,
        }}
    readings = [
        {"metric": kind, "value": value, "unit": unit, "name": name,
         "available": True, "entity_id": "sensor." + kind,
         "threshold": threshold, "exceeded": kind == "co2"}
        for kind, value, unit, name, threshold in (
            ("temperature", 20., "°C", "Room temperature", None),
            ("humidity", 50., "%", "Relative humidity", None),
            ("co2", 1600., "ppm", "Carbon dioxide", 1000.),
            ("pm25", 10., "µg/m³", "Fine particles", 25.),
            ("pm10", 32., "µg/m³", "Particles", 50.),
            ("illuminance", 120., "lx", "Daylight", None),
            ("voc", 110., "µg/m³", "VOC", None),
            ("noise", 35., "dB", "Sound", None),
            ("pressure", 1012., "hPa", "Pressure", None),
        )
    ]
    room = {"area_id": area, "name": "Living room", "status": "attention",
            "high_count": 1, "windows": [], "readings": readings,
            "environment": {"climate_plan": {
                "status": "ready", "controller": "environment", "profile": "home",
                "away": "home", "occupancy": "occupied", "sleeping": False,
                "temperature_c": 20., "equipment_plan": {
                    "humidity": {"status": "advisory", "action": "idle", "measured_rh": 50.},
                }, "actuation": {"status": "advisory_only"},
            }}}
    data = {"version": 1, "rooms": [room],
            "summary": {"total": 1, "safe": 0, "attention": 1, "unknown": 0},
            "outdoor": {"status": "safe", "weather": [{"condition": "sunny", "temperature_c": 8.}],
                        "readings": [], "warnings": [], "blockers": []}}
    states = {
        "sensor.hem": {"state": "ready", "attributes": {"dashboard": data}},
        controller: managed("heat", friendly_name="HEM Living room heater", control_mode="pid",
            physical_primary_entity_id=physical, physical_source_state="heat",
            requested_hvac_mode="heat", measurements={"temperature": 20., "humidity": 50.},
            controller_status={"status": "controlling"}, supported_features=1,
            hvac_modes=["off", "heat"], temperature=21., current_temperature=20.),
        physical: {"state": "heat", "attributes": {
            "friendly_name": "Living room heater", "hvac_action": "heating", "temperature": 30.}},
        "select.hem_method": managed("pid", options=["existing", "automatic", "manual", "off", "pid"]),
        "switch.hem_announce": managed("on", device_fault_role="announce",
            friendly_name="Announce device errors", native_error={"status": "ok"}),
    }
    for reading in readings:
        states[reading["entity_id"]] = {"state": str(reading["value"]), "attributes": {
            "friendly_name": reading["name"], "unit_of_measurement": reading["unit"]}}
    return {"states": states, "room": room, "controller": controller, "physical": physical,
            "entities": {controller: {"device_id": "hem-controller-device"},
                         physical: {"device_id": "physical-heater-device"}}}


SCRIPT = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const supplied=JSON.parse(process.argv[2]),registered=new Map(),routes=[],locations=[];
class Node {
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.attrs={};
    this.dataset={};this.classList={add(){}};this.isConnected=true;this.events=[];}
  addEventListener(){}
  attachShadow(){const listeners=[];this.shadowRoot={
    addEventListener(type,handler,options){listeners.push({type,handler,capture:options===true});},
    querySelector(){return null;},querySelectorAll(){return [];},
    deliver(type,event){for(const item of [...listeners].sort((a,b)=>Number(b.capture)-Number(a.capture))){
      if(item.type===type&&!event.stopped)item.handler(event);}},};return this.shadowRoot;}
  dispatchEvent(event){this.events.push(event);return true;}
  setAttribute(name,value){this.attrs[name]=String(value);}
  getAttribute(name){return this.attrs[name]??null;}
  append(...children){this.children.push(...children);}
  appendChild(child){this.append(child);}
  get firstChild(){return null;}
  querySelector(){return null;}
}
const context={HTMLElement:Node,document:{createElement:tag=>new Node(tag)},
  window:{history:{pushState:(_state,_title,path)=>routes.push(path)},
    dispatchEvent:event=>locations.push(event.type)},console,
  CustomEvent:class{constructor(type,options){this.type=type;Object.assign(this,options);}},
  Event:class{constructor(type){this.type=type;}},setTimeout,clearTimeout,
  customElements:{get:name=>registered.get(name),define:(name,ctor)=>registered.set(name,ctor)}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const Card=registered.get('home-environment-manager-card');
const clone=value=>JSON.parse(JSON.stringify(value));
function make(){const data=clone(supplied),card=new Card();card._config={entity:'sensor.hem'};
  card.calls=[];card._hass={language:'en',states:data.states,entities:data.entities,
    localize:()=>undefined,callService:(...args)=>{card.calls.push(args);return Promise.resolve();}};
  card._closeInfo87=()=>{};return {card,...data};}
function button(attrs,disabled=false){return {disabled,getAttribute:name=>attrs[name]??null,
  closest(selector){return [...selector.matchAll(/\[([^\]=]+)(?:[^\]]*)\]/g)]
    .some(match=>Object.hasOwn(attrs,match[1]))?this:null;}};}
function click(card,attrs,disabled=false){const target=button(attrs,disabled),event={target,
  preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;}};
  card._installFolds87();card.shadowRoot.deliver('click',event);return event;}
const cases=[];function test(name,run){cases.push({name,run});}

test('physical device icon precedes native entity name and has no trailing icon',()=>{
  const {card,room,physical}=make(),html=card._controllerPanel(room);
  const heading=html.match(/<div class="hem-physical-heading122">([\s\S]*?)<\/div>/)[1];
  assert.ok(heading.indexOf('data-open-physical-device122')<heading.indexOf('data-open-physical93'));
  assert.ok(heading.includes('data-open-physical-device122="'+physical+'"'));
  assert.ok(!heading.includes('mdi:open-in-new'));
  const name=heading.match(/<button[^>]*data-open-physical93[^>]*>([\s\S]*?)<\/button>/)[1];
  assert.ok(name.includes('Living room heater'));assert.ok(!name.includes('ha-icon'));
});
test('folded controller begins with its own device button and keeps its entity name',()=>{
  const {card,controller}=make(),container=new Node();
  container.setAttribute('data-managed-climate93',controller);container.setAttribute('data-controller-area','living');
  const shell={dataset:{},classList:{add(){}},querySelector(){return null;},
    querySelectorAll:selector=>selector==='.managed-controller'?[container]:[]};
  card._compactAfterRender87(shell);
  const html=container.children[0].children[0].innerHTML;
  assert.ok(html.indexOf('data-open-controller-device122')<html.indexOf('data-open-controller89'));
  assert.ok(!html.includes('data-open-native89'));
  assert.ok(html.includes('data-open-controller-device122="'+controller+'"'));
});
test('device page clicks use separate current registry identities without folding or services',()=>{
  const {card,controller,physical}=make();routes.length=0;locations.length=0;
  const common={'data-controller-area':'living','data-controller-id122':controller};
  for(const [kind,id] of [['physical',physical],['controller',controller]]){
    const event=click(card,{...common,['data-open-'+kind+'-device122']:id});
    assert.ok(event.prevented&&event.stopped);
  }
  assert.deepEqual(JSON.parse(JSON.stringify(routes)),['/config/devices/device/physical-heater-device']);
  assert.equal(locations.length,1);assert.equal(card.events.length,0);assert.equal(card.calls.length,0);
  assert.equal(card._devicesExpanded87.size,0);
});
test('names still open their exact native and HEM entities',()=>{
  const {card,controller,physical}=make();
  click(card,{'data-controller-area':'living','data-hem-controller93':controller,'data-open-physical93':physical});
  click(card,{'data-controller-area':'living','data-controller-id89':controller,'data-open-controller89':controller});
  assert.equal(JSON.stringify(card.events.map(e=>e.detail.entityId)),JSON.stringify([physical,controller]));
  assert.ok(card.events.every(e=>e.type==='hass-more-info'));assert.equal(card.calls.length,0);
});
test('missing or changed registry and forged source links never fall back to physical ownership',()=>{
  const {card,controller,physical}=make();routes.length=0;
  delete card._hass.entities[controller];
  assert.equal(card._entityDeviceId122(controller),null);
  assert.ok(card._devicePageButton122('controller','living',controller,controller,'mdi:cog','HEM').includes('disabled'));
  assert.equal(card._openDevicePage122('living',controller,controller,'controller'),false);
  assert.equal(card._openDevicePage122('living',controller,physical,'controller'),false);
  assert.equal(card._openDevicePage122('living',controller,'climate.unrelated','physical'),false);
  const previous=card._controllerSignature();
  card._hass.entities[controller]={device_id:'replacement/hem'};
  assert.notEqual(card._controllerSignature(),previous);
  // A controller gear must not navigate to its device page or fall back to a physical device.
  assert.equal(card._openDevicePage122('living',controller,controller,'controller'),false);
  assert.equal(routes.length,0);
  card._hass.states[controller].attributes.physical_primary_entity_id='climate.unrelated';
  assert.equal(card._openDevicePage122('living',controller,physical,'physical'),false);
});
test('announce control displays icon and state while retaining accessible purpose and behavior',()=>{
  const {card,room}=make(),html=card._controllerPanel(room);
  const button=html.match(/<button[^>]*data-device-error-announce[^>]*>[\s\S]*?<\/button>/)[0];
  assert.ok(button.includes('aria-label="Announce device errors"')&&button.includes('title="Announce device errors"'));
  assert.ok(button.includes('aria-checked="true"'));
  assert.ok(html.includes('data-detail-id="device-option:switch.hem_announce"'));
  assert.ok(html.includes('mdi:bell-ring-outline'));
  assert.ok(!button.includes('ha-icon'),'Purpose icon opens help independently of the state toggle');
  const body=button.slice(button.indexOf('>')+1,button.lastIndexOf('</button>'));
  assert.ok(body.includes('<b>On</b>'));assert.ok(!body.includes('Announce device errors'));
  click(card,{'data-controller-area':'living','data-device-error-announce':'switch.hem_announce'});
  assert.equal(JSON.stringify(card.calls),JSON.stringify([['switch','turn_off',{entity_id:'switch.hem_announce'}]]));
});
test('details use the same actual headline selection and retain complementary data',()=>{
  const {card,room}=make(),overview=card._roomGlance122(room),details=card._roomDetailReadings122(room,overview);
  assert.equal(JSON.stringify([...overview.metrics].sort()),JSON.stringify(['co2','humidity','pm25','temperature']));
  assert.ok(!details.some(item=>['temperature','humidity','pm25'].includes(item.metric)));
  assert.ok(details.find(item=>item.metric==='co2').overview_detail122);
  for(const metric of ['pm10','illuminance','voc','noise','pressure'])assert.ok(details.some(item=>item.metric===metric));
  assert.ok(room.readings.every(item=>!item.overview_detail122),'Display must not mutate evidence');
});
test('first expansion has four complementary tiles and More retains additional readings',()=>{
  const {card,room}=make();
  let html=card._room(room);
  assert.equal((html.match(/data-room-metric114=/g)||[]).length,4);
  assert.ok(html.includes('data-expand="living"'));
  assert.ok(html.includes('data-overview-detail122="co2"'));
  assert.ok(html.includes('<div class="hem-room-readings66"></div>'));
  assert.ok(html.includes('data-detail-id="room-info:living"'));
  card._expanded.add('living');html=card._room(room);
  assert.equal((html.match(/data-room-metric114=/g)||[]).length,6);
  const warning=card._metricInfo122(room.readings.find(item=>item.metric==='co2'));
  assert.ok(!warning.includes('metric-number')&&!warning.includes('role="progressbar"'));
  assert.ok(!warning.includes('1,600'));
  assert.equal(warning.match(/<div class="metric-limit">([^<]*)<\/div>/)[1],'Limit 1,000 ppm');
  assert.ok(warning.includes('metric-help-content'));
  assert.ok(warning.includes('data-room-metric114="co2"'));
});
test('unavailable measurements remain distinct and mold calibration retains its current estimate',()=>{
  const {card,room}=make();
  room.readings.push({metric:'pm25',available:false,entity_id:'sensor.failed_particles'});
  assert.ok(card._roomDetailReadings122(room).some(item=>item.entity_id==='sensor.failed_particles'));
  const mold={metric:'mold',available:true,value:74.,details:{calibration_factor:1.25}};
  room.readings=[mold];room.environment={};
  assert.ok(card._roomDetailReadings122(room)[0].overview_detail122);
  const html=card._metricInfo122(mold);
  assert.ok(html.includes('1.25')&&html.includes('mold-calibration-details'));
  assert.ok(html.includes('<span class="metric-number">74 <small>%</small></span>'));
  room.readings=[{metric:'temperature',available:false,value:null}];
  assert.ok(!card._roomGlance122(room).metrics.has('temperature'));
  assert.equal(card._roomDetailReadings122(room).length,1);
});

let failed=0;for(const {name,run} of cases){try{run();console.log('PASS: '+name);}
 catch(error){failed++;console.error('FAIL: '+name+'\n'+error.stack);}}
if(failed)process.exitCode=1;else console.log('BETA122_DEVICE_NAVIGATION_AND_ROOM_DETAILS=PASS ('+cases.length+' cases)');
"""


@contextmanager
def browser_page(playwright, executable):
    browser = playwright.chromium.launch(executable_path=executable, headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1024, "height": 1000})
    try:
        yield page
    except Exception:
        screenshot_dir = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
        if screenshot_dir:
            try:
                destination = Path(screenshot_dir)
                destination.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(destination / "beta122-card-details-failure.png"), full_page=True)
            except Exception as capture_error:
                print(f"Could not capture Beta122 failure screenshot: {capture_error}")
        raise
    finally:
        browser.close()


def browser_checks(data):
    from playwright.sync_api import expect, sync_playwright
    executable = os.environ.get("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert executable, "Chromium required for Beta122 browser checks"
    with sync_playwright() as playwright, browser_page(playwright, executable) as page:
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content("""<!doctype html><html><head><style>
          *{box-sizing:border-box}body{margin:8px;background:#101820;color:#e8edf3;font-family:Arial}
          :root{--primary-text-color:#e8edf3;--secondary-text-color:#aebbc8;
          --card-background-color:#18212b;--secondary-background-color:#22303d;--divider-color:#455463}
          home-environment-manager-card{max-width:760px;margin:0 auto}
          </style></head><body></body></html>""")
        page.add_script_tag(path=str(CARD))
        page.evaluate("""data=>{
          window.calls=[];window.info=[];window.routes=[];window.locations=0;
          window.history.pushState=(_state,_title,path)=>routes.push(path);
          window.addEventListener('location-changed',()=>locations++);
          window.card=document.createElement('home-environment-manager-card');document.body.append(card);
          card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
          card._config={entity:'sensor.hem'};
          const entities={...data.entities,
            'sensor.hem':{config_entry_id:'entry0'},
            [data.controller]:{...data.entities[data.controller],config_entry_id:'entry0'}};
          card._hass={language:'en',states:data.states,entities,user:{is_admin:true},connection:{},
            localize:()=>undefined,callService:(...args)=>{calls.push(args);return Promise.resolve();}};
          card._renderContent(true);
          card._configEntryId114='entry0';
          card._configEntryOwner114='sensor.hem';
          card._areaDeviceIds=new Map([['living','room-hub']]);
          // The controller settings modal is registry-backed; it must never
          // duplicate the compact device card above the categories.
          window.registry122=['select.hem_method','switch.hem_announce'].map(id=>({
            entity_id:id,config_entry_id:'entry0',platform:'environment_manager',
            device_id:'hem-controller-device',unique_id:'entry0_'+id.replace('.','_')}));
          card._hass.callWS=async request=>request.type==='config/entity_registry/list'?
            registry122:Promise.reject(Error('Unexpected WebSocket request'));
        }""", data)
        room = page.locator('[data-room-fold87="living"]')
        assert room.get_attribute("open") is None
        room.locator(":scope > summary").evaluate("node=>node.click()")
        controller = room.locator('[data-device-fold87="climate.hem_heater"]')
        assert controller.get_attribute("open") is None
        controller.locator('[data-open-controller-device122]').click()
        dialog=page.locator('.hem-controller-options126')
        expect(dialog).to_be_visible()
        assert page.evaluate("routes.length")==0, "Controller gear must not navigate"
        # The full settings dialog shows only exact registry-owned controls,
        # never a duplicate controller panel or quick switch row.
        page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length===2")
        assert dialog.locator('[data-managed-climate93]').count()==0
        assert dialog.locator('.managed-controller,.hem-device-quick-row8').count()==0
        assert dialog.locator('[data-hem-full-row127="select.hem_method"]').count()==1
        assert dialog.locator('[data-hem-full-row127="switch.hem_announce"]').count()==1
        assert page.evaluate("calls.length")==0
        dialog.locator('[data-close-hem-controller126]').click()
        expect(dialog).to_have_count(0)
        assert controller.get_attribute("open") is None
        controller.locator('[data-open-controller89]').click()
        assert page.evaluate("info.at(-1)") == data["controller"]
        assert controller.get_attribute("open") is None
        controller.locator(":scope > summary").evaluate("node=>node.click()")
        heading = controller.locator(".hem-physical-heading122")
        assert heading.locator(":scope > button").nth(0).get_attribute("data-open-physical-device122") == data["physical"]
        assert heading.locator('[data-open-physical93] ha-icon').count() == 0
        heading.locator('[data-open-physical-device122]').click()
        assert page.evaluate("routes.at(-1)") == "/config/devices/device/physical-heater-device"
        heading.locator('[data-open-physical93]').click()
        assert page.evaluate("info.at(-1)") == data["physical"]
        assert page.evaluate("calls.length") == 0
        announce = controller.locator('[data-device-error-announce]')
        assert announce.inner_text().strip() == "On"
        assert controller.locator('[data-detail-id="device-option:switch.hem_announce"] > summary ha-icon').count() == 1
        assert announce.get_attribute("aria-label") == "Announce device errors"
        assert announce.get_attribute("title") == "Announce device errors"
        announce.click()
        assert page.evaluate("calls") == [["switch", "turn_off", {"entity_id": "switch.hem_announce"}]]
        tiles = room.locator(".metric-grid > .metric")
        expect(tiles).to_have_count(4)
        assert room.locator('.metric-grid [data-room-metric114="temperature"]').count() == 0
        assert room.locator('.metric-grid [data-room-metric114="humidity"]').count() == 0
        assert room.locator('.metric-grid [data-room-metric114="pm25"]').count() == 0
        warning = room.locator('[data-overview-detail122="co2"]')
        # The English fixture uses grouped numbers. Assert the threshold's own
        # DOM text, not a raw-number substring that can match hidden help text.
        assert warning.locator(":scope > .metric-limit").inner_text() == "Limit 1,000 ppm"
        assert warning.locator('.metric-number, .hem-room-metric-value107, [role="progressbar"]').count() == 0
        assert "1,600" not in warning.inner_text()
        headline = room.locator('.hem-room-glance87 [data-hem-source105="sensor.co2"] .hem-room-metric-value107')
        assert headline.count() == 1
        assert headline.inner_text() == "1,600"
        warning.locator("details.metric-help > summary").click()
        page.wait_for_function("!!card._floatingInfo87")
        assert page.locator(".hem-floating-info87").is_visible()
        page.keyboard.press("Escape")
        assert room.locator(".hem-room-readings66").is_hidden()
        assert room.locator('[data-detail-id="room-info:living"]').count() == 1
        more = room.locator('[data-expand="living"]')
        more.click()
        # The click queues _render on requestAnimationFrame. Wait for the
        # resulting DOM, retaining the exact complementary-tile requirements.
        expect(more).to_have_attribute("aria-expanded", "true")
        expect(tiles).to_have_count(6)
        more.click()
        expect(more).to_have_attribute("aria-expanded", "false")
        expect(tiles).to_have_count(4)
        # Re-render only registry data: the existing source device must never
        # become a fallback when the HEM registry association is missing.
        page.evaluate("""()=>{
          card._hass={...card._hass,entities:{...card._hass.entities,
            'climate.hem_heater':{device_id:null}}};card._renderContent();
        }""")
        expect(controller.locator('[data-open-controller-device122]')).to_be_disabled()
        expect(heading.locator('[data-open-physical-device122]')).to_be_enabled()
        page.evaluate("""()=>{card._hass.entities['climate.hem_heater']={device_id:'hem-controller-device'};
          card._renderContent();}""")
        expect(controller.locator('[data-open-controller-device122]')).to_be_enabled()
        screenshot_dir = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
        for width, label in ((1024, "desktop"), (375, "mobile"), (320, "narrow")):
            page.set_viewport_size({"width": width, "height": 1000})
            page.evaluate("card._renderContent(true)")
            assert page.evaluate("document.documentElement.scrollWidth") <= width
            expect(tiles).to_have_count(4)
            expect(controller.locator('[data-open-controller-device122]')).to_be_visible()
            expect(heading.locator('[data-open-physical-device122]')).to_be_visible()
            for selector in (".hem-device-main87", ".hem-physical-heading122", ".metric-grid"):
                for element in room.locator(selector).all():
                    rect = element.bounding_box()
                    assert rect and rect["x"] >= 0 and rect["x"] + rect["width"] <= width + 1, (width, selector, rect)
            if screenshot_dir:
                destination = Path(screenshot_dir)
                destination.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(destination / f"beta122-card-details-{label}.png"), full_page=True)
        assert not errors, errors
    print("BETA122_CARD_DETAILS_BROWSER=PASS (desktop, mobile, narrow; mocked HA only)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--logic-only", action="store_true")
    args = parser.parse_args()
    data = fixture()
    result = subprocess.run(["node", "-e", SCRIPT, str(CARD), json.dumps(data)])
    if result.returncode:
        return result.returncode
    if not args.logic_only:
        browser_checks(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
