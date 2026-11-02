"""Beta85 actual Chromium UI for an interrupted native command and Resume.

The real dashboard functions run with synthetic HA states and service stubs.
No physical native climate command can be dispatched from this test.
"""
from __future__ import annotations
import runpy
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta66_browser.py'))
states=base['states'].copy()
room=base['room'].copy()
native=states['climate.managed']
native={**native, 'attributes':{**native['attributes'],
    'control_mode':'manual','physical_source_state':'off'}}
states['climate.managed']=native
# Continue Automatic is unavailable while PID/Automatic is already selected.
# Simulate the real native user override, which demoted this controller to
# Manual and retained its prior algorithm for explicit restoration.
states['select.method']={**states['select.method'],'state':'manual'}
status=states['sensor.control_status']
states['sensor.control_status']={**status,'attributes':{**status['attributes'],
    'status_code':'paused','paused_reason':'native_command_failed_or_uncertain',
    'command_pending':True,
    'native_resume_recovery':{
        'decision':'first_check','entity':'climate.comfee','requested':'dry',
        'observed':'off','remaining_seconds':60,'phase':'intent',
        'needs_physical_check':True,
    }
}}
def row(state,**attributes):
    return {'state':state,'attributes':{
        'area_id':'bedroom','source_entity_ids':['climate.comfee'],
        **attributes,
    }}
states['button.resume']=row('unknown',controller_resume_role='check_and_continue',
    native_resume_recovery=states['sensor.control_status']['attributes']['native_resume_recovery'])
executable=shutil.which('chromium') or shutil.which('google-chrome')
assert executable,'Chromium required for actual UI test'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=executable,headless=True,
        args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':440,'height':1100})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content('<html><body></body></html>')
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    page.evaluate("""({states,room})=>{
        window.calls=[];window.room=room;
        window.card=document.createElement('home-environment-manager-card');
        document.body.append(card);
        card._hass={language:'en',states,localize:()=>undefined,
            callService:(...args)=>{calls.push(args);return Promise.resolve();}};
        window.draw=()=>{card.shadowRoot.innerHTML=card._styles()+
            '<ha-card class="shell"><div class="content">'+
             card._climatePanel(room)+'</div></ha-card>';};
        draw();
    }""",{'states':states,'room':room})
    recovery=page.locator('.hem-resume-recovery')
    assert recovery.count()==1
    assert 'Previous command not confirmed' in recovery.inner_text()
    assert 'dry' in recovery.inner_text() and 'off' in recovery.inner_text()
    assert '60 s' in recovery.inner_text()
    assert page.evaluate('calls.length')==0
    button=page.locator('[data-native-resume="button.resume"]')
    assert button.count()==1
    button.click()
    page.wait_for_timeout(40)
    assert page.evaluate('calls')==[
        ['button','press',{'entity_id':'button.resume'}]]
    page.evaluate("""()=>{
        card.shadowRoot.querySelector('[data-native-resume]').dataset.nativeResume='button.unrelated';
        card.shadowRoot.querySelector('[data-native-resume]').click();
    }""")
    page.wait_for_timeout(20)
    assert page.evaluate('calls.length')==1
    for locale,label in [('el','Η προηγούμενη εντολή'),('de','Vorheriger Gerätebefehl')]:
        page.evaluate("(locale)=>{card._hass={...card._hass,language:locale};draw()}",locale)
        assert label in page.locator('.hem-resume-recovery').inner_text()
    page.evaluate("""()=>{
        const states={...card._hass.states};
        states['sensor.control_status']={
            ...states['sensor.control_status'],
            attributes:{...states['sensor.control_status'].attributes,
                native_resume_recovery:null}
        };
        states['button.resume']={...states['button.resume'],
            attributes:{...states['button.resume'].attributes,native_resume_recovery:null}};
        card._hass={...card._hass,states};draw();
    }""")
    assert page.locator('.hem-resume-recovery').count()==0
    assert not errors,errors
    browser.close()
print("BETA85_CHROMIUM_NATIVE_RESUME_EXPLANATION_AND_EXACT_BUTTON=PASS")
