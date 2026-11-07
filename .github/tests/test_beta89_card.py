"""Beta89 real Chromium interactions: physical activity, air sensors, dual links.

Runs the existing Beta87 compact-card browser contract first; no HA devices
or external services are contacted.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import runpy
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta87_compact_browser.py'))
states=deepcopy(base['states'])
rooms=deepcopy(base['rooms'])
data=deepcopy(base['data'])
area='room0'
source_heat='climate.physical_0_0'
source_dry='climate.physical_0_1'
ctrl_heat='climate.managed_0_0'
ctrl_dry='climate.managed_0_1'

states[source_heat]['attributes']['hvac_action']='heating'
states[source_heat]['state']='heat'
states[ctrl_heat]['attributes']['requested_hvac_mode']='heat'
states[ctrl_heat]['attributes']['physical_primary_entity_id']=source_heat
states[source_dry]['attributes']['hvac_action']='drying'
states[source_dry]['state']='dry'
states[ctrl_dry]['attributes']['physical_primary_entity_id']=source_dry
rooms[0]['readings'] += [
    {'metric':'co2','value':718,'unit':'ppm','name':'Main CO2','available':True},
    {'metric':'pm25','value':7.2,'unit':'µg/m³','name':'Particle sensor','available':True},
    {'metric':'pm10','value':12.5,'unit':'µg/m³','name':'Fine particles','available':True},
    {'metric':'tvoc','value':163,'unit':'ppb','name':'VOC','available':True},
    {'metric':'aqi','value':43,'unit':'US AQI','name':'AQI','available':True},
    {'metric':'hcho','value':2.3,'unit':'µg/m³','name':'Formaldehyde','available':True},
    {'metric':'radon','value':39,'unit':'Bq/m³','name':'Radon','available':True},
    {'metric':'voc','value':900,'available':False}, # never show unavailable
]
data['rooms']=rooms
states['sensor.hem']['attributes']['dashboard']=data
for j in range(3):
    states[f'button.resume_0_{j}']['attributes']['controller_resume_role']='continue_automatic'
states['button.resume_0_0']['state']='unavailable' # HA-disables when healthy
states['button.resume_0_1']['state']='unknown' # physical manual override requires Continue
states['select.control_0_1']['state']='manual'
states[ctrl_dry]['attributes']['control_mode']='manual'
states['button.resume_0_2']['state']='unavailable'

chrome=shutil.which('chromium') or shutil.which('google-chrome')
assert chrome,'Chromium required'
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(executable_path=chrome,headless=True,
       args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':590,'height':1100})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.set_content('<html><body></body></html>')
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    page.evaluate("""({states,entities})=>{
        window.calls=[]; window.info=[];window.routes=[];
        window.history.pushState=(_state,_title,path)=>routes.push(path);
        window.card=document.createElement('home-environment-manager-card');
        document.body.append(card);
        card.addEventListener('hass-more-info',ev=>info.push(ev.detail.entityId));
        card._hass={language:'el',states,entities,user:{is_admin:true},connection:{},localize:()=>undefined,
          callService:(...args)=>{calls.push(args);return Promise.resolve();}};
        card._config={entity:'sensor.hem'};
        card._renderContent(true);
        card._configEntryId114='entry0';card._configEntryOwner114='sensor.hem';
        card._areaDeviceIds=new Map([['room0','room-hub']]);
    }""",{'states':states,'entities':{
        'sensor.hem':{'config_entry_id':'entry0'},
        ctrl_heat:{'device_id':'hem-heater-device','config_entry_id':'entry0'},
        source_heat:{'device_id':'physical-heater-device'},
    }})
    room=page.locator('[data-room-fold87="room0"]')
    glance=room.locator(':scope > summary')
    assert 'hem-activity-heat' in glance.locator('.hem-room-reading87').nth(0).get_attribute('class')
    assert 'hem-activity-dry' in glance.locator('.hem-room-reading87').nth(1).get_attribute('class')
    chips=glance.locator('.hem-room-air-chip89')
    assert chips.count()==2,chips.count() # Temperature + RH + at most two extras
    text=page.evaluate("""()=>[...card.shadowRoot.querySelectorAll(
      '[data-room-fold87="room0"] .hem-room-air-chip89')].map(e=>e.textContent).join(' ')""")
    for metric in ('CO₂','PM2.5'):
        assert metric in text,(metric,text)
    assert all(name not in text for name in ('Lux','PM10','TVOC','HCHO','Rn')), text
    assert '900' not in text
    assert glance.bounding_box()['height']<=52,glance.bounding_box()
    # Names open entities; the leading icon opens this HEM controller's own
    # device page. Neither action toggles its disclosure.
    glance.click()
    controller=room.locator('[data-device-fold87="climate.managed_0_0"]')
    assert controller.get_attribute('open') is None
    controller.locator('button[data-open-controller89]').click()
    assert page.evaluate('info')[-1]==ctrl_heat
    assert controller.get_attribute('open') is None
    controller.locator('button[data-open-controller-device122]').click()
    modal=page.locator('.hem-controller-options126')
    assert modal.is_visible()
    assert page.evaluate('routes.length')==0
    assert modal.locator('[data-managed-climate93="'+ctrl_heat+'"]').count()==1
    modal.locator('[data-close-hem-controller126]').click()
    assert not modal.is_visible()
    assert controller.get_attribute('open') is None
    controller.locator('button[data-open-controller-device122]').evaluate(
      "(el)=>el.setAttribute('data-open-controller-device122','climate.unrelated')")
    length=page.evaluate('routes.length')
    controller.locator('button[data-open-controller-device122]').click()
    assert page.evaluate('routes.length')==length
    assert page.locator('.hem-controller-options126').count()==0
    controller.locator(':scope > summary').evaluate('(el)=>el.click()')
    assert controller.get_attribute('open') is not None
    controller.locator('button[data-open-physical93]').click()
    assert page.evaluate('info')[-1]==source_heat
    controller.locator('button[data-open-physical-device122]').click()
    assert page.evaluate('routes')[-1]=='/config/devices/device/physical-heater-device'
    auto=controller.locator('.hem-continue-auto89')
    assert auto.count()==1
    assert auto.is_disabled()
    assert 'Συνέχιση αυτόματης λειτουργίας' in auto.inner_text()
    manual=room.locator('[data-device-fold87="climate.managed_0_1"]')
    manual.locator(':scope > summary').evaluate('(el)=>el.click()')
    resume=manual.locator('.hem-continue-auto89')
    assert resume.count()==1 and resume.is_enabled()
    resume.click()
    page.wait_for_timeout(40)
    assert page.evaluate('calls')==[
       ['button','press',{'entity_id':'button.resume_0_1'}]],page.evaluate('calls')
    # Requested HEAT without actual heating must never color temperature.
    page.evaluate("""()=> {
      const next=structuredClone(card._hass.states);
      next['climate.physical_0_0'].attributes.hvac_action='idle';
      next['climate.physical_0_1'].attributes.hvac_action='idle';
      card._hass={...card._hass,states:next};
      card._renderContent(true);
    }""")
    glance=page.locator('[data-room-fold87="room0"] > summary')
    assert 'hem-activity-neutral' in glance.locator('.hem-room-reading87').nth(0).get_attribute('class')
    assert 'hem-activity-neutral' in glance.locator('.hem-room-reading87').nth(1).get_attribute('class')
    # Mobile never introduces a horizontal sensor scroller.
    page.set_viewport_size({'width':360,'height':1000})
    for room_header in page.locator('.hem-room-glance87').all():
        assert room_header.locator('.hem-room-air-chip89').count()<=2
    assert page.locator('.hem-room-air89').first.evaluate(
        '(node)=>getComputedStyle(node).overflowX')!='auto'
    assert not errors,errors
    browser.close()
print('BETA89_CHROMIUM_ACTIVITY_SENSORS_DUAL_ENTITY_LINKS_AUTO_BUTTON=PASS')
