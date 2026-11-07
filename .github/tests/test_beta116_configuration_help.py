"""Beta116: the card exposes each rendered setting's purpose-specific help.

--logic-only runs production rendering and refresh signatures in Node. The full
run also checks the real information disclosure, escaping, keyboard close and
no accidental setting/service changes in Chromium.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / 'frontend/air-quality-advisor-card.js'


def fixture():
    path = ROOT / '.github/tests/test_beta112_room_activity.py'
    tree = ast.parse(path.read_text(), filename=str(path))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'fixture')
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    states = namespace['fixture']()
    help_text = 'Choose who controls this device: existing thermostat, HEM automatic, manual target, PID, or off.'
    states['select.method_cooler']['attributes']['configuration_help'] = help_text
    common = {key: states['select.method_cooler']['attributes'][key]
              for key in ('area_id', 'source_device_id', 'source_entity_ids')}
    extra = {
        'switch.cooler_maximum': {'state': 'off', 'attributes': {
            **common, 'equipment_option_role': 'policy', 'setting_key': 'native_full_output',
            'native_full_output_supported': True, 'native_full_output_modes': ['cool'],
            'setting_label': 'Maximum target by mode (Cooling)', 'configuration_help':
            'ON: request this device’s minimum cooling temperature.\n\n'
            'OFF: leave its native target unchanged.\n- HEM still decides when to run.\n'
            '<img src=x onerror="unsafe()">'}},
        'select.cooler_calibration': {'state': 'imc_lambda', 'attributes': {
            **common, 'pid_calibration_role': 'method', 'options': ['manual', 'imc_lambda'],
            'configuration_help': 'Choose how PID gains are calculated from the measured device and room response.'}},
        'number.cooler_gain': {'state': '2', 'attributes': {
            **common, 'pid_calibration_field': 'pid_process_gain', 'min': 0, 'max': 100,
            'step': 0.1, 'configuration_help': 'Measured temperature change per unit of device output, used to calculate PID gains.'}},
        'button.cooler_calibrate': {'state': 'unknown', 'attributes': {
            **common, 'pid_calibration_role': 'apply',
            'configuration_help': 'Calculate PID gains from the entered response measurements and selected method.'}},
    }
    states.update(extra)
    return states


states = fixture()
script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const card=Object.create(customElements.get('home-environment-manager-card').prototype);
card._hass={language:'en',states:input,localize:()=>undefined,
 callService:()=>{throw Error('Help sent a service call')}};
card._interactions66=true;card._detailsExpanded66=new Set();
card._windowSwitchPending66=new Set();card._calibrationExpanded65=new Set();
card._expanded=new Set();card._areaDeviceIds=new Map();card._config={entity:'sensor.hem'};
const room=input['sensor.hem'].attributes.dashboard.rooms.find(r=>r.area_id==='cool');
const html=card._controllerPanel(room);
const ids=['select.method_cooler','switch.cooler_maximum','select.cooler_calibration','number.cooler_gain','button.cooler_calibrate'];
for(const id of ids){
 const prefix=id==='switch.cooler_maximum'?'device-option:':'setting-help:';
 assert.ok(html.includes('data-detail-id="'+prefix+id+'"'),id+' help missing');
 for(const paragraph of input[id].attributes.configuration_help.split(/\n\s*\n/))
   assert.ok(html.includes('<p class="hem-help-text116">'+paragraph.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')+'</p>'),id+' wrong help');
}
assert.ok(!html.includes('<img src=x'),'help HTML executed');
assert.ok(html.includes('data-climate-method="select.method_cooler"'));
assert.ok(html.includes('data-device-quick-switch8="switch.cooler_maximum"'));
assert.ok(html.includes('aria-checked="false"'));
assert.ok(html.includes('data-pid-model-input="pid_process_gain"'));
assert.ok(html.includes('data-save-pid-model="number.cooler_gain"'));
assert.ok(html.includes('data-apply-pid-calibration="button.cooler_calibrate"'));
assert.equal(card._configurationHelp116('<input>', 'number.test', {attributes:{}}, 'Test'),'<input>');
assert.equal(card._configurationHelp116('<input>', 'number.test', {attributes:{configuration_help:{bad:'shape'}}}, 'Test'),'<input>');
assert.equal(card._configurationHelp116('', 'number.test', {attributes:{configuration_help:'Text'}}, 'Test'),'');
const signature=card._controllerSignature();
input['select.method_cooler'].attributes.configuration_help='Updated localized setting explanation';
assert.notEqual(card._controllerSignature(),signature,'help-only update cannot refresh the card');
console.log('BETA116_CONFIGURATION_HELP_RENDER_ESCAPING_REFRESH=PASS');
"""
result = subprocess.run([shutil.which('node') or 'node', '-e', script, str(CARD)],
    input=json.dumps(states), text=True, capture_output=True, check=True)
print(result.stdout.strip())
if '--logic-only' in sys.argv:
    raise SystemExit(0)

from playwright.sync_api import sync_playwright

chrome = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH') or shutil.which('chromium') or shutil.which('google-chrome')
assert chrome and Path(chrome).is_file(), 'Chromium required'
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=chrome, headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width': 590, 'height': 950})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content('<!doctype html><html><body><main></main></body></html>')
    page.add_script_tag(path=str(CARD))
    page.evaluate("""states=>{
      window.calls=[];window.card=document.createElement('home-environment-manager-card');
      document.querySelector('main').append(card);
      card._hass={language:'en',states,localize:()=>undefined,
        callService:(...args)=>{calls.push(args);return Promise.resolve()}};
      card._config={entity:'sensor.hem'};card._renderContent(true);
    }""", states)
    row = page.locator('[data-room-fold87="cool"]')
    row.locator('.hem-room-name87').click()
    # Open the existing device disclosure before reaching its settings.
    device = row.locator('[data-device-fold87="climate.managed_cooler"]')
    if device.get_attribute('open') is None:
        device.locator(':scope > summary .hem-device-state87').click()
    method = row.locator('[data-detail-id="setting-help:select.method_cooler"]')
    method.locator(':scope > summary').click()
    body = page.locator('.hem-floating-info87')
    body.wait_for(state='visible')
    assert states['select.method_cooler']['attributes']['configuration_help'] in body.text_content()
    assert row.locator('[data-climate-method="select.method_cooler"]').input_value() == 'pid'
    page.keyboard.press('Escape')
    # Native dismissal hides synchronously; its queued toggle removes the node.
    body.wait_for(state='detached')
    assert body.count() == 0, 'Escape did not close setting help'
    maximum = row.locator('[data-detail-id="device-option:switch.cooler_maximum"]')
    maximum.locator(':scope > summary').click()
    body.wait_for(state='visible')
    assert body.locator('img').count() == 0, 'help content became HTML'
    assert '<img src=x' in body.text_content()
    assert row.locator('[data-device-quick-switch8="switch.cooler_maximum"]').get_attribute('aria-checked') == 'false'
    assert page.evaluate('calls') == [], 'opening help mutated a setting'
    assert not errors, errors
    browser.close()
print('BETA116_CONFIGURATION_HELP_DISCLOSURE_READ_ONLY=PASS')
