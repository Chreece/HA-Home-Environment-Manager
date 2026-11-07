"""Announcement language menus exercise production forms and settings writes.

HA transport and form widgets are replaced; language validation, dropdown
contents, entity identity, draft validation and persistence are production code.
No equipment services are provided by these fixtures.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
import importlib
import json
import math
from pathlib import Path
from string import Formatter
import sys
from types import ModuleType, SimpleNamespace as N
from typing import Any
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem061b5languagesettings"
package = ModuleType(PKG)
package.__path__ = [str(ROOT)]
sys.modules[PKG] = package
const = importlib.import_module(PKG + ".const")
languages = importlib.import_module(PKG + ".languages")
tts = importlib.import_module(PKG + ".tts_languages")
metadata = importlib.import_module(PKG + ".settings_help")


def stub(name, **values):
    result = ModuleType(PKG + "." + name)
    result.__dict__.update(values)
    sys.modules[result.__name__] = result


stub("ai_rewrite", DEFAULT_AGENT="none")
stub("hub_delivery", hub_installed=lambda hass: False)
stub("discovery", is_pressure_sensor=lambda hass, entity: False)
stub("arrival_preparation", CONF_TIMEOUT="arrival_preparation_timeout_minutes",
     MIN_TIMEOUT=1, MAX_TIMEOUT=240)


def production(filename, names, namespace, owner=None):
    body = ast.parse((ROOT / filename).read_text()).body
    if owner:
        body = next(node for node in body
                    if isinstance(node, ast.ClassDef) and node.name == owner).body
    selected = [node for node in body if isinstance(
        node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    assert len(selected) == len(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), filename, "exec"), namespace)


class Marker(str):
    def __new__(cls, name, default=None, **kwargs):
        value = super().__new__(cls, name)
        value.default = default
        value.schema = name
        return value


class Selectors:
    SelectSelectorMode = N(DROPDOWN="dropdown")
    NumberSelectorMode = N(BOX="box")

    def __getattr__(self, name):
        if name.endswith("Config"):
            return lambda **config: config
        return lambda config=None: N(config=config or {}, kind=name)


class Entity:
    def __init__(self):
        self.removers = []

    async def async_added_to_hass(self):
        self.removers = []

    def async_on_remove(self, remover):
        self.removers.append(remover)

    def async_write_ha_state(self):
        self.writes = getattr(self, "writes", 0) + 1

    @property
    def extra_state_attributes(self):
        return {}


def connect(hass, signal, callback):
    hass.listeners[signal] = callback
    return lambda: hass.listeners.pop(signal, None)


ns = {**vars(const), "__name__": PKG + ".production", "__package__": PKG,
      "Any": Any, "asyncio": asyncio, "deepcopy": deepcopy, "math": math,
      "HomeAssistantError": ValueError, "ConfigFlowResult": dict,
      "probatio": N(Optional=Marker, Schema=lambda value: value),
      "selector": Selectors(), "_marker": Marker,
      "SUPPORTED_LANGUAGE_TAGS": languages.SUPPORTED_LANGUAGE_TAGS,
      "normalize_announcement_language": languages.normalize_announcement_language,
      "DEFAULT_AGENT": "none", "hub_installed": lambda hass: False,
      "conversation_agent_choices": lambda hass, saved: [{"value": "none"}],
      "_tts_player_options": lambda hass: [],
      "SettingsMetadata": metadata.SettingsMetadata, "SelectEntity": Entity,
      "EntityCategory": N(CONFIG="config"), "callback": lambda method: method,
      "async_dispatcher_connect": connect}
production("device_controls.py", {"update_device_setting"}, ns)
production("room_setup.py", {"field", "select"}, ns)
production("room_setup.py", {"async_step_setup_general"}, ns, "RoomSetupMixin")
delivery_tree = ast.parse((ROOT / "config_flow.py").read_text())
delivery_owner = next(node.name for node in delivery_tree.body
                      if isinstance(node, ast.ClassDef) and any(
                          getattr(item, "name", "") == "async_step_delivery" for item in node.body))
production("config_flow.py", {"async_step_delivery"}, ns, delivery_owner)
production("select.py", {"TTSLanguageSelect"}, ns)


class States:
    def __init__(self):
        self.items = {"tts.greek": N(attributes={"supported_languages": ["el"],
                                               "default_language": "el"})}

    def get(self, entity):
        return self.items.get(entity)

    def async_all(self, domain):
        return [state for entity, state in self.items.items()
                if entity.startswith(domain + ".")]


class GeneralFlow:
    async_step_setup_general = ns["async_step_setup_general"]
    async_step_delivery = ns["async_step_delivery"]

    def __init__(self, **saved):
        self._values = deepcopy(saved)
        self._setup_order = []
        self._setup_index = 0
        self.saved = 0
        self.hass = N(states=States(), config=N(language="el"),
                      services=N(has_service=lambda *args: False))

    def _general_options(self):
        result = {key: [] for key in (
            const.CONF_WEATHER, const.CONF_OUTDOOR, const.CONF_WARNINGS,
            const.CONF_NOTIFY_TARGETS, const.CONF_MEDIA_PLAYERS,
            "general_room_occupancy_sensors", "general_home_trackers",
            "pollen_entities", const.CONF_AWAY_WINDOWS_PERSONS)}
        result.update({
            const.CONF_TTS_ENGINE: [{"value": "none"}, {"value": "tts.greek"}],
            const.CONF_AI_AGENT: [{"value": "none"}],
            const.CONF_AWAY_WINDOWS_DELIVERY: [{"value": "mobile_notification"}],
            **{key: [{"value": "none"}] for key in (
                "general_occupied_rooms_entity", "general_sleep_rooms_entity",
                "general_wake_alarm_entity", "general_wake_lead_minutes_entity")},
        })
        return result

    def _room_attribute_options(self, hass, entity):
        return [{"value": "__state__"}]

    def async_show_form(self, **values):
        return values

    async def _finish(self):
        self.saved += 1
        return {"saved": deepcopy(self._values)}


class Manager:
    _active = False

    def __init__(self, **saved):
        self.entry = N(entry_id="existing_entry", data={"keep": {"room": "unchanged"}},
                       options={"tts_engine": "tts.greek", **saved})
        self.saved = []
        self.hass = N(config=N(language="en"), states=States(), listeners={},
                      config_entries=N(async_update_entry=self.save))

    @property
    def settings(self):
        return {**self.entry.data, **self.entry.options}

    def save(self, entry, *, options):
        self.saved.append(deepcopy(options))
        entry.options = deepcopy(options)


def language_field(form):
    marker = next(key for key in form["data_schema"] if key == "language")
    return marker, form["data_schema"][marker].config


class AnnouncementLanguageSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def test_general_and_setup_offer_auto_and_all_supported_languages(self):
        expected = ["auto", *(tag.lower() for tag in languages.SUPPORTED_LANGUAGE_TAGS)]
        self.assertEqual(len(expected), 39)
        for step in ("async_step_setup_general", "async_step_delivery"):
            for engine in (None, "tts.greek"):
                with self.subTest(step=step, engine=engine):
                    flow = GeneralFlow(tts_engine=engine)
                    before = deepcopy(flow._values)
                    form = await getattr(flow, step)()
                    marker, config = language_field(form)
                    self.assertEqual(marker.default, "auto")
                    self.assertEqual(config["options"], expected)
                    self.assertEqual(config["translation_key"], "output_language")
                    self.assertEqual(config["mode"], "dropdown")
                    self.assertEqual(flow._values, before)

    async def test_provider_change_never_replaces_saved_announcement_language(self):
        for engine in ("none", "tts.greek"):
            flow = GeneralFlow(language="fr", tts_engine="tts.greek")
            result = await flow.async_step_setup_general({"tts_engine": engine})
            self.assertEqual(result["saved"]["language"], "fr")
            self.assertEqual(flow.saved, 1)

    async def test_existing_delivery_menu_exposes_language_without_other_native_settings(self):
        flow = GeneralFlow(language="pt-BR", tts_engine="tts.greek")
        flow._menu_mode = True
        form = await flow.async_step_delivery()
        marker, config = language_field(form)
        self.assertEqual(marker.default, "pt-br")
        self.assertEqual(len(config["options"]), 39)
        self.assertEqual(config["translation_key"], "output_language")
        for hidden in (const.CONF_AUTO_NOTIFY, const.CONF_AUTO_TTS,
                       const.CONF_REPEAT_MINUTES, const.CONF_AI_REWRITE, const.CONF_HUB):
            self.assertNotIn(hidden, form["data_schema"])
        result = await flow.async_step_delivery({"language": "zh-hant"})
        self.assertEqual(result["saved"]["language"], "zh-Hant")

    async def test_canonical_and_legacy_tags_round_trip_through_both_forms(self):
        for step in ("async_step_setup_general", "async_step_delivery"):
            for original, expected in (("pt_br", "pt-BR"), ("zh-TW", "zh-Hant"),
                                       ("ZH_hans", "zh-Hans"), ("en_GB", "en"),
                                       ("no-NO", "nb"), ("auto", "auto")):
                with self.subTest(step=step, language=original):
                    flow = GeneralFlow(language=original)
                    marker, _ = language_field(await getattr(flow, step)())
                    self.assertEqual(marker.default, expected.lower())
                    result = await getattr(flow, step)({"language": expected.lower()})
                    self.assertEqual(result["saved"]["language"], original)
                    flow = GeneralFlow(language="fr")
                    result = await getattr(flow, step)({"language": original})
                    self.assertEqual(result["saved"]["language"], expected)

    async def test_unrelated_form_saves_preserve_existing_regional_voice_selection(self):
        for step in ("async_step_setup_general", "async_step_delivery"):
            for original in ("en_GB", "de-DE", "pt_br", "zh-TW"):
                with self.subTest(step=step, language=original):
                    flow = GeneralFlow(language=original, tts_engine="tts.greek")
                    result = await getattr(flow, step)({"tts_engine": "none"})
                    self.assertEqual(result["saved"]["language"], original)

    async def test_invalid_language_reports_error_without_saving_or_coercion(self):
        for step in ("async_step_setup_general", "async_step_delivery"):
            for invalid in ("zz", "English", "", None, False, ["en"]):
                with self.subTest(step=step, invalid=invalid):
                    flow = GeneralFlow(language="fr")
                    before = deepcopy(flow._values)
                    form = await getattr(flow, step)({"language": invalid})
                    self.assertEqual(form["errors"]["language"], "invalid_room_source")
                    self.assertEqual(flow.saved, 0)
                    self.assertEqual(flow._values, before)

    async def test_native_selector_keeps_identity_and_persists_all_choices(self):
        manager = Manager()
        entity = ns["TTSLanguageSelect"](manager, manager.entry.entry_id)
        self.assertEqual(entity._attr_unique_id, "existing_entry_home_language")
        self.assertEqual(entity._attr_translation_key, "home_language")
        self.assertEqual(entity.options[0], "Home Assistant language (default)")
        self.assertEqual(entity.current_option, entity.options[0])
        self.assertEqual(len(entity.options), 39)
        self.assertEqual(set(entity.options[1:]), set(languages.NATIVE_NAMES.values()))
        for choice in tts.announcement_language_options(manager.hass):
            await entity.async_select_option(choice["label"])
            self.assertEqual(manager.settings["language"], choice["value"])
            self.assertEqual(entity.current_option, choice["label"])
            self.assertEqual(manager.settings["keep"], {"room": "unchanged"})
            self.assertEqual(manager.settings["tts_engine"], "tts.greek")
        before = deepcopy(manager.settings)
        with self.assertRaises(ValueError):
            await entity.async_select_option("Unknown language")
        self.assertEqual(manager.settings, before)

    async def test_native_setting_writer_validates_and_normalizes_without_provider(self):
        manager = Manager(language="fr")
        writer = ns["update_device_setting"]
        for invalid in ("zz", "", None, False, {"language": "en"}):
            with self.assertRaises(ValueError):
                await writer(manager, "global_setting", "language", invalid)
        self.assertEqual(manager.saved, [])
        await writer(manager, "global_setting", "language", "pt_br")
        self.assertEqual(manager.settings["language"], "pt-BR")
        await writer(manager, "global_setting", "language", "auto")
        self.assertEqual(manager.settings["language"], "auto")

    async def test_native_selector_refreshes_when_general_settings_change(self):
        manager = Manager(language="en")
        entity = ns["TTSLanguageSelect"](manager, manager.entry.entry_id)
        entity.hass = manager.hass
        await entity.async_added_to_hass()
        signal = f"{const.SIGNAL_UPDATED}_{manager.entry.entry_id}"
        self.assertIn(signal, manager.hass.listeners)
        manager.entry.options["language"] = "zh-Hant"
        manager.hass.listeners[signal]()
        self.assertEqual(entity.writes, 1)
        self.assertEqual(entity.current_option, languages.NATIVE_NAMES["zh-Hant"])
        entity.removers[0]()
        self.assertNotIn(signal, manager.hass.listeners)

    def test_translated_menu_labels_and_native_default_agree_for_every_locale(self):
        expected = {"auto", *(tag.lower() for tag in languages.SUPPORTED_LANGUAGE_TAGS)}
        for tag in languages.SUPPORTED_LANGUAGE_TAGS:
            catalog = json.loads((ROOT / "translations" / f"{tag}.json").read_text())
            choices = catalog["selector"]["output_language"]["options"]
            self.assertEqual(set(choices), expected)
            hass = N(config=N(language=tag))
            self.assertEqual(tts.announcement_language_options(hass)[0]["label"], choices["auto"])
            for section in ("config", "options"):
                general = catalog[section]["step"]["setup_general"]
                delivery = catalog[section]["step"]["delivery"]
                self.assertEqual(general["data"]["language"], delivery["data"]["language"])
                self.assertIn("HEM", general["data_description"]["language"])
                self.assertNotIn("TTS", general["data"]["language"])
        english = json.loads((ROOT / "strings.json").read_text())
        translated_english = json.loads((ROOT / "translations/en.json").read_text())
        self.assertEqual(english["selector"]["output_language"],
                         translated_english["selector"]["output_language"])
        for section in ("config", "options"):
            for step in ("setup_general", "delivery"):
                for field in ("data", "data_description"):
                    self.assertEqual(english[section]["step"][step][field]["language"],
                                     translated_english[section]["step"][step][field]["language"])
        self.assertEqual(english["config"]["step"]["setup_general"]["data"]["language"],
                         "Announcement language")


class SpokenRecommendationLanguageTests(unittest.TestCase):
    def test_every_announced_locale_has_complete_templates_and_matching_placeholders(self):
        messages = importlib.import_module(PKG + ".messages")
        extra = importlib.import_module(PKG + ".recommendation_text")
        supported = set(languages.SUPPORTED_LANGUAGE_TAGS)
        self.assertEqual(set(messages.ROOM_VENTILATION_TEXT), supported)
        self.assertEqual(set(extra.ROOM_VENTILATION_TEXT), supported - {"en", "de", "el"})
        self.assertEqual(set(extra.CLIMATE_WINDOW_TEXT), supported - {"en", "de", "el"})
        room_keys = set(messages.ROOM_VENTILATION_TEXT["en"])
        climate_keys = {"title_climate_window", "climate_window_cool",
                        "climate_window_heat", "climate_window_dry"}
        fields = lambda text: [name for _, name, _, _ in Formatter().parse(text)
                               if name is not None]
        for tag in supported:
            with self.subTest(language=tag):
                self.assertEqual(set(messages.ROOM_VENTILATION_TEXT[tag]), room_keys)
                for key in room_keys | climate_keys:
                    table = messages.ROOM_VENTILATION_TEXT if key in room_keys else messages.TEXT
                    template = table[tag][key]
                    self.assertEqual(sorted(fields(template)), sorted(fields(table["en"][key])))
                    self.assertNotIn("{", template.format(
                        area="ROOM", windows="WINDOW", value="VALUE"))
                    if tag not in ("en", "de", "el"):
                        self.assertNotEqual(template, table["en"][key])

    def test_all_primary_reminders_and_climate_opportunities_use_selected_language(self):
        messages = importlib.import_module(PKG + ".messages")
        logic = importlib.import_module(PKG + ".logic")
        room_cases = {
            "air_refresh_wake": ("refresh_title", "wake"),
            "air_refresh_return": ("refresh_title", "return"),
            "window_heat_loss": ("heat_title", "heat"),
            "window_cooling_loss": ("cool_title", "cool"),
        }
        for tag in languages.SUPPORTED_LANGUAGE_TAGS:
            for code in (*room_cases, "climate_window_cool", "climate_window_heat", "climate_window_dry"):
                with self.subTest(language=tag, code=code):
                    reason = logic.Reason(code, value="DELTA_VALUE")
                    rec = logic.Recommendation(
                        "close" if code.startswith("window_") else "open",
                        "room", "ROOM_NAME", (logic.Window("binary_sensor.window", "WINDOW_NAME", True),),
                        (reason,),
                    )
                    title, body = messages.announcement(rec, tag)
                    self.assertIn("ROOM_NAME", body)
                    if code in room_cases:
                        title_key, message_key = room_cases[code]
                        templates = messages.ROOM_VENTILATION_TEXT[tag]
                        self.assertEqual(title, templates[title_key])
                        self.assertEqual(body, templates[message_key].format(
                            area="ROOM_NAME", windows="WINDOW_NAME", value="DELTA_VALUE"))
                    else:
                        self.assertEqual(title, messages.TEXT[tag]["title_climate_window"])
                        self.assertIn(messages.TEXT[tag][code].format(value="DELTA_VALUE"), body)
                    if not code.startswith("air_refresh_"):
                        if rec.action == "close":
                            self.assertIn("WINDOW_NAME", body)
                        else:
                            self.assertNotIn("WINDOW_NAME", body)
                        self.assertIn("DELTA_VALUE", body)


if __name__ == "__main__":
    unittest.main()
