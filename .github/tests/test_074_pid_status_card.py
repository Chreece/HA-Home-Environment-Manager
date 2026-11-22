"""Level-scoped PID editors and truthful learning status on the real card.

The Node part executes production filtering/model/rendering helpers without a
browser. Chromium checks cumulative levels and repeated HA redraws.
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
CARD = ROOT / "custom_components/environment_manager/frontend/home-environment-manager-card.js"

NODE = r"""
const fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync(process.argv[1],'utf8');
// Isolated production sections use the same bundled locale helpers as the full card.
const localeStart=src.indexOf('  /* HEM_TRANSLATION_DATA_B8_START */');
const localeEnd=src.indexOf('  const BRAND_TITLE =',localeStart);
assert(localeStart>0&&localeEnd>localeStart);
const localeBootstrap=src.slice(localeStart,localeEnd);
const escape=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const start=src.indexOf('  const HEM_PID_WORDS074=');
const end=src.indexOf('  HomeEnvironmentManagerCard.prototype._hemPidStatusRender074=',start);
assert(start>0&&end>start);
const api=new Function('escape',localeBootstrap+src.slice(start,end)+'\nreturn {pidStatusModels074,pidStatusHtml074,HEM_PID_REASONS074,HEM_PID_WORDS074};')(escape);
const NOW=Date.now()/1000;
const auditStart=src.indexOf('  const auditPolicyB8='),auditEnd=src.indexOf('  const auditProto=',auditStart);
const audit=new Function(localeBootstrap+src.slice(auditStart,auditEnd)+'\nreturn {auditPolicyB8,auditLevelB8,auditVisibleB8};')();
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
 pid_review:{state:'pending',operating_mode:'dry',created_at:NOW-100,expires_at:NOW-100+48*3600,
   current:{kp:40,ki:3,kd:0},apply:{kp:44,ki:3.3,kd:0}},
 pid_last_calibration:{at:1795082400,operating_mode:'dry',previous_gains:{kp:40,ki:3,kd:0},applied_gains:{kp:44,ki:3.3,kd:0}}};
for(const method of ['manual','adaptive_suggest','adaptive_auto']){
 for(const f of fields(method).filter(f=>['kp','ki','kd'].includes(f.state.attributes.setting_key))){
  assert.equal(audit.auditLevelB8(f),'advanced');
  assert.equal(Boolean(audit.auditVisibleB8({settingsAudit:{level:'basic',query:''}},f)),false);
  assert.equal(Boolean(audit.auditVisibleB8({settingsAudit:{level:'advanced',query:''}},f)),true);
  assert.equal(Boolean(audit.auditVisibleB8({settingsAudit:{level:'expert',query:''}},f)),true);
 }
}
const expert=field('dry','pid_process_gain',2);
assert.equal(audit.auditLevelB8(expert),'expert');
assert.equal(Boolean(audit.auditVisibleB8({settingsAudit:{level:'advanced',query:''}},expert)),false);
assert.equal(Boolean(audit.auditVisibleB8({settingsAudit:{level:'expert',query:''}},expert)),true);
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
suggest.pid_learning_status={...suggest.pid_learning_status,required_cycles:3,
 status:'ready_for_review',reason:'recommendation_pending'};
suggest.pid_review.current={...suggest.pid_control_parameters};
suggest.pid_review.apply={kp:48.4,ki:3.63,kd:0};
model=api.pidStatusModels074(fields('adaptive_suggest'),suggest,'en').find(m=>m.mode==='dry');
assert.equal(model.required,3);assert(model.note.includes('only after'));
assert(model.review);assert(api.pidStatusHtml074([model],'en','UTC').includes('data-hem-pid-proposal074'));
// Missing feedback identity must hide a retained context's evidence, even if
// a delayed snapshot still contains its old Ready state/count/phase/proposal.
// Rendering remains read-only, so resolving the same sensor can show it again.
for(const language of ['en','el','de']){
 const sample=structuredClone(suggest);
 sample.pid_learning_status={...sample.pid_learning_status,context_verified:false,valid_cycles:5};
 sample.pid_learning_progress.valid_cycles=6;
 const before=JSON.stringify(sample);
 model=api.pidStatusModels074(fields('adaptive_suggest'),sample,language,NOW).find(m=>m.mode==='dry');
 assert.equal(model.state,'waiting');assert.equal(model.review,null);assert.equal(model.cycles,null);
 assert.equal(model.phase,'');assert.equal(model.rejection,'');
 html=api.pidStatusHtml074([model],language,'UTC');
 assert(!html.includes('data-hem-pid-proposal074'));
 assert(!html.includes(api.HEM_PID_WORDS074[language].cycles));
 assert(!html.includes(api.HEM_PID_WORDS074[language].phases.observing_on_response));
 assert.equal(JSON.stringify(sample),before,'Hiding evidence must not discard a stored proposal');
 sample.pid_learning_status={...sample.pid_learning_status,context_verified:true,valid_cycles:3};
 model=api.pidStatusModels074(fields('adaptive_suggest'),sample,language,NOW).find(m=>m.mode==='dry');
 assert.equal(model.state,'ready_for_review');assert.deepEqual(model.review,suggest.pid_review);
 assert.equal(model.cycles,3,'The current persisted summary outranks the paused observer count');
 sample.pid_learning_status={...sample.pid_learning_status,status:'collecting',valid_cycles:0,
  reason:'waiting_for_complete_cycles'};
 sample.pid_review={state:'none'};
 model=api.pidStatusModels074(fields('adaptive_suggest'),sample,language,NOW).find(m=>m.mode==='dry');
 assert.equal(model.cycles,0,'An empty persisted summary cannot borrow expired observer cycles');
}
// Lifecycle explanations replace stale readiness in the same compact panel.
for(const language of ['en','el','de'])for(const reason of ['recommendation_expired',
 'recommendation_discarded','recommendation_stale','tuning_settings_changed','new_cycle_required',
 'observation_interrupted','saved_context_resumed']){
 const sample=structuredClone(suggest);
 sample.pid_learning_status={...sample.pid_learning_status,status:'collecting',reason};
 sample.pid_review={state:reason==='recommendation_discarded'?'discarded':'expired',reason,operating_mode:'dry'};
 model=api.pidStatusModels074(fields('adaptive_suggest'),sample,language).find(m=>m.mode==='dry');
 assert.equal(model.state,'collecting');assert.equal(model.review,null);assert(model.reason.length>12);
 html=api.pidStatusHtml074([model],language,'UTC');
 assert(!html.includes('data-hem-pid-proposal074'));assert(!html.includes(reason));
}
// Age and current-gain checks also cover a delayed, formerly-ready HA snapshot.
for(const change of [
 sample=>sample.pid_review.created_at=NOW-48*3600-.001,
 sample=>delete sample.pid_review.created_at,
 sample=>sample.pid_review.created_at=NOW+60,
 sample=>sample.pid_control_parameters.kp+=1,
 sample=>sample.pid_review={state:'expired',reason:'tuning_settings_changed',operating_mode:'dry'},
]){
 const sample=structuredClone(suggest);change(sample);
 model=api.pidStatusModels074(fields('adaptive_suggest'),sample,'en',NOW).find(m=>m.mode==='dry');
 assert.equal(model.state,'collecting');assert.equal(model.review,null);
}
const atExpiry=structuredClone(suggest);
atExpiry.pid_review.created_at=NOW-48*3600;atExpiry.pid_review.expires_at=NOW;
assert.equal(api.pidStatusModels074(fields('adaptive_suggest'),atExpiry,'en',NOW)
 .find(m=>m.mode==='dry').state,'ready_for_review');
const applied=structuredClone(suggest);
applied.pid_learning_status={...applied.pid_learning_status,status:'applied',reason:'applied'};
applied.pid_review={...applied.pid_review,state:'applied',reason:'applied'};
applied.pid_last_calibration={at:NOW,operating_mode:'dry',
 previous_gains:applied.pid_review.current,applied_gains:applied.pid_review.apply};
applied.pid_control_parameters={...applied.pid_review.apply};
model=api.pidStatusModels074(fields('adaptive_suggest'),applied,'en').find(m=>m.mode==='dry');
assert.equal(model.state,'applied');assert.equal(model.review,null);
assert(api.pidStatusHtml074([model],'en','UTC').includes('48.4'));
// Every advertised state has plain-language EN/EL/DE text and no raw enum.
for(const lang of ['en','el','de'])for(const state of Object.keys(api.HEM_PID_WORDS074.en.states)){
 const sample=structuredClone(state==='ready_for_review'?suggest:status);sample.pid_learning_status.status=state;
 model=api.pidStatusModels074(fields(state==='ready_for_review'?'adaptive_suggest':'adaptive_auto'),sample,lang).find(m=>m.mode==='dry');
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
                pid_review:{state:'pending',operating_mode:'dry',created_at:Date.now()/1000-100,
                  expires_at:Date.now()/1000-100+48*3600,current:{kp:1.2,ki:.03,kd:0},apply:{kp:1.32,ki:.033,kd:0}},
                pid_last_calibration:{at:1795082400,operating_mode:'dry',previous_gains:{kp:1,ki:.025,kd:0},applied_gains:{kp:1.2,ki:.03,kd:0}}};
              states['sensor.pid_status']={state:'controlling',attributes:pidStatus};
              // HA publishes a new states mapping. In-place mutation would
              // leave the production controller cache pointing at the setup
              // snapshot that did not contain the diagnostic sensor.
              card._hass={...card._hass,states:{...states}};card._renderContent(true);
            }""", language)
            room = page.locator('[data-room-fold87="living"]')
            room.locator(":scope > summary").evaluate("node=>node.click()")
            room.locator('[data-device-fold87="climate.hem_heater"] [data-open-controller-device122]').click()
            page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length===20")
            modal = page.locator(".hem-controller-options126")
            pid = modal.locator('[data-hem-full-category127="pid"]')
            pid.locator(":scope > summary").click()
            level = modal.locator('[data-settings-level-b8]')
            expect(level).to_have_value('basic')
            for key in ("kp", "ki", "kd"):
                expect(pid.locator(f'[data-hem-full-row127="number.dry_{key}"]')).to_be_hidden()
                expect(pid.locator(f'[data-hem-full-row127="number.heat_{key}"]')).to_be_hidden()
            expect(pid.locator('[data-hem-pid-mode074="dry"]')).to_be_visible()
            expect(pid.locator('[data-hem-pid-review-b18="approve"]')).to_be_visible()
            level.select_option('advanced')
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
            # The real card replaces stale Ready/proposed values without
            # rebuilding the form or multiplying settings/actions.
            page.evaluate("""()=>{
              window.pidReviewFixture={...pidStatus.pid_review};
              window.kpInput=card._hemControllerDialog126.node.querySelector('[data-hem-full-value127="number.dry_kp"]');
            }""")
            cycle_label, phase_text = {
                "en": ("accepted cycles", "Waiting for confirmed OFF"),
                "el": ("αποδεκτοί κύκλοι", "Αναμονή επιβεβαίωσης ότι η συσκευή είναι κλειστή"),
                "de": ("akzeptierte Zyklen", "Warten auf bestätigten AUS-Zustand"),
            }[language]
            page.evaluate("""()=>{
              window.pidStatus={...pidStatus,pid_learning_status:{...pidStatus.pid_learning_status,
                context_verified:false,valid_cycles:5},pid_learning_progress:{...pidStatus.pid_learning_progress,
                valid_cycles:6}};
              window.pidUnresolvedBefore=JSON.stringify(pidStatus);
              card._hass={...card._hass,states:{...card._hass.states,
                'sensor.pid_status':{state:'controlling',attributes:pidStatus}}};
              card._hemFullRender127(card._hemControllerDialog126,'device');
            }""")
            expect(active).to_have_attribute("data-hem-pid-state074", "waiting")
            assert active.locator("[data-hem-pid-proposal074]").count() == 0
            assert active.locator(".hem-pid-status-row074").filter(has_text=cycle_label).count() == 0
            expect(active).not_to_contain_text(phase_text)
            assert page.evaluate("JSON.stringify(pidStatus)===pidUnresolvedBefore")
            assert page.evaluate("JSON.stringify(pidStatus.pid_review)===JSON.stringify(pidReviewFixture)")
            assert page.evaluate("kpInput===card._hemControllerDialog126.node.querySelector('[data-hem-full-value127=\"number.dry_kp\"]')")
            # The original pending proposal survives ordinary sensor recovery.
            # The fresh saved count remains authoritative over old progress.
            page.evaluate("""()=>{
              window.pidStatus={...pidStatus,pid_learning_status:{...pidStatus.pid_learning_status,
                context_verified:true,valid_cycles:3}};
              card._hass={...card._hass,states:{...card._hass.states,
                'sensor.pid_status':{state:'controlling',attributes:pidStatus}}};
              card._hemFullRender127(card._hemControllerDialog126,'device');
            }""")
            expect(active).to_have_attribute("data-hem-pid-state074", "ready_for_review")
            expect(active.locator("[data-hem-pid-proposal074]")).to_be_visible()
            expect(active.locator(".hem-pid-status-row074").filter(has_text=cycle_label)).to_contain_text("3 / 3")
            expect(active).to_contain_text(phase_text)
            assert page.evaluate("kpInput===card._hemControllerDialog126.node.querySelector('[data-hem-full-value127=\"number.dry_kp\"]')")
            lifecycle_words = {
                "en": ("expired after 48 hours", "proposal was discarded", "Timing settings changed", "new complete cycle"),
                "el": ("έληξε μετά από 48 ώρες", "πρόταση απορρίφθηκε", "ρυθμίσεις χρονισμού άλλαξαν", "νέος πλήρης κύκλος"),
                "de": ("nach 48 Stunden abgelaufen", "Vorschlag wurde verworfen", "Zeiteinstellungen wurden geändert", "neuer vollständiger Zyklus"),
            }[language]
            for reason, review_state, expected_text in zip(
                ("recommendation_expired", "recommendation_discarded", "tuning_settings_changed", "new_cycle_required"),
                ("expired", "discarded", "expired", "none"), lifecycle_words,
            ):
                page.evaluate("""({reason,reviewState})=>{
                  window.pidStatus={...pidStatus,pid_learning_status:{...pidStatus.pid_learning_status,
                    status:'collecting',reason},pid_review:{...pidReviewFixture,state:reviewState,reason}};
                  const states={...card._hass.states,'sensor.pid_status':{state:'controlling',attributes:pidStatus}};
                  for(const scope of ['dry','generic']){
                    states['button.'+scope+'_approve']={...states['button.'+scope+'_approve'],state:'unavailable'};
                    states['button.'+scope+'_discard']={...states['button.'+scope+'_discard'],
                      state:reviewState==='expired'?'unknown':'unavailable'};
                  }
                  card._hass={...card._hass,states};
                  card._hemFullRender127(card._hemControllerDialog126,'device');
                }""", {"reason": reason, "reviewState": review_state})
                expect(active).to_have_attribute("data-hem-pid-state074", "collecting")
                expect(active).to_contain_text(expected_text)
                assert active.locator("[data-hem-pid-proposal074]").count() == 0
                expect(pid.locator('[data-hem-pid-review-b18="approve"] button[data-hem-full-apply127]')).to_be_disabled()
                for key in ("kp", "ki", "kd"):
                    expect(pid.locator(f'[data-hem-full-row127="number.dry_{key}"]')).to_be_visible()
                    assert pid.locator(f'[data-hem-full-row127="number.dry_{key}"]').count() == 1
                assert page.evaluate("kpInput===card._hemControllerDialog126.node.querySelector('[data-hem-full-value127=\"number.dry_kp\"]')")
                assert pid.locator("[data-hem-pid-status074]").count() == 1
                assert modal.evaluate("node=>node.scrollWidth<=node.clientWidth+1")
            page.evaluate("""()=>{
              window.pidStatus={...pidStatus,pid_learning_status:{...pidStatus.pid_learning_status,
                status:'applied',reason:'applied'},pid_review:{...pidReviewFixture,state:'applied',reason:'applied'},
                pid_control_parameters:{...pidReviewFixture.apply},pid_last_calibration:{
                  at:Date.now()/1000,operating_mode:'dry',previous_gains:pidReviewFixture.current,
                  applied_gains:pidReviewFixture.apply}};
              card._hass={...card._hass,states:{...card._hass.states,
                'sensor.pid_status':{state:'controlling',attributes:pidStatus}}};
              card._hemFullRender127(card._hemControllerDialog126,'device');
            }""")
            expect(active).to_have_attribute("data-hem-pid-state074", "applied")
            expect(active.locator("[data-hem-pid-last074]")).to_contain_text("→")
            assert active.locator("[data-hem-pid-proposal074]").count() == 0
            expect(inactive).to_have_attribute("data-hem-pid-state074", "inactive")
            # Refresh status in place; keep the PID accordion and native inputs.
            page.evaluate("""()=>{window.kpInput=card._hemControllerDialog126.node.querySelector('[data-hem-full-value127="number.dry_kp"]');
              if(!kpInput)throw Error('Missing visible gain input');
              window.pidStatus={...pidStatus,pid_learning_status:{...pidStatus.pid_learning_status,
                status:'cooldown',reason:'calibration_cooldown'},pid_review:{state:'none'}};
              card._hass={...card._hass,states:{...card._hass.states,
                'sensor.pid_status':{state:'controlling',attributes:pidStatus}}};
              card._hemFullRender127(card._hemControllerDialog126,'device');}""")
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
    print("PASS: Advanced Kp/Ki/Kd, Basic status/review actions, active/inactive mode evidence, proposal/history, stable redraws, EN/EL/DE at 320/390/760px")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-only", action="store_true")
    args = parser.parse_args()
    node_checks()
    if not args.node_only:
        browser_checks()
