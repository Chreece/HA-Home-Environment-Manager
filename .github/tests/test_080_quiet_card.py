"""Quiet hours use real time selectors, exact aliases and shared device opt-in.

Node executes production classification, form adaptation and fresh Options
transactions. Optional Chromium uses the existing authenticated-menu fixtures
to exercise translated controls, autosave and mobile layout without devices.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'custom_components/environment_manager'
CARD = SOURCE / 'frontend/home-environment-manager-card.js'
SCHEMA = [
    {'name': 'quiet_hours_enabled', 'default': False, 'selector': {'boolean': {}}},
    {'name': 'quiet_hours_start', 'default': '22:00:00', 'selector': {'time': {}}},
    {'name': 'quiet_hours_end', 'default': '08:00:00', 'selector': {'time': {}}},
]

NODE = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const schema=JSON.parse(fs.readFileSync(0,'utf8')),classes=new Map();
global.HTMLElement=class {};global.window={customCards:[]};
global.document={createElement:()=>({addEventListener(){},append(){}})};
global.customElements={get:name=>classes.get(name),define:(name,ctor)=>classes.set(name,ctor)};
let source=fs.readFileSync(process.argv[1],'utf8');
source=source.replace(/\}\)\(\);\s*$/,
 'globalThis.quietTest080={homeType128,homeGroup128,hemFieldCategory141,hemHomeNativeDuplicate141,auditPolicyB8,auditVisibleB8};})();');
vm.runInThisContext(source);
const api=quietTest080,Proto=classes.get('home-environment-manager-card').prototype;
const make=()=>{const card=Object.create(Proto);card._hass={language:'en',states:{},entities:{}};
 card._language=()=> 'en';card._hemFullContext127=()=>true;
 card._hemSettingLabel062=(_id,_state,reg)=>reg.translation_key;return card;};
const card=make(),saved={flowId:'flow',entryId:'entry0',draft:{}};
const fields=card._homeFields128(saved,{type:'form',step_id:'setup_general',flow_id:'flow',data_schema:schema});
assert.deepEqual(fields.map(f=>f.kind),['boolean','time','time']);
assert(fields.every(f=>f.category==='presence'));
for(const field of fields){
 assert.equal(api.auditPolicyB8.home_option_levels[field.name],'basic');
 const html=card._homeFieldHtml128(field,{errors:{}});
 if(field.kind==='time'){
  assert.match(html,/<input type="time" step="1" required/);
  assert(html.includes('value="'+field.value+'"'));
 }
 const key='home_'+field.name,domain=field.kind==='time'?'time':'switch';
 const native={id:domain+'.renamed_'+field.name,domain,reg:{translation_key:key,
  unique_id:'entry0_home_'+key},state:{state:field.kind==='time'?field.value:'off',attributes:{}}};
 assert.equal(api.hemFieldCategory141(native,'home'),'presence');
 assert.equal(api.auditPolicyB8.native_levels[key],'basic');
 assert.equal(api.auditPolicyB8.home_aliases[key],field.name);
 assert(api.hemHomeNativeDuplicate141(native,{fields}));
 assert(!api.hemHomeNativeDuplicate141(native,{fields:[],unsupported:true}));
 for(const phase of ['dirty','saving','pending','failed','confirming'])
  assert(!api.hemHomeNativeDuplicate141(native,{fields,nativeEdits:new Map([[native.id,{phase}]])}));
}
const owner='entry0_area_living_controller',device='controller-device';
function add(id,key,mode){
 const attrs={controller_id:owner,source_entity_ids:['fan.physical'],
  ...(mode?{settings_scope:'operating_mode',operating_mode:mode,setting_key:key}:{})};
 card._hass.states[id]={state:'off',attributes:attrs};
 card._hass.entities[id]={device_id:device,platform:'environment_manager',config_entry_id:'entry0',
  unique_id:owner+(mode?'_mode_'+mode:'')+'_'+key,translation_key:'equipment_'+key};
}
add('switch.renamed_quiet','quiet_hours');
for(const mode of ['heat','cool','dry'])add('switch.'+mode+'_sleep','quiet_sleep',mode);
const deviceFields=card._hemFullFields127({entryId:'entry0',area:'living',device,
 controller:{climate:{attributes:{controller_id:owner}}}},'device');
assert.equal(deviceFields.filter(f=>f.reg.translation_key==='equipment_quiet_hours').length,1);
const shared=deviceFields.find(f=>f.id==='switch.renamed_quiet');
assert.equal(api.hemFieldCategory141(shared,'device'),'mode');
assert.equal(api.auditPolicyB8.native_levels.equipment_quiet_hours,'basic');
assert(api.auditVisibleB8({settingsAudit:{level:'basic',query:''}},shared));
assert.equal(deviceFields.filter(f=>f.state.attributes.settings_scope==='operating_mode').length,3);

async function transaction(value){
 const c=make(),commits=[],requests=[],data=Object.fromEntries(schema.map(f=>[f.name,f.default]));
 data.unchanged=17;
 const s={entryId:'entry0',connection:{},draft:{...data,quiet_hours_start:value},
  node:{querySelector:()=>null},optionsAutosave:{dirty:new Map([
   ['quiet_hours_start',{value,revision:1}]]),revision:1,running:false}};
 let queued;
 c._settingsActive=()=>true;c._settingsOptionsStatus=()=>{};c._settingsHomeFieldErrorB10=()=>{};
 c._hemFullLoad127=()=>{};c._settingsQueue=(_entry,callback)=>(queued=Promise.resolve().then(callback));
 s.api=async(method,path,payload)=>{
  requests.push({method,path,payload});
  if(method==='DELETE')return {};
  if(payload?.handler)return {type:'menu',flow_id:'transaction',handler:'entry0',menu_options:['general_settings']};
  if(payload?.next_step_id)return {type:'form',flow_id:'transaction',handler:'entry0',step_id:'setup_general',
   data_schema:[...schema,{name:'unchanged',default:17,selector:{number:{min:0,max:60}}}]};
  commits.push(payload);return {type:'create_entry',flow_id:'transaction'};
 };
 c._settingsSaveOptions(s,'home');await queued;await new Promise(setImmediate);
 return {commits,s,requests};
}
(async()=>{
 for(const value of ['00:00','06:35','23:59:59']){
  const result=await transaction(value);assert.equal(result.commits.length,1);
  assert.equal(result.commits[0].quiet_hours_start,value);
  assert.equal(result.commits[0].quiet_hours_end,'08:00:00');
  assert.equal(result.commits[0].quiet_hours_enabled,false);
  assert.equal(result.commits[0].unchanged,17);
  assert.equal(result.s.optionsAutosave.dirty.size,0);
 }
 for(const value of ['',null,12,'25:00','08:99','12:34:99','1:30','22:00+02:00']){
  const result=await transaction(value);assert.equal(result.commits.length,0,String(value));
  assert.equal(result.s.optionsAutosave.blocked,true);
 }
 console.log('080_QUIET_CARD_TIME_SELECTORS_VALIDATION_AUTOSAVE_ALIASES_AND_SHARED_DEVICE=PASS');
})().catch(error=>{console.error(error);process.exitCode=1});
"""


def browser_checks():
    from playwright.sync_api import expect, sync_playwright

    room = runpy.run_path(str(ROOT / '.github/tests/test_beta114_room_settings.py'))
    base = runpy.run_path(str(ROOT / '.github/tests/test_beta108_setpoint_feedback_browser.py'))
    tree = ast.parse((ROOT / '.github/tests/test_062b7_autosave.py').read_text())
    setup = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == 'SETUP' for target in node.targets))
    chrome = os.getenv('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
    assert chrome, 'Chromium required for quiet-hours browser checks'
    shots = Path(os.environ['HEM_TEST_SCREENSHOT_DIR']) if os.environ.get('HEM_TEST_SCREENSHOT_DIR') else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome, headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'])
        for language, width in (('en', 760), ('el', 320), ('de', 390)):
            page = browser.new_page(viewport={'width': width, 'height': 1000})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_content('<style>body{margin:0;background:#161616;color:#eee;font:14px Arial;'
                '--card-background-color:#222;--secondary-background-color:#292929;'
                '--primary-text-color:#eee;--secondary-text-color:#aaa;--divider-color:#555}</style>')
            page.evaluate(base['icon_fixture']())
            page.add_script_tag(path=str(CARD))
            states = deepcopy(base['fixture_definitions']()['states'])
            states['sensor.hem']['attributes']['dashboard']['rooms'] = states['sensor.hem']['attributes']['dashboard']['rooms'][:2]
            page.evaluate(room['SETUP'], {'states': states, 'form': room['FORM'], 'native': False})
            page.evaluate('form=>window.roomSchema=form', room['FORM'])
            page.evaluate(setup)
            catalog = json.loads((SOURCE / 'translations' / f'{language}.json').read_text())
            page.evaluate(r"""({language,catalog,schema})=>{
              card._hass.language=language;card._hass.user={id:'quiet-viewer',is_admin:true};
              card._hass.localize=key=>key.startsWith('component.environment_manager.')?
                key.slice('component.environment_manager.'.length).split('.')
                  .reduce((value,part)=>value?.[part],catalog):undefined;
              for(const field of schema){
                homeForm.data_schema.push(field);homeData[field.name]=field.default;
                const domain=field.selector.time?'time':'switch',id=domain+'.renamed_'+field.name;
                card._hass.states[id]={state:domain==='time'?field.default:'off',attributes:{
                  friendly_name:catalog.entity[domain]['home_'+field.name].name}};
                registry.push({entity_id:id,translation_key:'home_'+field.name,device_id:'homehub',
                  unique_id:'entry0_home_'+field.name,platform:'environment_manager',config_entry_id:'entry0'});
              }
              card._hass={...card._hass,states:{...card._hass.states}};card._renderContent(true);
            }""", {'language': language, 'catalog': catalog, 'schema': SCHEMA})
            assert page.evaluate('card._openHomeSettings128()')
            dialog = page.locator('dialog.hem-home-options128')
            expect(dialog.locator('[data-settings-level-b8]')).to_have_value('basic')
            page.evaluate("card._homeSettingsDialog128.node.querySelectorAll('details').forEach(node=>node.open=true)")
            for field in SCHEMA:
                key = field['name']
                row = dialog.locator(f'[data-hem-home-field128="{key}"]')
                expect(row).to_be_visible()
                expect(row).to_contain_text(catalog['options']['step']['setup_general']['data'][key])
                assert row.evaluate("node=>node.closest('[data-hem-unified141]').getAttribute('data-hem-unified141')") == 'presence'
                assert dialog.locator(f'[data-hem-full-row127$="renamed_{key}"]').count() == 0
                assert row.evaluate('node=>node.scrollWidth<=node.clientWidth+1')
            start = dialog.locator('[data-hem-home-input128="quiet_hours_start"]')
            end = dialog.locator('[data-hem-home-input128="quiet_hours_end"]')
            expect(start).to_have_attribute('type', 'time')
            expect(end).to_have_attribute('type', 'time')
            start.fill('21:30:00')
            start.dispatch_event('change')
            page.wait_for_function("homeData.quiet_hours_start.startsWith('21:30')")
            end.fill('07:15:00')
            end.dispatch_event('change')
            page.wait_for_function("homeData.quiet_hours_end.startsWith('07:15')")
            dialog.locator('[data-hem-home-input128="quiet_hours_enabled"]').check()
            page.wait_for_function('homeData.quiet_hours_enabled===true')
            assert page.evaluate('homeData.general_away_cooldown_minutes') == 10
            assert page.evaluate('writes.length') == 0
            previous = page.evaluate('optionWrites.length')
            start.fill('')
            start.dispatch_event('change')
            page.wait_for_timeout(550)
            assert page.evaluate('optionWrites.length') == previous
            assert page.evaluate("homeData.quiet_hours_start.startsWith('21:30')")
            start.fill('21:30:00')
            start.dispatch_event('change')
            if shots:
                page.screenshot(path=str(shots / f'quiet-hours-{language}-{width}.png'), full_page=True)
            assert not errors, errors
            page.close()
        browser.close()
    print('080_QUIET_CARD_BROWSER_TRANSLATED_BASIC_HOURS_ALIASES_AND_AUTOSAVE=PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--with-browser', action='store_true')
    args = parser.parse_args()
    subprocess.run([shutil.which('node') or 'node', '-e', NODE, str(CARD)],
                   input=json.dumps(SCHEMA), text=True, check=True)
    if args.with_browser:
        browser_checks()
