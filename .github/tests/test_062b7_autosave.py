"""Production menu autosave with delayed/failed services and stale HA snapshots.

Only transport boundaries are mocked; no HA backend or appliances are contacted.
"""
from pathlib import Path
from copy import deepcopy
import os, runpy, shutil
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[2]
CARD=ROOT/'custom_components/environment_manager/frontend/air-quality-advisor-card.js'
room=runpy.run_path(str(ROOT/'.github/tests/test_beta114_room_settings.py'))
base=runpy.run_path(str(ROOT/'.github/tests/test_beta108_setpoint_feedback_browser.py'))
CHROME=os.getenv('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
assert CHROME
SETUP=r'''() => {
 card._hass.connection={};card._homeDeviceId='homehub';
 card._hass.entities['sensor.hem'].device_id='homehub';
 window.writes=[];window.defer=false;window.reject=false;window.finishWrite=null;
 window.optionWrites=[];window.optionMode={};window.optionFlows=new Map();
 window.homeData={general_away_cooldown_minutes:10,general_home_policy:'any_home',pollen_avoid_ventilation:false,weather_entities:['weather.home']};
 window.homeForm={type:'form',step_id:'setup_general',handler:'entry0',errors:{},data_schema:[
  {name:'general_away_cooldown_minutes',default:10,selector:{number:{min:0,max:60,step:1}}},
  {name:'general_home_policy',default:'any_home',selector:{select:{options:['any_home','all_home']}}},
  {name:'pollen_avoid_ventilation',default:false,selector:{boolean:{}}},
  {name:'weather_entities',default:['weather.home'],selector:{select:{multiple:true,options:['weather.home','weather.extra']}}}
 ]};
 const sources=structuredClone(window.roomSchema);
 card._hass.callApi=async(method,path,data)=>{
   calls.push({method,path,data});
   if(method==='DELETE'){optionFlows.delete(path.split('/').at(-1));return {};}
   if(path==='config/config_entries/options/flow'){
     const id='fresh'+(++seq);optionFlows.set(id,{});
     return {type:'menu',flow_id:id,handler:'entry0',menu_options:['edit_room_room0','edit_room_room1','general_settings']};
   }
   const id=path.split('/').at(-1),flow=optionFlows.get(id);
   if(!flow)throw Error('Unknown options flow');
   if(data.next_step_id){
     flow.home=data.next_step_id==='general_settings';
     const form=structuredClone(flow.home?homeForm:sources);
     for(const field of form.data_schema)field.default=structuredClone((flow.home?homeData:committed)[field.name]);
     flow.form={...form,flow_id:id};return flow.form;
   }
   optionWrites.push(structuredClone(data));
   if(optionMode.hold)await new Promise(resolve=>window.finishOptions=resolve);
   if(optionMode.fail)throw Error('Options rejected');
   if(optionMode.validation)return {...flow.form,errors:{temperature:'invalid_room_source'}};
   if(flow.home)homeData=structuredClone(data);else committed=structuredClone(data);
   optionFlows.delete(id);return {type:'create_entry',flow_id:id};
 };
 const fields=[
  ['number.maximum','10',{min:0,max:100,step:1,unit_of_measurement:'min',friendly_name:'Maximum ON time',configuration_help:'Maximum continuous operating time.'},'living-device','entry0_area_room0_max_on'],
  ['select.method','automatic',{options:['automatic','manual','pid'],friendly_name:'Controller'},'living-device','entry0_area_room0_pid_method'],
  ['switch.eco','off',{friendly_name:'Closed-door Eco'},'living-device','entry0_area_room0_closed_door_eco'],
  ['time.sleep','22:00:00',{friendly_name:'Sleep starts'},'living-device','entry0_area_room0_sleep_start'],
  ['button.reset','unknown',{friendly_name:'Reset calibration'},'living-device','entry0_area_room0_calibrate'],
  ['number.home_maximum','10',{min:0,max:100,step:1,friendly_name:'Preparation limit'},'homehub','entry0_home_preparation'],
 ];
 window.registry=fields.map(([id,state,attributes,device_id,unique_id])=>{
  card._hass.states[id]={state,attributes};return {entity_id:id,device_id,unique_id,platform:'environment_manager',config_entry_id:'entry0'};
 });
 card._hass.callWS=async request=>{
  if(request.type==='config/entity_registry/list')return registry;
  throw Error('Unexpected WS: '+request.type);
 };
 card._hass.callService=async(domain,action,data)=>{
   writes.push({domain,action,data:structuredClone(data)});
   if(defer)await new Promise((resolve,reject)=>window.finishWrite={resolve,reject});
   if(reject)throw Error('Rejected');
 };
 window.ack=(id,value)=>{
  card._hass={...card._hass,states:{...card._hass.states,[id]:{...card._hass.states[id],state:String(value)}}};
  card._renderContent(true);
 };
}'''
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=CHROME,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 for width,language in ((320,'el'),(390,'en'),(760,'de')):
  page=browser.new_page(viewport={'width':width,'height':950});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content('<style>body{margin:0;font:14px Arial;--card-background-color:#222;--primary-text-color:#eee;--secondary-text-color:#aaa}</style>')
  page.evaluate(base['icon_fixture']());page.add_script_tag(path=str(CARD))
  states=deepcopy(base['fixture_definitions']()['states'])
  states['sensor.hem']['attributes']['dashboard']['rooms']=states['sensor.hem']['attributes']['dashboard']['rooms'][:2]
  page.evaluate(room['SETUP'],{'states':states,'form':room['FORM'],'native':False})
  page.evaluate('(form)=>window.roomSchema=form',room['FORM']);page.evaluate(SETUP)
  page.evaluate('(language)=>card._hass.language=language',language)
  assert page.evaluate("card._openRoomSettings114('room0')")
  page.wait_for_function('card._roomSettingsDialog114?.fullRegistry127?.length===6')
  modal=page.locator('dialog.hem-room-options114')
  assert modal.locator('[data-hem-full-apply127="number.maximum"]').count()==0
  assert modal.locator('[data-hem-full-apply127="select.method"]').count()==0
  expect(modal.locator('[data-room-options-save114]')).to_be_hidden()
  page.evaluate("card._roomSettingsDialog114.node.querySelectorAll('details').forEach(e=>e.open=true)")
  # A request acknowledgment is not a state confirmation. Stale rerenders
  # must never put 10 back into the editor while the accepted value is 25.
  maximum=modal.locator('[data-hem-full-value127="number.maximum"]')
  page.evaluate('defer=true')
  maximum.fill('25');maximum.dispatch_event('change')
  page.wait_for_function('writes.length===1')
  maximum.blur();page.evaluate('card._renderContent(true)')
  expect(maximum).to_have_value('25')
  page.evaluate('finishWrite.resolve();defer=false')
  page.wait_for_function("card._roomSettingsDialog114.nativeEdits.get('number.maximum').phase==='confirming'")
  page.evaluate('card._renderContent(true)');expect(maximum).to_have_value('25')
  page.evaluate("ack('number.maximum',25)")
  expect(maximum).to_have_value('25')
  assert page.evaluate("card._roomSettingsDialog114.nativeEdits.get('number.maximum').phase")== 'saved'
  # Rapid same-field edits are serialized; the old response cannot replace 35.
  page.evaluate('defer=true')
  maximum.fill('30');maximum.dispatch_event('change');page.wait_for_function('writes.length===2')
  maximum.fill('35');maximum.dispatch_event('change')
  page.evaluate('card._renderContent(true)');expect(maximum).to_have_value('35')
  assert page.evaluate('writes.length')==2
  page.evaluate('finishWrite.resolve();defer=false')
  page.wait_for_function('writes.length===3')
  assert page.evaluate('writes.at(-1).data.value')==35
  page.evaluate("ack('number.maximum',30)");expect(maximum).to_have_value('35')
  page.evaluate("ack('number.maximum',35)")
  # Invalid partial text must not send any request, nor mutate HA state.
  maximum.fill('150');maximum.dispatch_event('change');page.wait_for_timeout(500)
  assert page.evaluate('writes.length')==3
  assert page.evaluate("card._hass.states['number.maximum'].state")=='35'
  maximum.fill('40');maximum.dispatch_event('change');page.wait_for_function('writes.length===4')
  page.evaluate("ack('number.maximum',40)")
  # Selects and time values commit without Apply. Action buttons stay deliberate.
  method=modal.locator('[data-hem-full-value127="select.method"]');method.select_option('pid')
  page.wait_for_function('writes.length===5');assert page.evaluate('writes.at(-1).data.option')=='pid'
  page.evaluate("ack('select.method','pid')")
  sleep=modal.locator('[data-hem-full-value127="time.sleep"]');sleep.fill('06:45');sleep.dispatch_event('change')
  page.wait_for_function('writes.length===6');assert page.evaluate('writes.at(-1).data.time')=='06:45:00'
  page.evaluate("ack('time.sleep','06:45:00')")
  assert page.evaluate("writes.filter(w=>w.domain==='button').length")==0
  modal.locator('[data-hem-full-apply127="button.reset"]').click()
  page.wait_for_function("writes.some(w=>w.domain==='button')")
  # Rejection keeps the edited value and exposes an explicit retry, never a
  # hidden infinite retry loop or a misleading Saved label.
  page.evaluate('reject=true');maximum.fill('45');maximum.dispatch_event('change')
  page.wait_for_function("card._roomSettingsDialog114.nativeEdits.get('number.maximum').phase==='failed'")
  row=modal.locator('[data-hem-full-row127="number.maximum"]')
  expect(row.locator('[role="alert"]')).to_be_visible();expect(maximum).to_have_value('45')
  count=page.evaluate('writes.length');page.wait_for_timeout(500);assert page.evaluate('writes.length')==count
  page.evaluate('reject=false');row.locator('[data-settings-retry]').click()
  page.wait_for_function('(n)=>writes.length>n',arg=count);page.evaluate("ack('number.maximum',45)")
  # Room selection writes preserve untouched sources and keep the same dialog.
  humidity=modal.locator('[data-room-options-group114="humidity"]')
  humidity.locator('[data-room-clear114]').click()
  page.wait_for_function('committed.humidity.length===0')
  assert page.evaluate('committed.temperature')==room['DEFAULTS']['temperature']
  assert page.evaluate('card._roomSettingsDialog114.finished') is False
  assert modal.locator('[data-room-options-group114]').count()==7
  # Failing source save does not erase edits or auto-retry.
  page.evaluate('optionMode.fail=true')
  modal.locator('[data-room-options-group114="temperature"] [data-room-clear114]').click()
  page.wait_for_function('card._roomSettingsDialog114.optionsAutosave.blocked===true')
  n=page.evaluate('optionWrites.length');page.wait_for_timeout(200);assert page.evaluate('optionWrites.length')==n
  page.evaluate('optionMode.fail=false')
  modal.locator('[data-room-options-status114] button').click()
  page.wait_for_function('committed.temperature.length===0')
  # Home applies checkboxes, numeric values and enum selectors without Save.
  page.evaluate('card._closeRoomSettings114(false)')
  assert page.evaluate('card._openHomeSettings128()')
  page.wait_for_function('card._homeSettingsDialog128?.fields?.length===4')
  home=page.locator('dialog.hem-home-options128')
  page.evaluate("card._homeSettingsDialog128.node.querySelectorAll('details').forEach(e=>e.open=true)")
  expect(home.locator('[data-hem-home-save128]')).to_be_hidden()
  home.locator('[data-hem-home-input128="general_home_policy"]').select_option('all_home')
  page.wait_for_function("homeData.general_home_policy==='all_home'")
  home.locator('[data-hem-home-input128="general_away_cooldown_minutes"]').fill('23')
  page.wait_for_function('homeData.general_away_cooldown_minutes===23')
  home.locator('[data-hem-home-input128="pollen_avoid_ventilation"]').check()
  page.wait_for_function('homeData.pollen_avoid_ventilation===true')
  assert page.evaluate('homeData.general_away_cooldown_minutes')==23
  assert page.evaluate('homeData.general_home_policy')=='all_home'
  assert page.evaluate('card._homeSettingsDialog128.finished') is False
  assert 'Applies immediately' not in home.inner_text()
  assert 'Saved with Save' not in home.inner_text()
  # No delayed native write after identity/connection replacement.
  before=page.evaluate('writes.length')
  home.locator('[data-hem-full-value127="number.home_maximum"]').fill('55')
  page.evaluate('card._hass.connection={};card._renderContent(true)')
  page.wait_for_timeout(550);assert page.evaluate('writes.length')==before
  assert not errors,errors
  page.close()
 # The actual Device dialog uses the same pending-value protection, including
 # settings that were not present in the abbreviated registry cache.
 device=runpy.run_path(str(ROOT/'.github/tests/test_beta122_card_details.py'))['fixture']()
 page=browser.new_page(viewport={'width':390,'height':950});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content('<style>body{font:14px Arial;--card-background-color:#222;--primary-text-color:#eee}</style>')
 page.evaluate(base['icon_fixture']());page.add_script_tag(path=str(CARD))
 page.evaluate(r"""data=>{
  window.card=document.createElement('home-environment-manager-card');document.body.append(card);
  card._config={entity:'sensor.hem'};window.writes=[];
  card._hass={language:'en',states:data.states,user:{is_admin:true},connection:{},localize:()=>undefined,
    entities:{'sensor.hem':{config_entry_id:'entry0'},[data.controller]:{device_id:'controlled',config_entry_id:'entry0'}},
    callService:async(...args)=>{writes.push(args);await new Promise(resolve=>window.complete=resolve)},
    callWS:async()=>[{entity_id:'number.device_maximum',device_id:'controlled',config_entry_id:'entry0',
      platform:'environment_manager',unique_id:'ctrl_a_max_on'}]};
  card._hass.states[data.controller].attributes.controller_id='ctrl_a';
  card._hass.states['number.device_maximum']={state:'10',attributes:{min:0,max:100,step:1,
    friendly_name:'Maximum ON time',controller_id:'ctrl_a'}};
  card._renderContent(true);card._configEntryId114='entry0';card._configEntryOwner114='sensor.hem';
  card._areaDeviceIds=new Map([['living','room-hub']]);
 }""",device)
 assert page.evaluate('(controller)=>card._openHemControllerSettings126("living",controller)',device['controller'])
 page.wait_for_function('card._hemControllerDialog126?.fullRegistry127?.length===1')
 page.evaluate('card._hemControllerDialog126.node.querySelectorAll("details").forEach(d=>d.open=true)')
 modal=page.locator('dialog.hem-controller-options126');control=modal.locator('[data-hem-full-value127="number.device_maximum"]')
 assert modal.locator('[data-hem-full-apply127="number.device_maximum"]').count()==0
 control.fill('28');control.dispatch_event('change');page.wait_for_function('writes.length===1')
 control.blur();page.evaluate('card._renderContent(true)');expect(control).to_have_value('28')
 page.evaluate('complete();card._renderContent(true)');expect(control).to_have_value('28')
 assert page.evaluate("card._hass.states['number.device_maximum'].state")=='10'
 page.evaluate("card._hass.states['number.device_maximum']={...card._hass.states['number.device_maximum'],state:'28'};card._renderContent(true)")
 page.wait_for_function("card._hemControllerDialog126.nativeEdits.get('number.device_maximum').phase==='saved'")
 assert 'Applies immediately' not in modal.inner_text()
 assert not errors,errors
 page.close()
 browser.close()
print('PASS: all Home/Room native editor types, fresh Options saves, delayed/out-of-order updates, validation, failures, ownership and EN/EL/DE responsive menus')
