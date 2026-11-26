"""Beta91 actual Chromium: no DOM replacement/flicker under HA updates.

Validates that connected card/room/device/links retain object identity,
keyboard focus and native popover while state updates repeatedly. The old
scroll-position workaround alone could not guarantee this.
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
data['rooms']=rooms
states['sensor.hem']['attributes']['dashboard']=data
chrome=shutil.which('chromium') or shutil.which('google-chrome')
assert chrome,'Chromium required'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=chrome,headless=True,
        args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':550,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content("""<!doctype html><html><head><style>
       *{box-sizing:border-box}body{margin:0;background:#111;color:#eee}
       :root{--primary-text-color:#eee;--secondary-text-color:#aaa;
       --card-background-color:#202020;--secondary-background-color:#292929;
       --divider-color:#444}
       #scroller{height:350px;overflow-y:auto;width:520px}
       </style></head><body><main id="scroller"></main></body></html>""")
    page.add_script_tag(path=str(ROOT/'frontend/home-environment-manager-card.js'))
    page.evaluate("""({states})=>{
        window.card=document.createElement('home-environment-manager-card');
        document.getElementById('scroller').append(card);
        card._hass={language:'en',states,localize:()=>undefined,
            callService:()=>Promise.reject(new Error('No actuator I/O authorized'))};
        card._config={entity:'sensor.hem'};
        card._roomsExpanded87=new Set(['room0']);
        card._devicesExpanded87=new Set(['climate.managed_0_0']);
        window.styleBuilds=0;
        const styles=card._styles;
        card._styles=function(){styleBuilds++;return styles.call(this)};
        card._renderContent(true);
        window.originalCard=card.shadowRoot.querySelector('ha-card.shell');
        window.originalRoom=card.shadowRoot.querySelector('[data-room-fold87="room0"]');
        window.originalDevice=card.shadowRoot.querySelector('[data-device-fold87="climate.managed_0_0"]');
        window.originalLink=window.originalDevice.querySelector('button[data-open-controller89]');
        window.originalLink.focus();
        const scroller=document.getElementById('scroller');
        scroller.scrollTop=220;
        window.originalScroll=scroller.scrollTop;
    }""",{'states':states})
    initial=page.evaluate("originalScroll")
    assert initial>100,initial
    for i in range(60):
        page.evaluate("""i=>{
          const old=card._hass.states;
          const native={...old['climate.physical_0_0'],
            attributes:{...old['climate.physical_0_0'].attributes,
              hvac_action:i%2?'heating':'idle'}};
          const states={...old,'climate.physical_0_0':native};
          card._hass={...card._hass,states};
          card._renderContent(true);
        }""",i)
        result=page.evaluate("""()=>({
          card:originalCard===card.shadowRoot.querySelector('ha-card.shell'),
          room:originalRoom===card.shadowRoot.querySelector('[data-room-fold87="room0"]'),
          device:originalDevice===card.shadowRoot.querySelector('[data-device-fold87="climate.managed_0_0"]'),
          link:originalLink===card.shadowRoot.querySelector('[data-device-fold87="climate.managed_0_0"] button[data-open-controller89]'),
          focus:card.shadowRoot.activeElement===originalLink,
          scroll:document.getElementById('scroller').scrollTop,
          opened:originalRoom.open&&originalDevice.open,
          updates:card._stableDomUpdates91||0
        })""")
        assert all(result[k] for k in ('card','room','device','link','focus','opened')), (i,result)
        assert abs(result['scroll']-initial)<=3,(i,result,initial)
    result=page.evaluate("""()=>{
        const data=structuredClone(card._hass.states['sensor.hem'].attributes.dashboard);
        // Live attention changes should never reorder the entire room list.
        data.rooms.forEach((room,index)=>room.status=index%2?'attention':'safe');
        const current=card._hass.states;
        const state={...current['sensor.hem'],attributes:{
          ...current['sensor.hem'].attributes,dashboard:data}};
        card._hass={...card._hass,states:{...current,'sensor.hem':state}};
        const before=[...card.shadowRoot.querySelectorAll('.hem-room-fold87')].map(
          el=>el.getAttribute('data-room-fold87'));
        card._renderContent(true);
        const after=[...card.shadowRoot.querySelectorAll('.hem-room-fold87')].map(
          el=>el.getAttribute('data-room-fold87'));
        return {before,after,identical:originalCard===card.shadowRoot.querySelector('ha-card.shell')};
    }""")
    assert result['before']==result['after'] and result['identical'],result
    # Inserting and reordering siblings must preserve the focused control's owner.
    for change in ("insert", "rename", "remove"):
        report=page.evaluate("""change=>{
          const state=card._hass.states['sensor.hem'];
          const dashboard=structuredClone(state.attributes.dashboard);
          const extra={...dashboard.rooms[0],area_id:'new-area',name:'AAA new area'};
          if(change==='insert') dashboard.rooms.push(extra);
          if(change==='rename') dashboard.rooms.find(r=>r.area_id==='room0').name='ZZZ room';
          if(change==='remove') dashboard.rooms=dashboard.rooms.filter(r=>r.area_id!=='new-area');
          card._hass.states={...card._hass.states,'sensor.hem':{...state,
            attributes:{...state.attributes,dashboard}}};
          card._renderContent(true);
          return {room:originalRoom===card.shadowRoot.querySelector('[data-room-fold87="room0"]'),
            expanded:originalRoom.open,focused:card.shadowRoot.activeElement===originalLink,
            owner:originalLink.closest('[data-room-fold87]')?.dataset.roomFold87,
            styles:styleBuilds};
        }""",change)
        assert report=={'room':True,'expanded':True,'focused':True,'owner':'room0','styles':1}, (change,report)
    page.locator('[data-device-fold87="climate.managed_0_0"] details.hem-context76 > summary').first.click()
    page.wait_for_timeout(50)
    popup=page.locator('.hem-floating-info87')
    assert popup.count()==1 and popup.is_visible()
    page.evaluate("card._renderContent(true)")
    assert popup.count()==1 and popup.is_visible(),'Information popup flickered closed after HA update'
    assert page.evaluate('card._stableDomUpdates91')>=60
    assert not errors,errors
    browser.close()
print('BETA91_CHROMIUM_IN_PLACE_DOM_60_UPDATES_FOCUS_SCROLL_HELP=PASS')
