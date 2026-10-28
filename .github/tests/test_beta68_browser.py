"""Exercise full card.hass/render path under a large state stream in Chromium."""
import os,shutil,json,runpy
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
# Retain all 38 locales, exact switches, diagnostics keyboard and focus tests.
base=runpy.run_path(str(ROOT/'.github/tests/test_beta66_browser.py'))
states=base['states'];room=base['room']
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':590,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content('<html><head><style>body{margin:8px;background:#111;color:#eee;font-family:Arial}:root{--primary-text-color:#eee;--secondary-text-color:#aaa;--card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}</style></head><body></body></html>')
 page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
 page.evaluate('''({states,room})=>{
  for(let i=0;i<5000;i++)states['sensor.unrelated_'+i]={state:String(i),attributes:{}};
  states['sensor.hem']={state:'safe',attributes:{dashboard:{version:1,rooms:[room],summary:{total:1,safe:1,attention:0,unknown:0},outdoor:{status:'safe',weather:[{condition:'partlycloudy',temperature_c:10,wind_kmh:6}],readings:[{metric:'aqi',value:27,unit:'US AQI',available:true}],warnings:[],blockers:[]}}}};
  window.card=document.createElement('home-environment-manager-card');window.calls=[];document.body.append(card);
  window.renders=0;const original=card._renderContent;card._renderContent=function(...args){renders++;return original.apply(this,args);};
  card.setConfig({entity:'sensor.hem'});card.hass={language:'el',states,localize:()=>undefined,callService:(...args)=>{calls.push(args);return Promise.resolve();}};
 }''',{'states':states,'room':room})
 page.wait_for_function('card._hasValidRender===true')
 assert page.locator('.hem-room-readings66 b').count()==2
 result=page.evaluate('''async()=>{
  const start=renders;const states=card._hass.states;
  for(let i=0;i<1000;i++) card.hass={...card._hass,states:{...states,'sensor.unrelated_0':{state:String(i),attributes:{}}}};
  const synchronously=renders-start;
  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
  return {synchronously,frames:renders-start,states:Object.keys(states).length};
 }''')
 assert result['synchronously']==0 and result['frames']==1,result
 # Real state change forces a DOM rebuild after the disclosure click.
 page.evaluate('''()=>{
  card.shadowRoot.querySelector('.hem-diagnostics>summary').click();
  const s=card._hass.states;const c=s['sensor.control_status'];
  card.hass={...card._hass,states:{...s,'sensor.control_status':{...c,state:'window_open_pause',attributes:{...c.attributes,status_code:'window_open_pause'}}}};
 }''')
 page.wait_for_timeout(80)
 assert page.locator('.hem-diagnostics').evaluate('(e)=>e.open')
 assert page.evaluate('calls.length')==0
 # Burst did not create an ongoing refresh timer, nor pending detached writes.
 rendered=page.evaluate('renders');page.wait_for_timeout(150)
 assert page.evaluate('renders')==rendered
 page.evaluate('()=>{card._render(true);card.remove();}')
 page.wait_for_timeout(80);assert page.evaluate('renders')==rendered
 page.evaluate('()=>document.body.append(card)');page.wait_for_timeout(80)
 assert page.evaluate('renders')==rendered+1
 assert not errors,errors
 page.locator('.hem-diagnostics>summary').click();page.wait_for_timeout(30)
 page.screenshot(path=str(ROOT/'dist/beta68-device-card.png'),full_page=True)
 browser.close()
 print(json.dumps({'test':'full-browser-stream','state_inventory':result['states'],'updates_per_burst':1000,'render_frames':result['frames'],'idle_redraws':0,'detached_redraws':0,'side_effect_service_calls':0,'single_click_diagnostics':'retained','page_errors':errors}))
