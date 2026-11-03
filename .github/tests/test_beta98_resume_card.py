"""Beta98 Chromium: paused PID remains resumable and describes self-recovery.

The production HEM card runs in actual Chromium. No live devices, network
calls, or native service requests. Regression for the user's disabled
Continue Automatic with an already selected PID control mode.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import runpy
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
fixture=runpy.run_path(str(ROOT/'.github/tests/test_beta87_compact_browser.py'))
states=deepcopy(fixture['states'])
data=deepcopy(fixture['data'])
data['rooms']=deepcopy(fixture['rooms'])
states['sensor.hem']['attributes']['dashboard']=data

# Automatic is ALREADY selected, but the real native device has an
# outstanding physical command. HA says the user can press its Resume button.
controller='climate.managed_0_1'
source='climate.physical_0_1'
selector='select.control_0_1'
resume='button.resume_0_1'
status='sensor.control_0_1'
states[controller]['attributes']['control_mode']='pid'
states[selector]['state']='pid'
states[status]['attributes'].update({
    'status_code':'awaiting_physical_acknowledgement',
    'command_pending':True,
    'automatic_recovery_requested':True,
    'settings_saved':True,
    'recovery_detail':'Settings saved; HEM verifies previous physical command',
    'native_resume_recovery':{
       'decision':'settling','entity':source,'requested':'dry',
       'observed':'off','settings_saved':True,
       'instructions':('Settings and Automatic/PID are saved. HEM '
                       'will verify the device automatically; '
                       'you do not need to press again.'),
       'remaining_seconds':60,
    },
})
states[resume]['state']='unknown' # Available HA button with no past click.
states[resume]['attributes'].update({
    'controller_resume_role':'continue_automatic',
    'automatic_already_selected':False,
    'automatic_recovery_requested':True,
})
# A healthy Auto controller must still honor HA saying unavailable.
states['button.resume_0_0']['state']='unavailable'
chrome=shutil.which('chromium') or shutil.which('google-chrome')
assert chrome, 'Chromium required'
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(executable_path=chrome,headless=True,
         args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':390,'height':900})
    errors=[]
    page.on('pageerror',lambda ex:errors.append(str(ex)))
    page.set_content("""<html><head><style>
      *{box-sizing:border-box}body{margin:0;background:#111;color:#eee}
      :root{--primary-text-color:#eee;--secondary-text-color:#aaa;
        --card-background-color:#202020;--secondary-background-color:#292929;
        --divider-color:#444}
    </style></head><body></body></html>""")
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    page.evaluate("""({states})=>{
        window.calls=[];
        window.card=document.createElement('home-environment-manager-card');
        document.body.append(card);
        card._hass={language:'en',states,localize:()=>undefined,
            callService:(...args)=>{calls.push(args);return Promise.resolve();}};
        card._config={entity:'sensor.hem'};
        card._renderContent(true);
    }""",{'states':states})
    room=page.locator('[data-room-fold87="room0"]')
    room.locator(':scope > summary').evaluate('(el)=>el.click()')
    device=room.locator('[data-device-fold87="climate.managed_0_1"]')
    device.locator(':scope > summary').evaluate('(el)=>el.click()')
    button=device.locator('.hem-continue-auto89')
    assert button.count()==1
    assert button.is_enabled(), 'PID selected but paused should not disable Continue'
    recovery=device.locator('.hem-resume-recovery')
    assert recovery.count()==1
    text=recovery.inner_text()
    assert 'Settings and Automatic/PID are saved' in text,text
    assert 'press again' not in text.lower()
    assert 'dry' in text and 'off' in text and 'Previous command' not in text
    assert 'Settings saved' in device.inner_text()
    button.click()
    page.wait_for_timeout(50)
    assert page.evaluate('calls')==[
        ['button','press',{'entity_id':resume}]
    ],page.evaluate('calls')
    healthy=room.locator('[data-device-fold87="climate.managed_0_0"]')
    healthy.locator(':scope > summary').evaluate('(el)=>el.click()')
    assert healthy.locator('.hem-continue-auto89').is_disabled()

    # A newly confirmed ACK and restored automatic availability are reflected
    # in-place without closing the expansion or disturbing the 4-sensor layout.
    page.evaluate("""({status,resume})=>{
      const next=structuredClone(card._hass.states);
      next[status].attributes.native_resume_recovery=null;
      next[status].attributes.command_pending=false;
      next[status].attributes.automatic_recovery_requested=false;
      next[status].attributes.recovery_detail=null;
      next[resume].state='unavailable';
      card._hass={...card._hass,states:next};
      card._renderContent(true);
    }""",{'status':status,'resume':resume})
    assert button.is_disabled()
    assert device.get_attribute('open') is not None
    assert device.locator('.hem-resume-recovery').count()==0
    for width in (320,390,590):
        page.set_viewport_size({'width':width,'height':900})
        page.evaluate('card._renderContent(true)')
        assert page.evaluate('document.documentElement.scrollWidth')<=width,width
    assert len(page.evaluate('calls'))==1
    assert not errors,errors
    browser.close()
print('BETA98_CHROMIUM_PAUSED_PID_RESUME_ACTIONABLE_AND_HUMAN_ACK=PASS')
