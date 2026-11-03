"""Beta103: warning chip never collapses; manual all-attrs dialog survives HA refresh."""
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
import runpy,shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta87_compact_browser.py'))
states=deepcopy(base['states'])
dashboard=deepcopy(base['data'])
source='binary_sensor.warning_elsdorf'
attrs={'headline':'Entwarnung: Kampfmittelfund - Rhein-Erft-Kreis / Stadt Elsdorf',
       'description':'Dies ist die Entwarnung.<br/><br/>Die Warnung ist aufgehoben.' +
          ' Verkehrshinweis. '*70,
       'severity':'severe','start':'2026-11-03T12:14:12+01:00',
       'end':'2026-11-03T19:00:00+01:00','nested':{'warnings':[1,2,3]},
       'friendly_name':'Warnung Wesseling'}
states[source]={'state':'on','attributes':attrs}
dashboard['outdoor'].update(
   warnings=[{'entity_id':source,'name':'Warnung Wesseling','active':True}],
   blockers=[{'code':'active_warning','label':'Warnung Wesseling','value':''}])
states['sensor.hem']['attributes'].update(dashboard=dashboard,warning_sources=[source])
chrome=shutil.which('chromium') or shutil.which('google-chrome')
assert chrome
with sync_playwright() as browser_api:
    browser=browser_api.chromium.launch(executable_path=chrome,headless=True,
        args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':570,'height':800})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content('<html><body style="margin:0;background:#111;color:white"></body></html>')
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    page.evaluate("""({states})=>{
       window.card=document.createElement('home-environment-manager-card');
       document.body.append(card);
       card._hass={language:'de',states,localize:()=>undefined};
       card._config={entity:'sensor.hem'};
       card._renderContent(true);
    }""",{'states':states})
    chip=page.locator('button.hem-wx-chip103')
    assert chip.is_visible()
    box=chip.bounding_box()
    assert box['width']>=170 and box['height']>=20,box
    assert 'Entwarnung' in chip.inner_text(),chip.inner_text()
    assert page.locator('.hem-outside-details87').count()==1
    chip.click()
    popup=page.locator('.hem-wx-dialog103')
    assert popup.is_visible()
    assert 'Die Warnung ist aufgehoben' in popup.inner_text()
    assert 'severity' in popup.inner_text()
    assert popup.locator('.hem-wx-row103').count()==len(attrs)+1
    page.evaluate("card.shadowRoot.querySelector('.hem-wx-dialog103').scrollTop=155")
    prior=page.evaluate("card.shadowRoot.querySelector('.hem-wx-dialog103').scrollTop")
    assert prior>0,prior
    page.evaluate("""()=>{
      for(let n=0;n<35;n++){
        const states={...card._hass.states};
        const native=states['binary_sensor.warning_elsdorf'];
        states['binary_sensor.warning_elsdorf']={...native,attributes:{
          ...native.attributes,severity:n%2?'moderate':'severe'}};
        card.hass={...card._hass,states};
      }
    }""")
    popup=page.locator('.hem-wx-dialog103')
    assert popup.is_visible(), 'dialog closed by HA refresh'
    assert popup.get_attribute('popover')=='manual'
    assert page.evaluate("card.shadowRoot.querySelector('.hem-wx-dialog103').scrollTop")>=prior-2
    # Native manual popover does not dismiss when clicking outside it.
    page.mouse.click(560,760)
    assert popup.is_visible()
    assert 'severity' in popup.inner_text()
    page.set_viewport_size({'width':340,'height':600})
    # Normal card updates must leave the popup pinned and within viewport.
    page.evaluate("card._renderContent(true)")
    assert popup.is_visible()
    assert popup.bounding_box()['width']<=340
    assert popup.bounding_box()['height']<=600
    popup.locator('[data-wx-close103]').click()
    assert popup.count()==0
    # Escape also closes an explicitly opened dialog.
    page.locator('button.hem-wx-chip103').click()
    assert page.locator('.hem-wx-dialog103').is_visible()
    page.locator('.hem-wx-dialog103').press('Escape')
    assert page.locator('.hem-wx-dialog103').count()==0
    # Inactive or unrelated warnings must not gain clickable details.
    page.evaluate("""()=>{
      const states={...card._hass.states};
      states['sensor.hem']={...states['sensor.hem'],
        attributes:{...states['sensor.hem'].attributes,
          dashboard:{...states['sensor.hem'].attributes.dashboard,
            outdoor:{...states['sensor.hem'].attributes.dashboard.outdoor,
              warnings:[]}}}};
      card.hass={...card._hass,states};
    }""")
    # Live card reconciliation may defer its DOM commit for a frame.
    page.wait_for_function(
      "()=>card.shadowRoot.querySelectorAll('button.hem-wx-chip103').length===0",
      timeout=5000)
    assert page.locator('button.hem-wx-chip103').count()==0
    assert not errors,errors
    browser.close()
print('BETA103_VISIBLE_WARNING_PINNED_ATTRIBUTES_REFRESH_SCROLL_MOBILE=PASS')
