"""B13 full device and room settings from the authoritative HA entity registry.

All data and services are mocked. No native appliance is contacted.
"""
from __future__ import annotations
from pathlib import Path
import runpy,os,shutil
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[2]
CARD=ROOT/"custom_components/environment_manager/frontend/air-quality-advisor-card.js"
room_module=runpy.run_path(str(ROOT/".github/tests/test_beta114_room_settings.py"))
device_module=runpy.run_path(str(ROOT/".github/tests/test_beta122_card_details.py"))
base=runpy.run_path(str(ROOT/".github/tests/test_beta108_setpoint_feedback_browser.py"))
chrome=os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert chrome

def setup_page(browser,width=390):
    page=browser.new_page(viewport={"width":width,"height":950})
    errors=[]
    page.on("pageerror",lambda err: errors.append(str(err)))
    page.set_content("""<!DOCTYPE html><html><head><style>
      *{box-sizing:border-box}body{margin:0;font:14px Arial;color:#eee;background:#111;
        --primary-text-color:#eee;--secondary-text-color:#aaa;
        --card-background-color:#202830;--secondary-background-color:#293440;
        --divider-color:#444;--primary-color:#03a9f4}
      </style></head><body></body></html>""")
    page.evaluate(base["icon_fixture"]())
    page.add_script_tag(path=str(CARD))
    return page,errors

def registry_record(entity_id,device,entry="entry0",platform="environment_manager",unique_id=None):
    return {"entity_id":entity_id,"device_id":device,"config_entry_id":entry,
            "platform":platform,"unique_id":unique_id or ("entry0_area_room0_"+entity_id.replace(".","_"))}

with sync_playwright() as playwright:
    browser=playwright.chromium.launch(executable_path=chrome,headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage"])
    # Room: the abbreviated hass.entities cache contains only the dashboard.
    # A full websocket registry must supply the other controls.
    page,errors=setup_page(browser)
    states=base["fixture_definitions"]()["states"]
    data=states["sensor.hem"]["attributes"]["dashboard"]
    data["rooms"]=data["rooms"][:2]
    data["rooms"][0]["name"]="Living room"
    data["rooms"][1]["name"]="Bedroom"
    page.evaluate(room_module["SETUP"],{"states":states,"form":room_module["FORM"],"native":False})
    page.evaluate("""() => {
      const fields=[
        ["number.hem_room_target","17",{min:10,max:30,step:0.5,friendly_name:"Room target"}],
        ["select.hem_room_pid","manual",{options:["manual","defaults"],friendly_name:"PID gain"}],
        ["switch.hem_room_sleep","off",{friendly_name:"Room sleep"}],
        ["time.hem_room_sleep_start","22:00:00",{friendly_name:"Sleep starts"}],
        ["button.hem_room_calibrate","unknown",{friendly_name:"Recalibrate mold"}],
        ["number.foreign_room","9",{min:0,max:40,step:1,friendly_name:"Foreign room target"}],
        ["select.foreign_entry","manual",{options:["manual"],friendly_name:"Foreign entry select"}],
        ["button.foreign_platform","unknown",{friendly_name:"Foreign platform"}]
      ];
      for(const [id,state,attributes] of fields){
        card._hass.states[id]={state,attributes};
      }
      window.registry127=[
        {entity_id:"number.hem_room_target",device_id:"living-device",config_entry_id:"entry0",platform:"environment_manager",unique_id:"entry0_area_room0_climate_profile_temperature_home"},
        {entity_id:"select.hem_room_pid",device_id:"living-device",config_entry_id:"entry0",platform:"environment_manager",unique_id:"entry0_area_room0_pid_gain_source"},
        {entity_id:"switch.hem_room_sleep",device_id:"living-device",config_entry_id:"entry0",platform:"environment_manager",unique_id:"entry0_area_room0_sleep_room"},
        {entity_id:"time.hem_room_sleep_start",device_id:"living-device",config_entry_id:"entry0",platform:"environment_manager",unique_id:"entry0_area_room0_climate_sleep_start"},
        {entity_id:"button.hem_room_calibrate",device_id:"living-device",config_entry_id:"entry0",platform:"environment_manager",unique_id:"entry0_area_room0_mold_recalibrate"},
        {entity_id:"number.foreign_room",device_id:"bed-device",config_entry_id:"entry0",platform:"environment_manager",unique_id:"entry0_area_room1_climate_profile_temperature_home"},
        {entity_id:"select.foreign_entry",device_id:"living-device",config_entry_id:"other_entry",platform:"environment_manager",unique_id:"other_entry_area_room0_pid_gain_source"},
        {entity_id:"button.foreign_platform",device_id:"living-device",config_entry_id:"entry0",platform:"other_integration",unique_id:"entry0_area_room0_mold_recalibrate"}
      ];
      window.nativeCalls127=[];
      card._hass.callWS=async request=>{
        if(request.type==="config/entity_registry/list")return registry127;
        throw Error("Unexpected WS request "+request.type);
      };
      card._hass.callService=(...args)=>{nativeCalls127.push(args);return Promise.resolve();};
    }""")
    assert page.evaluate("card._openRoomSettings114('room0')") is True
    page.wait_for_function("card._roomSettingsDialog114?.fullRegistry127?.length===8")
    dialog=page.locator(".hem-room-options114")
    expect(dialog).to_be_visible()
    assert dialog.locator("[data-room-controls114]").count()==0
    for id in ("number.hem_room_target","select.hem_room_pid","switch.hem_room_sleep",
               "time.hem_room_sleep_start","button.hem_room_calibrate"):
        expect(dialog.locator(f'[data-hem-full-row127="{id}"]')).to_have_count(1)
    for id in ("number.foreign_room","select.foreign_entry","button.foreign_platform"):
        assert dialog.locator(f'[data-hem-full-row127="{id}"]').count()==0
    assert page.evaluate("nativeCalls127.length")==0
    for category in ("targets","pid","presence","schedule"):
        section=dialog.locator(f'[data-hem-full-category127="{category}"]')
        expect(section).to_have_count(1)
    dialog.locator('[data-hem-full-category127="targets"] > summary').click()
    dialog.locator('[data-hem-full-value127="number.hem_room_target"]').fill("21.5")
    dialog.locator('[data-hem-full-apply127="number.hem_room_target"]').click()
    page.wait_for_function("nativeCalls127.length===1")
    assert page.evaluate("nativeCalls127[0]")==["number","set_value",{"entity_id":"number.hem_room_target","value":21.5}]
    dialog.locator('[data-hem-full-category127="schedule"] > summary').click()
    dialog.locator('[data-hem-full-value127="time.hem_room_sleep_start"]').fill("06:40")
    dialog.locator('[data-hem-full-apply127="time.hem_room_sleep_start"]').click()
    page.wait_for_function("nativeCalls127.length===2")
    assert page.evaluate("nativeCalls127[1]")==["time","set_value",{"entity_id":"time.hem_room_sleep_start","time":"06:40:00"}]
    dialog.locator('[data-hem-full-category127="pid"] > summary').click()
    dialog.locator('[data-hem-full-apply127="button.hem_room_calibrate"]').click()
    page.wait_for_function("nativeCalls127.length===3")
    assert page.evaluate("nativeCalls127[2]")==["button","press",{"entity_id":"button.hem_room_calibrate"}]
    assert page.evaluate("calls.filter(c=>c.method==='POST'&&c.data?.temperature).length")==0
    dialog.locator('[data-room-options-x114]').click()
    assert not errors,errors
    page.close()
    # Controller: multiple HEM-owned settings (including an inactive mode)
    # must appear, even though _controllerPanel shows only current mode.
    page,errors=setup_page(browser)
    fixture=device_module["fixture"]()
    page.evaluate("""data=>{
      window.calls=[];window.routes=[];
      window.history.pushState=(_s,_t,path)=>routes.push(path);
      window.card=document.createElement("home-environment-manager-card");
      document.body.append(card);
      card._config={entity:"sensor.hem"};
      card._hass={language:"el",states:data.states,user:{is_admin:true},entities:{
        "sensor.hem":{config_entry_id:"entry0"},
        [data.controller]:{device_id:"hem-controller-device",config_entry_id:"entry0"}
      },connection:{},localize:()=>undefined,
        callService:(...args)=>{calls.push(args);return Promise.resolve();}};
      card._renderContent(true);card._configEntryId114="entry0";
      card._configEntryOwner114="sensor.hem";
      card._areaDeviceIds=new Map([["living","room-hub"]]);
      const fields=[
        ["number.hem_pid_kp","1.2",{min:0,max:100,step:0.1,friendly_name:"PID Kp",controller_id:"ctrl_a"}],
        ["select.hem_cool_mode","manual",{options:["manual","pid"],friendly_name:"Cool control",controller_id:"ctrl_a",settings_scope:"operating_mode",operating_mode:"cool"}],
        ["switch.hem_quiet","on",{friendly_name:"Quiet room",controller_id:"ctrl_a"}],
        ["button.hem_apply","unknown",{friendly_name:"Apply calibration",controller_id:"ctrl_a"}],
        ["number.foreign_controller","100",{min:0,max:100,step:1,friendly_name:"Other controller",controller_id:"ctrl_b"}]
      ];
      card._hass.states[data.controller].attributes.controller_id="ctrl_a";
      for(const [id,state,attributes] of fields)card._hass.states[id]={state,attributes};
      window.registryController127=fields.map(([id])=>({
        entity_id:id,device_id:id==="number.foreign_controller"?"other-hem-device":"hem-controller-device",
        config_entry_id:"entry0",platform:"environment_manager",unique_id:"entry0_controller_alpha_"+id.replace(".","_")
      }));
      card._hass.callWS=async req=>req.type==="config/entity_registry/list"?
        registryController127:Promise.reject(Error("Unexpected request"));
    }""",fixture)
    room=page.locator('[data-room-fold87="living"]')
    room.locator(":scope > summary").evaluate("(node)=>node.click()")
    controller=room.locator('[data-device-fold87="'+fixture["controller"]+'"]')
    controller.locator('[data-open-controller-device122]').click()
    modal=page.locator(".hem-controller-options126")
    expect(modal).to_be_visible()
    page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length===5")
    assert page.evaluate("routes.length")==0
    for id in ("number.hem_pid_kp","select.hem_cool_mode","switch.hem_quiet","button.hem_apply"):
        expect(modal.locator(f'[data-hem-full-row127="{id}"]')).to_have_count(1)
    assert modal.locator('[data-hem-full-row127="number.foreign_controller"]').count()==0
    assert modal.locator('[data-hem-full-category127="pid"]').count()>=1
    assert modal.locator('[data-hem-full-category127="mode"]').count()>=1
    assert page.evaluate("calls.length")==0
    modal.locator('[data-hem-full-category127="pid"] > summary').click()
    modal.locator('[data-hem-full-value127="number.hem_pid_kp"]').fill("2.5")
    modal.locator('[data-hem-full-apply127="number.hem_pid_kp"]').click()
    page.wait_for_function("calls.length===1")
    assert page.evaluate("calls[0]")==["number","set_value",{"entity_id":"number.hem_pid_kp","value":2.5}]
    modal.locator('[data-close-hem-controller126]').click()
    assert not modal.is_visible()
    assert not errors,errors
    page.close()
    browser.close()
print("HEM_B13_COMPLETE_ROOM_AND_DEVICE_CONTROLS_REGISTRY=PASS")
