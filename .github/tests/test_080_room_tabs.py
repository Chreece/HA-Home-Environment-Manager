"""Two-row room summaries keep readings, disclosures and routing usable.

Chromium renders the packaged card at mobile and narrow desktop-column sizes,
with and without native HA floor grouping. All transport is local fixture data.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
import shutil

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/home-environment-manager-card.js"

SETUP = r"""data=>{
  window.calls=[];window.settings=[];window.info=[];
  window.card=document.createElement('home-environment-manager-card');
  document.querySelector('main').append(card);
  card.addEventListener('hass-more-info',e=>info.push(e.detail.entityId));
  card._openRoomSettings114=area=>settings.push(area);
  card.setConfig({entity:'sensor.hem'});
  card.hass={language:data.language,states:data.states,user:{is_admin:true},
    entities:{...data.entities,'sensor.hem':{device_id:'hem-home-device'}},
    connection:{},config:{time_zone:'UTC'},localize:()=>undefined,
    callService:(...args)=>{calls.push(args);return Promise.resolve()},
    callWS:async request=>{
      if(request.type==='config/device_registry/list')return [
        {id:'hem-home-device',identifiers:[['environment_manager','entry']]},
        ...['living','kitchen'].map(area=>({id:'hem-'+area,
          identifiers:[['environment_manager','entry_area_'+area]]}))];
      if(request.type==='history/history_during_period'){
        const now=Date.now()/1000;
        return {[request.entity_ids[0]]:[{s:'20',lu:now-120},{s:'21',lu:now-60}]};
      }
      if(request.type==='environment_manager/control_trend')return {trend:[]};
      throw Error('Unexpected fixture request: '+request.type);
    }};
  window.floorMode080=enabled=>{
    card._floorConnection140=card._hass.connection;
    card._floorRegistry140={floors:enabled?[
      {floor_id:'ground',name:'Ground floor',level:0}]:[],
      areas:[],membership:new Map([['living','ground'],['kitchen','ground']])};
    card._renderContent(true);
  };
}"""

REPORT = r"""()=>{
  const box=node=>{const r=node.getBoundingClientRect();
    return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}};
  const visible=node=>node.getClientRects().length&&getComputedStyle(node).display!=='none';
  const frame=document.querySelector('main');
  return {viewport:innerWidth,pageScroll:document.documentElement.scrollWidth,
    frameWidth:frame.clientWidth,frameScroll:frame.scrollWidth,
    rows:[...card.shadowRoot.querySelectorAll('.hem-room-glance87')].map(summary=>({
      area:summary.parentElement.getAttribute('data-room-fold87'),
      header:box(summary),scrollWidth:summary.scrollWidth,clientWidth:summary.clientWidth,
      tab:box(summary.querySelector('.hem-room-tab080')),
      tabRow:box(summary.querySelector('.hem-room-tabline080')),
      tabVisual:{
        outerBorder:getComputedStyle(summary.parentElement).borderTopWidth,
        tabBg:getComputedStyle(summary.querySelector('.hem-room-tab080')).backgroundColor,
        bodyBg:getComputedStyle(summary,'::before').backgroundColor,
        tabBottom:getComputedStyle(summary.querySelector('.hem-room-tab080')).borderBottomColor,
        panelRow:getComputedStyle(summary,'::before').gridRowStart,
        panelOffset:getComputedStyle(summary,'::before').top
      },
      name:box(summary.querySelector('.hem-room-name87')),
      settings:box(summary.querySelector('[data-room-settings114]')),
      faces:summary.querySelector('.hem-room-faces') && box(summary.querySelector('.hem-room-faces')),
      faceLabel:summary.querySelector('.hem-room-faces')?.getAttribute('aria-label'),
      alerts:[...summary.querySelectorAll('.hem-room-alerts87 button')].map(button=>({
        ...box(button),icon:button.querySelector('ha-icon').getAttribute('icon')})),
      nameText:summary.querySelector('.hem-room-name87').textContent,
      nameTitle:summary.querySelector('.hem-room-name87').title,
      settingsLabel:summary.querySelector('[data-room-settings114]').getAttribute('aria-label'),
      metrics:[...summary.querySelectorAll('.hem-room-metric107')].filter(visible).map(node=>({
        box:box(node),scrollWidth:node.scrollWidth,clientWidth:node.clientWidth,
        value:node.querySelector('.hem-room-metric-value107')?.textContent,
        glyphs:[...node.querySelectorAll('ha-icon')].map(icon=>({
          ...box(icon.shadowRoot.querySelector('svg')),icon:icon.getAttribute('icon')})),
        valueBox:box(node.querySelector('.hem-room-metric-value107'))})),
      leaves:[...summary.querySelectorAll('.hem-room-metric107,'+
        ':scope > ha-icon:last-child')].filter(visible).map(box),
      chevron:box(summary.querySelector(':scope > ha-icon:last-child')),
      chevronIcon:summary.querySelector(':scope > ha-icon:last-child').getAttribute('icon')
    }))};
}"""


def assert_geometry(report, label):
    assert report['pageScroll'] <= report['viewport'] + 1, (label, report)
    assert report['frameScroll'] <= report['frameWidth'] + 1, (label, report)
    assert len(report['rows']) == 2, (label, report)
    for row in report['rows']:
        context = (label, row)
        assert row['tabVisual']['outerBorder'] == '0px', ('no outer frame above tab', *context)
        assert row['tabVisual']['tabBg'] == row['tabVisual']['bodyBg'], ('one surface colour', *context)
        assert row['tabVisual']['tabBottom'] == row['tabVisual']['bodyBg'], ('no tab seam', *context)
        assert abs(row['tab']['left'] - row['header']['left']) <= 1, ('aligned outer edges', *context)
        assert row['tab']['top'] >= row['header']['top'] - 1, ('no border above title', *context)
        assert row['tabVisual']['panelRow'] == '2' and row['tabVisual']['panelOffset'] == '-1px', ('continuous outline', *context)
        assert row['scrollWidth'] <= row['clientWidth'] + 1, context
        assert 60 <= row['header']['height'] <= 100, ('two compact rows', *context)
        assert row['settings']['right'] <= row['name']['left'] + 1, context
        assert row['name']['width'] > 12, context
        if row['faces']:
            assert row['faceLabel'], context
            assert row['name']['right'] <= row['faces']['left'] <= row['name']['right'] + 8, context
        assert row['alerts'], context
        previous = row['faces'] or row['name']
        assert previous['right'] <= row['alerts'][0]['left'] <= previous['right'] + 8, context
        for alert in row['alerts']:
            assert alert['width'] >= 22 and alert['right'] <= row['tab']['right'], context
            assert row['tabRow']['top'] <= alert['top'] < alert['bottom'] <= row['tabRow']['bottom'], context
        assert row['settings']['top'] < row['name']['bottom'], context
        assert row['nameText'] in row['nameTitle'], context
        assert row['nameText'] in row['settingsLabel'], context
        assert row['settings']['width'] >= 32 and row['settings']['height'] >= 32, context
        assert row['metrics'], context
        centers = []
        for metric in row['metrics']:
            rect = metric['box']
            assert rect['top'] >= max(row['name']['bottom'], row['settings']['bottom']), context
            assert row['header']['left'] <= rect['left'] < rect['right'] <= row['header']['right'], context
            assert metric['scrollWidth'] <= metric['clientWidth'] + 1, context
            assert metric['value'], context
            assert rect['left'] <= metric['valueBox']['left'] <= metric['valueBox']['right'] <= rect['right'], context
            value_center = (metric['valueBox']['top'] + metric['valueBox']['bottom']) / 2
            for glyph in metric['glyphs']:
                assert glyph['height'] > 0 and abs((glyph['top'] + glyph['bottom']) / 2 - value_center) <= 1, (
                    'visible glyph and value must share a center', glyph['icon'], *context)
            centers.append((rect['top'] + rect['bottom']) / 2)
        assert max(centers) - min(centers) <= 1, ('overview must remain one row', *context)
        leaves = sorted(row['leaves'], key=lambda rect: rect['left'])
        for first, second in zip(leaves, leaves[1:]):
            assert first['right'] <= second['left'] + 0.5, ('overview controls overlap', *context)
        assert row['chevron']['right'] <= row['header']['right'], context


def run():
    base = runpy.run_path(str(ROOT / '.github/tests/test_beta122_card_details.py'))['fixture']()
    # Header temperature links require the selected room measurement's source
    # evidence. The shared details fixture only supplies standalone readings.
    temperature = next(reading for reading in base['room']['readings']
                       if reading['metric'] == 'temperature')
    base['room']['environment']['measurement_evidence'] = {
        'temperature': {'value': temperature['value'], 'source_count': 1,
                        'source_ids': [temperature['entity_id']]},
        'humidity': {'value': 50, 'source_count': 2,
                     'source_ids': ['sensor.humidity', 'sensor.humidity_second']},
    }
    base['states']['sensor.humidity_second'] = deepcopy(base['states']['sensor.humidity'])
    icons = runpy.run_path(str(ROOT / '.github/tests/test_061b1_room_fold.py'))['icon_fixture']()
    chrome = os.environ.get('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
    assert chrome, 'Chromium is required for room-tab layout validation'
    shots = Path(os.environ['HEM_TEST_SCREENSHOT_DIR']) if os.environ.get('HEM_TEST_SCREENSHOT_DIR') else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page(viewport={'width': 1024, 'height': 1100})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            for language in ('en', 'el', 'de'):
                data = deepcopy(base)
                second = deepcopy(data['room'])
                second.update(area_id='kitchen', name={
                    'en': 'Kitchen and dining room with an unusually long room name',
                    'el': 'Κουζίνα και τραπεζαρία με πολύ μεγάλο όνομα δωματίου',
                    'de': 'Küche und Essbereich mit außergewöhnlich langem Raumnamen',
                }[language])
                data['states']['sensor.hem']['attributes']['dashboard']['rooms'].append(second)
                # Exercise more simultaneous alerts than the old desktop/mobile caps.
                second.update(action='close', windows=[
                    {'entity_id':'binary_sensor.open', 'name':'Open', 'opened':True},
                    {'entity_id':'binary_sensor.missing', 'name':'Offline', 'opened':None}])
                second['environment']['room_ventilation']={'air_refresh_status':'refresh_recommended'}
                data['language'] = language
                page.set_content('''<!doctype html><style>
                  *{box-sizing:border-box}body{margin:0;background:#101820;color:#e8edf3;font-family:Arial}
                  :root{--primary-text-color:#e8edf3;--secondary-text-color:#aebbc8;
                  --card-background-color:#18212b;--secondary-background-color:#22303d;--divider-color:#455463}
                  main{width:760px;max-width:100%;margin:0 auto}
                </style><main></main>''')
                # A fresh page keeps custom-element registration and listeners isolated.
                page.evaluate(icons)
                page.add_script_tag(path=str(CARD))
                page.evaluate(SETUP, data)
                # No separate legacy custom card may be registered or suggested.
                assert page.evaluate('''() => !customElements.get(
                    'air-quality-advisor-card') && !customElements.get(
                    'air-quality-advisor-card-editor') &&
                    !!customElements.get('home-environment-manager-card') &&
                    !!customElements.get('home-environment-manager-card-editor') &&
                    window.customCards.filter(
                        c=>c.type==='home-environment-manager-card').length===1
                ''')
                expect(page.locator('[data-room-settings114="living"]')).to_be_enabled()
                for floors in (False, True):
                    page.evaluate('floorMode080', floors)
                    for viewport, column in ((1024, 760), (1024, 320), (320, 320), (390, 390), (600, 600)):
                        page.set_viewport_size({'width': viewport, 'height': 1100})
                        page.evaluate("width=>document.querySelector('main').style.width=width+'px'", column)
                        label = f'{language}-{viewport}-{column}-floors{floors}'
                        report = page.evaluate(REPORT)
                        if shots and language == 'el' and (viewport, column) in ((1024, 760), (320, 320)):
                            page.screenshot(path=str(shots / f'room-tabs-{label}.png'), full_page=True)
                        assert_geometry(report, label)
                        kitchen = next(row for row in report['rows'] if row['area'] == 'kitchen')
                        assert {'mdi:weather-windy', 'mdi:window-open-variant', 'mdi:window-closed-variant'} <= {
                            alert['icon'] for alert in kitchen['alerts']}, label
                        assert len(kitchen['alerts']) >= 5, (label, kitchen['alerts'])
                        assert any(glyph['icon'] == 'mdi:approximately-equal'
                                   for metric in kitchen['metrics'] for glyph in metric['glyphs']), label
                # Render through the real card, including its measurement selection.
                faces = page.evaluate("""base=>{
                  function render(t,r,options={}){
                    const room=structuredClone(base);
                    room.readings=[
                      {metric:'temperature',value:t,available:t!==null},
                      {metric:'humidity',value:r,available:r!==null,threshold:options.rhLimit||65},
                      ...(options.air||[])];
                    room.environment={international:{pmv_ppd:options.pmv},thermal_comfort:options.adaptive};
                    const wrapper=document.createElement('div');
                    wrapper.innerHTML=card._room(room);
                    const face=wrapper.querySelector('.hem-room-faces');
                    if(!face.title||face.title!==face.getAttribute('aria-label')||
                        !wrapper.querySelector('.hem-room-condition-detail').textContent.includes(face.title))
                      throw Error('Missing readable condition label');
                    const art=face.querySelector('svg');
                    if(face.querySelectorAll('svg').length!==1||art.getAttribute('aria-hidden')!=='true'||
                      !art.querySelector('.hem-face-shell')||
                      wrapper.querySelector('.hem-room-condition-detail svg')?.outerHTML!==art.outerHTML)
                      throw Error('Conditions did not render as one consistent face');
                    const states=art.dataset.conditions.split(' ');
                    for(const [state,part] of [['poor-air','.hem-face-mask'],['humid','.hem-face-drop'],['dry','.hem-face-dry']])
                      if(states.includes(state)!==!!art.querySelector(part))throw Error('Missing or unexpected feature '+state);
                    return art.dataset.conditions;
                  }
                  const poor={metric:'co2',value:1400,available:true,exceeded:true};
                  const missing={...poor,available:false,value:null};
                  return [render(20,30),render(26,64),render(19,29),render(27,65,{air:[poor]}),
                    render(null,null),render(null,45),render(null,null,{air:[poor]}),
                    render(22,45,{air:[missing]}),render(22,45,{air:[{...poor,metric:'aqi',
                      evaluation_status:'configuration_required'}]}),render(22,55,{rhLimit:55}),
                    render(22,45,{adaptive:{status:'below_band'}}),
                    render(22,45,{pmv:{status:'estimate',pmv:0.7},adaptive:{status:'below_band'}})];
                }""", data['room'])
                assert faces == ['comfortable','comfortable','cold dry','poor-air hot humid','unknown','unknown',
                                 'poor-air','unknown','unknown','humid','cold','hot'], faces
                for enabled in (False, True):
                    page.evaluate("""enabled=>{
                      card._hass.states['sensor.hem'].attributes.dashboard.show_room_smileys=enabled;
                      card._renderContent(true);
                    }""", enabled)
                    report = page.evaluate(REPORT)
                    assert_geometry(report, f'{language} smileys {enabled}')
                    assert all(bool(row['faces']) == enabled for row in report['rows'])
                    expect(page.locator('.hem-room-condition-detail [aria-hidden]')).to_have_count(2 if enabled else 0)
                    assert all(page.locator('.hem-room-condition-detail').all_text_contents())
                room = page.locator('[data-room-fold87="living"]')
                summary = room.locator(':scope > summary')
                summary.locator('.hem-room-name87').click()
                expect(room).to_have_attribute('open', '')
                expect(summary.locator(':scope > ha-icon:last-child')).to_have_attribute('icon', 'mdi:chevron-up')
                page.evaluate('card._renderContent(true)')
                expect(room).to_have_attribute('open', '')
                summary.focus()
                page.keyboard.press('Enter')
                expect(room).not_to_have_attribute('open', '')
                summary.locator('[data-room-settings114]').click()
                assert page.evaluate('settings') == ['living']
                expect(room).not_to_have_attribute('open', '')
                summary.locator('[data-hem-source105="sensor.temperature"]').click()
                expect(page.locator('.hem-avg-dialog105')).to_be_visible()
                assert page.evaluate('card._averageDialog105.entity122') == 'sensor.temperature'
                expect(room).not_to_have_attribute('open', '')
                page.keyboard.press('Escape')
                expect(page.locator('.hem-avg-dialog105')).to_have_count(0)
                floor = page.locator('[data-floor-fold140="ground"]')
                floor.locator(':scope > summary').click()
                expect(room).not_to_be_visible()
                floor.locator(':scope > summary').click()
                expect(room).to_be_visible()
                assert page.evaluate('calls') == [], 'Read-only room actions sent a device command'
                assert not errors, errors
                page.close()
                page = browser.new_page(viewport={'width': 1024, 'height': 1100})
                page.on('pageerror', lambda error: errors.append(str(error)))
        except Exception:
            if shots:
                page.screenshot(path=str(shots / 'room-tabs-failure.png'), full_page=True)
                (shots / 'room-tabs-failure.json').write_text(json.dumps(page.evaluate(REPORT), indent=2))
            raise
        finally:
            browser.close()
    print('080_ROOM_TABS_RESPONSIVE_FLOORS_KEYBOARD_SETTINGS_AND_TRENDS=PASS')


if __name__ == '__main__':
    run()
