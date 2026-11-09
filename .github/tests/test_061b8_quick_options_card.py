"""Compact per-device options and truthful waits through the real card.

Node checks exact setting provenance and service calls. Chromium checks the
connected UI, keyboard/touch help, live refresh, and EN/EL/DE mobile geometry.
All entities and service transport are fixtures; no hardware is contacted.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
BASE = runpy.run_path(str(ROOT / ".github/tests/test_061b7_mode_settings_card.py"))
NAME = BASE["EQUIPMENT_NAME"]
MAXIMUM_NAME = runpy.run_path(str(ROOT / "equipment_name_catalog.py"))["native_full_output_label"]
HELP = runpy.run_path(str(ROOT / "equipment_help.py"))["equipment_configuration_help"]
NOW = 1800000000.
STATES = {"en": {"on": "On", "off": "Off"},
          "el": {"on": "Ναι", "off": "Όχι"},
          "de": {"on": "An", "off": "Aus"}}
TARGET_NOTICE = {
    "en": ("Native target not confirmed", "Further attempts for this target have stopped.",
           "does not block automatic ON/OFF control"),
    "el": ("Ο στόχος της συσκευής δεν επιβεβαιώθηκε", "Οι προσπάθειες για αυτόν τον στόχο σταμάτησαν.",
           "δεν εμποδίζει τον αυτόματο έλεγχο ON/OFF"),
    "de": ("Gerätesollwert nicht bestätigt", "Weitere Versuche für diesen Sollwert wurden beendet.",
           "blockiert die automatische Ein/Aus-Regelung nicht"),
}
ATTEMPT_LABELS = {"en": ("Recorded attempts", "Limit"),
                  "el": ("Καταγεγραμμένες προσπάθειες", "Όριο"),
                  "de": ("Erfasste Versuche", "Grenze")}


def fixture(language="en"):
    states = BASE["fixture"](language)
    # One modern mode profile, one legacy fan-capable climate, and a fan with
    # PM2.5 verification cover all current shared flags without duplicating
    # the modern controller's mode-specific quiet settings.
    for entity in list(states):
        a = states[entity]["attributes"]
        if a.get("settings_scope") == "operating_mode" and (
                a.get("source_device_id") == "hardware1" or
                a.get("source_device_id") == "hardware0" and a.get("operating_mode") not in ("heat", "cool")):
            del states[entity]
    states["climate.managed_0_0"]["attributes"].update(
        supported_operating_modes=["heat", "cool"], selected_operating_mode="heat")
    states["climate.managed_0_1"]["attributes"].pop("supported_operating_modes", None)
    states["climate.managed_0_1"]["attributes"].pop("selected_operating_mode", None)
    quiet = deepcopy(states["switch.mode_quiet_sleep"])
    quiet["attributes"].update(setting_key="quiet_occupied",
        setting_label=NAME("quiet_occupied", language),
        configuration_help=HELP("quiet_occupied", language))
    states["switch.mode_quiet_occupied"] = quiet
    old, fan = "climate.physical_0_2", "fan.physical_0_2"
    states[fan] = {"state": "on", "attributes": {
        "friendly_name": "Particle filter", "percentage": 35, "supported_features": 1}}
    states.pop(old, None)
    for entity, state in states.items():
        a = state["attributes"]
        if a.get("source_entity_ids") == [old]:
            a["source_entity_ids"] = [fan]
            a["source_device_id"] = "hardware2"
            if entity.startswith("climate."):
                state["state"] = "fan_only"
                a.update(physical_primary_entity_id=fan, physical_source_state="on",
                         friendly_name="HEM Particle filter", hvac_modes=["off", "fan_only"])
            if "physical_entity_states" in a:
                a["physical_entity_states"] = {fan: "on"}

    roles = {"pause_on_window_open": {"window_pause_role": "policy"},
             "announce_device_errors": {"device_fault_role": "announce", "native_error": {"status": "ok"}},
             "announce_before_start": {"window_announcement_role": "policy"},
             "native_full_output": {"native_full_output_role": "policy", "native_full_output_supported": True}}
    ids = {"pause_on_window_open": "switch.window_", "announce_device_errors": "switch.errors_",
           "announce_before_start": "switch.airing_"}
    states.pop("switch.shared_window", None)
    for device in (0, 1, 2):
        source = fan if device == 2 else f"climate.physical_0_{device}"
        keys = ["pause_on_window_open", "announce_device_errors", "sleep_when_everyone_asleep"]
        keys += ["sensor_verified"] if device == 2 else [
            "announce_before_start", "native_full_output", "quiet_sleep", "quiet_occupied"]
        for key in keys:
            modes = ["heat", "cool"] if device < 2 else []
            full = NAME(key, language)
            label = (MAXIMUM_NAME(modes, language) if key == "native_full_output"
                     else full.partition(" · ")[2] or full.rstrip(" ·"))
            entity = ids.get(key, f"switch.{key}_") + str(device)
            states[entity] = {"state": "on" if key in ("pause_on_window_open", "announce_device_errors", "quiet_sleep", "native_full_output") else "off",
                "attributes": {"area_id": "room0", "source_device_id": f"hardware{device}",
                    "source_entity_ids": [source], "equipment_option_role": "policy",
                    "setting_key": key, "setting_label": label,
                    "configuration_help": HELP(key, language, modes=modes), **roles.get(key, {}),
                    **({"native_full_output_modes": modes} if key == "native_full_output" else {})}}
        if device < 2:
            states[f"number.airing_{device}"]["attributes"]["configuration_help"] = HELP("window_open_wait_minutes", language)
    # A legacy timed entity may survive an upgrade, but never creates a control.
    states["switch.unsupported_timer"] = {"state": "on", "attributes": {
        **states["switch.sensor_verified_2"]["attributes"],
        "setting_key": "timed_setpoint_sequence", "timed_setpoint_role": "policy",
        "timed_setpoint_supported": False}}
    states["switch.unsupported_full_output"] = {"state": "on", "attributes": {
        **states["switch.sensor_verified_2"]["attributes"],
        "setting_key": "native_full_output", "native_full_output_role": "policy",
        "native_full_output_supported": False}}
    states['climate.physical_0_0']['state'] = 'off'
    states['climate.physical_0_0']['attributes'].update(hvac_action='idle', current_temperature=20.51)
    states['climate.managed_0_0']['attributes']['physical_source_state'] = 'off'
    states['sensor.control_0_0'].update(state='pid_output_inactive')
    states['sensor.control_0_0']['attributes'].update(status_code='pid_output_inactive',
        status_reason_code='pid_output_inactive', demand_percent=4.9,
        pid_pwm_state='off_window', pid_pwm_next_window_at=NOW + 120,
        pid_pwm_next_window_seconds=120, pid_pwm_effective_cycle_seconds=3000,
        pid_pwm_wait_reason='completed_pulse_rest',
        pid_pwm_last_confirmed_on_at=NOW - 2880, pid_pwm_last_confirmed_off_at=NOW - 2733,
        pid_control_metric='temperature', pid_control_target=21, pid_control_measurement=20.51,
        native_operating_limits={'min_on_seconds': 120, 'min_off_seconds': 120, 'max_on_seconds': 7200},
        pid_control_parameters={'kp': 10, 'ki': 0, 'kd': 0, 'sample_seconds': 300, 'cycle_seconds': 600})
    return states


def target_fixture(language="en", service="set_humidity"):
    """A running binary controller whose three native target attempts ended."""
    states = fixture(language)
    source = "climate.physical_0_0"
    humidity = service == "set_humidity"
    metric, requested, reported = ("humidity", 30, 50) if humidity else ("temperature", 35, 23)
    mode = "dry" if humidity else "heat"
    native = states[source]
    native["state"] = mode
    native["attributes"].update(friendly_name="Comfee" if humidity else "Radiator",
        hvac_modes=["off", mode], hvac_action="drying" if humidity else "heating",
        supported_features=4 if humidity else 1, **{metric: reported})
    if humidity:
        native["attributes"].update(min_humidity=30, max_humidity=90, current_humidity=52)
        native["attributes"].pop("temperature", None)
    else:
        native["attributes"]["temperature_unit"] = "°C"
    states["switch.native_full_output_0"]["attributes"].update(
        native_full_output_modes=[mode], setting_label=MAXIMUM_NAME([mode], language),
        configuration_help=HELP("native_full_output", language, modes=[mode]))
    managed = states["climate.managed_0_0"]
    managed["state"] = mode
    managed["attributes"].update(control_mode="pid", selected_operating_mode=mode,
        supported_operating_modes=[mode], hvac_modes=["off", mode], physical_source_state=mode,
        controller_status={"status": "controlling"})
    for entity in list(states):
        a = states[entity]["attributes"]
        if a.get("settings_scope") == "operating_mode" and a.get("source_device_id") == "hardware0":
            del states[entity]
    states["select.target_mode"] = {"state": "pid", "attributes": {
        "source_device_id": "hardware0", "source_entity_ids": [source], "area_id": "room0",
        "settings_scope": "operating_mode", "operating_mode": mode,
        "operating_mode_label": BASE["LABELS"][language][mode], "setting_key": "control_mode",
        "setting_label": BASE["LABELS"][language]["method"], "options": ["automatic", "pid", "manual", "off"]}}
    status = states["sensor.control_0_0"]
    status["state"] = "controlling"
    status["attributes"].update(status_code="controlling", status_reason_code="controlling",
        command_pending=False, native_resume_recovery=None, automatic_recovery_requested=False,
        queued_power_switch_pending=False, native_target_attempt_budget={
            "role": "binary_pid_full_demand", "entity_id": source, "service": service,
            "mode": mode, "requested": {metric: requested}, "reported": {metric: reported},
            "temperature_unit": None if humidity else "°C", "attempts": 3, "attempt_limit": 3,
            "state": "unconfirmed", "exhausted": True, "nonblocking": True, "next_retry_at": None})
    # The sensor's explicit null must win while this separate button entity
    # still carries feedback from before the final native target attempt.
    states["button.target_resume"] = {"state": "unknown", "attributes": {
        "source_device_id": "hardware0", "source_entity_ids": [source], "area_id": "room0",
        "controller_resume_role": "continue_automatic", "native_resume_recovery": {
            "entity": source, "requested": f"{metric}={requested}", "observed": f"{metric}={reported}",
            "remaining_seconds": 60, "instructions": "STALE TARGET WAIT"}}}
    return states


NODE_CHECKS = r"""
vm.runInContext('Date.now=()=>1800000000000',context);
const tests=[];function test(name,run){tests.push({name,run});}
const plain=value=>JSON.parse(JSON.stringify(value));
function setup(locale='en'){
  const {card}=make();card._hass={...card._hass,language:locale,states:clone(supplied.fixtures[locale])};
  card._render=()=>{};return card;
}
function entries(card){return card._managedControllers('room0');}
function refresh(card,states){card._hass={...card._hass,states:clone(states)};}
function control(card,device,key,forged={}){
  const entry=entries(card)[device],option=card._deviceQuickOptions8(entry).find(item=>item.key===key);
  const attrs={'data-controller-area':'room0','data-managed-controller':entry.entityId,
    'data-device-quick-key8':key,'data-device-quick-switch8':option?.id,
    ...(option?.attribute?{[option.attribute]:option.id}:{}),...forged};
  return {disabled:false,getAttribute:name=>attrs[name]??null};
}
test('all shared options form one row; scoped flags and retired timing never duplicate',()=>{
  const card=setup(),items=entries(card),room=card._hass.states['sensor.hem'].attributes.dashboard.rooms[0];
  assert.deepEqual(plain(items.map(entry=>card._deviceQuickOptions8(entry).length)),[5,7,4]);
  assert.deepEqual(plain(card._deviceQuickOptions8(items[0]).map(item=>item.key)),[
    'pause_on_window_open','announce_device_errors','announce_before_start','native_full_output','sleep_when_everyone_asleep']);
  assert.ok(card._deviceQuickOptions8(items[2]).some(item=>item.key==='sensor_verified'));
  assert.ok(!card._deviceQuickOptions8(items[2]).some(item=>item.key==='native_full_output'));
  const html=card._controllerPanel(room);
  assert.equal((html.match(/class="hem-device-quick-row8"/g)||[]).length,3);
  for(const attribute of ['data-window-policy-switch','data-device-error-announce'])
    assert.equal((html.match(new RegExp(attribute+'=','g'))||[]).length,3);
  assert.equal((html.match(/data-window-announce-switch=/g)||[]).length,2);
  assert.equal((html.match(/data-timed-setpoint-switch=/g)||[]).length,0);
  assert.ok(!html.includes('class="hem-window-policy66"'));
  assert.ok(!html.includes('class="hem-device-error-toggle"'));
  // Scoped quiet controls are settings, not card controls. The compact card
  // keeps only its policy tiles; advanced controls remain in the device menu.
  assert.ok(!html.includes('data-mode-setting-entity="switch.mode_quiet_sleep"'));
  assert.ok(!html.includes('data-mode-setting-entity="switch.mode_quiet_occupied"'));
  const advanced=card._operatingModeControls7(items[0],'room0');
  assert.ok(advanced.includes('data-mode-setting-entity="switch.mode_quiet_sleep"'));
  assert.ok(advanced.includes('data-mode-setting-entity="switch.mode_quiet_occupied"'));
});
test('localized visible state is compact; separate icon and switch keep exact accessible purpose',()=>{
  for(const locale of ['en','el','de']){
    const card=setup(locale),entry=entries(card)[0],html=card._deviceQuickRow8(entry,'room0');
    for(const option of card._deviceQuickOptions8(entry)){
      const button=html.match(new RegExp('<button[^>]*data-device-quick-switch8="'+option.id.replaceAll('.','\\.')+'"[^>]*>[\\s\\S]*?<\\/button>'))?.[0];
      assert.ok(button,option.id);
      assert.ok(button.includes('aria-label="'+option.label+'"'));
      assert.ok(button.includes('<b>'+supplied.statesText[locale][option.state.state]+'</b>'));
      const body=button.slice(button.indexOf('>')+1,button.lastIndexOf('</button>'));
      assert.ok(!body.includes(option.label));assert.ok(!body.includes('ha-icon'));
      assert.ok(html.includes('data-detail-id="device-option:'+option.id+'"'));
      assert.ok(html.includes('icon="'+option.icon+'"'));
    }
    assert.equal(card.calls.length,0);
  }
});
test('every shared control calls only its exact configuration switch',async()=>{
  const card=setup();
  for(let device=0;device<3;device++)for(const option of card._deviceQuickOptions8(entries(card)[device])){
    await card._submitDeviceQuick8(control(card,device,option.key));
    assert.deepEqual(plain(card.calls.at(-1)),['switch',option.state.state==='on'?'turn_off':'turn_on',{entity_id:option.id}]);
  }
  assert.equal(card.calls.length,16);
  assert.ok(card.calls.every(([domain])=>domain==='switch'));
});
test('forged device/key/entity, source replacement, duplicates and stale applicability fail closed',async()=>{
  const card=setup(),key='native_full_output';
  for(const forged of [
    {'data-managed-controller':'climate.managed_0_1'},
    {'data-device-quick-switch8':'switch.native_full_output_1'},
    {'data-device-quick-key8':'announce_before_start'},
  ])await card._submitDeviceQuick8(control(card,0,key,forged));
  const saved=control(card,0,key),states=clone(card._hass.states),before=card._controllerSignature();
  states['switch.native_full_output_0'].attributes.native_full_output_supported=false;refresh(card,states);
  assert.notEqual(card._controllerSignature(),before);
  await card._submitDeviceQuick8(saved);
  assert.ok(!card._deviceQuickOptions8(entries(card)[0]).some(item=>item.key===key));
  states['switch.native_full_output_0'].attributes.native_full_output_supported=true;
  states['switch.native_full_output_0'].attributes.source_device_id='replacement';refresh(card,states);
  await card._submitDeviceQuick8(saved);
  assert.ok(!card._deviceQuickOptions8(entries(card)[0]).some(item=>item.key===key));
  states['switch.duplicate']=clone(states['switch.sleep_when_everyone_asleep_0']);refresh(card,states);
  assert.ok(!card._deviceQuickOptions8(entries(card)[0]).some(item=>item.key==='sleep_when_everyone_asleep'));
  states['switch.duplicate_window']=clone(states['switch.window_0']);refresh(card,states);
  assert.equal(entries(card)[0].windowPolicyInfo,null);
  assert.equal(card.calls.length,0);
});
test('full-output preference requires current native support and cannot fall through generic discovery',async()=>{
  const card=setup(),saved=control(card,0,'native_full_output'),states=clone(card._hass.states);
  const option=card._deviceQuickOptions8(entries(card)[0]).find(item=>item.key==='native_full_output');
  assert.equal(option.icon,'mdi:target-variant');
  assert.ok(option.help.includes('ON') && option.help.includes('OFF'));
  const before=card._controllerSignature();
  states['switch.native_full_output_0'].attributes.native_full_output_supported=false;
  refresh(card,states);assert.notEqual(card._controllerSignature(),before);
  await card._submitDeviceQuick8(saved);assert.equal(card.calls.length,0);
  assert.ok(!card._deviceQuickOptions8(entries(card)[0]).some(item=>
    item.key==='native_full_output'));
  states['switch.native_full_output_0'].attributes.native_full_output_supported=true;
  states['switch.native_full_output_0'].state='off';refresh(card,states);
  await card._submitDeviceQuick8(control(card,0,'native_full_output'));
  assert.deepEqual(plain(card.calls),[['switch','turn_on',{entity_id:'switch.native_full_output_0'}]]);
});
test('a pending write cannot duplicate; unavailable preference never guesses OFF',async()=>{
  const card=setup();let finish;
  card._hass.callService=(...args)=>{card.calls.push(args);return new Promise(resolve=>finish=resolve);};
  const a=control(card,0,'announce_device_errors'),b=control(card,0,'announce_device_errors');
  const pending=card._submitDeviceQuick8(a);
  await card._submitDeviceQuick8(b);assert.equal(card.calls.length,1);
  assert.ok(card._deviceQuickRow8(entries(card)[0],'room0').includes('aria-busy="true"'));
  finish();await pending;
  const saved=control(card,0,'announce_device_errors'),states=clone(card._hass.states);
  states['switch.errors_0'].state='unavailable';refresh(card,states);
  await card._submitDeviceQuick8(saved);assert.equal(card.calls.length,1);
  const html=card._deviceQuickRow8(entries(card)[0],'room0');
  assert.ok(html.includes('<b>—</b>'));assert.ok(html.includes('device-option:switch.errors_0'));
});
test('known native stability and HA startup have truthful labels, source evidence and countdowns',()=>{
  for(const locale of ['en','el','de']){
    const card=setup(locale),states=clone(card._hass.states),d=states['sensor.control_0_0'].attributes;
    d.status_code='native_device_stabilizing';d.readiness_until=1800000030;
    d.readiness_source_entity_ids=['climate.physical_0_0'];d.unavailable_source_entity_ids=[];
    refresh(card,states);let view=card._controllerPresentation7(entries(card)[0]);
    assert.ok(view.label.startsWith('30 s · '));assert.ok(view.waiting);
    assert.ok(view.label.includes(card._controllerStatusLabel('native_device_stabilizing')));
    assert.ok(view.evidence.some(value=>value.includes('Radiator')));
    d.status_code='startup_warmup';d.readiness_until=1800000120;refresh(card,states);
    view=card._controllerPresentation7(entries(card)[0]);assert.ok(view.label.startsWith('2 min · '));
    assert.ok(!view.label.includes(card._controllerStatusLabel('waiting_for_physical_device')));
  }
});
test('PID rest explains confirmed prior pulse and live target; infeasible demand has no invented timer',()=>{
  const card=setup(),states=clone(card._hass.states),d=states['sensor.control_0_0'].attributes;
  Object.assign(d,{status_code:'pid_output_inactive',pid_pwm_state:'off_window',
    pid_pwm_next_window_at:1800000120,pid_pwm_wait_reason:'completed_pulse_rest',
    pid_pwm_last_confirmed_off_at:1799999940,pid_control_metric:'temperature',
    pid_control_target:21,pid_control_measurement:20.51,demand_percent:4.9});
  refresh(card,states);let view=card._controllerPresentation7(entries(card)[0]);
  assert.equal(view.label,'2 min · PID · Next eligible window');assert.ok(view.waiting);
  assert.ok(view.evidence.some(value=>value.includes('previous ON pulse')));
  for(const value of ['4.9%','21 °C','20.5 °C'])assert.ok(view.evidence.some(row=>row.includes(value)),value);
  d.pid_pwm_next_window_at=1799999999;refresh(card,states);
  view=card._controllerPresentation7(entries(card)[0]);
  assert.equal(view.label,'0 s · PID · Evaluation due');
  d.pid_pwm_state='demand_below_minimum_safe_pulse';refresh(card,states);
  view=card._controllerPresentation7(entries(card)[0]);
  assert.equal(view.label,'PID · Demand below minimum safe pulse');
  assert.ok(view.evidence.some(row=>row.includes('No next pulse is scheduled')));
  assert.ok(!view.evidence.some(row=>row.includes('Next eligible pulse')));
  d.status_code='manual';refresh(card,states);view=card._controllerPresentation7(entries(card)[0]);
  assert.equal(view.waiting,false);assert.ok(!view.evidence.some(row=>row.includes('previous ON pulse')));
});
test('exhausted native targets are informational; actual telemetry and independent power waits stay truthful',()=>{
  for(const locale of ['en','el','de'])for(const service of ['set_humidity','set_temperature']){
    const card=setup(locale),states=clone(supplied.targetFixtures[locale][service]);refresh(card,states);
    const entry=entries(card)[0],notice=card._nativeTargetNotice8(entry);
    assert.equal(notice.heading,supplied.targetText[locale][0]);
    assert.ok(notice.help.includes(supplied.targetText[locale][1]));
    assert.ok(notice.help.includes(supplied.targetText[locale][2]));
    const expected=service==='set_humidity'?['30%','50%']:['35 °C','23 °C'];
    const [attempts,limit]=supplied.attemptLabels[locale];
    for(const value of [...expected,attempts+': 3 · '+limit+': 3'])
      assert.ok(notice.evidence.some(row=>row.includes(value)),value);
    const room=states['sensor.hem'].attributes.dashboard.rooms[0],html=card._controllerPanel(room);
    assert.ok(html.includes('data-native-target-notice8="climate.physical_0_0"'));
    assert.ok(!html.includes('STALE TARGET WAIT'));
    assert.ok(!html.includes('class="managed-status hem-resume-recovery"'));
    assert.ok(card._deviceSummary65(entry).includes('<b>'+expected[1]+'</b>'));
    assert.equal(card._controllerPresentation7(entry).status,'controlling');
    const d=states['sensor.control_0_0'].attributes,budget=d.native_target_attempt_budget;
    const signature=card._controllerSignature();
    budget.state='confirmed';budget.exhausted=false;refresh(card,states);
    assert.notEqual(card._controllerSignature(),signature);
    assert.equal(card._nativeTargetNotice8(entries(card)[0]),null);
    budget.state='unconfirmed';budget.exhausted=true;
    for(const change of [{attempts:2},{nonblocking:false},{entity_id:'climate.physical_0_1'},
      {role:'ordinary_setpoint'},{state:'awaiting_feedback'}]){
      const copy=clone(states);Object.assign(copy['sensor.control_0_0'].attributes.native_target_attempt_budget,change);
      refresh(card,copy);assert.equal(card._nativeTargetNotice8(entries(card)[0]),null);
    }
    d.native_resume_recovery={entity:'climate.physical_0_0',requested:'state=off',observed:'state=dry',
      instructions:'REAL POWER ACK PENDING',remaining_seconds:30};
    refresh(card,states);
    assert.ok(card._controllerPanel(room).includes('REAL POWER ACK PENDING'));
    assert.ok(card._nativeTargetNotice8(entries(card)[0]));
    assert.equal(card.calls.length,0);
  }
});
test('upgraded exhausted targets retain their full historical attempt count beside the new limit',()=>{
  for(const locale of ['en','el','de']){
    const card=setup(locale),states=clone(supplied.targetFixtures[locale].set_humidity);
    states['sensor.control_0_0'].attributes.native_target_attempt_budget.attempts=12;
    refresh(card,states);
    const notice=card._nativeTargetNotice8(entries(card)[0]),[attempts,limit]=supplied.attemptLabels[locale];
    assert.ok(notice.evidence.includes(attempts+': 12 · '+limit+': 3'));
    assert.ok(!notice.evidence.some(row=>row.includes('3 / 3') || row.includes('12 / 3')));
    assert.ok(notice.help.includes(supplied.targetText[locale][1]));
    assert.equal(card.calls.length,0);
  }
});
(async()=>{let failed=0;for(const {name,run} of tests){try{await run();console.log('PASS: '+name);}
 catch(error){failed++;console.error('FAIL: '+name+'\n'+error.stack);}}
 if(failed)process.exitCode=1;else console.log('HEM_061B8_DEVICE_QUICK_OPTIONS_LOGIC=PASS ('+tests.length+' cases)');})();
"""


def logic_checks():
    supplied = {"states": fixture(), "entities": {}, "statesText": STATES,
                "fixtures": {language: fixture(language) for language in STATES},
                "targetText": TARGET_NOTICE, "attemptLabels": ATTEMPT_LABELS, "targetFixtures": {
                    language: {service: target_fixture(language, service)
                               for service in ("set_humidity", "set_temperature")}
                    for language in STATES}}
    script = BASE["NODE_BASE"].replace("JSON.parse(process.argv[2])", "JSON.parse(fs.readFileSync(0,'utf8'))")
    result = subprocess.run(["node", "-e", script + NODE_CHECKS, str(CARD)],
                            input=json.dumps(supplied), text=True)
    if result.returncode:
        raise SystemExit(result.returncode)


def browser_checks():
    from playwright.sync_api import expect, sync_playwright
    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome, "Chromium is required for the connected card layout checks"
    destination = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
    shots = Path(destination) if destination else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 390, "height": 1000}, has_touch=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.set_content('<style>*{box-sizing:border-box}body{margin:0;background:#111;color:#eee;font:14px Arial}'
                             ':root{--primary-text-color:#eee;--secondary-text-color:#bbb;--primary-color:#03a9f4;'
                             '--card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}</style>')
            page.evaluate(BASE["BASE"]["BASE"]["PREVIOUS"]["icon_fixture"]())
            page.add_script_tag(path=str(CARD))
            page.evaluate("""({states,now})=>{
              Date.now=()=>now*1000;
              window.calls=[];window.card=document.createElement('home-environment-manager-card');
              document.body.append(card);card._config={entity:'sensor.hem'};
              card._hass={language:'en',states,localize:()=>undefined,
                callService:(...args)=>{calls.push(args);return Promise.resolve();}};
              card._roomsExpanded87=new Set(['room0']);
              card._devicesExpanded87=new Set([0,1,2].map(i=>'climate.managed_0_'+i));
              window.refresh8=(states,language='en')=>{
                card._hass={...card._hass,states:structuredClone(states),language};card._renderContent(true);
              };refresh8(states);
            }""", {"states": fixture(), "now": NOW})

            def device(index):
                return page.locator(f'[data-device-fold87="climate.managed_0_{index}"]')

            def row(index):
                return device(index).locator('.hem-device-quick-row8')

            def chip(index, key):
                return row(index).locator(f'[data-quick-option8="{key}"]')

            def state(index, key):
                return chip(index, key).locator('button[role="switch"]')

            def help_icon(index, key):
                return chip(index, key).locator('summary')

            def close_help():
                page.keyboard.press("Escape")
                expect(page.locator('.hem-floating-info87')).to_have_count(0)

            def open_help(index, key):
                close_help()
                help_icon(index, key).click()
                expect(page.locator('.hem-floating-info87')).to_be_visible()
                return page.locator('.hem-floating-info87')

            def assert_geometry(language, width):
                for index, expected_count in ((0, 5), (1, 7), (2, 4)):
                    expect(row(index)).to_have_count(1)
                    expect(row(index).locator('.hem-device-quick-option8')).to_have_count(expected_count)
                    geometry = row(index).evaluate("""element=>{
                      const box=e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,
                        top:r.top,bottom:r.bottom,width:r.width,height:r.height,client:e.clientWidth,scroll:e.scrollWidth};};
                      return {row:box(element),chips:[...element.children].map(chip=>({
                        ...box(chip),actions:[...chip.querySelectorAll(':scope > button,:scope > details > summary')].map(box),
                        text:box(chip.querySelector('button>b')),value:chip.querySelector('button').innerText,
                        font:getComputedStyle(chip.querySelector('button')).fontSize}))};
                    }""")
                    context = (language, width, index, geometry)
                    assert geometry["row"]["scroll"] <= geometry["row"]["client"] + 1, context
                    assert geometry["row"]["left"] >= -1 and geometry["row"]["right"] <= width + 1, context
                    tops = [item["top"] for item in geometry["chips"]]
                    assert max(tops) - min(tops) < 1, context
                    for item in geometry["chips"]:
                        assert item["value"] in STATES[language].values(), context
                        assert item["scroll"] <= item["client"] + 1, context
                        assert item["text"]["left"] >= item["left"] and item["text"]["right"] <= item["right"], context
                        for action in item["actions"]:
                            assert action["width"] >= 24 and action["height"] >= 24, context
                    for left, right in zip(geometry["chips"], geometry["chips"][1:]):
                        assert left["right"] <= right["left"], context

            for language in ("en", "el", "de"):
                states = fixture(language)
                page.evaluate("([s,l])=>refresh8(s,l)", [states, language])
                # Per-mode control and parameter disclosures still exist, and
                # their own quiet flag is not repeated in the shared toolbar.
                expect(device(0).locator('.hem-operating-mode7')).to_have_count(2)
                assert chip(0, 'quiet_sleep').count() == 0
                assert device(0).locator('[data-mode-setting-entity="switch.mode_quiet_sleep"]').count() == 1
                assert page.locator('.hem-window-policy66,.hem-device-error-toggle').count() == 0
                for width in (320, 390):
                    page.set_viewport_size({"width": width, "height": 1000})
                    assert_geometry(language, width)
                    if shots:
                        for index in (0, 1):
                            device(index).screenshot(path=str(shots / f"061b8-quick-options-{language}-{width}-device{index}.png"), animations="disabled")
                    for key in ('pause_on_window_open', 'announce_device_errors', 'announce_before_start',
                                'sleep_when_everyone_asleep', 'native_full_output'):
                        pop = open_help(0, key)
                        entity = state(0, key).get_attribute('data-device-quick-switch8')
                        expected = states[entity]['attributes']['configuration_help']
                        paragraphs = pop.locator('.hem-help-text116').all_text_contents()
                        assert expected.split('\n\n') == paragraphs[:len(expected.split('\n\n'))], (language, key, paragraphs)
                        bounds = pop.evaluate("e=>({left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right,client:e.clientWidth,scroll:e.scrollWidth})")
                        assert bounds['left'] >= 0 and bounds['right'] <= width and bounds['scroll'] <= bounds['client'] + 1, (language, width, key, bounds)
                        assert page.evaluate('calls.length') == 0
                        if shots and key == 'native_full_output':
                            page.screenshot(path=str(shots / f"061b8-quick-help-{language}-{width}.png"), full_page=False)
                        # Second click is a close, including a live state refresh.
                        page.evaluate("([s,l])=>refresh8(s,l)", [states, language])
                        expect(page.locator('.hem-floating-info87')).to_be_visible()
                        help_icon(0, key).click()
                        expect(page.locator('.hem-floating-info87')).to_have_count(0)
                close_help()

            states = fixture()
            page.evaluate("s=>refresh8(s)", states)
            # Real touch and keyboard disclosure actions are read-only.
            icon = help_icon(0, 'announce_device_errors')
            icon.tap()
            expect(page.locator('.hem-floating-info87')).to_be_visible()
            icon.tap()
            expect(page.locator('.hem-floating-info87')).to_have_count(0)
            icon.focus()
            page.keyboard.press('Enter')
            expect(page.locator('.hem-floating-info87')).to_be_visible()
            close_help()
            assert icon.evaluate('e=>e===e.getRootNode().activeElement')
            open_help(0, 'pause_on_window_open')
            page.mouse.click(1, 1)
            expect(page.locator('.hem-floating-info87')).to_have_count(0)
            assert page.evaluate('calls.length') == 0

            # All 16 states are real independent toggles. No native climate/fan
            # service and no neighbouring controller's flag can be addressed.
            expected_calls = []
            for index in (0, 1, 2):
                controls = row(index).locator('button[role="switch"]')
                keys = controls.evaluate_all("items=>items.map(e=>e.dataset.deviceQuickKey8)")
                for key in keys:
                    button = state(index, key)
                    entity = button.get_attribute('data-device-quick-switch8')
                    expected_calls.append(['switch', 'turn_off' if states[entity]['state'] == 'on' else 'turn_on', {'entity_id': entity}])
                    button.click()
                    page.wait_for_function('(count)=>calls.length===count', arg=len(expected_calls))
            assert page.evaluate('calls') == expected_calls

            # The waiting-time editor belongs in its help bubble, only when
            # that device's window announcement setting is enabled.
            states['switch.airing_0']['state'] = 'on'
            page.evaluate("s=>refresh8(s)", states)
            pop = open_help(0, 'announce_before_start')
            timeout = pop.locator('[data-window-wait-input="number.airing_0"]')
            timeout.fill('31')
            pop.locator('[data-save-window-wait="number.airing_0"]').click()
            assert page.evaluate('calls.length') == len(expected_calls)
            timeout.fill('0')
            pop.locator('[data-save-window-wait="number.airing_0"]').click()
            expected_calls.append(['number', 'set_value', {'entity_id': 'number.airing_0', 'value': 0}])
            page.wait_for_function('(count)=>calls.length===count', arg=len(expected_calls))
            assert page.evaluate('calls') == expected_calls
            timeout.focus()
            close_help()
            assert help_icon(0, 'announce_before_start').evaluate('e=>e===e.getRootNode().activeElement')
            assert page.evaluate('card._focusedEditor===null'), 'Dismissed help cannot retain an editor lock'

            forged = state(0, 'native_full_output')
            forged.evaluate("e=>{e.dataset.deviceQuickSwitch8='switch.native_full_output_1';e.click();}")
            assert page.evaluate('calls.length') == len(expected_calls)
            page.evaluate("s=>refresh8(s)", states)
            open_help(0, 'native_full_output')
            states['switch.native_full_output_0']['attributes']['native_full_output_supported'] = False
            page.evaluate("s=>refresh8(s)", states)
            expect(chip(0, 'native_full_output')).to_have_count(0)
            expect(page.locator('.hem-floating-info87')).to_have_count(0)
            assert state(1, 'native_full_output').is_enabled()
            states['switch.errors_0']['state'] = 'unavailable'
            page.evaluate("s=>refresh8(s)", states)
            assert state(0, 'announce_device_errors').is_disabled()
            assert state(0, 'announce_device_errors').inner_text() == '—'
            open_help(0, 'announce_device_errors')
            close_help()

            # A retained support flag without any qualified native modes is
            # also insufficient to show the maximum-target control.
            states['switch.native_full_output_0']['attributes'].update(
                native_full_output_supported=True, native_full_output_modes=[])
            page.evaluate("s=>refresh8(s)", states)
            expect(chip(0, 'native_full_output')).to_have_count(0)
            assert state(1, 'native_full_output').is_enabled()

            # An exhausted native RH target is information, not a controller
            # pause. Keep the native reported 50% visible and do not resurrect
            # the old target wait from the slower Continue button update.
            for language in ("en", "el", "de"):
                targets = target_fixture(language)
                page.evaluate("([s,l])=>refresh8(s,l)", [targets, language])
                for width in (320, 390):
                    page.set_viewport_size({"width": width, "height": 1000})
                    expect(device(0).locator('[data-native-target-notice8]')).to_be_visible()
                    expect(device(0).locator('.hem-resume-recovery')).to_have_count(0)
                    native_values = device(0).locator('.hem-device-data b').all_text_contents()
                    assert '50%' in native_values and '30%' not in native_values, (language, native_values)
                    assert 'STALE TARGET WAIT' not in device(0).inner_text()
                    if shots:
                        device(0).screenshot(path=str(shots / f"061b8-native-target-{language}-{width}.png"), animations="disabled")
                    device(0).locator('[data-detail-id="device-info:climate.managed_0_0"] > summary').click()
                    pop = page.locator('.hem-floating-info87')
                    expect(pop).to_be_visible()
                    evidence = pop.locator('[data-native-target-evidence8]')
                    expect(evidence).to_be_visible()
                    content = evidence.inner_text()
                    attempts, limit = ATTEMPT_LABELS[language]
                    for phrase in (*TARGET_NOTICE[language], '30%', '50%', f'{attempts}: 3 · {limit}: 3'):
                        assert phrase in content, (language, width, phrase, content)
                    bounds = pop.evaluate("e=>({left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right,client:e.clientWidth,scroll:e.scrollWidth})")
                    assert bounds['left'] >= 0 and bounds['right'] <= width and bounds['scroll'] <= bounds['client'] + 1, (language, width, bounds)
                    if shots:
                        page.screenshot(path=str(shots / f"061b8-native-target-help-{language}-{width}.png"), full_page=False)
                    close_help()
                # A different, real power command must retain its waiting
                # explanation alongside the nonblocking target notice.
                targets['sensor.control_0_0']['attributes']['native_resume_recovery'] = {
                    'entity': 'climate.physical_0_0', 'requested': 'state=off', 'observed': 'state=dry',
                    'instructions': 'REAL POWER ACK PENDING', 'remaining_seconds': 30}
                page.evaluate("([s,l])=>refresh8(s,l)", [targets, language])
                expect(device(0).locator('.hem-resume-recovery')).to_contain_text('REAL POWER ACK PENDING')
                expect(device(0).locator('[data-native-target-notice8]')).to_be_visible()
            assert page.evaluate('calls') == expected_calls
            assert not errors, errors
        except Exception:
            if shots:
                page.screenshot(path=str(shots / "061b8-quick-options-failure.png"), full_page=True)
            print('CARD_PAGE_ERRORS', errors)
            raise
        finally:
            browser.close()
    print("HEM_061B8_DEVICE_QUICK_OPTIONS_BROWSER=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--logic-only', action='store_true')
    group.add_argument('--browser-only', action='store_true')
    args = parser.parse_args()
    if not args.browser_only:
        logic_checks()
    if not args.logic_only:
        browser_checks()
