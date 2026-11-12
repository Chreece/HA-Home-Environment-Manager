"""Delayed registry responses and late native ACKs must not undo UI edits."""
from pathlib import Path
import ast
import os
import runpy
import shutil
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / 'custom_components/environment_manager/frontend/air-quality-advisor-card.js'
CHROME = os.getenv('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
assert CHROME
# Reuse the exact transport fixtures from the existing production-card tests.
floor_tree = ast.parse((ROOT / '.github/tests/test_061b20_floors.py').read_text())
floor_setup = next(n.args[0].value for n in ast.walk(floor_tree)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    and n.func.attr == 'evaluate' and n.args and isinstance(n.args[0], ast.Constant)
    and isinstance(n.args[0].value, str) and 'window.floors140=' in n.args[0].value)
fixtures = runpy.run_path(str(ROOT / '.github/tests/test_beta122_card_details.py'))['fixture']()
autosave_tree = ast.parse((ROOT / '.github/tests/test_062b7_autosave.py').read_text())
autosave_setup = next(ast.literal_eval(n.value) for n in autosave_tree.body
    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SETUP'
    for t in n.targets))
room = runpy.run_path(str(ROOT / '.github/tests/test_beta114_room_settings.py'))
base = runpy.run_path(str(ROOT / '.github/tests/test_beta108_setpoint_feedback_browser.py'))

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME, headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage'])
    for language in ('en', 'el', 'de'):
        page = browser.new_page(viewport={'width': 390, 'height': 950})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.add_script_tag(path=str(CARD))
        page.evaluate(floor_setup, fixtures['states'])
        page.wait_for_function('card._floorRegistry140?.floors.length===2')
        page.evaluate('(lang)=>card._hass.language=lang', language)
        assert page.evaluate("card._floorOpen140('ground')")
        field = page.locator('[data-floor-name140]')
        # A pre-save list request completes after the write. The subsequent
        # current list is deliberately held to expose even transient rollback.
        page.evaluate("""()=>{
          const original=card._hass.callWS;let first=true;
          window.originalFloorWS=original;
          card._hass.callWS=async req=>{
            if(first&&req.type==='config/floor_registry/list'){
              first=false;const stale=structuredClone(floors140);
              return await new Promise(resolve=>window.staleFloor=()=>resolve(stale));
            }
            if(req.type==='config/floor_registry/list'&&writes.some(w=>w.name==='New name')){
              const fresh=structuredClone(floors140);
              return await new Promise(resolve=>window.freshFloor=()=>resolve(fresh));
            }
            return original(req);
          };
          card._floorFetch140(true);
        }""")
        field.fill('New name'); field.dispatch_event('change'); field.blur()
        page.wait_for_function("floors140[0].name==='New name'")
        page.evaluate('staleFloor()')
        page.wait_for_function("typeof freshFloor==='function'")
        expect(field).to_have_value('New name')
        assert page.evaluate("card._floorDialog140.floorEdits.get('name').phase") == 'confirming'
        page.evaluate('card._hass.callWS=originalFloorWS;freshFloor()')
        page.wait_for_function('card._floorDialog140.floorEdits.size===0')
        expect(field).to_have_value('New name')
        # Failure of an earlier request must not discard a newer queued edit.
        page.evaluate("""()=>{let first=true;card._hass.callWS=async req=>{
          if(first&&req.type==='config/floor_registry/update'){
            first=false;return await new Promise((resolve,reject)=>window.failFirst=()=>reject(Error('test rejection')));
          }
          return originalFloorWS(req);
        }}""")
        field.fill('First edit'); field.dispatch_event('change')
        page.wait_for_function("typeof failFirst==='function'")
        field.fill('Latest edit'); field.dispatch_event('change')
        page.evaluate('failFirst()')
        page.wait_for_function("floors140[0].name==='Latest edit'&&card._floorDialog140.floorEdits.size===0")
        expect(field).to_have_value('Latest edit')
        # An invalid newer draft must not be overwritten or acknowledged by
        # the older request completing while the user is still editing.
        page.evaluate("""()=>{let first=true;card._hass.callWS=async req=>{
          if(first&&req.type==='config/floor_registry/update'){
            first=false;await new Promise(resolve=>window.finishOld=resolve);
          }
          return originalFloorWS(req);
        }}""")
        field.fill('Accepted earlier'); field.dispatch_event('change')
        page.wait_for_function("typeof finishOld==='function'")
        field.fill(''); field.dispatch_event('change'); field.blur()
        page.evaluate('finishOld()')
        page.wait_for_function("floors140[0].name==='Accepted earlier'")
        expect(field).to_have_value('')
        assert page.evaluate("card._floorDialog140.floorEdits.get('name').invalid") is True
        field.fill('Final name'); field.dispatch_event('change')
        page.wait_for_function('card._floorDialog140.floorEdits.size===0')
        expect(field).to_have_value('Final name')
        assert not errors, errors
        page.close()

    page = browser.new_page(viewport={'width': 390, 'height': 950})
    page.clock.install()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.evaluate(base['icon_fixture']())
    page.add_script_tag(path=str(CARD))
    page.evaluate(room['SETUP'], {'states': base['fixture_definitions']()['states'],
        'form': room['FORM'], 'native': False})
    page.evaluate('(form)=>window.roomSchema=form', room['FORM'])
    page.evaluate(autosave_setup)
    assert page.evaluate("card._openRoomSettings114('room0')")
    page.wait_for_function('card._roomSettingsDialog114?.fullRegistry127?.length===6')
    page.evaluate("card._roomSettingsDialog114.node.querySelectorAll('details').forEach(e=>e.open=true)")
    value = page.locator('[data-hem-full-value127="number.maximum"]')
    value.fill('25'); value.dispatch_event('change')
    page.wait_for_function("card._roomSettingsDialog114.nativeEdits.get('number.maximum').phase==='confirming'")
    page.clock.fast_forward(16000)
    page.wait_for_function("card._roomSettingsDialog114.nativeEdits.get('number.maximum').phase==='unconfirmed'")
    expect(value).to_have_value('25')
    assert page.evaluate('writes.length') == 1, 'A timeout must not retry automatically'
    page.evaluate("ack('number.maximum',25)")
    page.wait_for_function("card._roomSettingsDialog114.nativeEdits.get('number.maximum').phase==='saved'")
    assert page.evaluate('writes.length') == 1, 'Late ACK must not issue a second command'
    assert not errors, errors
    browser.close()
print('PASS: stale floor snapshots, rapid failed writes, invalid newer drafts and late native confirmation')
