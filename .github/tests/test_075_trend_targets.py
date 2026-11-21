"""Historical targets and controller output share the measured trend timeline.

Run production card code in Node; the default also exercises Chromium pointer,
keyboard, retry and 320px geometry. All transport and HA states are fixtures.
"""
from __future__ import annotations

import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
BASE = runpy.run_path(str(ROOT / ".github/tests/test_beta122_entity_trends.py"))
START = BASE["START"]

def backend_payloads():
    """Run real target resolution, capture, storage, authorization and WS copy."""
    source = runpy.run_path(str(ROOT / ".github/tests/test_075_control_trend_capture.py"))
    capture = source["CollectorTests"](methodName="runTest")
    capture.setUp()
    try:
        capture.capture()
        capture.dryer()
        source["CLOCK"].now += 30
        capture.capture()
        history = capture.manager._environment_history
        now = source["CLOCK"].now
    finally:
        capture.doCleanups()
    boundary = runpy.run_path(str(ROOT / ".github/tests/test_075_control_history.py"))
    transport = boundary["ControlTrendWebSocketTests"](methodName="runTest")
    transport.setUp()
    transport.manager._environment_history = history
    transport.report["measurement_evidence"] = {
        metric: {"source_ids": [sensor], "source_count": 1}
        for metric, sensor in (("temperature", "sensor.temp"), ("humidity", "sensor.rh"))
    }
    result = {"now": now}
    for metric, sources in (("temperature", ["sensor.temp"]), ("humidity", ["sensor.rh"]), ("mold", [])):
        with patch.object(boundary["api"].time, "time", return_value=now):
            boundary["api"].websocket_control_trend(transport.hass, transport.connection, {
                "id": 1, "type": "environment_manager/control_trend", "entity_id": "sensor.hem",
                "area_id": "room", "metric": metric, "source_ids": sources,
            })
        assert not transport.errors, transport.errors
        result[metric] = transport.results[-1]
    return result


def fixture():
    data = BASE["fixture"]()
    dashboard = data["states"]["sensor.hem"]["attributes"]["dashboard"]
    dashboard["control_trend_version"] = 1
    room = dashboard["rooms"][0]
    sources = ["sensor.temp_a", "sensor.temp_b"]
    samples = [{"t": START + index * 900, "v": 19 + index / 4} for index in range(5)]
    room["environment"]["measurement_evidence"]["temperature"]["trend"] = samples

    def point(at, until, target, **overrides):
        return {"t": START + at, "until": START + until, "target": target,
                "target_low": None, "target_high": None, "demand_percent": 40,
                "output_percent": 100, "output_kind": "activity",
                "profile": "home", "mode": "heat", "control_mode": "pid", **overrides}

    def series(points, **overrides):
        return {"metric": "temperature", "basis": "temperature", "unit": "°C",
                "feedback_source_ids": sources, "context_id": "living:temperature",
                "target_kind": "control", "points": points, **overrides}

    response = {
        "area_id": "living", "metric": "temperature", "source_ids": sources,
        "retention_seconds": 604800, "sample_interval_seconds": 300,
        "controllers": [
            {"controller_id": "radiator", "name": "Radiator <north>",
             "source_entity_ids": ["climate.radiator"],
             "series": [series([
                 point(450, 900, 21),
                 point(900, 1800, 22, profile="comfort", demand_percent=75),
                 point(1800, 2100, None, mode="off", demand_percent=0, output_percent=0),
                 point(2400, 3000, 23, break_before=True, demand_percent=None,
                       output_percent=None, output_kind=None),
                 point(3000, 3900, 22, profile="eco", output_kind="position", output_percent=25),
                 point(3900, 4200, 24, profile="comfort", demand_percent=80,
                       output_kind="position", output_percent=35),
             ])]},
            {"controller_id": "heat_pump", "name": "Heat pump",
             "source_entity_ids": ["climate.heat_pump"],
             "series": [series([point(600, 3300, None, target_low=20, target_high=23,
                                      demand_percent=None, output_percent=0, mode="auto")])]},
        ],
    }
    data.update(response=response, now=START + 6000, samples=samples,
                backend=backend_payloads(),
                languages=[path.stem for path in
                           (ROOT / "custom_components/environment_manager/translations").glob("*.json")])
    return data


NODE = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const data=JSON.parse(fs.readFileSync(0,'utf8')),t=data.start;
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(n){return this.classes.get(n)},define(n,C){this.classes.set(n,C)}};
global.window={innerWidth:590};
global.document={createElement:()=>({content:{firstElementChild:null}})};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card'),card=Object.create(Card.prototype);
let now=data.now;Date.now=()=>now*1000;
const pending=[];
card._config={entity:'sensor.hem'};
card._hass={language:'en',config:{time_zone:'Europe/Berlin'},states:structuredClone(data.states),connection:{},
  localize:()=>undefined,callService:()=>{throw Error('Trend called device service')},
  callWS:message=>new Promise((resolve,reject)=>pending.push({message,resolve,reject}))};
const nodes=new Map();
const node=key=>{
  if(!nodes.has(key))nodes.set(key,{textContent:'',style:{},attributes:{},
    setAttribute(k,v){this.attributes[k]=v},removeAttribute(k){delete this.attributes[k]}});
  return nodes.get(key);
};
const chart=node('chart'),outputChart=node('outputChart'),cursor=node('cursor'),dot=node('dot');
cursor.querySelector=()=>dot;
const handlers=new Map();
const root={scrollTop:0,setAttribute(){},addEventListener(type,handler){
  if(!handlers.has(type))handlers.set(type,[]);handlers.get(type).push(handler);
},querySelector(selector){
  if(['.hem-avg-body105','.hem-avg-head105>strong','[data-close-avg105]'].includes(selector))return null;
  if(selector==='.hem-trend-cursor114')return cursor;
  if(selector==='[data-trend-chart114]')return chart;
  return node(selector);
},querySelectorAll(selector){return selector==='[data-trend-chart114]'?[chart,outputChart]:[node('outputCursor')]}};
const open=()=>{
  const saved=card._averageDialog105={area:'living',metric:'temperature',sources:'sensor.temp_a|sensor.temp_b',
    width114:480,view114:{range:0,end:null,cursor:null},node:root};
  return saved;
};
const evidence=()=>card._evidence105('living','temperature');
const render=()=>card._averageBody105('living','temperature',evidence());
const original=JSON.stringify(data.response);
(async()=>{
  const saved=open();
  const task=card._loadControlTrend075(saved);
  assert.deepEqual(pending[0].message,{type:'environment_manager/control_trend',entity_id:'sensor.hem',
    area_id:'living',metric:'temperature',source_ids:['sensor.temp_a','sensor.temp_b']});
  assert.equal(saved.statusControl075,'loading');
  pending[0].resolve(data.response);await task;
  assert.equal(saved.statusControl075,'ready');
  let html=render(),model=saved.model114;
  assert.equal(model.points.length,5,'Control evidence became a measured sample');
  assert.equal(model.first,t);assert.equal(model.last,t+4200,'Latest control observation was clipped by older mean');
  assert.ok(model.min<19&&model.max>24&&model.max<30,'Percentage output polluted temperature scale');
  assert.ok(html.includes('hem-control-target075')&&html.includes('data-control-field075="target_low"'));
  assert.ok(html.includes('hem-control-band075')&&html.includes('hem-control-demand075')&&html.includes('hem-control-reported075'));
  assert.ok(html.includes('Radiator &lt;north&gt;')&&!html.includes('Radiator <north>'));
  assert.ok(html.includes('hem-control-target-key075')&&html.includes('hem-control-output-legend075'));
  assert.ok(!/NaN|Infinity|undefined/.test(html));
  const group=model.controls075[0];
  assert.equal(card._controlTrendPoint075(group,t+449),null,'Today target appeared before first observation');
  assert.equal(card._controlTrendPoint075(group,t+500).target,21);
  assert.equal(card._controlTrendPoint075(group,t+900).target,22,'Target did not step at its recorded time');
  assert.equal(card._controlTrendPoint075(group,t+2200),null,'Target bridged genuine unobserved interval');
  assert.equal(card._controlTrendPoint075(group,t+4201),null,'Target extended after last observed interval');
  const targetPath=card._controlTrendPath075(group,model,'target');
  assert.ok((targetPath.match(/M/g)||[]).length>=2,'Restart or off interval was connected');
  card._inspectTrend114(t+1050);
  assert.equal(card._trendSelection114(model).time,t+1050,'Mean snap moved controller cursor to another time');
  assert.equal(node('[data-control-target075="0"]').textContent,'22 °C');
  assert.equal(node('[data-control-demand075="0"]').textContent,'75%');
  assert.equal(node('[data-control-output075="0"]').textContent,'On');
  assert.ok(node('[data-trend-label114]').textContent.includes(card._trendDate114(t+900,'time')),
    'Nearest measured sample lost its actual recorded time');
  assert.equal(node('[data-trend-value114]').attributes['data-sample-time114'],String(t+900));
  assert.equal(dot.style.display,'none','Nearest sample dot moved to unrecorded cursor time');
  assert.equal(outputChart.attributes['aria-valuetext'],chart.attributes['aria-valuetext']);
  card._inspectTrend114(t+1800);
  assert.equal(node('[data-control-target075="0"]').textContent,'—');
  assert.equal(node('[data-control-demand075="0"]').textContent,'0%','Zero demand was mistaken for missing');
  assert.equal(node('[data-control-output075="0"]').textContent,'Off','Reported OFF was mistaken for missing');
  card._inspectTrend114(t+2500);
  assert.equal(node('[data-control-demand075="0"]').textContent,'—');
  assert.equal(node('[data-control-output075="0"]').textContent,'—');
  saved.view114.cursor=null;saved.view114.end=null;render();card._inspectTrend114();
  assert.equal(card._trendSelection114(saved.model114).time,t+4200);
  assert.equal(node('[data-control-target075="0"]').textContent,'24 °C');
  assert.equal(node('[data-trend-value114]').textContent,'—','Stale mean was fabricated at the new target time');
  assert.ok(saved.model114.inspect075.some(p=>p.t===t+3900),'Keyboard cannot reach a target-only transition');
  assert.equal(saved.model114.inspect075.at(-1).t,t+4200);

  // No measured history still displays bounded control evidence, with no PV.
  const mean=evidence().value,old=mean.trend;mean.trend=[];
  saved.view114={range:0,end:null,cursor:null};html=render();model=saved.model114;
  assert.equal(model.points.length,0);assert.ok(html.includes('data-trend-chart114'));
  assert.equal(model.first,t+450);assert.equal(model.last,t+4200);
  card._inspectTrend114(t+900);
  assert.equal(node('[data-trend-value114]').textContent,'—');
  assert.equal(node('[data-control-target075="0"]').textContent,'22 °C');
  card._bindTrend114(saved,null);
  const key=key=>handlers.get('keydown').forEach(handler=>handler({
    key,target:{closest:()=>chart},preventDefault(){},
  }));
  key('ArrowRight');
  assert.equal(saved.view114.cursor,t+1800,'Keyboard got stuck at a target with no measured sample');
  key('ArrowRight');assert.equal(saved.view114.cursor,t+2100);
  key('End');assert.equal(saved.view114.cursor,t+4200);
  mean.trend=old;

  // A native °F sensor gets converted C targets, never a C value relabelled F.
  const native=card._averageDialog105={...saved,entity122:'sensor.temp_f',metric:'temperature',unit122:'°F',
    history122:[{t,v:68},{t:t+1200,v:69}],historyEnd122:t+3600,status122:'ready',
    controlData075:structuredClone(data.response),view114:{range:0,end:null,cursor:t+900}};
  card._hass.states['sensor.temp_f'].state='69';
  native.controlData075.source_ids=['sensor.temp_f'];
  for(const c of native.controlData075.controllers)for(const s of c.series)s.feedback_source_ids=['sensor.temp_f'];
  html=card._averageBody105('living','temperature',card._entityTrendEvidence122(native));
  assert.equal(native.model114.controls075[0].points[0].target,69.8);
  assert.ok(native.model114.max>75&&native.model114.max<85);
  assert.equal(native.model114.heldUntil,t+3600);
  native.historyEnd122=t+3600;native.view114.cursor=t+4000;
  assert.equal(card._trendSelection114(native.model114).point,null,'Target timeline extended Recorder held state');

  // Mold identities stay provenance, while the chart request has no raw source.
  const mold=structuredClone(data.response);mold.metric='mold';mold.source_ids=[];
  for(const c of mold.controllers)for(const s of c.series){
    s.metric='mold';s.basis='mold_surface_rh';s.unit='%';
    s.feedback_source_ids=['sensor.room_temp','sensor.room_rh','weather.home'];
  }
  assert.ok(card._validateControlTrend075(mold,{area_id:'living',metric:'mold',source_ids:[]}));
  assert.throws(()=>card._validateControlTrend075(data.response,{area_id:'living',metric:'temperature',source_ids:['sensor.temp_a']}));
  const invalid=structuredClone(data.response);invalid.controllers[0].series[0].points[0].until=t+40000;
  assert.throws(()=>card._validateControlTrend075(invalid,{area_id:'living',metric:'temperature',source_ids:data.response.source_ids}));
  const wrong=structuredClone(data.response);wrong.controllers[0].series[0].feedback_source_ids=['sensor.other'];
  assert.throws(()=>card._validateControlTrend075(wrong,{area_id:'living',metric:'temperature',source_ids:data.response.source_ids}));

  // Labels remain translated by the production 38-locale bundle.
  card._averageDialog105=saved;saved.view114={range:0,end:null,cursor:t+900};
  for(const [language,label] of [['en','HEM target'],['el','Στόχος HEM'],['de','HEM-Ziel']]){
    card._hass.language=language;html=render();
    assert.ok(!/undefined|NaN/.test(html));
    if(language==='en')assert.ok(html.includes(label));
    else assert.ok(!html.includes('>HEM target<')&&!html.includes('>PID demand<'),language);
  }
  for(const language of data.languages){
    card._hass.language=language;html=render();
    assert.ok(!/undefined|NaN/.test(html),language);
    if(language!=='en')assert.ok(!html.includes('>HEM target<')&&!html.includes('>PID demand<'),language);
  }
  card._hass.language='en';
  assert.equal(JSON.stringify(data.response),original,'Rendering changed persisted history evidence');

  // Actual collector -> bounded journal -> authenticated WS -> card. Mold's
  // feedback provenance is not the chart's empty native-source request.
  const retainedNow=now;now=data.backend.now;
  for(const metric of ['temperature','humidity','mold']){
    const response=data.backend[metric];
    const parsed=card._validateControlTrend075(response,{area_id:response.area_id,metric,source_ids:response.source_ids});
    const series=parsed.controllers[0].series[0],point=series.points[0];
    const actualEvidence={room:{area_id:'room',name:'Room',readings:[{metric,unit:series.unit}]},
      value:{source_ids:response.source_ids,source_count:response.source_ids.length,value:null,trend:[]}};
    const actual=card._averageDialog105={area:'room',metric,controlEnabled075:true,controlData075:parsed,
      statusControl075:'ready',node:root,width114:480,view114:{range:0,end:null,cursor:null}};
    const actualHtml=card._averageBody105('room',metric,actualEvidence);
    assert.equal(actual.model114.controls075.length,1,metric);
    assert.equal(actual.model114.points.length,0,'Stored controller measurement became a physical sample');
    assert.ok(actualHtml.includes('hem-control-sample075'),'First observation has no visible target marker');
    card._inspectTrend114();
    assert.equal(card._trendSelection114(actual.model114).time,point.until,'One-point view chose artificial padded end');
    assert.equal(node('[data-control-target075="0"]').textContent,card._format(point.target,3)+' '+series.unit);
  }
  assert.equal(data.backend.humidity.controllers[0].series[0].points[0].target,41);
  assert.equal(data.backend.mold.controllers[0].series[0].points[0].target,60);
  assert.ok(data.backend.mold.controllers[0].series[0].feedback_source_ids.length);
  now=retainedNow;card._averageDialog105=saved;

  // Only marked dashboards ask for optional targets; failure leaves PV intact.
  const baseCount=pending.length,disabled=open();
  delete card._hass.states['sensor.hem'].attributes.dashboard.control_trend_version;
  await card._loadControlTrend075(disabled);assert.equal(pending.length,baseCount);
  card._hass.states['sensor.hem'].attributes.dashboard.control_trend_version=1;
  const failed=card._loadControlTrend075(disabled);pending.at(-1).reject(Error('Unavailable'));await failed;
  assert.equal(disabled.statusControl075,'error');html=render();
  assert.ok(html.includes('data-retry-control075')&&html.includes('class="hem-avg-line105"'));
  const retry=card._loadControlTrend075(disabled,true);
  pending.at(-1).resolve({...data.response,controllers:[]});await retry;
  assert.equal(disabled.statusControl075,'empty');
  assert.ok(render().includes('HEM target · No recorded sample'));
  const stale=open(),staleTask=card._loadControlTrend075(stale);
  const fresh=open(),freshTask=card._loadControlTrend075(fresh);
  pending.at(-1).resolve(data.response);await freshTask;
  pending.at(-2).resolve({...data.response,controllers:[]});await staleTask;
  assert.equal(card._averageDialog105,fresh);assert.equal(fresh.statusControl075,'ready');
  const closed=open(),closedTask=card._loadControlTrend075(closed);card._averageDialog105=null;
  pending.at(-1).resolve(data.response);await closedTask;assert.equal(card._averageDialog105,null);
  const reconnect=open(),reconnectTask=card._loadControlTrend075(reconnect);card._hass.connection={};
  pending.at(-1).resolve(data.response);await reconnectTask;
  assert.equal(reconnect.controlData075,undefined,'Old connection response was accepted');
  const refresh=open(),refreshTask=card._loadControlTrend075(refresh);
  pending.at(-1).resolve(data.response);await refreshTask;
  refresh.view114={range:21600,end:t+3600,cursor:t+900};const pinned=structuredClone(refresh.view114);
  const count=pending.length;now+=59;card._refreshAverage105();assert.equal(pending.length,count);
  now+=2;card._refreshAverage105();assert.equal(pending.length,count+1);
  card._refreshAverage105();assert.equal(pending.length,count+1);
  pending.at(-1).resolve(data.response);await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(refresh.view114,pinned,'Control refresh moved pinned period or cursor');
  console.log('PASS: recorded target steps/ranges, exact cursor, isolated output, sources, gaps, units, transport and locales');
})().catch(error=>{console.error(error);process.exitCode=1});
"""


def browser_checks(data):
    from playwright.sync_api import expect, sync_playwright

    chrome = shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
                                             args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 590, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content("""<style>body{margin:0;background:#202020;color:#eee;font-family:Arial}
          :root{--primary-text-color:#eee;--secondary-text-color:#aaa;--card-background-color:#222;
          --secondary-background-color:#292929;--primary-color:#03a9f4;--divider-color:#444}</style>""")
        page.add_script_tag(path=str(CARD))
        page.evaluate("""data=>{
          window.data=data;window.controlRequests=[];window.deviceCalls=[];
          Date.now=()=>data.now*1000;
          window.card=document.createElement('home-environment-manager-card');document.body.append(card);
          card._config={entity:'sensor.hem'};
          card.hass={language:'en',config:{time_zone:'Europe/Berlin'},states:structuredClone(data.states),
            connection:{},localize:()=>undefined,callService:(...args)=>deviceCalls.push(args),
            callWS:message=>{
              if(message.type==='environment_manager/control_trend')
                return new Promise((resolve,reject)=>controlRequests.push({message,resolve,reject}));
              if(message.type==='environment_manager/trend')return Promise.resolve({
                area_id:'living',metric:'temperature',source_ids:['sensor.temp_a','sensor.temp_b'],
                source_count:2,trend:data.samples});
              if(message.type==='history/history_during_period')
                return Promise.resolve({[message.entity_ids[0]]:data.histories[message.entity_ids[0]]||[]});
              return Promise.resolve([]);
            }};
          card._openAverage105('living','temperature');
        }""", data)
        popup = page.locator(".hem-avg-dialog105")
        expect(popup).to_be_visible()
        expect(popup.locator('[data-control-status075="loading"]')).to_be_visible()
        page.evaluate("controlRequests[0].resolve(data.response)")
        expect(popup.locator(".hem-control-target075")).to_have_count(2)
        expect(popup.locator(".hem-control-output-chart075")).to_have_count(2)
        assert popup.locator('[data-control-field075="target"]').count() == 1
        assert popup.locator('[data-control-field075="target_low"]').count() == 1
        main = popup.locator("[data-trend-chart114]").first
        main.focus()
        main.press("End")
        expect(popup.locator('[data-control-target075="0"]')).to_have_text("24 °C")
        expect(popup.locator("[data-trend-value114]")).to_have_text("—")
        main.press("ArrowLeft")
        assert page.evaluate("card._averageDialog105.view114.cursor") == START + 3900
        main.press("Home")
        assert page.evaluate("card._averageDialog105.view114.cursor") == START
        expect(popup.locator('[data-control-target075="0"]')).to_have_text("—")
        point = page.evaluate("""()=>{
          const m=card._averageDialog105.model114,r=card._averageDialog105.node
            .querySelector('[data-trend-chart114]').getBoundingClientRect();
          return {x:r.x+(m.left+(m.right-m.left)*(data.start+1050-m.start)/(m.end-m.start))*r.width/m.width,
            y:r.y+r.height/2};
        }""")
        page.mouse.move(point["x"], point["y"])
        expect(popup.locator('[data-control-target075="0"]')).to_have_text("22 °C")
        expect(popup.locator('[data-control-demand075="0"]')).to_have_text("75%")
        assert abs(page.evaluate("card._averageDialog105.view114.cursor") - START - 1050) < 30
        assert popup.locator("[data-trend-value114]").get_attribute("data-sample-time114") == str(START + 900)
        assert popup.locator(".hem-trend-cursor114 circle").evaluate("e=>e.style.display") == "none"
        assert main.get_attribute("aria-valuetext") == popup.locator(".hem-control-output-chart075").first.get_attribute("aria-valuetext")
        for language in ("en", "el", "de"):
            page.evaluate("language=>{card._hass.language=language;card._refreshAverage105(true)}", language)
            assert "undefined" not in popup.inner_text()
            for width in (590, 375, 320):
                page.set_viewport_size({"width": width, "height": 740})
                expect(popup).to_be_visible()
                assert popup.evaluate("e=>e.scrollWidth<=e.clientWidth+1"), (language, width)
                bounds = popup.bounding_box()
                assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width + 1
        page.evaluate("""()=>{
          card._hass.language='en';card._loadControlTrend075(card._averageDialog105,true);
          controlRequests.at(-1).reject(Error('temporary'));
        }""")
        expect(popup.locator('[data-retry-control075]')).to_be_visible()
        assert main.count() == 1
        popup.locator('[data-retry-control075]').click()
        page.evaluate("controlRequests.at(-1).resolve(data.response)")
        expect(popup.locator('[data-retry-control075]')).to_have_count(0)
        popup.locator("[data-close-avg105]").click()
        expect(popup).to_have_count(0)
        assert page.evaluate("deviceCalls") == []
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    data = fixture()
    subprocess.run(["node", "-e", NODE, str(CARD)], input=json.dumps(data), text=True, check=True)
    if "--logic-only" not in sys.argv:
        browser_checks(data)
        print("PASS: target/output popup pointer, keyboard, retry, localization and narrow-screen geometry")
