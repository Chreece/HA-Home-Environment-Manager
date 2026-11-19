"""Visible PID gains and truthful, mode-scoped learning status on the real card.

The Node part executes production filtering/model/rendering helpers without a
browser. The Chromium part checks default visibility and repeated HA redraws.
All state and service transports are local fixtures; no device is contacted.
"""
from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"

NODE = r"""
const fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync(process.argv[1],'utf8');
const escape=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const start=src.indexOf('  const HEM_PID_WORDS074=');
const end=src.indexOf('  AirQualityAdvisorCard.prototype._hemPidStatusRender074=',start);
assert(start>0&&end>start);
const api=new Function('escape',src.slice(start,end)+'\nreturn {pidStatusModels074,pidStatusHtml074,HEM_PID_REASONS074,HEM_PID_WORDS074};')(escape);
const auditStart=src.indexOf('  const auditPolicyB8='),auditEnd=src.indexOf('  const auditProto=',auditStart);
const audit=new Function(src.slice(auditStart,auditEnd)+'\nreturn {auditPolicyB8,auditLevelB8,auditVisibleB8};')();
assert.deepEqual(audit.auditPolicyB8,JSON.parse(fs.readFileSync(process.argv[2],'utf8')));
function field(mode,key,value){return {id:(key.includes('method')||key==='control_mode'?'select.':'number.')+mode+'_'+key,
 domain:key.includes('method')||key==='control_mode'?'select':'number',label:key,
 reg:{translation_key:'equipment_'+key},state:{state:String(value),attributes:{
 settings_scope:'operating_mode',operating_mode:mode,setting_key:key,controller_id:'ctrl_a'}}};}
function fields(method='adaptive_auto'){return ['dry','heat'].flatMap(mode=>[
 field(mode,'kp',mode==='dry'?40:7),field(mode,'ki',mode==='dry'?3:.2),field(mode,'kd',mode==='dry'?0:.4),
 field(mode,'control_mode','pid'),field(mode,'pid_calibration_method',method)]);}
const status={selected_operating_mode:'dry',control_method:'pid',pid_calibration_method:'adaptive_auto',
 pid_control_parameters:{kp:44,ki:3.3,kd:0},
 pid_learning_status:{status:'collecting',reason:'waiting_for_complete_cycles',operating_mode:'dry',valid_cycles:2,required_cycles:5},
 pid_learning_progress:{phase:'observing_on_response',valid_cycles:2,required_for_auto:5,last_rejection_reason:'on_cycle_too_short'},
 pid_review:{state:'pending',operating_mode:'dry',current:{kp:40,ki:3,kd:0},apply:{kp:44,ki:3.3,kd:0}},
 pid_last_calibration:{at:1795082400,operating_mode:'dry',previous_gains:{kp:40,ki:3,kd:0},applied_gains:{kp:44,ki:3.3,kd:0}}};
for(const method of ['manual','adaptive_suggest','adaptive_auto']){
 for(const f of fields(method).filter(f=>['kp','ki','kd'].includes(f.state.attributes.setting_key))){
  assert.equal(audit.auditLevelB8(f),'primary');
  assert.equal(Boolean(audit.auditVisibleB8({settingsAudit:{advanced:false,query:''}},f)),true);
 }
}
const advanced=field('dry','pid_process_gain',2);
assert.equal(Boolean(audit.auditVisibleB8({settingsAudit:{advanced:false,query:''}},advanced)),false);
for(const lang of ['en','el','de','fr']){
 const models=api.pidStatusModels074(fields(),status,lang);
 const active=models.find(m=>m.mode==='dry'),inactive=models.find(m=>m.mode==='heat');
 assert.equal(active.current,true);assert.deepEqual(active.gains,{kp:44,ki:3.3,kd:0});
 assert.equal(active.cycles,2);assert.equal(active.required,5);assert(active.reason);assert(active.rejection);
 assert.equal(inactive.current,false);assert.equal(inactive.state,'inactive');
 assert.deepEqual(inactive.gains,{kp:7,ki:.2,kd:.4});assert.equal(inactive.review,null);assert.equal(inactive.last,null);
 const html=api.pidStatusHtml074(models,lang,'Europe/Berlin');
 assert(html.includes('data-hem-pid-mode074="dry"'));assert(!html.includes('data-hem-pid-proposal074'));
 assert(html.includes('data-hem-pid-last074'));assert(html.includes('→'));
 assert(!html.includes('waiting_for_complete_cycles'));assert(!html.includes('on_cycle_too_short'));
 for(const [code,translations] of Object.entries(api.HEM_PID_REASONS074)){
  assert.equal(translations.length,3,code);assert(translations.every(t=>typeof t==='string'&&t.length>12),code);
 }
}
// A stale proposal or calibration tagged to a different mode must never leak.
const wrongMode=structuredClone(status);wrongMode.pid_calibration_method='adaptive_suggest';
wrongMode.pid_review.operating_mode='heat';wrongMode.pid_last_calibration.operating_mode='heat';
let model=api.pidStatusModels074(fields('adaptive_suggest'),wrongMode,'en').find(m=>m.mode==='dry');
assert.equal(model.review,null);assert.equal(model.last,null);
// Older historical records cannot borrow today's gains and pretend these were
// the values applied in the past; applied_gains is the only historical source.
const older=structuredClone(status);delete older.pid_last_calibration.applied_gains;
let html=api.pidStatusHtml074(api.pidStatusModels074(fields(),older,'en'),'en','UTC');
assert(html.includes('Applied values were not recorded'));
// Missing live attributes are unknown, not proof no calibration ever happened.
html=api.pidStatusHtml074(api.pidStatusModels074(fields(),{},'en'),'en','UTC');
assert(html.includes('Live learning status is unavailable'));assert(!html.includes('No calibration has been applied'));
// Suggest mode reports its own threshold, not the five-cycle auto threshold.
const suggest=structuredClone(status);suggest.pid_calibration_method='adaptive_suggest';
suggest.pid_learning_status.required_cycles=3;
model=api.pidStatusModels074(fields('adaptive_suggest'),suggest,'en').find(m=>m.mode==='dry');
assert.equal(model.required,3);assert(model.note.includes('only after'));
assert(model.review);assert(api.pidStatusHtml074([model],'en','UTC').includes('data-hem-pid-proposal074'));
// Every advertised state has plain-language EN/EL/DE text and no raw enum.
for(const lang of ['en','el','de'])for(const state of Object.keys(api.HEM_PID_WORDS074.en.states)){
 const sample=structuredClone(status);sample.pid_learning_status.status=state;
 model=api.pidStatusModels074(fields(),sample,lang).find(m=>m.mode==='dry');
 assert.equal(model.state,state);assert.equal(model.stateLabel,api.HEM_PID_WORDS074[lang].states[state]);
}
console.log('PASS: production visibility, effective versus saved gains, mode isolation, proposal/history provenance, all statuses and EN/EL/DE fallback');
"""


def node_checks():
    subprocess.run([
        shutil.which("node") or "node", "-e", NODE, str(CARD),
        str(CARD.with_name("settings-audit-policy.json")),
    ], check=True)


def browser_checks():
    from playwright.sync_api import sync_playwright, expect

    chrome = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome, "Chromium is required for visible-field coverage"
    fixture = runpy.run_path(str(ROOT / ".github/tests/test_beta122_card_details.py"))["fixture"]
    icons = runpy.run_path(str(ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"))["icon_fixture"]
    tree = ast.parse((ROOT / ".github/tests/test_062b18_device_pid_actions.py").read_text())
    setup = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "SETUP" for t in n.targets))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome, headless=True,
                                    args=["--no-sandbox", "--disable-dev-shm-usage"])
        for language, width in (("en", 760), ("el", 390), ("de", 320)):
            page = browser.new_page(viewport={"width": width, "height": 950})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_content('<style>body{margin:0;background:#161616;color:#eee;--card-background-color:#222;--primary-text-color:#eee;--secondary-text-color:#aaa}</style>')
            page.evaluate(icons())
            page.add_script_tag(path=str(CARD))
            page.evaluate(setup, fixture())
            page.evaluate(r"""language=>{
              card._hass.language=language;card._hass.config={time_zone:'Europe/Berlin'};
              const states=card._hass.states;
              states['climate.hem_heater'].attributes.selected_operating_mode='dry';
              states['climate.hem_heater'].attributes.supported_operating_modes=['dry','heat'];
              function add(mode,key,value){
                const domain=key==='control_mode'||key==='pid_calibration_method'?'select':'number';
                const id=domain+'.'+mode+'_'+key;
                states[id]={state:String(value),attributes:{...states['number.dry_kp'].attributes,
                  operating_mode:mode,setting_key:key,min:0,max:100,step:.001,
                  options:['pid','manual','adaptive_suggest','adaptive_auto'],friendly_name:id}};
                deviceRegistry.push({entity_id:id,device_id:'hem-controller-device',config_entry_id:'entry0',
                  platform:'environment_manager',unique_id:'ctrl_a_mode_'+mode+'_'+key,translation_key:'equipment_'+key});
              }
              add('dry','control_mode','pid');
              for(const [key,value] of Object.entries({kp:7,ki:.2,kd:.4,control_mode:'pid',pid_calibration_method:'adaptive_auto'}))add('heat',key,value);
              window.pidStatus={area_id:'living',source_entity_ids:['climate.native_heater'],controller_id:'ctrl_a',
                status_code:'controlling',control_method:'pid',selected_operating_mode:'dry',pid_calibration_method:'adaptive_suggest',
                pid_control_parameters:{kp:1.2,ki:.03,kd:0},
                pid_learning_status:{status:'ready_for_review',reason:'recommendation_pending',operating_mode:'dry',valid_cycles:3,required_cycles:3},
                pid_learning_progress:{phase:'awaiting_verified_off',valid_cycles:3,required_for_auto:5},
                pid_review:{state:'pending',operating_mode:'dry',current:{kp:1.2,ki:.03,kd:0},apply:{kp:1.32,ki:.033,kd:0}},
                pid_last_calibration:{at:1795082400,operating_mode:'dry',previous_gains:{kp:1,ki:.025,kd:0},applied_gains:{kp:1.2,ki:.03,kd:0}}};
              states['sensor.pid_status']={state:'controlling',attributes:pidStatus};
              card._statusStates65=null;card._renderContent(true);
            }""", language)
            room = page.locator('[data-room-fold87="living"]')
            room.locator(":scope > summary").evaluate("node=>node.click()")
            room.locator('[data-device-fold87="climate.hem_heater"] [data-open-controller-device122]').click()
            page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length===20")
            modal = page.locator(".hem-controller-options126")
            pid = modal.locator('[data-hem-full-category127="pid"]')
            pid.locator(":scope > summary").click()
            expect(modal.locator('[data-settings-advanced-b8]')).not_to_be_checked()
            for key in ("kp", "ki", "kd"):
                expect(pid.locator(f'[data-hem-full-row127="number.dry_{key}"]')).to_be_visible()
                expect(pid.locator(f'[data-hem-full-row127="number.heat_{key}"]')).to_be_visible()
            active = pid.locator('[data-hem-pid-mode074="dry"]')
            inactive = pid.locator('[data-hem-pid-mode074="heat"]')
            expect(active).to_be_visible()
            expect(active).to_have_attribute("data-hem-pid-state074", "ready_for_review")
            expect(active.locator("[data-hem-pid-proposal074]")).to_be_visible()
            expect(active.locator("[data-hem-pid-last074]")).to_contain_text("→")
            expect(inactive).to_have_attribute("data-hem-pid-state074", "inactive")
            assert inactive.locator("[data-hem-pid-proposal074],[data-hem-pid-last074]").count() == 0
            # Refresh status in place; keep the PID accordion and native inputs.
            page.evaluate("""()=>{window.kpInput=card._hemControllerDialog126.node.querySelector('[data-hem-full-value127="number.dry_kp"]');
              if(!kpInput)throw Error('Missing visible gain input');
              pidStatus.pid_learning_status.status='cooldown';pidStatus.pid_learning_status.reason='calibration_cooldown';
              pidStatus.pid_review={state:'none'};card._hemFullRender127(card._hemControllerDialog126,'device');}""")
            expect(active).to_have_attribute("data-hem-pid-state074", "cooldown")
            assert active.locator("[data-hem-pid-proposal074]").count() == 0
            assert page.evaluate("kpInput===card._hemControllerDialog126.node.querySelector('[data-hem-full-value127=\"number.dry_kp\"]')")
            expect(pid).to_have_attribute("open", "")
            assert pid.locator("[data-hem-pid-status074]").count() == 1
            assert modal.evaluate("node=>node.scrollWidth<=node.clientWidth+1")
            assert page.evaluate("calls.length") == 0
            assert not errors, errors
            page.close()
        browser.close()
    print("PASS: default visible Kp/Ki/Kd, active/inactive mode evidence, proposal/history, stable redraws, EN/EL/DE at 320/390/760px")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-only", action="store_true")
    args = parser.parse_args()
    node_checks()
    if not args.node_only:
        browser_checks()
