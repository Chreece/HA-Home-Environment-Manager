"""Operate scoped mode settings on the real card without physical HA services."""
from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = runpy.run_path(str(ROOT / ".github/tests/test_061b6_window_controls_card.py"))
NODE_BASE = runpy.run_path(str(ROOT / ".github/tests/test_beta122_card_details.py"))["SCRIPT"].split("const cases=[];", 1)[0]
EQUIPMENT_NAME = runpy.run_path(str(ROOT / "equipment_name_catalog.py"))["localized_equipment_name"]
LABELS = {
    "en": {"parameters": "Parameters", "selected": "Selected mode", "method": "Control method",
           "heat": "Heating", "cool": "Cooling", "dry": "Drying", "fan_only": "Fan",
           "auto": "Native automatic mode", "heat_cool": "Heating / cooling",
           "target": "Away profile · Heating target", "calibration": "PID calibration method"},
    "el": {"parameters": "Παράμετροι", "selected": "Επιλεγμένη λειτουργία", "method": "Μέθοδος ελέγχου",
           "heat": "Θέρμανση", "cool": "Ψύξη", "dry": "Αφύγρανση", "fan_only": "Ανεμιστήρας",
           "auto": "Αυτόματη λειτουργία συσκευής", "heat_cool": "Θέρμανση / ψύξη",
           "target": "Προφίλ απουσίας · Στόχος θέρμανσης", "calibration": "Μέθοδος βαθμονόμησης PID"},
    "de": {"parameters": "Parameter", "selected": "Gewählter Modus", "method": "Regelmethode",
           "heat": "Heizen", "cool": "Kühlen", "dry": "Entfeuchten", "fan_only": "Ventilator",
           "auto": "Native Automatik", "heat_cool": "Heizen / Kühlen",
           "target": "Abwesenheitsprofil · Heizungssollwert", "calibration": "PID-Kalibrierungsmethode"},
}
for locale, labels in LABELS.items():
    labels["kp"] = "PID · Kp"
    labels.update({key: EQUIPMENT_NAME(key, locale)
                   for key in ("cycle_seconds", "quiet_sleep", "pid_review_discard")})


def fixture(language="en"):
    states = BASE["fixture"]()
    labels = LABELS[language]
    modes_by_device = {0: ["heat", "cool", "dry", "fan_only", "auto", "heat_cool"],
                       1: ["heat", "cool"]}
    for device, modes in modes_by_device.items():
        managed = states[f"climate.managed_0_{device}"]
        managed["attributes"].update(supported_operating_modes=modes,
            selected_operating_mode="cool" if device == 0 else "heat",
            operating_mode_ui_labels={key: labels[key] for key in ("parameters", "selected")})
        states[f"climate.physical_0_{device}"]["attributes"].update(
            hvac_modes=["off", *modes], fan_modes=["low", "medium", "high"],
            fan_mode="low", supported_features=9)
        # These native endpoints expose single-temperature targets, not RH.
        target_modes = [mode for mode in modes if mode in ("heat", "cool")]
        states[f"switch.native_full_output_{device}"]["attributes"].update(
            native_full_output_modes=target_modes,
            setting_label=BASE["BASE"]["NAME"](target_modes, language),
            configuration_help=BASE["BASE"]["HELP"]("native_full_output", language, modes=target_modes))
        for mode in modes:
            provenance = {"area_id": "room0", "source_device_id": f"hardware{device}",
                          "source_entity_ids": [f"climate.physical_0_{device}"],
                          "settings_scope": "operating_mode", "operating_mode": mode,
                          "operating_mode_label": labels[mode]}

            def field(entity, key, value, label, **attrs):
                states[entity] = {"state": value, "attributes": {
                    **provenance, "setting_key": key, "setting_label": label,
                    "configuration_help": f"{labels[mode]} · {label}", **attrs}}

            method_id = ("select.user_renamed_method" if device == 0 and mode == "heat"
                         else f"select.method_{device}_{mode}")
            method = "pid" if (device, mode) in ((0, "heat"), (1, "cool")) else "automatic"
            options = ["existing", "automatic", "manual", "off"]
            if mode in ("heat", "cool", "dry", "fan_only"):
                options.insert(2, "pid")
            field(method_id, "control_mode", method, labels["method"], options=options)
            if mode in ("heat", "cool"):
                field(f"number.gain_{device}_{mode}", "kp", "1.2" if mode == "heat" else "9",
                      labels["kp"], min=0, max=100, step=0.1)
            if device == 0 and mode == "heat":
                field("number.cycle_0_heat", "cycle_seconds", "3600", labels["cycle_seconds"],
                      min=600, max=86400, step=60, unit_of_measurement="s")
                field("number.away_target", "target_away_heat", "18", labels["target"],
                      min=5, max=30, step=0.5, unit_of_measurement="°C")
                field("select.mode_calibration", "pid_calibration_method", "adaptive_suggest", labels["calibration"],
                      options=["manual", "imc_lambda", "adaptive_suggest"],
                      option_labels={"manual": "Manual calibration", "imc_lambda": "IMC / λ",
                                     "adaptive_suggest": "Adaptive suggestion"})
                field("switch.mode_quiet_sleep", "quiet_sleep", "off", labels["quiet_sleep"])
                field("button.mode_review_discard", "pid_review_discard", "unknown", labels["pid_review_discard"],
                      pid_review_role="discard", pending=True)
                field("button.mode_unavailable", "pid_apply_calibration", "unavailable", "Apply unavailable model")
    # Existing global entities remain registered for compatibility, but their
    # controls must not compete with the scoped mode controls on this card.
    states["select.legacy_calibration"] = {"state": "manual", "attributes": {
        "area_id": "room0", "source_device_id": "hardware0",
        "source_entity_ids": ["climate.physical_0_0"],
        "pid_calibration_role": "method", "options": ["manual", "imc_lambda"]}}
    states["switch.shared_window"] = {"state": "on", "attributes": {
        "area_id": "room0", "source_device_id": "hardware0",
        "source_entity_ids": ["climate.physical_0_0"], "window_pause_role": "policy"}}
    spoof = deepcopy(states["number.gain_0_heat"])
    spoof["attributes"]["source_device_id"] = "another-physical-device"
    states["number.wrong_device"] = spoof
    unsupported = deepcopy(states["select.method_0_cool"])
    unsupported["attributes"]["operating_mode"] = "defrost"
    states["select.unsupported_mode"] = unsupported
    room = states["sensor.hem"]["attributes"]["dashboard"]["rooms"][0]
    room.update(status="attention", high_count=1, readings=[{
        "metric": "mold", "value": 80, "available": True, "exceeded": True,
        "unit": "%", "threshold": 70, "name": "Mold indication",
        "entity_id": "derived.mold_room0", "details": {"status": "ready", "calibration_factor": 1.25},
    }])
    return states


NODE_CHECKS = r"""
const tests=[];function test(name,run){tests.push({name,run});}
const plain=value=>JSON.parse(JSON.stringify(value));
function setup(){const {card}=make();card._render=()=>{};return card;}
function refresh(card,states){card._hass={...card._hass,states:clone(states)};}
function fieldControl(card,id,value,forged={}){
  const field=card._hass.states[id],a=field.attributes,domain=id.split('.')[0];
  const controller=Object.keys(card._hass.states).find(key=>key.startsWith('climate.managed_')&&
    card._hass.states[key].attributes.source_device_id===a.source_device_id);
  const attrs={'data-controller-area':a.area_id,'data-managed-controller':controller,
    'data-mode-setting-mode':a.operating_mode,'data-mode-setting-key':a.setting_key,
    'data-mode-setting-entity':id,...(domain==='select'?{'data-mode-setting-select':id}:
      {'data-mode-setting-action':domain}),...forged};
  const input={value:String(value??''),getAttribute:key=>({
    'data-mode-setting-input':id,'data-mode-setting-mode':a.operating_mode,
    'data-mode-setting-key':a.setting_key})[key],checkValidity:()=>true,reportValidity(){}};
  return {value,disabled:false,getAttribute:key=>attrs[key]??null,
    closest:selector=>selector==='.hem-mode-number7'?{querySelector:()=>input}:null};
}
test('supported modes use metadata, own parameters, native options and one physical owner',()=>{
  const card=setup(),entries=card._managedControllers('room0');
  assert.equal(entries.length,3);
  assert.deepEqual(plain(entries[0].operatingModes.map(mode=>mode.mode)),
    ['heat','cool','dry','fan_only','auto','heat_cool']);
  assert.equal(entries[0].operatingModes[0].method.id,'select.user_renamed_method');
  assert.equal(entries[0].operatingModes.find(mode=>mode.mode==='auto').method.state.attributes.options.includes('pid'),false);
  assert.equal(entries[0].operatingModes.find(mode=>mode.mode==='fan_only').method.state.attributes.options.includes('pid'),true);
  assert.equal(entries[0].operatingModes.flatMap(mode=>mode.parameters).some(field=>field.id==='number.wrong_device'),false);
  assert.equal(entries[2].operatingModes.length,0);
  const room=card._hass.states['sensor.hem'].attributes.dashboard.rooms[0];
  const html=card._controllerPanel(room);
  assert.equal((html.match(/class="hem-operating-mode7"/g)||[]).length,8);
  assert.equal((html.match(/data-climate-method=/g)||[]).length,1);
  assert.equal((html.match(/data-pid-calibration-method=/g)||[]).length,0);
  assert.equal((html.match(/data-window-announce-switch=/g)||[]).length,2);
  assert.equal((html.match(/data-device-quick-key8="native_full_output"/g)||[]).length,2);
  assert.ok(!html.includes('data-timed-setpoint-switch'));
  assert.ok(html.includes('data-device-quick-switch8="switch.native_full_output_0"'));
  assert.ok(html.includes('data-window-policy-switch="switch.shared_window"'));
  assert.ok(!entries[0].operatingModes.some(mode=>mode.parameters.some(field=>field.key==='native_full_output')));
  // Compact card omits parameters; the separate advanced renderer remains verified.
  assert.ok(!html.includes('data-mode-setting-input='));
  const advanced=card._operatingModeControls7(entries[0],'room0');
  assert.ok(advanced.includes('data-mode-setting-input="number.cycle_0_heat"'));
  assert.ok(advanced.includes('data-mode-setting-input="number.away_target"'));
  assert.ok(!html.includes('data-operating-mode="defrost"'));
});
test('mode writes use exact native setting entities and reject forged scope and stale bounds',async()=>{
  const card=setup();
  await card._submitModeSetting7(fieldControl(card,'select.user_renamed_method','manual'));
  await card._submitModeSetting7(fieldControl(card,'number.gain_0_cool','8.1'));
  await card._submitModeSetting7(fieldControl(card,'button.mode_review_discard'));
  await card._submitModeSetting7(fieldControl(card,'switch.mode_quiet_sleep'));
  assert.deepEqual(plain(card.calls),[
    ['select','select_option',{entity_id:'select.user_renamed_method',option:'manual'}],
    ['number','set_value',{entity_id:'number.gain_0_cool',value:8.1}],
    ['button','press',{entity_id:'button.mode_review_discard'}],
    ['switch','turn_on',{entity_id:'switch.mode_quiet_sleep'}]]);
  for(const forged of [
    {'data-mode-setting-mode':'cool'},{'data-mode-setting-key':'target_away_heat'},
    {'data-managed-controller':'climate.managed_0_1'},
    {'data-mode-setting-entity':'number.gain_1_heat'},
  ])await card._submitModeSetting7(fieldControl(card,'number.gain_0_heat','2',forged));
  for(const value of ['',101,4.65])
    await card._submitModeSetting7(fieldControl(card,'number.gain_0_heat',value));
  await card._submitModeSetting7(fieldControl(card,'select.method_0_auto','pid'));
  await card._submitModeSetting7(fieldControl(card,'button.mode_unavailable'));
  assert.equal(card.calls.length,4);
  const control=fieldControl(card,'number.gain_0_heat','4.6'),next=clone(card._hass.states);
  next['number.gain_0_heat'].attributes.step=1;refresh(card,next);
  await card._submitModeSetting7(control);assert.equal(card.calls.length,4);
});
test('setting availability is independent of hardware and duplicates fail closed',()=>{
  const card=setup(),states=clone(card._hass.states);
  states['climate.managed_0_0'].state='unavailable';states['climate.physical_0_0'].state='unavailable';
  refresh(card,states);
  let heat=card._managedControllers('room0')[0].operatingModes[0];
  assert.equal(card._modeSettingAvailable7(heat.method),true);
  assert.equal(card._modeSettingAvailable7(heat.parameters.find(field=>field.key==='kp')),true);
  states['number.gain_0_heat'].state='unavailable';refresh(card,states);
  heat=card._managedControllers('room0')[0].operatingModes[0];
  assert.equal(card._modeSettingAvailable7(heat.parameters.find(field=>field.key==='kp')),false);
  states['select.duplicate']=clone(states['select.user_renamed_method']);
  states['number.duplicate']=clone(states['number.gain_0_cool']);refresh(card,states);
  const entry=card._managedControllers('room0')[0];
  assert.equal(entry.operatingModes[0].method,null);
  assert.equal(entry.operatingModes[1].parameters.some(field=>field.key==='kp'),false);
  assert.equal(card._managedControllers('room0')[1].operatingModes[0].method.id,'select.method_1_heat');
});
test('mold warning tile retains 80 percent with its 70 percent limit, never fabricates missing data',()=>{
  const card=setup(),room=card._hass.states['sensor.hem'].attributes.dashboard.rooms[0];
  assert.equal(card._roomGlance122(room).extras[0].value,80);
  const item=card._roomDetailReadings122(room)[0];assert.equal(item.overview_detail122,true);
  const html=card._metricInfo122(item);
  assert.ok(html.includes('<span class="metric-number">80 <small>%</small></span>'));
  assert.ok(html.includes('Limit 70 %'));
  assert.ok(html.includes('metric-attention'));
  const unavailable={...item,value:null,available:false,details:{status:'inputs_unavailable'}};
  assert.ok(card._metric(unavailable).includes('>- <small>%</small>'));
  assert.ok(!card._metricInfo122(unavailable).includes('metric-number'));
  assert.ok(card._metric({...item,value:NaN}).includes('>- <small>%</small>'));
});
test('qualified mold demand is separate from physical availability and saved target',()=>{
  const card=setup(),states=clone(card._hass.states),attrs=states['climate.managed_0_0'].attributes;
  const demand={mold_protection_required:true,reason:'mold_above_limit',
    mold_surface_rh:80,mold_surface_limit:70,mold_target_active:true,
    requested_humidity_target:60,effective_humidity_target:48};
  attrs.humidity_demand=demand;
  attrs.controller_status={status:'within_target_band',reason:'within_target_band'};
  states['sensor.control_0_0'].attributes.status_code='within_target_band';
  states['sensor.control_0_0'].attributes.status_reason_code='within_target_band';
  states['climate.physical_0_0'].state='unavailable';refresh(card,states);
  let entry=card._managedControllers('room0')[0],presentation=card._controllerPresentation7(entry);
  assert.equal(presentation.status,'physical_device_unavailable');
  assert.ok(presentation.demand.includes(card._metricName('mold')));
  assert.ok(presentation.evidence.join(' ').includes('80%'));
  assert.ok(presentation.evidence.join(' ').includes('48%'));
  let html=card._deviceSummary65(entry);
  assert.ok(!html.includes('Within the configured target range'));
  assert.ok(html.includes('Physical device is unavailable'));
  assert.ok(html.includes('48%'));
  assert.equal(card._hass.states['number.away_target'].state,'18');
  assert.equal(card.calls.length,0);
  attrs.humidity_demand={};attrs.controller_status.mold_demand=demand;refresh(card,states);
  assert.equal(card._controllerPresentation7(card._managedControllers('room0')[0]).status,'physical_device_unavailable');
  attrs.humidity_demand=demand;
  states['climate.physical_0_0'].state='off';refresh(card,states);
  presentation=card._controllerPresentation7(card._managedControllers('room0')[0]);
  assert.equal(presentation.status,'mold_above_limit');
  states['sensor.control_0_0'].attributes.status_code='off';refresh(card,states);
  assert.equal(card._controllerPresentation7(card._managedControllers('room0')[0]).status,'off');
  attrs.humidity_demand={mold_protection_required:false,status:'inputs_unavailable'};
  attrs.controller_status.mold_demand=demand;
  states['sensor.control_0_0'].attributes.status_code='within_target_band';refresh(card,states);
  presentation=card._controllerPresentation7(card._managedControllers('room0')[0]);
  assert.equal(presentation.qualified,false);assert.equal(presentation.status,'within_target_band');
});
(async()=>{let failed=0;for(const {name,run} of tests){try{await run();console.log('PASS: '+name);}
 catch(error){failed++;console.error('FAIL: '+name+'\n'+error.stack);}}
 if(failed)process.exitCode=1;else console.log('HEM_061B7_SCOPED_MODE_CARD_LOGIC=PASS ('+tests.length+' cases)');})();
"""


def logic_checks():
    result = subprocess.run(["node", "-e", NODE_BASE + NODE_CHECKS,
                             str(ROOT / "frontend/air-quality-advisor-card.js"),
                             json.dumps({"states": fixture(), "entities": {}})])
    if result.returncode:
        raise SystemExit(result.returncode)


def run():
    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or shutil.which("chromium") or shutil.which("google-chrome")
    shots = Path(os.environ["HEM_TEST_SCREENSHOT_DIR"]) if os.environ.get("HEM_TEST_SCREENSHOT_DIR") else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 390, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content('<style>*{box-sizing:border-box}body{margin:0;background:#111;color:#eee;font:14px Arial}'
                         ':root{--primary-text-color:#eee;--secondary-text-color:#bbb;--primary-color:#03a9f4;'
                         '--card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}</style>')
        page.evaluate(BASE["BASE"]["PREVIOUS"]["icon_fixture"]())
        page.add_script_tag(path=str(ROOT / "frontend/air-quality-advisor-card.js"))
        page.evaluate("""states=>{
          window.calls=[]; window.card=document.createElement('home-environment-manager-card');
          document.body.appendChild(card);
          card._hass={language:'en',states,localize:()=>undefined,
            callService:(...args)=>{calls.push(args);return Promise.resolve();}};
          card._config={entity:'sensor.hem'};
          card._roomsExpanded87=new Set(['room0']);
          card._devicesExpanded87=new Set([0,1,2].map(i=>'climate.managed_0_'+i));
          // Legacy editor interaction tests use a test-only full-mode
          // renderer. In production only the compact method controls are
          // shown on the card; b17 verifies the real categorized modal.
          const compactPanel=card._controllerPanel;
          card._controllerPanel=function(room){
            const template=document.createElement('template');
            template.innerHTML=compactPanel.call(this,room);
            for(const box of template.content.querySelectorAll('.hem-operating-modes7')){
              const controller=box.closest('[data-managed-climate93]')
                ?.getAttribute('data-managed-climate93');
              const entry=this._managedControllers(room.area_id)
                .find(item=>item.entityId===controller);
              if(entry)box.outerHTML=this._operatingModeControls7(entry,room.area_id);
            }
            return template.innerHTML;
          };
          window.refresh7=(states,language='en')=>{
            card._hass={...card._hass,states:structuredClone(states),language}; card._renderContent(true);
          };refresh7(states);
        }""", fixture())

        def panel(device, mode):
            return page.locator(f'[data-mode-controller="climate.managed_0_{device}"][data-operating-mode="{mode}"]')

        def method(device, mode):
            return panel(device, mode).locator('select[data-mode-setting-key="control_mode"]')

        def number(entity):
            return page.locator(f'[data-mode-setting-input="{entity}"]')

        def action(entity):
            return page.locator(f'button[data-mode-setting-entity="{entity}"]')

        def count():
            return page.evaluate("calls.length")

        parameter_panels = ((0, "heat"), (0, "cool"), (1, "heat"), (1, "cool"))

        def parameters(device, mode):
            return panel(device, mode).locator('details.hem-mode-parameters7')

        def assert_parameters_open(context):
            for device, mode in parameter_panels:
                assert parameters(device, mode).evaluate("element => element.open"), (
                    context, device, mode, "User-opened Parameters must survive the refresh")
                assert number(f"number.gain_{device}_{mode}").is_visible(), (
                    context, device, mode, "An expanded mode must expose its own parameters")

        assert page.locator('.hem-operating-mode7').count() == 8
        assert page.locator('[data-climate-method]').count() == 1, "Only the legacy third device keeps a global method"
        assert page.locator('[data-pid-calibration-method]').count() == 0
        assert page.locator('[data-window-announce-switch]').count() == 2
        assert page.locator('[data-window-policy-switch="switch.shared_window"]').count() == 1
        assert page.locator('[data-device-quick-key8="native_full_output"]').count() == 2
        assert page.locator('[data-timed-setpoint-switch]').count() == 0
        assert page.locator('[data-device-quick-switch8="switch.native_full_output_0"]').is_visible()
        assert page.locator('.hem-operating-mode7 [data-device-quick-key8="native_full_output"],.hem-operating-mode7 [data-window-policy-switch]').count() == 0
        assert panel(0, "defrost").count() == 0
        assert page.locator('[data-mode-setting-input="number.wrong_device"]').count() == 0
        assert method(0, "auto").locator('option[value="pid"]').count() == 0
        assert method(0, "heat_cool").locator('option[value="pid"]').count() == 0
        assert method(0, "fan_only").locator('option[value="pid"]').count() == 1
        assert method(0, "heat").input_value() == "pid"
        assert method(0, "cool").input_value() == "automatic"
        assert panel(0, "cool").locator('.hem-mode-selected7').inner_text() == "Selected mode"
        assert panel(0, "heat").locator('.hem-mode-selected7').count() == 0
        mold = page.locator('[data-overview-detail122="mold"]')
        assert mold.locator('.metric-number').inner_text() == "80 %"
        assert mold.locator(':scope > .metric-limit').first.inner_text() == "Limit 70 %"
        assert page.locator('.hem-room-glance87 .hem-room-air-chip89').first.locator('.hem-room-metric-value107').inner_text() == "80"

        # The first render installs the disclosure state. Exercise the same
        # summary clicks as a user instead of seeding a private pre-render Set,
        # which interaction setup correctly initializes to its empty default.
        for device, mode in parameter_panels:
            details = parameters(device, mode)
            assert not details.evaluate("element => element.open"), (device, mode)
            details.locator(':scope > summary').click()
        assert_parameters_open("initial user clicks")
        assert count() == 0, "Opening configuration panels must not call a device service"

        for language in ("en", "el", "de"):
            page.evaluate("([s,l])=>refresh7(s,l)", [fixture(language), language])
            assert_parameters_open(f"{language} locale refresh")
            assert LABELS[language]["heat"] in panel(0, "heat").locator('h4').inner_text()
            assert LABELS[language]["parameters"] in panel(0, "heat").locator('.hem-mode-parameters7>summary').inner_text()
            cycle_label = panel(0, "heat").locator('.hem-mode-number7 label').filter(
                has=number("number.cycle_0_heat")).locator(':scope > span')
            label_evidence = cycle_label.evaluate("""element => {
              const style = getComputedStyle(element);
              return {inner_text: element.innerText, text_content: element.textContent,
                outer_html: element.outerHTML, display: style.display,
                white_space: style.whiteSpace, text_transform: style.textTransform};
            }""")
            label_evidence.update(locale=language, viewport=page.viewport_size,
                expected=LABELS[language]["cycle_seconds"] + " (s)")
            print("HEM_061B7_CYCLE_LABEL=" + json.dumps(label_evidence, ensure_ascii=False), flush=True)
            if shots:
                # Capture before the assertion so a browser-only mismatch
                # leaves useful evidence in the CI artifact, not an empty folder.
                (shots / f"061b7-label-{language}.json").write_text(
                    json.dumps(label_evidence, ensure_ascii=False, indent=2), encoding="utf-8")
                try:
                    panel(0, "heat").screenshot(
                        path=str(shots / f"061b7-label-{language}.png"), animations="disabled")
                except Exception as error:
                    print(f"HEM_061B7_LABEL_SCREENSHOT_FAILED={error!r}", flush=True)
            assert cycle_label.is_visible(), label_evidence
            assert cycle_label.inner_text() == LABELS[language]["cycle_seconds"] + " (s)", label_evidence
            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                for box in page.locator('.hem-operating-mode7,.hem-mode-number7,.hem-mode-heading7').all():
                    bounds = box.evaluate("e=>({width:e.clientWidth,scroll:e.scrollWidth,left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right})")
                    assert bounds["scroll"] <= bounds["width"] + 1, (language, width, bounds)
                    assert bounds["left"] >= -1 and bounds["right"] <= width + 1, (language, width, bounds)
                if width == 320 and language in ("el", "de"):
                    assert cycle_label.evaluate("e=>{const range=document.createRange();range.selectNodeContents(e);return range.getClientRects().length}") > 1
                if shots:
                    panel(0, "heat").screenshot(path=str(shots / f"061b7-modes-{language}-{width}.png"), animations="disabled")

        states = fixture()
        page.evaluate("s=>refresh7(s)", states)
        assert_parameters_open("return to English before scoped service checks")
        method(0, "heat").select_option("manual")
        assert page.evaluate("calls") == [["select", "select_option", {"entity_id": "select.user_renamed_method", "option": "manual"}]]
        method(0, "cool").select_option("pid")
        assert page.evaluate("calls[1]") == ["select", "select_option", {"entity_id": "select.method_0_cool", "option": "pid"}]
        assert method(1, "heat").input_value() == "automatic"
        number("number.gain_0_heat").fill("4.6")
        action("number.gain_0_heat").click()
        assert page.evaluate("calls[2]") == ["number", "set_value", {"entity_id": "number.gain_0_heat", "value": 4.6}]
        number("number.gain_0_cool").fill("8.1")
        action("number.gain_0_cool").click()
        assert page.evaluate("calls[3]") == ["number", "set_value", {"entity_id": "number.gain_0_cool", "value": 8.1}]
        assert number("number.gain_1_heat").input_value() == "1.2"
        action("switch.mode_quiet_sleep").click()
        assert page.evaluate("calls[4]") == ["switch", "turn_on", {"entity_id": "switch.mode_quiet_sleep"}]
        action("button.mode_review_discard").click()
        assert page.evaluate("calls[5]") == ["button", "press", {"entity_id": "button.mode_review_discard"}]
        assert action("button.mode_unavailable").is_disabled()
        page.locator('[data-mode-setting-select="select.mode_calibration"]').select_option("imc_lambda")
        assert page.evaluate("calls[6]") == ["select", "select_option", {"entity_id": "select.mode_calibration", "option": "imc_lambda"}]

        for value in ("101", "4.65", ""):
            number("number.gain_0_heat").fill(value)
            action("number.gain_0_heat").click()
            assert count() == 7, "Native range, step and empty-value checks must prevent a service"
        for attribute, value in (("data-mode-setting-mode", "cool"),
                                 ("data-managed-controller", "climate.managed_0_1"),
                                 ("data-mode-setting-key", "target_away_heat"),
                                 ("data-mode-setting-entity", "number.gain_1_heat")):
            page.evaluate("s=>refresh7(s)", states)
            number("number.gain_0_heat").fill("2")
            action("number.gain_0_heat").evaluate("(e,[a,v])=>{e.setAttribute(a,v);e.click()}", [attribute, value])
            assert count() == 7, (attribute, value)

        # An HA refresh cannot discard a user's unfinished mode-specific edit.
        page.evaluate("s=>refresh7(s)", states)
        number("number.gain_0_heat").fill("8.5")
        number("number.gain_0_heat").evaluate("e=>window.editBefore7=e")
        updated = deepcopy(states)
        updated["number.gain_0_heat"]["state"] = "3.4"
        page.evaluate("s=>{card.hass={...card._hass,states:s}}", updated)
        page.evaluate("()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
        assert_parameters_open("live Home Assistant update with an unfinished edit")
        assert number("number.gain_0_heat").input_value() == "8.5"
        assert number("number.gain_0_heat").evaluate("e=>e===editBefore7 && e===e.getRootNode().activeElement")
        action("number.gain_0_heat").click()
        assert page.evaluate("calls[7]") == ["number", "set_value", {"entity_id": "number.gain_0_heat", "value": 8.5}]

        states["climate.managed_0_0"]["state"] = "unavailable"
        states["climate.physical_0_0"]["state"] = "unavailable"
        states["climate.managed_0_0"]["attributes"]["humidity_demand"] = {
            "mold_protection_required": True, "reason": "mold_above_limit",
            "mold_surface_rh": 80, "mold_surface_limit": 70, "mold_target_active": True,
            "requested_humidity_target": 60, "effective_humidity_target": 48}
        states["sensor.control_0_0"]["attributes"]["status_code"] = "within_target_band"
        page.evaluate("s=>refresh7(s)", states)
        assert method(0, "heat").is_enabled() and number("number.gain_0_heat").is_enabled()
        device = page.locator('[data-device-fold87="climate.managed_0_0"]')
        assert device.locator('.hem-device-state76>.hem-status-pill76').first.inner_text() == "Physical device is unavailable"
        diagnostics = device.locator('[data-detail-id="diagnostics:climate.managed_0_0"]')
        diagnostics.locator(':scope > summary').click()
        assert "Mold" in diagnostics.inner_text() and "80%" in diagnostics.inner_text()
        assert "48%" in diagnostics.inner_text()
        assert "Within the configured target range" not in diagnostics.inner_text()
        states["number.gain_0_heat"]["state"] = "unavailable"
        page.evaluate("s=>refresh7(s)", states)
        assert number("number.gain_0_heat").is_disabled() and action("number.gain_0_heat").is_disabled()
        states["number.duplicate"] = deepcopy(states["number.gain_0_cool"])
        states["select.duplicate"] = deepcopy(states["select.user_renamed_method"])
        page.evaluate("s=>refresh7(s)", states)
        assert number("number.gain_0_cool").count() == 0
        assert method(0, "heat").count() == 0
        assert panel(0, "heat").locator('select').first.is_disabled()
        assert page.locator('[data-climate-method]').count() == 1
        assert method(1, "heat").is_enabled()
        assert not errors, errors
        browser.close()
    print("HEM_061B7_SCOPED_MODE_CONTROLS=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--logic-only", action="store_true")
    options = parser.parse_args()
    logic_checks()
    if not options.logic_only:
        run()
