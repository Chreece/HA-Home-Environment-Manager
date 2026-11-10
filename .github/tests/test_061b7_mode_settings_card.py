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
  assert.equal((html.match(/class="hem-operating-mode7"/g)||[]).length,0);
  assert.equal((html.match(/data-hem-card-method129=/g)||[]).length,2);
  assert.equal((html.match(/data-climate-method=/g)||[]).length,0);
  assert.equal((html.match(/data-pid-calibration-method=/g)||[]).length,0);
  assert.equal((html.match(/data-window-announce-switch=/g)||[]).length,2);
  assert.equal((html.match(/data-device-quick-key8="native_full_output"/g)||[]).length,2);
  assert.ok(!html.includes('data-timed-setpoint-switch'));
  assert.ok(html.includes('data-device-quick-switch8="switch.native_full_output_0"'));
  assert.ok(html.includes('data-window-policy-switch="switch.shared_window"'));
  assert.ok(!entries[0].operatingModes.some(mode=>mode.parameters.some(field=>field.key==='native_full_output')));
  assert.ok(!html.includes('data-mode-setting-input="number.cycle_0_heat"'));
  assert.ok(!html.includes('data-mode-setting-input="number.away_target"'));
  assert.ok(html.includes('data-mode-setting-select="select.method_0_cool"'));
  assert.ok(html.includes('data-mode-setting-select="select.method_1_heat"'));
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
                         ':root{--primary-text-color:#eee;--secondary-background-color:#292929;'
                         '--card-background-color:#202020;--divider-color:#444;--primary-color:#03a9f4}</style>')
        page.evaluate(BASE["BASE"]["PREVIOUS"]["icon_fixture"]())
        page.add_script_tag(path=str(ROOT / "frontend/air-quality-advisor-card.js"))
        page.evaluate("""states=>{
          window.calls=[];
          window.card=document.createElement('home-environment-manager-card');
          document.body.appendChild(card);
          const entities={'sensor.hem':{config_entry_id:'entry0'}};
          for(let i=0;i<3;i++){
            entities['climate.managed_0_'+i]={
              device_id:'managed-device-'+i,config_entry_id:'entry0'};
          }
          const registry=[];
          // Native method selectors share the immutable controller identifier.
          for(const state of Object.values(states)){
            const source=state?.attributes?.source_device_id;
            if(['hardware0','hardware1','hardware2'].includes(source))
              state.attributes.controller_id='controller_'+source.slice(-1);
          }
          for(const [id,state] of Object.entries(states)){
            const source=state?.attributes?.source_device_id;
            if(!['hardware0','hardware1','hardware2'].includes(source))continue;
            const n=Number(source.slice(-1));
            if(!['number','select','switch','button','time'].includes(id.split('.')[0]))continue;
            if(id==='number.wrong_device'||id==='select.unsupported_mode')continue;
            registry.push({entity_id:id,device_id:'managed-device-'+n,
              config_entry_id:'entry0',platform:'environment_manager',
              unique_id:id==='select.control_0_'+n
                ?'controller_'+n+'_control_mode'
                :'entry0_controller_'+n+'_'+id.replace('.','_')});
          }
          window.registry7=registry;
          card._hass={language:'en',states,user:{is_admin:true},
            entities,connection:{},localize:()=>undefined,
            callWS:async request=>request.type==='config/entity_registry/list'?
              registry7:Promise.reject(Error('Unexpected WebSocket request')),
            callService:(...args)=>{calls.push(args);return Promise.resolve();}};
          card._config={entity:'sensor.hem'};
          card._roomsExpanded87=new Set(['room0']);
          card._devicesExpanded87=new Set([0,1,2].map(i=>'climate.managed_0_'+i));
          card._renderContent(true);
          card._configEntryId114='entry0';card._configEntryOwner114='sensor.hem';
          card._areaDeviceIds=new Map([['room0','room-hub']]);
          // This fixture injects a verified registry without the initial hass
          // setter. Simulate the completed registry context so a subsequent
          // native hass refresh does not reset its ownership and close dialog.
          card._deviceRegistryContext={stateId:'sensor.hem',connection:card._hass.connection};
          card._deviceRegistryLoaded=true;
          window.refresh7=(states,language='en')=>{
            card._hass={...card._hass,states:structuredClone(states),language};
            card._renderContent(true);
          };
        }""", fixture())

        # The card is a quick control surface: current method, status,
        # recovery, and binary tiles. No PID/target/calibration form fields.
        card_panel=page.locator('section[data-managed-climate93="climate.managed_0_0"]')
        assert card_panel.locator('[data-hem-card-method129]').count()==1
        assert card_panel.locator('[data-mode-setting-select="select.method_0_cool"]').count()==1
        assert card_panel.locator('[data-mode-setting-input]').count()==0
        assert card_panel.locator('[data-mode-setting-action]').count()==0
        assert card_panel.locator('.hem-calibration').count()==0
        assert card_panel.locator('[data-quick-option8]').count()>=2
        assert card_panel.locator('[data-detail-id="diagnostics:climate.managed_0_0"]').count()==1
        assert page.locator('[data-climate-method]').count()==0  # legacy method retired
        assert page.locator('[data-timed-setpoint-switch]').count()==0
        assert page.evaluate("calls.length")==0
        card_panel.locator('[data-mode-setting-select="select.method_0_cool"]').select_option('pid')
        assert page.evaluate("calls[0]")==['select','select_option',
            {'entity_id':'select.method_0_cool','option':'pid'}]

        # The device settings dialog must contain ONLY native categorized
        # settings; it must never replicate the card controller above them.
        assert page.evaluate("card._openHemControllerSettings126('room0','climate.managed_0_0')") is True
        page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length>8")
        modal=page.locator('dialog.hem-controller-options126')
        assert modal.is_visible()
        assert modal.locator('.managed-controller,.hem-device-quick-row8').count()==0
        assert modal.locator('[data-hem-full-list127="device"]').count()==1
        # The legacy device-level selector must not duplicate scoped controls.
        assert modal.locator('[data-hem-full-row127="select.control_0_0"]').count()==0
        assert modal.locator('[data-hem-full-row127="select.user_renamed_method"]').count()==1
        assert modal.locator('[data-hem-full-row127="select.method_0_cool"]').count()==1
        assert page.evaluate("calls.length")==1
        for category,entity in (
            ('mode','select.user_renamed_method'),
            ('pid','number.gain_0_heat'),
            ('mode','number.away_target'),
            ('mode','switch.mode_quiet_sleep'),
        ):
            section=modal.locator(f'[data-hem-full-category127="{category}"]')
            assert section.count()==1,(category,entity)
            assert section.locator(f'[data-hem-full-row127="{entity}"]').count()==1,(category,entity)
        assert modal.locator('[data-hem-full-row127="number.wrong_device"]').count()==0
        assert modal.locator('[data-hem-full-row127="select.unsupported_mode"]').count()==0
        assert modal.locator('[data-hem-full-row127="button.mode_unavailable"]').count()==1

        # The former standalone Targets/Fan accordions now share Control.
        assert modal.locator('[data-hem-full-category127="targets"]').count()==0
        assert modal.locator('[data-hem-full-category127="fan"]').count()==0
        assert modal.locator('[data-hem-full-category127="other"]').count()==0
        modal.locator('[data-hem-full-category127="mode"] > summary').click()
        modal.locator('[data-hem-full-category127="pid"] > summary').click()
        modal.locator('[data-hem-full-value127="select.user_renamed_method"]').select_option('manual')
        modal.locator('[data-hem-full-apply127="select.user_renamed_method"]').click()
        assert page.evaluate("calls[1]")==['select','select_option',
            {'entity_id':'select.user_renamed_method','option':'manual'}]
        gain=modal.locator('[data-hem-full-value127="number.gain_0_heat"]')
        gain.fill("4.6")
        modal.locator('[data-hem-full-apply127="number.gain_0_heat"]').click()
        assert page.evaluate("calls[2]")==['number','set_value',
            {'entity_id':'number.gain_0_heat','value':4.6}]
        modal.locator('[data-hem-full-apply127="switch.mode_quiet_sleep"]').click()
        assert page.evaluate("calls[3]")==['switch','turn_on',
            {'entity_id':'switch.mode_quiet_sleep'}]
        modal.locator('[data-hem-full-category127="pid"] [data-hem-full-value127="select.mode_calibration"]').select_option('imc_lambda')
        modal.locator('[data-hem-full-apply127="select.mode_calibration"]').click()
        assert page.evaluate("calls[4]")==['select','select_option',
            {'entity_id':'select.mode_calibration','option':'imc_lambda'}]
        assert modal.locator('[data-hem-full-apply127="button.mode_unavailable"]').is_disabled()
        assert modal.locator('option[value="imc_lambda"]').first.inner_text()=='IMC / λ'
        assert modal.locator('[data-hem-full-row127="number.gain_0_heat"] strong').first.inner_text().startswith('Heating · PID · Kp')

        # A locale refresh preserves open sections, never recreates the
        # duplicate quick panel, and presents localized scoped labels.
        for language in ('el','de','en'):
            page.evaluate("([s,l])=>refresh7(s,l)", [fixture(language),language])
            assert modal.locator('.managed-controller').count()==0
            assert modal.locator('[data-hem-full-category127="pid"]').get_attribute('open') is not None
            label=modal.locator('[data-hem-full-row127="number.gain_0_heat"] strong').first.inner_text()
            assert label.startswith(LABELS[language]['heat']+' · '),(language,label)
        gain=modal.locator('[data-hem-full-value127="number.gain_0_heat"]')
        gain.fill("8.5")
        gain.evaluate("el=>window.editBefore7=el")
        changed=fixture()
        changed['number.gain_0_heat']['state']='3.4'
        page.evaluate("s=>{card.hass={...card._hass,states:s}}",changed)
        page.evaluate("()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
        assert gain.input_value()=="8.5"
        assert gain.evaluate("el=>el===editBefore7 && el===el.getRootNode().activeElement")

        # Real missing physical feedback does not discard a saved method,
        # nor does a second controller or registry spoof enter this dialog.
        changed['climate.managed_0_0']['state']='unavailable'
        changed['climate.physical_0_0']['state']='unavailable'
        page.evaluate("s=>refresh7(s)",changed)
        assert modal.locator('[data-hem-full-row127="number.gain_0_heat"]').count()==1
        assert card_panel.locator('[data-detail-id="diagnostics:climate.managed_0_0"]').count()==1
        if shots:
            modal.screenshot(path=str(shots/'b17-categorized-device-settings.png'),animations='disabled')
        modal.locator('[data-close-hem-controller126]').click()
        assert not modal.is_visible()
        # Even an offline device must not resurrect the retired selector.
        assert page.evaluate("card._openHemControllerSettings126('room0','climate.managed_0_2')") is True
        page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length>8")
        assert modal.locator('[data-hem-full-row127="select.control_0_2"]').count()==0
        modal.locator('[data-close-hem-controller126]').click()
        assert not errors,errors
        browser.close()
    print("HEM_061B7_SCOPED_MODE_SETTINGS_IN_CATEGORIZED_DIALOG=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--logic-only", action="store_true")
    options = parser.parse_args()
    logic_checks()
    if not options.logic_only:
        run()
