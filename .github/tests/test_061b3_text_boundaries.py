"""0.6.1b3: protect actual text/value geometry in compact translated cards.

Runs the production card with local HA transport and real HA-sized icon boxes.
The numeric text Range checks also detect the old anonymous flex-text bug;
checking only the outer chip's width would miss its clipped temperature.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
import shutil


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
WARNING = "binary_sensor.frost_warning"
AQI = "sensor.outdoor_aqi"


def fixture(language):
    base = runpy.run_path(str(ROOT / ".github/tests/test_beta122_card_details.py"))["fixture"]()
    states, rooms = {}, []
    names = ["Badezimmer", "Gästezimmer", "Küche", "Schlafzimmer", {
        "el": "Wohnzimmer · Καθιστικό και τραπεζαρία με μεγάλη ονομασία δωματίου",
        "en": "Living room and dining area with an unusually long room name",
        "de": "Wohnzimmer und Essbereich mit außergewöhnlich langem Raumnamen",
    }[language]]
    for index, name in enumerate(names):
        room = deepcopy(base["room"])
        room.update(area_id=f"room{index}", name=name,
                    status="safe" if index == 4 else "unknown", high_count=0)
        values = [("temperature", 19.4 + index / 10, "°C"), ("humidity", 56.9, "%")]
        if index == 4:
            values += [("pm25", 14., "µg/m³"), ("aqi", 13., "US AQI")]
        room["readings"] = []
        for metric, value, unit in values:
            entity = f"sensor.room{index}_{metric}"
            room["readings"].append({"metric": metric, "value": value, "unit": unit,
                "name": metric, "available": True, "entity_id": entity})
            states[entity] = {"state": str(value), "attributes": {
                "friendly_name": f"{name} {metric}", "unit_of_measurement": unit}}
        plan = room["environment"]["climate_plan"]
        plan["temperature_c"] = values[0][1]
        plan["equipment_plan"]["humidity"]["measured_rh"] = 56.9
        rooms.append(room)
    outdoor = {"status": "unsafe", "weather": [{"condition": "partlycloudy",
        "temperature_c": 3.9, "wind_kmh": 6.}], "readings": [{"metric": "aqi",
        "value": 71., "unit": "US AQI", "available": True, "entity_id": AQI}],
        "blockers": [{"code": "weather_cold", "value": "4°C"},
                     {"code": "active_warning", "label": "Frost warning"}],
        "warnings": [{"entity_id": WARNING, "name": "Frost warning", "active": True}]}
    states[AQI] = {"state": "71", "attributes": {
        "friendly_name": "Outside air quality", "unit_of_measurement": "US AQI"}}
    states[WARNING] = {"state": "on", "attributes": {"event": "FROST",
        "description": "Frost warning for the full local area, including sheltered roads and gardens.",
        "severity": "moderate", "friendly_name": "Frost warning"}}
    states["sensor.hem"] = {"state": "ready", "attributes": {"warning_sources": [WARNING],
        "dashboard": {"version": 1, "rooms": rooms, "summary": {"safe": 1, "attention": 0,
        "unknown": 4}, "outdoor": outdoor}}}
    return {"language": language, "states": states}


SETUP = r"""data => {
  window.calls=[];window.info=[];window.card=document.createElement('home-environment-manager-card');
  document.querySelector('main').append(card);
  card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
  card.setConfig({entity:'sensor.hem'});
  card.hass={language:data.language,states:data.states,entities:{},localize:()=>undefined,
    config:{time_zone:'UTC'},connection:{},callService:(...args)=>{calls.push(args);return Promise.resolve();},
    callWS:async request=>{
      if(request.type==='config/device_registry/list')return [];
      if(request.type==='history/history_during_period'){
        const now=Date.now()/1000;return {[request.entity_ids[0]]:[{s:'70',lu:now-120},{s:'71',lu:now-60}]};
      }
      throw Error('Unexpected mocked HA request: '+request.type);
    }};
  window.refresh061b3=()=>{
    const states=structuredClone(card._hass.states),root=states['sensor.hem'];
    root.attributes.dashboard_revision=(root.attributes.dashboard_revision||0)+1;
    root.attributes.dashboard.outdoor.blockers[0].value='-12,7°C';
    root.attributes.dashboard.outdoor.blockers.splice(1,0,{code:'weather_wind',value:'123,4 km/h'});
    root.attributes.dashboard.outdoor.readings.push({metric:'pm25',value:14.,unit:'µg/m³',
      available:true,entity_id:'sensor.outdoor_pm25'});
    states['sensor.outdoor_pm25']={state:'14',attributes:{
      friendly_name:'Outside fine particles',unit_of_measurement:'µg/m³'}};
    Object.assign(root.attributes.dashboard.outdoor.weather[0],{
      condition:'lightning-rainy',temperature_c:-12.7,humidity:99.9,wind_kmh:123.4});
    states['binary_sensor.frost_warning'].attributes.event=
      'FROST - a long warning area name that remains available in the full details';
    card.setConfig({entity:'sensor.hem',title:'Home Environment Manager · '+
      'Καθιστικό και τραπεζαρία με αναλυτικές ενδείξεις περιβάλλοντος '.repeat(3)});
    card.hass={...card._hass,states};
  };
}"""


REPORT = r"""() => {
  const root=card.shadowRoot,box=node=>{
    const r=node.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};
  const visible=node=>node&&node.getClientRects().length&&getComputedStyle(node).visibility!=='hidden';
  const inside=(a,b)=>a.left>=b.left-1&&a.right<=b.right+1;
  // Find the actual glyph range, including values rendered as an anonymous
  // text node beside an icon. No dependency on the new split-label markup.
  const sample=(node,needle,label)=>{
    if(!node)return {label,missing:true};
    const text=node.textContent,start=text.indexOf(needle);
    if(start<0)return {label,missing:true,text,needle};
    const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT),range=document.createRange();
    let current,offset=0,begun=false;
    while(current=walker.nextNode()){
      const end=offset+current.length;
      if(!begun&&start<end){range.setStart(current,start-offset);begun=true;}
      if(begun&&start+needle.length<=end){range.setEnd(current,start+needle.length-offset);break;}
      offset=end;
    }
    const rects=[...range.getClientRects()].filter(r=>r.width>0).map(r=>({left:r.left,right:r.right}));
    const clipped=[];
    for(let parent=range.startContainer.parentElement;parent;parent=parent.parentElement){
      if(!inside(rects[0]||{left:-Infinity,right:Infinity},box(parent))||
          rects.some(r=>!inside(r,box(parent))))clipped.push(parent.className||parent.tagName);
      if(parent.matches('ha-card'))break;
    }
    return {label,text:needle,visible:Boolean(visible(node)),rects,box:box(node),clipped};
  };
  const cold=root.querySelector('.outside-alerts .reason'),outside=root.querySelector('.outside');
  const value=card._hass.states['sensor.hem'].attributes.dashboard.outdoor.blockers[0].value;
  const samples=[sample(cold,value,'cold blocker'),
    sample(root.querySelector('.weather-line strong'),card._format(
      card._hass.states['sensor.hem'].attributes.dashboard.outdoor.weather[0].temperature_c)+'°C','weather temperature')];
  for(const reading of card._hass.states['sensor.hem'].attributes.dashboard.outdoor.readings){
    const chip=root.querySelector('.out-chip[data-hem-source105="'+reading.entity_id+'"]');
    samples.push(sample(chip?.querySelector('b'),card._format(reading.value),'outdoor '+reading.metric+' value'),
      sample(chip?.querySelector('small'),reading.unit,'outdoor '+reading.metric+' unit'));
  }
  const weather=card._hass.states['sensor.hem'].attributes.dashboard.outdoor.weather[0];
  for(const [key,unit] of [['humidity','%'],['wind_kmh',' km/h']]){
    if(typeof weather[key]==='number')samples.push(sample(root.querySelector('.hem-weather-extras123'),
      card._format(weather[key])+unit,'weather '+key));
  }
  for(const node of root.querySelectorAll('.hem-outside-blocker-value123')){
    samples.push(sample(node,node.textContent.trim(),'measured blocker'));
  }
  for(const node of root.querySelectorAll('.hem-room-metric-value107,.hem-room-metric-unit107,.hem-overview-stat87 b,.hem-overview-title87 strong')){
    if(visible(node))samples.push(sample(node,node.textContent.trim(),node.className||'room count'));
  }
  const containers=[...root.querySelectorAll('ha-card,.card-heading,.outside,.outdoor-head,.hem-outside-details87,.hem-overview87,.hem-room-glance87,footer')]
    .filter(visible).map(node=>({name:node.className||node.tagName,box:box(node),client:node.clientWidth,
      scroll:node.scrollWidth,overflow:getComputedStyle(node).overflowX}));
  const labels=[...root.querySelectorAll('.card-heading h2,.outside-title,.hem-weather-condition123,'+
      '.hem-outside-blocker-label123,.hem-outside-metric-label123,.hem-overview-title87>b,'+
      '.hem-room-name87,.hem-overview-stat87 small')].filter(visible)
    .map(node=>({text:node.textContent,box:box(node),parent:box(node.parentElement),
      title:node.title||node.parentElement.title,ellipsis:getComputedStyle(node).textOverflow,
      client:node.clientWidth,scroll:node.scrollWidth}));
  return {viewport:innerWidth,pageScroll:document.documentElement.scrollWidth,
    frame:box(document.querySelector('main')),outside:box(outside),
    head:box(root.querySelector('.outdoor-head')),row:box(root.querySelector('.hem-outside-details87')),
    coldTitle:cold?.title,coldAria:cold?.getAttribute('aria-label'),samples,containers,labels};
}"""


def settle(page):
    page.wait_for_function("card._lastState===card._hass.states['sensor.hem']")
    page.evaluate("async()=>{await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));}")


def assert_layout(report):
    assert report["pageScroll"] <= report["viewport"] + 1, report
    assert report["row"]["height"] <= 29, report
    assert report["head"]["height"] <= 32, report
    assert report["row"]["top"] >= report["head"]["bottom"] - 1, report
    assert report["outside"]["height"] <= 85, report
    assert report["samples"][0]["text"] in report["coldTitle"], report
    assert report["samples"][0]["text"] in report["coldAria"], report
    for sample in report["samples"]:
        assert not sample.get("missing"), sample
        assert sample["visible"] and sample["rects"] and not sample["clipped"], sample
    for container in report["containers"]:
        assert container["scroll"] <= container["client"] + 1, container
        assert container["box"]["left"] >= report["frame"]["left"] - 1, container
        assert container["box"]["right"] <= report["frame"]["right"] + 1, container
        assert container["overflow"] not in ("auto", "scroll"), container
    for label in report["labels"]:
        assert label["box"]["left"] >= label["parent"]["left"] - 1, label
        assert label["box"]["right"] <= label["parent"]["right"] + 1, label
        if label["scroll"] > label["client"] + 1:
            assert label["ellipsis"] == "ellipsis" and label["text"] in label["title"], label


def run():
    from playwright.sync_api import expect, sync_playwright
    executable = os.environ.get("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert executable, "Chromium required for text boundary regression"
    shots = Path(os.environ["HEM_TEST_SCREENSHOT_DIR"]) if os.environ.get("HEM_TEST_SCREENSHOT_DIR") else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    icons = runpy.run_path(str(ROOT / ".github/tests/test_061b1_room_fold.py"))["icon_fixture"]()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page, current, report = None, "setup", None
        try:
            for language in ("el", "en", "de"):
                page = browser.new_page(viewport={"width": 665, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.set_content("""<!doctype html><html><head><style>
                  *{box-sizing:border-box}body{margin:8px;background:#111;color:#eee;font-family:Arial,sans-serif;
                    --primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;
                    --card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}
                  main{width:625px;max-width:100%;margin:0 auto}home-environment-manager-card{display:block}
                  </style></head><body><main></main></body></html>""")
                page.evaluate(icons)
                page.add_script_tag(path=str(CARD))
                page.evaluate(SETUP, fixture(language))
                for viewport, card_width, label in ((665,625,"reported"),(375,359,"mobile"),
                        (320,304,"narrow"),(1024,760,"desktop"),(1024,320,"narrow-column")):
                    current = f"{language}-{label}"
                    page.set_viewport_size({"width": viewport, "height": 1000})
                    page.locator("main").evaluate("(node,width)=>node.style.width=width+'px'", card_width)
                    settle(page)
                    report = page.evaluate(REPORT)
                    assert_layout(report)
                    if shots:
                        page.screenshot(path=str(shots / f"061b3-text-{current}.png"), full_page=True)
                # Live refresh must retain the full negative value and the
                # complete warning text, even in a narrow desktop column.
                page.evaluate("refresh061b3()")
                settle(page)
                report = page.evaluate(REPORT)
                assert_layout(report)
                warning = page.locator(f'[data-wx-open103="{WARNING}"]')
                assert "full details" in warning.get_attribute("title")
                warning.click()
                dialog = page.locator(".hem-wx-dialog103")
                expect(dialog).to_be_visible()
                assert "full details" in dialog.inner_text()
                dialog.locator(f'[data-wx-native103="{WARNING}"]').click()
                expect(dialog).to_have_count(0)
                assert page.evaluate("info.at(-1)") == WARNING
                page.locator(f'.out-chip[data-hem-source105="{AQI}"]').click()
                history = page.locator(".hem-avg-dialog105")
                expect(history).to_be_visible()
                history.locator(f'[data-open-entity122="{AQI}"]').click()
                expect(history).to_have_count(0)
                assert page.evaluate("info.at(-1)") == AQI
                assert page.evaluate("calls") == [], "Layout actions must not control equipment"
                assert not errors, errors
                print(f"PASS: {language} text bounds, five viewport/column layouts, live values and source actions")
                page.close()
        except Exception:
            if page and shots:
                page.screenshot(path=str(shots / f"061b3-failure-{current}.png"), full_page=True)
                (shots / f"061b3-failure-{current}.json").write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            raise
        finally:
            browser.close()
    print("HEM_061B3_TRANSLATED_TEXT_BOUNDARIES=PASS")


if __name__ == "__main__":
    run()
