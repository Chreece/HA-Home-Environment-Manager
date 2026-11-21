"""Room feedback distinguishes enabled native modes from reported activity.

The real production card runs with immutable HA states. Node verifies native
evidence precedence and source ownership; Chromium verifies the distinct visual
cue, narrow layouts, information text and native-only HA setter updates. Tests
never contact a Home Assistant instance or send physical service commands.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
SPEC = importlib.util.spec_from_file_location(
    "native_mode_metric_fixture", ROOT / ".github/tests/test_074b6_metric_activity.py"
)
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)


def fixture():
    states = baseline.fixture()
    # Reproduce the screenshot: the original thermostat reports a heat mode
    # and 30 °C target, while the HEM controller has 2.4% requested PID demand.
    # Neither fact is a physical hvac_action report.
    heater = states["climate.heater"]
    heater["attributes"].pop("hvac_action")
    heater["attributes"].update(
        hvac_modes=["off", "heat"], current_temperature=20.2, temperature=30
    )
    for entity in ("climate.managed_heater", "select.method_heater"):
        states[entity]["attributes"]["source_entity_ids"] = ["climate.heater"]
    managed = states["climate.managed_heater"]["attributes"]
    managed["controller_status"]["demand_percent"] = 2.4
    managed["measurements"].update(temperature=20.8, humidity=46)
    states["climate.cooler"]["attributes"].pop("hvac_action")
    states["climate.cooler"]["attributes"]["hvac_modes"] = ["off", "cool"]
    # A native climate DRY endpoint, rather than an ON humidifier with no
    # directional activity report, can expose an enabled drying mode.
    states["climate.dryer"] = {"state": "dry", "attributes": {
        "friendly_name": "Drying climate", "hvac_modes": ["off", "dry"]}}
    for entity in ("climate.managed_dryer", "select.method_dryer"):
        states[entity]["attributes"]["source_entity_ids"] = ["climate.dryer"]
    states["climate.managed_dryer"]["attributes"].update(
        physical_primary_entity_id="climate.dryer", physical_source_state="dry"
    )
    del states["humidifier.dryer"]
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
    callService:()=>{throw Error('Native mode feedback issued a service call')}};
  card._interactions66=true;card._detailsExpanded66=new Set();
  card._windowSwitchPending66=new Set();card._calibrationExpanded65=new Set();
  card._expanded=new Set();card._areaDeviceIds=new Map();card._config={entity:'sensor.hem'};
  return card;
};
const room=(c,area)=>c._hass.states['sensor.hem'].attributes.dashboard.rooms.find(r=>r.area_id===area);
const glance=(c,area)=>c._room(room(c,area)).split('</summary>')[0];
const tones=html=>[...html.matchAll(/class="[^"]*hem-room-metric107[^\"]*hem-activity-([a-z]+)[^\"]*"/g)].map(m=>m[1]);
const measurement=(c,metric='temperature',area='heat')=>c._measurementActivityB6(metric,area);
const change=(c,id,patch)=>{
  const old=c._hass.states[id];
  c._hass={...c._hass,states:{...c._hass.states,[id]:{...old,...patch,
    attributes:patch.attributes?{...old.attributes,...patch.attributes}:old.attributes}}};
};
const noActive=(c,area)=>assert.match(glance(c,area),/class="hem-room-active87" aria-label="0 Active"/);
const cases=[];function test(name,run){cases.push({name,run});}

test('screenshot thermostat mode produces qualified heat feedback without an active device',()=>{
  const c=make(),result=measurement(c);
  assert.equal(result.tone,'heatmode');
  assert.match(result.text,/Enabled mode: Heating; current activity is not reported/);
  assert.deepEqual(tones(glance(c,'heat')),['heatmode','neutral','neutral','neutral']);
  noActive(c,'heat');
  for(const demand of [0,2.4,100]){
    change(c,'climate.managed_heater',{attributes:{controller_status:{status:'controlling',demand_percent:demand}}});
    assert.equal(measurement(c).tone,'heatmode','PID demand changed the mode evidence');
  }
  change(c,'climate.heater',{attributes:{temperature:5,current_temperature:25}});
  assert.equal(measurement(c).tone,'heatmode','Target error was mistaken for native activity');
});
test('only the relevant measurement receives each single-direction native mode hint',()=>{
  for(const [area,metric,wanted] of [
    ['heat','temperature','heatmode'],['cool','temperature','coolmode'],['dry','humidity','drymode']]){
    const c=make();assert.equal(measurement(c,metric,area).tone,wanted);
    assert.equal(measurement(c,metric==='humidity'?'temperature':'humidity',area).tone,'neutral');
    for(const unrelated of ['co2','aqi','pressure'])assert.equal(measurement(c,unrelated,area).tone,'neutral');
    noActive(c,area);
    const reading=room(c,area).readings.find(r=>r.metric===metric);
    assert.equal(c._metricActivityHelpB6(reading,area).tone,wanted);
    assert.match(c._metric(reading,false,area),new RegExp('hem-activity-'+wanted));
  }
});
test('missing, null and empty action allow a hint; explicit action always takes precedence',()=>{
  for(const action of [undefined,null,'','  ']){
    const c=make();change(c,'climate.heater',{attributes:{hvac_action:action}});
    assert.equal(measurement(c).tone,'heatmode');noActive(c,'heat');
  }
  for(const [action,wanted,label] of [
    ['heating','heat','Heating'],['cooling','cool','Cooling'],
    ['preheating','preheat','Preheating'],['defrosting','defrost','Defrosting'],
    ['idle','neutral','Idle'],['off','neutral','Off'],
    ['unknown','neutral','Current activity is not reported'],
    ['unrecognized-action','neutral','Current activity is not reported']]){
    const c=make();change(c,'climate.heater',{attributes:{hvac_action:action}});
    assert.deepEqual(measurement(c),{tone:wanted,text:label},action);
    assert.ok(!measurement(c).text.includes('Enabled mode'));
  }
  for(const action of [false,0,{},[],['heating'],'constructor','__proto__','toString']){
    const c=make();change(c,'climate.heater',{attributes:{hvac_action:action}});
    assert.equal(measurement(c).tone,'neutral',JSON.stringify(action));noActive(c,'heat');
  }
});
test('native Off, auto and unavailable cannot borrow the facade selected heat mode',()=>{
  for(const mode of ['off','auto','heat_cool','fan_only','unknown','unavailable','unexpected']){
    const c=make();change(c,'climate.heater',{state:mode});
    assert.equal(measurement(c).tone,'neutral',mode);noActive(c,'heat');
  }
  const c=make();delete c._hass.states['climate.heater'];
  assert.equal(measurement(c).tone,'neutral');noActive(c,'heat');
});
test('native source and supply restored or unavailable evidence suppresses mode hints',()=>{
  for(const state of ['off','unknown','unavailable',null]){
    const c=make();change(c,'climate.managed_heater',{attributes:{upstream_power_switch:'switch.supply'}});
    if(state!==null)c._hass.states['switch.supply']={state,attributes:{}};
    assert.equal(measurement(c).tone,'neutral',String(state));noActive(c,'heat');
    assert.ok(!measurement(c).text.includes('Enabled mode'));
  }
  const c=make();change(c,'climate.managed_heater',{attributes:{upstream_power_switch:'switch.supply'}});
  c._hass.states['switch.supply']={state:'on',attributes:{}};
  assert.equal(measurement(c).tone,'heatmode');
  const liveSupply=c._controllerSignature();
  change(c,'switch.supply',{attributes:{restored:true}});
  assert.notEqual(c._controllerSignature(),liveSupply,'Supply restored flag did not invalidate rendering');
  assert.equal(measurement(c).tone,'neutral','Restored supply ON was accepted as live power evidence');
  assert.match(measurement(c).text,/Power supply state unavailable/);
  const restoredSupply=c._controllerSignature();
  change(c,'switch.supply',{attributes:{restored:false}});
  assert.notEqual(c._controllerSignature(),restoredSupply);
  assert.equal(measurement(c).tone,'heatmode');
  for(const action of [undefined,'heating']){
    const restored=make();change(restored,'climate.heater',{attributes:{restored:true,hvac_action:action}});
    assert.equal(measurement(restored).tone,'neutral');
    assert.match(measurement(restored).text,/Device unavailable/);noActive(restored,'heat');
  }
});
test('wrong room, foreign primary and ambiguous source lists cannot create a mode hint',()=>{
  const foreign=make();change(foreign,'climate.heater',{attributes:{area_id:'cool'}});
  assert.equal(measurement(foreign).tone,'neutral');noActive(foreign,'heat');
  const primary=make();change(primary,'climate.managed_heater',{
    attributes:{physical_primary_entity_id:'climate.cooler'}});
  assert.equal(measurement(primary).tone,'neutral');noActive(primary,'heat');
  const ambiguous=make();
  for(const id of ['climate.managed_heater','select.method_heater'])change(ambiguous,id,{attributes:{
    source_entity_ids:['climate.heater','climate.second_heater'],physical_primary_entity_id:null}});
  ambiguous._hass.states['climate.second_heater']={state:'heat',attributes:{hvac_modes:['off','heat']}};
  assert.equal(measurement(ambiguous).tone,'neutral');noActive(ambiguous,'heat');
  const absent=make();delete absent._hass.states['climate.managed_heater'];delete absent._hass.states['select.method_heater'];
  assert.equal(measurement(absent).tone,'neutral','Unselected physical device was silently enrolled');
});
test('a companion climate cannot supply mode feedback for an idle primary endpoint',()=>{
  const c=make();change(c,'climate.heater',{attributes:{hvac_action:'idle'}});
  for(const id of ['climate.managed_heater','select.method_heater'])change(c,id,{attributes:{
    source_entity_ids:['climate.heater','climate.accessory']}});
  c._hass.states['climate.accessory']={state:'heat',attributes:{hvac_modes:['off','heat']}};
  assert.equal(measurement(c).tone,'neutral');noActive(c,'heat');
});
test('reported activity wins over enabled modes and opposing mode hints remain qualified',()=>{
  const c=make();change(c,'climate.mixed_cool',{attributes:{hvac_action:null}});
  assert.equal(measurement(c,'temperature','mixed').tone,'heat');
  assert.match(measurement(c,'temperature','mixed').text,/Heating/);
  assert.match(measurement(c,'temperature','mixed').text,/Enabled mode: Cooling/);
  change(c,'climate.mixed_heat',{attributes:{hvac_action:null}});
  assert.equal(measurement(c,'temperature','mixed').tone,'mixedmode');
  assert.match(measurement(c,'temperature','mixed').text,/Enabled mode: Heating/);
  assert.match(measurement(c,'temperature','mixed').text,/Enabled mode: Cooling/);
  for(const id of ['humidifier.mixed_wet','humidifier.mixed_dry'])change(c,id,{state:'off',attributes:{action:'off'}});
  noActive(c,'mixed');
  change(c,'climate.mixed_heat',{state:'off',attributes:{hvac_action:'heating'}});
  assert.equal(measurement(c,'temperature','mixed').tone,'conflict');
  assert.match(measurement(c,'temperature','mixed').text,/reported while set to Off/);
});
test('supply Off retains contradiction explanation without enabling activity',()=>{
  const c=make();change(c,'climate.heater',{attributes:{hvac_action:'heating'}});
  change(c,'climate.managed_heater',{attributes:{upstream_power_switch:'switch.supply'}});
  c._hass.states['switch.supply']={state:'off',attributes:{}};
  assert.equal(measurement(c).tone,'neutral');
  assert.match(measurement(c).text,/Heating reported.*Power supply off/);noActive(c,'heat');
});
test('native mode, action and restored-only updates all invalidate the render signature',()=>{
  for(const patch of [{state:'off'},{state:'cool'},{attributes:{hvac_action:'heating'}},
      {attributes:{restored:true}},{attributes:{restored:false}}]){
    const c=make(),signature=c._controllerSignature();change(c,'climate.heater',patch);
    assert.notEqual(c._controllerSignature(),signature,JSON.stringify(patch));
  }
  const c=make();change(c,'climate.heater',{attributes:{restored:true}});
  const old=c._controllerSignature();change(c,'climate.heater',{attributes:{restored:false}});
  assert.notEqual(c._controllerSignature(),old);
  assert.equal(measurement(c).tone,'heatmode');
});
test('native mode qualifications are localized in English, Greek and German',()=>{
  for(const [language,fragments] of [
    ['en',['Enabled mode: Heating','current activity is not reported']],
    ['el',['Ενεργοποιημένη λειτουργία: Θέρμανση','δεν αναφέρεται η τρέχουσα δραστηριότητα']],
    ['de',['Aktivierter Modus: Heizen','die aktuelle Aktivität wird nicht gemeldet']]]){
    const c=make();c._hass.language=language;
    for(const fragment of fragments)assert.ok(measurement(c).text.includes(fragment),measurement(c).text);
    assert.ok(!measurement(c).text.includes('{mode}'));
  }
});
test('rendering does not mutate evidence or expose standalone mode text',()=>{
  const c=make(),before=JSON.stringify(c._hass.states);
  for(const area of ['heat','cool','dry','mixed']){
    const html=glance(c,area);
    assert.ok(!html.replace(/<[^>]*>/g,' ').includes('Enabled mode'));
    c._room(room(c,area));
  }
  assert.equal(JSON.stringify(c._hass.states),before);
});
let failed=0;for(const {name,run} of cases){try{run();console.log('PASS: '+name);}
 catch(error){failed++;console.error('FAIL: '+name+'\n'+error.stack);}}
if(failed)process.exitCode=1;else console.log('NATIVE_MODE_FEEDBACK_EVIDENCE=PASS ('+cases.length+' cases)');
"""


REPORT = r"""([area,metric])=>{
 const room=card.shadowRoot.querySelector('[data-room-fold87="'+area+'"]');
 const badge=room.querySelector('summary [data-hem-average105="'+metric+'"]')||
   room.querySelector('summary [data-hem-source105="sensor.'+area+'_'+metric+'"]');
 const icon=badge.querySelector(':scope > ha-icon'),style=getComputedStyle(badge);
 const average=badge.querySelector('.hem-avg-marker105 ha-icon');
 const device=room.querySelector('.hem-device-measures87 .hem-device-reading87.hem-activity-'+
   (metric==='humidity'?'drymode':'heatmode'));
 const body=room.querySelector('.metric[data-room-metric114="'+metric+'"]');
 return {title:badge.title,classes:badge.className,colour:getComputedStyle(icon).color,
   valueColour:getComputedStyle(badge.querySelector('.hem-room-metric-value107')).color,
   averageColour:average?getComputedStyle(average).color:null,
   outline:style.outlineStyle,outlineColour:style.outlineColor,
   width:badge.getBoundingClientRect().width,height:badge.getBoundingClientRect().height,
   active:room.querySelector('.hem-room-active87').getAttribute('aria-label'),
   device:device?{outline:getComputedStyle(device).outlineStyle,
     colour:getComputedStyle(device.querySelector('ha-icon')).color}:null,
   body:body?{outline:getComputedStyle(body).outlineStyle,
     colour:getComputedStyle(body.querySelector('.metric-name>ha-icon')).color}:null};
}"""


def browser_checks(states):
    from playwright.sync_api import sync_playwright

    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
        shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome, "Chromium required"
    helpers = baseline.baseline.layout_helpers()
    colours = baseline.baseline.COLOURS
    output = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
    if output:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 760, "height": 1000})
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
          window.calls=[];window.card=document.createElement('home-environment-manager-card');
          document.getElementById('card-frame').append(card);
          card._hass={language:'en',states,localize:()=>undefined,callWS:async()=>({}),
            callService:(...args)=>{calls.push(args);return Promise.resolve()}};
          card._config={entity:'sensor.hem'};card._expanded.add('heat');
          card._roomsExpanded87=new Set(['heat']);
          // Keep the existing temperature information tile visible to test
          // its bubble and dashed marker as well as the compact summary.
          const room=states['sensor.hem'].attributes.dashboard.rooms.find(r=>r.area_id==='heat');
          const reading=room.readings.find(r=>r.metric==='temperature');
          reading.exceeded=true;reading.threshold=20;
          card._renderContent(true);
          window.beforeSensor=card._hass.states['sensor.hem'];
          window.beforeFacade=card._hass.states['climate.managed_heater'];
          window.nativeChange=patch=>{
            const old=card._hass.states['climate.heater'];
            card.hass={...card._hass,states:{...card._hass.states,'climate.heater':{
              ...old,...patch,attributes:{...old.attributes,...patch.attributes}}}};
          };
        }""", states)
        for language, fragment in (
            ("en", "Enabled mode: Heating"),
            ("el", "Ενεργοποιημένη λειτουργία: Θέρμανση"),
            ("de", "Aktivierter Modus: Heizen"),
        ):
            page.evaluate("language=>{card.hass={...card._hass,language}}", language)
            page.wait_for_function("""text=>card.shadowRoot.querySelector(
                '[data-room-fold87="heat"] summary [data-hem-average105="temperature"]').title.includes(text)""", arg=fragment)
            for width in (320, 390, 760):
                page.set_viewport_size({"width": width, "height": 1000})
                helpers["assert_layout"](page.evaluate(helpers["LAYOUT_REPORT"]), f"mode-{language}-{width}")
                report = page.evaluate(REPORT, ["heat", "temperature"])
                assert report["colour"] == report["outlineColour"] == colours["heat"], report
                assert report["outline"] == "dashed", report
                assert report["valueColour"] != colours["heat"], report
                assert report["averageColour"] not in colours.values(), report
                assert report["device"] == {"outline": "dashed", "colour": colours["heat"]}, report
                assert report["body"] == {"outline": "dashed", "colour": colours["heat"]}, report
                assert fragment in report["title"], report
                for area, metric, colour in (("cool", "temperature", "cool"), ("dry", "humidity", "dry")):
                    other = page.evaluate(REPORT, [area, metric])
                    assert other["colour"] == colours[colour] and other["outline"] == "dashed", other
                if output:
                    page.locator("#card-frame").screenshot(path=str(output / f"native-mode-{language}-{width}.png"))
            page.locator('[data-room-fold87="heat"] [data-room-metric114="temperature"] .metric-help > summary').click()
            page.wait_for_function("!!card._floatingInfo87")
            assert fragment in page.locator('.hem-floating-info87').inner_text()
            page.keyboard.press("Escape")

        # Native-only updates through the public HA setter must change both
        # presentation surfaces while the facade and dashboard stay identical.
        page.evaluate("()=>{card.hass={...card._hass,language:'en'}}")
        page.wait_for_function("card._language()==='en'")
        page.set_viewport_size({"width": 390, "height": 1000})
        initial = page.evaluate(REPORT, ["heat", "temperature"])
        for patch, tone, outlined in (
            ({"attributes": {"hvac_action": "heating"}}, "heat", False),
            ({"attributes": {"hvac_action": "idle"}}, "neutral", False),
            ({"attributes": {"hvac_action": None}}, "heatmode", True),
            ({"attributes": {"restored": True}}, "neutral", False),
            ({"attributes": {"restored": False}}, "heatmode", True),
            ({"state": "off"}, "neutral", False),
            ({"state": "heat"}, "heatmode", True),
        ):
            page.evaluate("patch=>nativeChange(patch)", patch)
            page.wait_for_function("""tone=>card.shadowRoot.querySelector(
                '[data-room-fold87="heat"] summary [data-hem-average105="temperature"]').classList.contains('hem-activity-'+tone)""", arg=tone)
            report = page.evaluate(REPORT, ["heat", "temperature"])
            assert (report["outline"] == "dashed") is outlined, (patch, report)
            assert abs(report["width"] - initial["width"]) < 0.1, (patch, report, initial)
            assert abs(report["height"] - initial["height"]) < 0.1, (patch, report, initial)
            assert report["active"] == ("1 Active" if tone == "heat" else "0 Active"), report
            assert page.evaluate("card._hass.states['sensor.hem']===beforeSensor && card._hass.states['climate.managed_heater']===beforeFacade")
        assert page.evaluate("calls") == []
        assert not errors, errors
        browser.close()
    print("NATIVE_MODE_FEEDBACK_COLOURS_BUBBLES_NATIVE_UPDATES_MOBILE=PASS")


if __name__ == "__main__":
    states = fixture()
    result = subprocess.run(["node", "-e", NODE_CHECKS, str(CARD)],
        input=json.dumps({"states": states}), text=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    if "--logic-only" not in sys.argv:
        browser_checks(states)
