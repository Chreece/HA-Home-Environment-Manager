"""v0.7.1: production card's unified contacts, data, disclosures and shade cues.

Chromium with an isolated Home Assistant snapshot; no physical commands.
"""
from copy import deepcopy
from pathlib import Path
import os
import runpy
import shutil

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
states = deepcopy(runpy.run_path(
    str(ROOT / ".github/tests/test_beta114_interactive_trends.py")
)["fixture"]())
room = states["sensor.hem"]["attributes"]["dashboard"]["rooms"][0]
room["status"] = "unknown"
room["readings"] = [v for v in room["readings"] if v["metric"] == "temperature"]
room["environment"]["measurement_evidence"].pop("humidity")
room["environment"]["climate_plan"]["temperature_c"] = 21.456
room["environment"]["moisture"] = {
    "status": "drying", "drying_potential_g_kg": 1.2,
    "outside_air_rh_when_warmed_percent": 42.0
}
room["windows"] = [{"entity_id":"binary_sensor.window", "name":"Balcony window", "opened":False}]
room["environment"]["door_context"] = {
    "boundary":"open", "eco_active":False,
    "contacts":[
        {"entity_id":"binary_sensor.fire", "health":"ok","kind":"fire","state":"open"},
        {"entity_id":"binary_sensor.door", "health":"ok","kind":"interior","state":"open"},
    ],
    "connections":[{"other_area":"hall","other_name":"Hall",
                    "state":"open","kind":"interior"}],
    "advisories":[{"code":"fire_door_open"},
                  {"code":"moisture_transfer_risk","related_area":"hall"}],
}
room["environment"]["shade_cooling"] = {
    "status":"cooling_hold", "close_reason":"closing_recommended",
    "selected_covers":["cover.roller"],
    "covers":{"cover.roller":"recent_close_hold"}
}
states["cover.roller"] = {"state":"open","attributes":{"friendly_name":"Living roller"}}
for entity, name in (("binary_sensor.window","Balcony window"),
                     ("binary_sensor.door","Living door"),
                     ("binary_sensor.fire","Fire door")):
    states[entity] = {"state":"on" if entity.endswith("door") or entity.endswith("fire") else "off",
                      "attributes":{"friendly_name":name}}

CHROME = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert CHROME, "Chromium is required"

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME, headless=True,
                                 args=["--no-sandbox", "--disable-dev-shm-usage"])
    for language, width in (("en",390),("el",320),("de",760)):
        page = browser.new_page(viewport={"width":width,"height":1000})
        errors = []
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.set_content('<style>body{margin:0;background:#202020;color:#eee;'
                         '--primary-text-color:#eee;--secondary-text-color:#bbb;'
                         '--card-background-color:#222;--secondary-background-color:#292929;'
                         '--primary-color:#03a9f4;--divider-color:#444}</style>')
        page.add_script_tag(path=str(CARD))
        page.evaluate(r"""({language,states})=>{
          window.calls=[];
          window.card=document.createElement('home-environment-manager-card');
          document.body.appendChild(card);
          card._config={entity:'sensor.hem'};
          card._hass={language,states,connection:{},user:{is_admin:true},
            config:{time_zone:'Europe/Berlin'},localize:()=>undefined,
            callWS:async()=>({}),callService:(...args)=>{calls.push(args);
              throw Error('Read-only test may not call services')}};
          card._renderContent(true);
        }""", {"language":language,"states":deepcopy(states)})
        row=page.locator('[data-room-fold87="living"]')
        assert row.count()==1
        assert "hem-room-partial" in row.get_attribute("class")
        row.locator('.hem-room-name87').click()
        expect(row.locator('.hem-room-missing071')).to_be_visible()
        assert page.evaluate("card._roomInputs071(card._dashboard105().rooms[0])")=={
            "temperature":True, "humidity":False}
        combined=row.locator('.hem-windows-doors071')
        assert combined.count()==1
        label=combined.locator('.hem-openings-heading071 .field-label').inner_text()
        assert label=={"en":"Windows & doors","de":"Fenster & Türen",
                       "el":"Παράθυρα & πόρτες"}[language], label
        assert combined.locator('.hem-room-door062').count()==1
        assert combined.locator('.window-list .window').count()==3
        assert combined.locator('.window-list .window small').count()==0
        assert combined.locator('.window-list .window ha-icon').count()==3
        info=combined.locator('.hem-door-head062 details.hem-context76')
        info.locator('summary').click()
        notes=info.locator('.hem-context-body76').inner_text()
        expected={"en":("Close the fire/safety door","Close the interior door"),
                  "de":("Brand-/Sicherheitstür schließen","Innentür schließen"),
                  "el":("Κλείσε την πόρτα πυρασφάλειας","Κλείσε την εσωτερική πόρτα")}[language]
        for reason in expected:
            assert reason in notes,notes

        physics=row.locator('details.hem-physics-fold105')
        assert physics.count()==1
        physics.locator(':scope > summary').click()
        metric=physics.locator('details.hem-science-line071').first
        expect(metric).to_be_visible()
        metric.locator(':scope > summary').click()
        assert metric.get_attribute("open") is not None
        note=metric.locator('.hem-science-inline071')
        expect(note).to_be_visible()
        assert note.evaluate("el=>getComputedStyle(el).position")=="static"
        assert note.evaluate("el=>el.closest('details.hem-science-line071')!==null")

        covers=row.locator('details.hem-covers-fold105')
        assert covers.count()==1
        assert covers.locator('.hem-cover-close071').count()==1
        assert covers.locator('.hem-cover-state105').count()==0
        covers.locator(':scope > summary').click()
        source=covers.locator('.hem-cover-source071')
        assert source.count()==1
        assert "Living roller" in source.inner_text()
        assert source.locator('ha-icon').count()==1
        disclosure=covers.locator('.shade-heading details.hem-context76')
        assert disclosure.count()==1
        assert disclosure.locator('.hem-context-body76').is_hidden()
        disclosure.locator('summary').click()
        expect(disclosure.locator('.hem-context-body76')).to_be_visible()

        page.evaluate("""() => {
          const room=card._hass.states['sensor.hem'].attributes.dashboard.rooms[0];
          room.readings=[{metric:'co2',value:1400,available:true,name:'CO2',unit:'ppm'}];
          room.environment.measurement_evidence={};
          room.environment.climate_plan.temperature_c=null;
          card._roomsExpanded87=new Set(['living']);
          card._renderContent(true);
        }""")
        assert "hem-room-unknown" in page.locator('[data-room-fold87="living"]').get_attribute("class")
        assert page.evaluate("card._roomInputs071(card._dashboard105().rooms[0])")=={
            "temperature":False,"humidity":False}
        assert page.evaluate("calls.length")==0
        assert not errors,errors
        page.close()
    browser.close()
print("HEM_071_ROOM_UI=PASS")
