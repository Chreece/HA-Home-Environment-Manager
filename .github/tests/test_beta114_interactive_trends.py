"""Interactive recorded averages: time navigation, exact samples and stable input.

--logic-only runs the production JavaScript model/markup in Node. The default
also checks mouse, keyboard, touch pointer, source navigation and responsive
light/dark chart layouts in Chromium. No physical device service is called.
HEM_TEST_SCREENSHOT_DIR enables desktop/mobile screenshots for visual review.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
START = 1793520000


def fixture():
    points = [{"t": START + i * 3600, "v": round(20.123 + (i % 12) / 10, 3)}
              for i in range(97) if not 37 <= i <= 45]
    evidence = {"value": 21.456, "source_ids": ["sensor.temp_a", "sensor.temp_b"],
                "source_count": 2, "trend": points}
    room = {"area_id": "living", "name": "Wohnzimmer", "status": "safe",
            "action": None, "windows": [],
            "readings": [{"metric": "temperature", "value": 21.456,
                          "unit": "°C", "available": True, "name": "Room temperature"},
                         {"metric": "humidity", "value": 50.2, "unit": "%",
                          "available": True, "name": "Humidity", "entity_id": "sensor.humidity"}],
            "environment": {"measurement_evidence": {"temperature": evidence,
                "humidity": {"value": 50.2, "source_count": 1, "source_ids": ["sensor.humidity"]}},
                "climate_plan": {"status": "ready", "controller": "environment", "profile": "home",
                    "temperature_c": 21.456, "equipment_plan": {}, "actuation": {"status": "advisory_only"}}}}
    dashboard = {"version": 1, "rooms": [room],
                 "summary": {"safe": 1, "attention": 0, "unknown": 0},
                 "outdoor": {"status": "safe", "readings": [], "weather": [],
                             "warnings": [], "blockers": []}}
    states = {"sensor.hem": {"state": "ready", "attributes": {"dashboard": dashboard}}}
    for entity_id, name in (("sensor.temp_a", "Living room"), ("sensor.temp_b", "Window side"),
                            ("sensor.humidity", "Room humidity")):
        states[entity_id] = {"state": "21.4", "attributes": {"friendly_name": name}}
    return states


NODE_CHECKS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const states=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={innerWidth:590};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');
const c=Object.create(Card.prototype);
c._config={entity:'sensor.hem'};
c._hass={language:'en',config:{time_zone:'Europe/Berlin'},states,
  localize:()=>undefined,callService:()=>{throw Error('Read-only chart called HA service')}};
const evidence=c._evidence105('living','temperature');
const original=JSON.stringify(evidence);
c._averageDialog105={area:'living',metric:'temperature',sources:evidence.value.source_ids.join('|'),width114:480};
let html=c._averageBody105('living','temperature',evidence);
let m=c._averageDialog105.model114,s=c._averageDialog105.view114;
assert.equal(s.range,86400,'Multi-day history should open at the most recent day');
assert.equal(m.end-m.start,86400);
assert.equal(m.visible.length,25);
assert.equal(c._trendSelection114(m).point.v,evidence.value.trend.at(-1).v);
assert.ok(html.includes('21.456 °C'),'Current exact mean is available beside the recorded value');
assert.ok(html.includes('role="slider"')&&html.includes('data-trend-range114="604800"'));
assert.ok(!/NaN|Infinity/.test(html));
assert.equal(JSON.stringify(evidence),original,'Rendering changed the recorded history');
const rowsBefore=JSON.stringify(evidence);
// Invoke real navigation with DOM painting stubbed; state and bounds are real.
c._refreshAverage105=function(){this._averageBody105('living','temperature',evidence)};
c._moveTrend114('older');
m=c._averageDialog105.model114;
assert.equal(m.end,evidence.value.trend.at(-1).t-86400);
assert.equal(m.newer,true);
const held=m.end;
evidence.value.trend.push({t:evidence.value.trend.at(-1).t+3600,v:22.987});
c._averageBody105('living','temperature',evidence);
assert.equal(c._averageDialog105.model114.end,held,'An HA update must not pull an older view to latest');
c._moveTrend114('latest');
assert.equal(c._averageDialog105.view114.end,null);
assert.equal(c._averageDialog105.model114.end,evidence.value.trend.at(-1).t);
const liveEnd=c._averageDialog105.model114.end;
c._averageDialog105.node={querySelector:()=>null};
c._inspectTrend114(liveEnd-3600);
assert.equal(s.end,liveEnd,'Inspecting a live chart must pin its visible period');
assert.equal(s.cursor,liveEnd-3600);
// Gaps remain split paths; inspector reports missing samples instead of
// interpolating a value into the ten-hour source outage.
s.range=0;s.cursor=evidence.value.trend[36].t+4*3600;
html=c._averageBody105('living','temperature',evidence);m=c._averageDialog105.model114;
assert.equal(m.gaps.length,1);
assert.equal(c._trendSelection114(m).point,null);
assert.match(html,/class="hem-trend-gap114"/);
assert.match(html,/class="hem-avg-line105" d="M[^\"]+ M/);
s.cursor=evidence.value.trend[5].t;
assert.equal(c._trendSelection114(m).point.v,evidence.value.trend[5].v);
assert.equal(c._trendSelection114(m).time,evidence.value.trend[5].t);
// Displaying data never rewrites the underlying recorded history.
const expected=JSON.parse(rowsBefore);expected.value.trend.push({t:expected.value.trend.at(-1).t+3600,v:22.987});
expected.room.environment.measurement_evidence.temperature=expected.value;
assert.equal(JSON.stringify(evidence),JSON.stringify(expected));
// Sparse, constant and unavailable samples: no fabricated line, no zero date.
const one=structuredClone(evidence);one.value.trend=[{t:1793520000,v:-2.345}];
c._averageDialog105.view114={range:0,end:null,cursor:null};
html=c._averageBody105('living','temperature',one);m=c._averageDialog105.model114;
assert.equal(m.visible.length,1);assert.equal(m.start+m.end,2*1793520000);
assert.equal(c._trendSelection114(m).point.v,-2.345);
assert.ok(!/NaN|Infinity/.test(html));
const empty=structuredClone(one);empty.value.trend=[];
html=c._averageBody105('living','temperature',empty);m=c._averageDialog105.model114;
assert.equal(m.visible.length,0);assert.equal(c._trendSelection114(m).point,null);
assert.ok(!html.includes('data-trend-chart114'));assert.ok(html.includes('History appears'));
const unordered=structuredClone(one);
unordered.value.trend=[{t:1793521800,v:21.333},{t:1793520000,v:21},
  {t:1793520900,v:null},{t:1793521800,v:21.444},{t:-2,v:20},
  {t:9e15,v:20},{t:1793522700,v:21.555}];
html=c._averageBody105('living','temperature',unordered);m=c._averageDialog105.model114;
assert.deepEqual(m.points.map(p=>p.t),[1793520000,1793521800,1793522700]);
assert.equal(m.points[1].v,21.444);assert.equal(m.gaps.length,1);
assert.ok(!/NaN|Infinity/.test(html));
for(const language of ['en','de','el']){
  c._hass.language=language;
  assert.ok(c._trendDate114(1793520000).length>10);
  const rendered=c._averageBody105('living','temperature',one);
  assert.ok(!rendered.includes('undefined'));
  const title=({en:'Temperature',de:'Temperatur',el:'Θερμοκρασία'})[language];
  assert.ok(rendered.includes('<strong>'+title+'</strong>'),'Trend metric title must be translated');
}
console.log('BETA114_TREND_GEOMETRY_GAPS_EXACT_VALUES_NAVIGATION=PASS');
"""


def browser_checks(states):
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
        page.evaluate("""states=>{
          window.info=[];window.calls=[];
          window.card=document.createElement('home-environment-manager-card');
          document.body.append(card);
          card.addEventListener('hass-more-info',e=>info.push(e.detail.entityId));
          card._config={entity:'sensor.hem'};
          card._hass={language:'en',config:{time_zone:'Europe/Berlin'},states,callWS:async()=>({}),
            localize:()=>undefined,callService:(...args)=>{calls.push(args);return Promise.resolve()}};
          card._renderContent(true);
        }""", states)
        trigger = page.locator('[data-room-fold87="living"] [data-hem-average105="temperature"]').first
        trigger.click()
        popup = page.locator(".hem-avg-dialog105")
        popup.wait_for(state="visible")
        chart = popup.locator("[data-trend-chart114]")
        assert popup.locator('[data-trend-range114="86400"]').get_attribute("aria-pressed") == "true"
        assert popup.locator("[data-trend-value114]").inner_text() == "20.123"
        assert "21.456" in popup.locator(".hem-trend-current114").inner_text()
        assert chart.get_attribute("role") == "slider"
        popup.locator('[data-trend-range114="21600"]').click()
        popup.locator('[data-trend-move114="older"]').click()
        model = page.evaluate("card._averageDialog105.model114")
        assert model["end"] == START + 90 * 3600
        assert popup.locator('[data-trend-move114="newer"]').is_enabled()

        def select_sample(index, *, down=False):
            point = page.evaluate("i=>card._averageDialog105.model114.visible[i]", index)
            coord = page.evaluate("""t=>{
              const saved=card._averageDialog105,m=saved.model114;
              const r=saved.node.querySelector('[data-trend-chart114]').getBoundingClientRect();
              return {x:r.x+(m.left+(m.right-m.left)*(t-m.start)/(m.end-m.start))*r.width/m.width,
                      y:r.y+r.height*.5};
            }""", point["t"])
            page.mouse.move(coord["x"], coord["y"])
            if down:
                page.mouse.down()
            assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == point["t"]
            return point, coord

        selected, _ = select_sample(2)
        chart.focus()
        chart.press("Home")
        first = page.evaluate("card._averageDialog105.model114.visible[0]")
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == first["t"]
        chart.press("ArrowRight")
        second = page.evaluate("card._averageDialog105.model114.visible[1]")
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == second["t"]
        chart.press("End")
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == model["end"]
        chart.press("PageUp")
        assert page.evaluate("card._averageDialog105.model114.end") == model["end"] - 21600
        chart.press("PageDown")
        assert page.evaluate("card._averageDialog105.model114.end") == model["end"]
        assert chart.evaluate("e=>e===e.getRootNode().activeElement")

        def update():
            page.evaluate("""()=>{
              const states=structuredClone(card._hass.states);
              const value=states['sensor.hem'].attributes.dashboard.rooms[0].environment.measurement_evidence.temperature;
              value.trend.push({t:value.trend.at(-1).t+3600,v:22.987});value.value=22.987;
              card.hass={...card._hass,states};card._renderContent(true);
            }""")

        selected, _ = select_sample(2)
        chart.focus()
        page.evaluate("window.retainedChart=card._averageDialog105.node.querySelector('[data-trend-chart114]')")
        update()
        assert page.evaluate("retainedChart===card._averageDialog105.node.querySelector('[data-trend-chart114]')")
        assert chart.evaluate("e=>e===e.getRootNode().activeElement"), "HA update lost chart keyboard focus"
        assert page.evaluate("card._averageDialog105.model114.end") == model["end"]
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == selected["t"]
        # A live HA update cannot remove a chart during an active drag.
        selected, coord = select_sample(3, down=True)
        update()
        assert page.evaluate("card._averageDialog105.pending114")
        assert page.evaluate("retainedChart===card._averageDialog105.node.querySelector('[data-trend-chart114]')")
        page.mouse.up()
        assert not page.evaluate("card._averageDialog105.pending114")
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == selected["t"]
        popup.locator('[data-trend-move114="latest"]').click()
        assert popup.locator('[data-trend-move114="newer"]').is_disabled()
        assert popup.locator("[data-trend-value114]").inner_text() == "22.987"
        # Explicit touch pointer events use the same actual time coordinates.
        selected, coord = select_sample(1)
        chart.dispatch_event("pointerdown", {"pointerId": 17, "pointerType": "touch", "isPrimary": True,
                              "button": 0, "clientX": coord["x"], "clientY": coord["y"]})
        target = page.evaluate("""()=>{
          const saved=card._averageDialog105,m=saved.model114,point=m.visible[3];
          const r=saved.node.querySelector('[data-trend-chart114]').getBoundingClientRect();
          return {t:point.t,x:r.x+(m.left+(m.right-m.left)*(point.t-m.start)/(m.end-m.start))*r.width/m.width,
                  y:r.y+r.height*.5};
        }""")
        chart.dispatch_event("pointermove", {"pointerId": 17, "pointerType": "touch", "isPrimary": True,
                              "clientX": target["x"], "clientY": target["y"]})
        chart.dispatch_event("pointerup", {"pointerId": 17, "pointerType": "touch", "isPrimary": True})
        assert page.evaluate("card._averageDialog105.pointer114===undefined")
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == target["t"]
        # A real browser touch tap returns to a different actual record.
        page.touchscreen.tap(coord["x"], coord["y"])
        assert float(popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")) == selected["t"]
        # Navigate to the outage, inspect its middle and preserve visible gaps.
        popup.locator('[data-trend-range114="0"]').click()
        assert popup.locator(".hem-trend-gap114").count() == 1
        gap_t = START + 41 * 3600
        chart.evaluate("""(e,t)=>{
          const m=card._averageDialog105.model114,r=e.getBoundingClientRect();
          e.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerType:'mouse',isPrimary:true,
            clientX:r.x+(m.left+(m.right-m.left)*(t-m.start)/(m.end-m.start))*r.width/m.width,clientY:r.y+50}));
        }""", gap_t)
        assert popup.locator("[data-trend-value114]").inner_text() == "—"
        assert "No recorded sample" in popup.locator("[data-trend-label114]").inner_text()
        chart.focus()
        chart.press("ArrowRight")
        assert popup.locator("[data-trend-value114]").get_attribute("data-sample-time114")
        popup.locator('[data-hem-source105="sensor.temp_a"]').click()
        assert page.evaluate("info") == []
        assert page.evaluate("card._averageDialog105.entity122") == "sensor.temp_a"
        popup.locator('[data-open-entity122="sensor.temp_a"]').click()
        assert page.evaluate("info") == ["sensor.temp_a"]
        assert popup.count() == 0
        assert page.evaluate("calls") == []
        trigger.click()
        popup.wait_for(state="visible")

        screenshot_dir = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
        if screenshot_dir:
            Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
        for width, theme, language in ((590, "dark", "en"), (390, "dark", "el"),
                                       (320, "light", "de")):
            page.set_viewport_size({"width": width, "height": 900})
            page.evaluate("""({theme,language})=>{
              const light=theme==='light',s=document.documentElement.style;
              s.setProperty('--primary-text-color',light?'#213047':'#e9edf4');
              s.setProperty('--secondary-text-color',light?'#5b6c81':'#a5b2c4');
              s.setProperty('--card-background-color',light?'#fff':'#202830');
              s.setProperty('--divider-color',light?'#dce4ed':'#3b4654');
              document.body.style.background=light?'#eef3f8':'#111';
              card._hass={...card._hass,language};card._refreshAverage105(true);
            }""", {"theme": theme, "language": language})
            page.wait_for_timeout(60)
            bounds = popup.bounding_box()
            assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width + 1
            assert popup.evaluate("e=>e.scrollWidth<=e.clientWidth+1"), "Trend panel overflowed horizontally"
            assert chart.is_visible()
            assert chart.evaluate("e=>getComputedStyle(e).touchAction") == "pan-y"
            expected_title = {"en": "Temperature", "de": "Temperatur", "el": "Θερμοκρασία"}[language]
            expected_heading = {"en": "Average trend", "de": "Mittelwertverlauf", "el": "Τάση μέσου όρου"}[language]
            expected_close = {"en": "Close trend", "de": "Verlauf schließen", "el": "Κλείσιμο τάσης"}[language]
            assert popup.locator(".hem-average-summary105 strong").inner_text() == expected_title
            assert popup.locator(".hem-avg-head105>strong").inner_text() == expected_heading
            assert popup.get_attribute("aria-label") == expected_heading
            assert popup.locator("[data-close-avg105]").get_attribute("aria-label") == expected_close
            if screenshot_dir:
                page.screenshot(path=str(Path(screenshot_dir) / f"beta114-trend-{width}-{theme}.png"))
        # One value and empty history keep sources usable without invented data.
        page.evaluate("""()=>{
          const value=card._hass.states['sensor.hem'].attributes.dashboard.rooms[0].environment.measurement_evidence.temperature;
          value.trend=[{t:1793520000,v:0}];card._averageDialog105.view114={range:0,end:null,cursor:null};
          card._refreshAverage105(true);
        }""")
        assert popup.locator(".hem-trend-sample114").count() == 1
        assert popup.locator("[data-trend-value114]").inner_text() == "0"
        page.evaluate("""()=>{
          card._hass.states['sensor.hem'].attributes.dashboard.rooms[0].environment.measurement_evidence.temperature.trend=[];
          card._refreshAverage105(true);
        }""")
        assert popup.locator("[data-trend-chart114]").count() == 0
        assert popup.locator(".hem-avg-collect105").is_visible()
        assert popup.locator("[data-trend-value114]").inner_text() == "—"
        # Contributor identity changing must close the prior mean's history.
        page.evaluate("""()=>{
          const value=card._hass.states['sensor.hem'].attributes.dashboard.rooms[0].environment.measurement_evidence.temperature;
          value.source_ids=['sensor.temp_a'];value.source_count=1;card._refreshAverage105(true);
        }""")
        assert popup.count() == 0
        assert page.evaluate("calls") == []
        assert not errors, errors
        browser.close()
    print("BETA114_TREND_MOUSE_TOUCH_KEYBOARD_STABILITY_RESPONSIVE=PASS")


if __name__ == "__main__":
    states = fixture()
    subprocess.run(["node", "-e", NODE_CHECKS, str(CARD)],
                   input=json.dumps(states), text=True, check=True)
    if "--logic-only" not in sys.argv:
        browser_checks(deepcopy(states))
