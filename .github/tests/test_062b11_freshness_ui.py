"""Verify real card Automatic/Custom presentation and exact autosave targets."""
from pathlib import Path
from copy import deepcopy
import ast,os,runpy,shutil
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
CARD=ROOT/'custom_components/environment_manager/frontend/air-quality-advisor-card.js'
ROOM=runpy.run_path(str(ROOT/'.github/tests/test_beta114_room_settings.py'))
BASE=runpy.run_path(str(ROOT/'.github/tests/test_beta108_setpoint_feedback_browser.py'))
tree=ast.parse((ROOT/'.github/tests/test_062b7_autosave.py').read_text())
SETUP=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
           and any(isinstance(t,ast.Name) and t.id=='SETUP' for t in n.targets))
CHROME=os.getenv('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome');assert CHROME
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=CHROME,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 for lang,width in [('el',320),('en',390),('de',760)]:
  page=browser.new_page(viewport={'width':width,'height':900});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content('<style>body{margin:0;background:#151515;color:#eee;font:14px Arial;--card-background-color:#222;--primary-text-color:#eee}</style>')
  page.evaluate(BASE['icon_fixture']());page.add_script_tag(path=str(CARD))
  states=deepcopy(BASE['fixture_definitions']()['states'])
  states['sensor.hem']['attributes']['dashboard']['rooms']=states['sensor.hem']['attributes']['dashboard']['rooms'][:2]
  page.evaluate(ROOM['SETUP'],{'states':states,'form':ROOM['FORM'],'native':False})
  page.evaluate('(form)=>window.roomSchema=form',ROOM['FORM']);page.evaluate(SETUP)
  page.evaluate(r'''(language)=>{
    card._hass.language=language;
    const extra=[
      ['select.env_mode','auto',{options:['auto','custom'],friendly_name:'Environment freshness'},'homehub','home_global_threshold_mode_max_age_mode'],
      ['select.home_age_mode','auto',{options:['auto','custom'],friendly_name:'Home freshness'},'homehub','home_global_policy_source_freshness_mode'],
      ['number.env_minutes','90',{min:1,max:100000,step:1,friendly_name:'Custom environment age'},'homehub','global_threshold_max_age_minutes'],
      ['number.home_minutes','240',{min:10,max:1440,step:1,friendly_name:'Custom home age'},'homehub','global_occupancy_source_stale_minutes'],
      ['select.room_age_mode','auto',{options:['auto','custom'],friendly_name:'Room freshness'},'living-device','area_climate_policy_occupancy_freshness_mode'],
      ['number.room_minutes','240',{min:10,max:1440,step:1,friendly_name:'Custom room age'},'living-device','area_climate_operating_occupancy_stale_minutes'],
    ];
    for(const [id,value,attributes,device,translation] of extra){
      card._hass.states[id]={state:value,attributes};registry.push({entity_id:id,config_entry_id:'entry0',device_id:device,translation_key:translation,platform:'environment_manager',unique_id:device==='living-device'?'entry0_area_room0_'+(id.startsWith('select.')?'climate_policy_occupancy_freshness_mode':'climate_operating_occupancy_stale_minutes'):'entry0_home_'+id.replace('.','_')});
    }
    Object.assign(homeData,{general_source_freshness_mode:'auto',general_source_stale_minutes:240,
      global_threshold_max_age_mode:'auto',global_threshold_max_age_minutes:90});
    homeForm.data_schema.push(
      {name:'general_source_freshness_mode',default:'auto',selector:{select:{options:['auto','custom']}}},
      {name:'general_source_stale_minutes',default:240,selector:{number:{min:10,max:1440,step:1}}},
      {name:'global_threshold_max_age_mode',default:'auto',selector:{select:{options:['auto','custom']}}},
      {name:'global_threshold_max_age_minutes',default:90,selector:{number:{min:1,max:100000,step:1}}});
  }''',lang)
  assert page.evaluate('card._openHomeSettings128()')
  page.wait_for_function('card._homeSettingsDialog128?.fields?.length===8')
  home=page.locator('dialog.hem-home-options128');page.evaluate('card._homeSettingsDialog128.node.querySelectorAll("details").forEach(d=>d.open=true)')
  # Default auto: only the policy select, no manual timer.
  for k in ('general_source_stale_minutes','global_threshold_max_age_minutes'):
    assert home.locator(f'[data-hem-home-field128="{k}"]').evaluate('n=>getComputedStyle(n).display')=='none',k
  # A native copy of the same setting must not be duplicated when Home Options is ready.
  for key in ('select.home_age_mode','select.env_mode','number.home_minutes','number.env_minutes'):
    assert home.locator(f'[data-hem-full-row127="{key}"]').count()==0,key
  source=home.locator('[data-hem-home-input128="general_source_freshness_mode"]')
  source.select_option('custom')
  page.wait_for_function("homeData.general_source_freshness_mode==='custom'")
  custom=home.locator('[data-hem-home-field128="general_source_stale_minutes"]')
  expect(custom).to_be_visible();custom.locator('input').fill('45');custom.locator('input').dispatch_event('change')
  page.wait_for_function('homeData.general_source_stale_minutes===45')
  home.locator('[data-hem-home-input128="global_threshold_max_age_mode"]').select_option('custom')
  page.wait_for_function("homeData.global_threshold_max_age_mode==='custom'")
  number=home.locator('[data-hem-home-field128="global_threshold_max_age_minutes"]')
  expect(number).to_be_visible();number.locator('input').fill('33');number.locator('input').dispatch_event('change')
  page.wait_for_function('homeData.global_threshold_max_age_minutes===33')
  home.locator('[data-hem-home-input128="general_source_freshness_mode"]').select_option('auto')
  page.wait_for_function("homeData.general_source_freshness_mode==='auto'")
  expect(custom).to_be_hidden()
  assert page.evaluate('homeData.general_source_stale_minutes')==45  # Stored custom input retained.
  page.evaluate('card._closeHomeSettings128(false)')
  assert page.evaluate("card._openRoomSettings114('room0')")
  page.wait_for_function('card._roomSettingsDialog114?.fullRegistry127?.length>=10')
  room=page.locator('dialog.hem-room-options114');page.evaluate('card._roomSettingsDialog114.node.querySelectorAll("details").forEach(d=>d.open=true)')
  mode=room.locator('[data-hem-full-value127="select.room_age_mode"]')
  age=room.locator('[data-hem-full-row127="number.room_minutes"]')
  expect(mode).to_be_visible();expect(age).to_be_hidden()
  mode.select_option('custom')
  page.wait_for_function('writes.some(w=>w.domain==="select"&&w.data.option==="custom")')
  expect(age).to_be_visible()
  age.locator('input').fill('18');age.locator('input').dispatch_event('change')
  page.wait_for_function('writes.some(w=>w.domain==="number"&&w.data.entity_id==="number.room_minutes")')
  assert page.evaluate('writes.at(-1).data.value')==18
  page.evaluate("ack('number.room_minutes',18)")
  page.evaluate("ack('select.room_age_mode','custom')")
  page.evaluate('card._renderContent(true)');expect(age).to_be_visible()
  mode.select_option('auto')
  page.wait_for_function('writes.filter(w=>w.domain==="select"&&w.data.entity_id==="select.room_age_mode").length===2')
  expect(age).to_be_hidden()
  assert not errors,errors
  page.close()
 browser.close()
print('PASS: automatic defaults, custom numeric reveal, safe autosave, no duplicates and exact native targets in EN/EL/DE')