"""Weather chips keep a visible leading glyph at every supported card width.

The short FROST warning exposed an unsupported MDI name: HA reserved its icon
box but rendered no glyph. The offline fixture intentionally leaves unknown
icon names blank, unlike older generic-icon fixtures. The supported identifier
is documented at https://pictogrammers.com/library/mdi/icon/weather-cloudy-alert/.
Node checks the production chip renderer; Chromium checks visible SVG content,
compact layout, the native tooltip, keyboard/click opening and pinned details.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/home-environment-manager-card.js"
SOURCE = "binary_sensor.frost_warning"
DESCRIPTION = "Es tritt leichter Frost zwischen 0 °C und -4 °C auf."


def fixture():
    outdoor = {
        "status": "unsafe",
        "weather": [{"condition": "partlycloudy", "temperature_c": 2.5, "wind_kmh": 7}],
        "readings": [{"metric": "aqi", "value": 51, "unit": "US AQI", "available": True}],
        "blockers": [{"code": "weather_temperature_low", "value": 2.6}],
        "warnings": [{"entity_id": SOURCE, "name": "Weather warning", "active": True}],
    }
    return {
        SOURCE: {"state": "on", "attributes": {
            "friendly_name": "Weather warning", "event": "FROST", "description": DESCRIPTION}},
        "sensor.hem": {"state": "ready", "attributes": {
            "warning_sources": [SOURCE], "dashboard": {
                "version": 1, "summary": {"safe": 0, "attention": 0, "unknown": 0},
                "outdoor": outdoor, "rooms": []}}},
    }


NODE_CHECKS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');
const card=Object.create(Card.prototype);
card._hass={language:'el',states:input.states,localize:()=>undefined};
card._config={entity:'sensor.hem'};
const warning=input.states['sensor.hem'].attributes.dashboard.outdoor.warnings[0];
const supported='mdi:weather-cloudy-alert';
const before=JSON.stringify(card._hass.states);
for(const [item,interactive] of [[warning,true],[{...warning,entity_id:'sensor.missing_warning'},false]]){
  const html=card._weatherChip101(item);
  const icons=[...html.matchAll(/<ha-icon[^>]*\bicon="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(icons[0],supported,'A missing MDI glyph leaves an empty leading icon slot');
  assert.ok(!html.includes('mdi:weather-alert"'));
  assert.equal(html.includes('data-wx-open103='),interactive);
  if(interactive){
    assert.match(html,/<button type="button"/);
    assert.match(html,/aria-label="FROST/);
    assert.match(html,/class="hem-wx-chip-text103">FROST<\/span>/);
    assert.ok(html.includes(input.description),'Native warning tooltip lost its detail');
    assert.equal(icons[1],'mdi:information-outline');
  }
}
assert.equal(JSON.stringify(card._hass.states),before,'Rendering mutated source evidence');
console.log('WEATHER_WARNING_SUPPORTED_GLYPH_AND_NATIVE_DETAILS=PASS');
"""


ICON_FIXTURE = r"""() => {
  const glyphs={
    'mdi:weather-cloudy-alert':'<path d="M6 19a5 5 0 0 1 0-10 6.5 6.5 0 0 1 12.5 2A4 4 0 0 1 19 19H6Z"/><path d="M12 9v4m0 2v1"/>',
    'mdi:information-outline':'<circle cx="12" cy="12" r="9"/><path d="M12 10v7m0-10v1"/>',
    'mdi:close':'<path d="m6 6 12 12M6 18 18 6"/>',
    'mdi:open-in-new':'<path d="M14 3h7v7M10 14 21 3M10 3H3v18h18v-7"/>',
  };
  customElements.define('ha-icon',class extends HTMLElement{
    static get observedAttributes(){return ['icon'];}
    constructor(){super();this.attachShadow({mode:'open'});}
    connectedCallback(){this.draw();}
    attributeChangedCallback(){this.draw();}
    draw(){
      const glyph=glyphs[this.getAttribute('icon')];
      this.shadowRoot.innerHTML='<style>:host{display:inline-flex;align-items:center;justify-content:center;'+
        'vertical-align:middle;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px)}'+
        'svg{width:100%;height:100%;display:block}</style>'+(glyph?
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">'+glyph+'</svg>':'');
    }
  });
}"""


def browser_checks(states):
    from playwright.sync_api import sync_playwright

    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
        shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome, "Chromium required"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content("""<!doctype html><html><head><style>
          *{box-sizing:border-box}body{margin:0;background:#111;color:#eee;font-family:Arial}
          :root{--primary-text-color:#eee;--secondary-text-color:#aaa;
            --card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}
          #frame{max-width:100%}
        </style></head><body><main id="frame"></main></body></html>""")
        page.evaluate(ICON_FIXTURE)
        page.add_script_tag(path=str(CARD))
        page.evaluate("""states=>{
          window.calls=[];window.info=[];
          window.card=document.createElement('home-environment-manager-card');
          document.getElementById('frame').append(card);
          card.addEventListener('hass-more-info',e=>info.push(e.detail.entityId));
          card._hass={language:'el',states,localize:()=>undefined,
            callService:(...args)=>{calls.push(args);throw Error('Display sent a device command')}};
          card._config={entity:'sensor.hem'};card._renderContent(true);
        }""", states)
        for viewport, card_width in ((1000, 800), (1000, 640), (1000, 590),
                                      (1000, 320), (390, 390), (320, 320)):
            page.set_viewport_size({"width": viewport, "height": 900})
            page.locator("#frame").evaluate("(node,width)=>node.style.width=width+'px'", card_width)
            chip = page.locator("button.hem-wx-chip103")
            report = chip.evaluate("""node=>{
              const box=node.getBoundingClientRect(),style=getComputedStyle(node);
              const icon=node.querySelector(':scope>ha-icon:first-child'),glyph=icon.shadowRoot.querySelector('svg');
              const i=icon.getBoundingClientRect(),g=glyph?.getBoundingClientRect();
              const row=node.closest('.hem-outside-details87'),r=row.getBoundingClientRect();
              const label=node.querySelector('.hem-wx-chip-text103'),text=label.getBoundingClientRect();
              return {icon:icon.getAttribute('icon'),glyphs:glyph?.querySelectorAll('path').length||0,
                width:box.width,iconWidth:i.width,glyphWidth:g?.width||0,glyphHeight:g?.height||0,
                inset:i.left-box.left,padding:parseFloat(style.paddingLeft)+parseFloat(style.borderLeftWidth),
                textVisible:getComputedStyle(label).display!=='none',textGap:text.left-i.right,
                rowClient:row.clientWidth,rowScroll:row.scrollWidth,
                left:box.left,right:box.right,rowLeft:r.left,rowRight:r.right};
            }""")
            assert report["icon"] == "mdi:weather-cloudy-alert" and report["glyphs"] > 0, report
            assert report["glyphWidth"] > 0 and report["glyphHeight"] > 0, report
            assert abs(report["inset"] - report["padding"]) < 1, report
            if report["textVisible"]:
                assert 0 <= report["textGap"] <= 6, report
            assert report["rowScroll"] <= report["rowClient"] + 2, report
            assert report["left"] >= report["rowLeft"] - 1, report
            assert report["right"] <= report["rowRight"] + 1, report
            assert DESCRIPTION in chip.get_attribute("title")
            assert "FROST" in chip.get_attribute("aria-label")
            chip.focus()
            chip.press("Enter")
            popup = page.locator(".hem-wx-dialog103")
            popup.wait_for(state="visible")
            assert popup.get_attribute("popover") == "manual"
            assert DESCRIPTION in popup.inner_text()
            dialog_icon = popup.locator(".hem-wx-head103 strong > ha-icon")
            assert dialog_icon.get_attribute("icon") == "mdi:weather-cloudy-alert"
            assert dialog_icon.locator("svg path").count() > 0
            box = popup.bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= viewport, box
            assert box["y"] >= 0 and box["y"] + box["height"] <= 900, box
            popup.press("Escape")
            assert popup.count() == 0
            chip.click()
            popup.wait_for(state="visible")
            popup.locator("[data-wx-close103]").click()
            assert popup.count() == 0
        chip.press("Space")
        popup.wait_for(state="visible")
        popup.locator("[data-wx-native103]").click()
        assert page.evaluate("info") == [SOURCE]
        assert page.evaluate("calls") == []
        assert not errors, errors
        browser.close()
    print("WEATHER_WARNING_VISIBLE_GLYPH_RESPONSIVE_KEYBOARD_AND_DETAILS=PASS")


if __name__ == "__main__":
    states = fixture()
    result = subprocess.run(["node", "-e", NODE_CHECKS, str(CARD)],
        input=json.dumps({"states": states, "description": DESCRIPTION}), text=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    if "--logic-only" not in sys.argv:
        browser_checks(states)
