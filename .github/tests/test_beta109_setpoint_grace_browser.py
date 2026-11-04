"""Beta109: native setpoint delays are readable waits, with exact seconds.

Exercise the shipped card methods in Node and the rendered card in Chromium.
The existing Beta108 fixture keeps native measurements separate from intent.
Use --status-only when Chromium is unavailable; release CI runs both layers.
No Home Assistant service or physical device is contacted.
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
    "native_setpoint_startup_grace",
    "native_setpoint_shutdown_grace",
    "native_setpoint_shutdown_preparing",
    "native_setpoint_shutdown_blocked",
)
REASONS = (
    "invalid_shutdown_sequence", "invalid_shutdown_deadline", "invalid_shutdown_retry_history",
    "shutdown_target_authority_changed", "shutdown_finish_authority_changed",
    "upstream_switch_not_verified_on", "shutdown_command_evidence_missing",
    "native_mode_changed_during_shutdown", "shutdown_sequence_in_progress",
)
LABELS = {
    "en": (
        "Waiting before setting the operating temperature",
        "Waiting before switching off",
        "Preparing the device to switch off",
        "Waiting until the device can switch off safely",
    ),
    "el": (
        "Αναμονή πριν τη ρύθμιση της θερμοκρασίας λειτουργίας",
        "Αναμονή πριν την απενεργοποίηση",
        "Προετοιμασία απενεργοποίησης της συσκευής",
        "Αναμονή για ασφαλή απενεργοποίηση της συσκευής",
    ),
    "de": (
        "Warten vor dem Einstellen der Betriebstemperatur",
        "Warten vor dem Ausschalten",
        "Ausschalten des Geräts wird vorbereitet",
        "Warten, bis das Gerät sicher ausgeschaltet werden kann",
    ),
}


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
    # Retain a stale two-check Resume explanation to prove that an ordinary
    # scheduled delay does not display it as an action the user must take.
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
const assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={};
let now=input.now;
Date.now=()=>now*1000;
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');
let services=0;
const make=(language,states)=>{
  const card=Object.create(Card.prototype);
  card._hass={language,states:structuredClone(states),localize:()=>undefined,
    callService:()=>{services++;throw Error('A display check sent a service command')}};
  card._interactions66=true;card._detailsExpanded66=new Set();
  card._windowSwitchPending66=new Set();card._calibrationExpanded65=new Set();
  card._areaDeviceIds=new Map();card._config={entity:'sensor.hem'};
  return card;
};
const panel=card=>card._controllerPanel(
  card._hass.states['sensor.hem'].attributes.dashboard.rooms[0]);
for(const [language,labels] of Object.entries(input.labels)) {
  for(const [index,code] of input.codes.entries()) {
    const card=make(language,input.fixtures[code]);
    const entry=card._managedControllers('room0')[0];
    const phase=card._setpointPhase109(entry);
    assert.equal(card._controllerStatusLabel(code),labels[index]);
    assert.equal(phase.label,labels[index]+(index<2?' · 30 s':''));
    assert.equal(phase.grace,index<2);
    assert.equal(phase.seconds,index<2?30:null);
    const html=panel(card);
    assert.ok(html.includes(phase.label));
    assert.ok(html.includes('mdi:timer-sand'));
    assert.equal(html.includes('hem-resume-recovery'),index>=2);
    assert.ok(!html.includes('30 min') && !html.includes('1 min'));
    if(index===0) assert.equal(phase.target,null);
    else assert.ok(phase.target.includes('5 °C'));
    const before=JSON.stringify(card._hass.states);
    card._setpointPhase109(entry);panel(card);
    assert.equal(JSON.stringify(card._hass.states),before,'presentation mutated HA evidence');
  }
}
const card=make('en',input.fixtures[input.codes[1]]);
const entry=card._managedControllers('room0')[0];
const status=entry.statusInfo.state.attributes, nested=entry.climate.attributes.controller_status;
now=input.now+1.1;
assert.equal(card._setpointPhase109(entry).seconds,29);
now=input.now+31;
assert.equal(card._setpointPhase109(entry).seconds,0);
now=input.now;
delete status.setpoint_wait_until;delete nested.setpoint_wait_until;
assert.equal(card._setpointPhase109(entry).seconds,30);
delete status.setpoint_wait_remaining_seconds;
assert.equal(card._setpointPhase109(entry).seconds,30,'nested climate phase fallback');
delete nested.setpoint_wait_remaining_seconds;
assert.equal(card._setpointPhase109(entry).seconds,null,'missing wait is not fabricated as zero');
assert.ok(!/\d+ s\b/.test(card._setpointPhase109(entry).label));
const signature=card._controllerSignature();
status.setpoint_wait_remaining_seconds=12;
assert.notEqual(card._controllerSignature(),signature,'countdown-only update must redraw');
const signature2=card._controllerSignature();
status.setpoint_wait_until=input.now+12;
assert.notEqual(card._controllerSignature(),signature2,'deadline-only update must redraw');
status.status_code='minimum_on_hold';status.native_minimum_on_until=input.now+30;
assert.equal(card._setpointPhase109(entry),null);
assert.ok(panel(card).includes('1 min'),'ordinary minimum-ON presentation changed');
assert.ok(panel(card).includes('hem-resume-recovery'),'real recovery explanation was hidden');
const french=make('fr',input.fixtures[input.codes[0]]);
assert.equal(french._controllerStatusLabel(input.codes[0]),input.labels.en[0]);
for(const language of Object.keys(input.labels)) {
  const held=make(language,input.fixtures[input.codes[3]]);
  const heldEntry=held._managedControllers('room0')[0];
  const english=make('en',input.fixtures[input.codes[3]]);
  for(const reason of input.reasons) {
    const label=held._controllerStatusLabel(reason);
    assert.ok(label.length>20 && !label.includes('_'),reason+': '+label);
    if(language!=='en') assert.notEqual(label,english._controllerStatusLabel(reason));
    heldEntry.statusInfo.state.attributes.status_reason_code=reason;
    assert.ok(held._deviceSummary65(heldEntry).includes(label));
  }
  const withFault=make(language,input.fixtures[input.codes[1]]);
  const original=withFault._managedControllers.bind(withFault);
  withFault._managedControllers=area=>original(area).map(e=>({...e,
    errorAnnounce:{state:'on',attributes:{native_error:{status:'error',
      code:'E7',description:'Native error example'}}}}));
  const html=panel(withFault);
  assert.ok(html.includes('hem-device-error') && html.includes('Native error example'));
  assert.ok(!html.includes('hem-resume-recovery'));
}
assert.equal(services,0);
console.log('BETA109_SETPOINT_STATUS_SECONDS_LOCALIZATION_READ_ONLY=PASS');
"""


def run_status_checks(previous, fixtures):
    node = shutil.which("node")
    assert node, "Node is required to exercise the actual card methods"
    subprocess.run(
        [node, "-e", NODE_CHECKS, str(CARD)], check=True,
        input=json.dumps({"fixtures": fixtures, "codes": CODES, "reasons": REASONS,
                          "labels": LABELS, "now": previous.NOW}), text=True,
    )
    spec = importlib.util.spec_from_file_location(
        "_hem_beta109_status_catalog", ROOT / "controller_status_catalog.py")
    assert spec and spec.loader
    catalog = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(catalog)
    assert set(CODES) <= catalog.CONTROLLER_STATUS_CODES
    assert set(CODES) <= catalog.EQUIPMENT_SENSOR_STATUSES
    assert set(REASONS) <= catalog.CONTROLLER_STATUS_CODES


def run_browser_checks(previous, base, helper):
    from playwright.sync_api import sync_playwright

    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
        shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome and Path(chrome).is_file(), "Chromium required (or use --status-only)"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 590, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content("""<!doctype html><html><head><style>
          *{box-sizing:border-box}body{margin:0;background:#111;color:#ddd;font-family:Arial,sans-serif}
          :root{--primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;
          --card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}
          #card-frame{width:100%;max-width:100%}
        </style></head><body><main id="card-frame"></main></body></html>""")
        page.evaluate("now => {Date.now=()=>now*1000}", previous.NOW)
        page.evaluate(previous.icon_fixture())
        page.add_script_tag(path=str(CARD))
        for language, labels in LABELS.items():
            for index, code in enumerate(CODES):
                states = phase_fixture(previous, base, helper, language, code)
                page.evaluate(previous.RENDER, {
                    "states": states, "language": language, "controller": previous.CONTROLLER})
                device = page.locator(f'[data-device-fold87="{previous.CONTROLLER}"]')
                phase = device.locator('.hem-device-state76 > .hem-status-pill76').first
                assert previous.normalize(phase.inner_text()) == labels[index] + (
                    " · 30 s" if index < 2 else "")
                assert "hem-tone-neutral" in phase.get_attribute("class")
                assert phase.locator('ha-icon').get_attribute("icon") == "mdi:timer-sand"
                assert device.locator('.hem-resume-recovery').count() == (0 if index < 2 else 1)
                previous.assert_native_tiles(device, language, target_present=True)
                glance = device.locator(':scope > summary')
                assert labels[index] in glance.get_attribute("aria-label")
                assert glance.locator('ha-icon[icon="mdi:timer-sand"]').count() == 1
                assert glance.locator('ha-icon[icon="mdi:alert-circle-outline"]').count() == 0
                assert glance.locator('ha-icon[icon="mdi:alert-octagon-outline"]').count() == 0
                assert page.evaluate("calls") == []
                assert not errors, errors
        # A real native device error still has its own attention indicator;
        # the wait status is not a general exemption from fault presentation.
        page.evaluate("""({controller,status}) => {
          const entry=card._managedControllers('room0')[0];
          const fault={state:'on',attributes:{native_error:{status:'error',
            code:'E7',description:'Native error example'}}};
          const original=card._managedControllers.bind(card);
          card._managedControllers=area=>original(area).map(e=>
            e.entityId===controller?{...e,errorAnnounce:fault}:e);
          card._hass.states[status].attributes.status_code='native_setpoint_shutdown_grace';
          card._renderContent(true);
        }""", {"controller": previous.CONTROLLER, "status": previous.STATUS})
        device = page.locator(f'[data-device-fold87="{previous.CONTROLLER}"]')
        assert device.locator(':scope > summary ha-icon[icon="mdi:alert-octagon-outline"]').count() == 1
        assert page.evaluate("calls") == []
        assert not errors, errors
        browser.close()
    print("BETA109_SETPOINT_GRACE_RENDERED_SECONDS_AND_NATIVE_VALUES=PASS")


if __name__ == "__main__":
    previous = fixture_module()
    base = previous.fixture_definitions()
    helper = previous.recovery_module()
    fixtures = {code: phase_fixture(previous, base, helper, "en", code) for code in CODES}
    run_status_checks(previous, fixtures)
    if "--status-only" not in sys.argv[1:]:
        run_browser_checks(previous, base, helper)
