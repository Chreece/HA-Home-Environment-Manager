from pathlib import Path
import re
T=Path.cwd()/'.github/tests'
for p in T.glob('*.py'):
 if p.name=='test_062b7_autosave.py':continue
 s=p.read_text()
 # The control itself now commits the change, not a separate button.
 s='\n'.join(line.replace('data-hem-full-apply127','data-hem-full-value127').replace('.click()',".dispatch_event('change')")
   if '.click()' in line and any('data-hem-full-apply127="'+domain+'.' in line for domain in ('number','select','time'))
   else line for line in s.split('\n'))
 if p.name=='test_beta116_configuration_help.py':
  s=s.replace('data-hem-full-apply127="number.cooler_gain"','data-hem-full-value127="number.cooler_gain"')
 if p.name in ('test_062b3_door_ui.py','test_062b2_settings_menus.py'):
  for obj in ('target','coordination','meter'):
   s=s.replace(f"{obj}.locator('[data-hem-full-apply127]').click()",f"{obj}.locator('select').dispatch_event('change')")
  s=s.replace("timeout.locator('[data-hem-full-apply127]').click()","timeout.locator('input').dispatch_event('change')")
  s=s.replace("            dialog.locator('[data-room-options-save114]').click()\n            page.wait_for_function('card._roomSettingsDialog114?.finished===true')",
              "            page.wait_for_function('card._roomSettingsDialog114?.optionsAutosave?.dirty.size===0')\n            assert card_menu_open(page)")
  s=s.replace('HEADINGS =', 'HEADINGS =') # no generated import side effects
  # A tiny local assertion helper makes successful autosave's retained dialog explicit.
  s=s.replace('with sync_playwright() as pw:',"def card_menu_open(page):\n    return page.evaluate('card._roomSettingsDialog114.finished===false')\n\nwith sync_playwright() as pw:")
  # Some files name the Playwright context differently.
  if 'def card_menu_open' not in s:
   s=s.replace('with sync_playwright() as playwright:',"def card_menu_open(page):\n    return page.evaluate('card._roomSettingsDialog114.finished===false')\n\nwith sync_playwright() as playwright:")
 p.write_text(s)
# Mock Options flows now expose the latest persisted defaults, like the real backend.
p=T/'test_beta114_room_settings.py';s=p.read_text()
s=s.replace('''    const step={...structuredClone(form),flow_id};''','''    const step={...structuredClone(form),flow_id};
    for(const field of step.data_schema)field.default=structuredClone(committed[field.name]);''')
start=s.index('  const calls=[];\n  const saved=',s.index('def logic_checks'))
end=s.index("  console.log('BETA114",start)
s=s[:start]+'''  const calls=[];
  const saved={flowId:'options1',api:async(method,path)=>{calls.push({method,path});}};
  await helper.cleanup(saved);await helper.cleanup(saved);
  assert.deepEqual(calls,[{method:'DELETE',path:'config/config_entries/options/flow/options1'}]);
  const completed={flowId:'done',finished:true,api:saved.api};
  await helper.cleanup(completed);assert.equal(calls.length,1);
  const delayed={api:saved.api};await helper.cleanup(delayed);
  delayed.flowId='late';await helper.cleanup(delayed);
  assert.equal(calls.at(-1).path,'config/config_entries/options/flow/late');
'''+s[end:]
start=s.index('        detect.click()\n',s.index('def browser_checks'))
end=s.index('        # A canceled create response',start)
s=s[:start]+'''        detect.click()
        page.wait_for_function('committed.shades.length===2')
        assert page.evaluate('committed.shades') == COVERS
        assert popup.locator('[data-room-options-save114]').is_hidden()
        assert page.evaluate('card._roomSettingsDialog114.finished') is False
        for width in (320,390,700):
            page.set_viewport_size({'width':width,'height':850})
            assert shades.evaluate('n=>n.scrollWidth<=n.clientWidth+1')
        shades.locator('[data-room-clear114]').click()
        page.wait_for_function('committed.shades.length===0')
        assert page.evaluate('committed.temperature') == DEFAULTS['temperature']
        popup.locator('[data-room-options-close114]').click()
        assert popup.count()==0
        assert page.evaluate("card._openRoomSettings114('room0')")
        assert page.evaluate('card._roomSettingsDialog114.draft.shades') == []
        reveal_source(shades);shades.locator('summary').click()
        shades.locator(f'input[value="{COVERS[1]}"]').check()
        detect.click()
        cover_selection=[COVERS[1],COVERS[0]]
        page.wait_for_function('committed.shades.length===2')
        temp=popup.locator('[data-room-options-group114="temperature"]')
        reveal_source(temp);temp.locator('summary').click()
        page.evaluate('mode.validation=true;window.beforeCommitted=structuredClone(committed)')
        temp.locator('input[value="sensor.temp_a"]').uncheck()
        page.wait_for_function('card._roomSettingsDialog114.optionsAutosave.blocked===true')
        assert temp.locator('[data-room-options-field-error114]').is_visible()
        assert not temp.locator('input[value="sensor.temp_a"]').is_checked()
        assert page.evaluate('JSON.stringify(committed)===JSON.stringify(beforeCommitted)')
        page.evaluate('mode.validation=false')
        popup.locator('[data-room-options-status114] button').click()
        page.wait_for_function("!committed.temperature.includes('sensor.temp_a')")
        temp.locator('input[value="sensor.temp_c"]').check()
        page.wait_for_function("committed.temperature.includes('sensor.temp_c')")
        temp.locator('input[type="search"]').fill('TEMP C')
        assert temp.locator('[data-room-options-choice114]:visible').count()==1
        humidity=popup.locator('[data-room-options-group114="humidity"]')
        reveal_source(humidity);humidity.locator('summary').click()
        humidity.locator('[data-room-clear114]').click()
        page.wait_for_function('committed.humidity.length===0')
        page.evaluate('window.before=card._roomSettingsDialog114.node;card._renderContent(true)')
        assert page.evaluate('before===card._roomSettingsDialog114.node')
        expected=deepcopy(DEFAULTS)
        expected.update(temperature=['sensor.temp_b','sensor.temp_c'],humidity=[],shades=cover_selection)
        assert page.evaluate('committed')==expected
        assert popup.locator('[data-room-detect-shades115]').count()==1
        popup.locator('[data-room-options-close114]').focus();page.keyboard.press('Tab')
        assert popup.locator('[data-room-options-x114]').evaluate('n=>n===n.getRootNode().activeElement')
        popup.locator('[data-room-options-close114]').click()
        assert popup.count()==0

'''+s[end:]
start=s.index('        # A network failure after Save')
end=s.index('        # A different card source',start)
s=s[:start]+'''        # A failed automatic save retains editors and does not retry on its own.
        page.evaluate("calls=[];mode={};card._openRoomSettings114('room0')")
        page.evaluate('mode.failSave=true')
        page.evaluate("card._roomSettingsSelection114(card._roomSettingsDialog114,'temperature',[])")
        page.wait_for_function('card._roomSettingsDialog114.optionsAutosave.blocked===true')
        assert popup.locator('[data-room-options-status114]').get_attribute('role')=='alert'
        assert popup.locator('[data-room-options-save114]').is_hidden()
        count=page.evaluate("calls.filter(c=>c.data?.temperature).length")
        page.wait_for_timeout(200)
        assert page.evaluate("calls.filter(c=>c.data?.temperature).length")==count
        page.evaluate('mode={}')
        popup.locator('[data-room-options-status114] button').click()
        page.wait_for_function('committed.temperature.length===0')

'''+s[end:]
s=s.replace('''        assert native.evaluate("calls.length") == 2 and native.evaluate("committed") == DEFAULTS''','''        native.wait_for_function('card._roomSettingsDialog114.optionsAutosave?.dirty.size===0')
        assert native.evaluate('committed') == native.evaluate('card._roomSettingsDialog114.draft')''')
s=s.replace('''        popup.locator('[data-room-options-save114]').click()
        native.wait_for_function("card._roomSettingsDialog114.finished===true")''','''        native.wait_for_function('card._roomSettingsDialog114.optionsAutosave?.dirty.size===0')
        assert native.evaluate('card._roomSettingsDialog114.finished') is False''')
s=s.replace('assert native.evaluate("calls.at(-1).data") == expected','assert native.evaluate("calls.filter(c=>c.data?.temperature).at(-1).data") == expected')
s=s.replace('assert popup.locator(\'[data-room-detect-shades115]\').count() == 0','assert popup.locator(\'[data-room-detect-shades115]\').count() == 1')
s=s.replace('''        native.evaluate("card._openRoomSettings114('room1')")
        native.evaluate("card.remove()")
        native.wait_for_function("calls.some(c=>c.method==='DELETE'&&c.path.endsWith('options2'))")''','''        native.evaluate("card._openRoomSettings114('room1')")
        native.evaluate("window.lastFlow=card._roomSettingsDialog114.flowId;card.remove()")
        native.wait_for_function("calls.some(c=>c.method==='DELETE'&&c.path.endsWith(lastFlow))")''')
s=s.replace('BETA115_DETECTED_COVERS_DRAFT_ONLY_FALLBACK_NATIVE_AND_EXPLICIT_SAVE=PASS','B7_DETECTED_COVERS_AUTOSAVE_FALLBACK_NATIVE_AND_VALIDATION=PASS')
p.write_text(s)
# Home test now exercises successive automatic transactions; its fake backend
# persists form defaults so a later field update cannot revert an earlier one.
p=T/'test_061b14_unified_home_settings.py';s=p.read_text()
s=s.replace('''          if(method==="POST" && data?.weather_entities)return {
            type:"create_entry",flow_id:"optionsHOME"
          };''','''          if(method==="POST" && data?.weather_entities){
            for(const field of homeForm.data_schema)field.default=structuredClone(data[field.name]);
            return {type:"create_entry",flow_id:"optionsHOME"};
          }''')
s=s.replace('''    expect(dialog.locator('[data-hem-home-save128]')).to_be_enabled()
    dialog.locator('[data-hem-home-save128]').click()
    page.wait_for_function("card._homeSettingsDialog128?.finished===true")''','''    expect(dialog.locator('[data-hem-home-save128]')).to_be_hidden()
    page.wait_for_function('card._homeSettingsDialog128.optionsAutosave?.dirty.size===0')
    assert page.evaluate('card._homeSettingsDialog128.finished') is False''')
s=s.replace('assert page.evaluate("homeCalls.filter(c=>c.method===\'DELETE\').length") == 0','assert page.evaluate("homeCalls.filter(c=>c.method===\'DELETE\').length") == 1')
p.write_text(s)
# Floor autosave deliberately leaves the same dialog open.
p=T/'test_061b20_floors.py';s=p.read_text()
s=s.replace('''    dialog.locator('[data-floor-save140]').click()
    expect(dialog).to_have_count(0)''','''    expect(dialog.locator('[data-floor-save140]')).to_be_hidden()
    page.wait_for_function('card._floorDialog140.floorEdits?.size===0')
    expect(dialog).to_be_visible()''')
s=s.replace('''    assert page.evaluate("writes.map(w=>w.type)") == [
        "config/floor_registry/update",
        "config/area_registry/update",
        "config/area_registry/update",
    ]''','''    assert page.evaluate("writes.filter(w=>w.type==='config/floor_registry/update').length") == 3
    assert page.evaluate("writes.filter(w=>w.type==='config/area_registry/update').length") == 2
    assert page.evaluate("writes.some(w=>w.name==='Living level')")
    assert page.evaluate("writes.some(w=>w.level===-1)")
    assert page.evaluate("writes.some(w=>w.icon==='mdi:home-floor-b')")
    dialog.locator('[data-floor-close140]').last.click()''')
p.write_text(s)
