"""Render and exercise the real custom card in Chromium; no HA device writes."""
import json,os,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
langs=[p.stem.lower() for p in (ROOT/'translations').glob('*.json')]
COMMON={'area_id':'bedroom','source_entity_ids':['climate.comfee']}
def row(state,**attrs):return {'state':state,'attributes':{**COMMON,**attrs}}
states={
 'climate.managed':row('dry',friendly_name='Comfee-Schlafzimmer',control_mode='pid',physical_source_state='off',requested_hvac_mode='dry',measurements={'humidity':58.8,'temperature':21.6},humidity=60,current_temperature=21.6,upstream_power_switch='switch.strip',upstream_power_state='on',controller_status={'status':'sleep_room_control_paused'}),
 'climate.comfee':{'state':'off','attributes':{'friendly_name':'Comfee'}},
 'select.method':row('pid',options=['existing','automatic','manual','off','pid']),
 'select.calibration':row('manual',pid_calibration_role='method',options=['manual','imc_lambda','cohen_coon']),
 'select.capacity':row('legacy',pid_fan_capacity_role='strategy',options=['legacy','measured']),
 'select.direction':row('dry',pid_fan_capacity_role='direction',options=['choose','dry']),
 'number.stage1':row('0',pid_fan_capacity_field='pid_capacity_stage_1',min=0,max=100,step=1),
 'number.stage2':row('0',pid_fan_capacity_field='pid_capacity_stage_2',min=0,max=100,step=1),
 'button.capacity':row('2026-10-28',pid_fan_capacity_role='apply',calibration_status='complete_measured_stage_capacities_required'),
 'sensor.control_status':row('sleep_room_control_paused',status_code='sleep_room_control_paused',status_reason_code='sleep_room_control_paused',physical_entity_states={'climate.comfee':'off'},demand_percent=0,upstream_power_switch='switch.strip',upstream_power_state='on',upstream_idle_since=1793180000,upstream_idle_cooldown_seconds=600,sleep_pause_requested=True),
 'switch.strip':{'state':'on','attributes':{'friendly_name':'Schlafzimmer Steckdose'}},
 'sensor.light1':{'state':'0','attributes':{'friendly_name':'Lux Bett','device_class':'illuminance','unit_of_measurement':'lx'}},
 'sensor.light2':{'state':'160','attributes':{'friendly_name':'Lux Fenster','device_class':'illuminance','unit_of_measurement':'lx'}},
}
room={'area_id':'bedroom','name':'Schlafzimmer','status':'safe','windows':[],'readings':[], 'environment':{'climate_plan':{'status':'ready','controller':'environment','profile':'home','temperature_c':21.6,'equipment_plan':{'humidity':{'status':'advisory','action':'idle','measured_rh':58.8},'humidity_evidence':'selected_mean'},'actuation':{'status':'advisory_only'}}}}
with sync_playwright() as p:
 executable=os.environ.get('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
 assert executable,'Chromium required for frontend behavior checks'
 browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':590,'height':1050})
 errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
 page.set_content('''<html><head><style>body{background:#101010;color:white;margin:8px;font-family:Arial}*{box-sizing:border-box}:root{--primary-text-color:#eee;--secondary-text-color:#aaa;--card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#404040}</style></head><body></body></html>''')
 page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
 page.evaluate('''({states,room})=>{
 window.calls=[];window.room=room;
 window.card=document.createElement('home-environment-manager-card');
 document.body.append(card);card._hass={language:'el',states,localize:()=>undefined,callService:(...args)=>{calls.push(args);return Promise.resolve();}};
 window.draw=()=>{card.shadowRoot.innerHTML=card._styles()+'<ha-card class="shell"><div class="content">'+card._climatePanel(room)+'</div></ha-card>';};draw();
 }''',{'states':states,'room':room})
 assert not errors,errors
 text=page.locator('home-environment-manager-card .content').inner_text()
 assert 'Επισκόπηση δωματίου' in text,text
 assert 'Μόνο σχεδιασμός' not in text and 'Selected mean' not in text and 'Idle' not in text
 assert '58,8' in text and '60%' in text and '21,6' in text
 assert page.locator('[data-calibration-id]').count()==1
 assert page.locator('[data-pid-calibration-method]').is_hidden()
 assert page.locator('[data-pid-capacity-input]').count()==0,'Legacy strategy must not show unused measured stages'
 assert page.evaluate('calls.length')==0,'Read-only render sent a device command'
 for lang in langs:
  page.evaluate('(lang)=>{card._hass={...card._hass,language:lang};draw();}',lang)
  got=page.evaluate('''()=>({label:card._controllerStatusLabel('idle'),mean:card._controllerStatusLabel('selected_mean'),cal:card._controllerStatusLabel('complete_measured_stage_capacities_required'),lux:card._metricName('illuminance'),home:card._controllerStatusLabel('home'),html:card._controllerPanel(room)})''')
  assert got['label'] not in ('idle','') and got['mean'] not in ('selected_mean','') and 'complete_measured_stage_capacities_required' not in got['cal'],(lang,got)
  assert got['lux']!='metric_illuminance' and got['home'] not in ('','unknown'),lang
  assert 'data-calibration-id' in got['html'] and '<select data-climate-method' in got['html'],lang
 # Expand, then rerender preserving just this device's section.
 page.evaluate("()=>{card._hass={...card._hass,language:'el'};draw();}")
 page.locator('details.hem-calibration>summary').click()
 page.wait_for_timeout(100)
 assert page.locator('[data-pid-calibration-method]').is_visible()
 page.evaluate('draw()');page.wait_for_timeout(100)
 assert page.locator('[data-pid-calibration-method]').is_visible()
 # Current service handlers remain connected and scoped to verified device.
 page.locator('[data-climate-method]').select_option('automatic')
 page.wait_for_timeout(50)
 assert page.evaluate('calls.length')==1
 assert page.evaluate('calls[0]')[:2]==['select','select_option']
 page.evaluate("()=>{card._hass={...card._hass,states:{...card._hass.states,'select.capacity':{...card._hass.states['select.capacity'],state:'measured'}}};draw();}")
 assert page.locator('[data-pid-capacity-input]').count()==2
 assert 'complete_measured_stage_capacities_required' not in page.locator('home-environment-manager-card .content').inner_text()
 # Status matching is exact, not a substring of device/entity names.
 index=page.evaluate("()=>card._managedControllers('bedroom')[0].statusInfo.id")
 assert index=='sensor.control_status'
 # Entity ID matching fallback supports existing status sensors before restart.
 page.evaluate("()=>{const s={...card._hass.states['sensor.control_status']};s.attributes={...s.attributes};delete s.attributes.source_entity_ids;card._hass={...card._hass,states:{...card._hass.states,'sensor.control_status':s}};}")
 assert page.evaluate("()=>card._managedControllers('bedroom')[0].statusInfo.id")=='sensor.control_status'
 # An unsafe friendly name cannot become markup.
 page.evaluate("()=>{card._hass={...card._hass,states:{...card._hass.states,'switch.strip':{state:'on',attributes:{friendly_name:'<img src=x onerror=alert(1)>'}}}};draw();}")
 assert page.locator('home-environment-manager-card img').count()==0
 # Optional lux labels and zero are real values, not blank/unavailable.
 lx=page.evaluate("()=>card._metric({metric:'illuminance',entity_id:'sensor.light1',name:'Lux Bett',value:0,available:true,unit:'lx',threshold:null})")
 assert 'Lux Bett' in lx and 'lx' in lx and '0 <small>' in lx,lx
 # Responsive bounds for expanded advanced controls.
 page.set_viewport_size({'width':375,'height':1100})
 assert page.evaluate('document.documentElement.scrollWidth')<=375
 page.evaluate("()=>{card._calibrationExpanded65.clear();card._hass={...card._hass,states:{...card._hass.states,'select.capacity':{...card._hass.states['select.capacity'],state:'legacy'},'switch.strip':{state:'on',attributes:{friendly_name:'Schlafzimmer Steckdose'}}}};draw();}")
 page.set_viewport_size({'width':590,'height':1050})
 Path(ROOT/'dist').mkdir(exist_ok=True)
 page.screenshot(path=str(ROOT/'dist/beta65-device-card.png'),full_page=True)
 assert not errors,errors
 browser.close()
print('PASS Beta65 browser: 38 locales, translated statuses, room summary, live RH/target/demand/supply, scoped diagnostics, collapsed calibration, expansion persistence, legacy hides unused inputs, valid service routing, XSS escaping, zero lux, mobile width')
