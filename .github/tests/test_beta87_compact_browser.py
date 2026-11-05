"""Beta87 real Chromium layout and data-preservation regression.

No live HA services, devices, network, or hardware commands. Verifies the
collapsed room/device surfaces, accessible popovers (top layer beyond card
bounds), persistent expand state, and desktop/mobile width constraints.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
chrome=shutil.which("chromium") or shutil.which("google-chrome")
assert chrome,"Chromium required"

def row(value,area,source,**attrs):
    return {"state":value,"attributes":{
        "area_id":area,"source_entity_ids":[source],**attrs,
    }}

def room(area,index):
    status=["safe","attention","unknown","safe","unknown"][index]
    return {
        "area_id":area,"name":("Badezimmer" if index==0 else f"Room {index}"),
        "status":status,"action":"close" if index==1 else None,
        "windows":[{"entity_id":f"binary_sensor.{area}_window",
                    "name":"Window","opened":index==1}],
        "readings":[
            {"metric":"temperature","value":20.1+index,
             "available":True,"unit":"°C","name":"Room temperature"},
            {"metric":"humidity","value":61.2-index,
             "available":True,"unit":"%","name":"Room humidity"},
            {"metric":"illuminance","value":37+index,
             "available":True,"unit":"lx","name":"Light"},
        ],
        "environment":{"climate_plan":{
            "status":"ready","controller":"environment","profile":"home",
            "temperature_c":20.1+index,"equipment_plan":{
                "humidity":{"status":"advisory","measured_rh":61.2-index,"action":"idle"}
            },
            "actuation":{"status":"advisory_only"},
        }},
    }

states={}
areas=[f"room{i}" for i in range(5)]
rooms=[room(a,i) for i,a in enumerate(areas)]
for i,area in enumerate(areas):
    for j in range(3 if i==0 else 1):
        suffix=f"{i}_{j}"
        source=f"climate.physical_{suffix}"
        managed=f"climate.managed_{suffix}"
        active=i==0 and j==0
        attrs={
            "friendly_name":f"Comfee Dehumidifier {suffix} very long native controller name",
            "control_mode":"pid",
            "physical_source_state":"dry" if active else "off",
            "requested_hvac_mode":"dry",
            "measurements":{"temperature":19.4+j,"humidity":61.2-j},
            "current_temperature":19.4+j, "humidity":60,
            "controller_status":{"status":"controlling" if active else
                                  "physical_acknowledgement_missing" if j==1
                                  else "within_target_band"},
        }
        states[managed]=row("dry" if active else "off",area,source,**attrs)
        states[source]={
            "state":"dry" if active else "off",
            "attributes":{"hvac_action":"drying" if active else "idle",
                          "friendly_name":f"Native device {suffix}"},
        }
        states[f"select.control_{suffix}"]=row(
            "pid",area,source,options=["existing","automatic","manual","off","pid"]
        )
        states[f"select.calibration_{suffix}"]=row(
            "manual",area,source,pid_calibration_role="method",
            options=["manual","imc_lambda","cohen_coon",
                     "adaptive_suggest","adaptive_auto"]
        )
        status="paused" if j==1 else "controlling" if active else "within_target_band"
        states[f"sensor.control_{suffix}"]=row(
            status,area,source,status_code=status,
            paused_reason="physical_acknowledgement_missing" if j==1 else None,
            demand_percent=9.8 if active else 0,
            physical_entity_states={source:"dry" if active else "off"},
        )
        states[f"button.resume_{suffix}"]=row(
            "unknown",area,source,controller_resume_role="check_and_continue"
        )
        if i==0 and j==1:
            states[f"switch.errors_{suffix}"]=row(
                "on",area,source,device_fault_role="announce",
                native_error={
                    "status":"error","code":"E24",
                    "description":"Real native sensor error",
                    "severity":"error","source_entity_id":source,
                    "native_error_entities":[source],
                },
            )
data={
    "version":1,"summary":{"safe":2,"attention":1,"unknown":2},
    "outdoor":{
        "status":"unsafe",
        "weather":[{"condition":"rainy","temperature_c":8.7,
                    "wind_kmh":6.0,"humidity":78}],
        "readings":[{"metric":"aqi","value":35,"unit":"US AQI",
                     "available":True}],
        "blockers":[{"code":"weather_condition","value":"rainy","label":"Rain"}],
        "warnings":[],
    },
    "rooms":rooms,
}
states["sensor.hem"]={"state":"ready","attributes":{"dashboard":data}}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=chrome,headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage"])
    page=browser.new_page(viewport={"width":590,"height":950})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content("""<!doctype html><html><head><style>
      *{box-sizing:border-box}body{margin:0;background:#111;color:#ddd;font-family:Arial}
      :root{--primary-text-color:#eee;--secondary-text-color:#aaa;
      --card-background-color:#202020;--secondary-background-color:#292929;
      --divider-color:#444}</style></head><body></body></html>""")
    page.add_script_tag(path=str(ROOT/"frontend/air-quality-advisor-card.js"))
    page.evaluate("""({states})=>{
       window.calls=[];
       window.card=document.createElement('home-environment-manager-card');
       document.body.append(card);
       card._hass={language:'el',states,localize:()=>undefined,
           callService:(...args)=>{calls.push(args);return Promise.resolve();}};
       card._config={entity:'sensor.hem'};
       card._renderContent(true);
    }""",{"states":states})
    assert not errors,errors
    assert page.locator(".card-heading h2").count()==1
    assert page.locator(".card-heading .overline").is_hidden()
    assert page.locator(".card-logo").is_hidden()
    assert page.locator(".hem-overview87").count()==1
    assert page.locator(".hem-overview-stat87").count()==3
    assert page.locator(".donut").count()==0
    assert page.locator(".hem-room-fold87:not([open])").count()==5
    assert page.locator(".hem-room-glance87").count()==5
    height=page.locator(".hem-room-glance87").first.bounding_box()["height"]
    if height>52:
        diag=page.locator(".hem-room-glance87").first.evaluate("""node=>({
            client:node.clientWidth,scroll:node.scrollWidth,height:node.clientHeight,
            children:[...node.children].map(c=>({
                tag:c.tagName,klass:c.className?.baseVal||c.className,
                width:c.getBoundingClientRect().width,
                height:c.getBoundingClientRect().height, display:getComputedStyle(c).display
            }))
        })""")
        raise AssertionError(("room summary must be one line",height,diag))

    outdoor=page.locator(".outside")
    assert outdoor.count()==1
    assert outdoor.locator(".outdoor-head").count()==1
    assert outdoor.locator(".hem-outside-details87").count()==1
    assert outdoor.bounding_box()["height"]<=85,outdoor.bounding_box()
    assert outdoor.locator(".out-chip").count()>=1

    first=page.locator('.hem-room-fold87[data-room-fold87="room0"]')
    assert "20,1" in first.locator(".hem-room-glance87").inner_text()
    assert "61,2" in first.locator(".hem-room-glance87").inner_text()
    assert not first.locator(".hem-room-body87").is_visible()
    assert page.evaluate("calls.length")==0

    first.locator(":scope > summary").click()
    assert first.get_attribute("open") is not None
    assert first.locator(".hem-room-body87").is_visible()
    assert first.locator(".hem-device-fold87").count()==3
    assert first.locator(".hem-device-fold87:not([open])").count()==3
    assert not first.locator("[data-climate-method]").first.is_visible()
    warning=first.locator(".hem-device-attention87 .hem-hint87")
    assert warning.count()>=1
    assert first.locator(".hem-room-alerts87 .hem-hint87").count()>=2
    device=first.locator('.hem-device-fold87[data-device-fold87="climate.managed_0_1"]')
    assert "60,2" in device.locator(":scope > summary").inner_text()
    device.locator(":scope > summary").evaluate("(el)=>el.click()")
    assert device.get_attribute("open") is not None
    assert device.locator("[data-climate-method]").is_visible()
    assert device.locator("[data-device-error-announce]").count()==1
    assert device.locator(".hem-device-error").count()==1

    # Popovers rise above the card clipping boundary and remain completely
    # on screen even when the trigger is close to the left or right edge.
    info=device.locator("details.hem-context76 > summary").first
    info.click()
    page.wait_for_timeout(80)
    floating=page.locator(".hem-floating-info87")
    if floating.count()!=1:
        diag=info.evaluate("""node=>({
            open:node.parentElement.open,
            root:node.getRootNode()===card.shadowRoot,
            ready:card.shadowRoot.querySelector('ha-card.shell')?.className,
            portalReady:typeof card._openInfo87,
            popup:!!card._floatingInfo87,
            oldExpanded:[...card._detailsExpanded66||[]],
            present:card.shadowRoot.querySelectorAll('.hem-floating-info87').length
        })""")
        raise AssertionError(("Info bubble must show after opening",diag,errors))
    assert floating.evaluate("(e)=>e.matches(':popover-open')")
    rect=floating.bounding_box()
    assert rect and rect["x"]>=0 and rect["x"]+rect["width"]<=590,(rect,errors)
    assert floating.evaluate("(e)=>getComputedStyle(e).position")=="fixed"
    page.keyboard.press("Escape")
    assert floating.count()==0 or not floating.is_visible()

    # Persist expanded room/device choices over an HA refresh.
    page.evaluate("card._renderContent(true)")
    assert first.get_attribute("open") is not None
    assert device.get_attribute("open") is not None
    assert page.evaluate("calls.length")==0

    first.locator(":scope > summary").click()
    assert first.get_attribute("open") is None
    for width in [320,360,430,590]:
        page.set_viewport_size({"width":width,"height":950})
        page.evaluate("card._renderContent(true)")
        assert page.evaluate("document.documentElement.scrollWidth")<=width,width
        assert page.locator(".hem-room-fold87:not([open])").count()==5
        assert page.locator(".hem-overview87").bounding_box()["height"]<=58
        assert page.locator(".hem-room-glance87").first.bounding_box()["height"]<=57
        assert page.locator(".outside").bounding_box()["height"]<=89
    assert not errors,errors
    browser.close()
print(json.dumps({
    "status":"PASS","test":"beta87 compact fold and unclipped help",
    "rooms":5,"devices_first_room":3,
    "viewports":[320,360,430,590],
    "hardware_calls":0,
}))
