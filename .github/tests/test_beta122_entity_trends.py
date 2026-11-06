"""Recorded entity history shares the interactive room-average trend window.

--logic-only exercises the production normalizer, evidence adapter and chart
model in Node. The default also drives real Chromium pointer/keyboard input,
asynchronous HA history replies and fresh-card recovery. Only the authenticated
HA transport is a fixture; no physical service is called. Persisted room-mean
storage/restart behavior is checked separately by the backend regression suite.
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


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
BASE = runpy.run_path(str(ROOT / ".github/tests/test_beta114_interactive_trends.py"))
START = BASE["START"]
END = START + 96 * 3600
NOW = END + 300


def fixture():
    states = BASE["fixture"]()
    room = states["sensor.hem"]["attributes"]["dashboard"]["rooms"][0]
    for entity, unit, value, device_class in (
        ("sensor.temp_a", "°C", "21.456", "temperature"),
        ("sensor.temp_b", "°C", "21.0", "temperature"),
        ("sensor.humidity", "%", "50.2", "humidity"),
    ):
        states[entity].update(entity_id=entity, state=value,
                              last_changed="2026-11-05T00:05:00+00:00",
                              last_updated="2026-11-05T00:05:00+00:00")
        states[entity]["attributes"].update(
            unit_of_measurement=unit, device_class=device_class,
            state_class="measurement")
    states["sensor.temp_f"] = {
        "entity_id": "sensor.temp_f", "state": "70.123",
        "attributes": {"friendly_name": "Fahrenheit probe", "unit_of_measurement": "°F",
                       "device_class": "temperature", "state_class": "measurement"},
    }
    room["readings"].append({"metric": "temperature", "value": 70.123,
                             "unit": "°F", "available": True,
                             "name": "Fahrenheit probe", "entity_id": "sensor.temp_f"})
    states["binary_sensor.window"] = {
        "entity_id": "binary_sensor.window", "state": "off",
        "attributes": {"friendly_name": "Window", "device_class": "window"},
    }
    room["windows"] = [{"entity_id": "binary_sensor.window", "name": "Window", "state": "off"}]
    states["sensor.unselected"] = {"state": "99", "attributes": {"unit_of_measurement": "%"}}
    humidity = []
    for index in range(97):
        if 37 <= index <= 45:
            if index == 37:
                humidity.append({"s": "unavailable", "lu": START + index * 3600,
                                 "a": {"unit_of_measurement": "%"}})
            continue
        humidity.append({"s": str(round(50.123 + (index % 12) / 10, 3)),
                         "lu": START + index * 3600,
                         "a": {"unit_of_measurement": "%", "state_class": "measurement"}})
    histories = {
        "sensor.humidity": humidity,
        "sensor.temp_a": [{"s": "21.125", "lu": START, "a": {"unit_of_measurement": "°C"}},
                          {"s": "21.875", "lu": END, "a": {"unit_of_measurement": "°C"}}],
    }
    return {"states": states, "histories": histories, "start": START, "end": END, "now": NOW}


NODE_CHECKS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const data=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={innerWidth:590};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');
const card=Object.create(Card.prototype);
card._config={entity:'sensor.hem'};
card._hass={language:'en',config:{time_zone:'Europe/Berlin'},states:data.states,
  localize:()=>undefined,callService:()=>{throw Error('Entity trend called a physical service')}};
const id='sensor.temp_f',t=data.start;
const rows=[
  {s:'71.25',lu:t+600,a:{unit_of_measurement:'°F'}},
  {s:'70.125',lu:t,a:{unit_of_measurement:'°F'}},
  {s:'71.5',lu:t+600,a:{unit_of_measurement:'°F'}},
  {s:'unavailable',lu:t+900,a:{unit_of_measurement:'°F'}},
  {s:'0',lu:t+1200,a:{unit_of_measurement:'°F'}},
  {s:'-2.345',lu:t+1500,a:{unit_of_measurement:'°F'}},
  {s:'',lu:t+1800,a:{unit_of_measurement:'°F'}},
  {s:'   ',lu:t+2100,a:{unit_of_measurement:'°F'}},
  {s:false,lu:t+2400,a:{unit_of_measurement:'°F'}},
  {s:null,lu:t+2700,a:{unit_of_measurement:'°F'}},
  {s:'Infinity',lu:t+3000,a:{unit_of_measurement:'°F'}},
  {s:'20.1',lu:t+3300,a:{unit_of_measurement:'°C'}},
  {s:'72',lu:t+3600,a:{unit_of_measurement:'°F',restored:true}},
  {s:' 72.125 ',lu:t+3900,a:{unit_of_measurement:'°F'}},
  {s:'99',lu:t-1,a:{unit_of_measurement:'°F'}},
  {s:'99',lu:t+4001,a:{unit_of_measurement:'°F'}},
  {s:'99',lu:-1},{s:'99',lu:'not-a-time'},
];
const original=JSON.stringify(rows);
const parsed=card._entityHistoryPoints122({[id]:rows,'sensor.other':[{s:'999',lu:t}]},id,t,t+4000,'°F');
const numeric=parsed.filter(p=>Number.isFinite(p.v));
assert.deepEqual(numeric.map(p=>[p.t,p.v]),[
  [t,70.125],[t+600,71.5],[t+1200,0],[t+1500,-2.345],[t+3900,72.125],
]);
assert.ok(parsed.some(p=>p.v===null||p.break_before),'Unknown, restored and changed-unit evidence must remain gaps');
assert.equal(JSON.stringify(rows),original,'Normalization changed Recorder evidence');
assert.deepEqual(card._entityHistoryPoints122({'sensor.other':rows},id,t,t+4000,'°F'),[]);
assert.ok(parsed.every(p=>p.t>=t&&p.t<=t+4000));
assert.ok(parsed.every((p,i)=>!i||p.t>parsed[i-1].t),'History must be ordered and deduplicated');

// A week at one-minute cadence is larger than the plotting cap. Downsample
// across the WHOLE interval and retain real source samples, never averages.
const dense=Array.from({length:10081},(_,i)=>({s:String(60.123+(i%17)/100),lu:t+i*60,
  a:{unit_of_measurement:'°F'}}));
dense[3800]={s:'unknown',lu:t+3800*60,a:{unit_of_measurement:'°F'}};
const bounded=card._entityHistoryPoints122({[id]:dense},id,t,t+604800,'°F');
assert.ok(bounded.length<=1000&&bounded.length>10);
assert.equal(bounded[0].t,t,'Do not discard the beginning of the seven-day request');
assert.equal(bounded.at(-1).t,t+604800);
const actual=new Map(dense.filter(p=>Number.isFinite(Number(p.s))).map(p=>[p.lu,Number(p.s)]));
for(const p of bounded.filter(p=>Number.isFinite(p.v)))assert.equal(p.v,actual.get(p.t));
assert.ok(bounded.some(p=>p.v===null||p.break_before),'Sampling erased a source outage');

const history=Array.from({length:97},(_,i)=>({t:t+i*3600,v:70.123+(i%12)/10}));
const saved=card._averageDialog105={entity122:id,history122:history,status122:'ready',
  unit122:'°F',area:'living',metric:'temperature',width114:480};
let evidence=card._entityTrendEvidence122(saved);
assert.equal(evidence.entity_id,id);
assert.equal(evidence.unit,'°F');
assert.equal(evidence.value.source_count,1);
assert.deepEqual(evidence.value.source_ids,[id]);
assert.deepEqual(evidence.value.trend,history,'The current HA reading must not fabricate a history point');
const before=JSON.stringify(history);
let html=card._averageBody105(saved.area,saved.metric,evidence);
let model=saved.model114;
assert.equal(model.unit,'°F','Entity temperature retains its recorded native unit');
assert.equal(saved.view114.range,86400);
assert.equal(model.end-model.start,86400);
assert.ok(html.includes('data-open-entity122')&&html.includes('Fahrenheit probe'));
for(const range of [21600,86400,604800,0])assert.ok(html.includes('data-trend-range114="'+range+'"'));
assert.ok(!/NaN|Infinity/.test(html));
card._refreshAverage105=()=>card._averageBody105(saved.area,saved.metric,card._entityTrendEvidence122(saved));
card._moveTrend114('older');
assert.equal(saved.model114.end,history.at(-1).t-86400);
const held=saved.model114.end;
history.push({t:history.at(-1).t+3600,v:74.987});
card._refreshAverage105();
assert.equal(saved.model114.end,held,'New history must not move an older inspected window');
card._moveTrend114('latest');
assert.equal(saved.view114.end,null);
assert.equal(saved.model114.end,history.at(-1).t);
saved.node={querySelector:()=>null};
card._inspectTrend114(history.at(-2).t);
assert.equal(saved.view114.cursor,history.at(-2).t);
assert.equal(card._trendSelection114(saved.model114).point.v,history.at(-2).v);
card._hass.states[id]={...card._hass.states[id],state:'unavailable'};
evidence=card._entityTrendEvidence122(saved);
assert.equal(evidence.value.value,null);
assert.equal(evidence.value.trend.length,98,'Unavailable current feedback erased recorded history');
assert.equal(JSON.stringify(history.slice(0,-1)),before,'Chart inspection mutated recorded samples');
for(const language of ['en','de','el']){
  card._hass.language=language;
  html=card._averageBody105(saved.area,saved.metric,evidence);
  assert.ok(!/NaN|Infinity|undefined/.test(html));
  assert.ok(html.includes('data-open-entity122'));
}
// Explicit source outages stay missing even when shorter than the plotting
// cadence; neither adjacent real sample may stand in for the interior.
const shortGap={...saved,history122:[{t:t+900,v:20},{t:t+960,v:21,break_before:true}],
  view114:{range:0,end:null,cursor:t+930}};
card._averageDialog105=shortGap;
card._averageBody105(shortGap.area,shortGap.metric,card._entityTrendEvidence122(shortGap));
assert.deepEqual(shortGap.model114.gaps,[[t+900,t+960]]);
assert.equal(card._trendSelection114(shortGap.model114).point,null,'Short outage was replaced by a nearby sample');
for(const [stamp,value] of [[t+900,20],[t+960,21]]){
  shortGap.view114.cursor=stamp;
  assert.equal(card._trendSelection114(shortGap.model114).point.v,value);
}
// Leading unavailable evidence is part of All. Centering the sole valid
// sample around the first (missing) timestamp would hide the only point.
const oneAfterGap={...saved,history122:[{t,v:null},{t:t+3600,v:20}],
  view114:{range:0,end:null,cursor:t+3600}};
card._averageDialog105=oneAfterGap;
html=card._averageBody105(oneAfterGap.area,oneAfterGap.metric,card._entityTrendEvidence122(oneAfterGap));
assert.equal(oneAfterGap.model114.start,t);
assert.equal(oneAfterGap.model114.end,t+3600);
assert.deepEqual(oneAfterGap.model114.visible,[{t:t+3600,v:20}]);
assert.equal(card._trendSelection114(oneAfterGap.model114).point.v,20);
assert.ok(html.includes('data-trend-chart114')&&html.includes('class="hem-trend-sample114"'));
oneAfterGap.view114.cursor=t+1800;
assert.equal(card._trendSelection114(oneAfterGap.model114).point,null);
card._averageDialog105=saved;
console.log('BETA122_ENTITY_HISTORY_REAL_SAMPLES_UNITS_GAPS_BOUNDS_SHARED_CHART=PASS');
(async()=>{
  Date.now=()=>data.now*1000;
  card._hass.language='en';card._hass.connection={};
  const pending=[];
  card._hass.callWS=message=>new Promise((resolve,reject)=>pending.push({message,resolve,reject}));
  // Only DOM painting is isolated here; use the production async request,
  // identity checks, normalization and loading/error/empty transitions.
  card._refreshAverage105=function(){
    const current=this._averageDialog105;
    if(current)this._averageBody105(current.area,current.metric,this._entityTrendEvidence122(current));
  };
  const open=(entityId)=>{
    const active={entity122:entityId,history122:[],status122:'loading',
      area:'living',metric:entityId==='sensor.humidity'?'humidity':'temperature',
      unit122:card._hass.states[entityId].attributes.unit_of_measurement,
      connection122:card._hass.connection,dashboard122:'sensor.hem',width114:480};
    card._averageDialog105=active;
    return {active,request:card._loadEntityTrend122(active)};
  };
  const old=open('sensor.temp_a'),fresh=open('sensor.humidity');
  assert.equal(old.active.status122,'loading');
  assert.equal(fresh.active.status122,'loading');
  const message=pending[1].message;
  assert.equal(message.type,'history/history_during_period');
  assert.deepEqual(message.entity_ids,['sensor.humidity']);
  assert.equal(message.include_start_time_state,false,'Recorder must not create a carry-in sample at query start');
  assert.equal(message.significant_changes_only,false);
  assert.equal(message.minimal_response,false);
  assert.equal(message.no_attributes,false);
  assert.equal((Date.parse(message.end_time)-Date.parse(message.start_time))/1000,604800);
  pending[1].resolve({'sensor.humidity':data.histories['sensor.humidity']});
  await fresh.request;
  assert.equal(fresh.active.status122,'ready');
  assert.equal(fresh.active.history122[0].t,data.start);
  const historyBefore=JSON.stringify(fresh.active.history122);
  pending[0].resolve({'sensor.temp_a':data.histories['sensor.temp_a']});
  await old.request;
  assert.equal(card._averageDialog105,fresh.active);
  assert.equal(JSON.stringify(fresh.active.history122),historyBefore);
  const closed=open('sensor.temp_a');
  card._averageDialog105=null;
  pending[2].resolve({'sensor.temp_a':data.histories['sensor.temp_a']});
  await closed.request;
  assert.equal(card._averageDialog105,null,'A closed request resurrected its popup');
  const switched=open('sensor.temp_a');
  card._hass={...card._hass,connection:{}};
  pending[3].resolve({'sensor.temp_a':data.histories['sensor.temp_a']});
  await switched.request;
  assert.deepEqual(switched.active.history122,[],'Reply from an old HA connection was accepted');
  const failed=open('sensor.humidity');
  pending[4].reject(new Error('Recorder unavailable'));
  await failed.request;
  assert.equal(failed.active.status122,'error');
  const retry=card._loadEntityTrend122(failed.active);
  assert.equal(failed.active.status122,'loading');
  pending[5].resolve({});await retry;
  assert.equal(failed.active.status122,'empty');
  assert.deepEqual(failed.active.history122,[],'An empty Recorder response fabricated a current sample');
  // Two requests for the SAME popup also need a generation guard.
  const firstRetry=card._loadEntityTrend122(failed.active);
  const newerRetry=card._loadEntityTrend122(failed.active);
  pending[7].resolve({'sensor.humidity':data.histories['sensor.humidity']});await newerRetry;
  pending[6].resolve({});await firstRetry;
  assert.equal(failed.active.status122,'ready');
  assert.equal(failed.active.history122[0].t,data.start);
  const pinned={range:21600,end:data.end-21600,cursor:data.end-21600-3600};
  failed.active.view114={...pinned};
  const existing=JSON.stringify(failed.active.history122);
  const refresh=card._loadEntityTrend122(failed.active,true);
  assert.equal(JSON.stringify(failed.active.history122),existing,'Refreshing erased the visible recorded history');
  pending[8].resolve({'sensor.humidity':[
    ...data.histories['sensor.humidity'],{s:'52.456',lu:data.now,a:{unit_of_measurement:'%'}}]});
  await refresh;
  assert.deepEqual(failed.active.view114,pinned,'A background history refresh reset the inspected period/cursor');
  assert.equal(failed.active.model114.last,data.now);
  assert.equal(failed.active.model114.end,pinned.end);
  const restarted=Object.create(Card.prototype);
  restarted._config={entity:'sensor.hem'};
  restarted._hass={...card._hass,connection:{},states:structuredClone(data.states)};
  restarted._hass.states['sensor.humidity'].state='unavailable';
  restarted._hass.states['sensor.humidity'].last_changed=new Date((data.now+600)*1000).toISOString();
  let fetched=0;
  restarted._hass.callWS=async request=>{
    fetched++;assert.deepEqual(request.entity_ids,['sensor.humidity']);
    return {'sensor.humidity':structuredClone(data.histories['sensor.humidity'])};
  };
  restarted._refreshAverage105=card._refreshAverage105;
  const active=restarted._averageDialog105={entity122:'sensor.humidity',unit122:'%',
    area:'living',metric:'humidity',history122:[],status122:'loading',width114:480,
    connection122:restarted._hass.connection,dashboard122:'sensor.hem'};
  await restarted._loadEntityTrend122(active);
  assert.equal(fetched,1,'A new card must fetch actual Recorder history');
  assert.equal(active.status122,'ready');
  assert.equal(active.model114.first,data.start);
  assert.equal(active.model114.last,data.end);
  assert.equal(restarted._entityTrendEvidence122(active).value.value,null);
  // Exercise the actual refresh gate after an empty response. Only DOM
  // painting is inert; request timing, native evidence and navigation are real.
  let now=data.now;
  Date.now=()=>now*1000;
  global.document={createElement:()=>({content:{firstElementChild:null}})};
  const recovering=Object.create(Card.prototype),recoveryRequests=[];
  recovering._config={entity:'sensor.hem'};
  recovering._hass={...card._hass,connection:{},states:structuredClone(data.states),
    callWS:message=>new Promise(resolve=>recoveryRequests.push({message,resolve}))};
  const empty=recovering._averageDialog105={entity122:'sensor.humidity',unit122:'%',
    area:'living',metric:'humidity',history122:[],status122:'loading',width114:480,
    connection122:recovering._hass.connection,dashboard122:'sensor.hem',
    node:{scrollTop:0,setAttribute(){},querySelector:()=>null}};
  const initial=recovering._loadEntityTrend122(empty);
  recoveryRequests[0].resolve({});await initial;
  assert.equal(empty.status122,'empty');
  assert.ok(recovering._averageBody105(empty.area,empty.metric,recovering._entityTrendEvidence122(empty))
    .includes('data-retry-history122'),'Empty history must expose Try again');
  const selectedRange={range:21600,end:null,cursor:null};
  empty.view114={...selectedRange};
  now+=59;
  recovering._hass.states['sensor.humidity'].last_updated=new Date(now*1000).toISOString();
  recovering._refreshAverage105();
  assert.equal(recoveryRequests.length,1,'Empty history bypassed the refresh throttle');
  now+=2;
  recovering._refreshAverage105();
  assert.equal(recoveryRequests.length,2,'New native evidence did not reload empty history');
  assert.deepEqual(empty.view114,selectedRange);
  recovering._refreshAverage105();
  assert.equal(recoveryRequests.length,2,'An in-flight refresh was duplicated');
  recoveryRequests[1].resolve({'sensor.humidity':data.histories['sensor.humidity']});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(empty.status122,'ready');
  assert.deepEqual(empty.view114,selectedRange,'Empty-history recovery reset the selected navigation');
  assert.equal(empty.model114.visible.length,7);
  now+=61;
  recovering._refreshAverage105();
  assert.equal(recoveryRequests.length,2,'Unchanged native evidence repeatedly fetched history');
  delete global.document;
  console.log('BETA122_ENTITY_HISTORY_ASYNC_IDENTITY_LOADING_RETRY_FRESH_CLIENT=PASS');
})().catch(error=>{console.error(error);process.exitCode=1});
"""


def browser_checks(data):
    from playwright.sync_api import sync_playwright

    chrome = shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome, "Chromium required"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, headless=True,
                                   args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 590, "height": 900}, has_touch=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content("""<!doctype html><html><head><style>
          *{box-sizing:border-box}body{margin:0;background:#111;color:#ddd;font-family:Arial}
          :root{--primary-text-color:#e9edf4;--secondary-text-color:#a5b2c4;
          --card-background-color:#202830;--secondary-background-color:#28323d;
          --divider-color:#3b4654;--primary-color:#25b5df}</style></head><body></body></html>""")
        page.add_script_tag(path=str(CARD))
        page.evaluate("""data=>{
          window.fixture=data;window.historyRequests=[];window.info=[];window.serviceCalls=[];
          Date.now=()=>fixture.now*1000;
          window.makeCard=states=>{
            const card=document.createElement('home-environment-manager-card');
            document.body.append(card);
            card.addEventListener('hass-more-info',e=>info.push(e.detail.entityId));
            card._config={entity:'sensor.hem'};
            card._hass={language:'en',config:{time_zone:'Europe/Berlin'},states,
              connection:{},localize:()=>undefined,
              callService:(...args)=>{serviceCalls.push(args);return Promise.resolve()},
              callWS:message=>{
                if(message.type!=='history/history_during_period')return Promise.resolve([]);
                return new Promise((resolve,reject)=>historyRequests.push({message,resolve,reject}));
              }};
            card._renderContent(true);return card;
          };
          window.card=makeCard(structuredClone(data.states));
        }""", data)

        def requests():
            return page.evaluate("historyRequests.length")

        def resolve(index, entity="sensor.humidity", rows=None):
            page.evaluate("""({index,entity,rows})=>historyRequests[index].resolve({
              [entity]:rows??fixture.histories[entity]})""",
                          {"index": index, "entity": entity, "rows": rows})

        def open_entity(entity="sensor.humidity"):
            previous = requests()
            page.evaluate("id=>card._openEntityTrend122(id)", entity)
            page.wait_for_function("count=>historyRequests.length===count+1", arg=previous)
            return previous

        trigger = page.locator('[data-room-fold87="living"] [data-hem-source105="sensor.humidity"]').first
        trigger.click()
        popup = page.locator(".hem-avg-dialog105")
        popup.wait_for(state="visible")
        page.wait_for_function("historyRequests.length===1")
        assert popup.locator('[data-entity-history-status122="loading"]').is_visible()
        assert popup.locator("[data-open-entity122]").is_visible()
        assert page.evaluate("info") == [], "A numeric badge should open its trend first"
        request = page.evaluate("historyRequests[0].message")
        assert request["type"] == "history/history_during_period"
        assert request["entity_ids"] == ["sensor.humidity"]
        assert request["include_start_time_state"] is False
        assert request["significant_changes_only"] is False
        assert request["minimal_response"] is False
        assert request["no_attributes"] is False
        period = page.evaluate("(Date.parse(historyRequests[0].message.end_time)-Date.parse(historyRequests[0].message.start_time))/1000")
        assert period == 604800
        resolve(0)
        popup.locator('[data-entity-history-status122="ready"]').wait_for(state="attached")
        chart = popup.locator("[data-trend-chart114]")
        assert chart.is_visible() and chart.get_attribute("role") == "slider"
        assert popup.locator('[data-trend-range114="86400"]').get_attribute("aria-pressed") == "true"
        assert popup.locator("[data-trend-value114]").inner_text() == "50.123"
        assert page.evaluate("card._averageDialog105.model114.last") == END
        assert "50.2" in popup.locator(".hem-trend-current114").inner_text()

        for range_seconds in (21600, 604800, 0, 86400, 21600):
            popup.locator(f'[data-trend-range114="{range_seconds}"]').click()
            assert popup.locator(f'[data-trend-range114="{range_seconds}"]').get_attribute("aria-pressed") == "true"
        popup.locator('[data-trend-move114="older"]').click()
        model = page.evaluate("card._averageDialog105.model114")
        assert model["end"] == END - 21600
        assert popup.locator('[data-trend-move114="newer"]').is_enabled()

        def point(index, *, down=False):
            selected = page.evaluate("i=>card._averageDialog105.model114.visible[i]", index)
            coord = page.evaluate("""t=>{
              const s=card._averageDialog105,m=s.model114;
              const r=s.node.querySelector('[data-trend-chart114]').getBoundingClientRect();
              return {x:r.x+(m.left+(m.right-m.left)*(t-m.start)/(m.end-m.start))*r.width/m.width,
                      y:r.y+r.height*.5};
            }""", selected["t"])
            page.mouse.move(coord["x"], coord["y"])
            if down:
                page.mouse.down()
            assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == selected["t"]
            assert float(popup.locator("[data-trend-value114]").inner_text()) == selected["v"]
            return selected, coord

        point(2)
        chart.focus()
        chart.press("Home")
        first = page.evaluate("card._averageDialog105.model114.visible[0].t")
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == first
        chart.press("ArrowRight")
        second = page.evaluate("card._averageDialog105.model114.visible[1].t")
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == second
        chart.press("End")
        chart.press("PageUp")
        assert page.evaluate("card._averageDialog105.model114.end") == model["end"] - 21600
        chart.press("PageDown")
        assert page.evaluate("card._averageDialog105.model114.end") == model["end"]

        def update_current(value):
            page.evaluate("""value=>{
              fixture.now+=1;
              const states=structuredClone(card._hass.states);
              states['sensor.humidity'].state=value;
              states['sensor.humidity'].last_updated=new Date(fixture.now*1000).toISOString();
              card.hass={...card._hass,states};card._renderContent(true);
            }""", value)

        selected, _ = point(2)
        chart.focus()
        page.evaluate("window.retainedChart=card._averageDialog105.node.querySelector('[data-trend-chart114]')")
        update_current("51.234")
        assert page.evaluate("retainedChart===card._averageDialog105.node.querySelector('[data-trend-chart114]')")
        assert chart.evaluate("e=>e===e.getRootNode().activeElement")
        assert page.evaluate("card._averageDialog105.model114.end") == model["end"]
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == selected["t"]
        assert "51.234" in popup.locator(".hem-trend-current114").inner_text()
        assert page.evaluate("card._averageDialog105.model114.last") == END, "A live reading fabricated historical data"
        selected, _ = point(3, down=True)
        update_current("51.987")
        assert page.evaluate("card._averageDialog105.pending114")
        assert page.evaluate("retainedChart===card._averageDialog105.node.querySelector('[data-trend-chart114]')")
        page.mouse.up()
        assert not page.evaluate("card._averageDialog105.pending114")
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == selected["t"]
        selected, coord = point(1)
        page.touchscreen.tap(coord["x"], coord["y"])
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == selected["t"]

        # Qualified native updates can refresh Recorder after its throttle,
        # without replacing the chart or moving an inspected period/cursor.
        before_refresh = requests()
        chart.focus()
        pinned = page.evaluate("structuredClone(card._averageDialog105.view114)")
        page.evaluate("fixture.now+=61")
        update_current("52.456")
        page.wait_for_function("count=>historyRequests.length===count+1", arg=before_refresh)
        assert page.evaluate("retainedChart===card._averageDialog105.node.querySelector('[data-trend-chart114]')")
        assert chart.is_visible()
        recorded_end = page.evaluate("""()=>{
          fixture.histories['sensor.humidity'].push({s:'52.456',lu:fixture.now,a:{unit_of_measurement:'%'}});
          return fixture.now;
        }""")
        resolve(before_refresh)
        page.wait_for_function("end=>card._averageDialog105.model114.last===end", arg=recorded_end)
        assert page.evaluate("card._averageDialog105.view114") == pinned
        assert page.evaluate("retainedChart===card._averageDialog105.node.querySelector('[data-trend-chart114]')")
        assert chart.evaluate("e=>e===e.getRootNode().activeElement")
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == selected["t"]

        # Loading and steady data use the same popup; explicit navigation is
        # separate from the trend trigger and dispatches exactly one event.
        popup.locator("[data-open-entity122]").click()
        assert page.evaluate("info") == ["sensor.humidity"]
        assert popup.count() == 0

        # Average and contributor history may share the same area/metric.
        # Returning to the average replaces the entity popup rather than
        # treating it as a second press of the already-open average.
        average_trigger = page.locator(
            '[data-room-fold87="living"] [data-hem-average105="temperature"]').first
        average_trigger.click()
        popup.wait_for(state="visible")
        mean_points = page.evaluate("structuredClone(card._averageDialog105.model114.points)")
        contributor_request = requests()
        popup.locator('[data-hem-source105="sensor.temp_a"]').click()
        page.wait_for_function("count=>historyRequests.length===count+1", arg=contributor_request)
        assert page.evaluate("card._averageDialog105.entity122") == "sensor.temp_a"
        assert page.evaluate("[card._averageDialog105.area,card._averageDialog105.metric]") == ["living", "temperature"]
        # The manual popover can cover this summary button at this viewport.
        # Focus the real button and use native keyboard activation, keeping
        # its normal click binding without clicking through the popup.
        average_trigger.focus()
        assert average_trigger.evaluate("el=>el.getRootNode().activeElement===el")
        average_trigger.press("Enter")
        assert popup.is_visible(), "A contributor popup was mistaken for the already-open average"
        assert page.evaluate("!card._averageDialog105.entity122")
        assert page.evaluate("card._averageDialog105.sources") == "sensor.temp_a|sensor.temp_b"
        assert page.evaluate("card._averageDialog105.model114.points") == mean_points
        page.evaluate("window.retainedAveragePopup=card._averageDialog105.node")
        resolve(contributor_request, "sensor.temp_a")
        page.wait_for_timeout(20)
        assert page.evaluate("card._averageDialog105.node===retainedAveragePopup")
        assert page.evaluate("!card._averageDialog105.entity122")
        assert page.evaluate("card._averageDialog105.model114.points") == mean_points
        popup.locator("[data-close-avg105]").click()

        # Reverse-resolved replies cannot replace another entity's popup.
        older = open_entity("sensor.temp_a")
        newer = open_entity("sensor.humidity")
        resolve(newer)
        popup.locator('[data-entity-history-status122="ready"]').wait_for(state="attached")
        page.evaluate("window.retainedPopup=card._averageDialog105.node")
        resolve(older, "sensor.temp_a")
        page.wait_for_timeout(20)
        assert page.evaluate("card._averageDialog105.entity122") == "sensor.humidity"
        assert page.evaluate("card._averageDialog105.node===retainedPopup")
        assert page.evaluate("card._averageDialog105.model114.points[0].v") == 50.123
        chart.focus()
        chart.press("Escape")
        pending = open_entity("sensor.temp_a")
        popup.locator("[data-close-avg105]").click()
        resolve(pending, "sensor.temp_a")
        page.wait_for_timeout(20)
        assert popup.count() == 0, "A late reply reopened a closed trend"

        # A fresh card/HA connection requests Recorder again and receives
        # samples older than this browser session and the new HA state.
        pending = open_entity("sensor.temp_a")
        page.evaluate("""()=>{
          const states=structuredClone(card._hass.states);
          states['sensor.humidity'].state='unavailable';
          states['sensor.humidity'].last_changed=new Date((fixture.now+600)*1000).toISOString();
          card.remove();fixture.now+=600;window.card=makeCard(states);
        }""")
        assert page.evaluate("!card._averageDialog105")
        fresh = open_entity()
        resolve(fresh)
        popup.locator('[data-entity-history-status122="ready"]').wait_for(state="attached")
        resolve(pending, "sensor.temp_a")
        page.wait_for_timeout(20)
        assert page.evaluate("card._averageDialog105.entity122") == "sensor.humidity"
        assert page.evaluate("card._averageDialog105.model114.first") == START
        assert page.evaluate("card._averageDialog105.model114.last") == recorded_end
        assert "Unavailable" in popup.locator(".hem-trend-current114").inner_text()
        assert chart.is_visible(), "Current unavailability must not remove recorded history"

        screenshot_dir = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
        if screenshot_dir:
            Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
        for width, language in ((590, "en"), (390, "el"), (320, "de")):
            page.set_viewport_size({"width": width, "height": 900})
            page.evaluate("language=>{card._hass={...card._hass,language};card._refreshAverage105(true)}", language)
            page.wait_for_timeout(40)
            bounds = popup.bounding_box()
            assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width + 1
            assert popup.evaluate("e=>e.scrollWidth<=e.clientWidth+1"), "Entity chart overflowed horizontally"
            assert popup.locator("[data-open-entity122]").is_visible()
            assert chart.is_visible()
            if screenshot_dir:
                page.screenshot(path=str(Path(screenshot_dir) / f"beta122-entity-trend-{width}-{language}.png"))

        popup.locator("[data-close-avg105]").click()
        failed = open_entity()
        page.evaluate("index=>historyRequests[index].reject(new Error('Recorder unavailable'))", failed)
        popup.locator('[data-entity-history-status122="error"]').wait_for()
        assert popup.locator("[data-trend-chart114]").count() == 0
        previous = requests()
        popup.locator("[data-retry-history122]").click()
        page.wait_for_function("count=>historyRequests.length===count+1", arg=previous)
        assert popup.locator('[data-entity-history-status122="loading"]').is_visible()
        resolve(previous, rows=[])
        popup.locator('[data-entity-history-status122="empty"]').wait_for()
        assert popup.locator("[data-trend-chart114]").count() == 0
        assert popup.locator("[data-open-entity122]").is_visible()
        popup.locator("[data-open-entity122]").click()
        assert page.evaluate("info") == ["sensor.humidity", "sensor.humidity"]
        previous = requests()
        page.evaluate("card._openEntityTrend122('sensor.unselected')")
        assert requests() == previous and popup.count() == 0
        assert page.evaluate("serviceCalls") == []
        assert not errors, errors
        browser.close()
    print("BETA122_ENTITY_TREND_INPUT_STABILITY_ASYNC_RESTART_NAVIGATION_STATES=PASS")


if __name__ == "__main__":
    data = fixture()
    subprocess.run(["node", "-e", NODE_CHECKS, str(CARD)],
                   input=json.dumps(data), text=True, check=True)
    if "--logic-only" not in sys.argv:
        browser_checks(deepcopy(data))
