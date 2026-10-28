"""Real Chromium regression for rapid live refreshes and localised device UI."""
import json,os,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
COMMON={'area_id':'bedroom','source_entity_ids':['climate.comfee']}
def row(state,**attributes): return {'state':state,'attributes':{**COMMON,**attributes}}
states={
 'climate.managed':row('dry',friendly_name='Comfee-Schlafzimmer',control_mode='pid',physical_source_state='off',requested_hvac_mode='dry',measurements={'humidity':59.,'temperature':21.5},humidity=60,current_temperature=21.5,controller_status={'status':'within_target_band'}),
 'climate.comfee':{'state':'off','attributes':{'friendly_name':'Comfee Schlafzimmer'}},
 'select.method':row('pid',options=['existing','automatic','manual','off','pid']),
 'select.calibration':row('manual',pid_calibration_role='method',options=['manual','imc_lambda','cohen_coon']),
 'sensor.control_status':row('within_target_band',status_code='within_target_band',physical_entity_states={'climate.comfee':'off'},window_policy={'blocked':False,'status':'window_closed_ready'}),
 'switch.window_policy':row('on',window_pause_role='policy',window_resume_delay_seconds=60),
}
room={'area_id':'bedroom','name':'Schlafzimmer','status':'safe','windows':[],'readings':[], 'environment':{'climate_plan':{'status':'ready','controller':'environment','profile':'home','temperature_c':21.5,'equipment_plan':{'humidity':{'status':'advisory','action':'idle','measured_rh':59.},'humidity_evidence':'selected_mean'},'actuation':{'status':'advisory_only'}}}}
with sync_playwright() as p:
 executable=os.environ.get('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
 assert executable
 browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':590,'height':1100})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content('<html><head><style>body{background:#101010;color:white;margin:8px;font-family:Arial}*{box-sizing:border-box}:root{--primary-text-color:#eee;--secondary-text-color:#aaa;--card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#404040}</style></head><body></body></html>')
 page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
 page.evaluate('''({states,room})=>{
  window.calls=[];window.room=room;window.card=document.createElement('home-environment-manager-card');
  document.body.append(card);card._hass={language:'el',states,localize:()=>undefined,callService:(...args)=>{calls.push(args);return Promise.resolve();}};
  window.draw=()=>{card.shadowRoot.innerHTML=card._styles()+'<ha-card class="shell"><div class="content">'+card._climatePanel(room)+'</div></ha-card>';};draw();
 }''',{'states':states,'room':room})
 assert not errors,errors
 numbers=page.locator('.hem-room-readings66 b')
 assert numbers.count()==2
 assert '21,5' in numbers.nth(0).inner_text() and '59 %' in numbers.nth(1).inner_text()
 assert numbers.nth(0).evaluate('(e)=>getComputedStyle(e).fontSize')==numbers.nth(1).evaluate('(e)=>getComputedStyle(e).fontSize')
 assert page.locator('[data-window-policy-switch]').get_attribute('aria-checked')=='true'
 assert page.evaluate('calls.length')==0
 result=page.evaluate('''()=>{
  card.shadowRoot.querySelector('details.hem-diagnostics>summary').click();
  for(let i=0;i<20;i++)draw();
  return card.shadowRoot.querySelector('details.hem-diagnostics').open;
 }''')
 assert result,'Diagnostics must remain open after ONE click and immediate refresh'
 page.wait_for_timeout(100)
 assert page.locator('details.hem-diagnostics').evaluate('(e)=>e.open')
 text=page.locator('details.hem-diagnostics').inner_text()
 assert 'within_target_band' not in text and 'climate.managed' not in text,text
 assert 'Comfee Schlafzimmer' in text
 assert page.evaluate("()=>card._controllerStatusLabel('within_target_band')") in text
 assert page.locator('details.hem-calibration').evaluate('(e)=>e.open') is False
 page.locator('.hem-technical66>summary').click()
 page.evaluate('draw()');page.wait_for_timeout(30)
 assert page.locator('.hem-technical66').evaluate('(e)=>e.open')
 assert 'climate.managed' in page.locator('.hem-technical66').inner_text()
 page.locator('details.hem-diagnostics>summary').click()
 page.evaluate('draw()');page.wait_for_timeout(30)
 assert not page.locator('details.hem-diagnostics').evaluate('(e)=>e.open')
 page.locator('details.hem-diagnostics>summary').focus()
 page.keyboard.press('Enter');page.evaluate('draw()');page.wait_for_timeout(30)
 assert page.locator('details.hem-diagnostics').evaluate('(e)=>e.open')
 page.locator('details.hem-calibration>summary').click();page.evaluate('draw()')
 assert page.locator('[data-pid-calibration-method]').is_visible()
 assert page.evaluate('calls.length')==0,'Disclosure expansion is read-only'
 page.locator('[data-window-policy-switch]').click();page.wait_for_timeout(100)
 assert page.evaluate('calls')==[['switch','turn_off',{'entity_id':'switch.window_policy'}]]
 page.evaluate('draw()')
 page.evaluate("()=>{card.shadowRoot.querySelector('[data-window-policy-switch]').dataset.windowPolicySwitch='switch.unrelated';card.shadowRoot.querySelector('[data-window-policy-switch]').click();}")
 page.wait_for_timeout(20);assert page.evaluate('calls.length')==1
 outdoor={'status':'unknown','safe_to_ventilate':False,'data_complete':False,'weather':[{'condition':'partlycloudy','temperature_c':12,'wind_kmh':7}],'readings':[],'warnings':[], 'blockers':[{'code':'aqi_scale_unconfigured','label':'Outdoor AQI'}]}
 outside=page.evaluate('(o)=>card._outside(o)',outdoor)
 assert 'Δεν έχει οριστεί η κλίμακα AQI' in outside,outside
 assert 'Άγνωστες εξωτερικές συνθήκες' not in outside
 assert '12' in outside and 'Κράτησε' not in outside
 outdoor.update(status='unsafe',blockers=[{'code':'active_warning','label':'Storm'}])
 outside=page.evaluate('(o)=>card._outside(o)',outdoor)
 assert 'Κράτησε τα παράθυρα κλειστά' in outside
 assert 'Δεν έχει οριστεί η κλίμακα AQI' not in outside
 for path in (ROOT/'translations').glob('*.json'):
  lang=path.stem.lower()
  data=page.evaluate('''(lang)=>{card._hass={...card._hass,language:lang};draw();return {label:card._l66('windowSwitch'),open:card._controllerStatusLabel('window_open_pause'),wait:card._controllerStatusLabel('window_close_warmup'),unknown:card._controllerStatusLabel('window_state_unknown'),aqi:card._l66('aqiSetup')};}''',lang)
  assert all(data.values()),lang
  assert data['open']!='window_open_pause' and data['wait']!='window_close_warmup'
  if lang!='en':assert data['label']!='Stop when a window opens',lang
 page.evaluate("()=>{card._hass={...card._hass,language:'el',states:{...card._hass.states,'switch.duplicate':card._hass.states['switch.window_policy']}};draw();}")
 assert page.locator('[data-window-policy-switch]').count()==0
 page.evaluate("()=>{const states={...card._hass.states};delete states['switch.duplicate'];card._hass={...card._hass,states};draw();}")
 page.set_viewport_size({'width':375,'height':1100})
 assert page.evaluate('document.documentElement.scrollWidth')<=375
 assert not errors,errors
 page.set_viewport_size({'width':590,'height':1100})
 Path(ROOT/'dist').mkdir(exist_ok=True)
 page.screenshot(path=str(ROOT/'dist/beta66-device-card.png'),full_page=True)
 browser.close()
print('PASS Beta66 Chromium: one-click persistent nested diagnostics and calibration, keyboard/rapid refresh, translated status vs canonical IDs, prominent RH, exact outside AQI reason, retained active warning, scoped window switch, 38 locales, narrow screen')
