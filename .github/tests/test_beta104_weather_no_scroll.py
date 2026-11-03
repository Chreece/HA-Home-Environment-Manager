"""Beta104: no horizontal scrollbars; responsive weather summary and pinned attributes."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import runpy,shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
fixture=runpy.run_path(str(ROOT/'.github/tests/test_beta87_compact_browser.py'))
states=deepcopy(fixture['states'])
dashboard=deepcopy(fixture['data'])
primary='binary_sensor.warning_elsdorf'
headline='Entwarnung: Kampfmittelfund - Rhein-Erft-Kreis / Stadt Elsdorf'
native={'headline':headline,
  'description':'Die Warnung ist aufgehoben.<br/><br/>Mehr Informationen von der Feuerwehr.'*8,
  'severity':'moderate','friendly_name':'Wesseling warning',
  'nested':{'hazard':'found object','long_native_data':['a'*180]*4}}
states[primary]={'state':'on','attributes':native}
dashboard['outdoor'].update(
  warnings=[{'entity_id':primary,'name':'Wesseling warning','active':True}],
  blockers=[{'code':'active_warning','label':'Wesseling warning','value':''}])
states['sensor.hem']['attributes'].update(warning_sources=[primary],dashboard=dashboard)
chrome=shutil.which('chromium') or shutil.which('google-chrome')
assert chrome,'Chromium required'
with sync_playwright() as playwright:
  browser=playwright.chromium.launch(executable_path=chrome,headless=True,
    args=['--no-sandbox','--disable-dev-shm-usage'])
  page=browser.new_page(viewport={'width':590,'height':850})
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content("""<html><body style="margin:0;background:#111;color:#eee">
    <style>*{box-sizing:border-box}</style></body></html>""")
  page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
  page.evaluate("""({states})=>{
    window.card=document.createElement('home-environment-manager-card');
    document.body.append(card);
    card._hass={language:'el',states,localize:()=>undefined};
    card._config={entity:'sensor.hem'};
    card._renderContent(true);
  }""",{'states':states})
  for width in (320,340,360,390,480,590,800):
    page.set_viewport_size({'width':width,'height':850})
    row=page.locator('.hem-outside-details87')
    assert row.count()==1
    layout=row.evaluate("""node=>{
      const chip=node.querySelector('.hem-wx-chip103');
      const rect=node.getBoundingClientRect();
      const c=chip?.getBoundingClientRect();
      return {client:node.clientWidth,scroll:node.scrollWidth,
        overflow:getComputedStyle(node).overflowX,
        outerWidth:rect.width,
        chipWidth:c?.width,chipLeft:c?.left,chipRight:c?.right,
        rowLeft:rect.left,rowRight:rect.right,
        height:rect.height}
    }""")
    assert layout['overflow']!='auto', (width,layout)
    assert layout['scroll']<=layout['client']+2,(width,layout)
    assert layout['chipWidth']>35,(width,layout)
    assert layout['chipRight']<=layout['rowRight']+2,(width,layout)
    assert layout['chipLeft']>=layout['rowLeft']-2,(width,layout)
    assert layout['height']<=29,(width,layout)
  chip=page.locator('button.hem-wx-chip103')
  assert 'Entwarnung: Kampfmittelfund' in chip.inner_text()
  assert 'Stadt Elsdorf' not in chip.inner_text()  # full location in details
  assert headline in chip.get_attribute('title')
  chip.click()
  popup=page.locator('.hem-wx-dialog103')
  assert popup.is_visible()
  assert popup.locator('.hem-wx-row103').count()==len(native)+1
  assert headline in popup.inner_text()
  assert 'long_native_data' in popup.inner_text()
  assert popup.evaluate("(el)=>getComputedStyle(el).scrollbarWidth")=='none'
  # Scroll *content* when necessary, but NEVER display scrollbar chrome.
  page.evaluate("card.shadowRoot.querySelector('.hem-wx-dialog103').scrollTop=100")
  assert popup.is_visible()
  popup.locator('[data-wx-close103]').click()
  assert popup.count()==0
  # Other outdoor warnings cannot create horizontal scrollbars either.
  page.evaluate("""()=>{
    const states={...card._hass.states};
    const hem=states['sensor.hem'];
    states['sensor.hem']={...hem,attributes:{...hem.attributes,
      dashboard:{...hem.attributes.dashboard,outdoor:{
        ...hem.attributes.dashboard.outdoor,
        blockers:[{code:'weather_wind',label:'Wind',value:'strong gusts above threshold'}],
        warnings:[{entity_id:'binary_sensor.warning_elsdorf',name:'test',active:true}]
      }}}};
    card.hass={...card._hass,states};
  }""")
  page.wait_for_function("""()=>card.shadowRoot.querySelector('.hem-outside-details87 .reason')""")
  for width in (320,590):
    page.set_viewport_size({'width':width,'height':850})
    row=page.locator('.hem-outside-details87')
    layout=row.evaluate("el=>({client:el.clientWidth,scroll:el.scrollWidth,overflow:getComputedStyle(el).overflowX})")
    assert layout['overflow']!='auto',(width,layout)
    assert layout['scroll']<=layout['client']+2,(width,layout)
  assert not errors,errors
  browser.close()
print('BETA104_NO_HORIZONTAL_SCROLLBAR_COMPACT_WEATHER_AND_PINNED_DETAILS=PASS')
