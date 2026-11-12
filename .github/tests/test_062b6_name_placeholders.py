"""Actual card localization calls must supply required name placeholders."""
from pathlib import Path
import json
import os
import shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'custom_components/environment_manager'
CHROME=os.getenv('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
assert CHROME
keys=('equipment_sleep_when_everyone_asleep','equipment_native_full_output',
      'equipment_pause_on_window_open','equipment_announce_device_errors')
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=CHROME,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page();page.add_script_tag(path=str(SRC/'frontend/air-quality-advisor-card.js'))
    for language in ('en','el','de'):
        catalog=json.loads((SRC/'translations'/f'{language}.json').read_text())
        names={key:catalog['entity']['switch'][key]['name'] for key in keys}
        result=page.evaluate(r'''({language,names})=>{
            const card=document.createElement('home-environment-manager-card');
            document.body.appendChild(card);
            const failures=[],calls=[],labels=[];
            card._hass={language,states:{},entities:{},localize:(key,variables)=>{
                calls.push({key,variables});
                const name=names[key.split('.').at(-2)];
                if(!name)return key;
                if(!variables||typeof variables.channel!=='string'){
                    failures.push(key);return '';
                }
                return name.replaceAll('{channel}',variables.channel);
            }};
            for(const key of Object.keys(names)){
                const id='switch.test';
                for(let index=0;index<15;index++){
                    const plain=card._hemSettingLabel062(id,{attributes:{}},{translation_key:key});
                    const channel=card._hemSettingLabel062(id,{attributes:{}},{translation_key:key,
                        translation_placeholders:{channel:'Outlet B · '}});
                    const missing=card._hemSettingLabel062(id,null,{translation_key:key});
                    labels.push({plain,channel,missing});
                }
            }
            card.remove();return {failures,calls: calls.length,labels};
        }''',{'language':language,'names':names})
        assert not result['failures'],result
        assert result['calls']==180,result['calls']
        for labels in result['labels']:
            assert labels['plain'] and '{channel}' not in labels['plain'],labels
            assert labels['missing']==labels['plain'],labels
            assert 'Outlet B' in labels['channel'],labels
    browser.close()
print('PASS: 540 actual card name translations; EN/EL/DE, empty and real channels, unavailable rows, repeated renders')
