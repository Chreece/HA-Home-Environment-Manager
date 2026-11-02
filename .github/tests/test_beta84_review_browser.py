"""Beta84 live Chromium actionable PID review and exclusive calibration menu.

Synthetic Home Assistant states, no real commands or device connections.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
COMMON={"area_id":"bathroom","source_entity_ids":["climate.dehumidifier"]}
def row(state,**attributes):
    return {"state":state,"attributes":{**COMMON,**attributes}}

states={
    "climate.managed":row("dry",friendly_name="Bathroom dehumidifier",
                          control_mode="pid",physical_source_state="off",
                          controller_status={"status":"within_target_band"},
                          measurements={"humidity":58.},"humidity":60.),
    "climate.dehumidifier":{"state":"off","attributes":{"friendly_name":"Dehumidifier"}},
    "select.method":row("pid",options=["existing","automatic","manual","off","pid"]),
    "select.calibration":row(
        "adaptive_suggest",pid_calibration_role="single_authoritative_method",
        options=["manual","imc_lambda","cohen_coon","adaptive_suggest","adaptive_auto"]
    ),
    "button.review_approve":row(
        "unknown",pid_review_role="approve",pending=True,confidence="medium",
        current_gains={"kp":20.,"ki":.2,"kd":3.},
        next_gains={"kp":22.,"ki":.22,"kd":3.}
    ),
    "button.review_discard":row(
        "unknown",pid_review_role="discard",pending=True,
    ),
    "button.classical_apply":row(
        "unknown",pid_calibration_role="apply",calibration_status="ready_to_apply_when_physical_off",
    ),
    "number.model_gain":row(
        "4",pid_calibration_field="pid_process_gain",min=0,max=10000,step=.01,
    ),
}
room={
    "area_id":"bathroom","name":"Bathroom","status":"safe",
    "windows":[],"readings":[],
    "environment":{"climate_plan":{
        "status":"ready","controller":"environment","profile":"home",
        "temperature_c":21.,"equipment_plan":{"humidity":{"status":"advisory",
                                                          "action":"idle","measured_rh":58.}},
        "actuation":{"status":"advisory_only"},
    }},
}
executable=shutil.which("chromium") or shutil.which("google-chrome")
assert executable,"Chromium is required"
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=executable,headless=True,
                              args=["--no-sandbox","--disable-dev-shm-usage"])
    page=browser.new_page(viewport={"width":590,"height":1000})
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.set_content('<html><body></body></html>')
    page.add_script_tag(path=str(ROOT/"frontend/air-quality-advisor-card.js"))
    page.evaluate("""({states,room})=>{
        window.calls=[];
        window.card=document.createElement('home-environment-manager-card');
        document.body.appendChild(card);
        card._hass={language:'en',states,localize:()=>undefined,
            callService:(...args)=>{calls.push(args);return Promise.resolve();}};
        window.draw=()=>{card.shadowRoot.innerHTML=card._styles()+
           '<ha-card class="shell"><div class="content">'+card._climatePanel(room)+'</div></ha-card>';};
        window.draw();
    }""",{"states":states,"room":room})
    page.locator("details.hem-calibration>summary").click()
    assert page.locator("[data-pid-calibration-method]").count()==1
    assert page.locator("[data-pid-review-action='approve']").count()==1
    assert page.locator("[data-pid-review-action='discard']").count()==1
    assert page.locator("[data-pid-model-input]").count()==0
    assert page.locator("[data-apply-pid-calibration]").count()==0
    assert "20" in page.locator(".managed-controllers").inner_text()
    assert "22" in page.locator(".managed-controllers").inner_text()

    page.locator("[data-pid-review-action='approve']").click()
    page.wait_for_timeout(30)
    assert page.evaluate("calls")==[
      ["button","press",{"entity_id":"button.review_approve"}]
    ]
    page.locator("[data-pid-review-action='discard']").click()
    page.wait_for_timeout(30)
    assert page.evaluate("calls").at(-1)==[
      "button","press",{"entity_id":"button.review_discard"}
    ]
    # A stale or unrelated button must not be able to issue an approval.
    page.evaluate("""()=>{
       const button=card.shadowRoot.querySelector('[data-pid-review-action="approve"]');
       button.dataset.pidReviewEntity='button.unrelated';
       button.click();
    }""")
    page.wait_for_timeout(20)
    assert page.evaluate("calls.length")==2

    page.evaluate("""()=>{
       card._hass.states['button.review_approve'].attributes.pending=false;
       draw();
    }""")
    assert page.locator("[data-pid-review-action]").count()==0
    page.evaluate("""()=>{
       card._hass.states['select.calibration'].state='cohen_coon';
       draw();
    }""")
    assert page.locator("[data-pid-review-action]").count()==0
    assert page.locator("[data-pid-model-input]").count()>=1
    assert page.locator("[data-apply-pid-calibration]").count()==1
    page.evaluate("""()=>{
       card._hass.states['select.calibration'].state='adaptive_auto';
       draw();
    }""")
    assert page.locator("[data-pid-review-action]").count()==0
    assert page.locator("[data-pid-model-input]").count()==0
    assert page.locator("[data-apply-pid-calibration]").count()==0
    assert not errors,errors
    browser.close()
print("BETA84_CHROMIUM_EXCLUSIVE_PID_SELECTOR_ACTION_BUTTONS=PASS")
