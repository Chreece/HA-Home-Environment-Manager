"""PID review and calibration remain usable in categorized HEM device settings.

The card exposes only current control method, diagnostics, resume and binary
quick switches. All actions here use mocked HA services.
"""
from __future__ import annotations

import runpy
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
device_module = runpy.run_path(str(ROOT / ".github/tests/test_beta122_card_details.py"))
base = runpy.run_path(str(ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"))
chrome = shutil.which("chromium") or shutil.which("google-chrome")
assert chrome, "Chromium is required"
fixture = device_module["fixture"]()
states = fixture["states"]
controller = fixture["controller"]
source_id = states[controller]["attributes"]["source_device_id"]


def option(value, **extra):
    return {"state": value, "attributes": {
        "source_device_id": source_id, "area_id": "living",
        "source_entity_ids": ["climate.physical"], "controller_id": "ctrl_a", **extra,
    }}


states["select.calibration"] = option("adaptive_suggest",
    setting_key="pid_calibration_method", options=[
        "manual", "imc_lambda", "cohen_coon", "adaptive_suggest", "adaptive_auto"],
    option_labels={"adaptive_suggest": "Adaptive suggestions", "cohen_coon": "Cohen-Coon"})
states["button.review_approve"] = option("unknown",
    setting_key="pid_review_approve", pid_review_role="approve", pending=True,
    confidence="medium", current_gains={"kp": 20., "ki": .2, "kd": 3.},
    next_gains={"kp": 22., "ki": .22, "kd": 3.})
states["button.review_discard"] = option("unknown",
    setting_key="pid_review_discard", pid_review_role="discard", pending=True)
states["button.classical_apply"] = option("unknown",
    setting_key="pid_apply_calibration", pid_calibration_role="apply")
states["number.model_gain"] = option("4",
    setting_key="pid_process_gain", min=0, max=10000, step=0.01)
states["button.foreign_review"] = option("unknown",
    setting_key="pid_review_approve", controller_id="ctrl_b")

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=chrome, headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 390, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content('<style>body{font:14px Arial;background:#151515;color:#fff}</style>')
    page.evaluate(base["icon_fixture"]())
    page.add_script_tag(path=str(CARD))
    page.evaluate("""data=>{
      window.calls=[];window.card=document.createElement('home-environment-manager-card');
      document.body.appendChild(card);
      card._config={entity:'sensor.hem'};
      card._hass={language:'en',states:data.states,user:{is_admin:true},
        entities:{'sensor.hem':{config_entry_id:'entry0'},
          [data.controller]:{device_id:'hem-controller-device',config_entry_id:'entry0'}},
        connection:{},localize:()=>undefined,
        callService:(...args)=>{calls.push(args);return Promise.resolve();}};
      card._renderContent(true);
      card._configEntryId114='entry0';
      card._configEntryOwner114='sensor.hem';
      card._areaDeviceIds=new Map([['living','room-hub']]);
      window.registry84=[
        'select.calibration','button.review_approve','button.review_discard',
        'button.classical_apply','number.model_gain','button.foreign_review'
      ].map(id=>({entity_id:id,config_entry_id:'entry0',
        platform:'environment_manager',
        device_id:'hem-controller-device',unique_id:'entry0_'+id.replace('.','_')}));
      card._hass.states[data.controller].attributes.controller_id='ctrl_a';
      card._hass.callWS=async request=>request.type==='config/entity_registry/list'?
        registry84:Promise.reject(Error('Unexpected WebSocket request'));
    }""", fixture)
    assert page.locator('details.hem-calibration,[data-pid-review-action]').count()==0
    assert page.evaluate("card._openHemControllerSettings126('living',"+
                         repr(controller)+")") is True
    page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length===6")
    modal = page.locator("dialog.hem-controller-options126")
    assert modal.is_visible()
    assert modal.locator('.managed-controller,.hem-device-quick-row8').count()==0
    section = modal.locator('[data-hem-full-category127="pid"]')
    assert section.count()==1
    section.locator(":scope > summary").click()
    for id in ("select.calibration", "button.review_approve", "button.review_discard",
               "button.classical_apply", "number.model_gain"):
        assert modal.locator('[data-hem-full-row127="'+id+'"]').count()==1
    assert modal.locator('[data-hem-full-row127="button.foreign_review"]').count()==0
    assert modal.locator('option[value="adaptive_suggest"]').inner_text()=="Adaptive suggestions"
    assert page.evaluate("calls.length")==0

    modal.locator('[data-hem-full-apply127="button.review_approve"]').click()
    modal.locator('[data-hem-full-apply127="button.review_discard"]').click()
    assert page.evaluate("calls")==[
        ["button", "press", {"entity_id": "button.review_approve"}],
        ["button", "press", {"entity_id": "button.review_discard"}],
    ]
    modal.locator('[data-hem-full-value127="select.calibration"]').select_option("cohen_coon")
    modal.locator('[data-hem-full-apply127="select.calibration"]').click()
    assert page.evaluate("calls[-1] if false else calls.at(-1)")==[
        "select", "select_option", {"entity_id": "select.calibration", "option": "cohen_coon"},
    ]
    # The actual HA entity availability, not stale review HTML, gates writes.
    page.evaluate("""()=>{
      card._hass.states['button.review_approve'].state='unavailable';
      card._renderContent(true);
    }""")
    assert modal.locator('[data-hem-full-apply127="button.review_approve"]').is_disabled()
    assert len(page.evaluate("calls")) == 3
    assert not errors, errors
    browser.close()

print("HEM_PID_REVIEW_ACTIONS_ONLY_IN_CATEGORIZED_DEVICE_SETTINGS=PASS")
