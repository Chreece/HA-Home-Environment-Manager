"""Beta90: preserve Lovelace's real scroll offset through frequent card redraws.

Real headless Chromium with synthetic HEM dashboard; no hardware, external
services or network calls. Includes scroller nested outside the card host.
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
data=deepcopy(base['data'])
rooms=deepcopy(base['rooms'])
# Ensure the open room is substantially taller than its scrolling viewport.
for index in range(5):
    rooms[index]['readings'] += [
        {'metric':'co2','available':True,'value':650+index,'unit':'ppm'},
        {'metric':'pm25','available':True,'value':5+index,'unit':'µg/m³'},
        {'metric':'illuminance','available':True,'value':0,'unit':'lx'},
    ]
data['rooms']=rooms
states['sensor.hem']['attributes']['dashboard']=data
chrome=shutil.which('chromium') or shutil.which('google-chrome')
assert chrome,'Chromium required'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=chrome,headless=True,
        args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':590,'height':780})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.set_content("""<!doctype html><html><head><style>
      *{box-sizing:border-box}body{margin:0;background:#111;color:#ddd}
      :root{--primary-text-color:#eee;--secondary-text-color:#aaa;
      --card-background-color:#202020;--secondary-background-color:#292929;
      --divider-color:#444}
      #lovelace-scroll{height:280px;overflow-y:auto;width:570px;
       border:1px solid #555;scrollbar-width:thin}
    </style></head><body>
      <main id="lovelace-scroll"></main>
      <div style="height:800px">Other dashboard content</div>
    </body></html>""")
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    page.evaluate("""({states})=>{
      window.card=document.createElement('home-environment-manager-card');
      document.getElementById('lovelace-scroll').append(card);
      card._hass={language:'en',states,localize:()=>undefined,
        callService:()=>Promise.resolve()};
      card._config={entity:'sensor.hem'};
      card._roomsExpanded87=new Set(['room0']);
      card._devicesExpanded87=new Set(['climate.managed_0_0']);
      card._renderContent(true);
      const scroller=document.getElementById('lovelace-scroll');
      scroller.scrollTop=260;
      window.savedTop=scroller.scrollTop;
    }""",{'states':states})
    orig=page.evaluate('savedTop')
    assert orig>=130,orig
    for i in range(20):
        page.evaluate("""(i)=>{
          const current=card._hass.states;
          const next={...current};
          // Native feedback-only updates should not drag Lovelace to top.
          const physical={...current['climate.physical_0_0']};
          physical.attributes={...physical.attributes,
              hvac_action:i%2?'heating':'idle'};
          next['climate.physical_0_0']=physical;
          card._hass={...card._hass,states:next};
          card._renderContent(true);
        }""",i)
        top=page.evaluate("document.getElementById('lovelace-scroll').scrollTop")
        assert abs(top-orig)<=3,(i,top,orig)
    page.wait_for_timeout(80)
    final=page.evaluate("document.getElementById('lovelace-scroll').scrollTop")
    assert abs(final-orig)<=3,(final,orig)
    assert page.locator('.hem-room-fold87[data-room-fold87="room0"]').get_attribute('open') is not None
    assert page.locator('.hem-device-fold87[data-device-fold87="climate.managed_0_0"]').get_attribute('open') is not None
    assert page.evaluate('document.getElementById("lovelace-scroll").scrollWidth')<=570
    for width in (320,360,430):
        page.set_viewport_size({'width':width,'height':780})
        page.evaluate("(w)=>document.getElementById('lovelace-scroll').style.width=w+'px'",width)
        page.evaluate("card._renderContent(true)")
        assert page.evaluate('document.documentElement.scrollWidth')<=width,width
        assert page.locator('.hem-room-air-chip89').count()<=10
        for heading in page.locator('.hem-room-glance87').all():
            assert heading.bounding_box()['height']<=58
    assert not errors,errors
    browser.close()
print('BETA90_CARD_STABLE_SCROLL_AND_FOUR_SENSOR_SUMMARY=PASS')
