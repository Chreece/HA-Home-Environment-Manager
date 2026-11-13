"""B12: a battery-powered offline TRV stays on the HEM card.

Chromium reproduces Home Assistant's unavailable-state attribute loss. Only
exact HEM climate/status registry pairs may restore the display: an unrelated
entity in the same room must not become a managed controller. Display must
not issue a native command or require a configured supply switch.
"""
from __future__ import annotations

from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"frontend/air-quality-advisor-card.js"
assert SOURCE.exists()
controller="entry_controller_battery_trv"
sources=["climate.zigbee_trv"]
attrs={
    "area_id":"bedroom","source_device_id":"physical_trv",
    "source_entity_ids":sources,
}
states={
    "climate.hem_valve":{"state":"unavailable","attributes":{}},
    "climate.zigbee_trv":{"state":"unavailable","attributes":{"friendly_name":"Bedroom Zigbee TRV"}},
    "sensor.hem_valve_status":{"state":"waiting_for_physical_device","attributes":{
        **attrs,"controller_id":controller,"control_method":"pid",
        "status_code":"waiting_for_physical_device",
        "status_reason_code":"native_source_unavailable",
        "native_sources_available":False,
        "native_primary_entity_id":"climate.zigbee_trv",
        "unavailable_source_entity_ids":sources,
    }},
    "select.hem_valve_heat":{"state":"pid","attributes":{
        **attrs,"settings_scope":"operating_mode",
        "operating_mode":"heat","setting_key":"control_mode",
        "options":["existing","automatic","pid","manual","off"],
    }},
    "switch.hem_errors":{"state":"on","attributes":{
        **attrs,"device_fault_role":"announce","setting_label":"Announce device errors",
        "native_error":{"status":"unavailable","unavailable_entities":sources},
    }},
}
registry={
    "climate.hem_valve":{
        "platform":"environment_manager","unique_id":controller+"_climate",
        "device_id":"logical_trv","config_entry_id":"hem_entry"},
    "sensor.hem_valve_status":{
        "platform":"environment_manager","unique_id":controller+"_control_status",
        "device_id":"logical_trv","config_entry_id":"hem_entry"},
}
room={"area_id":"bedroom","name":"Bedroom","status":"unknown",
      "environment":{"climate_plan":{"status":"unavailable"}}}

binary=shutil.which("chromium") or shutil.which("google-chrome")
assert binary,"Chromium is required"
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=binary,headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage"])
    page=browser.new_page(viewport={"width":420,"height":900})
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.set_content("<html><body></body></html>")
    page.add_script_tag(path=str(SOURCE))
    page.evaluate("""({states,registry,room})=>{
      window.calls=[];window.room=room;
      window.card=document.createElement('home-environment-manager-card');
      document.body.append(card);
      card._hass={language:'en',states,entities:registry,localize:()=>undefined,
        callService:(...args)=>{calls.push(args);return Promise.resolve();}};
      window.display=()=>{
        const devices=card._managedControllers('bedroom');
        card.shadowRoot.innerHTML=card._styles()+
          '<ha-card>'+card._controllerPanel(room)+'</ha-card>';
        return {count:devices.length,controller:devices[0]?.entityId,
          status:devices[0]?.climate?.state,
          methods:devices[0]?.operatingModes?.map(m=>m.mode)};
      };
    }""",{"states":states,"registry":registry,"room":room})
    result=page.evaluate("display()")
    assert result=={"count":1,"controller":"climate.hem_valve",
                    "status":"unavailable","methods":["heat"]},result
    html=page.locator(".managed-controllers")
    assert html.count()==1,html.count()
    offline=page.locator(".hem-physical-offline-b12")
    assert offline.count()==1,html.inner_text()
    assert "Physical device unavailable" in offline.inner_text()
    assert "climate.zigbee_trv" in offline.inner_text()
    assert page.locator("[data-hem-card-method129]").count()==1
    assert page.evaluate("calls.length")==0

    for language,phrase in [
        ("el","Μη διαθέσιμη φυσική συσκευή"),
        ("de","Physisches Gerät nicht verfügbar"),
        ("en","Physical device unavailable"),
    ]:
        page.evaluate("""lang=>{
          card._hass={...card._hass,language:lang,
            states:{...card._hass.states}};
        }""",language)
        assert page.evaluate("display().count")==1
        assert phrase in page.locator(".hem-physical-offline-b12").inner_text()
    assert page.evaluate("calls.length")==0

    # No registry proof: a foreign sensor must not acquire HEM settings.
    page.evaluate("""()=>{
       const reg={...card._hass.entities};
       delete reg['sensor.hem_valve_status'];
       card._hass={...card._hass,entities:reg,states:{...card._hass.states}};
    }""")
    assert page.evaluate("display().count")==0

    # A restored physical TRV and actual HEM climate use the usual path, no
    # phantom offline alert or duplicate controller.
    page.evaluate("""()=>{
      const states={...card._hass.states};
      states['climate.zigbee_trv']={state:'heat',attributes:{
        friendly_name:'Bedroom Zigbee TRV'}};
      states['climate.hem_valve']={state:'heat',attributes:{
        area_id:'bedroom',source_device_id:'physical_trv',
        source_entity_ids:['climate.zigbee_trv'],control_mode:'pid',
        supported_operating_modes:['heat'],selected_operating_mode:'heat'
      }};
      card._hass={...card._hass,states};
    }""")
    assert page.evaluate("display().count")==1
    assert page.locator(".hem-physical-offline-b12").count()==0
    assert page.evaluate("calls.length")==0
    assert not errors,errors
    browser.close()

print("HEM_B12_OFFLINE_BATTERY_TRV_RETAINED_EXACT_REGISTRY_NO_ACTUATION=PASS")
