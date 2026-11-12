"""Settings presentation does not change configuration, scope or service targets."""
from pathlib import Path
from copy import deepcopy
import ast
import json
import os
import runpy
import shutil
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'custom_components/environment_manager'
CARD=SRC/'frontend/air-quality-advisor-card.js'
POLICY=json.loads((SRC/'frontend/settings-audit-policy.json').read_text())
CHROME=os.getenv('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
assert CHROME
room=runpy.run_path(str(ROOT/'.github/tests/test_beta114_room_settings.py'))
base=runpy.run_path(str(ROOT/'.github/tests/test_beta108_setpoint_feedback_browser.py'))
tree=ast.parse((ROOT/'.github/tests/test_062b7_autosave.py').read_text())
setup=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
           and any(isinstance(t,ast.Name) and t.id=='SETUP' for t in n.targets))
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=CHROME,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 for language,width in [('en',760),('el',320),('de',390)]:
  page=browser.new_page(viewport={'width':width,'height':950});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content('<style>body{margin:0;font:14px Arial;--card-background-color:#222;--primary-text-color:#eee;--secondary-text-color:#aaa}</style>')
  page.evaluate(base['icon_fixture']());page.add_script_tag(path=str(CARD))
  states=deepcopy(base['fixture_definitions']()['states'])
  states['sensor.hem']['attributes']['dashboard']['rooms']=states['sensor.hem']['attributes']['dashboard']['rooms'][:2]
  page.evaluate(room['SETUP'],{'states':states,'form':room['FORM'],'native':False})
  page.evaluate('(form)=>window.roomSchema=form',room['FORM']);page.evaluate(setup)
  page.evaluate('lang=>card._hass.language=lang',language)
  page.evaluate(r'''()=>{
    window.auditAdd=(id,key,value,attrs,device='living-device')=>{
      card._hass.states[id]={state:value,attributes:{min:0,max:100,step:1,friendly_name:key,...attrs}};
      registry.push({entity_id:id,translation_key:key,device_id:device,unique_id:'entry0_area_room0_'+id.replace('.','_'),platform:'environment_manager',config_entry_id:'entry0'});
    };
    auditAdd('number.pid_gain','equipment_kp','10',{friendly_name:'Proportional gain',settings_scope:'operating_mode',setting_key:'kp'});
    auditAdd('number.met','area_area_environment_met','1',{friendly_name:'Activity MET'});
    auditAdd('number.radon','area_area_environment_radon_reference_bq_m3','50',{});
    auditAdd('number.min_on','equipment_min_on_seconds','5',{friendly_name:'Minimum ON time'});
    auditAdd('switch.verified','equipment_sensor_verified','on',{});
    auditAdd('number.future','future_new_setting','10',{});
    auditAdd('number.age','global_occupancy_source_stale_minutes','240',{max:1440},'homehub');
    auditAdd('number.away','global_occupancy_away_cooldown_minutes','10',{},'homehub');
    auditAdd('select.home_policy','home_global_policy_home_policy','any_home',{options:['any_home','all_home']},'homehub');
    homeData.general_source_stale_minutes=240;
    homeForm.data_schema.push({name:'general_source_stale_minutes',default:240,selector:{number:{min:10,max:1440,step:1}}});
  }''')
  assert page.evaluate('card._settingsAuditPolicyB8()')==POLICY
  # All catalog keys and future controls have an explicit deterministic policy.
  classified=page.evaluate('(keys)=>keys.map(k=>card._settingsAuditLevelB8({domain:"number",reg:{translation_key:k}}))',list(POLICY['advanced']))
  assert set(classified)=={'advanced'}
  for key in ('equipment_min_on_seconds','equipment_min_off_seconds','equipment_max_on_seconds',
              'equipment_sensor_verified','equipment_pause_on_window_open','equipment_off_state_watchdog_mode','new_future_setting'):
   assert page.evaluate('(key)=>card._settingsAuditLevelB8({domain:"number",reg:{translation_key:key}})',key)=='primary'
  assert page.evaluate("card._openRoomSettings114('room0')")
  page.wait_for_function('card._roomSettingsDialog114?.fullRegistry127?.length===15')
  modal=page.locator('dialog.hem-room-options114')
  search=modal.locator('[data-settings-search-b8]');advanced=modal.locator('[data-settings-advanced-b8]')
  expect(search).to_be_visible();expect(advanced).not_to_be_checked()
  for entity in ('number.pid_gain','number.met','number.radon'):
   assert modal.locator(f'[data-hem-full-row127="{entity}"]').get_attribute('hidden') is not None
  for entity in ('number.min_on','switch.verified','number.future'):
   assert modal.locator(f'[data-hem-full-row127="{entity}"]').get_attribute('hidden') is None
  before=page.evaluate('JSON.stringify({writes,committed,homeData})')
  advanced.check();page.evaluate('card._renderContent(true)')
  assert modal.locator('[data-hem-full-row127="number.pid_gain"]').get_attribute('hidden') is None
  advanced.uncheck();search.fill('proportional')
  gain=modal.locator('[data-hem-full-value127="number.pid_gain"]');expect(gain).to_be_visible()
  assert not advanced.is_checked() # Search discovers advanced controls without another setting.
  assert page.evaluate('JSON.stringify({writes,committed,homeData})')==before
  search.fill('no matching control');expect(modal.locator('[data-settings-empty-b8]')).to_be_visible()
  search.fill('proportional');gain.fill('22');gain.dispatch_event('change')
  page.wait_for_function('writes.length===1')
  assert page.evaluate('writes[0]')=={'domain':'number','action':'set_value','data':{'entity_id':'number.pid_gain','value':22}}
  gain.blur();search.fill('')
  # Keep an unconfirmed/failed edit visible even with Advanced collapsed.
  expect(gain).to_have_value('22');assert modal.locator('[data-hem-full-row127="number.pid_gain"]').get_attribute('hidden') is None
  page.evaluate("ack('number.pid_gain',22)")
  assert modal.locator('[data-hem-full-row127="number.pid_gain"]').get_attribute('hidden') is not None
  search.fill('number.future');expect(modal.locator('[data-hem-full-value127="number.future"]')).to_be_visible()
  assert modal.locator('[data-settings-tools-b8]').evaluate('n=>n.scrollWidth<=n.clientWidth+1')
  page.evaluate('card._closeRoomSettings114(false)');assert page.evaluate('card._openHomeSettings128()')
  page.wait_for_function('card._homeSettingsDialog128?.fields?.length===5 && card._homeSettingsDialog128?.fullRegistry127?.length===15')
  home=page.locator('dialog.hem-home-options128')
  for entity in ('number.age','number.away','select.home_policy'):
   assert home.locator(f'[data-hem-full-row127="{entity}"]').count()==0
  for key in ('general_source_stale_minutes','general_away_cooldown_minutes','general_home_policy'):
   assert home.locator(f'[data-hem-home-field128="{key}"]').count()==1
  # Without a usable Options form, native controls must remain a fallback.
  assert page.evaluate('''()=>{const s=card._homeSettingsDialog128,old=s.fields;s.fields=null;
    const ids=card._hemFullFields127(s,'home').map(f=>f.id);s.fields=old;
    return ['number.age','number.away','select.home_policy'].every(id=>ids.includes(id));}''')
  assert not errors,errors
  page.close()
 browser.close()
print('PASS: exact identities; advanced search/discovery; protected safety/action controls; unchanged settings; autosave targets; 3 verified Home aliases; EN/EL/DE at 320/390/760px')
