"""Real card/Options regression for door/Eco placement and contextual names.

Only mocked Home Assistant transports are used; no appliance is contacted.
"""
from __future__ import annotations
from copy import deepcopy
import os
from pathlib import Path
import runpy
import shutil
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / 'custom_components/environment_manager/frontend/air-quality-advisor-card.js'
room = runpy.run_path(str(ROOT / '.github/tests/test_beta114_room_settings.py'))
base = runpy.run_path(str(ROOT / '.github/tests/test_beta108_setpoint_feedback_browser.py'))
CHROME = os.getenv('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
assert CHROME, 'Chromium required for settings menu verification'
HEADINGS = {
    'en': 'Windows, doors, ventilation and shading',
    'el': 'Παράθυρα, πόρτες, αερισμός και σκίαση',
    'de': 'Fenster, Türen, Lüftung und Beschattung',
}
LABELS = r"""() => {
  const card=document.createElement('home-environment-manager-card');
  document.body.appendChild(card);
  card._hass={language:'el',states:{},entities:{},devices:{d:{name:'Gästezimmer Environment',area_id:'room0'}}};
  const saved={room:{name:'Gästezimmer'},area:'room0',device:'d'};
  const reg={device_id:'d'};
  const label=(attributes,record=reg,context=saved)=>card._hemSettingLabel062(
    'number.example',{attributes},record,context);
  const result={
    friendly:label({friendly_name:'Gästezimmer Environment ° Παρουσία χώρου · Καθυστέρηση κενού χώρου (λεπτά)'}),
    original:label({friendly_name:'ignored'},{...reg,original_name:'Gästezimmer Environment · Προφίλ · Ύπνος · Στόχος θέρμανσης (°C)'}),
    metadata:label({setting_display_name:'Προφίλ · Ύπνος · Στόχος ψύξης (°C)',setting_group:'Προφίλ'}),
    mode:label({setting_label:'Μέγιστη ισχύς (%)',operating_mode_label:'Θέρμανση'}),
    custom:label({setting_display_name:'Wrong'},{...reg,name:'My useful override'}),
    customOwner:label({setting_display_name:'Wrong'},{...reg,name:'Gästezimmer Environment · My useful override'}),
    legacyCustom:label({setting_display_name:'Wrong'},{...reg,name_by_user:'Custom legacy'}),
    unavailable:card._hemSettingLabel062('number.missing',null,{...reg,original_name_unprefixed:'Όριο υγρασίας (%)'},saved),
    degrees:label({friendly_name:'Gästezimmer Environment ° Ελάχιστη θερμοκρασία (°C)'}),
    noSubstring:label({friendly_name:'GästezimmerNord temperature'}),
  };
  card._hass.language='de';
  result.german=label({friendly_name:'Gästezimmer Environment Profil · Schlaf · Heizsollwert (°C)'});
  card._hass.language='en';
  result.home=label({friendly_name:'Home Environment Manager · Announcement · Repeat interval (min)'}, {}, {});
  result.device=label({friendly_name:'Bedroom radiator · Heat · Target (°C)'},
    {device_id:'rad'}, {device:'rad',controller:{climate:{attributes:{friendly_name:'Bedroom radiator'}}}});
  result.fallback=card._hemSettingLabel062('switch.empty',{attributes:{}},{},{},false,'Announce errors');
  card.remove();
  return result;
}"""

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME, headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage'])
    page=browser.new_page()
    page.add_script_tag(path=str(CARD))
    results=page.evaluate(LABELS)
    assert results == {
        'friendly':'Καθυστέρηση κενού χώρου (λεπτά)',
        'original':'Ύπνος · Στόχος θέρμανσης (°C)',
        'metadata':'Ύπνος · Στόχος ψύξης (°C)',
        'mode':'Θέρμανση · Μέγιστη ισχύς (%)',
        'custom':'My useful override', 'customOwner':'My useful override',
        'legacyCustom':'Custom legacy', 'unavailable':'Όριο υγρασίας (%)',
        'degrees':'Ελάχιστη θερμοκρασία (°C)',
        'noSubstring':'GästezimmerNord temperature',
        'german':'Schlaf · Heizsollwert (°C)',
        'home':'Repeat interval (min)', 'device':'Heat · Target (°C)',
        'fallback':'Announce errors',
    }, results
    page.close()

    for width in (320,390,760):
        for language in HEADINGS:
            page=browser.new_page(viewport={'width':width,'height':950})
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_content('''<style>body{margin:0;font:14px Arial;background:#111;color:#eee;
                --primary-text-color:#eee;--secondary-text-color:#bbb;--primary-color:#03a9f4;
                --card-background-color:#252525;--secondary-background-color:#292929;--divider-color:#494949}</style>''')
            page.evaluate(base['icon_fixture']())
            page.add_script_tag(path=str(CARD))
            states=deepcopy(base['fixture_definitions']()['states'])
            rooms=states['sensor.hem']['attributes']['dashboard']['rooms']
            states['sensor.hem']['attributes']['dashboard']['rooms']=rooms[:2]
            rooms[0]['name']='Gästezimmer'
            form=deepcopy(room['FORM'])
            form['description_placeholders']['area_name']='Gästezimmer'
            form['data_schema'].append({'name':'door_sensors','default':['binary_sensor.door_a'],
                'selector':{'select':{'multiple':True,'options':[
                    {'value':'binary_sensor.door_a','label':'Interior door A'},
                    {'value':'binary_sensor.door_b','label':'Interior door B'}]}}})
            page.evaluate(room['SETUP'],{'states':states,'form':form,'native':False})
            page.evaluate(r"""language=>{
                card._hass.language=language;card._hass.connection={};
                card._hass.devices={'living-device':{name:'Gästezimmer Environment',area_id:'room0'}};
                const data=[
                  ['switch.closed_room_eco','off','climate_operating_closed_door_eco','Eco when doors are closed and room is empty'],
                  ['number.room_delay','10','climate_operating_unoccupied_delay_minutes','Vacancy delay (min)'],
                  ['number.sleep_heat','18','climate_profile_sleep_heat','Sleep · Heating target (°C)']
                ];
                window.registry062=data.map(([entity_id,value,key,name])=>{
                    card._hass.states[entity_id]={state:value,attributes:{
                      friendly_name:'Gästezimmer Environment ° '+name,
                      configuration_help:'The setting applies only to this room. Existing safety checks remain in force.',
                      min:0,max:240,step:1,
                      setting_key:entity_id==='switch.closed_room_eco'?'area_'+key:undefined}};
                    return {entity_id,device_id:'living-device',config_entry_id:'entry0',platform:'environment_manager',
                        unique_id:'entry0_area_room0_'+key};
                });
                window.native062=[];
                card._hass.callWS=async request=>{
                    if(request.type==='config/entity_registry/list')return registry062;
                    throw Error('Unexpected request '+request.type);
                };
                card._hass.callService=async (...args)=>{native062.push(args);};
            }""",language)
            assert page.evaluate("card._openRoomSettings114('room0')")
            page.wait_for_function('card._roomSettingsDialog114?.fullRegistry127?.length===3')
            dialog=page.locator('dialog.hem-room-options114')
            group=dialog.locator('[data-hem-unified141="ventilation"]')
            expect(group.locator(':scope > summary strong')).to_have_text(HEADINGS[language])
            assert dialog.locator('[data-hem-unified141="presence"] [data-room-options-group114="door_sensors"]').count()==0
            assert dialog.locator('[data-hem-unified141="presence"] [data-hem-full-row127="switch.closed_room_eco"]').count()==0
            assert dialog.locator('[data-hem-full-row127="switch.closed_room_eco"]').count()==1
            order=group.locator('[data-hem-unified-sources141]').evaluate('node=>[...node.children].map(n=>n.getAttribute("data-room-options-group114")||(n.hasAttribute("data-hem-door-eco062")?"eco":"unexpected"))')
            assert order==['windows','door_sensors','eco','shades'],order
            assert page.evaluate('native062.length')==0
            for text in dialog.locator('.hem-full-label127 strong').all_text_contents():
                assert 'Gästezimmer' not in text and 'Environment' not in text,text
            group.locator(':scope > summary').click()
            door=group.locator('[data-room-options-group114="door_sensors"]')
            door.locator(':scope > summary').click()
            door.locator('input[type=checkbox][value="binary_sensor.door_b"]').check()
            draft=page.evaluate('structuredClone(card._roomSettingsDialog114.draft)')
            eco=group.locator('[data-hem-full-row127="switch.closed_room_eco"]')
            button=eco.locator('[data-hem-full-apply127]')
            button.focus()
            page.evaluate('card._hemFullRender127(card._roomSettingsDialog114,"room")')
            expect(button).to_be_focused()
            assert page.evaluate('card._roomSettingsDialog114.draft')==draft
            assert eco.count()==1
            button.click()
            assert page.evaluate('native062')==[['switch','turn_on',{'entity_id':'switch.closed_room_eco'}]]
            eco.locator('.hem-full-help127 > summary').click()
            page.evaluate('card.shadowRoot.activeElement?.blur();card._hemFullRender127(card._roomSettingsDialog114,"room")')
            expect(eco.locator('.hem-full-help127')).to_have_attribute('open','')
            paragraph=eco.locator('.hem-full-help-body127 p')
            assert paragraph.evaluate('n=>n.getBoundingClientRect().width')>150
            assert group.evaluate('n=>n.scrollWidth<=n.clientWidth+2')
            assert page.evaluate('card._roomSettingsDialog114.draft')==draft
            dialog.locator('[data-room-options-save114]').click()
            page.wait_for_function('card._roomSettingsDialog114?.finished===true')
            committed=page.evaluate('committed')
            assert committed==draft,(committed,draft)
            assert set(committed)=={field['name'] for field in form['data_schema']}
            assert 'closed_door_eco' not in committed
            assert not errors,errors
            page.close()
    browser.close()
print('PASS: all-menu contextual labels; exact door/Eco adjacency, drafts, writes and help at EN/EL/DE 320/390/760px')
