"""0.6.1b12: room-hub-only native settings and controller gear modal in real Chromium.

All HA calls are local, inspectable fixtures. Nothing connects to physical hardware.
"""
from __future__ import annotations
import os
from pathlib import Path
import runpy
import shutil
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[2]
BRAND=ROOT/"custom_components/environment_manager/frontend/air-quality-advisor-card.js"
room_test=runpy.run_path(str(ROOT/".github/tests/test_beta114_room_settings.py"))
before=runpy.run_path(str(ROOT/".github/tests/test_beta108_setpoint_feedback_browser.py"))
BASIC=room_test["FORM"]
states=before["fixture_definitions"]()["states"]
data=states["sensor.hem"]["attributes"]["dashboard"]
data["rooms"]=data["rooms"][:2]
data["rooms"][0]["name"]="Living room"
data["rooms"][1]["name"]="Bedroom"
chrome=os.environ.get("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert chrome,"Chromium required"

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=chrome,headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage"])
    page=browser.new_page(viewport={"width":390,"height":950})
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.set_content("""<!doctype html><html><head><style>
      *{box-sizing:border-box}body{margin:0;font:14px Arial;background:#111;color:#eee;
      --card-background-color:#202830;--secondary-background-color:#293440;
      --primary-text-color:#eef2f6;--secondary-text-color:#b4bfca;
      --divider-color:#475665;--primary-color:#03a9f4}
      </style></head><body></body></html>""")
    page.evaluate(before["icon_fixture"]())
    page.add_script_tag(path=str(BRAND))
    page.evaluate(room_test["SETUP"],{"states":states,"form":BASIC,"native":False})
    page.evaluate("""() => {
      const added={
        'number.hem_home_target_a':['entry0_area_room0_climate_profile_temperature_home','living-device','17', {min:10,max:30,step:0.5,friendly_name:'Home comfort target'}],
        'select.hem_pid_gain_a':['entry0_area_room0_pid_gain_source','living-device','defaults', {options:['defaults','manual'],friendly_name:'PID gain source'}],
        'switch.hem_occupancy_a':['entry0_area_room0_sleep_room','living-device','off',{friendly_name:'Room sleep'}],
        'number.foreign_room':['entry0_area_room1_climate_profile_temperature_home','bed-device','10',{min:0,max:30,step:1,friendly_name:'FOREIGN BEDROOM'}],
        'number.spoof_room':['another_entry_area_room0_climate_profile_temperature_home','living-device','5',{min:0,max:30,step:1,friendly_name:'FORGED ENTRY'}],
        'number.spoof_device':['entry0_area_room0_climate_profile_temperature_home','physical-device','5',{min:0,max:30,step:1,friendly_name:'FORGED DEVICE'}]
      };
      for(const [id,[unique_id,device_id,value,attributes]] of Object.entries(added)){
        card._hass.states[id]={state:value,attributes};
        card._hass.entities[id]={platform:'environment_manager',config_entry_id:'entry0',unique_id,device_id};
      }
      window.nativeCalls=[];
      card._hass.callService=(...args)=>{nativeCalls.push(args);return Promise.resolve();};
    }""")
    assert page.evaluate("card._openRoomSettings114('room0')") is True
    dialog=page.locator(".hem-room-options114")
    expect(dialog).to_be_visible()
    assert dialog.locator('[data-room-options-group114]').count()>=7
    for category,id in (("targets","number.hem_home_target_a"),
                        ("pid","select.hem_pid_gain_a"),
                        ("presence","switch.hem_occupancy_a")):
        section=dialog.locator(f'[data-room-native-group126="{category}"]')
        expect(section).to_have_count(1)
        expect(section.locator(f'[data-hem-room-row126="{id}"]')).to_have_count(1)
    assert dialog.locator('[data-hem-room-row126="number.foreign_room"]').count()==0
    assert dialog.locator('[data-hem-room-row126="number.spoof_room"]').count()==0
    assert dialog.locator('[data-hem-room-row126="number.spoof_device"]').count()==0
    assert page.evaluate("nativeCalls.length")==0
    comfort=dialog.locator('[data-room-native-group126="comfort"]')
    comfort.locator("summary").click()
    comfort.locator('[data-hem-full-value127="number.hem_home_target_a"]').fill("21.5")
    comfort.locator('[data-hem-full-apply127="number.hem_home_target_a"]').click()
    page.wait_for_function("nativeCalls.length===1")
    assert page.evaluate("nativeCalls[0]")==["number","set_value",{"entity_id":"number.hem_home_target_a","value":21.5}]
    dialog.locator('[data-room-native-group126="occupancy"] > summary').click()
    dialog.locator('[data-hem-full-apply127="switch.hem_occupancy_a"]').click()
    page.wait_for_function("nativeCalls.length===2")
    assert page.evaluate("nativeCalls[1]")==["switch","turn_on",{"entity_id":"switch.hem_occupancy_a"}]
    # The separate seven-field Options Flow is not submitted by a native room edit.
    assert page.evaluate("calls.filter(call=>call.method==='POST'&&call.data?.temperature).length")==0
    dialog.locator('[data-room-options-x114]').click()
    expect(dialog).to_have_count(0)
    assert not errors,errors
    browser.close()
print("PASS: b13 complete room setting groups, exact-room registry and native service scoping")
