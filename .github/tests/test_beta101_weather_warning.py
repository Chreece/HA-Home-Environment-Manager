"""Weather warnings: native subject, reported attributes, click, live updates."""
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
import runpy,shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
baseline=runpy.run_path(str(ROOT/'.github/tests/test_beta87_compact_browser.py'))
states=deepcopy(baseline['states'])
data=deepcopy(baseline['data'])
entity='binary_sensor.warnung_wesseling'
name='Warnung Wesseling Stadt'
native={
    'headline':'Entwarnung: Kampfmittelfund - Rhein-Erft-Kreis / Stadt Elsdorf',
    'description':'Die Warnung ist aufgehoben.<br/><br/>Die Feuerwehr informiert.',
    'level':3,'start':'2026-11-03T12:00:00+01:00',
    'end':'2026-11-03T13:00:00+01:00',
    'nested':{'items':['<img src=x onerror=alert(1)>',{'level':2}]},
    'friendly_name':name
}
states[entity]={'state':'on','attributes':native}
data['outdoor']['warnings']=[{'entity_id':entity,'name':name,'active':True}]
data['outdoor']['blockers']=[{'code':'active_warning','label':name,'value':''}]
states['sensor.hem']['attributes'].update(warning_sources=[entity],dashboard=data)
chrome=shutil.which('chromium') or shutil.which('google-chrome')
assert chrome,'Chromium required for live card test'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=chrome,headless=True,
        args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':590,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content('<html><body style="margin:0;background:#111;color:#eee"></body></html>')
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    page.evaluate("""({states})=>{
       window.info=[];
       window.card=document.createElement('home-environment-manager-card');
       document.body.append(card);
       card.addEventListener('hass-more-info',e=>info.push(e.detail.entityId));
       card._hass={language:'el',states,localize:()=>undefined};
       card._config={entity:'sensor.hem'};
       card._renderContent(true);
    }""",{'states':states})
    chip=page.locator('button.hem-wx-chip103')
    assert chip.count()==1
    assert 'Entwarnung: Kampfmittelfund' in chip.inner_text()
    assert 'Die Warnung ist aufgehoben' in chip.get_attribute('title')
    assert chip.bounding_box()['width']>=170,chip.bounding_box()
    assert chip.is_visible()
    chip.click()
    pop=page.locator('.hem-wx-dialog103')
    pop.wait_for(state='visible')
    assert pop.get_attribute('popover')=='manual'
    assert 'Entwarnung: Kampfmittelfund' in pop.inner_text()
    assert 'Die Warnung ist aufgehoben.' in pop.inner_text()
    assert pop.locator('.hem-wx-row103').count()==len(native)+1
    assert 'headline' in pop.inner_text() and 'description' in pop.inner_text()
    assert 'nested' in pop.inner_text()
    assert page.evaluate("card.shadowRoot.querySelector('img[onerror]')") is None
    # Clicking anywhere outside the panel must not light-dismiss the warning.
    page.mouse.click(575,840)
    assert pop.is_visible()
    pop.locator('[data-wx-native103]').click()
    assert page.evaluate('info')==[entity]
    assert pop.count()==0
    # A native attribute edit updates even when dashboard revision is stable.
    page.evaluate("""()=>{
        const states={...card._hass.states};
        states['binary_sensor.warnung_wesseling']={
          ...states['binary_sensor.warnung_wesseling'],
          attributes:{...states['binary_sensor.warnung_wesseling'].attributes,
            headline:'Sturmböen',description:'Windwarnung'}};
        card.hass={...card._hass,states};
    }""")
    # HA's stable-DOM scheduler defers a live weather refresh briefly.
    page.wait_for_function(
      "() => !!card.shadowRoot.querySelector('button.hem-wx-chip103')?.textContent.includes('Sturmböen')",
      timeout=5000)
    chip=page.locator('button.hem-wx-chip103')
    assert 'Sturmböen' in chip.inner_text()
    chip.click()
    pop=page.locator('.hem-wx-dialog103')
    assert 'Windwarnung' in pop.inner_text()
    pop.locator('[data-wx-close103]').click()
    assert pop.count()==0
    # Distinct warnings with the same friendly name use their entity IDs.
    page.evaluate("""()=>{
        const states={...card._hass.states};
        states['sensor.second_warning']={state:'on',attributes:{
          friendly_name:'Warnung Wesseling Stadt',
          headline:'Glätte',description:'Glatteis'}};
        states['sensor.hem']={...states['sensor.hem'],
          attributes:{...states['sensor.hem'].attributes,
            warning_sources:['binary_sensor.warnung_wesseling','sensor.second_warning'],
            dashboard:{...states['sensor.hem'].attributes.dashboard,
              outdoor:{...states['sensor.hem'].attributes.dashboard.outdoor,
                warnings:[
                  {entity_id:'binary_sensor.warnung_wesseling',name:'same',active:true},
                  {entity_id:'sensor.second_warning',name:'same',active:true}]}}}};
        card.hass={...card._hass,states};
    }""")
    page.wait_for_function(
       "()=>card.shadowRoot.querySelectorAll('button.hem-wx-chip103').length===2")
    chips=page.locator('button.hem-wx-chip103')
    assert 'Sturmböen' in chips.nth(0).inner_text()
    assert 'Glätte' in chips.nth(1).inner_text()
    assert 'Glatteis' in chips.nth(1).get_attribute('title')
    assert chips.nth(1).get_attribute('data-wx-open103')=='sensor.second_warning'
    page.set_viewport_size({'width':360,'height':740})
    # Narrow cards retain the first warning inline and expose additional
    # warnings through the explicit outdoor information disclosure.
    assert chips.nth(0).is_visible() and not chips.nth(1).is_visible()
    page.locator('details.hem-outside-info123 > summary').click()
    information=page.locator('.hem-floating-info87')
    information.wait_for(state='visible')
    second=information.locator('[data-outside-warning123="sensor.second_warning"]')
    assert 'Sturmböen' in information.locator(
        '[data-outside-warning123="binary_sensor.warnung_wesseling"]').inner_text()
    assert 'Glätte' in second.inner_text() and 'Glatteis' in second.inner_text()
    second.click()
    assert information.count()==0
    pop=page.locator('.hem-wx-dialog103')
    pop.wait_for(state='visible')
    assert pop.is_visible() and pop.bounding_box()['width']<=360
    assert 'Glatteis' in pop.inner_text()
    assert pop.locator('.hem-wx-row103').count()==4
    assert all(key in pop.inner_text() for key in ('friendly_name','headline','description'))
    pop.locator('[data-wx-native103="sensor.second_warning"]').click()
    assert page.evaluate('info')==[entity,'sensor.second_warning']
    assert pop.count()==0
    assert not errors,errors
    browser.close()
print('BETA101_WEATHER_WARNING_NATIVE_SUBJECT_ALL_ATTRS_RETAINED=PASS')
