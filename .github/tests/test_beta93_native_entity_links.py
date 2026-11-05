"""Beta93 native-vs-HEM titles: real browser, real card interactions.

The collapsed controller title opens the HEM facade. The expanded heading
shows the native Home Assistant integration's friendly_name and opens only
that independently verified physical entity. Test multiple sources, native
renames, stale/forged links, and mobile layout without invoking hardware.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import runpy
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
baseline=runpy.run_path(str(ROOT/'.github/tests/test_beta87_compact_browser.py'))
states=deepcopy(baseline['states'])
data=deepcopy(baseline['data'])
data['rooms']=deepcopy(baseline['rooms'])
states['sensor.hem']['attributes']['dashboard']=data

area='room0'
hem='climate.managed_0_0'
native='climate.physical_0_0'
fan='fan.mi_air_purifier_3c'
states[hem]['attributes']['friendly_name']='Mi Air Purifier 3C Controller Κλίμα · Mi Air Purifier 3C'
states[hem]['attributes']['physical_primary_entity_id']=native
states[native]['attributes']['friendly_name']='Mi Air Purifier 3C'
states[native]['state']='fan_only'
states[native]['attributes']['hvac_action']='idle'

chrome=shutil.which('chromium') or shutil.which('google-chrome')
assert chrome,'Chromium required'
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(executable_path=chrome,headless=True,
        args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':590,'height':1000})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.set_content("""<html><head><style>
       :root{--primary-text-color:#eee;--secondary-text-color:#aaa;
         --card-background-color:#202020;--secondary-background-color:#292929;
         --divider-color:#444}
       body{background:#111;color:#eee;margin:0;}
       </style></head><body></body></html>""")
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    page.evaluate("""({states})=>{
      window.calls=[];
      window.info=[];
      window.card=document.createElement('home-environment-manager-card');
      document.body.append(card);
      card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
      card._hass={language:'el',states,localize:()=>undefined,
        callService:(...args)=>{
          calls.push(args);
          throw Error('Test must not call any device service');
        }};
      card._config={entity:'sensor.hem'};
      card._renderContent(true);
    }""",{'states':states})

    room=page.locator('[data-room-fold87="room0"]')
    room.locator(':scope > summary').click()
    device=room.locator('[data-device-fold87="climate.managed_0_0"]')
    collapsed=device.locator(':scope > summary button[data-open-controller89]')
    assert collapsed.count()==1
    assert 'Controller Κλίμα' in collapsed.inner_text(),collapsed.inner_text()
    assert device.get_attribute('open') is None
    collapsed.click()
    assert page.evaluate('info')==[hem],page.evaluate('info')
    assert device.get_attribute('open') is None,'HEM title click must not expand'

    icon=device.locator(':scope > summary button[data-open-native89]')
    assert icon.count()==1
    icon.click()
    assert page.evaluate('info')[-1]==native
    assert device.get_attribute('open') is None

    device.locator(':scope > summary').evaluate('(node)=>node.click()')
    assert device.get_attribute('open') is not None
    # The compact wrapper is the managed-controller's child; its parent
    # retains the HEM metadata while containing the physical-title button.
    section=device.locator('xpath=..')
    assert 'managed-controller' in (section.get_attribute('class') or '')
    assert section.get_attribute('data-managed-climate93')==hem
    link=section.locator('button[data-open-physical93]')
    assert link.count()==1
    assert link.get_attribute('data-open-physical93')==native
    assert link.inner_text().strip()=='Mi Air Purifier 3C',link.inner_text()
    assert 'Controller' not in link.inner_text()
    assert section.locator('button[data-open-climate]').count()==0
    assert native in link.get_attribute('title')
    link.click()
    assert page.evaluate('info')[-1]==native,page.evaluate('info')
    assert device.get_attribute('open') is not None

    # A native integration rename is reflected without reloading Lovelace:
    # the HEM facade state itself stays unchanged.
    page.evaluate("""({native})=>{
      const before=card._hass.states;
      const changed={...before[native],attributes:{
        ...before[native].attributes,friendly_name:'My Living Room Air Purifier'}};
      card._hass={...card._hass,states:{...before,[native]:changed}};
      card._renderContent(false);
    }""",{'native':native})
    page.wait_for_timeout(90)
    assert link.inner_text().strip()=='My Living Room Air Purifier'
    collapsed=device.locator(':scope > summary button[data-open-controller89]')
    assert 'Controller Κλίμα' in collapsed.inner_text()
    link.click()
    assert page.evaluate('info')[-1]==native

    # Never guess the endpoint if multiple source entities exist and there
    # is no authoritative physical_primary_entity_id.
    page.evaluate("""({hem,native,fan})=>{
      const before=card._hass.states;
      const facade={...before[hem],attributes:{
        ...before[hem].attributes,source_entity_ids:[native,fan]}};
      delete facade.attributes.physical_primary_entity_id;
      card._hass={...card._hass,states:{
        ...before,[hem]:facade,[fan]:{state:'on',attributes:{
          friendly_name:'Mi Air Purifier 3C Fan'}}
      }};
      card._renderContent(true);
    }""",{'hem':hem,'native':native,'fan':fan})
    assert section.locator('button[data-open-physical93]').count()==0
    assert section.locator('.hem-physical-title93-unavailable').count()==1

    # Multiple sources are fine when HEM declares one verified primary.
    page.evaluate("""({hem,fan})=>{
      const before=card._hass.states;
      const facade={...before[hem],attributes:{
        ...before[hem].attributes,physical_primary_entity_id:fan}};
      card._hass={...card._hass,states:{...before,[hem]:facade}};
      card._renderContent(true);
    }""",{'hem':hem,'fan':fan})
    link=section.locator('button[data-open-physical93]')
    assert link.get_attribute('data-open-physical93')==fan
    assert link.inner_text().strip()=='Mi Air Purifier 3C Fan'
    link.click()
    assert page.evaluate('info')[-1]==fan

    # Forged/stale DOM references never open an unrelated HA entity.
    previous=page.evaluate('info.length')
    link.evaluate("(node)=>node.setAttribute('data-open-physical93','fan.other')")
    link.click()
    assert page.evaluate('info.length')==previous

    # Folded text still leads exclusively to HEM even with multiple sources.
    collapsed=device.locator(':scope > summary button[data-open-controller89]')
    collapsed.click()
    assert page.evaluate('info')[-1]==hem
    assert device.get_attribute('open') is not None
    for width in (320,360,590):
      page.set_viewport_size({'width':width,'height':1000})
      page.evaluate("card._renderContent(true)")
      assert page.evaluate('document.documentElement.scrollWidth')<=width,width

    assert page.evaluate('calls')==[],page.evaluate('calls')
    assert not errors,errors
    browser.close()
print('BETA93_NATIVE_EXPANDED_LINK_HEM_FOLDED_LINK_RENAME_AND_PROVENANCE=PASS')
