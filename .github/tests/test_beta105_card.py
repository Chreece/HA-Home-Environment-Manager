"""Beta105 source-native metric links, average charts, physics/covers folds.

Real headless Chromium uses the production card and deterministic HA state
fixtures. No physical device controls are contacted. Both source clicks and
cover switches are verified by exact entity IDs and the popup keeps history.
"""
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
import runpy,shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta87_compact_browser.py'))
states=deepcopy(base['states'])
data=deepcopy(base['data'])
room=data['rooms'][0]
area=room['area_id']
t0=1793760000.
def evidence(value,ids,trend=None):
    return {'value':value,'source_ids':ids,
            'source_count':len(ids),**({'trend':trend} if trend is not None else {})}
room['environment']['measurement_evidence']={
    'temperature':evidence(20.5,['sensor.temp_a','sensor.temp_b'],
        [{'t':t0,'v':19.8},{'t':t0+900,'v':20.1},{'t':t0+1800,'v':20.5}]),
    'humidity':evidence(54.4,['sensor.humidity_1']),
    'pm25':evidence(8.0,['sensor.pm_a','sensor.pm_b'],
        [{'t':t0,'v':6.0},{'t':t0+900,'v':8.0}]),
    'co2':evidence(700.,['sensor.co2_one']),
}
room['environment']['moisture']={
    'status':'drying','drying_potential_g_kg':2.4,
    'outside_air_rh_when_warmed_percent':48.}
room['environment']['condensation']={'status':'ready','condensation_margin_c':6.2}
room['environment']['shade_cooling']={
    'selected_covers':['cover.blind_a','cover.blind_b'],
    'status':'eligible','covers':{
        'cover.blind_a':'owned','cover.blind_b':'idle'},
    'sun_elevation':24.1,
}
# The baseline synthetic RH reading is displayed in the FIRST three tiles.
# Make that displayed reading a real native HA entity; otherwise the extra
# appended source is not the value the expanded tile actually displays.
room['readings'][1].update(entity_id='sensor.humidity_1',value=54.4)
room['readings'] += [
  {'entity_id':'sensor.co2_one','name':'CO₂ sensor','metric':'co2',
   'value':700,'available':True,'unit':'ppm'},
  {'entity_id':'sensor.pm_a','name':'PM A','metric':'pm25',
   'value':6.0,'available':True,'unit':'µg/m³'},
  {'entity_id':'sensor.pm_b','name':'PM B','metric':'pm25',
   'value':10.0,'available':True,'unit':'µg/m³'},
  {'entity_id':'sensor.humidity_1','name':'Native RH','metric':'humidity',
   'value':54.4,'available':True,'unit':'%'},
]
data['outdoor']['readings'][0]['entity_id']='sensor.outdoor_aqi'
for id in ('sensor.temp_a','sensor.temp_b','sensor.pm_a','sensor.pm_b',
           'sensor.co2_one','sensor.humidity_1','sensor.outdoor_aqi'):
    states[id]={'state':'20','attributes':{'friendly_name':id.replace('_',' ')}}
states['binary_sensor.room0_window']={'state':'off','attributes':{'device_class':'window'}}
states['cover.blind_a']={'state':'open','attributes':{'friendly_name':'Living room blind A'}}
states['cover.blind_b']={'state':'closed','attributes':{'friendly_name':'Living room blind B'}}
states['switch.shades_room0']={'state':'on','attributes':{
    'area_id':area,'close_only':True,
    'selected_shades':['cover.blind_a','cover.blind_b']}}
states['sensor.hem']['attributes']['dashboard']=data

chrome=shutil.which('chromium') or shutil.which('google-chrome')
assert chrome,'Chromium required'
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(executable_path=chrome,headless=True,
         args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':590,'height':990})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content('<html><body style="margin:0;background:#111;color:#eee"></body></html>')
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    page.evaluate("""({states})=>{
      window.info=[];window.calls=[];
      window.card=document.createElement('home-environment-manager-card');
      document.body.append(card);
      card.addEventListener('hass-more-info',ev=>info.push(ev.detail.entityId));
      card._hass={language:'el',states,localize:()=>undefined,
        callService:(...args)=>{calls.push(args);return Promise.resolve()}};
      card._config={entity:'sensor.hem'};
      card._renderContent(true);
    }""",{'states':states})
    row=page.locator('[data-room-fold87="room0"]')
    assert row.count()==1 and row.get_attribute('open') is None
    # Native multi-source temperature: average icon and chart, NOT an entity.
    temp=row.locator('[data-hem-average105="temperature"]')
    assert temp.count()==1
    assert temp.locator('ha-icon[icon="mdi:approximately-equal"]').count()==1
    temp.click()
    assert row.get_attribute('open') is None, 'metric click opened entire room'
    popup=page.locator('.hem-avg-dialog105')
    popup.wait_for(state='visible')
    assert popup.locator('.hem-avg-line105').count()==1
    assert 'αισθητήρες' in popup.inner_text()
    popup.locator('[data-hem-source105="sensor.temp_a"]').click()
    assert page.evaluate('info')[-1]=='sensor.temp_a'
    popup.locator('[data-close-avg105]').click()
    assert popup.count()==0
    # One real humidity sensor: direct HA dialog, no mean icon.
    humidity=row.locator('button[data-hem-source105="sensor.humidity_1"]')
    assert humidity.count()==1
    assert humidity.locator('.hem-avg-marker105').count()==0
    humidity.click()
    assert page.evaluate('info')[-1]=='sensor.humidity_1'
    assert row.get_attribute('open') is None
    # Distinct compact PM2.5 uses validated TWO-sensor mean; CO₂ remains
    # a single sensor and never receives an average badge.
    pm=row.locator('[data-hem-average105="pm25"]')
    assert pm.count()==1
    assert '8' in pm.inner_text()
    assert pm.locator('.hem-avg-marker105').count()==1
    co2=row.locator('[data-hem-source105="sensor.co2_one"]')
    assert co2.count()==1 and co2.locator('.hem-avg-marker105').count()==0
    # AQI chip and source click are separate from the whitespace spacing.
    outside=page.locator('.hem-outside-details87')
    aqi=outside.locator('[data-hem-source105="sensor.outdoor_aqi"]')
    assert aqi.count()==1
    gap=aqi.evaluate("el=>getComputedStyle(el).columnGap")
    assert float(gap.replace('px',''))>=4,gap
    aqi.click()
    assert page.evaluate('info')[-1]=='sensor.outdoor_aqi'
    # Source click in full metric card and window contact must use exactly
    # the native source and not interfere with built-in info/help buttons.
    # Click the room NAME, not the center of a summary containing
    # interactive sensor buttons (Playwright's center can hit those instead).
    row.locator('.hem-room-name87').click()
    assert row.get_attribute('open') is not None
    rhTile=row.locator('.metric-number[data-hem-source105="sensor.humidity_1"]')
    assert rhTile.count()==1
    rhTile.click()
    assert page.evaluate('info')[-1]=='sensor.humidity_1'
    contact=row.locator('[data-hem-source105="binary_sensor.room0_window"]')
    assert contact.count()==1
    contact.click()
    assert page.evaluate('info')[-1]=='binary_sensor.room0_window'
    # Physics section defaults folded, showing only two quick facts.
    physics=row.locator('details.hem-physics-fold105')
    assert physics.count()==1 and physics.get_attribute('open') is None
    assert 'g/kg' in physics.locator(':scope > summary').inner_text()
    assert physics.locator('.science-grid').is_hidden()
    physics.locator(':scope > summary').click()
    assert physics.get_attribute('open') is not None
    assert physics.locator('.science-grid').is_visible()
    # Covers: native open/closed icon state + toggle ONLY when folded.
    covers=row.locator('details.hem-covers-fold105')
    assert covers.count()==1 and covers.get_attribute('open') is None
    assert covers.locator('.hem-cover-state105').count()==2
    toggle=covers.locator('.hem-cover-toggle105')
    assert toggle.is_visible()
    toggle.click()
    page.wait_for_timeout(30)
    assert page.evaluate('calls')[-1]==[
      'switch','turn_off',{'entity_id':'switch.shades_room0'}]
    assert covers.get_attribute('open') is None
    covers.locator(':scope > summary').click()
    assert covers.get_attribute('open') is not None
    assert not toggle.is_visible()
    assert covers.locator('[data-open-shade="cover.blind_a"]').is_visible()
    covers.locator('[data-open-shade="cover.blind_a"]').click()
    assert page.evaluate('info')[-1]=='cover.blind_a'
    # Fold status survives a full HA card refresh and its DOM reconciler.
    page.evaluate('card._renderContent(true)')
    assert row.locator('details.hem-physics-fold105').get_attribute('open') is not None
    assert row.locator('details.hem-covers-fold105').get_attribute('open') is not None
    # Live chart refresh must not close the panel or discard its source IDs.
    page.locator('[data-hem-average105="temperature"]').click()
    popup=page.locator('.hem-avg-dialog105')
    assert popup.is_visible()
    page.evaluate("""()=>{
      const states={...card._hass.states};
      const hem=states['sensor.hem'];
      const rooms=structuredClone(hem.attributes.dashboard.rooms);
      rooms[0].environment.measurement_evidence.temperature.trend.push(
          {t:1793762700,v:20.7});
      states['sensor.hem']={...hem,attributes:{...hem.attributes,
        dashboard:{...hem.attributes.dashboard,rooms}}};
      card.hass={...card._hass,states};
    }""")
    assert popup.is_visible()
    assert popup.locator('.hem-avg-line105').count()==1
    popup.locator('[data-close-avg105]').click()
    # Real native contributors changing must reset chart identity, not mix sets.
    page.evaluate("""()=>{
      const states={...card._hass.states};
      const hem=states['sensor.hem'];
      const rooms=structuredClone(hem.attributes.dashboard.rooms);
      rooms[0].environment.measurement_evidence.temperature={
        value:20.5,source_ids:['sensor.temp_a'],source_count:1};
      states['sensor.hem']={...hem,attributes:{...hem.attributes,
        dashboard:{...hem.attributes.dashboard,rooms}}};
      card.hass={...card._hass,states};
    }""")
    page.wait_for_function(
        "()=>!card.shadowRoot.querySelector('[data-hem-average105=\"temperature\"]')")
    assert row.locator('[data-hem-average105="temperature"]').count()==0
    # Other room source spoofing must never open unrelated entities.
    test=row.locator('[data-hem-source105="sensor.temp_a"]')
    if test.count()!=1:
        debug=page.evaluate("""()=>{
          const data=card._dashboard105();
          const ev=data?.rooms?.find(r=>r.area_id==='room0')?.environment?.measurement_evidence?.temperature;
          const badges=[...card.shadowRoot.querySelectorAll('[data-room-fold87="room0"] .hem-room-reading87')]
            .map(el=>({tag:el.tagName,outer:el.outerHTML.slice(0,450)}));
          return {evidence:ev,sourceVisible:!!card._hass.states['sensor.temp_a'],
            allowed:card._nativeAllowed105('sensor.temp_a'),
            evidenceLookup:card._evidence105('room0','temperature'),
            badges,renderError:card._lastRenderError,
            dashboardVersion:data?.version};
        }""")
        raise AssertionError(("ONE_NATIVE_SOURCE_MUST_REMAIN_CLICKABLE",debug))
    test.evaluate("(el)=>el.setAttribute('data-hem-source105','sensor.unrelated')")
    original=page.evaluate('info.length')
    # This verifies rejection of a tampered entity ID, not viewport
    # actionability: a user may have folded the room during HA re-renders.
    # Dispatch the native button click even when its room body is hidden.
    test.evaluate('(el)=>el.click()')
    assert page.evaluate('info.length')==original
    for width in (320,360,430,590):
      page.set_viewport_size({'width':width,'height':990})
      assert row.locator('.hem-room-glance87').bounding_box()['height']<=55
    assert not errors,errors
    browser.close()
print('BETA105_AVERAGE_TRENDS_NATIVE_LINKS_PHYSICS_COVER_FOLDS_AQI=PASS')
