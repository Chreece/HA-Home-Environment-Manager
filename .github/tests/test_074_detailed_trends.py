"""Full-detail room history and exact Recorder outage boundaries.

The production chart and async transport run in Node; Chromium also exercises
loading, retry, switching charts, range navigation and narrow-screen geometry.
Only authenticated WebSocket responses and HA snapshots are fixtures.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
BASE = runpy.run_path(str(ROOT / ".github/tests/test_beta114_interactive_trends.py"))
START = BASE["START"]


def fixture():
    states = BASE["fixture"]()
    room = states["sensor.hem"]["attributes"]["dashboard"]["rooms"][0]
    # Seven retained days: the old whole-week preview supplied only about
    # ten means per day and spread the short interruption over several hours.
    means = [{"t": START + i * 900, "v": round(20 + (i % 43) / 100, 3),
              **({"break_before": True} if i == 632 else {})}
             for i in range(672) if i not in (630, 631)]
    mold = [{"t": START + i * 300, "v": None if i == 1900 else round(65 + (i % 71) / 10, 3)}
            for i in range(2017)]
    room["environment"]["measurement_evidence"]["temperature"]["trend"] = means[::10] + [means[-1]]
    room["environment"]["mold_trend"] = {
        "value": 68.5, "source_count": 0, "source_ids": [], "trend": mold[::22] + [mold[-1]],
    }
    room["readings"].append({"metric": "mold", "value": 68.5, "unit": "%", "available": True})
    detailed = {
        "temperature": {"area_id": "living", "metric": "temperature", "source_count": 2,
                        "source_ids": ["sensor.temp_a", "sensor.temp_b"], "trend": means},
        "mold": {"area_id": "living", "metric": "mold", "source_count": 0,
                 "source_ids": [], "trend": mold},
    }
    return {"states": states, "detailed": detailed, "start": START}


NODE = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const fixture=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(n){return this.classes.get(n)},define(n,C){this.classes.set(n,C)}};
global.window={innerWidth:590};
global.document={createElement:()=>({content:{firstElementChild:null}})};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card'),card=Object.create(Card.prototype);
let now=fixture.start+7*86400;
Date.now=()=>now*1000;
const pending=[];
card._config={entity:'sensor.hem'};
card._hass={language:'en',config:{time_zone:'Europe/Berlin'},states:structuredClone(fixture.states),
  connection:{},localize:()=>undefined,callService:()=>{throw Error('History called a device service')},
  callWS:message=>new Promise((resolve,reject)=>pending.push({message,resolve,reject}))};
card._closeAverage105=function(){this._averageDialog105=null};
const open=metric=>{
  const evidence=card._evidence105('living',metric);
  const saved=card._averageDialog105={area:'living',metric,sources:evidence.value.source_ids.join('|'),
    history074:[],status074:'loading',connection074:card._hass.connection,dashboard074:'sensor.hem',
    width114:480,view114:{range:86400,end:null,cursor:null},
    node:{scrollTop:0,setAttribute(){},querySelector:()=>null}};
  return {saved,request:card._loadAverageTrend074(saved)};
};
(async()=>{
  const average=open('temperature');
  assert.equal(average.saved.model114.points.length,0,'Sparse overview preview leaked into loading chart');
  assert.deepEqual(pending[0].message,{type:'environment_manager/trend',entity_id:'sensor.hem',area_id:'living',metric:'temperature'});
  pending[0].resolve(fixture.detailed.temperature);await average.request;
  assert.equal(average.saved.status074,'ready');
  assert.equal(average.saved.model114.points.length,670);
  assert.equal(average.saved.model114.visible.length,95,'The daily chart lost its retained quarter-hour samples');
  assert.deepEqual(average.saved.model114.gaps,[[fixture.start+629*900,fixture.start+632*900]]);
  const original=JSON.stringify(average.saved.history074);
  average.saved.view114={range:21600,end:fixture.start+620*900,cursor:fixture.start+617*900};
  const pinned=structuredClone(average.saved.view114);
  card._refreshAverage105(true);
  assert.equal(card._trendSelection114(average.saved.model114).point.t,pinned.cursor);
  const overview=card._hass.states['sensor.hem'].attributes.dashboard.rooms[0].environment.measurement_evidence.temperature;
  overview.trend.push({t:now,v:21.25});now+=59;card._refreshAverage105();
  assert.equal(pending.length,1,'History refresh ignored one-minute throttle');
  now+=2;card._refreshAverage105();assert.equal(pending.length,2);
  assert.equal(JSON.stringify(average.saved.history074),original,'Loading erased existing chart');
  card._refreshAverage105();assert.equal(pending.length,2,'In-flight request duplicated');
  pending[1].resolve({...fixture.detailed.temperature,trend:[...fixture.detailed.temperature.trend,{t:now-61,v:21.25}]});
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(average.saved.view114,pinned,'Background refresh moved the inspected view');
  now+=61;card._refreshAverage105();assert.equal(pending.length,2,'Unchanged overview repeatedly fetched history');

  const mold=open('mold');pending[2].resolve(fixture.detailed.mold);await mold.request;
  assert.equal(mold.saved.model114.points.length,2016,'Chart truncated mold history to the last 1000 points');
  assert.equal(mold.saved.model114.first,fixture.start);
  assert.equal(mold.saved.model114.visible.length,288);
  assert.deepEqual(mold.saved.model114.gaps,[[fixture.start+1899*300,fixture.start+1901*300]]);
  mold.saved.view114.cursor=fixture.start+1900*300;
  assert.equal(card._trendSelection114(mold.saved.model114).point,null,'Unavailable observation was filled');
  const room=card._hass.states['sensor.hem'].attributes.dashboard.rooms[0];
  room.environment.mold_trend.value=null;card._refreshAverage105(true);
  assert.equal(card._averageDialog105,mold.saved,'Current unavailability hid historical mold values');
  assert.equal(mold.saved.model114.points.length,2016);

  const stale=open('temperature'),fresh=open('mold');
  pending[4].resolve(fixture.detailed.mold);await fresh.request;
  pending[3].resolve(fixture.detailed.temperature);await stale.request;
  assert.equal(card._averageDialog105,fresh.saved);
  assert.equal(fresh.saved.model114.points.length,2016,'Stale response replaced another metric');
  const closed=open('temperature');card._averageDialog105=null;
  pending[5].resolve(fixture.detailed.temperature);await closed.request;
  assert.equal(card._averageDialog105,null,'Closed chart was resurrected');
  const reconnect=open('temperature');card._hass.connection={};
  pending[6].resolve(fixture.detailed.temperature);await reconnect.request;
  assert.deepEqual(reconnect.saved.history074,[],'Old connection response accepted');
  const switched=open('temperature');
  overview.source_ids=['sensor.temp_a','sensor.temp_c'];
  pending[7].resolve(fixture.detailed.temperature);await switched.request;
  assert.deepEqual(switched.saved.history074,[],'Different contributor history accepted');
  overview.source_ids=['sensor.temp_a','sensor.temp_b'];
  const failed=open('temperature');pending[8].reject(Error('unavailable'));await failed.request;
  assert.equal(failed.saved.status074,'error');
  const retry=card._loadAverageTrend074(failed.saved,true);
  pending[9].resolve({...fixture.detailed.temperature,trend:[]});await retry;
  assert.equal(failed.saved.status074,'empty');
  assert.deepEqual(failed.saved.history074,[],'Current mean became a fabricated recorded point');
  const older=card._loadAverageTrend074(failed.saved,true),newer=card._loadAverageTrend074(failed.saved,true);
  pending[11].resolve(fixture.detailed.temperature);await newer;
  pending[10].resolve({...fixture.detailed.temperature,trend:[]});await older;
  assert.equal(failed.saved.status074,'ready','Out-of-order reply erased the newer history');
  const invalid=card._loadAverageTrend074(failed.saved,true);
  pending[12].resolve({...fixture.detailed.temperature,source_ids:['sensor.other','sensor.temp_b']});await invalid;
  assert.equal(failed.saved.status074,'error','Mismatched sources were accepted');

  // Recorder stores a known state until its actual unavailable transition.
  // The chart must not erase twenty valid hours before a three-hour outage.
  const t=fixture.start,id='sensor.temp_a';
  card._hass.states[id]={state:'21',attributes:{unit_of_measurement:'°C'}};
  const native=card._averageDialog105={entity122:id,area:'living',metric:'temperature',unit122:'°C',
    history122:[{t,v:20},{t:t+20*3600,v:null},{t:t+23*3600,v:21}],
    historyEnd122:t+24*3600,status122:'ready',width114:480,
    view114:{range:0,end:null,cursor:t+19*3600}};
  let html=card._averageBody105('living','temperature',card._entityTrendEvidence122(native));
  assert.deepEqual(native.model114.gaps,[[t+20*3600,t+23*3600]]);
  assert.equal(card._trendSelection114(native.model114).point.v,20);
  for(const stamp of [t+20*3600,t+21*3600]){
    native.view114.cursor=stamp;assert.equal(card._trendSelection114(native.model114).point,null);
  }
  const x=(48+(native.model114.right-48)*20/24).toFixed(2);
  assert.ok(html.includes('L'+x+' '),'Last valid state was not drawn to its unavailable boundary');
  assert.equal(native.model114.points.length,2,'Held states fabricated physical samples');
  native.history122=[{t,v:20},{t:t+20*3600,v:null}];
  card._hass.states[id].state='unavailable';native.view114={range:21600,end:t+19*3600,cursor:t+18*3600};
  html=card._averageBody105('living','temperature',card._entityTrendEvidence122(native));
  assert.equal(card._trendSelection114(native.model114).point.v,20,'A valid held interval vanished when panned');
  assert.equal(native.model114.visible[0].carried_view,true);
  assert.ok(html.includes('<span>0 samples</span>'),'Viewport anchor counted as a measurement');
  assert.ok(!html.includes('class="hem-trend-sample114"'),'Viewport anchor drew a fake measurement dot');
  native.view114={range:0,end:null,cursor:t+23*3600};
  card._averageBody105('living','temperature',card._entityTrendEvidence122(native));
  assert.deepEqual(native.model114.gaps,[[t+20*3600,t+24*3600]]);
  assert.equal(card._trendSelection114(native.model114).point,null,'Current outage became a held value');
  console.log('PASS: full detailed trends, bounded loading, exact gaps, identity, retries, navigation and held Recorder states');
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
          window.fixture=data;window.requests=[];window.deviceCalls=[];
          window.card=document.createElement('home-environment-manager-card');document.body.append(card);
          card._config={entity:'sensor.hem'};
          card._hass={language:'el',states:data.states,connection:{},config:{time_zone:'Europe/Berlin'},
            localize:()=>undefined,callWS:message=>new Promise((resolve,reject)=>requests.push({message,resolve,reject})),
            callService:(...args)=>{deviceCalls.push(args);throw Error('No device writes')}};
          card._renderContent(true);
        }""", data)
        page.locator('[data-room-fold87="living"] [data-hem-average105="temperature"]').first.click()
        popup = page.locator('.hem-avg-dialog105')
        expect(popup.locator('[data-entity-history-status122="loading"]')).to_be_visible()
        assert popup.locator('[data-trend-chart114]').count() == 0
        page.evaluate("requests[0].resolve(fixture.detailed.temperature)")
        page.wait_for_function("card._averageDialog105.status074==='ready'")
        assert page.evaluate("card._averageDialog105.model114.visible.length") == 95
        assert popup.locator('.hem-trend-gap114').count() == 1
        assert page.locator('[data-room-fold87="living"]').get_attribute('open') is None
        chart = popup.locator('[data-trend-chart114]')
        chart.focus()
        chart.press('Home')
        chart.press('ArrowRight')
        assert page.evaluate("card._averageDialog105.view114.cursor!==null")
        popup.locator('[data-trend-range114="604800"]').click()
        assert page.evaluate("card._averageDialog105.model114.points.length") == 670
        page.evaluate("card._closeAverage105();card._openAverage105('living','mold')")
        page.evaluate("requests[1].reject(Error('temporary history failure'))")
        expect(popup.locator('[data-entity-history-status122="error"]')).to_be_visible()
        popup.locator('[data-retry-history122]').click()
        page.evaluate("requests[2].resolve(fixture.detailed.mold)")
        page.wait_for_function("card._averageDialog105.status074==='ready'")
        assert page.evaluate("card._averageDialog105.model114.points.length") == 2016
        assert page.evaluate("card._averageDialog105.model114.first") == START
        assert page.evaluate("requests.every(r=>r.message.type==='environment_manager/trend')")
        screenshot_dir = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
        for width in (590, 390, 320):
            page.set_viewport_size({"width": width, "height": 900})
            expect(chart).to_be_visible()
            assert popup.evaluate("e=>e.scrollWidth<=e.clientWidth+1")
            bounds = popup.bounding_box()
            assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width + 1
            if screenshot_dir:
                Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(Path(screenshot_dir) / f"hem-detailed-mold-{width}.png"))
        page.evaluate("card._closeAverage105();card._openAverage105('living','temperature');card._closeAverage105()")
        page.evaluate("requests[3].resolve(fixture.detailed.temperature)")
        assert popup.count() == 0
        assert page.evaluate("deviceCalls") == []
        assert not errors, errors
        browser.close()
    print("PASS: detailed trend browser loading/retry/keyboard/mobile/close and zero physical writes")


if __name__ == "__main__":
    data = fixture()
    subprocess.run(["node", "-e", NODE, str(CARD)], input=json.dumps(data), text=True, check=True)
    if "--logic-only" not in sys.argv:
        browser_checks(data)
