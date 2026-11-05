"""Beta92: repeated native updates cannot snap a nested Lovelace view to top.

Real Chromium executes the production HEM card inside a shadow-DOM
three-column dashboard, recreating the uploaded recording's scroll reset.
The regression injects the two browser/host layout timings that Beta91's
card-identity-only guard missed: synchronous and next-frame scroll resets.
No physical HA service or network connection is made.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import runpy
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
baseline = runpy.run_path(str(ROOT / '.github/tests/test_beta87_compact_browser.py'))
states = deepcopy(baseline['states'])
data = deepcopy(baseline['data'])
data['rooms'] = deepcopy(baseline['rooms'])
states['sensor.hem']['attributes']['dashboard'] = data
chrome = shutil.which('chromium') or shutil.which('google-chrome')
assert chrome, 'Chromium required'

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=chrome, headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage'],
    )
    page = browser.new_page(viewport={'width': 1420, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content("""<!doctype html><html><head><style>
      html, body { margin:0; background:#101010; color:#eee; }
      :root { --primary-text-color:#eee; --secondary-text-color:#aaa;
        --card-background-color:#202020; --secondary-background-color:#292929;
        --divider-color:#444 }
    </style></head><body></body></html>""")
    page.add_script_tag(path=str(ROOT/'frontend/air-quality-advisor-card.js'))
    origin = page.evaluate("""({states}) => {
      class TestHassLovelaceShell extends HTMLElement {
        connectedCallback() {
          const root = this.attachShadow({mode:'open'});
          root.innerHTML = '<style>' +
            '#scroll {height:360px;width:1370px;overflow:auto;scrollbar-width:thin;}' +
            '#columns {display:grid;grid-template-columns:380px 560px 380px;gap:15px}' +
            '.side {background:#252525;min-height:240px;padding:10px}' +
            '</style><main id="scroll"><div id="columns">' +
            '<aside id="left" class="side">Unrelated slider card</aside>' +
            '<section id="middle"></section>' +
            '<aside id="right" class="side">Unrelated thermostat cards</aside>' +
            '</div></main>';
        }
      }
      customElements.define('test-hass-lovelace-shell',TestHassLovelaceShell);
      const host = document.createElement('test-hass-lovelace-shell');
      document.body.append(host);
      const shadow = host.shadowRoot;
      const scroller = shadow.getElementById('scroll');
      const card = document.createElement('home-environment-manager-card');
      shadow.getElementById('middle').append(card);
      card._hass={language:'en',states,localize:()=>undefined,
          callService:()=>{throw Error('Physical service call forbidden')}};
      card._config={entity:'sensor.hem'};
      card._roomsExpanded87=new Set(['room0']);
      card._devicesExpanded87=new Set(['climate.managed_0_0']);
      card._renderContent(true);
      scroller.scrollTop=330;
      window.shell=host;
      window.scroller=scroller;
      window.card=card;
      window.firstCard=card.shadowRoot.querySelector('ha-card.shell');
      window.firstRoom=card.shadowRoot.querySelector(
          '[data-room-fold87="room0"]');
      window.firstDevice=card.shadowRoot.querySelector(
          '[data-device-fold87="climate.managed_0_0"]');
      window.firstLeft=shadow.getElementById('left');
      window.firstRight=shadow.getElementById('right');
      window.originalCommit=card._commitContent91;
      return scroller.scrollTop;
    }""", {'states':states})
    assert origin >= 200, ('scrolling dashboard not tall enough',origin)

    # Emulate the observed HA view jump at both possible layout timings.
    # Beta91 kept the root card identity and therefore never recovered it.
    page.evaluate("""() => {
      let updates=0;
      card._commitContent91=function(html) {
        const result=window.originalCommit.call(this,html);
        if((++updates)%2===0) scroller.scrollTop=0;
        else requestAnimationFrame(()=>{scroller.scrollTop=0});
        return result;
      };
    }""")
    for iteration in range(20):
        page.evaluate("""index => {
          const old=card._hass.states;
          const current=old['climate.physical_0_0'];
          const next={...old,
            'climate.physical_0_0':{...current,attributes:{
              ...current.attributes,hvac_action:index%2?'heating':'idle'
            }}
          };
          card._hass={...card._hass,states:next};
          card._renderContent(true);
        }""",iteration)
        page.wait_for_timeout(70)
        result=page.evaluate("""() => ({
          top:scroller.scrollTop,
          card:firstCard===card.shadowRoot.querySelector('ha-card.shell'),
          room:firstRoom===card.shadowRoot.querySelector('[data-room-fold87="room0"]'),
          device:firstDevice===card.shadowRoot.querySelector(
              '[data-device-fold87="climate.managed_0_0"]'),
          left:firstLeft===shell.shadowRoot.getElementById('left'),
          right:firstRight===shell.shadowRoot.getElementById('right'),
          opened:firstRoom.open && firstDevice.open,
          rescues:card._unexpectedScrollRescues92||0
        })""")
        assert abs(result['top']-origin)<=3, (iteration,result,origin)
        assert all(result[k] for k in ('card','room','device','left','right','opened')),result
        assert result['rescues']>=iteration+1,result

    # Do not move a user who scrolls intentionally in the next frame.
    page.evaluate("""() => {
      card._commitContent91=window.originalCommit;
      card._renderContent(true);
      scroller.scrollTop=125;
      // Real wheel/touch/key events inside the card increment this epoch.
      card._hemScrollEpoch90=(card._hemScrollEpoch90||0)+1;
    }""")
    page.wait_for_timeout(80)
    assert abs(page.evaluate('scroller.scrollTop')-125)<=3

    # Small native browser anchor changes are not forced back.
    page.evaluate("""() => {
      scroller.scrollTop=330;
      card._commitContent91=function(html) {
        const result=window.originalCommit.call(this,html);
        scroller.scrollTop-=12;
        return result;
      };
      card._renderContent(true);
    }""")
    page.wait_for_timeout(70)
    assert abs(page.evaluate('scroller.scrollTop')-318)<=3
    assert not errors,errors
    browser.close()

print('BETA92_LOVELACE_NATIVE_SCROLL_RESET_RECOVERY_20_FRAMES=PASS')
