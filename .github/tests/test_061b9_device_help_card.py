"""Device-specific help, exact mode titles, and complete timing retirement.

Node runs the shipped card against production localized metadata. Chromium
checks real touch/keyboard actions and EN/EL/DE geometry at 320 and 390 pixels.
The service recorder is a fixture; no physical device is contacted.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
BASE = runpy.run_path(str(ROOT / ".github/tests/test_061b8_quick_options_card.py"))
CATALOG = runpy.run_path(str(ROOT / "equipment_name_catalog.py"))
NAME = CATALOG["native_full_output_label"]
HELP = BASE["HELP"]
LANGUAGES = ("en", "el", "de")
KEYS = ("announce_device_errors", "native_full_output", "sleep_when_everyone_asleep")
LABELS = {
    "en": ("Announce device errors", "Keep device off when all asleep"),
    "el": ("Ανακοίνωση σφαλμάτων συσκευής", "Διατήρηση συσκευής κλειστής όταν όλοι κοιμούνται"),
    "de": ("Gerätefehler melden", "Gerät ausgeschaltet lassen, wenn alle schlafen"),
}


def fixture(language="en"):
    states = BASE["fixture"](language)
    # A heating/cooling device and a humidity-only dehumidifier must expose
    # different maximum-target mode lists, even though they share a room.
    source, controller = "climate.physical_0_1", "climate.managed_0_1"
    states[source] = {"state": "dry", "attributes": {
        "friendly_name": "Comfee", "hvac_modes": ["off", "dry"],
        "supported_features": 12, "hvac_action": "drying", "humidity": 50,
        "current_humidity": 52, "min_humidity": 30, "max_humidity": 90,
        "fan_modes": ["low", "medium", "high"], "fan_mode": "low"}}
    states[controller]["state"] = "dry"
    states[controller]["attributes"].update(friendly_name="HEM Comfee", hvac_modes=["off", "dry"],
        physical_source_state="dry", requested_hvac_mode="dry", humidity=55,
        measurements={"humidity": 52}, controller_status={"status": "controlling"})
    states["sensor.control_0_1"]["attributes"].update(
        status_code="controlling", physical_entity_states={source: "dry"})
    states["switch.native_full_output_1"]["attributes"].update(
        native_full_output_modes=["dry"], setting_label=NAME(["dry"], language),
        configuration_help=HELP("native_full_output", language, modes=["dry"]))
    # Exact metadata provenance is tested with user-renamed entities; no
    # controller name can be used to synthesize the destination switch ID.
    for key in KEYS:
        entity = {"announce_device_errors": "switch.errors_0",
                  "native_full_output": "switch.native_full_output_0",
                  "sleep_when_everyone_asleep": "switch.sleep_when_everyone_asleep_0"}[key]
        states["switch.renamed_" + key] = states.pop(entity)
    # All three historical metadata shapes must be ignored after an upgrade,
    # including a generic flag and a stale scoped field with an old help body.
    source_attrs = states["switch.renamed_native_full_output"]["attributes"]
    for suffix, extra in (
        ("role", {"timed_setpoint_role": "policy"}),
        ("flag", {"equipment_option_role": "policy", "setting_key": "timed_setpoint_sequence"}),
        ("scoped", {"settings_scope": "operating_mode", "operating_mode": "heat",
                    "operating_mode_label": "Heating", "setting_key": "timed_setpoint_sequence"}),
    ):
        provenance = {name: source_attrs[name]
                      for name in ("area_id", "source_device_id", "source_entity_ids")}
        states["switch.retired_timing_" + suffix] = {"state": "on", "attributes": {
            **provenance, **extra, "timed_setpoint_supported": True,
            "setting_label": "RETIRED TIMING OPTION", "configuration_help": "RETIRED 30 SECOND HELP"}}
    return states


NODE_CHECKS = r"""
const tests=[];function test(name,run){tests.push({name,run});}
const plain=value=>JSON.parse(JSON.stringify(value));
function setup(language='en'){
  const {card}=make();card._hass={...card._hass,language,states:clone(supplied.fixtures[language])};
  card._render=()=>{};return card;
}
function entry(card,index=0){return card._managedControllers('room0')[index];}
function options(card,index=0){return card._deviceQuickOptions8(entry(card,index));}
function refresh(card,states){card._hass={...card._hass,states:clone(states)};}
function control(card,key,id='switch.renamed_'+key){return button({
  'data-controller-area':'room0','data-managed-controller':'climate.managed_0_0',
  'data-device-quick-key8':key,'data-device-quick-switch8':id,
  ...(key==='announce_device_errors'?{'data-device-error-announce':id}:{})});}
const escaped=value=>value.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')
  .replaceAll('"','&quot;').replaceAll("'",'&#39;');
test('exact translated device titles and paragraph help are preserved',()=>{
  for(const language of ['en','el','de']){
    const card=setup(language),html=card._deviceQuickRow8(entry(card),'room0');
    for(const key of supplied.keys){
      const option=options(card).find(option=>option.key===key),attrs=option.state.attributes;
      assert.equal(option.label,attrs.setting_label);
      assert.ok(html.includes('<strong class="hem-help-heading9">'+escaped(attrs.setting_label)+'</strong>'));
      const paragraphs=attrs.configuration_help.split(/\n[ \t]*\n+/);
      assert.ok(paragraphs.length>=3,key+' lacks informative paragraphs');
      for(const paragraph of paragraphs)
        assert.ok(html.includes('<p class="hem-help-text116">'+escaped(paragraph.trim())+'</p>'),key);
      assert.ok(!option.help.includes('30 s') && !option.help.includes('30 seconds'));
    }
    assert.equal(options(card).find(option=>option.key==='announce_device_errors').label,supplied.labels[language][0]);
    assert.equal(options(card).find(option=>option.key==='sleep_when_everyone_asleep').label,supplied.labels[language][1]);
    assert.equal(options(card,1).find(option=>option.key==='native_full_output').label,supplied.dryNames[language]);
  }
});
test('all 38 translated maximum titles use only the supplied canonical modes',()=>{
  for(const sample of supplied.modeSamples){
    const card=setup(),states=clone(card._hass.states),attrs=states['switch.renamed_native_full_output'].attributes;
    Object.assign(attrs,{setting_label:sample.label,native_full_output_modes:sample.modes,
      configuration_help:sample.help});refresh(card,states);
    const option=options(card).find(option=>option.key==='native_full_output');
    assert.equal(option.label,sample.label,sample.language);
    assert.equal(option.help,sample.help,sample.language);
    const html=card._deviceQuickRow8(entry(card),'room0');
    assert.ok(html.includes('aria-label="'+escaped(sample.label)+'"'),sample.language);
  }
});
test('blank lines become paragraphs; literal markup and newline bullets remain text',()=>{
  const card=setup();
  assert.equal(card._configurationHelpText9('  Purpose.\r\n\r\nON: <img src=x>\r\n- One\r\n- Two\r\n\r\nOFF: Leave & retain.  '),
    '<p class="hem-help-text116">Purpose.</p><p class="hem-help-text116">ON: &lt;img src=x&gt;\n- One\n- Two</p><p class="hem-help-text116">OFF: Leave &amp; retain.</p>');
  assert.equal(card._configurationHelpText9({bad:'shape'}),'');
});
test('retired controls cannot enter inventory, scoped panels, signatures or either click path',async()=>{
  const card=setup(),before=card._controllerSignature(),room=card._hass.states['sensor.hem'].attributes.dashboard.rooms[0];
  const html=card._controllerPanel(room);
  assert.ok(!html.includes('RETIRED') && !html.includes('data-timed-setpoint-switch'));
  assert.ok(!entry(card).deviceFlags.some(field=>field.key==='timed_setpoint_sequence'));
  assert.ok(!entry(card).operatingModes.some(mode=>mode.parameters.some(field=>field.key==='timed_setpoint_sequence')));
  for(const suffix of ['role','flag','scoped']){
    const id='switch.retired_timing_'+suffix,attrs=card._hass.states[id].attributes;
    card._hass.states[id].state='off';attrs.configuration_help='CHANGED RETIRED';
    assert.equal(card._controllerSignature(),before);
    click(card,{'data-controller-area':'room0','data-managed-controller':'climate.managed_0_0',
      'data-timed-setpoint-switch':id});
    await card._submitDeviceQuick8(control(card,'timed_setpoint_sequence',id));
  }
  assert.equal(card.calls.length,0);
});
test('maximum policy cannot render or act with missing, invalid or withdrawn mode evidence',async()=>{
  const card=setup(),saved=control(card,'native_full_output'),original=clone(card._hass.states);
  for(const modes of [null,[],['auto'],['heat','fan_only'],'heat']){
    const states=clone(original);states['switch.renamed_native_full_output'].attributes.native_full_output_modes=modes;
    refresh(card,states);assert.ok(!options(card).some(option=>option.key==='native_full_output'));
    await card._submitDeviceQuick8(saved);
  }
  refresh(card,original);const before=card._controllerSignature();
  const updated=clone(original);updated['switch.renamed_native_full_output'].attributes.native_full_output_modes=['cool'];
  refresh(card,updated);assert.notEqual(card._controllerSignature(),before);
  updated['switch.renamed_native_full_output'].attributes.source_device_id='different-device';
  refresh(card,updated);await card._submitDeviceQuick8(saved);
  assert.equal(card.calls.length,0);
});
test('renamed configuration switches route exactly and announcement OFF never hides faults',async()=>{
  const card=setup();
  for(const key of supplied.keys){
    const option=options(card).find(option=>option.key===key);
    await card._submitDeviceQuick8(control(card,key));
    assert.deepEqual(plain(card.calls.at(-1)),['switch',option.state.state==='on'?'turn_off':'turn_on',
      {entity_id:'switch.renamed_'+key}]);
  }
  const states=clone(card._hass.states),error=states['switch.renamed_announce_device_errors'];
  error.state='off';error.attributes.native_error={status:'error',code:'E7',description:'Device fault remains visible'};
  refresh(card,states);const room=states['sensor.hem'].attributes.dashboard.rooms[0];
  assert.ok(card._controllerPanel(room).includes('Device fault remains visible'));
  assert.equal(card.calls.length,3);
});
(async()=>{let failed=0;for(const {name,run} of tests){try{await run();console.log('PASS: '+name);}
  catch(error){failed++;console.error('FAIL: '+name+'\n'+error.stack);}}
  if(failed)process.exitCode=1;else console.log('HEM_061B9_DEVICE_HELP_LOGIC=PASS ('+tests.length+' cases)');})();
"""


def logic_checks():
    samples = [{"language": language, "modes": modes, "label": NAME(modes, language),
                "help": HELP("native_full_output", language, modes=modes)}
               for language in CATALOG["EQUIPMENT_TRANSLATED_NAMES"]
               for modes in (["heat", "cool"], ["dry"], ["humidify"])]
    supplied = {"states": fixture(), "entities": {}, "keys": KEYS, "labels": LABELS,
                "fixtures": {language: fixture(language) for language in LANGUAGES},
                "dryNames": {language: NAME(["dry"], language) for language in LANGUAGES},
                "modeSamples": samples}
    script = BASE["BASE"]["NODE_BASE"].replace("JSON.parse(process.argv[2])", "JSON.parse(fs.readFileSync(0,'utf8'))")
    result = subprocess.run(["node", "-e", script + NODE_CHECKS, str(CARD)],
                            input=json.dumps(supplied), text=True)
    if result.returncode:
        raise SystemExit(result.returncode)


def browser_checks():
    from playwright.sync_api import expect, sync_playwright
    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome, "Chromium is required for mobile help interaction checks"
    shots = Path(os.environ["HEM_TEST_SCREENSHOT_DIR"]) if os.environ.get("HEM_TEST_SCREENSHOT_DIR") else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 320, "height": 1000}, has_touch=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.set_content('<style>*{box-sizing:border-box}body{margin:0;background:#111;color:#eee;font:14px Arial}'
                ':root{--primary-text-color:#eee;--secondary-text-color:#bbb;--primary-color:#03a9f4;'
                '--card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}</style>')
            page.evaluate(BASE["BASE"]["BASE"]["BASE"]["PREVIOUS"]["icon_fixture"]())
            page.add_script_tag(path=str(CARD))
            page.evaluate("""({states,now})=>{
              Date.now=()=>now*1000;
              window.calls=[];window.card=document.createElement('home-environment-manager-card');
              document.body.append(card);card._config={entity:'sensor.hem'};
              card._hass={language:'en',states,localize:()=>undefined,
                callService:(...args)=>{calls.push(args);return Promise.resolve();}};
              card._roomsExpanded87=new Set(['room0']);
              card._devicesExpanded87=new Set([0,1,2].map(i=>'climate.managed_0_'+i));
              window.refresh9=(states,language='en')=>{
                card._hass={...card._hass,states:structuredClone(states),language};card._renderContent(true);
              };refresh9(states);
            }""", {"states": fixture(), "now": BASE["NOW"]})

            def device(index=0):
                return page.locator(f'[data-device-fold87="climate.managed_0_{index}"]')

            def option(key, index=0):
                return device(index).locator(f'[data-quick-option8="{key}"]')

            def icon(key, index=0):
                return option(key, index).locator(':scope > details > summary')

            def close_help():
                page.keyboard.press('Escape')
                expect(page.locator('.hem-floating-info87')).to_have_count(0)

            for language in LANGUAGES:
                states = fixture(language)
                page.evaluate('([s,l])=>refresh9(s,l)', [states, language])
                expect(device().locator('.hem-operating-mode7')).to_have_count(2)
                assert page.locator('[data-timed-setpoint-switch],[data-mode-setting-key="timed_setpoint_sequence"]').count() == 0
                assert 'RETIRED' not in page.locator('home-environment-manager-card').inner_text()
                for width in (320, 390):
                    page.set_viewport_size({"width": width, "height": 1000})
                    for index, count in ((0, 5), (1, 7), (2, 4)):
                        row = device(index).locator('.hem-device-quick-row8')
                        expect(row.locator('.hem-device-quick-option8')).to_have_count(count)
                        geometry = row.evaluate("""e=>{const r=e.getBoundingClientRect();return {
                          left:r.left,right:r.right,client:e.clientWidth,scroll:e.scrollWidth,
                          chips:[...e.children].map(c=>{const r=c.getBoundingClientRect();return {top:r.top,left:r.left,right:r.right,
                            value:c.querySelector('button').innerText,client:c.clientWidth,scroll:c.scrollWidth};})};}""")
                        context = (language, width, index, geometry)
                        assert geometry['left'] >= 0 and geometry['right'] <= width, context
                        assert geometry['scroll'] <= geometry['client'] + 1, context
                        assert max(c['top'] for c in geometry['chips']) - min(c['top'] for c in geometry['chips']) < 1, context
                        for chip in geometry['chips']:
                            assert chip['value'] in BASE['STATES'][language].values(), context
                            assert chip['scroll'] <= chip['client'] + 1, context
                        for left, right in zip(geometry['chips'], geometry['chips'][1:]):
                            assert left['right'] <= right['left'], context
                        if shots and index < 2:
                            device(index).screenshot(path=str(shots / f'061b9-device-options-{language}-{width}-device{index}.png'), animations='disabled')
                    for index, key in ((0, KEYS[0]), (0, KEYS[1]), (0, KEYS[2]), (1, KEYS[1])):
                        close_help()
                        icon(key, index).tap()
                        pop = page.locator('.hem-floating-info87')
                        expect(pop).to_be_visible()
                        entity = option(key, index).locator('button').get_attribute('data-device-quick-switch8')
                        attrs = states[entity]['attributes']
                        heading = pop.locator('.hem-help-heading9')
                        assert heading.inner_text() == attrs['setting_label'], (language, key, heading.inner_text())
                        paragraphs = pop.locator('.hem-help-text116')
                        assert paragraphs.all_text_contents() == attrs['configuration_help'].split('\n\n')
                        assert paragraphs.count() >= 3
                        geometry = pop.evaluate("""e=>{const r=e.getBoundingClientRect(),h=e.querySelector('.hem-help-heading9'),
                          range=document.createRange();range.selectNodeContents(h);
                          return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,client:e.clientWidth,scroll:e.scrollWidth,
                            title:[...range.getClientRects()].map(r=>({left:r.left,right:r.right,top:r.top,bottom:r.bottom})),
                            lineHeight:parseFloat(getComputedStyle(e.querySelector('p')).lineHeight),
                            fontSize:parseFloat(getComputedStyle(e.querySelector('p')).fontSize)};}""")
                        context = (language, width, index, key, geometry)
                        assert geometry['left'] >= 0 and geometry['right'] <= width, context
                        assert geometry['top'] >= 0 and geometry['bottom'] <= 1001, context
                        assert geometry['scroll'] <= geometry['client'] + 1, context
                        assert geometry['lineHeight'] >= geometry['fontSize'] * 1.4, context
                        for text in geometry['title']:
                            assert text['left'] >= geometry['left'] and text['right'] <= geometry['right'], context
                        if shots:
                            page.screenshot(path=str(shots / f'061b9-device-help-{language}-{width}-device{index}-{key}.png'), full_page=False)
                        # Refresh must retain readable help and its ownership.
                        page.evaluate('([s,l])=>refresh9(s,l)', [states, language])
                        expect(pop).to_be_visible()
                        assert pop.locator('.hem-help-heading9').inner_text() == attrs['setting_label']
                        paragraphs.last.scroll_into_view_if_needed()
                        expect(paragraphs.last).to_be_visible()
                        icon(key, index).tap()
                        expect(pop).to_have_count(0)
                    assert page.evaluate('calls') == []

            states = fixture('de')
            page.evaluate('([s,l])=>refresh9(s,l)', [states, 'de'])
            maximum = icon('native_full_output')
            maximum.focus()
            page.keyboard.press('Enter')
            expect(page.locator('.hem-floating-info87')).to_be_visible()
            close_help()
            assert maximum.evaluate('e=>e===e.getRootNode().activeElement')
            maximum.tap()
            pop = page.locator('.hem-floating-info87')
            detail = option('native_full_output').locator(':scope > details')
            # The native disclosure's toggle event creates the portal on a
            # later task. Test an actually open bubble before clicking outside;
            # a zero count before that task is not evidence of dismissal.
            expect(pop).to_be_visible()
            expect(detail).to_have_js_property('open', True)
            page.mouse.click(1, 1)
            expect(pop).to_have_count(0)
            expect(detail).to_have_js_property('open', False)
            # A narrower current mode scope must replace the open title/help;
            # withdrawing support must close it and remove the stale action.
            maximum.tap()
            expect(pop).to_be_visible()
            expect(detail).to_have_js_property('open', True)
            a = states['switch.renamed_native_full_output']['attributes']
            expect(pop.locator('.hem-help-heading9')).to_have_text(a['setting_label'])
            a.update(native_full_output_modes=['cool'], setting_label=NAME(['cool'], 'de'),
                     configuration_help=HELP('native_full_output', 'de', modes=['cool']))
            page.evaluate('([s,l])=>refresh9(s,l)', [states, 'de'])
            expect(pop.locator('.hem-help-heading9')).to_have_text(a['setting_label'])
            expect(detail).to_have_js_property('open', True)
            assert pop.locator('.hem-help-text116').all_text_contents() == a['configuration_help'].split('\n\n')
            if shots:
                page.screenshot(path=str(shots / '061b9-device-help-de-390-live-scope.png'), full_page=False)
            a['native_full_output_supported'] = False
            page.evaluate('([s,l])=>refresh9(s,l)', [states, 'de'])
            expect(option('native_full_output')).to_have_count(0)
            expect(page.locator('.hem-floating-info87')).to_have_count(0)
            assert page.evaluate('calls') == []
            # A stale pre-upgrade DOM node cannot call the removed handler.
            page.evaluate("""()=>{const button=document.createElement('button');
              button.setAttribute('data-timed-setpoint-switch','switch.retired_timing_role');
              button.setAttribute('data-controller-area','room0');
              button.setAttribute('data-managed-controller','climate.managed_0_0');
              card.shadowRoot.append(button);button.click();button.remove();}""")
            assert page.evaluate('calls') == []
            option('announce_device_errors').locator('button').click()
            page.wait_for_function('calls.length===1')
            assert page.evaluate('calls') == [['switch', 'turn_off', {'entity_id': 'switch.renamed_announce_device_errors'}]]
            assert not errors, errors
        except Exception:
            if shots:
                page.screenshot(path=str(shots / '061b9-device-help-failure.png'), full_page=True)
            print('B9_CARD_PAGE_ERRORS', errors)
            raise
        finally:
            browser.close()
    print('HEM_061B9_DEVICE_HELP_BROWSER=PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--logic-only', action='store_true')
    group.add_argument('--browser-only', action='store_true')
    args = parser.parse_args()
    if not args.browser_only:
        logic_checks()
    if not args.logic_only:
        browser_checks()
