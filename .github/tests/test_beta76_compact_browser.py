"""Beta76: compact room & device UI under real Chromium interactions."""
import os, shutil, runpy, json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
# Preserve the full existing Beta66 single-click, translations, window-switch,
# keyboard and AQI tests before adding the new compact rendering assertions.
original=runpy.run_path(str(ROOT/'.github/tests/test_beta66_browser.py'))
states=original['states'].copy()
room=original['room'].copy()
room['windows']=[{'entity_id':'binary_sensor.bedroom_window','name':'Bedroom window'}]
room['environment']=dict(original['room']['environment'])
room['environment']['climate_plan']=dict(original['room']['environment']['climate_plan'])
room['environment']['climate_plan'].update(
    occupancy='occupied',sleeping=True,profile='sleep',
    low_target_c=19.,high_target_c=22.,
    reason='environment_only_no_hvac',
)
states['binary_sensor.bedroom_window']={
    'state':'on','attributes':{'friendly_name':'Bedroom window'}
}
states['sensor.control_status']={
    **states['sensor.control_status'],
    'attributes':{
        **states['sensor.control_status']['attributes'],
        'room_occupancy':'occupied',
        'sleeping':True,
        'home_presence_status':'home',
        'status_code':'sleep_room_control_paused',
        'status_reason_code':'sleep_room_control_paused',
        'sleep_pause_requested':True,
        'upstream_power_switch':'switch.supply',
        'upstream_power_state':'off',
    },
}
states['switch.supply']={
    'state':'off','attributes':{'friendly_name':'Bedroom power supply'}
}
executable=os.environ.get('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
assert executable, 'Chromium is required for a real layout test'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=executable,headless=True,
                              args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':590,'height':1000})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content('''<!doctype html><html><head><style>
       *{box-sizing:border-box}body{margin:8px;background:#111;color:#eee;font-family:Arial}
       :root{--primary-text-color:#eee;--secondary-text-color:#aaa;
       --card-background-color:#202020;--secondary-background-color:#292929;
       --divider-color:#444}</style></head><body></body></html>''')
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    page.evaluate('''({states,room})=>{
      window.calls=[];window.card=document.createElement('home-environment-manager-card');
      document.body.append(card);
      card._hass={language:'el',states,localize:()=>undefined,
        callService:(...args)=>{calls.push(args);return Promise.resolve();}};
      window.draw=()=>{card.shadowRoot.innerHTML=card._styles()+
       '<ha-card class="shell"><div class="content">'+card._room(room)+'</div></ha-card>';};
      draw();
    }''',{'states':states,'room':room})
    assert not errors,errors
    assert page.locator('.hem-compact-climate76').count()==1
    assert page.locator('.hem-compact-device76').count()==1
    assert page.locator('.hem-room-readings66 b').count()==2
    assert page.locator('.hem-room-readings66').is_visible()
    assert page.locator('.hem-device-data>div').count()>=5
    assert page.locator('.hem-device-state76 .hem-status-pill76').count()>=3
    assert page.locator('.hem-context-row76 .hem-status-pill76').count()>=3
    assert page.locator('.hem-room-readings66').evaluate(
        '(e)=>getComputedStyle(e).gridTemplateColumns.split(" ").length')==2
    # Tiles: fixed compact density with no hidden data or blank spacer rows.
    metrics=page.locator('.hem-compact-device76 .hem-device-data>div')
    sizes=[metrics.nth(i).bounding_box() for i in range(metrics.count())]
    assert max(item['height'] for item in sizes) < 66,sizes
    columns=page.locator('.hem-compact-device76 .hem-device-data').evaluate(
        '(e)=>getComputedStyle(e).gridTemplateColumns.split(" ").length')
    assert columns>=3,columns
    assert page.locator('.hem-compact-climate76>small').count()==0

    # Context lives behind a touch-friendly 27px information control.
    roomInfo=page.locator('[data-detail-id="room-info:bedroom"]')
    deviceInfo=page.locator('[data-detail-id="device-info:climate.managed"]')
    assert not roomInfo.evaluate('(e)=>e.open')
    assert not deviceInfo.evaluate('(e)=>e.open')
    roomInfo.locator('summary').click()
    deviceInfo.locator('summary').click()
    page.evaluate('''()=>{for(let i=0;i<12;i++)draw();}''')
    page.wait_for_timeout(80)
    assert page.locator('[data-detail-id="room-info:bedroom"]').evaluate('(e)=>e.open')
    assert page.locator('[data-detail-id="device-info:climate.managed"]').evaluate('(e)=>e.open')
    assert 'Bedroom power supply' in deviceInfo.inner_text()
    assert page.evaluate('calls.length')==0
    assert page.locator('details.hem-diagnostics').count()==1
    assert page.locator('details.hem-calibration').count()==1
    assert page.locator('[data-window-policy-switch]').count()==1

    # Info icon remains keyboard accessible and survives a status refresh.
    roomInfo.locator('summary').focus()
    page.keyboard.press('Enter')
    page.evaluate('draw()');page.wait_for_timeout(30)
    assert not page.locator('[data-detail-id="room-info:bedroom"]').evaluate('(e)=>e.open')

    # The existing ON/OFF switch retains its original action contract.
    page.locator('[data-window-policy-switch]').click()
    page.wait_for_timeout(100)
    assert page.evaluate('calls')==[
        ['switch','turn_off',{'entity_id':'switch.window_policy'}]]
    # Full-size device and room data remain accessible under every locale.
    languages=[x.stem.lower() for x in (ROOT/'translations').glob('*.json')]
    assert len(languages)==38
    for lang in languages:
        result=page.evaluate('''lang=>{
          card._hass={...card._hass,language:lang};
          draw();
          return {room:card.shadowRoot.querySelectorAll('.hem-room-readings66 b').length,
                  device:card.shadowRoot.querySelectorAll('.hem-device-data>div').length,
                  info:card.shadowRoot.querySelector('[data-detail-id="room-info:bedroom"] summary').getAttribute('aria-label')};
        }''',lang)
        assert result['room']==2 and result['device']>=5 and result['info'],(lang,result)

    for width in (320,375,430,590):
        page.set_viewport_size({'width':width,'height':1000})
        page.evaluate('draw()')
        assert page.evaluate('document.documentElement.scrollWidth')<=width,width
        assert page.locator('.hem-room-readings66 b').count()==2
        assert page.locator('[data-window-policy-switch]').count()==1
        if width==320:
            assert page.locator('.hem-compact-device76 .hem-device-data').evaluate(
              '(e)=>getComputedStyle(e).gridTemplateColumns.split(" ").length')<=2

    page.set_viewport_size({'width':590,'height':1000})
    page.evaluate('''()=>{card._hass={...card._hass,language:'el'};draw();}''')
    (ROOT/'dist').mkdir(exist_ok=True)
    page.screenshot(path=str(ROOT/'dist/beta76-compact-device-card.png'),full_page=True)
    assert not errors,errors
    browser.close()
print(json.dumps({'status':'PASS','ui':'compact room and device',
                  'languages':38,'viewport_widths':[320,375,430,590],
                  'diagnostics_and_window_policy':'preserved',
                  'room_and_device_info':'persistent on one click',
                  'control_service_calls_only_from_switch':1,
                  'console_errors':errors}))
