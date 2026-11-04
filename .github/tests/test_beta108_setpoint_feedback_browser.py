"""Beta108: native temperature feedback remains distinct from pending intent.

Render production recovery-helper output in the actual card with Chromium.
The native device reports heat, 18.6 degrees measured, and a 5-degree target;
the room goal is 21 degrees and the pending native request is 30 degrees.
No Home Assistant service or physical device is contacted.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path
import re
import shutil
import sys
from types import ModuleType, SimpleNamespace

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = "climate.managed_0_0"
NATIVE = "climate.physical_0_0"
STATUS = "sensor.control_0_0"
RESUME = "button.resume_0_0"
NOW = 1793762000.0
LABELS = {
    "en": ("Temperature", "Target", "Physical device", "Heating", "Temperature setpoint"),
    "el": ("Θερμοκρασία", "Στόχος", "Φυσική συσκευή", "Θέρμανση", "Επιθυμητή θερμοκρασία"),
    "de": ("Temperatur", "Zielwert", "Physisches Gerät", "Heizen", "Temperatur-Sollwert"),
}


def fixture_definitions():
    """Load data builders without running any inherited browser test."""
    path = ROOT / ".github/tests/test_beta87_compact_browser.py"
    selected = []
    collecting = False
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef) and node.name == "row":
            collecting = True
        if collecting and isinstance(node, ast.With):
            break
        if collecting:
            selected.append(node)
    assert selected
    namespace = {}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def recovery_module():
    """Support the helper's relative imports without initializing HA."""
    name = "_hem_beta108_browser"
    package = ModuleType(name)
    package.__path__ = [str(ROOT)]
    sys.modules[name] = package
    spec = importlib.util.spec_from_file_location(
        name + ".equipment_resume", ROOT / "equipment_resume.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def icon_fixture():
    # Reuse only the literal icon stand-in from Beta107. Unregistered HA
    # icons have zero intrinsic width and give misleading review images.
    path = ROOT / ".github/tests/test_beta107_room_metrics.py"
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "ICON_FIXTURE"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("The HA icon geometry fixture is missing")


def fixture(base, helper, language, *, target_present=True, mode_only=False,
            manual_check=False, exhausted_target=False, resume_state="unknown"):
    keep = (CONTROLLER, NATIVE, STATUS, RESUME, "select.control_0_0")
    states = {entity: deepcopy(base["states"][entity]) for entity in keep}
    data = deepcopy(base["data"])
    room = data["rooms"][0]
    data["rooms"] = [room]
    data["summary"] = {"safe": 0, "attention": 1, "unknown": 0}
    room.update(name="Wohnzimmer", status="attention", action=None, windows=[])
    room["environment"]["climate_plan"].update(temperature_target_c=21.0)
    managed = states[CONTROLLER]
    managed["state"] = "heat"
    managed["attributes"].update(
        friendly_name="Wohnzimmer heating controller", control_mode="automatic",
        physical_source_state="heat", requested_hvac_mode="heat",
        temperature=21.0, current_temperature=18.6,
        measurements={"temperature": 18.6},
        controller_status={"status": "paused" if manual_check else "awaiting_physical_acknowledgement"},
    )
    states["select.control_0_0"]["state"] = "automatic"
    native_attrs = {
        "friendly_name": "Wohnzimmer thermostat", "temperature_unit": "°C",
        "current_temperature": 18.6, "temperature": 5.0,
        "min_temp": 5.0, "max_temp": 30.0,
        "hvac_modes": ["heat", "off"], "supported_features": 1,
    }
    if not target_present:
        native_attrs.pop("temperature")
    states[NATIVE] = {"state": "heat", "attributes": native_attrs}
    live = SimpleNamespace(
        state="heat", attributes=native_attrs,
        last_changed=datetime.fromtimestamp(NOW - 10, timezone.utc),
        last_updated=datetime.fromtimestamp(NOW - 10, timezone.utc),
        last_reported=datetime.fromtimestamp(NOW - 10, timezone.utc),
    )
    pending = {
        "entity": NATIVE, "phase": "commanded",
        "when": NOW - (400 if exhausted_target else 30),
        "attempts": 4 if exhausted_target else 1,
        "service": "set_hvac_mode" if mode_only else "set_temperature",
        "expected": {"state": "off"} if mode_only else {"attributes": {"temperature": 30.0}},
        "power": mode_only, "output_on": not mode_only,
    }
    recovery = helper.check_pending(
        pending, live, NOW, None, matches_expected=False,
        language=language, temperature_unit="°C",
    )
    # Ordinary pending and manual verification expose the same settling
    # countdown. The retained exhausted request is old and has no countdown.
    assert recovery["remaining_seconds"] == (None if exhausted_target else 90), recovery
    if exhausted_target:
        recovery.update(command_attempts=4, retry_limit_reached=True,
                        requires_user_repeated_check=False)
        recovery["instructions"] = helper.exhausted_target_message(recovery, language=language)
    elif manual_check:
        recovery["instructions"] = helper.instructions(recovery, language=language)
    else:
        recovery["requires_user_repeated_check"] = False
        recovery["instructions"] = helper.pending_feedback_message(recovery, language=language)
    states[STATUS]["attributes"].update(
        status_code="paused" if manual_check else "awaiting_physical_acknowledgement",
        paused_reason="native_command_failed_or_uncertain" if manual_check else None,
        command_pending=not exhausted_target, native_resume_recovery=recovery,
        physical_entity_states={NATIVE: "heat"},
    )
    states[RESUME]["state"] = resume_state
    states[RESUME]["attributes"].update(native_resume_recovery=recovery)
    states["sensor.hem"] = {"state": "ready", "attributes": {"dashboard": data}}
    return states, recovery


RENDER = """({states,language,controller}) => {
  window.calls=[];
  window.card=document.createElement('home-environment-manager-card');
  document.getElementById('card-frame').replaceChildren(card);
  card._hass={language,states,localize:()=>undefined,
    callService:(...args)=>{calls.push(args);return Promise.resolve()}};
  card._config={entity:'sensor.hem'};
  card._roomsExpanded87=new Set(['room0']);
  card._devicesExpanded87=new Set([controller]);
  card._renderContent(true);
}"""


def normalize(text):
    return " ".join(text.replace("\xa0", " ").split())


def assert_native_tiles(device, language, *, target_present):
    temperature, target, physical, heat, _ = LABELS[language]
    cells = device.locator('.hem-device-data > div').evaluate_all("""nodes =>
      nodes.map(node=>[node.querySelector('span').textContent,node.querySelector('b').textContent])""")
    values = {normalize(label): normalize(value) for label, value in cells}
    measured = "18.6 °C" if language == "en" else "18,6 °C"
    assert values[temperature] == measured, (language, values)
    assert values[physical] == heat, (language, values)
    target_label = target + " · " + temperature
    if target_present:
        assert values[target_label] == "5 °C", (language, values)
    else:
        assert target_label not in values, ("missing target fabricated", language, values)
    # Neither the logical room goal nor the pending setpoint is physical
    # feedback. The three native values must not be replaced with 21 or 30.
    assert not any(re.search(r"\b(?:21|30)(?:[.,]0)?\s*°C", value) for value in values.values()), values
    assert "temperature" not in values, ("raw untranslated temperature label", language, values)


def run():
    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
        shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome and Path(chrome).is_file(), "Chromium required (or set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH)"
    shots = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
    shots = Path(shots) if shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    base = fixture_definitions()
    helper = recovery_module()
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
        page.evaluate(icon_fixture())
        page.add_script_tag(path=str(ROOT / "frontend/air-quality-advisor-card.js"))
        for language in LABELS:
            for case in ("setpoint", "missing-target", "mode-only", "manual-check", "exhausted-target"):
                target_present = case != "missing-target"
                states, recovery = fixture(
                    base, helper, language, target_present=target_present,
                    mode_only=case == "mode-only", manual_check=case == "manual-check",
                    exhausted_target=case == "exhausted-target",
                )
                page.evaluate(RENDER, {"states": states, "language": language, "controller": CONTROLLER})
                device = page.locator(f'[data-device-fold87="{CONTROLLER}"]')
                panel = device.locator('.hem-resume-recovery')
                panel.wait_for(state="visible")
                # Save review artifacts before assertions so CI failures leave
                # the actual native values and comparison text inspectable.
                if shots and (case == "setpoint" or (
                    language == "el" and case in ("missing-target", "exhausted-target")
                )):
                    device.screenshot(path=str(shots / f"setpoint-feedback-{language}-{case}.png"))
                assert_native_tiles(device, language, target_present=target_present)
                comparison = normalize(panel.locator(':scope > small').first.inner_text())
                instructions = normalize(panel.locator(':scope > small').last.inner_text())
                assert normalize(recovery["requested"]) in comparison, (case, comparison, recovery)
                assert normalize(recovery["observed"]) in comparison, (case, comparison, recovery)
                assert instructions == normalize(recovery["instructions"]), (case, instructions, recovery)
                if case == "mode-only":
                    assert recovery["requested"] == "off" and recovery["observed"] == "heat", recovery
                    assert "°C" not in comparison, comparison
                else:
                    assert LABELS[language][4] in comparison, (language, comparison)
                    assert re.search(r"\b30(?:[.,]0)?\s*°C", recovery["requested"]), recovery
                    assert not re.search(r"\bheat\b", comparison), comparison
                    assert not re.search(r"\b18[.,]6\b", comparison), comparison
                    if target_present:
                        assert re.search(r"\b5(?:[.,]0)?\s*°C", recovery["observed"]), recovery
                        assert re.search(r"\b30(?:[.,]0)?\s*°C", instructions), instructions
                        assert re.search(r"\b5(?:[.,]0)?\s*°C", instructions), instructions
                    else:
                        assert recovery["observed"] and not re.search(r"\d", recovery["observed"]), recovery
                        assert any(token in recovery["observed"].casefold() for token in (
                            "unavailable", "μη διαθέσιμ", "nicht verfügbar")), recovery
                expected_lines = 3 if case == "manual-check" else 2
                assert panel.locator(':scope > small').count() == expected_lines, (
                    "manual-check countdown leaked into automatic pending", case, panel.inner_text())
                resume_button = device.locator('.hem-continue-auto89')
                assert resume_button.count() == 1
                assert resume_button.is_enabled() == (states[RESUME]["state"] != "unavailable")
                if case == "exhausted-target":
                    assert states[STATUS]["attributes"]["command_pending"] is False
                    assert recovery["retry_limit_reached"] is True
                    assert recovery["command_attempts"] == 4
                    assert recovery["requires_user_repeated_check"] is False
                    assert re.search(r"\b4\b", instructions), instructions
                    # Availability belongs to HA's resume entity. A retained
                    # target neither disables an available button nor enables
                    # one that the backend has marked unavailable.
                    page.evaluate("""entity => {
                      const states=structuredClone(card._hass.states);
                      states[entity].state='unavailable';
                      card._hass={...card._hass,states};card._renderContent(true);
                    }""", RESUME)
                    assert resume_button.is_disabled()
                    assert panel.is_visible()
                assert device.get_attribute("open") is not None
                assert page.locator('[data-room-fold87="room0"]').get_attribute("open") is not None
                assert page.evaluate("calls") == [], "rendering recovery sent a service command"
                assert not errors, errors
        browser.close()
    print("BETA108_NATIVE_SETPOINT_FEEDBACK_TYPED_LOCALIZED_NO_MANUAL_COUNTDOWN=PASS")


if __name__ == "__main__":
    run()
