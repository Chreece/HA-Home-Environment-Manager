"""v0.6.1b5: one saved announcement language across text, Hub, AI and speech.

Run real delivery functions with simulated HA transport. Provider capabilities
must not change configuration choices or select a different spoken language.
No services outside this fixture are contacted.
"""
from __future__ import annotations

import ast
import importlib
import logging
from pathlib import Path
import string
import sys
from types import ModuleType, SimpleNamespace as N
from typing import Any
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem_061b5_announcement_fixture"
package = ModuleType(PKG)
package.__path__ = [str(ROOT)]
sys.modules[PKG] = package


def stub(name: str, **values: Any) -> ModuleType:
    module = ModuleType(name)
    module.__dict__.update(values)
    sys.modules[name] = module
    return module


# Registry identity and provider entity capabilities are the real access paths.
ha = stub("homeassistant", __path__=[])
helpers = stub("homeassistant.helpers", __path__=[])
area_registry = stub("homeassistant.helpers.area_registry", async_get=lambda hass: N(
    async_get_area=lambda area: N(name=hass.room_name) if area == "room" else None))
entity_registry = stub("homeassistant.helpers.entity_registry", async_get=lambda hass: N(
    async_get=lambda entity: N(platform="mobile_app", disabled_by=None)
    if entity == "notify.phone" else None))
helpers.area_registry = area_registry
helpers.entity_registry = entity_registry
ha.helpers = helpers
stub("homeassistant.components", __path__=[])
stub("homeassistant.components.tts", __path__=[])
stub("homeassistant.components.tts.const", DATA_COMPONENT="tts_component")

stub(PKG + ".discovery", entity_area=lambda hass, entity: None, is_window=lambda *args: True)
stub(PKG + ".occupancy_policy", _bool_presence=lambda value: False,
     home_presence=lambda *args, **kwargs: ("away", None, None))
stub(PKG + ".room_sources", native=lambda *args: [], selected=lambda *args: [])
stub(PKG + ".equipment_model", settings=lambda manager, spec: {"announce_device_errors": True})

const = importlib.import_module(PKG + ".const")
languages = importlib.import_module(PKG + ".languages")
tts = importlib.import_module(PKG + ".tts_languages")
logic = importlib.import_module(PKG + ".logic")
messages = importlib.import_module(PKG + ".messages")
hub = importlib.import_module(PKG + ".hub_delivery")
shade = importlib.import_module(PKG + ".shade_delivery")
away = importlib.import_module(PKG + ".away_windows")
faults = importlib.import_module(PKG + ".device_faults")
text = importlib.import_module(PKG + ".announcement_text")


async def rewrite(hass, rec, message, language, agent):
    hass.rewrites.append((language, agent))
    if getattr(hass, "after_rewrite", None) is not None:
        hass.after_rewrite()
    return message


# Compile production manager methods without constructing unrelated controllers.
manager_tree = ast.parse((ROOT / "manager.py").read_text(encoding="utf-8"))
manager_class = next(node for node in manager_tree.body if isinstance(node, ast.ClassDef)
                     and any(isinstance(item, ast.AsyncFunctionDef) and item.name == "async_announce"
                             for item in node.body))
methods = [node for node in manager_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
           and node.name in ("get_language", "_targets_in_room", "async_announce")]
compiled_class = ast.ClassDef(name="DeliveryManager", bases=[], keywords=[], body=methods, decorator_list=[])
scope = {**vars(const), "__name__": PKG + ".manager_fixture", "Any": Any,
         "_LOGGER": logging.getLogger("hem.announcement_fixture"),
         "announcement": messages.announcement,
         "announcement_language": languages.announcement_language,
         "tts_language": tts.tts_language,
         "entity_area": lambda hass, entity: None,
         "hub_available": hub.hub_available, "make_hub_payload": hub.make_hub_payload,
         "async_submit_hub": hub.async_submit_hub,
         "async_system_notification": hub.async_system_notification,
         "DEFAULT_AGENT": "default", "ai_effectively_enabled": lambda config: config.get("ai_rewrite", False),
         "async_rewrite_announcement": rewrite}
exec(compile(ast.fix_missing_locations(ast.Module(body=[compiled_class], type_ignores=[])),
             str(ROOT / "manager.py"), "exec"), scope)
DeliveryManager = scope["DeliveryManager"]


class States:
    def __init__(self):
        self.items = {
            "cover.one": N(entity_id="cover.one", name="Shade · 窗", attributes={}),
            "person.owner": N(entity_id="person.owner", state="not_home", attributes={}),
        }

    def get(self, entity):
        return self.items.get(entity)

    def async_all(self, domain=None):
        return [state for entity, state in self.items.items()
                if domain is None or entity.startswith(domain + ".")]


class Services:
    def __init__(self, hass):
        self.hass = hass
        self.calls = []
        self.accepted = True
        self.available = {("notify", "send_message"), ("notify", "announcement_hub"),
                          ("tts", "speak"), ("persistent_notification", "create")}

    def has_service(self, domain, service):
        return (domain, service) in self.available

    async def async_call(self, domain, service, data, **kwargs):
        self.calls.append(N(domain=domain, service=service, data=data, kwargs=kwargs))
        if (domain, service) == ("notify", "announcement_hub"):
            return {"accepted": self.accepted}
        if (domain, service) == ("tts", "speak"):
            supported = self.hass.provider.supported_languages
            if supported and data.get("language") not in supported:
                raise ValueError("The selected language is not supported by this TTS provider")


def fixture(language="auto", ha_language="en", provider_languages=None):
    manager = DeliveryManager()
    manager.settings = {
        const.CONF_LANGUAGE: language, const.CONF_AUTO_NOTIFY: True,
        const.CONF_AUTO_TTS: True, const.CONF_TTS_ENGINE: "tts.voice",
        const.CONF_MEDIA_PLAYERS: ["media_player.room"],
        const.CONF_NOTIFY_TARGETS: ["notify.phone"], const.CONF_SHADE_ANNOUNCE: True,
    }
    manager.entry = N(entry_id="hem")
    manager.plan = N(recommendations=(logic.Recommendation(
        action="open", area_id="room", area_name="Zimmer · Δωμάτιο",
        windows=(logic.Window("binary_sensor.window", "Window · 窗", False),),
        reasons=(logic.Reason("inside_co2", "CO₂", "1200 ppm"),),
    ),), climate_recommendations=())
    hass = manager.hass = N(config=N(language=ha_language), states=States(), rewrites=[],
                           room_name="Zimmer · Δωμάτιο", hub_installed=False)
    hass.provider = N(supported_languages=list(provider_languages or ()), default_language="en_US")
    hass.data = {"tts_component": N(get_entity=lambda entity: hass.provider if entity == "tts.voice" else None)}
    hass.config_entries = N(async_entries=lambda domain: [N(state=N(value="loaded"))]
                            if domain == "announcement_hub" and hass.hub_installed else [])
    hass.services = Services(hass)
    return manager


class LanguagePolicyTests(unittest.TestCase):
    def test_menu_and_saved_value_do_not_depend_on_tts_provider(self):
        manager = fixture("de-DE", provider_languages=["en_US"])
        choices = tts.language_options(manager.hass, "tts.voice")
        self.assertEqual({item["value"] for item in choices}, {"auto", *languages.SUPPORTED_LANGUAGE_TAGS})
        self.assertEqual(len(choices), 39)
        self.assertEqual(tts.preferred_language(manager.hass, "tts.voice", "de-DE"), "de")
        self.assertTrue(tts.supports_language(manager.hass, "tts.voice", "el"))
        self.assertEqual(choices, tts.language_options(manager.hass, None))
        manager.hass.config.language = "zh-Hans-TW"
        self.assertEqual(tts.announcement_language_options(manager.hass)[0]["label"],
                         "Home Assistant 语言（默认）")
        for value in (None, 1, "", "not-a-language", "xx", "en--US"):
            self.assertIsNone(languages.normalize_announcement_language(value), value)
        for value, expected in {"PT_br": "pt-BR", "pt-PT": "pt", "zh_TW": "zh-Hant",
                                "zh-Hans-TW": "zh-Hans", "zh-Hant-CN": "zh-Hant",
                                "no-NO": "nb", "DE-de": "de", "AUTO": "auto"}.items():
            self.assertEqual(languages.normalize_announcement_language(value), expected)

    def test_provider_matching_preserves_native_tokens_and_locale_meaning(self):
        manager = fixture(provider_languages=["en_US", "en_GB", "pt_PT", "zh_CN", "zh_TW"])
        self.assertEqual(tts.provider_languages(manager.hass, "tts.voice")[0][0], "en_US")
        for requested, expected in {"en-GB": "en_GB", "pt-PT": "pt_PT", "pt-BR": "pt-BR",
                                    "zh-Hant": "zh_TW", "zh-Hans": "zh_CN", "el": "el"}.items():
            self.assertEqual(tts.tts_language(manager.hass, "tts.voice", requested), expected)
        manager.hass.provider.supported_languages = ["zh_CN", "pt_PT"]
        self.assertEqual(tts.tts_language(manager.hass, "tts.voice", "zh-Hant"), "zh-Hant")
        manager.hass.states.items["tts.fallback"] = N(attributes={"supported_languages": ["de_DE"]})
        self.assertEqual(tts.tts_language(manager.hass, "tts.fallback", "de"), "de_DE")
        manager.hass.provider.supported_languages = ["en_AU", "en_US"]
        self.assertEqual(tts.tts_language(manager.hass, "tts.voice", "en"), "en_US")
        self.assertEqual(tts.tts_language(manager.hass, "tts.voice", "en-AU"), "en_AU")

    def test_auto_resolves_live_ha_language_and_explicit_auto_overrides_saved_choice(self):
        manager = fixture("el", ha_language="pt_BR", provider_languages=["pt_BR", "el_GR"])
        self.assertEqual(manager.get_language(None), "el")
        self.assertEqual(manager.get_language("auto"), "pt-BR")
        self.assertEqual(tts.tts_language(manager.hass, "tts.voice", "auto"), "pt_BR")
        manager.hass.config.language = "zh-Hant"
        manager.settings[const.CONF_LANGUAGE] = "auto"
        self.assertEqual(manager.get_language(None), "zh-Hant")
        manager.hass.config.language = "unsupported"
        self.assertEqual(manager.get_language(None), "en")

    def test_fixed_notice_catalogs_cover_every_supported_locale_and_placeholders(self):
        formatter = string.Formatter()
        def fields(template):
            return {field for _, field, _, _ in formatter.parse(template) if field is not None}
        for catalog in (text.SHADE_MESSAGES, text.AWAY_WINDOW_MESSAGES, text.FAULT_LABELS):
            self.assertEqual(set(catalog), set(languages.SUPPORTED_LANGUAGE_TAGS))
        for language in languages.SUPPORTED_LANGUAGE_TAGS:
            for key, expected in {"title": set(), "open": {"room"}, "close": {"room"},
                                  "open_cover": {"room", "cover"}, "close_cover": {"room", "cover"}}.items():
                self.assertEqual(fields(text.SHADE_MESSAGES[language][key]), expected, (language, key))
            self.assertEqual(fields(text.AWAY_WINDOW_MESSAGES[language][1]), {"windows"})
            self.assertTrue(all(value for value in text.AWAY_WINDOW_MESSAGES[language]))
            self.assertEqual(fields(text.FAULT_LABELS[language]["title"]), {"name"})
            self.assertEqual(set(text.FAULT_LABELS[language]), set(text.FAULT_LABELS["en"]))
            for key, value in text.FAULT_LABELS[language].items():
                self.assertTrue(value, (language, key))
                self.assertEqual(fields(value), {"name"} if key == "title" else set(), (language, key))


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_recommendation_text_ai_and_tts_follow_auto_at_send_time(self):
        manager = fixture(ha_language="de-DE", provider_languages=["de_DE", "el_GR", "fr-FR"])
        manager.settings["ai_rewrite"] = True
        for ha_language, language, voice in (("de-DE", "de", "de_DE"), ("el", "el", "el_GR")):
            manager.hass.config.language = ha_language
            manager.hass.services.calls.clear()
            result = await manager.async_announce(channels="auto")
            self.assertEqual(result, {"submitted": 2, "errors": []})
            notify, speech = manager.hass.services.calls
            self.assertEqual(notify.data["message"], messages.announcement(manager.plan.recommendations[0], language)[1])
            self.assertEqual(speech.data["language"], voice)
            self.assertEqual(speech.data["message"], notify.data["message"])
            self.assertEqual(manager.hass.rewrites[-1][0], language)
        manager.settings[const.CONF_LANGUAGE] = "de"
        await manager.async_announce(language="fr", channels="tts")
        self.assertEqual(manager.hass.services.calls[-1].data["language"], "fr-FR")
        self.assertEqual(manager.hass.rewrites[-1][0], "fr")
        await manager.async_announce(language="auto", channels="tts")
        self.assertEqual(manager.hass.services.calls[-1].data["language"], "el_GR")

    async def test_hub_receives_resolved_language_and_owns_a_rejected_delivery(self):
        manager = fixture(ha_language="zh_TW")
        manager.hass.hub_installed = True
        manager.settings.update({const.CONF_HUB: True, "ai_rewrite": True})
        result = await manager.async_announce(channels="both")
        self.assertEqual(result["submitted"], 1)
        self.assertEqual(len(manager.hass.services.calls), 1)
        payload = manager.hass.services.calls[0].data
        self.assertEqual(payload["language"], "zh-Hant")
        self.assertEqual(payload["text"], messages.announcement(manager.plan.recommendations[0], "zh-Hant")[1])
        self.assertEqual(payload["area"], ["Zimmer · Δωμάτιο"])
        self.assertTrue(payload["use_ai"])
        self.assertEqual(manager.hass.rewrites, [])
        manager.hass.services.calls.clear()
        manager.hass.services.accepted = False
        result = await manager.async_announce(channels="tts")
        self.assertEqual(result["submitted"], 0)
        self.assertEqual(len(manager.hass.services.calls), 1)
        self.assertIn("text_tts", manager.hass.services.calls[0].data)
        self.assertNotIn("text", manager.hass.services.calls[0].data)

    async def test_language_change_while_rewriting_does_not_change_already_built_speech(self):
        manager = fixture(ha_language="de", provider_languages=["de_DE", "el_GR"])
        manager.settings["ai_rewrite"] = True
        manager.hass.after_rewrite = lambda: setattr(manager.hass.config, "language", "el")
        await manager.async_announce(channels="both")
        notify, speech = manager.hass.services.calls
        self.assertEqual(notify.data["message"], messages.announcement(manager.plan.recommendations[0], "de")[1])
        self.assertEqual(speech.data["language"], "de_DE")
        self.assertEqual(manager.get_language(None), "el")

    async def test_incompatible_provider_cannot_silently_change_language_or_channel(self):
        manager = fixture("pt-BR", provider_languages=["pt_PT"])
        result = await manager.async_announce(channels="both")
        self.assertEqual(result["submitted"], 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(manager.hass.services.calls[-1].data["language"], "pt-BR")
        manager.hass.services.calls.clear()
        result = await manager.async_announce(channels="tts")
        self.assertEqual(result["submitted"], 0)
        self.assertEqual([(call.domain, call.service) for call in manager.hass.services.calls], [("tts", "speak")])

    async def test_shade_notice_localizes_all_languages_and_preserves_cover_identity(self):
        manager = fixture()
        for language in languages.SUPPORTED_LANGUAGE_TAGS:
            manager.settings[const.CONF_LANGUAGE] = language
            manager.hass.provider.supported_languages = [language]
            manager.hass.services.calls.clear()
            self.assertTrue(await shade.async_announce_before_move(manager, area="room", action="close", entity_id="cover.one"))
            notify, speech = manager.hass.services.calls
            self.assertEqual(notify.data["title"], text.SHADE_MESSAGES[language]["title"])
            self.assertEqual(notify.data["message"], text.SHADE_MESSAGES[language]["close_cover"].format(
                room=manager.hass.room_name, cover="Shade · 窗"))
            self.assertEqual(speech.data["language"], language)
        manager.settings.update({const.CONF_LANGUAGE: "auto", const.CONF_HUB: True})
        manager.hass.config.language = "pt-BR"
        manager.hass.hub_installed = True
        manager.hass.services.calls.clear()
        self.assertTrue(await shade.async_announce_before_move(manager, area="room", action="open"))
        self.assertEqual(manager.hass.services.calls[0].data["language"], "pt-BR")
        self.assertIs(manager.hass.services.calls[0].data["use_ai"], False)
        manager.hass.services.accepted = False
        manager.hass.services.calls.clear()
        self.assertFalse(await shade.async_announce_before_move(manager, area="room", action="open"))
        self.assertEqual(len(manager.hass.services.calls), 1)

    async def test_away_notice_language_keeps_explicit_person_channel_routing(self):
        manager = fixture(ha_language="zh-Hant")
        manager.hass.hub_installed = True
        manager.settings.update({const.CONF_AWAY_WINDOWS_PERSONS: ["person.owner"],
                                 const.CONF_AWAY_WINDOWS_DELIVERY: ["mobile_notification", "watch_tts"]})
        windows = (("binary_sensor.window", "Window · 窗"),)
        self.assertTrue(await away.deliver_notice(manager, windows))
        self.assertEqual(len(manager.hass.services.calls), 2)
        mobile, watch = [call.data for call in manager.hass.services.calls]
        for payload in (mobile, watch):
            self.assertEqual(payload["language"], "zh-Hant")
            self.assertEqual(payload["title"], text.AWAY_WINDOW_MESSAGES["zh-Hant"][0])
            self.assertEqual(payload["target_person"], ["person.owner"])
            self.assertNotIn("area", payload)
            self.assertIs(payload["use_ai"], False)
        self.assertEqual(mobile["person_destination"], ["mobile"])
        self.assertIn("text_notify", mobile)
        self.assertNotIn("text_tts", mobile)
        self.assertEqual(watch["person_destination"], ["watch"])
        self.assertIn("text_tts", watch)
        self.assertNotIn("text_notify", watch)
        self.assertIn("Window · 窗", watch["text_tts"])
        manager.hass.services.calls.clear()
        manager.hass.services.accepted = False
        self.assertFalse(await away.deliver_notice(manager, windows))
        self.assertEqual(len(manager.hass.services.calls), 2)
        self.assertTrue(all(call.service == "announcement_hub" for call in manager.hass.services.calls))

    async def test_faults_localize_wrapper_but_preserve_original_diagnostics(self):
        manager = fixture(ha_language="it", provider_languages=["it_IT"])
        spec = N(identifier="device", name="Device · Μονάδα", area_id="room", source_device_id="native")
        report = {"faults": [{"source_entity_id": "sensor.native_error", "severity": "critical", "code": "E07",
                              "description": "Original blocked filter", "info": {"vendor_detail": "保持原文"}}]}
        monitor = faults.NativeDeviceFaultMonitor(manager)
        monitor.active = True
        monitor._fingerprints[spec.identifier] = ("event",)
        await monitor._announce(spec, ("event",), report)
        notify, speech = manager.hass.services.calls
        self.assertEqual(speech.data["language"], "it_IT")
        self.assertEqual(notify.data["title"], text.FAULT_LABELS["it"]["title"].format(name=spec.name))
        for original in (spec.name, manager.hass.room_name, "sensor.native_error", "critical", "E07",
                         "Original blocked filter", "vendor_detail: 保持原文"):
            self.assertIn(original, notify.data["message"])
        manager.hass.services.calls.clear()
        manager.hass.hub_installed = True
        manager.settings.update({const.CONF_HUB: True, const.CONF_LANGUAGE: "pt-BR"})
        await monitor._announce(spec, ("event",), report)
        self.assertEqual(len(manager.hass.services.calls), 1)
        self.assertEqual(manager.hass.services.calls[0].data["language"], "pt-BR")
        self.assertIs(manager.hass.services.calls[0].data["use_ai"], False)
        self.assertIn("vendor_detail: 保持原文", manager.hass.services.calls[0].data["text"])


if __name__ == "__main__":
    unittest.main()
