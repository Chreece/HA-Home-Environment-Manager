"""Actual room Options transport, full drafts, cancellation and compact dialog.

The browser uses the production card with a deterministic Options API. No
physical device calls or real configuration entries are contacted. --logic-only
runs the parser, association guards and production submit/cleanup path in Node.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
MARKER = "  if (!customElements.get('air-quality-advisor-card'))"
KEYS = ["windows", "air_quality", "temperature", "humidity", "pressure",
        "climate_devices", "shades", "occupancy_sensors"]
DEFAULTS = {
    "windows": ["binary_sensor.window"], "air_quality": [],
    "temperature": ["sensor.temp_a", "sensor.temp_b"],
    "humidity": ["sensor.humidity"], "pressure": [],
    "climate_devices": ["climate.radiator"], "shades": [],
    "occupancy_sensors": ["binary_sensor.presence"],
}
FORM = {
    "type": "form", "step_id": "edit_room", "flow_id": "options1",
    "handler": "entry0", "description_placeholders": {"area_name": "Living room"},
    "errors": {}, "data_schema": [
        {"name": name, "required": False, "default": values,
         "selector": {"select": {"multiple": True, "custom_value": False,
             "options": [{"value": value, "label": value.replace("_", " ")}
                         for value in values + (["sensor.temp_c"] if name == "temperature" else [])]}}}
        for name, values in DEFAULTS.items()
    ],
}


def source():
    value = CARD.read_text(encoding="utf-8")
    # Local isolated development may supply the unmerged snippet explicitly.
    # CI always reads the integrated production card.
    if "HEM_DIRECT_ROOM_OPTIONS114_START" not in value:
        snippet = os.environ.get("HEM_ROOM_SETTINGS_SNIPPET")
        assert snippet, "Room options implementation is missing from the card"
        value = value.replace(MARKER, Path(snippet).read_text(encoding="utf-8") + "\n" + MARKER, 1)
    return value


def logic_checks(card_source):
    exported = """
globalThis.__roomOptions114={fields:_roomOptionsFields114,
  context:_roomOptionsContext114,cleanup:_roomOptionsCleanup114};
"""
    script = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements=new Map(),context={console,Promise,setTimeout,clearTimeout,
  HTMLElement:class {},window:{customCards:[]},customElements:{
    get:name=>elements.get(name),define:(name,cls)=>elements.set(name,cls)}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const helper=context.__roomOptions114,Ctor=elements.get('home-environment-manager-card');
const form=JSON.parse(process.argv[2]),plain=value=>JSON.parse(JSON.stringify(value));
assert.deepEqual(plain(helper.fields(form).map(f=>f.name)),Object.keys(form.data_schema.reduce((a,f)=>(a[f.name]=1,a),{})));
for(const mutate of [f=>f.data_schema.pop(),f=>f.data_schema[0].name='other_room',
  f=>f.data_schema[0].selector.select.multiple=false,f=>f.data_schema[0].default='not-an-array']){
  const invalid=structuredClone(form);mutate(invalid);assert.throws(()=>helper.fields(invalid));
}
const orphan=structuredClone(form);orphan.data_schema[0].default=['binary_sensor.removed'];
assert.deepEqual(plain(helper.fields(orphan)[0].defaults),['binary_sensor.removed']);
const makeNode=()=>{const nodes=new Map();return {
  setAttribute(){},querySelectorAll:()=>[],remove(){},querySelector:key=>{
    if(!nodes.has(key))nodes.set(key,{setAttribute(){},classList:{toggle(){}},
      replaceChildren(){},focus(){},textContent:'',hidden:false,disabled:false});return nodes.get(key);}};};
const card=Object.create(Ctor.prototype);
Object.assign(card,{isConnected:true,_configEntryId114:'entry0',_configEntryOwner114:'sensor.hem',
  _areaDeviceIds:new Map([['room0','room-device']]),_state:()=>['sensor.hem',{}],
  _dashboard105:()=>({rooms:[{area_id:'room0',name:'Living room'}]}),
  _hass:{language:'en',user:{is_admin:true},callApi:async()=>{},
    entities:{'sensor.hem':{config_entry_id:'entry0'}}}});
assert(helper.context(card,'room0'));assert.equal(helper.context(card,'foreign'),null);
card._configEntryOwner114='sensor.other';assert.equal(helper.context(card,'room0'),null);
card._configEntryOwner114='sensor.hem';card._hass.user.is_admin=false;
assert.equal(helper.context(card,'room0'),null);
(async()=>{
  assert.equal(await card._openRoomSettings114('room0'),false);
  card._hass.user.is_admin=true;
  const calls=[];
  const saved={...helper.context(card,'room0'),area:'room0',flowId:'options1',node:makeNode(),
    fields:helper.fields(form),draft:Object.fromEntries(form.data_schema.map(f=>[f.name,[...f.default]])),
    nativeForms:[],clientErrors:new Set(),busy:false,failed:false,finished:false,
    api:async(method,path,data)=>{calls.push({method,path,data});return {type:'create_entry',flow_id:'options1'};}};
  saved.draft.humidity=[];card._roomSettingsDialog114=saved;
  await card._submitRoomSettings114(saved);
  assert.equal(calls.length,1);assert.equal(calls[0].method,'POST');
  assert.deepEqual(plain(calls[0].data.humidity),[]);
  assert.deepEqual(Object.keys(calls[0].data).sort(),form.data_schema.map(f=>f.name).sort());
  assert.deepEqual(plain(calls[0].data.temperature),['sensor.temp_a','sensor.temp_b']);
  assert.equal(saved.finished,true);await helper.cleanup(saved);assert.equal(calls.length,1);
  const failed={...saved,node:makeNode(),failed:false,finished:false,busy:false,cleanupStarted:false,
    api:async(method,path,data)=>{calls.push({method,path,data});if(method==='POST')throw Error('offline');}};
  card._roomSettingsDialog114=failed;await card._submitRoomSettings114(failed);
  await failed.cleanupPromise;assert.equal(failed.failed,true);
  assert.deepEqual(calls.slice(1).map(c=>c.method),['POST','DELETE']);
  await helper.cleanup(failed);assert.equal(calls.length,3);
  console.log('BETA114_ROOM_OPTIONS_SCHEMA_ASSOCIATION_FULL_PAYLOAD_AND_CLEANUP=PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    with tempfile.TemporaryDirectory(prefix="hem-room-options114-") as temp:
        path = Path(temp) / "card.js"
        path.write_text(card_source.replace(MARKER, exported + MARKER, 1), encoding="utf-8")
        subprocess.run(["node", "--check", str(path)], check=True)
        subprocess.run(["node", "-e", script, str(path), json.dumps(FORM)], check=True)


SETUP = r"""({states,form,native})=>{
  window.calls=[];window.pending={};window.mode={};window.seq=0;
  if(native)customElements.define('ha-form',class extends HTMLElement{
    constructor(){super();this.attachShadow({mode:'open'}).innerHTML='<input aria-label="Native selector">';}
  });
  window.card=document.createElement('home-environment-manager-card');document.body.append(card);
  window.api=async(method,path,data)=>{
    calls.push({method,path,data:data===undefined?null:structuredClone(data)});
    if(method==='DELETE')return {};
    if(path==='config/config_entries/options/flow'){
      if(mode.failCreate)throw Error('offline');
      const menu={type:'menu',handler:'entry0',flow_id:'options'+(++seq),
        menu_options:{edit_room_room0:'Living room',edit_room_room1:'Bedroom'}};
      if(mode.holdCreate)return await new Promise(resolve=>pending.create=()=>resolve(menu));
      return menu;
    }
    const flow_id=path.split('/').at(-1);
    const step={...structuredClone(form),flow_id};
    if(data?.next_step_id){
      if(mode.holdAdvance)return await new Promise(resolve=>pending.advance=()=>resolve(step));
      if(mode.invalidSchema)step.data_schema.pop();
      return step;
    }
    if(mode.failSave)throw Error('offline');
    if(mode.validation)return {...step,errors:{temperature:'invalid_room_source'}};
    return {type:'create_entry',flow_id};
  };
  card._hass={language:'en',user:{is_admin:true},states,localize:()=>undefined,
    entities:{'sensor.hem':{config_entry_id:'entry0'}},callApi:api,
    callService:()=>{throw Error('Room form must not control a device');}};
  card._config={entity:'sensor.hem'};card._configEntryId114='entry0';
  card._configEntryOwner114='sensor.hem';
  card._areaDeviceIds=new Map([['room0','living-device'],['room1','bed-device']]);
  card._renderContent(true);
} """


def browser_checks(card_source):
    from playwright.sync_api import sync_playwright

    prior = runpy.run_path(str(ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"))
    fixture = prior["fixture_definitions"]()
    states = deepcopy(fixture["states"])
    data = states["sensor.hem"]["attributes"]["dashboard"]
    data["rooms"] = data["rooms"][:2]
    data["rooms"][0]["name"] = "Living room"
    data["rooms"][1]["name"] = "Bedroom"
    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or shutil.which("chromium") or shutil.which("google-chrome")
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])

        def new_page(native=False):
            page = browser.new_page(viewport={"width": 390, "height": 850})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_content('<style>body{margin:0;font:14px Arial;background:#111;color:#eee}'
                ':root{--card-background-color:#202830;--secondary-background-color:#293440;'
                '--primary-text-color:#eef2f6;--secondary-text-color:#b4bfca;--divider-color:#475665;'
                '--primary-color:#03a9f4}</style>')
            page.evaluate(prior["icon_fixture"]())
            page.add_script_tag(content=card_source)
            page.evaluate(SETUP, {"states": states, "form": FORM, "native": native})
            return page

        page = new_page()
        assert page.evaluate("card._openRoomSettings114('foreign')") is False
        page.evaluate("card._hass.user.is_admin=false")
        assert page.evaluate("card._openRoomSettings114('room0')") is False
        assert page.evaluate("calls.length") == 0
        page.evaluate("card._hass.user.is_admin=true")
        assert page.evaluate("card._openRoomSettings114('room0')") is True
        popup = page.locator(".hem-room-options114")
        assert popup.evaluate("node=>node.matches(':modal')")
        assert popup.locator("details").count() == 8
        assert len(page.evaluate("calls")) == 2, "Opening must not submit a settings form"
        temp = popup.locator('[data-room-options-group114="temperature"]')
        temp.locator("summary").click()
        temp.locator('input[value="sensor.temp_a"]').uncheck()
        temp.locator('input[value="sensor.temp_c"]').check()
        temp.locator('input[type="search"]').fill("TEMP C")
        assert temp.locator('[data-room-options-choice114]:visible').count() == 1
        humidity = popup.locator('[data-room-options-group114="humidity"]')
        humidity.locator("summary").click()
        humidity.locator('[data-room-clear114]').click()
        assert humidity.locator('[data-room-options-count114]').inner_text() == "0"
        # A normal hass refresh retains the exact dialog node and draft.
        page.evaluate("window.before=card._roomSettingsDialog114.node;card._renderContent(true)")
        assert page.evaluate("before===card._roomSettingsDialog114.node")
        for width in (320, 390, 700):
            page.set_viewport_size({"width": width, "height": 850})
            assert popup.evaluate("node=>node.scrollWidth<=node.clientWidth+1")
            box = popup.bounding_box()
            assert box and box["x"] >= 0 and box["x"] + box["width"] <= width + 1, box
        page.set_viewport_size({"width": 390, "height": 850})
        popup.locator('[data-room-options-save114]').focus()
        page.keyboard.press("Tab")
        assert popup.locator('[data-room-options-x114]').evaluate("node=>node===node.getRootNode().activeElement")
        # Backend validation keeps all edits rather than replacing them with defaults.
        page.evaluate("mode.validation=true")
        popup.locator('[data-room-options-save114]').click()
        page.wait_for_function("!card._roomSettingsDialog114.busy")
        assert temp.locator('input[value="sensor.temp_c"]').is_checked()
        assert not temp.locator('input[value="sensor.temp_a"]').is_checked()
        assert temp.locator('[data-room-options-field-error114]').is_visible()
        assert page.evaluate("calls.filter(c=>c.method==='DELETE').length") == 0
        page.evaluate("mode.validation=false")
        popup.locator('[data-room-options-save114]').click()
        page.wait_for_function("card._roomSettingsDialog114.finished===true")
        saved = page.evaluate("calls.filter(c=>c.data?.temperature).at(-1).data")
        expected = deepcopy(DEFAULTS)
        expected.update(temperature=["sensor.temp_b", "sensor.temp_c"], humidity=[])
        assert saved == expected, saved
        popup.locator('[data-room-options-close114]').click()
        assert popup.count() == 0

        # A canceled create response is cleaned up and never advances into a form.
        page.evaluate("calls=[];mode={holdCreate:true};void card._openRoomSettings114('room0')")
        popup.locator('[data-room-options-x114]').click()
        page.evaluate("pending.create()")
        page.wait_for_function("calls.some(c=>c.method==='DELETE')")
        assert page.evaluate("calls.map(c=>c.method)") == ["POST", "DELETE"]
        assert popup.count() == 0

        # Closing during the room-navigation response neither reopens nor saves.
        page.evaluate("calls=[];mode={holdAdvance:true};void card._openRoomSettings114('room0')")
        page.wait_for_function("typeof pending.advance==='function'")
        page.keyboard.press("Escape")
        page.evaluate("pending.advance()")
        page.wait_for_function("calls.some(c=>c.method==='DELETE')")
        assert len(page.evaluate("calls")) == 3 and popup.count() == 0

        # A network failure after Save does not automatically resubmit.
        page.evaluate("calls=[];mode={};card._openRoomSettings114('room0')")
        page.evaluate("mode.failSave=true")
        popup.locator('[data-room-options-save114]').click()
        page.wait_for_function("card._roomSettingsDialog114.failed===true")
        assert popup.locator('[data-room-options-status114]').get_attribute("role") == "alert"
        assert popup.locator('[data-room-options-save114]').is_disabled()
        page.wait_for_function("calls.some(c=>c.method==='DELETE')")
        page.evaluate("mode={}")
        popup.locator('[data-room-options-retry114]').click()
        page.wait_for_function("card._roomSettingsDialog114.fields!==null")
        assert page.evaluate("calls.filter(c=>c.data?.temperature).length") == 1

        # A different card source invalidates this room's open draft immediately.
        page.evaluate("card._configEntryOwner114='sensor.other';card._renderContent(true)")
        assert popup.count() == 0
        page.close()

        # The same complete data handling is used when HA's ha-form is loaded.
        native = new_page(native=True)
        native.evaluate("card._openRoomSettings114('room0')")
        popup = native.locator('.hem-room-options114')
        assert popup.locator('ha-form').count() == 8
        native.evaluate("""()=>{
          const form=card._roomSettingsDialog114.node.querySelector(
            '[data-room-options-group114="humidity"] ha-form');
          form.dispatchEvent(new CustomEvent('value-changed',{detail:{value:{}},bubbles:true}));
        }""")
        popup.locator('[data-room-options-save114]').click()
        native.wait_for_function("card._roomSettingsDialog114.finished===true")
        expected = deepcopy(DEFAULTS)
        expected['humidity'] = []
        assert native.evaluate("calls.at(-1).data") == expected
        popup.locator('[data-room-options-close114]').click()
        native.evaluate("card._openRoomSettings114('room1')")
        native.evaluate("card.remove()")
        native.wait_for_function("calls.some(c=>c.method==='DELETE'&&c.path.endsWith('options2'))")
        assert native.locator('.hem-room-options114').count() == 0
        assert not errors, errors
        browser.close()
    print("BETA114_ROOM_SETTINGS_BROWSER_DRAFTS_CANCEL_RACES_AND_NATIVE_FORM=PASS")


if __name__ == "__main__":
    value = source()
    logic_checks(value)
    if "--logic-only" not in sys.argv:
        browser_checks(value)
