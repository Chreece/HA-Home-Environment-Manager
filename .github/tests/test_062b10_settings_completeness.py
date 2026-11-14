"""Real HEM card: stable interactions, source refresh, room enrollment and paired autosave.

Uses production JS and browser pointer events; all HA calls are synthetic.
"""
from pathlib import Path
from copy import deepcopy
import runpy,os,shutil,json
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[2]
CARD=ROOT/'custom_components/environment_manager/frontend/air-quality-advisor-card.js'
base=runpy.run_path(str(ROOT/'.github/tests/test_beta108_setpoint_feedback_browser.py'))
room=runpy.run_path(str(ROOT/'.github/tests/test_beta114_room_settings.py'))
fixture=runpy.run_path(str(ROOT/'.github/tests/test_beta122_card_details.py'))['fixture']()
chrome=os.getenv('CHROME_BIN') or shutil.which('chromium')
assert chrome

def page_setup(browser,language='el',width=390):
 page=browser.new_page(viewport={'width':width,'height':900});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content('<style>body{font:14px Arial;background:#151515;color:#eee;--primary-text-color:#eee;--secondary-text-color:#aaa;--card-background-color:#202020;--secondary-background-color:#303030;--primary-color:#03a9f4}</style>')
 page.evaluate(base['icon_fixture']());page.add_script_tag(path=str(CARD))
 return page,errors

def check_device(browser):
 for language,width in [('el',320),('de',390),('en',900)]:
  page,errors=page_setup(browser,language,width)
  page.evaluate(r'''({data,language})=>{
    window.card=document.createElement('home-environment-manager-card');document.body.append(card);
    card._config={entity:'sensor.hem'};window.calls=[];
    const fields=[['number.native_maximum','equipment_max_on_seconds','10','Maximum ON time',{min:0,max:120,step:1}],
      ['switch.native_window','equipment_pause_on_window_open','off','Pause when window open',{}]];
    window.registry=fields.map(([id,key,state,label,attrs])=>{
      data.states[id]={state,attributes:{controller_id:'ctrl_a',setting_key:key,friendly_name:label,configuration_help:'Help for '+label,...attrs}};
      return {entity_id:id,device_id:'controlled',config_entry_id:'entry0',platform:'environment_manager',translation_key:key,unique_id:'ctrl_a_'+key};
    });
    data.states[data.controller].attributes.controller_id='ctrl_a';
    card._hass={language,states:data.states,user:{is_admin:true},connection:{},localize:()=>undefined,
      entities:{'sensor.hem':{config_entry_id:'entry0',device_id:'homehub'},[data.controller]:{device_id:'controlled',config_entry_id:'entry0'}},
      callService:async(...args)=>calls.push(args),callWS:async request=>{
        if(request.type==='config/entity_registry/list')return registry;
        if(request.type==='config/device_registry/list')return [
           {id:'homehub',identifiers:[['environment_manager','entry0']]},
           {id:'room-hub',identifiers:[['environment_manager','entry0_area_living']]}];
        if(request.type==='config/area_registry/list')return [{area_id:'living',name:'Living room',floor_id:null}];
        if(request.type==='config/floor_registry/list')return [];
        throw Error('Unexpected request '+request.type);
      }};
    card._renderContent(true);card._configEntryId114='entry0';card._configEntryOwner114='sensor.hem';
    card._areaDeviceIds=new Map([['living','room-hub']]);
  }''',{'data':deepcopy(fixture),'language':language})
  assert page.evaluate('(id)=>card._openHemControllerSettings126("living",id)',fixture['controller'])
  page.wait_for_function('card._hemControllerDialog126?.fullRegistry127?.length===2')
  dialog=page.locator('dialog.hem-controller-options126')
  sw=dialog.locator('[data-hem-full-row127="switch.native_window"] [data-hem-full-apply127]')
  dialog.locator('[data-hem-full-row127="switch.native_window"]').locator('xpath=ancestor::details[contains(@class,"hem-full-category127")]').evaluate('n=>n.open=true')
  sw.scroll_into_view_if_needed();rect=sw.bounding_box();page.mouse.move(rect['x']+10,rect['y']+10)
  handle=sw.element_handle();page.mouse.down();page.evaluate('card._renderContent(true)')
  assert handle.evaluate('e=>e.isConnected')
  page.mouse.up();page.wait_for_function('calls.length===1')
  assert page.evaluate('calls[0][0]')=='switch'
  # Event during a real press should never disconnect the pressed DOM node.
  group=dialog.locator('[data-hem-full-row127="number.native_maximum"]').locator('xpath=ancestor::details[contains(@class,"hem-full-category127")]')
  cat=group.locator(':scope > summary')
  cat.scroll_into_view_if_needed();rect=cat.bounding_box();page.mouse.move(rect['x']+20,rect['y']+20)
  handle=cat.element_handle();page.mouse.down()
  page.evaluate('card.hass={...card._hass,states:{...card._hass.states,"sensor.unrelated":{state:"123",attributes:{}}}}')
  assert handle.evaluate('e=>e.isConnected')
  page.mouse.up();expect(group).to_have_attribute('open','')
  native=dialog.locator('[data-hem-full-row127="number.native_maximum"] .hem-full-help127')
  native.locator('summary').click();expect(native).to_have_attribute('open','')
  page.evaluate('card._renderContent(true)');expect(native).to_have_attribute('open','')
  page.evaluate('card.hass={...card._hass,states:{...card._hass.states,"sensor.unrelated":{state:"124",attributes:{}}}}')
  expect(native).to_have_attribute('open','')

  assert not errors,errors
  page.close()

def check_options(browser):
 page,errors=page_setup(browser,'en',500)
 states=deepcopy(base['fixture_definitions']()['states'])
 states['sensor.hem']['attributes']['dashboard']['rooms']=states['sensor.hem']['attributes']['dashboard']['rooms'][:2]
 page.evaluate(room['SETUP'],{'states':states,'form':room['FORM'],'native':False})
 page.evaluate(r'''()=>{
   card._hass.connection={};card._homeDeviceId='homehub';card._hass.entities['sensor.hem'].device_id='homehub';
   window.flowWrites=[];window.flows=new Map();window.counter=0;window.liveHome={
      general_wake_alarm_entity:'none',general_wake_lead_minutes_entity:'none',pollen_high_from:3,pollen_max_scale:5,
      pollen_entities:[],general_home_policy:'any_home'};
   window.homeForm={type:'form',step_id:'setup_general',data_schema:[
      {name:'general_wake_alarm_entity',default:'none',selector:{select:{options:['none','sensor.alarm']}}},
      {name:'general_wake_lead_minutes_entity',default:'none',selector:{select:{options:['none','sensor.lead']}}},
      {name:'pollen_high_from',default:3,selector:{number:{min:0,max:100,step:0.1}}},
      {name:'pollen_max_scale',default:5,selector:{number:{min:1,max:100,step:0.1}}},
      {name:'pollen_entities',default:[],selector:{select:{multiple:true,options:[]}}},
      {name:'general_home_policy',default:'any_home',selector:{select:{options:['any_home','all_home']}}},
   ]};
   card._hass.callApi=async(method,path,data)=>{
     flowWrites.push({method,path,data:structuredClone(data)});
     if(method==='DELETE'){flows.delete(path.split('/').at(-1));return {};}
     if(path==='config/config_entries/options/flow'){
       const id='b10'+(++counter);flows.set(id,{});
       return {type:'menu',handler:'entry0',flow_id:id,menu_options:['choose_rooms','general_settings','edit_room_room0']};
     }
     const id=path.split('/').at(-1),flow=flows.get(id);if(!flow)throw Error('Missing flow');
     if(data?.next_step_id==='general_settings'){
       flow.kind='home';const form=structuredClone(homeForm);form.flow_id=id;form.handler='entry0';
       for(const field of form.data_schema)field.default=structuredClone(liveHome[field.name]);
       return form;
     }
     if(data?.next_step_id==='choose_rooms'){
       flow.kind='rooms';return {type:'form',step_id:'setup_rooms',flow_id:id,
         data_schema:[{name:'areas',default:window.chosenRooms||['room0'],selector:{select:{multiple:true,options:[
           {value:'room0',label:'Room 0'},{value:'room1',label:'Room 1'}]}}}]};
     }
     if(flow.kind==='home'){
       if((data.general_wake_alarm_entity!=='none') !== (data.general_wake_lead_minutes_entity!=='none'))throw Error('Invalid');
       liveHome=structuredClone(data);return {type:'create_entry',flow_id:id};
     }
     if(flow.kind==='rooms'){window.chosenRooms=data.areas;return {type:'create_entry'};}
     throw Error('Wrong flow');
   };
   card._hass.callWS=async req=>req.type==='config/entity_registry/list'?[]:[];
   card._renderContent(true);
 }''')
 assert page.evaluate('card._openHomeSettings128()')
 page.wait_for_function('card._homeSettingsDialog128?.fields?.length===6')
 modal=page.locator('dialog.hem-home-options128')
 expect(modal.locator('[data-settings-refresh-b10]')).to_be_visible()
 expect(modal.locator('[data-settings-manage-rooms-b10]')).to_be_visible()
 # Source actions belong BELOW the title header, never in its flex row.
 assert modal.locator('.hem-settings-source-actions-b15 > [data-settings-refresh-b10]').count()==1
 assert modal.locator('.hem-settings-source-actions-b15 > [data-settings-manage-rooms-b10]').count()==1
 assert modal.locator('.hem-room-options-head114 [data-settings-refresh-b10]').count()==0
 assert modal.locator('.hem-room-options-head114 [data-settings-manage-rooms-b10]').count()==0
 title=modal.locator('.hem-room-options-head114 h2')
 assert title.bounding_box()['width']>170,title.bounding_box()
 # Add a source while the menu is already open, then refresh without losing drafts.
 page.evaluate('homeForm.data_schema.find(f=>f.name==="pollen_entities").selector.select.options.push({value:"sensor.birch_index",label:"Birch index"})')
 old_count=page.evaluate('flowWrites.filter(x=>x.data?.next_step_id==="general_settings").length')
 modal.locator('[data-settings-refresh-b10]').click()
 page.wait_for_function('card._homeSettingsDialog128?.fields?.find(f=>f.name==="pollen_entities")?.schema.selector.select.options.length===1')
 page.wait_for_function('!card._homeSettingsDialog128?.sourcesRefreshingB10')
 assert page.evaluate('flowWrites.filter(x=>x.data?.next_step_id==="general_settings").length')==old_count+1
 assert modal.locator('[data-hem-home-input128="pollen_entities"][value="sensor.birch_index"]').count()==1
 assert modal.locator('[data-settings-refresh-b10]').is_enabled()
 # First half of the wake pair is held, not submitted.
 # Reopen all enclosing categories, including the b8 Advanced tier, before
 # triggering a genuine user edit; a hidden element cannot receive a click.
 modal.locator('[data-settings-advanced-b8]').check()
 page.evaluate("card._homeSettingsDialog128.node.querySelectorAll('details').forEach(n=>n.open=true)")
 modal.locator('[data-hem-home-input128="general_wake_alarm_entity"]').evaluate("n=>{for(let p=n;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true}")
 modal.locator('[data-hem-home-input128="general_wake_alarm_entity"]').select_option('sensor.alarm')
 page.wait_for_timeout(100)
 assert page.evaluate('flowWrites.filter(x=>x.data?.general_wake_alarm_entity=== "sensor.alarm").length')==0
 modal.locator('[data-hem-home-input128="general_wake_lead_minutes_entity"]').evaluate('n=>n.closest("details").open=true')
 modal.locator('[data-hem-home-input128="general_wake_lead_minutes_entity"]').select_option('sensor.lead')
 page.wait_for_function('liveHome.general_wake_alarm_entity==="sensor.alarm"')
 assert page.evaluate('liveHome.general_wake_lead_minutes_entity')=='sensor.lead'
 # Backend rejected field must appear at that field, not only generic status.
 page.evaluate("card._settingsHomeFieldErrorB10(card._homeSettingsDialog128,'pollen_entities','Invalid provider index')")
 expect(modal.locator('[data-hem-home-field128="pollen_entities"] [role="alert"]')).to_contain_text('Invalid provider')
 # A second click after autosave must still replace a previously cleaned-up
 # Options flow. The new form must own its cleanup and retain current choices.
 modal.locator('[data-settings-refresh-b10]').click()
 page.wait_for_function('!card._homeSettingsDialog128?.sourcesRefreshingB10')
 assert page.evaluate('card._homeSettingsDialog128.cleanupStarted') is False
 # Separate room-management flow, consent only for removals. Backend returns
 # setup_rooms, not choose_rooms, and create_entry may omit flow_id.
 before_rooms=page.evaluate('flowWrites.filter(x=>x.data?.next_step_id==="choose_rooms").length')
 modal.locator('[data-settings-manage-rooms-b10]').click()
 manage=page.locator('dialog.hem-settings-rooms-b10')
 expect(manage).to_be_visible()
 assert page.evaluate('flowWrites.filter(x=>x.data?.next_step_id==="choose_rooms").length')==before_rooms+1
 assert page.evaluate('card._homeSettingsDialog128.node.querySelector("[data-hem-home-status128]")?.getAttribute("role")')!='alert'
 manage.locator('[data-room-member-b10="room1"]').check()
 manage.locator('[data-settings-save-room-b10]').click()
 page.wait_for_function('Array.isArray(window.chosenRooms)')
 assert page.evaluate('chosenRooms.sort()')==['room0','room1']
 assert page.evaluate('flowWrites.some(x=>x.data?.areas?.length===2)')
 # Removal is never silently accepted: the user must acknowledge it.
 modal.locator('[data-settings-manage-rooms-b10]').click()
 manage=page.locator('dialog.hem-settings-rooms-b10')
 expect(manage).to_be_visible()
 manage.locator('[data-room-member-b10="room1"]').uncheck()
 assert manage.locator('[data-settings-save-room-b10]').is_disabled()
 manage.locator('[data-settings-removal-ack-b10]').check()
 assert manage.locator('[data-settings-save-room-b10]').is_enabled()
 manage.locator('[data-settings-save-room-b10]').click()
 page.wait_for_function('chosenRooms.length===1')
 assert page.evaluate('chosenRooms')==['room0']
 assert not errors,errors
 page.close()

with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=chrome,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 check_device(browser);check_options(browser)
 browser.close()
print('PASS b10: single-click stability, open help, source refresh, atomic wake inputs, explicit room enrollment and field errors')
