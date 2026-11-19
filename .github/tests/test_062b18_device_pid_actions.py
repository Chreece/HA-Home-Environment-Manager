"""B18: device PID settings show one per-mode editor and paired review actions.

Chromium exercises the production card with exact HA registry unique IDs. No
physical Home Assistant device or service is contacted.
"""
from __future__ import annotations
import os
from pathlib import Path
import runpy
import shutil
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[2]
CARD=ROOT/"custom_components/environment_manager/frontend/air-quality-advisor-card.js"
FIXTURE=runpy.run_path(str(ROOT/".github/tests/test_beta122_card_details.py"))["fixture"]
ICONS=runpy.run_path(str(ROOT/".github/tests/test_beta108_setpoint_feedback_browser.py"))["icon_fixture"]
CHROME=os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert CHROME

SETUP=r"""data=>{
  window.calls=[];window.routes=[];
  window.history.pushState=(_s,_t,path)=>routes.push(path);
  window.card=document.createElement('home-environment-manager-card');
  document.body.append(card);card._config={entity:'sensor.hem'};
  const states=data.states;
  states[data.controller].attributes.controller_id='ctrl_a';
  const registry=[];
  function add(id,key,state,mode,attributes={}){
    const scoped=Boolean(mode),uid='ctrl_a_'+(scoped?'mode_'+mode+'_':'')+key;
    const extra=scoped?{settings_scope:'operating_mode',operating_mode:mode,
       operating_mode_label:'Αφύγρανση',setting_key:key}:{};
    const common={area_id:'living',controller_id:'ctrl_a',
      source_device_id:'physical-heater-device',source_entity_ids:[data.physical],
      friendly_name:id,configuration_help:'Exact authorized controller setting'};
    states[id]={state,attributes:{...common,...extra,...attributes}};
    registry.push({entity_id:id,device_id:'hem-controller-device',
      config_entry_id:'entry0',platform:'environment_manager',
      unique_id:uid,translation_key:'equipment_'+key});
  }
  for(const role of ['approve','discard']){
    add('button.generic_'+role,'pid_review_'+role,'unknown',null,{pid_review_role:role});
    add('button.dry_'+role,'pid_review_'+role,'unknown','dry',{pid_review_role:role});
  }
  add('button.generic_apply','pid_apply_calibration','unavailable',null,
      {pid_calibration_role:'apply'});
  add('button.dry_apply','pid_apply_calibration','unavailable','dry',
      {pid_calibration_role:'apply'});
  add('button.fan_apply','pid_apply_fan_capacity','unknown',null,
      {pid_fan_capacity_role:'apply'});
  add('select.generic_method','pid_calibration_method','adaptive_suggest',null,
      {pid_calibration_role:'single_authoritative_method',options:['manual','adaptive_suggest']});
  add('select.dry_method','pid_calibration_method','adaptive_suggest','dry',
      {pid_calibration_role:'single_authoritative_method',options:['manual','adaptive_suggest']});
  add('number.generic_kp','kp','1.2',null,{min:0,max:100,step:.1});
  add('number.dry_kp','kp','1.2','dry',{min:0,max:100,step:.1});
  add('number.dry_ki','ki','0.03','dry',{min:0,max:100,step:.001});
  add('number.dry_kd','kd','0','dry',{min:0,max:100,step:.001});
  add('number.dry_target','target_manual_humidity','60','dry',{min:30,max:85,step:1});
  window.deviceRegistry=registry;
  card._hass={language:'el',states,user:{is_admin:true},entities:{
    'sensor.hem':{config_entry_id:'entry0'},
    [data.controller]:{device_id:'hem-controller-device',config_entry_id:'entry0'}
  },connection:{},localize:()=>undefined,
    callService:(...args)=>{calls.push(args);return Promise.resolve();},
    callWS:async request=>request.type==='config/entity_registry/list'?registry:
      Promise.reject(Error('Unexpected WebSocket request'))};
  card._renderContent(true);card._configEntryId114='entry0';
  card._configEntryOwner114='sensor.hem';
  card._areaDeviceIds=new Map([['living','room-hub']]);
}"""

LANG={
 "el":("Έγκριση πρότασης βαθμονόμησης","Απόρριψη πρότασης βαθμονόμησης",
       "Εφαρμογή βαθμονόμησης απόδοσης ανεμιστήρα","Έγκριση","Απόρριψη"),
 "en":("Approve calibration proposal","Reject calibration proposal",
       "Apply fan-capacity calibration","Approve","Reject"),
 "de":("Kalibrierungsvorschlag annehmen","Kalibrierungsvorschlag ablehnen",
       "Lüfterleistung kalibrieren","Annehmen","Ablehnen"),
}
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=CHROME,headless=True,
      args=["--no-sandbox","--disable-dev-shm-usage"])
 for lang,width in (("el",390),("en",760),("de",320)):
  page=browser.new_page(viewport={"width":width,"height":900});errors=[]
  page.on("pageerror",lambda error:errors.append(str(error)))
  page.set_content('<style>body{margin:0;background:#161616;color:#eee;--card-background-color:#222;--primary-text-color:#eee;--secondary-text-color:#aaa}</style>')
  page.evaluate(ICONS());page.add_script_tag(path=str(CARD))
  page.evaluate(SETUP,FIXTURE())
  room=page.locator('[data-room-fold87="living"]')
  room.locator(":scope > summary").evaluate("(node)=>node.click()")
  controller=room.locator('[data-device-fold87="climate.hem_heater"]')
  controller.locator('[data-open-controller-device122]').click()
  modal=page.locator(".hem-controller-options126")
  expect(modal).to_be_visible()
  page.wait_for_function("card._hemControllerDialog126?.fullRegistry127?.length===14")
  page.evaluate("(lang)=>card._hass.language=lang",lang)
  page.evaluate("card._hemFullRender127(card._hemControllerDialog126,'device')")
  for id in ("button.generic_approve","button.generic_discard",
             "button.generic_apply","select.generic_method","number.generic_kp"):
   assert modal.locator(f'[data-hem-full-row127="{id}"]').count()==0,id
  for id in ("button.dry_approve","button.dry_discard","button.dry_apply",
             "select.dry_method","number.dry_kp","number.dry_ki","number.dry_kd",
             "button.fan_apply","number.dry_target"):
   assert modal.locator(f'[data-hem-full-row127="{id}"]').count()==1,id
  # A humidity target is not a PID-calibration parameter.
  assert modal.locator('[data-hem-full-category127="mode"] [data-hem-full-row127="number.dry_target"]').count()==1
  assert modal.locator('[data-hem-full-category127="pid"] [data-hem-full-row127="number.dry_target"]').count()==0
  words=LANG[lang];pid=modal.locator('[data-hem-full-category127="pid"]')
  pid.locator(":scope > summary").click()
  # Presence in the DOM was insufficient: the old Advanced filter hid all
  # three gains even inside the opened PID section.
  expect(modal.locator('[data-settings-advanced-b8]')).not_to_be_checked()
  for key in ('kp','ki','kd'):
   expect(pid.locator(f'[data-hem-full-row127="number.dry_{key}"]')).to_be_visible()
  assert words[0] in pid.locator('[data-hem-full-row127="button.dry_approve"]').inner_text()
  assert words[1] in pid.locator('[data-hem-full-row127="button.dry_discard"]').inner_text()
  assert words[2] in pid.locator('[data-hem-full-row127="button.fan_apply"]').inner_text()
  approve=pid.locator('[data-hem-pid-review-b18="approve"]')
  discard=pid.locator('[data-hem-pid-review-b18="discard"]')
  assert approve.count()==discard.count()==1
  assert approve.locator("button[data-hem-full-apply127]").inner_text()==words[3]
  assert discard.locator("button[data-hem-full-apply127]").inner_text()==words[4]
  # The two decisions are adjacent native rows, never combined into one
  # unsafe service or detached from their distinct entity IDs.
  assert page.evaluate("""()=>{const a=card._hemControllerDialog126.node
    .querySelector('[data-hem-pid-review-b18="approve"]');
    const b=card._hemControllerDialog126.node
    .querySelector('[data-hem-pid-review-b18="discard"]');
    return a?.nextElementSibling===b;}""")
  x=approve.bounding_box();y=discard.bounding_box()
  assert x and y,(x,y)
  if width>340:
   assert abs(x["y"]-y["y"])<5,(x,y)
  else:
   assert y["y"]>=x["y"]+x["height"]-3,(x,y)
  assert modal.evaluate("e=>e.scrollWidth<=e.clientWidth+1")
  assert page.evaluate("calls.length")==0
  approve.locator("button[data-hem-full-apply127]").click()
  page.wait_for_function("calls.length===1")
  assert page.evaluate("calls[0]")==["button","press",{"entity_id":"button.dry_approve"}]
  discard.locator("button[data-hem-full-apply127]").click()
  page.wait_for_function("calls.length===2")
  assert page.evaluate("calls[1]")==["button","press",{"entity_id":"button.dry_discard"}]
  # If no mode-scoped action is usable, keep the live legacy fallback.
  test=page.evaluate("""()=>{const dialog=card._hemControllerDialog126;
    card._hass.states['button.dry_approve'].state='unavailable';
    return card._hemFullFields127(dialog,'device').map(f=>f.id);}""")
  assert "button.generic_approve" in test
  # A pending failed edit must remain discoverable, even when scoped wins.
  test=page.evaluate("""()=>{const dialog=card._hemControllerDialog126;
    card._hass.states['button.dry_approve'].state='unknown';
    dialog.nativeEdits||=new Map();
    dialog.nativeEdits.set('select.generic_method',{phase:'failed',valid:true});
    return card._hemFullFields127(dialog,'device').map(f=>f.id);}""")
  assert "select.generic_method" in test
  assert not errors,errors
  page.close()
 browser.close()
print("PASS: exact per-mode PID dedup, paired approve/reject, unique fan calibration, fallback, pending draft, EL/EN/DE and 320/390/760px")
