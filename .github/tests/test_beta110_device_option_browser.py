"""Render and operate the real device option on two controllers in one room."""
from copy import deepcopy
import os
from pathlib import Path
import runpy
import shutil

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = runpy.run_path(str(ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"))
CARD = ROOT / "frontend/air-quality-advisor-card.js"
SWITCH = "switch.native_full_output_"
CONTROLLER = "climate.managed_0_"
NAME = runpy.run_path(str(ROOT / "equipment_name_catalog.py"))["native_full_output_label"]
HELP = runpy.run_path(str(ROOT / "equipment_help.py"))["equipment_configuration_help"]


def states_for_test(language="en"):
    base = PREVIOUS["fixture_definitions"]()
    states = {}
    data = deepcopy(base["data"])
    data["rooms"] = data["rooms"][:1]
    data["rooms"][0].update(name="Living room", status="safe", windows=[])
    for i, label in enumerate(("Radiator", "Air conditioner", "Other controller")):
        physical = f"climate.physical_0_{i}"
        managed = CONTROLLER + str(i)
        for key in (managed, physical, f"sensor.control_0_{i}", f"select.control_0_{i}"):
            states[key] = deepcopy(base["states"][key])
        native_mode = "cool" if i == 1 else "heat"
        states[physical] = {"state": native_mode, "attributes": {
            "friendly_name": label, "hvac_modes": ["off", native_mode],
            "supported_features": 1, "min_temp": 5, "max_temp": 30,
            "temperature": 30 if i == 0 else 5, "current_temperature": 21.5}}
        attrs = states[managed]["attributes"]
        attrs.update(friendly_name=label, source_device_id=f"hardware{i}",
                     controller_status={"status": "controlling"},
                     requested_hvac_mode=native_mode, physical_source_state=native_mode)
        states[managed]["state"] = native_mode
        states[f"sensor.control_0_{i}"]["attributes"].update(
            source_device_id=f"hardware{i}", status_code="controlling", paused_reason=None,
            physical_entity_states={physical: native_mode})
        if i < 2:
            states[SWITCH + str(i)] = {"state": "on" if i else "off", "attributes": {
                "area_id": "room0", "source_device_id": f"hardware{i}",
                "source_entity_ids": [physical], "equipment_option_role": "policy",
                "setting_key": "native_full_output", "native_full_output_role": "policy",
                "native_full_output_supported": True, "native_full_output_modes": [native_mode],
                "setting_label": NAME([native_mode], language),
                "configuration_help": HELP("native_full_output", language, modes=[native_mode])}}
    states["sensor.hem"] = {"state": "ready", "attributes": {"dashboard": data}}
    return states


def run():
    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or shutil.which("chromium") or shutil.which("google-chrome")
    shots = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
    if shots:
        Path(shots).mkdir(exist_ok=True, parents=True)
    states = states_for_test()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 390, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content('<style>*{box-sizing:border-box}body{margin:0;background:#111;color:#eee;font:14px Arial}'
                         ':root{--primary-text-color:#eee;--secondary-text-color:#bbb;--primary-color:#03a9f4;'
                         '--card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}</style>')
        page.evaluate(PREVIOUS["icon_fixture"]())
        page.add_script_tag(path=str(CARD))
        page.evaluate("""(states) => {
          window.calls=[]; window.card=document.createElement('home-environment-manager-card');
          document.body.appendChild(card);
          card._hass={language:'en',states,localize:()=>undefined,
            callService:(...args)=>{calls.push(args);return Promise.resolve();}};
          card._config={entity:'sensor.hem'};
          card._roomsExpanded87=new Set(['room0']);
          card._devicesExpanded87=new Set([0,1,2].map(i=>'climate.managed_0_'+i));
          window.refresh110=(states,language='en')=>{
            card._hass={...card._hass, states:structuredClone(states), language};
            card._renderContent(true);
          };refresh110(states);
        }""", states)
        options = page.locator('[data-device-quick-switch8]')
        assert options.count() == 2
        assert page.locator('summary [data-device-quick-switch8]').count() == 0
        def option(i):
            return page.locator(f'[data-device-fold87="{CONTROLLER}{i}"] [data-device-quick-switch8]')
        for locale in ("en", "el", "de"):
            localized = states_for_test(locale)
            page.evaluate("([s,l])=>refresh110(s,l)", [localized, locale])
            for i, on in ((0, "false"), (1, "true")):
                control = option(i)
                assert control.count() == 1 and control.is_visible(), (locale, i)
                assert control.get_attribute("aria-checked") == on
                assert control.get_attribute("data-device-quick-switch8") == SWITCH + str(i)
                name = NAME(["cool" if i == 1 else "heat"], locale)
                assert control.get_attribute("aria-label") == name, (locale, name, control.get_attribute("aria-label"))
            if shots:
                page.locator(f'[data-device-fold87="{CONTROLLER}0"]').screenshot(
                    path=str(Path(shots) / f"device-option-{locale}.png"), animations="disabled")
        # Both controls are in the same room: service calls may address only
        # their own configuration switch. No native climate call is permitted.
        option(0).click()
        page.wait_for_function("calls.length===1")
        option(1).click()
        page.wait_for_function("calls.length===2")
        assert page.evaluate("calls") == [
            ["switch", "turn_on", {"entity_id": SWITCH+"0"}],
            ["switch", "turn_off", {"entity_id": SWITCH+"1"}],
        ]
        updated = deepcopy(states)
        updated[SWITCH+"0"]["state"] = "on"
        updated[SWITCH+"1"]["state"] = "off"
        page.evaluate("s=>refresh110(s)", updated)
        assert option(0).get_attribute("aria-checked") == "true"
        assert option(1).get_attribute("aria-checked") == "false"
        # Revalidate identity at click time rather than trusting a data attribute.
        option(0).evaluate("(e,id)=>{e.dataset.deviceQuickSwitch8=id;e.click();}", SWITCH+"1")
        assert page.evaluate("calls.length") == 2
        updated[SWITCH+"0"]["state"] = "unavailable"
        page.evaluate("s=>refresh110(s)", updated)
        assert option(0).is_disabled() or option(0).get_attribute("aria-disabled") == "true"
        assert option(1).is_enabled()
        updated[SWITCH+"0"]["state"] = "off"
        updated["switch.duplicate"] = deepcopy(updated[SWITCH+"0"])
        page.evaluate("s=>refresh110(s)", updated)
        assert option(0).count() == 0 and option(1).count() == 1
        assert not errors, errors
        browser.close()
    print("BETA110_REAL_CARD_LOCALIZED_DEVICE_SWITCH_AND_EXACT_SERVICE_ROUTING=PASS")


if __name__ == "__main__":
    run()
