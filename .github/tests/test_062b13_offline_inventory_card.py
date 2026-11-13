"""B13: reproduce the real offline Zigbee TRV / HACS-installed card failure.

The physical ZHA climate is unavailable, HEM's logical climate is unavailable
with *no* normal attributes, the HEM status sensor can also be unavailable,
and hass.entities (frontend registry) is absent. Source selection is supplied
only by HEM's authenticated, read-only dashboard snapshot. We additionally
verify the async snapshot/cache handoff, a healthy sibling, a missing logical
entity, recovery, EN/DE/EL copy, and zero physical service calls.
"""
from __future__ import annotations

from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"frontend/air-quality-advisor-card.js"
assert SOURCE.exists()
room={"area_id":"wohnzimmer","name":"Wohnzimmer",
      "environment":{"climate_plan":{"status":"unavailable"}}}
source="climate.wohnzimmer_trv"
cid="entry_controller_trv"
snapshot_trv={
    "controller_id":cid,"climate_entity_id":"climate.hem_trv",
    "area_id":"wohnzimmer","name":"Καθιστικό θερμοστάτης",
    "source_device_id":"zha_thermostat", "source_entity_ids":[source],
    "unavailable_source_entity_ids":[source],
    "control_mode":"pid","supported_operating_modes":["heat"],
    "selected_operating_mode":"heat","native_primary_entity_id":source,
    "status_code":"waiting_for_physical_device",
    "status_reason_code":"native_source_unavailable","upstream_power_switch":None,
}
states={
    "sensor.hem_recommendation":{"state":"idle","attributes":{
        "dashboard_api":"environment_manager/dashboard","dashboard_revision":7}},
    source:{"state":"unavailable","attributes":{
        "friendly_name":"Καθιστικό θερμοστάτης"}},
    "climate.hem_trv":{"state":"unavailable","attributes":{}},
    "sensor.hem_trv_status":{"state":"unavailable","attributes":{}},
    "climate.hem_purifier":{"state":"off","attributes":{
        "area_id":"wohnzimmer","source_entity_ids":["fan.mi_purifier"],
        "source_device_id":"purifier_physical","control_mode":"automatic",
        "supported_operating_modes":["fan_only"],
        "selected_operating_mode":"fan_only",
        "controller_status":{"status":"within_target_band"}}},
    "fan.mi_purifier":{"state":"off","attributes":{"friendly_name":"Mi Air Purifier"}},
    "select.hem_trv_heat":{"state":"pid","attributes":{
        "area_id":"wohnzimmer","source_entity_ids":[source],
        "source_device_id":"zha_thermostat","settings_scope":"operating_mode",
        "operating_mode":"heat","setting_key":"control_mode",
        "options":["existing","automatic","pid","manual","off"]}},
    "switch.hem_trv_error":{"state":"on","attributes":{
        "area_id":"wohnzimmer","source_entity_ids":[source],
        "source_device_id":"zha_thermostat","device_fault_role":"announce",
        "setting_label":"Announce device errors",
        "native_error":{"status":"unavailable","unavailable_entities":[source]}}},
}
with sync_playwright() as pw:
    browser=pw.chromium.launch(
        executable_path=shutil.which("chromium") or shutil.which("google-chrome"),
        headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
    page=browser.new_page(viewport={"width":420,"height":950})
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.set_content("<html><body></body></html>")
    page.add_script_tag(path=str(SOURCE))
    page.evaluate("""({states,room})=>{
      window.calls=[];window.room=room;
      window.card=document.createElement('home-environment-manager-card');
      document.body.append(card);
      card._config={entity:'sensor.hem_recommendation'};
      card._hass={language:'en',states,localize:()=>undefined,
          callService:(...args)=>{calls.push(args);return Promise.resolve();}};
      // hass.entities is intentionally UNDEFINED: this is the original bug.
      window.draw=()=>card.shadowRoot.innerHTML=card._styles()+
          '<ha-card>'+card._controllerPanel(room)+'</ha-card>';
    }""",{"states":states,"room":room})
    page.evaluate("draw()")
    assert page.locator(".managed-controller").count()==1, "Healthy purifier baseline"
    assert page.locator(".hem-physical-offline-b12").count()==0

    # Async WebSocket snapshot arrives after the original HA-state scan.
    page.evaluate("""row=>{
      card._dashboardEntity='sensor.hem_recommendation';
      card._dashboardData={version:1,rooms:[room],controllers:[row]};
      draw();
    }""",snapshot_trv)
    assert page.locator(".managed-controller").count()==2, (
        "WebSocket inventory must invalidate the prior per-room device cache")
    offline=page.locator(".hem-physical-offline-b12")
    assert offline.count()==1,page.locator(".managed-controllers").inner_text()
    assert source in offline.inner_text()
    assert "Physical device unavailable" in offline.inner_text()
    assert page.locator("[data-managed-climate93='climate.hem_trv']").count()==1
    assert page.locator("[data-device-error-announce]").count()==1
    assert page.locator("[data-hem-card-method129]").count()==1
    assert page.evaluate("calls.length")==0

    for locale,label in [("el","Μη διαθέσιμη φυσική συσκευή"),
                         ("de","Physisches Gerät nicht verfügbar"),
                         ("en","Physical device unavailable")]:
        page.evaluate("""loc=>{
          card._hass={...card._hass,language:loc,states:{...card._hass.states}};
          draw();
        }""",locale)
        assert label in page.locator(".hem-physical-offline-b12").inner_text()
        assert page.locator(".managed-controller").count()==2

    # Fully absent HEM facade state is still a registered offline controller.
    page.evaluate("""()=>{
      const states={...card._hass.states};
      delete states['climate.hem_trv'];
      card._hass={...card._hass,states};draw();
    }""")
    assert page.locator("[data-managed-climate93='climate.hem_trv']").count()==1
    assert page.locator(".hem-physical-offline-b12").count()==1

    # If no HEM facade was registered at all, show truthful, read-only
    # configured equipment rather than hiding it or inventing an entity ID.
    page.evaluate("""()=>{
      card._dashboardData={...card._dashboardData,controllers:[
        {...card._dashboardData.controllers[0],climate_entity_id:null}]};
      draw();
    }""")
    assert page.locator(".hem-physical-offline-b13").count()==1
    assert page.locator(".managed-controller").count()==2
    assert page.evaluate("calls.length")==0

    # When the ZHA TRV and genuine HEM facade recover, present ONE real
    # controller, not a duplicate synthesized display record.
    page.evaluate("""()=>{
      const states={...card._hass.states};
      states['climate.wohnzimmer_trv']={state:'heat',attributes:{
        friendly_name:'Καθιστικό θερμοστάτης'}};
      states['climate.hem_trv']={state:'heat',attributes:{
        area_id:'wohnzimmer',source_device_id:'zha_thermostat',
        source_entity_ids:['climate.wohnzimmer_trv'],
        control_mode:'pid',supported_operating_modes:['heat'],
        selected_operating_mode:'heat'}};
      card._dashboardData={...card._dashboardData,controllers:[{
        ...card._dashboardData.controllers[0],
        climate_entity_id:'climate.hem_trv',
        unavailable_source_entity_ids:[]}]};
      card._hass={...card._hass,states};draw();
    }""")
    assert page.locator("[data-managed-climate93='climate.hem_trv']").count()==1
    assert page.locator(".managed-controller").count()==2
    assert page.locator(".hem-physical-offline-b12").count()==0
    assert page.locator(".hem-physical-offline-b13").count()==0
    assert page.evaluate("calls.length")==0
    assert not errors,errors
    browser.close()
print("B13_ZIGBEE_TRV_SELECTED_AND_UNAVAILABLE_NO_FRONTEND_REGISTRY=PASS")
