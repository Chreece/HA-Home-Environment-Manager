"""Beta86: original native HA fault on the card, one default-ON switch.

Real Chromium checks safe exact switch and original HA entity navigation.
No physical device or relay command is ever sent during this regression.
"""
from __future__ import annotations
import runpy
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta66_browser.py'))
states=base["states"].copy()
room=base["room"].copy()
common={"area_id":"bedroom","source_entity_ids":["climate.comfee"]}
native_fault={
    "status":"error","source_entity_id":"sensor.comfee_error_code",
    "source_state":"E24","severity":"error",
    "code":"E24","description":"Water container full",
    "info":{"error_detail":"Remove the tank"},
    "native_error_entities":["sensor.comfee_error_code"],
    "active_count":1,
}
states["sensor.comfee_error_code"]={
    "state":"E24", "attributes":{"friendly_name":"Original Comfee error",
                               "error_message":"Water container full"}
}
states["sensor.other_device_error"]={
    "state":"E60", "attributes":{"friendly_name":"Other device"}
}
states["switch.hem_device_error_alerts"]={
    "state":"on","attributes":{
        **common,"friendly_name":"Announce device errors",
        "device_fault_role":"announce", "native_error":native_fault,
    }
}


def assert_announcement(page, label, state):
    control = page.locator('[data-device-error-announce]')
    assert control.count() == 1
    assert control.get_attribute("role") == "switch"
    assert control.get_attribute("aria-checked") == str(state == "on").lower()
    assert control.get_attribute("aria-label") == label
    assert control.get_attribute("title") == label
    # The purpose icon opens help; the adjacent localized state alone toggles.
    expected = page.evaluate("s=>card._quickState8(s)", state)
    assert control.inner_text().strip() == expected
    assert control.locator("ha-icon").count() == 0
    icon = page.locator('[data-detail-id="device-option:switch.hem_device_error_alerts"] > summary ha-icon')
    assert icon.count() == 1
    assert icon.get_attribute("icon") == (
        "mdi:bell-ring-outline" if state == "on" else "mdi:bell-off-outline")


executable=shutil.which("chromium") or shutil.which("google-chrome")
assert executable,"Chromium required for actual UI test"
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=executable,headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage"])
    page=browser.new_page(viewport={"width":390,"height":950})
    failures=[]
    page.on("pageerror",lambda error:failures.append(str(error)))
    page.set_content('<html><body></body></html>')
    page.add_script_tag(path=str(ROOT/"frontend/air-quality-advisor-card.js"))
    page.evaluate("""({states,room})=>{
        window.calls=[];window.opened=[];window.room=room;
        window.card=document.createElement('home-environment-manager-card');
        document.body.append(card);
        card.addEventListener('hass-more-info',event=>{
            opened.push(event.detail.entityId);
        });
        card._hass={language:'en',states,localize:()=>undefined,
            callService:(...args)=>{calls.push(args);return Promise.resolve();}};
        window.draw=()=>{card.shadowRoot.innerHTML=card._styles()+
            '<ha-card class="shell"><div class="content">'+
             card._climatePanel(room)+'</div></ha-card>';};
        draw();
    }""",{"states":states,"room":room})
    card=page.locator(".managed-controllers")
    assert card.count()==1
    error=page.locator(".hem-device-error")
    assert error.count()==1,error.count()
    for value in ("Physical device error","E24","Water container full",
                  "Remove the tank","sensor.comfee_error_code"):
        assert value in error.inner_text(),(value,error.inner_text())
    assert "sensor.other_device_error" not in error.inner_text()
    announcement=page.locator('[data-device-error-announce]')
    assert_announcement(page, "Announce device errors", "on")
    assert page.evaluate("calls.length")==0
    source=page.locator('[data-open-native-error="sensor.comfee_error_code"]')
    source.click()
    assert page.evaluate("opened")==["sensor.comfee_error_code"]
    assert page.evaluate("calls.length")==0
    announcement.click()
    page.wait_for_timeout(50)
    assert page.evaluate("calls")==[
        ["switch","turn_off",{"entity_id":"switch.hem_device_error_alerts"}]]
    # A fake unrelated toggle cannot reach the native device.
    page.evaluate("""()=>{
      const button=card.shadowRoot.querySelector('[data-device-error-announce]');
      button.dataset.deviceErrorAnnounce='switch.other';
      button.click();
    }""")
    page.wait_for_timeout(25)
    assert page.evaluate("calls.length")==1

    page.evaluate("""()=>{
       const copy={...card._hass.states};
       copy['switch.hem_device_error_alerts']={
           state:'off',attributes:{
               ...copy['switch.hem_device_error_alerts'].attributes,
               native_error:{status:'ok',source_entity_id:'sensor.comfee_error_code',
                 native_error_entities:['sensor.comfee_error_code'],active_count:0}
           }
       };
       card._hass={...card._hass,states:copy};draw();
    }""")
    assert page.locator('.hem-device-error').count()==0
    assert_announcement(page, "Announce device errors", "off")
    page.locator('[data-device-error-announce]').click()
    page.wait_for_timeout(50)
    assert page.evaluate("calls")[-1]==[
        "switch","turn_on",{"entity_id":"switch.hem_device_error_alerts"}
    ]
    # Device telemetry unavailable does not silently claim success.
    page.evaluate("""()=>{
       const copy={...card._hass.states};
       copy['switch.hem_device_error_alerts']={
           state:'on',attributes:{
               ...copy['switch.hem_device_error_alerts'].attributes,
               native_error:{status:'unavailable',source_entity_id:'sensor.comfee_error_code',
                 native_error_entities:['sensor.comfee_error_code'],active_count:0,
                 last_known_fault:{code:'E24',description:'Water container full'}}
           }
       };
       card._hass={...card._hass,states:copy};draw();
    }""")
    assert "E24" in page.locator('.hem-device-error').inner_text()
    assert "Unavailable" in page.locator('.hem-device-error').inner_text()

    for locale,label in [
        ("el","Ανακοίνωση σφαλμάτων συσκευής"),
        ("de","Gerätefehler melden"),
        ("en","Announce device errors"),
    ]:
        for state in ("on", "off"):
            page.evaluate("""({locale,state})=>{
                const id='switch.hem_device_error_alerts';
                card._hass={...card._hass,language:locale,states:{...card._hass.states,
                    [id]:{...card._hass.states[id],state}}};draw();
            }""", {"locale": locale, "state": state})
            assert_announcement(page, label, state)
    assert page.evaluate("calls") == [
        ["switch", "turn_off", {"entity_id": "switch.hem_device_error_alerts"}],
        ["switch", "turn_on", {"entity_id": "switch.hem_device_error_alerts"}],
    ]
    assert not failures,failures
    browser.close()
print("BETA86_CHROMIUM_NATIVE_FAULT_ORIGINAL_ENTITY_AND_DEFAULT_ON_SWITCH=PASS")
