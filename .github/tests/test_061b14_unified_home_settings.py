"""Unified Home and room HEM settings, exact-device writes, and Options lifecycle.

Runs against the production card in Chromium with mocked HA transports.
No Home Assistant configuration or actual hardware is modified.
"""
from __future__ import annotations
from pathlib import Path
import runpy
import os
import shutil

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
room = runpy.run_path(str(ROOT / ".github/tests/test_beta114_room_settings.py"))
base = runpy.run_path(str(ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"))
chrome = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert chrome, "Chromium is required for HEM settings verification"

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=chrome, headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 390, "height": 950})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content("""<!doctype html><html><head><style>
        body{margin:0;font:14px Arial;color:#eee;background:#111;
        --card-background-color:#202830;--secondary-background-color:#293440;
        --divider-color:#475665;--primary-color:#03a9f4;
        --primary-text-color:#eef2f6;--secondary-text-color:#b4bfca}
        </style></head><body></body></html>""")
    page.evaluate(base["icon_fixture"]())
    page.add_script_tag(path=str(CARD))
    states = base["fixture_definitions"]()["states"]
    rooms = states["sensor.hem"]["attributes"]["dashboard"]["rooms"]
    states["sensor.hem"]["attributes"]["dashboard"]["rooms"] = rooms[:2]
    page.evaluate(room["SETUP"], {"states": states, "form": room["FORM"], "native": False})
    page.evaluate(r"""() => {
        card._homeDeviceId="home-device";
        card._hass.entities["sensor.hem"].device_id="home-device";
        card._hass.connection={};
        card._hass.states["number.home_timeout"]={
          state:"35",attributes:{friendly_name:"Home arrival timeout",min:1,max:120,step:1}
        };
        card._hass.states["select.home_language"]={
          state:"auto",attributes:{friendly_name:"Home announcement language",options:["auto","el","de"]}
        };
        card._hass.states["number.bedroom_timeout"]={
          state:"15",attributes:{friendly_name:"Foreign room timeout",min:1,max:120,step:1}
        };
        card._hass.states["switch.foreign_entry"]={
          state:"on",attributes:{friendly_name:"Foreign entry"}
        };
        window.homeRegistry=[
          {entity_id:"number.home_timeout",device_id:"home-device",config_entry_id:"entry0",
           platform:"environment_manager",unique_id:"entry0_arrival_preparation_timeout"},
          {entity_id:"select.home_language",device_id:"home-device",config_entry_id:"entry0",
           platform:"environment_manager",unique_id:"entry0_home_language"},
          {entity_id:"number.bedroom_timeout",device_id:"bed-device",config_entry_id:"entry0",
           platform:"environment_manager",unique_id:"entry0_area_room1_timeout"},
          {entity_id:"switch.foreign_entry",device_id:"home-device",config_entry_id:"other",
           platform:"environment_manager",unique_id:"other_home_switch"}
        ];
        window.homeForm={
          type:"form",step_id:"setup_general",flow_id:"optionsHOME",handler:"entry0",
          errors:{},data_schema:[
            {name:"weather_entities",default:["weather.home"],selector:{
              select:{multiple:true,options:[
                {value:"weather.home",label:"Weather home"},
                {value:"weather.second",label:"Weather second"}]}}},
            {name:"general_home_policy",default:"any_home",selector:{
              select:{multiple:false,options:[
                {value:"any_home",label:"Any home"},{value:"all_home",label:"All home"}]}}},
            {name:"general_away_cooldown_minutes",default:10,selector:{
              number:{min:0,max:240,step:1,unit_of_measurement:"min"}}},
            {name:"pollen_avoid_ventilation",default:false,selector:{boolean:{}}},
            {name:"tts_engine",default:"tts.piper",selector:{
              select:{options:["tts.piper","tts.other"]}}}
          ]
        };
        window.homeCalls=[];
        window.nativeCalls=[];
        card._hass.callService=(...args)=>{nativeCalls.push(args);return Promise.resolve();};
        card._hass.callWS=async request=>{
          if(request.type==="config/entity_registry/list")return homeRegistry;
          throw Error("Unexpected websocket operation");
        };
        card._hass.callApi=async (method,path,data)=>{
          homeCalls.push({method,path,data});
          if(method==="DELETE")return {};
          if(path==="config/config_entries/options/flow")return {
            type:"menu",handler:"entry0",flow_id:"optionsHOME",
            menu_options:["choose_rooms","edit_room_room0","general_settings"]
          };
          if(data?.next_step_id==="general_settings")return homeForm;
          if(method==="POST" && data?.weather_entities)return {
            type:"create_entry",flow_id:"optionsHOME"
          };
          throw Error("Unknown options call "+path);
        };
        card._renderContent(true);
    }""")
    # Verify the card's Home gear opens the complete settings dialog.
    assert page.evaluate("Boolean(card.shadowRoot.querySelector('[data-edit-home]:not([disabled])'))")
    page.evaluate("card.shadowRoot.querySelector('[data-edit-home]').click()")
    page.wait_for_function("card._homeSettingsDialog128?.fullRegistry127?.length===4")
    dialog = page.locator("dialog.hem-home-options128")
    expect(dialog).to_be_visible()
    assert page.evaluate("homeCalls.some(c=>c.data?.next_step_id==='general_settings')")
    assert dialog.locator("[data-hem-home-field128]").count() == 5
    assert dialog.locator('[data-hem-home-category128="presence"]').count() == 1
    assert dialog.locator('[data-hem-home-category128="weather"]').count() == 1
    assert dialog.locator('[data-hem-home-category128="alerts"]').count() == 1
    assert dialog.locator('[data-hem-full-row127="number.home_timeout"]').count() == 1
    assert dialog.locator('[data-hem-full-row127="select.home_language"]').count() == 1
    assert dialog.locator('[data-hem-full-row127="number.bedroom_timeout"]').count() == 0
    assert dialog.locator('[data-hem-full-row127="switch.foreign_entry"]').count() == 0
    # All draft/native settings share one top-level category each.
    assert dialog.locator('[data-hem-home-form-groups128] > details').count() == 4
    assert dialog.locator('[data-hem-home-category128="other"]').count() == 0
    assert dialog.locator('[data-hem-full-category127="presence"]').count() == 0
    assert dialog.locator('[data-hem-home-category128="presence"] [data-hem-home-field128="general_home_policy"]').count()==1
    assert dialog.locator('[data-hem-home-category128="presence"] [data-hem-full-row127="number.home_timeout"]').count()==1
    assert dialog.locator('[data-hem-home-category128="alerts"] [data-hem-full-row127="select.home_language"]').count()==1

    dialog.locator('[data-hem-home-category128="weather"] > summary').click()
    dialog.locator('[data-hem-home-input128="weather_entities"][value="weather.second"]').check()
    dialog.locator('[data-hem-home-category128="presence"] > summary').click()
    dialog.locator('[data-hem-home-input128="general_home_policy"]').select_option("all_home")
    dialog.locator('[data-hem-home-input128="general_away_cooldown_minutes"]').fill("23")
    dialog.locator('[data-hem-home-category128="targets"] > summary').click()
    dialog.locator('[data-hem-home-input128="pollen_avoid_ventilation"]').check()
    # A native HA refresh must NOT replace unsaved draft fields or create
    # a second category containing the same controls.
    page.evaluate("card._renderContent(true)")
    assert dialog.locator('[data-hem-home-input128="general_home_policy"]').input_value()=="all_home"
    assert dialog.locator('[data-hem-home-input128="general_away_cooldown_minutes"]').input_value()=="23"
    assert dialog.locator('[data-hem-home-input128="weather_entities"][value="weather.second"]').is_checked()
    assert dialog.locator('[data-hem-home-form-groups128] > details').count() == 4
    assert dialog.locator('[data-hem-full-row127="number.home_timeout"]').count()==1
    assert page.evaluate("nativeCalls.length") == 0
    expect(dialog.locator('[data-hem-home-save128]')).to_be_enabled()
    dialog.locator('[data-hem-home-save128]').click()
    page.wait_for_function("card._homeSettingsDialog128?.finished===true")
    saved = page.evaluate("homeCalls.filter(c=>c.data?.weather_entities).at(-1).data")
    assert saved == {
      "weather_entities":["weather.home","weather.second"],
      "general_home_policy":"all_home","general_away_cooldown_minutes":23,
      "pollen_avoid_ventilation":True,"tts_engine":"tts.piper"
    }, saved
    assert page.evaluate("nativeCalls.length") == 0
    dialog.locator('[data-hem-home-close128]').last.click()
    expect(dialog).to_have_count(0)
    assert page.evaluate("homeCalls.filter(c=>c.method==='DELETE').length") == 0

    # Reopening uses fresh flow data, and registry controls are immediately writable.
    assert page.evaluate("card._openHomeSettings128()") is True
    page.wait_for_function("card._homeSettingsDialog128?.fullRegistry127?.length===4")
    dialog=page.locator("dialog.hem-home-options128")
    dialog.locator('[data-hem-full-category127="presence"] > summary').click()
    dialog.locator('[data-hem-full-value127="number.home_timeout"]').fill("45")
    dialog.locator('[data-hem-full-apply127="number.home_timeout"]').click()
    page.wait_for_function("nativeCalls.length===1")
    assert page.evaluate("nativeCalls[0]") == [
        "number","set_value",{"entity_id":"number.home_timeout","value":45}
    ]
    page.evaluate("card._renderContent(true)")
    expect(dialog).to_be_visible()
    assert dialog.locator('[data-hem-full-category127="presence"]').get_attribute("open") is not None
    dialog.locator('[data-hem-home-close128]').last.click()
    page.wait_for_function("homeCalls.some(c=>c.method==='DELETE')")

    # No non-admin access or guessed device registry owner.
    page.evaluate("card._hass.user.is_admin=false")
    assert page.evaluate("card._openHomeSettings128()") is False
    page.evaluate("card._hass.user.is_admin=true;card._homeDeviceId='foreign-device'")
    assert page.evaluate("card._openHomeSettings128()") is False

    assert not errors, errors
    browser.close()
print("PASS: Home global Options and exact-device native settings use unified secure accordions")
