"""Truthful performance-adaptation diagnostics on the production HEM card.

Pure Python and Node checks cover stale/mode evidence and view projection.
Chromium checks the real settings dialog, compact localized layouts and
preservation of controls/disclosures. All transports are local fixtures.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import importlib.util
import json
import math
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
CARD = SOURCE / "frontend/home-environment-manager-card.js"


def calibration_label_checks():
    catalog = runpy.run_path(str(SOURCE / "operating_mode_catalog.py"))
    for path in (SOURCE / "translations").glob("*.json"):
        translations = json.loads(path.read_text(encoding="utf-8"))
        expected = translations["entity"]["select"]["equipment_pid_calibration_method"]["state"]["adaptive_auto"]
        actual = catalog["mode_option_labels"]("pid_calibration_method", path.stem)["adaptive_auto"]
        assert actual == expected, f"{path.stem}: per-mode and device calibration labels disagree"
        assert not any(term in actual.casefold() for term in ("/day", "/ day", "/tag", "/ημέρα")), (
            f"{path.stem}: adaptive calibration no longer has a fixed daily limit")
    print("PASS: adaptive calibration labels agree across all 38 languages without a daily cap")


def status_checks():
    package = types.ModuleType("hem_074b4_status_test")
    package.__path__ = [str(SOURCE)]
    sys.modules[package.__name__] = package
    spec = importlib.util.spec_from_file_location(
        package.__name__ + ".pid_learning_status", SOURCE / "pid_learning_status.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    cfg = {"control_mode": "pid", "pid_calibration_method": "adaptive_auto",
           "operating_mode": "heat", "requested_mode": "heat"}
    raw = {"schema_version": 1, "status": "retained", "reason": "tracking_well",
           "operating_mode": "heat", "context_verified": True,
           "samples": 48, "observed_seconds": 1234.5,
           "target": 21., "band": .3, "target_semantics": "band",
           "output_kind": "acknowledged_native_command", "physical_activity": None,
           "feedback": {"metric": "temperature", "value": 21., "unit": "°C",
                        "source_ids": ["sensor.room_a", "sensor.room_b"],
                        "contributor_ids": ["sensor.room_a", "sensor.room_b"]},
           "performance": {"within_band_fraction": .98, "mean_absolute_error": .1},
           "candidate": {"kp": 9.5, "ki": .1, "kd": 0.},
           "valid_cycles": 5, "required_cycles": 5}
    before = deepcopy(raw)
    result = module.adaptive_snapshot(cfg=cfg, payload=raw)
    assert result["status"] == "retained"
    assert result["observed_seconds"] == 1234.5
    assert result["output_kind"] == "acknowledged_native_command" and result["physical_activity"] is None
    assert result["feedback"]["source_ids"] == ["sensor.room_a", "sensor.room_b"]
    assert "valid_cycles" not in result and "required_cycles" not in result
    result["feedback"]["source_ids"].append("sensor.other")
    assert raw == before, "Read-only projection must not mutate runtime evidence"
    for state in ("candidate", "ready_for_review", "verifying", "verified", "retained", "rollback"):
        result = module.adaptive_snapshot(cfg=cfg, payload={**raw, "status": state, "context_verified": False})
        assert result["status"] == "waiting"
        assert result["reason"] == "context_changed"
        assert "performance" not in result and "candidate" not in result
        assert "samples" not in result and "observed_seconds" not in result
        assert result["feedback"]["value"] == 21., "Current feedback is useful even when learning is paused"
    result = module.adaptive_snapshot(cfg=cfg, payload={**raw, "operating_mode": "dry"})
    assert result["reason"] == "context_changed" and "feedback" not in result
    for malformed in (None, [], {"status": []}, {**raw, "samples": True, "observed_seconds": math.nan}):
        result = module.adaptive_snapshot(cfg=cfg, payload=malformed)
        assert "samples" not in result and "observed_seconds" not in result
    assert module.adaptive_snapshot(cfg={**cfg, "control_mode": "manual"}, payload=raw)["status"] == "inactive"
    assert module.adaptive_snapshot(cfg={**cfg, "pid_calibration_method": "manual"}, payload=raw)["status"] == "disabled"
    print("PASS: mode/context-bound status, exact feedback, no invented cycle progress, read-only projection")


NODE = r"""
const fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync(process.argv[1],'utf8');
// Isolated production sections use the same bundled locale helpers as the full card.
const localeStart=src.indexOf('  /* HEM_TRANSLATION_DATA_B8_START */');
const localeEnd=src.indexOf('  const BRAND_TITLE =',localeStart);
assert(localeStart>0&&localeEnd>localeStart);
const localeBootstrap=src.slice(localeStart,localeEnd);
const escape=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const start=src.indexOf('  const HEM_PID_WORDS074='),end=src.indexOf('  HomeEnvironmentManagerCard.prototype._hemPidStatusRender074=',start);
assert(start>0&&end>start);
const api=new Function('escape',localeBootstrap+src.slice(start,end)+'\nreturn {pidStatusModels074,pidStatusHtml074,HEM_PID_WORDS074,HEM_PID_REASONS074,HEM_PID_PERFORMANCE_WORDS074B4,HEM_PID_PERFORMANCE_REASONS074B4};')(escape);
const NOW=Date.now()/1000;
function field(mode,key,value){return {id:'number.'+mode+'_'+key,domain:'number',label:key,
 reg:{translation_key:'equipment_'+key},state:{state:String(value),attributes:{
 settings_scope:'operating_mode',operating_mode:mode,setting_key:key,controller_id:'ctrl_a'}}};}
function fields(method='adaptive_auto'){return ['heat','dry'].flatMap(mode=>[
 field(mode,'kp',10),field(mode,'ki',.1),field(mode,'kd',0),field(mode,'control_mode','pid'),field(mode,'pid_calibration_method',method)]);}
const diagnostic={schema_version:1,engine:'performance',operating_mode:'heat',context_verified:true,
 status:'collecting',reason:'insufficient_evidence',metric:'temperature',increasing:true,
 measured:20.8,target:21,band:.3,target_semantics:'band',samples:48,observed_seconds:1234,
 feedback:{metric:'temperature',value:20.8,unit:'°C',source_ids:['sensor.room_a','sensor.room_b'],
 contributor_ids:['sensor.room_a','sensor.room_b'],aggregation:'mean',reported_at:NOW},
 performance:{within_band_fraction:.8,mean_absolute_error:.24},candidate:null};
const status={selected_operating_mode:'heat',control_method:'pid',pid_calibration_method:'adaptive_auto',
 pid_control_parameters:{kp:10,ki:.1,kd:0},pid_adaptive_status:diagnostic,
 pid_learning_status:{status:'waiting',reason:'single_feedback_sensor_required',operating_mode:'heat',valid_cycles:4,required_cycles:5},
 pid_learning_progress:{phase:'awaiting_verified_off',valid_cycles:4,required_for_auto:5},
 pid_review:{state:'none'},pid_last_calibration:null};
for(const language of ['en','el','de','fr']){
 const before=JSON.stringify(status),models=api.pidStatusModels074(fields(),status,language,NOW);
 const active=models.find(m=>m.mode==='heat'),inactive=models.find(m=>m.mode==='dry');
 assert.equal(active.state,'collecting');assert.equal(active.cycles,null);assert.equal(active.required,null);
 assert.equal(active.phase,'');assert.equal(active.rejection,'');assert.equal(inactive.state,'inactive');
 const html=api.pidStatusHtml074(models,language,'Europe/Berlin');
 assert(html.includes('sensor.room_a'));assert(html.includes('sensor.room_b'));assert(html.includes('80%'));
 assert(html.includes('data-hem-pid-observation074b4'));assert(html.includes('±'));assert(html.includes('48'));
 assert(!/24\s*(hours|ώρες|Stunden)/.test(html));assert(!html.includes('4 / 5'));assert(!html.includes('single_feedback_sensor_required'));
 assert(html.includes('aria-live="polite"'));assert.equal(JSON.stringify(status),before);
 for(const [state,reason] of [['retained','tracking_well'],['retained','stable_after_adjustment'],['retained','verification_inconclusive'],['limited','capacity_limited'],['waiting','measurement_noise'],
   ['candidate','candidate_ready'],['verifying','verification_in_progress'],['verified','performance_improved'],
   ['rollback','performance_worsened'],['applied','applied'],['evaluating','verification_in_progress'],['reverted','gains_reverted']]){
  const sample=structuredClone(status);sample.pid_adaptive_status={...diagnostic,status:state,reason};
  const model=api.pidStatusModels074(fields(),sample,language,NOW).find(m=>m.mode==='heat');
  assert.equal(model.state,state);assert(model.stateLabel.length>5);assert(model.reason.length>12);
  assert(!model.reason.includes(reason));assert.equal(model.review,null);
 }
 const sample=structuredClone(status);sample.pid_adaptive_status={...diagnostic,status:'candidate',reason:'candidate_ready',
  candidate:{kp:9.5,ki:.1,kd:0,previous_gains:{kp:10,ki:.1,kd:0}}};
 let model=api.pidStatusModels074(fields(),sample,language,NOW).find(m=>m.mode==='heat');
 let rendered=api.pidStatusHtml074([model],language,'UTC');
 assert(rendered.includes('data-hem-pid-candidate074b4'));assert(!rendered.includes('data-hem-pid-proposal074'));
 assert.deepEqual(model.gains,{kp:10,ki:.1,kd:0});assert.equal(model.last,null);
 sample.pid_adaptive_status.context_verified=false;
 model=api.pidStatusModels074(fields(),sample,language,NOW).find(m=>m.mode==='heat');
 rendered=api.pidStatusHtml074([model],language,'UTC');
 assert.equal(model.state,'waiting');assert.equal(model.candidate,null);assert.equal(model.performance,null);
 assert(!rendered.includes('data-hem-pid-observation074b4'));assert(!rendered.includes('data-hem-pid-in-band074b4'));
 assert(rendered.includes('sensor.room_a'),'Current feedback remains diagnosable while context is invalid');
 const stale=structuredClone(status);stale.pid_adaptive_status={...diagnostic,status:'waiting',reason:'single_feedback_sensor_required'};
 const staleHtml=api.pidStatusHtml074(api.pidStatusModels074(fields(),stale,language,NOW),language,'UTC');
 const index=language==='el'?1:language==='de'?2:0;
 assert(!staleHtml.includes(api.HEM_PID_REASONS074.single_feedback_sensor_required[index]));
 assert(!staleHtml.includes(api.HEM_PID_WORDS074[language]?.automatic||api.HEM_PID_WORDS074.en.automatic));
 const native=structuredClone(status);native.pid_adaptive_status.output_kind='acknowledged_native_command';
 const nativeHtml=api.pidStatusHtml074(api.pidStatusModels074(fields(),native,language,NOW),language,'UTC');
 assert(nativeHtml.includes('data-hem-pid-output074b4'));
 assert(nativeHtml.includes((api.HEM_PID_PERFORMANCE_WORDS074B4[language]||api.HEM_PID_PERFORMANCE_WORDS074B4.en).outputKinds.acknowledged_native_command));
}
for(const semantics of ['upper_threshold','lower_threshold']){
 const sample=structuredClone(status);sample.pid_adaptive_status={...diagnostic,target_semantics:semantics};
 const html=api.pidStatusHtml074(api.pidStatusModels074(fields(),sample,'en',NOW),'en','UTC');
 assert(html.includes(semantics==='upper_threshold'?'≤ 21':'≥ 21'));
}
// A new recommendation needs current lifecycle proof; a computed candidate
// alone is never represented as a ready-to-approve or applied change.
const suggest=structuredClone(status);suggest.pid_calibration_method='adaptive_suggest';
suggest.pid_adaptive_status={...diagnostic,status:'candidate',reason:'validated_improvement',evidence_id:'same-evidence'};
suggest.pid_review={algorithm:'performance_v1',state:'pending',operating_mode:'heat',
 evidence_id:'same-evidence',created_at:NOW-30,expires_at:NOW+600,current:{kp:10,ki:.1,kd:0},apply:{kp:9.5,ki:.1,kd:0}};
let model=api.pidStatusModels074(fields('adaptive_suggest'),suggest,'en',NOW).find(m=>m.mode==='heat');
assert.equal(model.state,'ready_for_review');assert(model.review);
assert(api.pidStatusHtml074([model],'en','UTC').includes('data-hem-pid-proposal074'));
for(const constraint of ['output_unverified','pending_command','other_controller_active','quiet_output_limit']){
 const held=structuredClone(suggest);held.pid_adaptive_status.constraints=[constraint];
 model=api.pidStatusModels074(fields('adaptive_suggest'),held,'en',NOW).find(m=>m.mode==='heat');
 assert.equal(model.state,'waiting',constraint);assert(model.review,'The pending proposal stays inspectable');
 assert(api.pidStatusHtml074([model],'en','UTC').includes('data-hem-pid-proposal074'));
 assert.equal(model.reason,api.HEM_PID_PERFORMANCE_REASONS074B4[constraint]?.[0]||api.HEM_PID_REASONS074[constraint]?.[0]);
 const automatic=structuredClone(status);automatic.pid_adaptive_status={...diagnostic,status:'candidate',
  reason:'validated_improvement',constraints:[constraint],candidate:{kp:9.5,ki:.1,kd:0}};
 const pending=api.pidStatusModels074(fields(),automatic,'en',NOW).find(m=>m.mode==='heat');
 assert.equal(pending.state,'waiting',constraint);assert.equal(pending.candidate,null);
 assert.equal(pending.reason,model.reason,'Both modes explain the current constraint');
}
for(const change of [s=>s.pid_review.algorithm='legacy',s=>s.pid_review.expires_at=NOW-1,
 s=>s.pid_review.current.kp=9,s=>s.pid_review.operating_mode='dry',s=>s.pid_adaptive_status.context_verified=false,
 s=>s.pid_review.evidence_id='another-evidence']){
 const sample=structuredClone(suggest);sample.pid_adaptive_status.status='ready_for_review';change(sample);
 model=api.pidStatusModels074(fields('adaptive_suggest'),sample,'en',NOW).find(m=>m.mode==='heat');
 assert.equal(model.review,null);assert.equal(model.state,'waiting');
}
const malicious=structuredClone(status);malicious.pid_adaptive_status.feedback.source_ids=['sensor.<img src=x onerror=alert(1)>'];
let html=api.pidStatusHtml074(api.pidStatusModels074(fields(),malicious,'en',NOW),'en','UTC');
assert(!html.includes('<img'));assert(html.includes('&lt;img'));
for(const [reason,values] of Object.entries(api.HEM_PID_PERFORMANCE_REASONS074B4)){
 assert.equal(values.length,3,reason);assert(values.every(v=>typeof v==='string'&&v.length>12),reason);
}
console.log('PASS: new performance status overrides legacy gates; exact means/targets/coverage; candidate and outcome truth; mode/context isolation; escaped EN/EL/DE');
"""


def node_checks():
    subprocess.run([shutil.which("node") or "node", "-e", NODE, str(CARD)], check=True)


def browser_checks():
    from playwright.sync_api import sync_playwright, expect

    chrome = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome, "Chromium is required for the settings-dialog regression"
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
              states['climate.hem_heater'].attributes.selected_operating_mode='heat';
              states['climate.hem_heater'].attributes.supported_operating_modes=['heat','dry'];
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
              for(const [key,value] of Object.entries({kp:10,ki:.1,kd:0,control_mode:'pid',pid_calibration_method:'adaptive_auto'}))add('heat',key,value);
              window.adaptive={schema_version:1,engine:'performance',status:'collecting',reason:'insufficient_evidence',
                operating_mode:'heat',context_verified:true,metric:'temperature',increasing:true,
                measured:20.8,target:21,band:.3,target_semantics:'band',samples:48,observed_seconds:1234,
                feedback:{value:20.8,metric:'temperature',unit:'°C',aggregation:'mean',
                  source_ids:['sensor.room_temperature_by_the_sofa','sensor.room_temperature_by_the_window'],
                  contributor_ids:['sensor.room_temperature_by_the_sofa','sensor.room_temperature_by_the_window']},
                performance:{within_band_fraction:.8,mean_absolute_error:.2}};
              window.pidStatus={area_id:'living',source_entity_ids:['climate.native_heater'],controller_id:'ctrl_a',
                status_code:'controlling',control_method:'pid',selected_operating_mode:'heat',pid_calibration_method:'adaptive_auto',
                pid_control_parameters:{kp:10,ki:.1,kd:0},pid_learning_status:adaptive,pid_adaptive_status:adaptive,
                pid_review:{state:'none'},pid_last_calibration:null};
              states['sensor.pid_status']={state:'controlling',attributes:pidStatus};
              window.refreshAdaptive=patch=>{
                window.adaptive={...adaptive,...patch};window.pidStatus={...pidStatus,pid_learning_status:adaptive,pid_adaptive_status:adaptive};
                card._hass={...card._hass,states:{...card._hass.states,'sensor.pid_status':{state:'controlling',attributes:pidStatus}}};
                card._hemFullRender127(card._hemControllerDialog126,'device');
              };
              card._hass={...card._hass,states:{...states}};card._renderContent(true);
            }""", language)
            room = page.locator('[data-room-fold87="living"]')
            room.locator(":scope > summary").evaluate("node=>node.click()")
            room.locator('[data-device-fold87="climate.hem_heater"] [data-open-controller-device122]').click()
            page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length===20")
            modal = page.locator(".hem-controller-options126")
            pid = modal.locator('[data-hem-full-category127="pid"]')
            pid.locator(":scope > summary").click()
            active = pid.locator('[data-hem-pid-mode074="heat"]')
            sources = active.locator('[data-hem-pid-feedback074b4="heat"]')
            level = modal.locator('[data-settings-level-b8]')
            expect(active).to_have_attribute("data-hem-pid-state074", "collecting")
            expect(active.locator('[data-hem-pid-in-band074b4]')).to_contain_text("80%")
            expect(active.locator('[data-hem-pid-target074b4]')).to_contain_text("±")
            expect(active.locator('[data-hem-pid-observation074b4]')).to_contain_text("48")
            sources.locator("summary").click()
            expect(sources).to_contain_text("sensor.room_temperature_by_the_sofa")
            expect(sources).to_contain_text("sensor.room_temperature_by_the_window")
            for selected in ("basic", "advanced", "expert"):
                level.select_option(selected)
                expect(active).to_be_visible()
                expect(active.locator('[data-hem-pid-measurement074b4]')).to_be_visible()
                expect(sources).to_have_attribute("open", "")
                gain = pid.locator('[data-hem-full-row127="number.heat_kp"]')
                if selected == "basic":
                    expect(gain).to_be_hidden()
                else:
                    expect(gain).to_be_visible()
            page.evaluate("window.gainNode=card._hemControllerDialog126.node.querySelector('[data-hem-full-value127=\"number.heat_kp\"]')")
            sources.locator("summary").focus()
            for state, reason in (("retained", "tracking_well"), ("limited", "capacity_limited"),
                                  ("verifying", "verification_in_progress"), ("verified", "performance_improved"),
                                  ("rollback", "performance_worsened"), ("reverted", "gains_reverted")):
                page.evaluate("({state,reason})=>refreshAdaptive({status:state,reason})", {"state": state, "reason": reason})
                expect(active).to_have_attribute("data-hem-pid-state074", state)
                expect(sources).to_have_attribute("open", "")
                expect(sources.locator("summary")).to_be_focused()
                assert page.evaluate("gainNode===card._hemControllerDialog126.node.querySelector('[data-hem-full-value127=\"number.heat_kp\"]')")
                assert modal.evaluate("node=>node.scrollWidth<=node.clientWidth+1")
            page.evaluate("()=>refreshAdaptive({status:'candidate',reason:'candidate_ready',candidate:{kp:9.5,ki:.1,kd:0}})")
            expect(active.locator('[data-hem-pid-candidate074b4]')).to_be_visible()
            assert active.locator('[data-hem-pid-proposal074]').count() == 0
            page.evaluate("()=>refreshAdaptive({constraints:['output_unverified']})")
            expect(active).to_have_attribute("data-hem-pid-state074", "waiting")
            assert active.locator('[data-hem-pid-candidate074b4]').count() == 0
            page.evaluate("()=>refreshAdaptive({context_verified:false,constraints:[]})")
            expect(active).to_have_attribute("data-hem-pid-state074", "waiting")
            assert active.locator('[data-hem-pid-candidate074b4],[data-hem-pid-observation074b4],[data-hem-pid-in-band074b4]').count() == 0
            expect(sources).to_have_attribute("open", "")
            assert pid.locator('[data-hem-pid-status074]').count() == 1
            assert page.evaluate("calls.length") == 0, "Status and level controls must not dispatch device commands"
            assert not errors, errors
            page.close()
        browser.close()
    print("PASS: real adaptive status at all levels, source disclosure and input identity, EN/EL/DE compact layouts")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-only", action="store_true")
    args = parser.parse_args()
    calibration_label_checks()
    status_checks()
    node_checks()
    if not args.node_only:
        browser_checks()
