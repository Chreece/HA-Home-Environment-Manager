"""Retired timing metadata cannot create controls or hide genuine recovery.

Use --status-only for production card checks in Node. The full run also checks
the connected card, actual native values, fault visibility and retirement in
Chromium. All service transport and devices are fixtures.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
CODES = (
    "native_setpoint_startup_grace", "native_setpoint_shutdown_grace",
    "native_setpoint_shutdown_preparing", "native_setpoint_shutdown_blocked",
)
LANGUAGES = ("en", "el", "de")


def fixture_module():
    path = ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"
    spec = importlib.util.spec_from_file_location("_hem_beta109_browser_fixture", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and node.module == "playwright.sync_api")]
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


def phase_fixture(previous, base, helper, language, code):
    # A stale retired phase must never hide an independent real recovery action.
    states, _ = previous.fixture(base, helper, language, manual_check=True)
    phase = {
        "status": code,
        "setpoint_wait_remaining_seconds": 30,
        "setpoint_wait_until": previous.NOW + 30,
        "requested_temperature": 30.0 if code == CODES[0] else 5.0,
        "native_mode": "heat",
    }
    states[previous.CONTROLLER]["attributes"]["controller_status"] = phase
    states[previous.STATUS]["attributes"].update(
        **{key: value for key, value in phase.items() if key != "status"},
        status_code=code,
        status_reason_code="minimum_on_hold" if code == CODES[3] else None,
        paused_reason=None,
    )
    room = states["sensor.hem"]["attributes"]["dashboard"]["rooms"][0]
    room["status"] = "safe"
    return states


NODE_CHECKS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={};Date.now=()=>input.now*1000;
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');let services=0;
const make=(language,states)=>{
  const card=Object.create(Card.prototype);
  card._hass={language,states:structuredClone(states),localize:()=>undefined,
    callService:()=>{services++;throw Error('Display sent a service command')}};
  card._interactions66=true;card._detailsExpanded66=new Set();
  card._windowSwitchPending66=new Set();card._calibrationExpanded65=new Set();
  card._areaDeviceIds=new Map();card._config={entity:'sensor.hem'};
  return card;
};
const panel=card=>card._controllerPanel(card._hass.states['sensor.hem'].attributes.dashboard.rooms[0]);
for(const language of input.languages)for(const code of input.codes){
  const card=make(language,input.fixtures[code]),entry=card._managedControllers('room0')[0];
  assert.equal(card._setpointPhase109,undefined,'retired phase renderer remains');
  const html=panel(card);
  assert.ok(!html.includes('30 s · '),'retired phase still creates a countdown');
  assert.ok(!html.includes('data-timed-setpoint-switch'));
  assert.ok(html.includes('hem-resume-recovery'),'real recovery explanation hidden by old phase');
  assert.ok(html.includes('data-native-resume='),'real recovery action hidden by old phase');
  const before=JSON.stringify(card._hass.states);panel(card);
  assert.equal(JSON.stringify(card._hass.states),before,'presentation mutated source evidence');
  const a=entry.statusInfo.state.attributes,signature=card._controllerSignature();
  a.setpoint_wait_remaining_seconds=12;a.setpoint_wait_until=input.now+12;a.requested_temperature=99;
  assert.equal(card._controllerSignature(),signature,'retired direct metadata is still hashed');
  a.status_code='minimum_on_hold';a.native_minimum_on_until=input.now+30;
  assert.ok(panel(card).includes('1 min'),'ordinary minimum-ON hold lost');
  assert.ok(panel(card).includes('hem-resume-recovery'));
  const original=card._managedControllers.bind(card);
  card._managedControllers=area=>original(area).map(e=>({...e,
    errorAnnounce:{state:'off',attributes:{native_error:{status:'error',
      code:'E7',description:'Native error example'}}}}));
  assert.ok(panel(card).includes('Native error example'),'disabled announcements hid native fault');
  assert.ok(panel(card).includes('hem-resume-recovery'));
}
assert.equal(services,0);
console.log('BETA109_TIMING_RETIREMENT_RECOVERY_NATIVE_FAULT_READ_ONLY=PASS');
"""


def run_status_checks(previous, fixtures):
    subprocess.run([shutil.which("node") or "node", "-e", NODE_CHECKS, str(CARD)],
        check=True, input=json.dumps({"fixtures": fixtures, "codes": CODES,
            "languages": LANGUAGES, "now": previous.NOW}), text=True)


def run_browser_checks(previous, base, helper):
    from playwright.sync_api import sync_playwright
    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome and Path(chrome).is_file(), "Chromium required (or use --status-only)"
    shots = Path(os.environ["HEM_TEST_SCREENSHOT_DIR"]) if os.environ.get("HEM_TEST_SCREENSHOT_DIR") else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 590, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content('<style>*{box-sizing:border-box}body{margin:0;background:#111;color:#ddd;font:14px Arial}'
                         ':root{--primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;'
                         '--card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}</style>')
        page.evaluate("now=>{Date.now=()=>now*1000}", previous.NOW)
        page.evaluate(previous.icon_fixture())
        page.add_script_tag(path=str(CARD))
        for language in LANGUAGES:
            for code in CODES:
                states = phase_fixture(previous, base, helper, language, code)
                page.evaluate(previous.RENDER, {"states": states, "language": language,
                    "controller": previous.CONTROLLER})
                device = page.locator(f'[data-device-fold87="{previous.CONTROLLER}"]')
                status = device.locator('.hem-device-state76 > .hem-status-pill76').first
                assert '30 s · ' not in status.inner_text(), (language, code, status.inner_text())
                assert device.locator('.hem-resume-recovery').count() == 1
                assert device.locator('[data-native-resume]').count() == 1
                assert device.locator('[data-timed-setpoint-switch]').count() == 0
                previous.assert_native_tiles(device, language, target_present=True)
                assert device.locator(':scope > summary ha-icon[icon="mdi:timer-sand"]').count() == 0
                assert page.evaluate('calls') == []
                if shots and code == CODES[0]:
                    device.screenshot(path=str(shots / f'beta109-retired-timing-recovery-{language}.png'))
        page.evaluate("""({controller,status})=>{
          const original=card._managedControllers.bind(card);
          card._managedControllers=area=>original(area).map(e=>e.entityId===controller?{...e,
            errorAnnounce:{state:'off',attributes:{native_error:{status:'error',
              code:'E7',description:'Native error example'}}}}:e);
          card._hass.states[status].attributes.status_code='native_setpoint_shutdown_grace';
          card._renderContent(true);
        }""", {"controller": previous.CONTROLLER, "status": previous.STATUS})
        device = page.locator(f'[data-device-fold87="{previous.CONTROLLER}"]')
        assert device.locator(':scope > summary ha-icon[icon="mdi:alert-octagon-outline"]').count() == 1
        assert 'Native error example' in device.inner_text()
        assert device.locator('.hem-resume-recovery').count() == 1
        assert page.evaluate('calls') == []
        assert not errors, errors
        browser.close()
    print('BETA109_RETIRED_TIMING_NATIVE_VALUES_REAL_RECOVERY_BROWSER=PASS')


if __name__ == "__main__":
    previous = fixture_module()
    base = previous.fixture_definitions()
    helper = previous.recovery_module()
    fixtures = {code: phase_fixture(previous, base, helper, "en", code) for code in CODES}
    run_status_checks(previous, fixtures)
    if "--status-only" not in sys.argv[1:]:
        run_browser_checks(previous, base, helper)
