"""B22: render actual HEM Setting Info UI with explanatory option text.

Real production Lovelace card, mocked HA transport. No services or physical
appliances are contacted. Covers EN/EL/DE, small mobile width, XSS escaping,
numeric bounds, dynamic select fallback and readable paragraphs.
"""
from __future__ import annotations

from pathlib import Path
import os
import runpy
import shutil

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "custom_components/environment_manager"
CARD = SRC / "frontend/air-quality-advisor-card.js"
option_help = runpy.run_path(str(SRC / "setting_option_explanations.py"))["option_help_locales"]
door_words = runpy.run_path(str(SRC / "equipment_door_policy.py"))["WORDS"]
browser_path = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert browser_path, "Chromium missing"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=browser_path, headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"])
    for locale, width in (("el", 320), ("en", 390), ("de", 760)):
        page = browser.new_page(viewport={"width": width, "height": 880})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(
            '<style>body{margin:0;background:#202020;color:#eee;font:14px Arial;'
            '--primary-text-color:#eee;--secondary-text-color:#bbb;'
            '--card-background-color:#252525;--secondary-background-color:#292929;'
            '--primary-color:#03a9f4;--divider-color:#444;}</style>'
        )
        page.add_script_tag(path=str(CARD))
        payload = {
            "language": locale,
            "texts": door_words,
            "options": option_help("equipment_door_start_coordination"),
            "watchdog": option_help("equipment_off_state_watchdog_mode"),
        }
        page.evaluate(r"""payload => {
          const card = document.createElement('home-environment-manager-card');
          document.body.appendChild(card);
          window.card = card;
          window.calls = [];
          card._hass = {language:payload.language,states:{},entities:{},user:{is_admin:true},
            localize:()=>undefined,callService:(...args)=>{calls.push(args);}};
          const door=payload.texts[payload.language];
          const labels=Object.fromEntries(Object.entries(payload.texts).map(([lang,values])=>
            [lang,Object.fromEntries(['inherit','observe','conflicts','shared'].map(v=>[v,values[v]]))]));
          const field={
            id:'select.test_door_coordination',domain:'select',
            reg:{translation_key:'equipment_door_start_coordination'},disabled:false,
            label:door.door_start_coordination,
            state:{state:'inherit',attributes:{
              options:['inherit','observe','conflicts','shared'],
              configuration_help:payload.texts.en.coord_help,
              configuration_help_locales:Object.fromEntries(Object.entries(payload.texts)
                .map(([lang,v])=>[lang,v.coord_help])),
              option_labels_locales:labels,
              option_help_locales:payload.options,
            }},
          };
          window.doorField=field;
          const numberField={
            id:'number.temp_limit',domain:'number',reg:{},disabled:false,
            label:'Temperature',
            state:{state:'20',attributes:{min:10,max:30,step:0.5,unit_of_measurement:'°C',
              configuration_help_locales:{
                en:'What: sets the temperature limit.\n\nHow: checked before applying a target.',
                el:'Τι κάνει: ορίζει όριο θερμοκρασίας.\n\nΠώς: ελέγχεται πριν εφαρμοστεί στόχος.',
                de:'Wirkung: Temperaturgrenze.\n\nAnwendung: vor dem Sollwert geprüft.'},
              configuration_help:'What: sets the temperature limit.'}},
          };
          const dynamicField={
            id:'select.vendor_fan_mode',domain:'select',reg:{},disabled:false,
            label:'Native mode',state:{state:'eco',attributes:{options:['eco','turbo'],
              configuration_help:'Use the native fan mode supported by the device.'}},
          };
          card.shadowRoot.innerHTML=card._styles()+'<div style="padding:8px" id="info-fixture22">'+
            card._hemFullRow127(field,'device')+
            card._hemFullRow127(numberField,'device')+
            card._hemFullRow127(dynamicField,'device')+'</div>';
        }""", payload)
        row = page.locator('[data-hem-full-row127="select.test_door_coordination"]')
        expect(row.locator('.hem-full-help-body127')).to_be_hidden()
        row.locator('summary').click()
        expect(row.locator('.hem-full-help-body127')).to_be_visible()
        panel = row.locator('.hem-full-help-body127')
        assert panel.locator(':scope > p').count() == 3
        assert panel.locator('[data-hem-option127]').count() == 4
        assert panel.locator('[data-hem-option127="inherit"] small').count() == 1
        assert door_words[locale]['inherit'] in panel.inner_text()
        assert option_help('equipment_door_start_coordination')[locale]['shared'] in panel.inner_text()
        assert panel.locator('script,img,iframe').count() == 0
        assert row.locator('[data-hem-full-value127]').input_value() == 'inherit'
        number = page.locator('[data-hem-full-row127="number.temp_limit"]')
        number.locator('summary').click()
        assert number.locator('.hem-full-help-body127 > p').count() == 3
        assert '10' in number.locator('.hem-full-range127').inner_text()
        assert '30' in number.locator('.hem-full-range127').inner_text()
        native = page.locator('[data-hem-full-row127="select.vendor_fan_mode"]')
        native.locator('summary').click()
        assert native.locator('[data-hem-option-help127]').count() == 0
        assert 'native fan mode' in native.locator('.hem-full-help-body127').inner_text()
        assert page.evaluate('calls.length') == 0
        # A known English source uses its reviewed bundled translation even
        # when incoming localized metadata has been replaced.
        page.evaluate(r"""() => {
          doorField.state.attributes.option_help_locales.el.conflicts=
            '<img src=x onerror=alert(1)> A setting example';
          card._hass.language='el';
          const node=card.shadowRoot.querySelector('[data-hem-full-row127="select.test_door_coordination"]');
          node.outerHTML=card._hemFullRow127(doorField,'device');
        }""")
        panel = page.locator('[data-hem-full-row127="select.test_door_coordination"]')
        panel.locator('summary').click()
        assert option_help('equipment_door_start_coordination')['el']['conflicts'] in panel.inner_text()
        assert '<img src=x onerror=alert(1)>' not in panel.inner_text()
        assert panel.locator('script,img,iframe').count() == 0
        assert page.evaluate('calls.length') == 0
        # An unknown vendor source takes the localized metadata fallback.
        # Its malicious-looking explanation must remain literal text.
        page.evaluate(r"""() => {
          doorField.state.attributes.option_help_locales.en.conflicts=
            'Vendor-specific explanation for the escaping regression fixture.';
          const node=card.shadowRoot.querySelector('[data-hem-full-row127="select.test_door_coordination"]');
          node.outerHTML=card._hemFullRow127(doorField,'device');
        }""")
        panel.locator('summary').click()
        assert '<img src=x onerror=alert(1)>' in panel.inner_text()
        assert panel.locator('script,img,iframe').count() == 0
        assert page.evaluate('calls.length') == 0
        assert not errors, errors
        page.close()
    browser.close()
print("PASS: native option-by-option info, current choice, numeric bounds, EN/EL/DE, mobile, escaping and zero services")
