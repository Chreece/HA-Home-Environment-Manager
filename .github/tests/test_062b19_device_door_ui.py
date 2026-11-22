"""B19: exact-door-owned device settings; no door means no controls.

Chromium uses production HEM card and mocked Home Assistant registry, states
and services, not real physical equipment. Preserve per-controller authority,
per-language labels and legitimate existing door-source metadata in Room UI.
"""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import shutil
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[2]
CARD=ROOT/"custom_components/environment_manager/frontend/home-environment-manager-card.js"
FIXTURE=runpy.run_path(str(ROOT/".github/tests/test_beta122_card_details.py"))["fixture"]
ICONS=runpy.run_path(str(ROOT/".github/tests/test_beta108_setpoint_feedback_browser.py"))["icon_fixture"]
CHROME=os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert CHROME

LABELS={
  "en":("Eco when door closed and room unoccupied",
        "Device start coordination across open doors","Coordinate eligible starts"),
  "el":("Eco με κλειστή πόρτα και άδειο δωμάτιο",
        "Συντονισμός εκκινήσεων μέσω ανοιχτής πόρτας",
        "Συντονισμός επιτρεπόμενων εκκινήσεων"),
  "de":("Eco bei geschlossener Tür und leerem Raum",
        "Gerätestarts über offene Türen koordinieren","Zulässige Starts koordinieren"),
}

SETUP=r"""data=>{
  window.calls=[];window.routes=[];
  window.history.pushState=(_s,_t,path)=>routes.push(path);
  window.card=document.createElement("home-environment-manager-card");
  document.body.append(card);card._config={entity:"sensor.hem"};
  const states=data.states;
  states[data.controller].attributes.controller_id="ctrl_a";
  const registry=[];
  const labels={
    en:{eco:"Eco when door closed and room unoccupied",
      sync:"Device start coordination across open doors",
      inherit:"Follow existing door policy",observe:"No coordination",
      conflicts:"Delay opposing starts",shared:"Coordinate eligible starts"},
    el:{eco:"Eco με κλειστή πόρτα και άδειο δωμάτιο",
      sync:"Συντονισμός εκκινήσεων μέσω ανοιχτής πόρτας",
      inherit:"Διατήρηση πολιτικής πόρτας",observe:"Χωρίς συντονισμό",
      conflicts:"Καθυστέρηση αντίθετων εκκινήσεων",
      shared:"Συντονισμός επιτρεπόμενων εκκινήσεων"},
    de:{eco:"Eco bei geschlossener Tür und leerem Raum",
      sync:"Gerätestarts über offene Türen koordinieren",
      inherit:"Bisherige Türregel übernehmen",observe:"Keine Koordinierung",
      conflicts:"Gegenläufige Starts verzögern",
      shared:"Zulässige Starts koordinieren"}
  };
  function add(id,key,state,configurable=true,controller="ctrl_a"){
    const extra={area_id:"living",controller_id:controller,
      source_device_id:"physical-heater-device",source_entity_ids:[data.physical],
      door_device_policy:true,door_room_configured:configurable,setting_key:key,
      setting_label_locales:Object.fromEntries(Object.entries(labels)
        .map(([lang,v])=>[lang,v[key==="door_closed_eco"?"eco":"sync"]])),
      configuration_help:"Only selected verified same-area door contacts can activate this setting",
      configuration_help_locales:{el:"Μόνο επιλεγμένοι και επαληθευμένοι αισθητήρες πόρτας του χώρου.",
        en:"Only verified selected doors belonging to this room.",
        de:"Nur verifizierte, gewählte Türkontakte dieses Raums."},
      ...(key==="door_start_coordination"?{
        options:["inherit","observe","conflicts","shared"],
        option_labels_locales:Object.fromEntries(Object.entries(labels)
          .map(([lang,v])=>[lang,Object.fromEntries(
            ["inherit","observe","conflicts","shared"].map(k=>[k,v[k]]))]))
      }:{})};
    states[id]={state,attributes:extra};
    registry.push({entity_id:id,device_id:"hem-controller-device",
      config_entry_id:"entry0",platform:"environment_manager",
      unique_id:controller+"_"+key,translation_key:"equipment_"+key});
  }
  add("switch.door_eco","door_closed_eco","off");
  add("select.door_sync","door_start_coordination","inherit");
  add("switch.no_door","door_closed_eco","off",false,"ctrl_b");
  window.deviceRegistry=registry;
  card._hass={language:"el",states,user:{is_admin:true},entities:{
    "sensor.hem":{config_entry_id:"entry0"},
    [data.controller]:{device_id:"hem-controller-device",config_entry_id:"entry0"}
  },connection:{},localize:()=>undefined,
    callService:(...args)=>{calls.push(args);return Promise.resolve();},
    callWS:async request=>request.type==="config/entity_registry/list"?registry:
      Promise.reject(Error("Unexpected WebSocket request"))};
  card._renderContent(true);card._configEntryId114="entry0";
  card._configEntryOwner114="sensor.hem";
  card._areaDeviceIds=new Map([["living","room-hub"]]);
}"""

with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=CHROME,headless=True,
    args=["--no-sandbox","--disable-dev-shm-usage"])
 for lang,width in (("el",390),("en",760),("de",320)):
  page=browser.new_page(viewport={"width":width,"height":950});errors=[]
  page.on("pageerror",lambda error:errors.append(str(error)))
  page.set_content('<style>body{margin:0;background:#161616;color:#eee;--card-background-color:#222;--primary-text-color:#eee;--secondary-text-color:#aaa}</style>')
  page.evaluate(ICONS());page.add_script_tag(path=str(CARD))
  page.evaluate(SETUP,FIXTURE())
  room=page.locator('[data-room-fold87="living"]')
  room.locator(":scope > summary").evaluate("(node)=>node.click()")
  room.locator('[data-device-fold87="climate.hem_heater"] [data-open-controller-device122]').click()
  modal=page.locator("dialog.hem-controller-options126")
  expect(modal).to_be_visible()
  page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length===3")
  page.evaluate("(lang)=>card._hass.language=lang",lang)
  page.evaluate("card._hemFullRender127(card._hemControllerDialog126,'device')")
  section=modal.locator('[data-hem-full-category127="ventilation"]')
  assert section.count()==1
  eco=section.locator('[data-hem-full-row127="switch.door_eco"]')
  sync=section.locator('[data-hem-full-row127="select.door_sync"]')
  assert eco.count()==sync.count()==1
  assert modal.locator('[data-hem-full-row127="switch.no_door"]').count()==0
  section.locator(":scope > summary").click()
  expect(eco).to_be_visible()
  expect(sync).to_be_hidden()
  modal.locator('[data-settings-level-b8]').select_option('advanced')
  assert LABELS[lang][0] in eco.inner_text()
  assert LABELS[lang][1] in sync.inner_text()
  assert LABELS[lang][2] in sync.locator("select").inner_text()
  assert modal.evaluate("e=>e.scrollWidth<=e.clientWidth+2")
  assert page.evaluate("calls.length")==0
  eco.locator("[data-hem-full-apply127]").click()
  page.wait_for_function("calls.length===1")
  assert page.evaluate("calls[0]")==["switch","turn_on",{"entity_id":"switch.door_eco"}]
  sync.locator("select").select_option("shared")
  page.wait_for_function("calls.length===2")
  assert page.evaluate("calls[1]")==["select","select_option",
    {"entity_id":"select.door_sync","option":"shared"}]
  # Remove the room's selected door. The native entity registry is retained,
  # yet NO door controls may stay in this device's dashboard.
  page.evaluate("""()=>{
    const saved=card._hemControllerDialog126;
    saved.node.querySelectorAll('input,select,button').forEach(n=>n.blur());
    for(const id of ['switch.door_eco','select.door_sync'])
      card._hass.states[id].attributes.door_room_configured=false;
    card._hemFullRender127(saved,'device');
  }""")
  assert modal.locator('[data-hem-full-row127="switch.door_eco"]').count()==0
  assert modal.locator('[data-hem-full-row127="select.door_sync"]').count()==0
  # Restored selected same-area door produces the same individual device rows
  # without altering room settings, entity IDs or the physical appliance.
  page.evaluate("""()=>{
    const saved=card._hemControllerDialog126;
    for(const id of ['switch.door_eco','select.door_sync'])
      card._hass.states[id].attributes.door_room_configured=true;
    card._hemFullRender127(saved,'device');
  }""")
  assert modal.locator('[data-hem-full-row127="switch.door_eco"]').count()==1
  assert modal.locator('[data-hem-full-row127="select.door_sync"]').count()==1
  assert page.evaluate("calls.length")==2
  assert not errors,errors
  page.close()
 browser.close()
print("PASS: device-only door Eco/coordination, no-door hiding, exact service targets, same owner, EL/EN/DE, 320/390/760px")
