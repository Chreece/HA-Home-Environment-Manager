"""B7: render real AQI source evidence without inventing units or safe air.

The fixture comes from production discovery, freshness, evaluation and dashboard
projection. Node runs the complete card; Chromium also checks the existing info
bubble, its read-only source actions, live refresh, and narrow-screen geometry.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
BACKEND = ROOT / ".github/tests/test_074b7_aqi_evidence.py"


def fixture():
    # Keep the backend test's lightweight HA module stubs in its own process.
    snapshot = json.loads(subprocess.check_output(
        [sys.executable, "-I", str(BACKEND), "--fixture-json"], text=True))
    readings = snapshot["outdoor"]["readings"] + [
        item for room in snapshot["rooms"] for item in room["readings"]]
    states = {item["entity_id"]: {"state": str(item["value"]), "attributes": {
        "friendly_name": item["name"], "unit_of_measurement": item["unit"],
        "device_class": item["metric"]}} for item in readings}
    states["sensor.hem"] = {"state": "ready", "attributes": {"dashboard": snapshot}}
    states["binary_sensor.window"] = {"state": "off", "attributes": {"friendly_name": "Window"}}
    return states


NODE_CHECKS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const states=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');
const make=()=>{
  const c=Object.create(Card.prototype);
  c._hass={language:'en',states:structuredClone(states),localize:()=>undefined,
    callService:()=>{throw Error('AQI display sent a service call')}};
  c._config={entity:'sensor.hem'};return c;
};
const outside=c=>c._hass.states['sensor.hem'].attributes.dashboard.outdoor;
const heading=html=>html.match(/class="outside-title">([^<]*)/)[1];
const cases=[];function test(name,run){cases.push({name,run});}

test('the seven production sources retain names and raw values without inferring scales',()=>{
  const c=make(),o=outside(c),before=JSON.stringify(o),html=c._outside(o);
  const views=o.readings.map(r=>c._outsideReadingB7(r));
  assert.deepEqual(views.map(r=>r.value),['1','2','1','2','1','1','85']);
  assert.equal(new Set(views.map(r=>r.name)).size,7);
  for(const [i,r] of views.entries()){
    const row=c._outsideReadingInfoB7(r);
    assert.ok(row.includes('>'+r.name+'</span>'),r.name);
    assert.ok(row.includes('data-outside-source123="'+o.readings[i].entity_id+'"'));
    assert.ok(r.title.includes(o.readings[i].entity_id));
    if(i<6){
      assert.equal(r.unit,'AQI');assert.equal(r.evaluated,false);
      assert.equal(r.reason,'AQI scale not configured');
      assert.ok(!/(?:US AQI|ppm|%|°C)/.test(r.text));
    }else{
      assert.equal(r.text,'85 US AQI');assert.equal(r.evaluated,true);assert.equal(r.reason,'');
    }
  }
  assert.match(html,/outside-partial/);assert.doesNotMatch(html,/outside-safe/);
  assert.equal(heading(html),'AQI scale not configured');
  assert.equal((html.match(/class="out-chip dim /g)||[]).length,6);
  assert.doesNotMatch(html,/out-chip elevated/);
  assert.equal(JSON.stringify(o),before,'Rendering changed backend/control evidence');
  assert.equal(o.safe_to_ventilate,true,'Optional AQI behavior changed');
  assert.match(c._outsideAQIHelpB7(),/Home settings, search AQI/);
  assert.doesNotMatch(c._outsideAQIHelpB7(),/Advanced|must|Outside settings/);
});

test('missing, stale and invalid numeric data cannot borrow a native HA state',()=>{
  for(const value of [null,NaN,Infinity,'1',1]){
    const c=make(),o=outside(c),r=o.readings[0];
    c._hass.states[r.entity_id].state='99';
    Object.assign(r,{value,value_available:false,available:false,evaluation_status:'unavailable'});
    o.unavailable_sensors=[r.entity_id];
    const view=c._outsideReadingB7(r),html=c._outside(o);
    assert.equal(view.text,'-');assert.equal(view.unit,'');assert.equal(view.evaluated,false);
    assert.equal(view.reason,c._t('missing'));assert.equal(view.name,'AQI Co2');
    assert.equal(heading(html),c._t('partialOutside'));
    assert.doesNotMatch(c._outsideReadingInfoB7(view),/>99(?: |<)/);
  }
  const c=make(),r=outside(c).readings[0];
  for(const value of [null,NaN,Infinity,'1'])
    assert.equal(c._outsideReadingB7({...r,value,value_available:true}).text,'-');
  assert.equal(c._outsideReadingB7({...r,value_available:false,available:true,
    evaluation_status:'ready'}).evaluated,false,'Explicit missing evidence wins');
});

test('legacy evaluated values remain compatible but unevaluated raw values require evidence',()=>{
  const c=make(),o=outside(c);
  for(const r of o.readings){delete r.value_available;delete r.evaluation_status;}
  assert.equal(c._outsideReadingB7(o.readings[0]).text,'-');
  assert.equal(c._outsideReadingB7(o.readings[6]).text,'85 US AQI');
});

test('invalid selected scales and missing custom limits get distinct neutral explanations',()=>{
  const c=make(),o=outside(c),r=o.readings[6];
  Object.assign(r,{value:701,available:false,value_available:true,evaluation_status:'invalid',
    details:{aqi:{scale:'us_epa',status:'invalid',reason:'aqi_out_of_range'}}});
  const v=c._outsideReadingB7(r);
  assert.equal(v.text,'701 US AQI');assert.equal(v.evaluated,false);
  assert.equal(v.reason,'AQI value or scale cannot be evaluated');
  assert.equal(heading(c._outside(o)),'AQI cannot be evaluated');
  Object.assign(r,{value:85,unit:'AQI',evaluation_status:'configuration_required',
    details:{aqi:{scale:'custom',status:'configuration_required',reason:'custom_limit_required'}}});
  assert.equal(c._outsideReadingB7(r).reason,'AQI comparison limit not configured');
  o.readings=[r];
  assert.equal(heading(c._outside(o)),'AQI comparison limit not configured');
});

test('weather and pollution hazards keep precedence over optional AQI setup',()=>{
  const c=make(),o=outside(c),r=o.readings[6];
  Object.assign(r,{value:155,available:true,value_available:true,evaluation_status:'ready',exceeded:true});
  o.status='unsafe';o.blockers=[{code:'outside_aqi',label:r.name,value:'155 US AQI'}];
  const html=c._outside(o);
  assert.equal(heading(html),c._t('badOutside'));assert.match(html,/outside-unsafe/);
  assert.equal((html.match(/class="out-chip elevated/g)||[]).length,1);
  o.conditional_open=true;
  assert.equal(heading(c._outside(o)),c._t('attention')+' · '+c._t('outside'));
  o.status='partial';o.blockers=[{code:'unavailable_weather'}];
  assert.equal(heading(c._outside(o)),c._t('partialOutside'));
});

test('source metadata is escaped and names cannot change sensor type or unit',()=>{
  const c=make(),base=outside(c).readings[0];
  const r={...base,metric:'humidity',name:'AQI Humidity <img src=x onerror=alert(1)>',
    value:61,unit:'%',available:true,evaluation_status:'ready'};
  const view=c._outsideReadingB7(r),row=c._outsideReadingInfoB7(view);
  assert.equal(view.text,'61 %');assert.equal(view.reason,'');
  assert.match(row,/&lt;img/);assert.doesNotMatch(row,/<img/);
  const fake=c._outsideReadingB7({...base,entity_id:'sensor.fake" onclick="attack()'});
  assert.equal(fake.id,null);assert.doesNotMatch(c._outsideReadingInfoB7(fake),/data-outside-source123=/);
  const noName=c._outsideReadingB7({...base,name:''});
  assert.equal(noName.name,base.entity_id);
});

test('AQI notes follow English, German and Greek card language',()=>{
  for(const [lang,note] of [['en','AQI scale not configured'],
      ['de','AQI-Skala nicht eingerichtet'],['el','Δεν έχει οριστεί η κλίμακα AQI']]){
    const c=make();c._hass.language=lang;
    assert.equal(c._outsideReadingB7(outside(c).readings[0]).reason,note);
    assert.ok(c._outsideAQIHelpB7().includes('AQI'));
  }
});

test('ordinary weather and evaluated pollutant presentation keep their status and measurements',()=>{
  const c=make(),o=outside(c);o.status='safe';o.readings=[];
  const html=c._outside(o);
  assert.equal(heading(html),c._t('goodOutside'));
  for(const text of ['22.7°C','61%','19.8 km/h'])assert.ok(html.includes(text),text);
  assert.doesNotMatch(html,/data-outside-reason-b7|AQI scale not configured/);
});

for(const {name,run} of cases){run();console.log('PASS '+name);}
console.log('B7_AQI_PRODUCTION_VALUES_NAMES_EVIDENCE=PASS ('+cases.length+' cases)');
"""


SETUP = r"""states=>{
  window.calls=[];window.requests=[];window.info=[];
  window.card=document.createElement('home-environment-manager-card');
  document.querySelector('main').append(card);
  card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
  card.setConfig({entity:'sensor.hem'});
  card.hass={language:'en',states,entities:{},localize:()=>undefined,
    config:{time_zone:'UTC'},connection:{},
    callService:(...args)=>{calls.push(args);return Promise.resolve()},
    callWS:async request=>{
      requests.push(structuredClone(request));
      if(['config/device_registry/list','config/floor_registry/list',
          'config/area_registry/list'].includes(request.type))return [];
      if(request.type==='history/history_during_period'){
        const now=Date.now()/1000;
        return {[request.entity_ids[0]]:[{s:'1',lu:now-120},{s:'2',lu:now-60}]};
      }
      throw Error('Unexpected mocked HA request: '+request.type);
    }};
  window.patchOutsideB7=patch=>{
    const next=structuredClone(card._hass.states),root=next['sensor.hem'];
    root.attributes.dashboard_revision=(root.attributes.dashboard_revision||0)+1;
    const out=root.attributes.dashboard.outdoor;
    if(patch.onlyFirst)out.readings=out.readings.slice(0,1);
    if(patch.reading)Object.assign(out.readings[0],patch.reading);
    if(patch.outdoor)Object.assign(out,patch.outdoor);
    card.hass={...card._hass,states:next};
  };
}"""


REPORT = r"""()=>{
  const pop=card._floatingInfo87,out=card.shadowRoot.querySelector('.outside');
  const box=node=>{const r=node.getBoundingClientRect();
    return {left:r.left,right:r.right,width:r.width,top:r.top,bottom:r.bottom};};
  return {viewport:document.documentElement.clientWidth,
    overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,
    heading:out.querySelector('.outside-title').textContent,
    status:out.className,weather:out.querySelector('.weather-line').getAttribute('aria-label'),
    popup:pop?box(pop):null,scroll:pop?{client:pop.clientHeight,full:pop.scrollHeight}:null,
    rows:pop?[...pop.querySelectorAll('[data-outside-source123]')].map(row=>({
      id:row.getAttribute('data-outside-source123'),name:row.querySelector('.hem-outside-info-name-b7')?.textContent,
      note:row.querySelector('.hem-outside-info-note-b7')?.textContent||'',
      value:row.querySelector('.hem-outside-info-value123')?.textContent,
      title:row.getAttribute('title'),box:box(row),
      valueBox:box(row.querySelector('.hem-outside-info-value123'))})):[]};
}"""


def browser_checks(states):
    from playwright.sync_api import expect, sync_playwright

    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
        shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome, "Chromium required"
    icons_tree = ast.parse((ROOT / ".github/tests/test_beta107_room_metrics.py").read_text())
    icons = next(ast.literal_eval(node.value) for node in icons_tree.body
                 if isinstance(node, ast.Assign) and any(
                     isinstance(target, ast.Name) and target.id == "ICON_FIXTURE"
                     for target in node.targets))
    shots = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
    if shots:
        shots = Path(shots)
        shots.mkdir(parents=True, exist_ok=True)
    expected = states["sensor.hem"]["attributes"]["dashboard"]["outdoor"]["readings"]
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
          main{width:100%;max-width:100%}home-environment-manager-card{display:block}
        </style></head><body><main></main></body></html>""")
        page.evaluate(icons)
        page.add_script_tag(path=str(CARD))
        page.evaluate(SETUP, states)
        disclosure = page.locator('details.hem-outside-info123 > summary')
        popup = page.locator('.hem-floating-info87')
        for width in (320, 390, 760):
            page.set_viewport_size({"width": width, "height": 1000})
            expect(disclosure).to_be_visible()
            disclosure.click()
            expect(popup).to_be_visible()
            report = page.evaluate(REPORT)
            assert not report["overflow"], (width, report)
            assert "outside-partial" in report["status"], report
            assert report["heading"] == "AQI scale not configured", report
            assert report["weather"] == "Partly cloudy · 22.7°C · 61% · 19.8 km/h", report
            assert 11 <= report["popup"]["left"] < report["popup"]["right"] <= width - 11, report
            assert 11 <= report["popup"]["top"] < report["popup"]["bottom"] <= 989, report
            assert report["scroll"]["full"] > report["scroll"]["client"], report
            assert len(report["rows"]) == 7, report
            for actual, source in zip(report["rows"], expected):
                assert actual["id"] == source["entity_id"] and actual["name"] == source["name"], actual
                assert actual["value"] == f'{int(source["value"])} {source["unit"]}', actual
                assert actual["id"] in actual["title"], actual
                assert actual["note"] == ("" if source["available"] else "AQI scale not configured"), actual
                assert actual["box"]["left"] >= report["popup"]["left"] - 1, actual
                assert actual["box"]["right"] <= report["popup"]["right"] + 1, actual
                assert actual["valueBox"]["left"] >= actual["box"]["left"] - 1, actual
                assert actual["valueBox"]["right"] <= actual["box"]["right"] + 1, actual
            expect(popup).to_contain_text("Home settings, search AQI")
            # An overflowing popup must remain scrollable and let the user
            # reach the final actual source, rather than merely clip it.
            scroll = popup.evaluate("""node=>{
              node.scrollTop=node.scrollHeight;
              const last=node.querySelector('[data-outside-source123="sensor.piraeus_air_quality_index"]');
              const box=node.getBoundingClientRect(),row=last.getBoundingClientRect();
              return {top:node.scrollTop,overflow:getComputedStyle(node).overflowY,
                popupTop:box.top,popupBottom:box.bottom,rowTop:row.top,rowBottom:row.bottom};
            }""")
            assert scroll["overflow"] in ("auto", "scroll") and scroll["top"] > 0, scroll
            assert scroll["rowTop"] >= scroll["popupTop"] - 1, scroll
            assert scroll["rowBottom"] <= scroll["popupBottom"] + 1, scroll
            popup.evaluate("node=>node.scrollTop=0")
            if shots:
                page.screenshot(path=str(shots / f"b7-aqi-{width}.png"), full_page=True)
            page.keyboard.press("Escape")
            expect(popup).to_have_count(0)

        # Clicking a named source keeps the existing exact-entity history and
        # native More info path. It must never call a control service.
        disclosure.click()
        source = expected[1]["entity_id"]
        popup.locator(f'[data-outside-source123="{source}"]').click()
        expect(popup).to_have_count(0)
        history = page.locator('.hem-avg-dialog105')
        expect(history).to_be_visible()
        assert page.evaluate('card._averageDialog105.entity122') == source
        history.locator(f'[data-open-entity122="{source}"]').click()
        expect(history).to_have_count(0)
        assert page.evaluate('info.at(-1)') == source

        # Reconcile an open bubble through the real HA setter, with both value
        # and scale status changing while source identity stays stable.
        disclosure.click()
        page.evaluate("patchOutsideB7({reading:{value:3,unit:'US AQI',available:true,value_available:true,evaluation_status:'ready'}})")
        first = popup.locator('[data-outside-source123="sensor.aqi_co2"]')
        expect(first.locator('.hem-outside-info-value123')).to_have_text('3 US AQI')
        expect(first.locator('.hem-outside-info-note-b7')).to_have_count(0)
        expect(popup).to_have_count(1)
        expect(page.locator('details.hem-outside-info123')).to_have_attribute('open', '')
        # Native sensor state still has 1. Freshness was rejected by backend;
        # the card must show a named missing row rather than revive that value.
        page.evaluate("patchOutsideB7({reading:{value:null,available:false,value_available:false,evaluation_status:'unavailable'},outdoor:{unavailable_sensors:['sensor.aqi_co2']}})")
        expect(first.locator('.hem-outside-info-value123')).to_have_text('-')
        expect(first.locator('.hem-outside-info-note-b7')).to_have_text('Unavailable')
        expect(page.locator('.outside-title')).to_have_text('Some outdoor data missing')
        expect(popup).to_have_count(1)
        page.keyboard.press('Escape')

        # A single issue still exposes its source explanation through the same
        # info control; no extra visible card row or new control is introduced.
        for reading, title in (
            ({"value": 1, "unit": "AQI", "available": False, "value_available": True,
              "evaluation_status": "configuration_required", "details": {
                  "aqi": {"scale": "not_configured", "reason": "aqi_scale_not_selected"}}},
             "AQI scale not configured"),
            ({"value": None, "value_available": False, "evaluation_status": "unavailable"},
             "Some outdoor data missing"),
        ):
            page.evaluate("patch=>patchOutsideB7(patch)", {
                "onlyFirst": True, "reading": reading,
                "outdoor": {"unavailable_sensors": [] if reading["value_available"] else ["sensor.aqi_co2"]}})
            expect(disclosure).to_be_visible()
            expect(page.locator('.outside-title')).to_have_text(title)
            disclosure.click()
            expect(popup.locator('[data-outside-source123]')).to_have_count(1)
            expect(popup.locator('.hem-outside-info-name-b7')).to_have_text('AQI Co2')
            page.keyboard.press('Escape')
        assert page.evaluate('calls') == []
        requests = page.evaluate('requests')
        allowed = {'config/device_registry/list', 'config/floor_registry/list',
                   'config/area_registry/list', 'history/history_during_period'}
        assert all(request['type'] in allowed for request in requests), requests
        history_requests = [request for request in requests
                            if request['type'] == 'history/history_during_period']
        assert history_requests, requests
        assert all(request['entity_ids'] == [source] for request in history_requests), history_requests
        assert not errors, errors
        browser.close()
    print('B7_AQI_BUBBLE_SOURCES_MOBILE_LIVE_UPDATES=PASS')


if __name__ == "__main__":
    states = fixture()
    result = subprocess.run(["node", "-e", NODE_CHECKS, str(CARD)],
        input=json.dumps(states), text=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    if "--logic-only" not in sys.argv:
        browser_checks(states)
