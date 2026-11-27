"""Historical targets and controller output share one measured trend graph.

Run production card code in Node; the default also exercises Chromium pointer,
keyboard, retry and 320px geometry. All transport and HA states are fixtures.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/home-environment-manager-card.js"
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
    # Capture one slow and two fast sensors through the same collector used
    # by HA. Change profile while the slow contributor is absent, then restart.
    capture.setUp()
    try:
        group = ["sensor.temp", "sensor.second", "sensor.hourly"]
        capture.settings["room_sources"]["room"]["temperature"] = group
        capture.native("climate.native", "heat", hvac_action="idle")
        clock = source["CLOCK"]
        start = clock.now
        for minute in range(126):
            clock.now = start + minute * 60
            for entity in group[:2]:
                capture.sensor(entity, 20., "temperature", "°C")
            if minute % 60 == 0:
                capture.sensor(group[-1], 20., "temperature", "°C")
            if minute == 35:
                capture.cfg["preset"] = "sleep"
            if minute == 114:
                journal = capture.manager._environment_history
                capture.manager._environment_history = journal.restore(journal.snapshot(), now=clock.now)
            capture.capture()
        hourly_history = capture.manager._environment_history
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
    transport.manager._environment_history = hourly_history
    transport.report["measurement_evidence"]["temperature"] = {"source_ids": group, "source_count": 3}
    with patch.object(boundary["api"].time, "time", return_value=clock.now):
        boundary["api"].websocket_control_trend(transport.hass, transport.connection, {
            "id": 2, "type": "environment_manager/control_trend", "entity_id": "sensor.hem",
            "area_id": "room", "metric": "temperature", "source_ids": group,
        })
    assert not transport.errors, transport.errors
    result["hourly"] = transport.results[-1]
    result["hourly_start"] = start
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
    sparse = deepcopy(response)
    for controller in sparse["controllers"]:
        row = controller["series"][0]
        base = row["points"][0]
        row["points"] = []
        for index, hour in enumerate((0, 6, 12, 18, 24)):
            stamp = START - 86400 + hour * 3600
            goal = 19 if index < 2 else 21
            scalar = controller["controller_id"] == "radiator"
            row["points"].append({**base, "t": stamp, "until": stamp + (0 if index % 2 else 60),
                                  "break_before": index > 0, "target_break_before": index == 4,
                                  "target": goal if scalar else None,
                                  "target_low": None if scalar else goal, "target_high": None if scalar else goal + 4})
    data.update(response=response, sparse=sparse, now=START + 6000, samples=samples,
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
    setAttribute(k,v){this.attributes[k]=v},removeAttribute(k){delete this.attributes[k]},
    toggleAttribute(k,on){if(on)this.attributes[k]='';else delete this.attributes[k]}});
  return nodes.get(key);
};
const chart=node('chart'),cursor=node('cursor'),dot=node('dot');
cursor.querySelector=()=>dot;
const handlers=new Map();
const root={scrollTop:0,setAttribute(){},addEventListener(type,handler){
  if(!handlers.has(type))handlers.set(type,[]);handlers.get(type).push(handler);
},querySelector(selector){
  if(['.hem-avg-body105','.hem-avg-head105>strong','[data-close-avg105]'].includes(selector))return null;
  if(selector==='.hem-trend-tag')return null; // SVG text geometry is checked in Chromium.
  const pick=selector.match(/^\[data-trend-pick="(\d+)-(\w+)"\]$/);
  if(pick){
    const field={demand_percent:'demand',output_percent:'output'}[pick[2]]||pick[2];
    const button=node(selector);
    button.querySelector=tag=>tag==='b'?node('[data-control-'+field+'075="'+pick[1]+'"]'):null;
    return button;
  }
  if(selector.startsWith('[data-trend-pick='))return null;
  if(selector==='.hem-trend-cursor114')return cursor;
  if(selector==='[data-trend-chart114]')return chart;
  return node(selector);
},querySelectorAll(selector){return selector==='[data-trend-chart114]'?[chart]:[]}};
const open=()=>{
  const saved=card._averageDialog105={area:'living',metric:'temperature',sources:'sensor.temp_a|sensor.temp_b',
    width114:480,view114:{range:0,end:null,cursor:null},node:root};
  return saved;
};
const evidence=()=>card._evidence105('living','temperature');
const render=()=>card._averageBody105('living','temperature',evidence());
const combinedGraph=html=>{
  const graphs=html.match(/<svg\b[^>]*\bdata-trend-chart114\b[\s\S]*?<\/svg>/g)||[];
  assert.equal(graphs.length,1,'Target and output must share one interactive SVG graph');
  assert.ok(!html.includes('hem-control-output-chart075')&&!html.includes('data-output-chart075'),
    'A separate controller output graph remains');
  return graphs[0];
};
const vertices=path=>[...path.matchAll(/[ML]\s*(-?[\d.]+)\s+(-?[\d.]+)/g)]
  .map(match=>({x:Number(match[1]),y:Number(match[2])}));
const near=(actual,expected,message)=>assert.ok(Math.abs(actual-expected)<.011,
  message+': '+actual+' vs '+expected);
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
  assert.ok(html.includes('data-trend-pick="0-target"')&&!html.includes('hem-control-key075'));
  assert.ok(!/NaN|Infinity|undefined/.test(html));
  const graph=combinedGraph(html);
  assert.equal(model.physicalValues075,true);
  assert.ok(graph.includes('<text x="'+(model.left-8)+'"'),'Measured values lost their physical axis labels');
  for(const series of ['hem-avg-line105','hem-control-target075','hem-control-demand075','hem-control-reported075'])
    assert.ok(graph.includes(series),series+' is outside the combined plotting SVG');
  assert.equal((graph.match(/class="hem-trend-cursor114"/g)||[]).length,1);
  assert.ok(!graph.includes('hem-control-cursor075'),'Combined graph has duplicate time cursors');
  assert.ok(graph.includes('hem-control-output-axis075')&&graph.includes('>100%</text>')&&graph.includes('>0%</text>'));
  assert.ok(graph.includes('data-control-output-series075="0"')&&graph.includes('data-control-output-series075="1"'),
    'A second controller lost its output series');
  assert.notEqual(model.controls075[0].color,model.controls075[1].color);
  assert.ok(model.right<model.width-14,'Output tick labels have no reserved space');
  const group=model.controls075[0];
  assert.equal(card._controlTrendPoint075(group,t+449),null,'Today target appeared before first observation');
  assert.equal(card._controlTrendPoint075(group,t+500).target,21);
  assert.equal(card._controlTrendPoint075(group,t+900).target,22,'Target did not step at its recorded time');
  assert.equal(card._controlTrendPoint075(group,t+2200),null,'Target bridged genuine unobserved interval');
  assert.equal(card._controlTrendPoint075(group,t+4201),null,'Target extended after last observed interval');
  const targetPath=card._controlTrendPath075(group,model,'target');
  assert.ok((targetPath.match(/M/g)||[]).length>=2,'Restart or off interval was connected');
  const demandPath=card._controlTrendPath075(group,model,'demand_percent',true);
  const reportedPath=card._controlTrendPath075(group,model,'output_percent',true);
  const targetVertices=vertices(targetPath),demandVertices=vertices(demandPath),reportedVertices=vertices(reportedPath);
  near(targetVertices[0].x,demandVertices[0].x,'Target and demand use different time axes');
  near(targetVertices[0].x,reportedVertices[0].x,'Target and reported output use different time axes');
  near(reportedVertices[0].y,model.top,'100% output is not at the combined plot top');
  near(Math.max(...reportedVertices.map(p=>p.y)),model.bottom,'Reported OFF is not at the combined plot bottom');
  near(demandVertices[0].y,model.bottom-(model.bottom-model.top)*.4,'40% demand uses a separate output lane');
  near(demandVertices.at(-1).y,model.bottom-(model.bottom-model.top)*.8,'80% demand uses the wrong scale');
  const gapX=model.left+(model.right-model.left)*2200/(model.end-model.start);
  for(const segment of reportedPath.split('M').filter(Boolean)){
    const xs=vertices('M'+segment).map(p=>p.x);
    assert.ok(!(Math.min(...xs)<gapX&&Math.max(...xs)>gapX),'Output line bridges missing evidence');
  }
  card._inspectTrend114(t+1050);
  assert.equal(card._trendSelection114(model).time,t+1050,'Mean snap moved controller cursor to another time');
  assert.equal(node('[data-control-target075="0"]').textContent,'22 °C');
  assert.equal(node('[data-control-demand075="0"]').textContent,'75%');
  assert.equal(node('[data-control-output075="0"]').textContent,'On');
  assert.ok(node('[data-trend-label114]').textContent.includes(card._trendDate114(t+900,'time')),
    'Nearest measured sample lost its actual recorded time');
  assert.equal(node('[data-trend-value114]').attributes['data-sample-time114'],String(t+900));
  assert.equal(dot.style.display,'none','Nearest sample dot moved to unrecorded cursor time');
  for(const detail of ['22 °C','75%','On','Radiator <north>','Heat pump'])
    assert.ok(chart.attributes['aria-valuetext'].includes(detail),'Combined graph accessibility omits '+detail);
  near(Number(cursor.attributes.transform.match(/translate\(([-\d.]+)/)[1]),
    model.left+(model.right-model.left)*1050/(model.end-model.start),'Cursor is on a different time axis');
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
  assert.equal(model.points.length,0);
  assert.ok(combinedGraph(html).includes('hem-control-reported075'));
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

  // Output remains inspectable without any target or measured sample. The
  // physical-value axis must not silently become a percentage scale.
  const retainedControls=saved.controlData075;
  saved.controlData075=card._validateControlTrend075(data.sparse,card._controlTrendContext075(saved));
  saved.view114={range:86400,end:t,cursor:null};render();model=saved.model114;
  for(const [index,field] of [[0,'target'],[1,'target_low'],[1,'target_high']]){
    const path=card._controlTrendPath075(model.controls075[index],model,field);
    assert.equal(path.split('M').length-1,2,'Only the explicit restart should split the target');
    const pts=vertices(path.split('M').slice(0,2).join('M'));
    const stepX=model.left+(model.right-model.left)*(t-43200-model.start)/(model.end-model.start);
    assert.ok(pts.some((p,i)=>i&&p.x===pts[i-1].x&&p.y!==pts[i-1].y&&Math.abs(p.x-stepX)<.011));
    assert.ok(pts.every((p,i)=>!i||p.x===pts[i-1].x||p.y===pts[i-1].y));
  }
  card._inspectTrend114(t-15*3600);
  assert.equal(node('[data-control-target075="0"]').textContent,'19 °C');
  assert.equal(node('[data-control-demand075="0"]').textContent,'—');
  assert.equal(node('[data-control-output075="0"]').textContent,'—');
  card._inspectTrend114(t-3*3600);
  assert.equal(node('[data-control-target075="0"]').textContent,'—');
  saved.controlData075=structuredClone(retainedControls);
  for(const controller of saved.controlData075.controllers)for(const series of controller.series)
    for(const point of series.points)point.target=point.target_low=point.target_high=null;
  saved.view114={range:0,end:null,cursor:t+900};html=render();model=saved.model114;
  assert.equal(model.points.length,0);
  assert.ok(combinedGraph(html).includes('hem-control-reported075'));
  assert.ok(!html.includes('data-control-field075="target"')&&!html.includes('data-control-field075="target_low"'));
  assert.ok(model.max<2,'Output-only history polluted the physical-value scale');
  assert.equal(model.physicalValues075,false);
  assert.ok(!combinedGraph(html).includes('<text x="'+(model.left-8)+'"')&&!html.includes('hem-control-unit075'),
    'Output-only evidence displays an invented physical-value axis');
  card._inspectTrend114(t+900);
  assert.ok(!html.includes('data-trend-pick="0-target"'));
  assert.equal(node('[data-control-demand075="0"]').textContent,'75%');
  assert.equal(node('[data-control-output075="0"]').textContent,'On');

  const singleOutput=structuredClone(saved.controlData075);
  singleOutput.controllers=singleOutput.controllers.slice(0,1);
  const singleSeries=singleOutput.controllers[0].series[0];
  singleSeries.points=[{...singleSeries.points[0],until:singleSeries.points[0].t,demand_percent:null}];
  saved.controlData075=singleOutput;saved.view114={range:0,end:null,cursor:null};html=render();model=saved.model114;
  assert.ok(combinedGraph(html).includes('hem-control-sample075'),'One output observation has no visible marker');
  assert.equal(model.physicalValues075,false);
  assert.ok(!combinedGraph(html).includes('<text x="'+(model.left-8)+'"')&&!html.includes('hem-control-unit075'),
    'A single output observation displays an invented physical-value axis');
  card._inspectTrend114();
  assert.equal(card._trendSelection114(saved.model114).time,t+450,'Single output observation used padded time');
  assert.equal(node('[data-control-output075="0"]').textContent,'On');

  // With no requested percentage and only binary reports, the same right
  // axis states On/Off instead of implying a measured power percentage.
  saved.controlData075=structuredClone(retainedControls);
  for(const controller of saved.controlData075.controllers)for(const series of controller.series)
    for(const point of series.points){
      point.demand_percent=null;
      if(point.output_percent!==null){point.output_percent=point.output_percent>0?100:0;point.output_kind='binary';}
    }
  html=render();
  assert.ok(combinedGraph(html).includes('>On</text>')&&html.includes('>Off</text>'));
  assert.ok(!html.includes('>100%</text>')&&!html.includes('hem-control-demand075'));

  // Target-only observations retain the original plot width; there is no
  // empty output axis, output legend or second graph.
  saved.controlData075=structuredClone(retainedControls);
  for(const controller of saved.controlData075.controllers)for(const series of controller.series)
    for(const point of series.points)point.demand_percent=point.output_percent=null;
  html=render();model=saved.model114;
  assert.ok(combinedGraph(html).includes('hem-control-target075'));
  assert.equal(model.physicalValues075,true);
  assert.ok(combinedGraph(html).includes('<text x="'+(model.left-8)+'"'),'Target-only history lost its physical axis labels');
  assert.ok(!html.includes('hem-control-output-axis075')&&!html.includes('hem-control-reported075'));
  assert.equal(model.right,model.width-14,'Absent output unnecessarily narrows the target graph');
  saved.controlData075=retainedControls;
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

  // A controller transition may be only seconds before a Recorder event.
  // Inspect its exact time and held measurement; snapping to the next native
  // event would skip that transition and trap ArrowLeft at the native event.
  const nativeHandlers=new Map();
  const nearNative=card._averageDialog105={...native,
    controlData075:structuredClone(native.controlData075),
    view114:{range:0,end:null,cursor:null},interactive114:false,
    node:{...root,addEventListener(type,handler){
      if(!nativeHandlers.has(type))nativeHandlers.set(type,[]);
      nativeHandlers.get(type).push(handler);
    }}};
  const nativeController=nearNative.controlData075.controllers[0];
  const nativeSeries=nativeController.series[0],nativePoint=nativeSeries.points[0];
  nativeController.series=[{...nativeSeries,points:[
    {...nativePoint,t:t+450,until:t+1195,target:21,output_percent:0},
    {...nativePoint,t:t+1195,until:t+1800,target:22,output_percent:100},
  ]}];
  nearNative.controlData075.controllers=[nativeController];
  const renderNearNative=()=>card._averageBody105('living','temperature',card._entityTrendEvidence122(nearNative));
  renderNearNative();
  card._inspectTrend114(t+1194);
  assert.equal(card._trendSelection114(nearNative.model114).time,t+1194,'Pointer skipped to a future native sample');
  assert.equal(node('[data-trend-value114]').textContent,'68');
  assert.equal(node('[data-control-target075="0"]').textContent,'69.8 °F');
  assert.equal(node('[data-control-output075="0"]').textContent,'Off');
  card._inspectTrend114(t+1195);
  assert.equal(card._trendSelection114(nearNative.model114).time,t+1195,'Controller transition snapped to a native sample');
  assert.equal(node('[data-trend-value114]').textContent,'68','Future native reading replaced the held state');
  assert.equal(node('[data-control-target075="0"]').textContent,'71.6 °F');
  assert.equal(node('[data-control-output075="0"]').textContent,'On');
  card._bindTrend114(nearNative,null);
  const nativeKey=key=>nativeHandlers.get('keydown').forEach(handler=>handler({
    key,target:{closest:()=>chart},preventDefault(){},
  }));
  card._inspectTrend114(t+1200);
  nativeKey('ArrowLeft');
  assert.equal(card._trendSelection114(nearNative.model114).time,t+1195,'ArrowLeft is stuck at the Recorder event');
  assert.equal(node('[data-trend-value114]').textContent,'68');
  assert.equal(node('[data-control-output075="0"]').textContent,'On');
  nativeKey('ArrowLeft');
  assert.equal(card._trendSelection114(nearNative.model114).time,t+450);
  assert.equal(node('[data-control-output075="0"]').textContent,'Off');
  nativeKey('ArrowRight');
  assert.equal(card._trendSelection114(nearNative.model114).time,t+1195);
  nativeKey('ArrowRight');
  assert.equal(card._trendSelection114(nearNative.model114).time,t+1200);
  assert.equal(node('[data-trend-value114]').textContent,'69');
  nearNative.controlData075.controllers=[];nearNative.view114.cursor=t+1195;
  renderNearNative();
  assert.equal(card._trendSelection114(nearNative.model114).time,t+1200,'Native-only Recorder snapping changed');
  card._averageDialog105=native;
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
  const hourly=data.backend.hourly,start=data.backend.hourly_start;
  now=start+125*60;
  card._averageDialog105={area:'room',metric:'temperature',controlData075:card._validateControlTrend075(hourly,hourly)};
  const [thermostat]=card._controlTrendGroups075({room:{area_id:'room',readings:[]},value:{source_ids:hourly.source_ids}});
  const daily={...model,start,end:now};
  const targetSteps=card._controlTrendPath075(thermostat,daily,'target');
  assert.equal(targetSteps.split('M').length-1,2,'Only the Home Assistant restart may split the target');
  const pos=minute=>card._controlTrendPoint075(thermostat,start+minute*60);
  for(const minute of [10.5,11,34.9])assert.equal(pos(minute).target,20);
  for(const minute of [35,59.9,60,75,120,124])assert.equal(pos(minute).target,18);
  assert.equal(pos(113.5),null,'Restart gap was filled');
  for(const field of ['measured','output_percent','demand_percent'])assert.equal(pos(35)[field],null);
  assert.equal(pos(5).output_percent,0,'A recorded idle report disappeared');
  const xy=vertices(targetSteps.split('M')[1]);
  const editX=daily.left+(daily.right-daily.left)*35/125;
  assert.ok(xy.some((v,i)=>i&&v.x===xy[i-1].x&&v.y!==xy[i-1].y&&Math.abs(v.x-editX)<.011));
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
  console.log('PASS: one target/output graph, independent value axes, exact cursor, sources, gaps, units, transport and locales');
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
        }""", data)
        # The public hass setter schedules the first card render. Open through
        # the rendered metric after that lifecycle completes, as a user does;
        # a popup opened before the first render can be replaced by that render.
        temperature = page.locator(
            '[data-room-fold87="living"] [data-hem-average105="temperature"]').first
        expect(temperature).to_be_visible()
        temperature.click()
        popup = page.locator(".hem-avg-dialog105")
        expect(popup).to_be_visible()
        expect(popup.locator('[data-control-status075="loading"]')).to_be_visible()
        page.evaluate("controlRequests[0].resolve(data.response)")
        expect(popup.locator(".hem-control-target075")).to_have_count(2)
        expect(popup.locator("[data-trend-chart114]")).to_have_count(1)
        expect(popup.locator(".hem-control-output-chart075,[data-output-chart075]")).to_have_count(0)
        expect(popup.locator(".hem-control-output-series075")).to_have_count(2)
        assert popup.locator('[data-control-field075="target"]').count() == 1
        assert popup.locator('[data-control-field075="target_low"]').count() == 1
        main = popup.locator("[data-trend-chart114]")
        assert main.evaluate("""svg=>[
          '.hem-avg-line105','.hem-control-target075','.hem-control-demand075','.hem-control-reported075',
          '.hem-control-output-axis075','.hem-trend-cursor114'
        ].every(selector=>[...svg.querySelectorAll(selector)].length&&
          [...svg.querySelectorAll(selector)].every(node=>node.ownerSVGElement===svg))"""), \
            "Measurement, target and output must occupy the same SVG plotting area"
        assert main.locator(".hem-trend-cursor114").count() == 1
        target = main.locator('[data-control-field075="target"]')
        demand = main.locator(".hem-control-demand075").first
        output = main.locator(".hem-control-reported075").first
        paths = main.locator('[data-control-field075]')
        assert target.evaluate("e=>getComputedStyle(e).strokeDasharray") == "none"
        assert demand.evaluate("e=>getComputedStyle(e).strokeDasharray") != "none"
        assert output.evaluate("e=>getComputedStyle(e).strokeDasharray") == "none"
        assert popup.locator(".hem-control-key075,.hem-control-output-legend075").count() == 0
        assert popup.evaluate("""el=>{
          const lines=[...el.querySelectorAll('[data-trend-line]')];
          const colors=lines.map(line=>getComputedStyle(line).stroke);
          return colors.length===new Set(colors).size&&lines.every((line,i)=>{
            const button=el.querySelector('[data-trend-pick="'+line.dataset.trendLine+'"]');
            return button&&['span','b'].every(tag=>getComputedStyle(button.querySelector(tag)).color===colors[i]);
          });
        }"""), "Every visible trace needs a distinct colour matching its label and value"
        expect(main.locator(".hem-control-output-axis075")).to_contain_text("100%")
        expect(main.locator(".hem-control-output-axis075")).to_contain_text("0%")
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
        for detail in ("22 °C", "75%", "On", "Radiator <north>", "Heat pump"):
            assert detail in main.get_attribute("aria-valuetext"), detail
        pid = popup.locator('[data-trend-pick="0-demand_percent"]')
        expected_color = pid.locator("b").evaluate("n=>getComputedStyle(n).color")
        pid.click()
        expect(pid).to_have_attribute("aria-pressed", "false")
        expect(demand).to_be_hidden()
        expect(main.locator('[data-trend-dot="0-demand_percent"]')).to_have_attribute("visibility", "hidden")
        assert "75%" not in main.get_attribute("aria-valuetext")
        assert pid.evaluate("""el=>[el.querySelector('span'),el.querySelector('b')].every(node=>{
          const [r,g,b]=getComputedStyle(node).color.match(/[0-9]+/g).map(Number);
          return r===g&&g===b;
        })""")
        expect(target).to_be_visible()
        pid.press("Space")
        expect(pid).to_be_focused()
        expect(pid).to_have_attribute("aria-pressed", "true")
        expect(demand).to_be_visible()
        assert pid.locator("b").evaluate("n=>getComputedStyle(n).color") == expected_color
        expect(demand).to_have_attribute("data-focused", "")
        expect(main.locator(".hem-trend-tag text")).to_have_text("75%")
        expect(main.locator('[data-trend-dot="0-demand_percent"]')).to_have_attribute("visibility", "visible")
        main.focus()
        main.press("Home")
        expect(main.locator(".hem-trend-tag")).to_have_attribute("visibility", "hidden")
        expect(main.locator('[data-trend-dot="0-demand_percent"]')).to_have_attribute("visibility", "hidden")
        main.press("End")
        goal = popup.locator('[data-trend-pick="0-target"]')
        goal.click()
        expect(target).to_be_hidden()
        goal.click()
        expect(main.locator(".hem-trend-tag text")).to_have_text("24 °C")
        # Each legend button controls its entire series, including fills, isolated
        # samples and both dependencies of a target band, without fetching history.
        requests_before = page.evaluate("controlRequests.length")
        measure = popup.locator('[data-trend-pick="measured"]')
        low = popup.locator('[data-trend-pick="1-target_low"]')
        high = popup.locator('[data-trend-pick="1-target_high"]')
        low.click()
        expect(main.locator(".hem-control-band075").first).to_be_hidden()
        expect(main.locator('[data-trend-layer="1-target_high"]')).to_have_css("display", "inline")
        high.click()
        low.click()
        expect(main.locator(".hem-control-band075").first).to_be_hidden()
        high.click()
        expect(main.locator(".hem-control-band075").first).to_be_visible()
        measure.click()
        expect(main.locator(".hem-avg-line105")).to_be_hidden()
        expect(main.locator(".hem-trend-sample114").first).to_be_hidden()
        expect(main.locator('path[fill^="url(#hem-trend-fill"]')).to_be_hidden()
        expect(main.locator(".hem-trend-cursor114 circle")).to_be_hidden()
        expect(target).to_be_visible()
        goal.click()
        popup.locator('[data-trend-range114="21600"]').click()
        page.evaluate("card._refreshAverage105(true)")
        expect(measure).to_have_attribute("aria-pressed", "false")
        expect(goal).to_have_attribute("aria-pressed", "false")
        expect(target).to_be_hidden()
        popup.locator('[data-trend-range114="86400"]').click()
        # The controller identity owns the choice even if a refresh reorders devices.
        for index in (1, 0):
            page.evaluate("card._averageDialog105.controlData075.controllers.reverse();card._refreshAverage105(true)")
            expect(popup.locator(f'[data-trend-pick="{index}-target"]')).to_have_attribute("aria-pressed", "false")
            expect(target).to_be_hidden()
        # All series can be hidden and recovered one at a time.
        buttons = popup.locator('[data-trend-pick]')
        for button in buttons.all():
            if button.get_attribute("aria-pressed") == "true":
                button.click()
        expect(main.locator('[data-trend-line]:visible')).to_have_count(0)
        expect(main.locator(".hem-control-sample075:visible")).to_have_count(0)
        expect(main.locator(".hem-trend-cursor114")).to_be_hidden()
        expect(main.locator(".hem-trend-tag")).to_have_attribute("visibility", "hidden")
        goal.press("Enter")
        expect(target).to_be_visible()
        expect(main.locator('[data-trend-line]:visible')).to_have_count(1)
        for button in buttons.all():
            if button.get_attribute("aria-pressed") == "false":
                button.click()
        assert page.evaluate("controlRequests.length") == requests_before
        for language in ("en", "el", "de"):
            page.evaluate("language=>{card._hass.language=language;card._refreshAverage105(true)}", language)
            assert "undefined" not in popup.inner_text()
            for width in (590, 375, 320):
                page.set_viewport_size({"width": width, "height": 740})
                expect(popup).to_be_visible()
                assert popup.evaluate("e=>e.scrollWidth<=e.clientWidth+1"), (language, width)
                bounds = popup.bounding_box()
                assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width + 1
                assert main.locator(".hem-control-output-series075").count() == 2
                assert main.evaluate("""svg=>[...svg.querySelectorAll('.hem-control-output-axis075 text')]
                  .every(label=>{const box=label.getBBox();
                    return box.x>=0&&box.x+box.width<=svg.viewBox.baseVal.width+1})"""), (language, width)
        page.evaluate("""()=>{
          const saved=card._averageDialog105;
          window.retainedControlData=saved.controlData075;
          saved.controlData075=structuredClone(retainedControlData);
          for(const controller of saved.controlData075.controllers)for(const series of controller.series)
            for(const point of series.points){
              point.demand_percent=null;
              if(point.output_percent!==null){point.output_percent=point.output_percent>0?100:0;point.output_kind='binary';}
            }
          card._refreshAverage105(true);
        }""")
        expect(main.locator(".hem-control-output-axis075")).to_have_count(1)
        for language in data["languages"]:
            page.evaluate("language=>{card._hass.language=language;card._refreshAverage105(true)}", language)
            assert main.evaluate("""svg=>{
              const labels=[...svg.querySelectorAll('.hem-control-output-axis075 text')];
              return labels.length>=2&&labels.every(label=>{const box=label.getBBox();
                return box.x>=0&&box.x+box.width<=svg.viewBox.baseVal.width+1});
            }"""), ("binary axis", language, 320)
            assert popup.evaluate("e=>e.scrollWidth<=e.clientWidth+1"), ("binary axis", language, 320)
        page.evaluate("""()=>{
          const saved=card._averageDialog105;
          card._hass.language='en';
          saved.controlData075=structuredClone(retainedControlData);
          for(const controller of saved.controlData075.controllers)for(const series of controller.series)
            for(const point of series.points)point.target=point.target_low=point.target_high=null;
          saved.history074=[];saved.status074='empty';
          saved.view114={range:0,end:null,cursor:data.start+900};card._refreshAverage105(true);
        }""")
        expect(popup.locator("[data-trend-chart114]")).to_have_count(1)
        expect(main.locator(".hem-control-reported075")).to_have_count(2)
        expect(main.locator('[data-control-field075="target"],[data-control-field075="target_low"]')).to_have_count(0)
        expect(popup.locator("[data-trend-value114]")).to_have_text("—")
        expect(popup.locator('[data-control-target075="0"]')).to_have_count(0)
        expect(popup.locator('[data-control-demand075="0"]')).to_have_text("75%")
        expect(main.locator(".hem-control-unit075")).to_have_count(0)
        assert main.evaluate("""svg=>![...svg.querySelectorAll('text')].some(label=>
          Number(label.getAttribute('x'))===card._averageDialog105.model114.left-8)"""), \
            "Output-only graph displays placeholder physical axis values"
        main.focus()
        main.press("ArrowRight")
        assert page.evaluate("card._averageDialog105.view114.cursor") == START + 1800
        expect(popup.locator('[data-control-output075="0"]')).to_have_text("Off")
        page.evaluate("""()=>{
          const saved=card._averageDialog105;
          saved.controlData075=retainedControlData;saved.history074=data.samples;saved.status074='ready';
          card._refreshAverage105(true);
        }""")
        page.evaluate("""()=>{
          card._hass.language='en';card._loadControlTrend075(card._averageDialog105,true);
          controlRequests.at(-1).reject(Error('temporary'));
        }""")
        expect(popup.locator('[data-retry-control075]')).to_be_visible()
        assert main.count() == 1
        popup.locator('[data-retry-control075]').click()
        page.evaluate("controlRequests.at(-1).resolve(data.response)")
        expect(popup.locator('[data-retry-control075]')).to_have_count(0)

        # Reproduce a day of brief controller reports. Both the scalar and
        # heat/cool limits must form staircases across the hours between them.
        page.evaluate("""()=>{
          const saved=card._averageDialog105;
          saved.controlData075=card._validateControlTrend075(data.sparse,card._controlTrendContext075(saved));
          saved.view114={range:86400,end:data.start,cursor:null};
          card._refreshAverage105(true);
        }""")
        for field in ("target", "target_low", "target_high"):
            path = main.locator(f'[data-control-field075="{field}"]').get_attribute("d")
            segments = path.split("M")[1:]
            assert len(segments) == 2, (field, path)  # One explicit restart.
            vertices = [(float(x), float(y)) for x, y in re.findall(
                r"[L ]*([\d.]+) ([\d.]+)", segments[0])]
            step_x = page.evaluate("""()=>{
              const m=card._averageDialog105.model114;
              return m.left+(m.right-m.left)*(data.start-43200-m.start)/(m.end-m.start);
            }""")
            assert any(abs(x-step_x)<.02 and x==old_x and y!=old_y
                       for (old_x,old_y),(x,y) in zip(vertices, vertices[1:])), (field, path)
            assert all(x==old_x or y==old_y for (old_x,old_y),(x,y) in zip(vertices, vertices[1:]))
        assert main.locator('.hem-control-target075 circle').count() == 0
        page.evaluate("card._inspectTrend114(data.start-15*3600)")
        expect(popup.locator('[data-control-target075="0"]')).to_have_text("19 °C")
        expect(popup.locator('[data-control-demand075="0"]')).to_have_text("—")
        expect(popup.locator('[data-control-output075="0"]')).to_have_text("—")
        page.evaluate("card._inspectTrend114(data.start-3*3600)")
        expect(popup.locator('[data-control-target075="0"]')).to_have_text("—")
        # A single sampled output has an isolated marker that follows its button.
        isolated = main.locator('[data-trend-layer="0-output_percent"] .hem-control-sample075').first
        expect(isolated).to_be_visible()
        popup.locator('[data-trend-pick="0-output_percent"]').click()
        expect(isolated).to_be_hidden()
        popup.locator("[data-close-avg105]").click()
        expect(popup).to_have_count(0)
        temperature.click()
        page.evaluate("controlRequests.at(-1).resolve(data.response)")
        expect(popup.locator('[data-trend-pick="0-output_percent"]')).to_have_attribute("aria-pressed", "true")
        popup.locator("[data-close-avg105]").click()
        assert page.evaluate("deviceCalls") == []
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    data = fixture()
    subprocess.run(["node", "-e", NODE, str(CARD)], input=json.dumps(data), text=True, check=True)
    if "--logic-only" not in sys.argv:
        browser_checks(data)
        print("PASS: single target/output graph pointer, keyboard, retry, localization and narrow-screen geometry")
