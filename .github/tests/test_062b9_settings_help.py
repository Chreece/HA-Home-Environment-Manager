"""On-demand help in real card menus; no device/configuration operations on read.

Home Options booleans/numbers/text/selects, native settings, Room selectors in
both HA-form and fallback renderers, and Floor registry settings are covered.
"""
from pathlib import Path
from copy import deepcopy
import ast
import json
import os
import runpy
import shutil
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'custom_components/environment_manager'
CARD=SOURCE/'frontend/air-quality-advisor-card.js'
ARTIFACTS=ROOT/'.github/test-artifacts/b9'
ARTIFACTS.mkdir(parents=True,exist_ok=True)
CHROME=os.getenv('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
assert CHROME
room=runpy.run_path(str(ROOT/'.github/tests/test_beta114_room_settings.py'))
base=runpy.run_path(str(ROOT/'.github/tests/test_beta108_setpoint_feedback_browser.py'))
tree=ast.parse((ROOT/'.github/tests/test_062b7_autosave.py').read_text())
setup=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
           and any(isinstance(t,ast.Name) and t.id=='SETUP' for t in n.targets))


def check_panel(page, dialog, button, expected=None):
    """Check actual visibility, right alignment, escaping and keyboard state."""
    assert button.get_attribute('type')=='button'
    assert button.get_attribute('aria-label')
    panel=dialog.locator('[data-setting-help-b9]').locator(
        'xpath=self::*[@id="'+button.get_attribute('aria-controls')+'"]')
    expect(panel).to_have_count(1)
    expect(button).to_have_attribute('aria-expanded','false')
    expect(panel).to_be_hidden()
    position=button.evaluate('n=>{const h=n.parentElement.getBoundingClientRect(),b=n.getBoundingClientRect();return {right:h.right-b.right,width:h.width}}')
    assert position['right'] <= 15, position
    button.focus();page.keyboard.press('Enter')
    expect(button).to_have_attribute('aria-expanded','true');expect(panel).to_be_visible()
    if expected:assert expected in panel.inner_text()
    assert panel.locator('img,script').count()==0
    assert panel.evaluate('n=>n.clientWidth>=160 && n.scrollWidth<=n.clientWidth+2')
    page.evaluate('card._renderContent(true)')
    expect(panel).to_be_visible()
    button.focus();page.keyboard.press('Escape')
    expect(panel).to_be_hidden();expect(dialog).to_be_visible()
    button.focus();page.keyboard.press('Space');expect(panel).to_be_visible()
    button.click();expect(panel).to_be_hidden()


with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=CHROME,headless=True,
                              args=['--no-sandbox','--disable-dev-shm-usage'])
    for language,width,native in [(lang,width,native) for lang,width in [('el',320),('en',390),('de',760)] for native in (False,True)]:
        page=browser.new_page(viewport={'width':width,'height':1000});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content('<style>body{margin:0;background:#151515;color:#eee;font:14px Arial;} :root{--card-background-color:#222;--primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;--secondary-background-color:#292929;--divider-color:#444}</style>')
        page.evaluate(base['icon_fixture']());page.add_script_tag(path=str(CARD))
        states=deepcopy(base['fixture_definitions']()['states'])
        states['sensor.hem']['attributes']['dashboard']['rooms']=states['sensor.hem']['attributes']['dashboard']['rooms'][:2]
        page.evaluate(room['SETUP'],{'states':states,'form':room['FORM'],'native':native})
        page.evaluate('(form)=>window.roomSchema=form',room['FORM']);page.evaluate(setup)
        catalog=json.loads((SOURCE/'translations'/f'{language}.json').read_text())
        page.evaluate(r'''({language,catalog})=>{
          card._hass.language=language;
          card._hass.localize=(key)=>{
            const prefix='component.environment_manager.';
            if(!key.startsWith(prefix))return undefined;
            return key.slice(prefix.length).split('.').reduce((v,k)=>v?.[k],catalog);
          };
          homeForm.data_schema.push({name:'use_mold_indicator',default:true,selector:{boolean:{}}});
          homeData.use_mold_indicator=true;
          homeForm.data_schema.push({name:'general_sleep_rooms_attribute',default:'rooms',selector:{text:{}}});
          homeData.general_sleep_rooms_attribute='rooms';
        }''',{'language':language,'catalog':catalog})
        assert page.evaluate('card._openHomeSettings128()')
        page.wait_for_function('card._homeSettingsDialog128?.fields?.length===6')
        dialog=page.locator('dialog.hem-home-options128')
        dialog.locator('[data-settings-advanced-b8]').check()
        page.evaluate("card._homeSettingsDialog128.node.querySelectorAll('[data-hem-unified141]').forEach(n=>n.open=true)")
        before=page.evaluate('JSON.stringify({writes,optionWrites,homeData,committed})')
        assert dialog.locator('.hem-home-helper128').count()==0
        assert dialog.locator('[data-hem-home-field128] [data-setting-info-b9]').count()==6
        for key in ('pollen_avoid_ventilation','use_mold_indicator','general_away_cooldown_minutes','general_home_policy','weather_entities','general_sleep_rooms_attribute'):
            field=dialog.locator(f'[data-hem-home-field128="{key}"]')
            button=field.locator('[data-setting-info-b9]')
            description=catalog['options']['step']['setup_general'].get('data_description',{}).get(key)
            check_panel(page,dialog,button,description)
        assert page.evaluate('JSON.stringify({writes,optionWrites,homeData,committed})')==before
        expect(dialog.locator('[data-hem-home-input128="pollen_avoid_ventilation"]')).not_to_be_checked()
        expect(dialog.locator('[data-hem-home-input128="use_mold_indicator"]')).to_be_checked()
        if language=='el' and not native:
            field=dialog.locator('[data-hem-home-field128="use_mold_indicator"]')
            field.screenshot(path=str(ARTIFACTS/'home-help-closed.png'))
            field.locator('[data-setting-info-b9]').click()
            field.screenshot(path=str(ARTIFACTS/'home-help-open.png'))
            field.locator('[data-setting-info-b9]').click()
        # An ordinary checkbox click still uses the exact existing automatic save.
        dialog.locator('[data-hem-home-input128="pollen_avoid_ventilation"]').check()
        page.wait_for_function('homeData.pollen_avoid_ventilation===true')
        assert page.evaluate('homeData.use_mold_indicator') is True
        # A validated source description remains searchable while collapsed.
        search=dialog.locator('[data-settings-search-b8]')
        help_text=catalog['options']['step']['setup_general']['data_description']['use_mold_indicator']
        search.fill(help_text.split()[0])
        expect(dialog.locator('[data-hem-home-field128="use_mold_indicator"]')).to_be_visible()
        search.fill('')
        page.evaluate("card._homeSettingsDialog128.node.querySelectorAll('[data-hem-unified141]').forEach(n=>n.open=true)")
        # Native help remains collapsed, right-aligned and read-only, even
        # when an unavailable entity has no metadata description.
        native_row=dialog.locator('[data-hem-full-row127="number.home_maximum"]')
        expect(native_row.locator('.hem-full-help-body127')).to_be_hidden()
        native_row.locator('summary').click();expect(native_row.locator('.hem-full-help-body127')).to_be_visible()
        native_row.locator('summary').click()
        # Help remains read-only during a pending native save and stale redraw.
        page.evaluate('defer=true')
        number=native_row.locator('input')
        number.fill('42');number.dispatch_event('change')
        page.wait_for_function('writes.length===1')
        native_row.locator('summary').click();page.evaluate('card._renderContent(true)')
        expect(number).to_have_value('42');assert page.evaluate('writes.length')==1
        page.evaluate('finishWrite.resolve();defer=false')
        page.evaluate("ack('number.home_maximum',42)")
        expect(number).to_have_value('42')
        page.evaluate('card._closeHomeSettings128(false)')
        assert page.evaluate("card._openRoomSettings114('room0')")
        page.wait_for_function('card._roomSettingsDialog114?.fields?.length===7')
        dialog=page.locator('dialog.hem-room-options114:not(.hem-home-options128)')
        page.evaluate("card._roomSettingsDialog114.node.querySelectorAll('[data-hem-unified141]').forEach(n=>n.open=true)")
        before=page.evaluate('JSON.stringify({writes,optionWrites,homeData,committed})')
        assert dialog.locator('.hem-room-options-helper115').count()==0
        for key in room['KEYS']:
            field=dialog.locator(f'[data-room-options-group114="{key}"]')
            check_panel(page,dialog,field.locator(':scope > summary [data-setting-info-b9]'))
            if native:
                assert field.locator('ha-form').evaluate('n=>n.computeHelper()')==''
        assert page.evaluate('JSON.stringify({writes,optionWrites,homeData,committed})')==before
        # Validation is not explanatory help: it must remain visible even
        # while the help panel is closed.
        page.evaluate("card._roomSettingsFieldError114(card._roomSettingsDialog114,'temperature','Invalid source')")
        expect(dialog.locator('[data-room-options-group114="temperature"] [role="alert"]')).to_be_visible()
        assert dialog.locator('[data-room-options-group114="temperature"] [data-setting-help-b9]').is_hidden()
        # Malicious-looking translated help is text, never HTML.
        page.evaluate(r'''()=>{
          card._hass.localize=key=>key.includes('edit_room.data_description.temperature')?'<img src=x onerror=alert(1)> Help & safety':undefined;
          card._renderRoomSettingsForm114(card._roomSettingsDialog114,card._roomSettingsDialog114.form,true);
          card._hemFullRender127(card._roomSettingsDialog114,'room');
          card._roomSettingsDialog114.node.querySelectorAll('[data-hem-unified141]').forEach(n=>n.open=true);
        }''')
        check_panel(page,dialog,dialog.locator('[data-room-options-group114="temperature"] [data-setting-info-b9]'),'<img src=x')
        # Floor name/level/icon, membership group and each Area also have help.
        page.evaluate(r'''()=>{
          card._closeRoomSettings114(false);card._floorFetch140=()=>{};
          const rooms=card._dashboard105().rooms;
          card._floorRegistry140={floors:[{floor_id:'testfloor',name:'Floor',level:0,icon:null}],
            areas:rooms.map(r=>({area_id:r.area_id,name:r.name,floor_id:'testfloor'})),membership:new Map()};
          window.floorWrites=[];card._hass.callWS=async value=>{floorWrites.push(value);return {};};
          card._floorOpen140('testfloor');
        }''')
        floor=page.locator('dialog.hem-floor-dialog140');expect(floor).to_be_visible()
        before=page.evaluate('JSON.stringify({writes,optionWrites,homeData,committed,floorWrites})')
        assert floor.locator('[data-setting-info-b9]').count()==6
        for button in floor.locator('[data-setting-info-b9]').all():
            # Floor refresh is checked separately by the b7 registry tests.
            panel_id=button.get_attribute('aria-controls')
            panel=floor.locator('[data-setting-help-b9]').locator('xpath=self::*[@id="'+panel_id+'"]')
            expect(panel).to_be_hidden();button.click();expect(panel).to_be_visible()
            assert panel.evaluate('n=>n.scrollWidth<=n.clientWidth+2')
            button.click();expect(panel).to_be_hidden()
        assert page.evaluate('JSON.stringify({writes,optionWrites,homeData,committed,floorWrites})')==before
        assert not errors,errors
        if language=='el' and not native:
            floor.screenshot(path=str(ARTIFACTS/'floor-help.png'))
        page.close()
    browser.close()
print('PASS: right-aligned on-demand help, EN/EL/DE, Home/Room/Floor; both source renderers; keyboard/escaping/search/validation; no writes on help; checkbox autosave preserved')
