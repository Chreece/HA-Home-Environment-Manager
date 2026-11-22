"""The global close-advice cooldown uses one bounded, localized setting.

Execute production Options forms, native number properties, validated writes
and card alias/locale helpers with Home Assistant transport replaced by fixtures.
The test reads canonical integration paths without legacy root symlinks.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
fixture_path = ROOT / ".github/tests/test_061b5_language_settings.py"
fixture = ModuleType("hem_close_cooldown_settings_fixture")
fixture.__file__ = str(fixture_path)
fixture_tree = ast.parse(fixture_path.read_text())
root_node = next(node for node in fixture_tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "ROOT"
                         for target in node.targets))
root_node.value = ast.Call(func=ast.Name(id="Path", ctx=ast.Load()),
                          args=[ast.Constant(str(SOURCE))], keywords=[])
sys.modules[fixture.__name__] = fixture
exec(compile(ast.fix_missing_locations(fixture_tree), str(fixture_path), "exec"), fixture.__dict__)
fixture.Entity.async_write_ha_state = lambda self: None
fixture.production("device_controls.py", {"_finite"}, fixture.ns)
fixture.ns.update(NumberEntity=fixture.Entity, NumberMode=N(BOX="box"))
fixture.production("number.py", {"ConfigNumber"}, fixture.ns)
ConfigNumber = fixture.ns["ConfigNumber"]
const = fixture.const
text = importlib.import_module(fixture.PKG + ".window_close_cooldown_text").WINDOW_CLOSE_COOLDOWN_TEXT
names = importlib.import_module(fixture.PKG + ".settings_name_catalog")
KEY = const.CONF_WINDOW_CLOSE_COOLDOWN_MINUTES
NATIVE_KEY = "global_setting_" + KEY
OPEN_KEY = const.CONF_WINDOW_OPEN_TIMEOUT_MINUTES


class CloseCooldownSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def test_general_default_and_whole_minute_values_round_trip_independently(self):
        flow = fixture.GeneralFlow(language="el", **{OPEN_KEY: 17})
        before = deepcopy(flow._values)
        form = await flow.async_step_setup_general()
        marker = next(field for field in form["data_schema"] if field == KEY)
        self.assertEqual(marker.default, 5)
        config = form["data_schema"][marker].config
        self.assertEqual((config["min"], config["max"], config["step"],
                          config["unit_of_measurement"]), (0, 60, 1, "min"))
        self.assertEqual(flow._values, before)
        for minutes in (0, 1, 5, 30, 60):
            result = await flow.async_step_setup_general({KEY: minutes})
            self.assertEqual(result["saved"][KEY], minutes)
            self.assertIs(type(result["saved"][KEY]), int)
            self.assertEqual(result["saved"][OPEN_KEY], 17)
            self.assertEqual(result["saved"]["language"], "el")

    async def test_invalid_form_and_native_values_cannot_save_or_target_a_room(self):
        manager = fixture.Manager(**{KEY: 5, OPEN_KEY: 17})
        for invalid in (-1, 61, 2.5, True, None, "invalid", float("nan"), float("inf")):
            with self.subTest(value=invalid):
                flow = fixture.GeneralFlow(**{KEY: 5, OPEN_KEY: 17})
                before = deepcopy(flow._values)
                form = await flow.async_step_setup_general({KEY: invalid})
                self.assertEqual(form["errors"][KEY], "invalid_room_source")
                self.assertEqual(flow._values, before)
                self.assertEqual(flow.saved, 0)
                with self.assertRaises(ValueError):
                    await fixture.ns["update_device_setting"](manager, "global_setting", KEY, invalid)
        with self.assertRaises(ValueError):
            await fixture.ns["update_device_setting"](manager, "global_setting", KEY, 12, area="other")
        self.assertEqual(manager.saved, [])

    async def test_native_number_default_identity_fallback_and_same_property_writes(self):
        manager = fixture.Manager(language="de", **{OPEN_KEY: 17})
        number = ConfigNumber(manager, manager.entry.entry_id, None, "global_setting",
                              KEY, (0, 60, 1, "min"))
        self.assertEqual(number.native_value, 5)
        self.assertEqual(number._attr_unique_id, "existing_entry_home_" + NATIVE_KEY)
        self.assertEqual(number._attr_native_unit_of_measurement, "min")
        for minutes in (0, 12, 60):
            await number.async_set_native_value(minutes)
            self.assertEqual(number.native_value, minutes)
            self.assertEqual(manager.settings[KEY], minutes)
            self.assertEqual(manager.settings[OPEN_KEY], 17)
            self.assertEqual(manager.settings["keep"], {"room": "unchanged"})
        for invalid in (None, True, -1, 61, 0.5, float("nan"), "bad"):
            manager.entry.options[KEY] = invalid
            self.assertEqual(number.native_value, 5)

    def test_native_and_both_form_catalogs_share_all_38_complete_explanations(self):
        self.assertEqual(set(text), set(fixture.languages.SUPPORTED_LANGUAGE_TAGS))
        self.assertEqual(len(text), 38)
        manager = fixture.Manager()
        number = ConfigNumber(manager, manager.entry.entry_id, None, "global_setting",
                              KEY, (0, 60, 1, "min"))
        for locale, values in text.items():
            with self.subTest(locale=locale):
                manager.hass.config.language = locale
                catalog = json.loads((SOURCE / "translations" / (locale + ".json")).read_text())
                self.assertEqual(number.name, catalog["entity"]["number"][NATIVE_KEY]["name"])
                self.assertEqual(number.name, names.localized_setting_name(NATIVE_KEY, locale))
                self.assertEqual(number.extra_state_attributes["configuration_help"], values["help"])
                for kind in ("config", "options"):
                    general = catalog[kind]["step"]["setup_general"]
                    self.assertEqual(general["data"][KEY], values["label"])
                    self.assertEqual(general["data_description"][KEY], values["help"])
                for token in ("HEM", "0–60", "5", "0"):
                    self.assertIn(token, values["help"])

    def test_card_basic_visibility_exact_alias_and_independent_viewer_language(self):
        catalog = {locale: {**values, "native": names.localized_setting_name(NATIVE_KEY, locale)}
                   for locale, values in text.items()}
        node = shutil.which("node")
        self.assertIsNotNone(node)
        subprocess.run([node, "-", str(SOURCE / "frontend/home-environment-manager-card.js"),
                        json.dumps(catalog, ensure_ascii=False)], input=NODE,
                       text=True, check=True)


NODE = r"""
const assert=require('node:assert/strict'),fs=require('node:fs');
const source=fs.readFileSync(process.argv[2],'utf8'),catalog=JSON.parse(process.argv[3]);
const localeStart=source.indexOf('  /* HEM_TRANSLATION_DATA_B8_START */');
const localeEnd=source.indexOf('  const BRAND_TITLE =',localeStart);
const policyStart=source.indexOf('  const auditPolicyB8=');
const policyEnd=source.indexOf('  const auditProto=',policyStart);
const aliasStart=source.indexOf('  const auditFieldsBefore=');
const aliasEnd=source.indexOf('  const auditRowBefore=',aliasStart);
assert(localeStart>0&&localeEnd>localeStart&&policyStart>0&&policyEnd>policyStart);
assert(aliasStart>0&&aliasEnd>aliasStart);
const key='window_close_cooldown_minutes',native='global_setting_'+key;
const make=(id,k)=>({id,label:k,domain:'number',reg:{translation_key:k},state:{state:'5',attributes:{}}});
const fields=[make('number.renamed_close_wait',native),
 make('number.open_wait','global_setting_window_open_timeout_minutes')];
const proto={_hemFullFields127:()=>fields};
const api=new Function('auditProto',source.slice(localeStart,localeEnd)+source.slice(policyStart,policyEnd)+
 source.slice(aliasStart,aliasEnd)+'\nreturn {hemTextB8,auditPolicyB8,auditVisibleB8};')(proto);
assert.equal(api.auditPolicyB8.native_levels[native],'basic');
assert.equal(api.auditPolicyB8.home_option_levels[key],'basic');
assert(api.auditVisibleB8({settingsAudit:{level:'basic',query:''}},fields[0]));
const saved={fields:[{name:key,kind:'number'}]};
assert.deepEqual(proto._hemFullFields127(saved,'home'),[fields[1]],'one global editor');
assert.deepEqual(proto._hemFullFields127(saved,'room'),fields,'never hide room settings');
assert.deepEqual(proto._hemFullFields127({...saved,unsupported:true},'home'),fields,'keep native fallback');
for(const phase of ['dirty','pending','saving','failed'])
 assert.deepEqual(proto._hemFullFields127({...saved,nativeEdits:new Map([[fields[0].id,{phase}]])},'home'),fields);
for(const [locale,values] of Object.entries(catalog))
 for(const field of ['label','help','native'])
  assert.equal(api.hemTextB8(catalog.en[field],locale),values[field],locale+' '+field);
console.log('PASS: one Basic home editor, pending native edits and all 38 viewer locales');
"""


def browser_checks():
    """Render the production Home menu and save through its Options transport."""
    from playwright.sync_api import expect, sync_playwright

    chrome = (os.getenv("CHROME_BIN") or os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
              or shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome, "Chromium is required for --with-browser"
    room = runpy.run_path(str(ROOT / ".github/tests/test_beta114_room_settings.py"))
    base = runpy.run_path(str(ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"))
    tree = ast.parse((ROOT / ".github/tests/test_062b7_autosave.py").read_text())
    setup = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "SETUP"
                         for target in node.targets))
    form = asyncio.run(fixture.GeneralFlow().async_step_setup_general())
    marker = next(field for field in form["data_schema"] if field == KEY)
    schema = {"name": KEY, "default": marker.default,
              "selector": {"number": form["data_schema"][marker].config}}
    states = deepcopy(base["fixture_definitions"]()["states"])
    states["sensor.hem"]["attributes"]["dashboard"]["rooms"] = (
        states["sensor.hem"]["attributes"]["dashboard"]["rooms"][:2])
    body = ('<style>body{margin:0;background:#161616;color:#eee;font:14px Arial;'
            '--card-background-color:#222;--primary-text-color:#eee;'
            '--secondary-text-color:#aaa}</style>')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome, headless=True,
                                    args=["--no-sandbox", "--disable-dev-shm-usage"])
        for language, width in (("en", 760), ("el", 320), ("de", 390)):
            context = browser.new_context(viewport={"width": width, "height": 950})
            context.route("https://hem-window-cooldown.test/**", lambda route: route.fulfill(
                status=200, content_type="text/html", body=body))
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("https://hem-window-cooldown.test/settings")
            page.evaluate(base["icon_fixture"]())
            page.add_script_tag(path=str(SOURCE / "frontend/home-environment-manager-card.js"))
            page.evaluate(room["SETUP"], {"states": states, "form": room["FORM"], "native": False})
            page.evaluate("form=>window.roomSchema=form", room["FORM"])
            page.evaluate(setup)
            catalog = json.loads((SOURCE / "translations" / (language + ".json")).read_text())
            page.evaluate(r"""({language,catalog,schema,key,nativeKey,openKey})=>{
              card._hass.language=language;card._hass.user={id:'cooldown-viewer',is_admin:true};
              card._hass.localize=key=>{
                const prefix='component.environment_manager.';
                return key.startsWith(prefix)?key.slice(prefix.length).split('.')
                  .reduce((value,part)=>value?.[part],catalog):undefined;
              };
              homeForm.data_schema.push(schema,{name:openKey,default:17,
                selector:{number:{min:0,max:30,step:1,unit_of_measurement:'min'}}});
              homeData[key]=schema.default;homeData[openKey]=17;
              const id='number.renamed_window_close_wait';
              card._hass.states[id]={state:String(schema.default),attributes:{
                min:0,max:60,step:1,unit_of_measurement:'min',
                friendly_name:catalog.entity.number[nativeKey].name,
                configuration_help:catalog.options.step.setup_general.data_description[key]}};
              registry.push({entity_id:id,translation_key:nativeKey,device_id:'homehub',
                unique_id:'entry0_home_'+nativeKey,platform:'environment_manager',
                config_entry_id:'entry0'});
              card._hass={...card._hass,states:{...card._hass.states}};
              card._renderContent(true);
            }""", {"language": language, "catalog": catalog, "schema": schema,
                   "key": KEY, "nativeKey": NATIVE_KEY, "openKey": OPEN_KEY})
            assert page.evaluate("card._openHomeSettings128()")
            page.wait_for_function("card._homeSettingsDialog128?.fields?.length===6 && "
                                   "card._homeSettingsDialog128?.fullRegistry127?.length===registry.length")
            dialog = page.locator("dialog.hem-home-options128")
            expect(dialog.locator("[data-settings-level-b8]")).to_have_value("basic")
            row = dialog.locator(f'[data-hem-home-field128="{KEY}"]')
            expect(row).to_have_count(1)
            assert row.evaluate("node=>node.closest('[data-hem-unified141]')"
                                ".getAttribute('data-hem-unified141')") == "ventilation"
            page.evaluate("card._homeSettingsDialog128.node.querySelectorAll('details')"
                          ".forEach(node=>node.open=true)")
            expect(row).to_be_visible()
            expect(dialog.locator('[data-hem-full-row127="number.renamed_window_close_wait"]')).to_have_count(0)
            control = row.locator(f'[data-hem-home-input128="{KEY}"]')
            expect(control).to_have_count(1)
            expect(control).to_have_value("5")
            for attr, value in (("min", "0"), ("max", "60"), ("step", "1")):
                expect(control).to_have_attribute(attr, value)
            expect(row).to_contain_text(text[language]["label"])
            before = page.evaluate("JSON.stringify({writes,optionWrites,homeData,committed})")
            button = row.locator("[data-setting-info-b9]")
            assert button.get_attribute("aria-label")
            panel = row.locator("[data-setting-help-b9]")
            expect(panel).to_have_attribute("id", button.get_attribute("aria-controls"))
            expect(panel).to_be_hidden()
            button.focus()
            page.keyboard.press("Enter")
            expect(button).to_have_attribute("aria-expanded", "true")
            expect(panel).to_be_visible()
            expect(panel).to_contain_text(text[language]["help"])
            for target in (dialog, row, panel):
                assert target.evaluate("node=>node.scrollWidth<=node.clientWidth+1"), (language, width)
            page.keyboard.press("Escape")
            expect(panel).to_be_hidden()
            expect(dialog).to_be_visible()
            assert page.evaluate("JSON.stringify({writes,optionWrites,homeData,committed})") == before
            room_before = page.evaluate("JSON.stringify(committed)")
            for minutes in (0, 12):
                control.fill(str(minutes))
                control.dispatch_event("change")
                page.wait_for_function("({key,minutes})=>homeData[key]===minutes",
                                       arg={"key": KEY, "minutes": minutes})
                expect(control).to_have_value(str(minutes))
                saved = page.evaluate("optionWrites.at(-1)")
                assert saved[KEY] == minutes
                assert saved[OPEN_KEY] == 17
                assert saved["general_away_cooldown_minutes"] == 10
                assert page.evaluate("JSON.stringify(committed)") == room_before
                assert page.evaluate("writes.length") == 0
                expect(dialog.locator('[data-hem-full-row127="number.renamed_window_close_wait"]')).to_have_count(0)
            assert page.evaluate("calls.filter(call=>call.data?.next_step_id)"
                                 ".every(call=>call.data.next_step_id==='general_settings')")
            assert page.evaluate("optionWrites.length") == 2
            assert not errors, errors
            context.close()
        browser.close()
    print("PASS: one Basic Home ventilation editor; default 5; global saves 0/12; "
          "independent opening timeout; keyboard help and EN/EL/DE layout at 320/390/760px")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-browser", action="store_true")
    args = parser.parse_args()
    result = unittest.main(argv=[sys.argv[0]], verbosity=2, exit=False).result
    if not result.wasSuccessful():
        sys.exit(1)
    if args.with_browser:
        browser_checks()
