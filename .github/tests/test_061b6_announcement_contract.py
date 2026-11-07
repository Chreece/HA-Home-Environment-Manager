"""Room opening, named closure, device deadlines and one Hub AI handoff.

Execute production message rendering and the actual manager delivery method
with simulated HA services. No real device or output receives these calls.
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import replace
import importlib
import json
import logging
from pathlib import Path
import runpy
from string import Formatter
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(Path(__file__).with_name("test_061b5_announcement_delivery.py")))
fixture = base["fixture"]
logic, messages, const, hub = (base[key] for key in ("logic", "messages", "const", "hub"))
window_text = importlib.import_module(base["PKG"] + ".window_open_text")
rewrite = importlib.import_module(base["PKG"] + ".ai_rewrite")
languages = base["languages"].SUPPORTED_LANGUAGE_TAGS


def recommendation(**changes):
    original = logic.Recommendation(
        "open", "studio", "Studio · Δωμάτιο",
        (logic.Window("binary_sensor.studio_left", "ContactLeftSecret47", False),
         logic.Window("binary_sensor.studio_right", "ContactRightSecret59", False)),
        (logic.Reason("inside_co2", "CO₂", "1200 ppm"),),
    )
    return replace(original, **changes)


def waiting(entity="climate.dryer", name="Comfee · Αφυγραντήρας", *, seconds=300, effect="dry"):
    return {"entity_id": entity, "friendly_name": name,
            "timeout_seconds": 300, "remaining_seconds": seconds, "effect": effect}


class AnnouncementTextTests(unittest.TestCase):
    def test_room_only_opening_and_all_measured_reasons_in_every_language(self):
        reasons = (
            logic.Reason("inside_co2", "CO₂", "1200 ppm"),
            logic.Reason("inside_pm25", "PM2.5", "44 µg/m³"),
            logic.Reason("inside_humidity", "RH", "74 %"),
            logic.Reason("inside_formaldehyde", "HCHO", "134 µg/m³"),
        )
        rec = recommendation(reasons=reasons)
        for language in languages:
            with self.subTest(language=language):
                _, content = messages.announcement(rec, language)
                self.assertIn(rec.area_name, content)
                for window in rec.windows:
                    self.assertNotIn(window.name, content)
                    self.assertNotIn(window.entity_id, content)
                for reason in reasons:
                    self.assertIn(messages.explain(reason, language), content)

    def test_closure_names_only_observed_open_contacts_and_all_reasons(self):
        rec = recommendation(action="close", windows=(
            logic.Window("binary_sensor.left", "Left · Αριστερά", True),
            logic.Window("binary_sensor.right", "Right · Δεξιά", True),
            logic.Window("binary_sensor.closed", "AlreadyClosedSecret", False),
            logic.Window("binary_sensor.unknown", "UnknownContactSecret", None),
        ), reasons=(
            logic.Reason("weather_cold", value="2 °C"),
            logic.Reason("weather_wind", value="49 km/h"),
            logic.Reason("active_warning", "StormName"),
            logic.Reason("outside_pm25", "PM2.5", "72 µg/m³"),
        ))
        for language in languages:
            with self.subTest(language=language):
                _, content = messages.announcement(rec, language)
                for name in (rec.area_name, "Left · Αριστερά", "Right · Δεξιά"):
                    self.assertIn(name, content)
                for name in ("AlreadyClosedSecret", "UnknownContactSecret"):
                    self.assertNotIn(name, content)
                for reason in rec.reasons:
                    self.assertIn(messages.explain(reason, language), content)

    def test_thermal_closure_also_keeps_other_causes_and_friendly_names(self):
        rec = recommendation(action="close", windows=(
            logic.Window("binary_sensor.open", "Bedroom window", True),
        ), reasons=(logic.Reason("window_heat_loss", value="20.1 °C / 20 °C"),
                    logic.Reason("active_warning", "Heavy rain")))
        for language in languages:
            _, content = messages.announcement(rec, language)
            for item in (rec.area_name, "Bedroom window", "20.1 °C / 20 °C", "Heavy rain"):
                self.assertIn(item, content)

    def test_cautioned_opening_names_each_waiting_device_and_its_remaining_time(self):
        rec = recommendation(reasons=(
            logic.Reason("climate_window_dry", "Dryer", "2.4 g/kg"),),
            cautions=(logic.Reason("weather_cold", value="3 °C"),
                      logic.Reason("weather_condition", value="rainy")),
            wait_seconds=300, wait_devices=(
                waiting(seconds=121),
                waiting("fan.purifier", "Air purifier · Καθαριστής", seconds=60, effect="filtration"),
            ))
        for language in languages:
            with self.subTest(language=language):
                _, content = messages.announcement(rec, language)
                self.assertNotIn("ContactLeftSecret47", content)
                self.assertNotIn("ContactRightSecret59", content)
                self.assertIn("2.4 g/kg", content)
                for caution in rec.cautions:
                    self.assertIn(messages.explain(caution, language), content)
                templates = window_text.WINDOW_OPEN_TEXT[language]
                self.assertIn(templates["device_wait"].format(
                    device=rec.wait_devices[0]["friendly_name"], area=rec.area_name, minutes=3), content)
                self.assertIn(templates.get("device_wait_one", templates["device_wait"]).format(
                    device=rec.wait_devices[1]["friendly_name"], area=rec.area_name, minutes=1), content)
                # A configured five-minute wait must not be restarted in speech.
                self.assertNotIn(templates["wait"].format(minutes=5), content)
        english = messages.announcement(rec, "en")[1]
        self.assertIn("after 1 minute if", english)
        self.assertIn("stay closed", english)

    def test_expired_or_invalid_device_deadline_cannot_promise_another_wait(self):
        for seconds in (0, -1, 1801, True, "300", float("nan"), float("inf"), None):
            with self.subTest(seconds=seconds):
                rec = recommendation(wait_seconds=300, wait_devices=(waiting(seconds=seconds),))
                _, content = messages.announcement(rec, "en")
                self.assertNotIn("Comfee", content)
                self.assertNotIn("will start", content)
                self.assertNotIn("automatic device starts", content)
        closed = recommendation(action="close", wait_seconds=300, wait_devices=(waiting(),),
                                windows=(logic.Window("binary_sensor.open", "WindowLeft", True),))
        self.assertNotIn("will start", messages.announcement(closed, "en")[1])

    def test_new_device_alternative_reasons_and_wait_templates_cover_all_locales(self):
        self.assertEqual(set(window_text.ROOM_WINDOW_NAMES), set(languages))
        self.assertEqual(set(window_text.DEVICE_WINDOW_WAIT), set(languages))
        self.assertEqual(set(window_text.DEVICE_WINDOW_REASONS), set(languages))
        for language in languages:
            for code, value in (("climate_window_humidify", "1.7 g/kg"),
                                ("climate_window_filtration", "18 µg/m³")):
                reason = logic.Reason(code, value=value)
                rendered = messages.explain(reason, language)
                self.assertIn(value, rendered)
                self.assertNotIn("climate_window", rendered)
                self.assertNotEqual(rendered, code.replace("_", " "))
            entry = window_text.WINDOW_OPEN_TEXT[language]
            for key in ("device_wait", "device_wait_one"):
                if key in entry:
                    fields = {field for _, field, _, _ in Formatter().parse(entry[key]) if field}
                    self.assertEqual(fields, {"device", "area", "minutes"})


class DirectAIContractTests(unittest.TestCase):
    def test_open_prompt_never_sends_contact_names_to_ai(self):
        rec = recommendation()
        original = messages.announcement(rec, "en")[1]
        prompt = rewrite.make_rewrite_prompt(rec, original, "en")
        data = json.loads(prompt.split("INPUT_DATA=", 1)[1])
        self.assertEqual(data["windows"], [])
        for window in rec.windows:
            self.assertNotIn(window.name, prompt)
        self.assertEqual(rewrite._validate_rewrite_text("OPEN|" + original, rec, original), original)
        bad = original + " Use ContactLeftSecret47."
        self.assertIsNone(rewrite._validate_rewrite_text("OPEN|" + bad, rec, original))

    def test_close_prompt_and_validation_keep_only_open_window_names(self):
        rec = recommendation(action="close", windows=(
            logic.Window("binary_sensor.left", "LeftWindow", True),
            logic.Window("binary_sensor.closed", "ClosedWindow", False)),
            reasons=(logic.Reason("weather_wind", value="49 km/h"),))
        original = messages.announcement(rec, "en")[1]
        prompt = rewrite.make_rewrite_prompt(rec, original, "en")
        data = json.loads(prompt.split("INPUT_DATA=", 1)[1])
        self.assertEqual(data["windows"], ["LeftWindow"])
        self.assertNotIn("ClosedWindow", prompt)
        self.assertEqual(rewrite._validate_rewrite_text("CLOSE|" + original, rec, original), original)
        self.assertIsNone(rewrite._validate_rewrite_text(
            "CLOSE|" + original.replace("LeftWindow", "the window"), rec, original))

    def test_fourth_reason_is_sent_and_a_dropped_measurement_rejects_rewrite(self):
        reasons = tuple(logic.Reason("inside_co2", f"CO₂-{i}", f"{1100+i} ppm") for i in range(4))
        rec = recommendation(reasons=reasons)
        original = messages.announcement(rec, "en")[1]
        prompt = rewrite.make_rewrite_prompt(rec, original, "en")
        data = json.loads(prompt.split("INPUT_DATA=", 1)[1])
        self.assertEqual(len(data["reasons"]), 4)
        self.assertIsNone(rewrite._validate_rewrite_text(
            "OPEN|" + original.replace("1103 ppm", "high"), rec, original))

    def test_keeping_only_the_measurement_does_not_keep_the_reason(self):
        rec = recommendation()
        original = messages.announcement(rec, "en")[1]
        weakened = original.replace("CO₂ is high (1200 ppm)", "CO₂ 1200 ppm")
        self.assertIsNone(rewrite._validate_rewrite_text(
            "OPEN|" + weakened, rec, original, "en"))
        self.assertEqual(rewrite._validate_rewrite_text(
            "OPEN|Please " + original, rec, original, "en"), "Please " + original)


class HubAIContractTests(unittest.IsolatedAsyncioTestCase):
    def manager(self, enabled=True):
        manager = fixture("el")
        manager.settings.update({const.CONF_HUB: True, const.CONF_AI_REWRITE: enabled,
                                 "ai_rewrite": enabled, const.CONF_AI_AGENT: "ai_task.announcer"})
        manager.hass.hub_installed = True
        return manager

    def assert_ai(self, manager, expected):
        self.assertTrue(manager.hass.services.calls)
        for call in manager.hass.services.calls:
            self.assertEqual((call.domain, call.service), ("notify", "announcement_hub"))
            self.assertIs(call.data["use_ai"], expected)
            self.assertEqual(call.data["ai_mode"], "rewrite")
            if expected:
                self.assertEqual(call.data["ai_agent"], "ai_task.announcer")
            else:
                self.assertNotIn("ai_agent", call.data)
        self.assertEqual(manager.hass.rewrites, [])

    async def test_caution_and_named_timeout_preserve_enabled_and_disabled_ai_choice(self):
        for enabled in (True, False):
            manager = self.manager(enabled)
            rec = replace(manager.plan.recommendations[0],
                          cautions=(logic.Reason("weather_cold", value="3 °C"),),
                          wait_seconds=300, wait_devices=(waiting(),))
            manager.plan.recommendations = (rec,)
            outcome = await manager.async_announce(channels="auto")
            self.assertEqual(outcome, {"submitted": 1, "errors": []})
            self.assert_ai(manager, enabled)
            content = manager.hass.services.calls[0].data["text"]
            self.assertIn("Comfee · Αφυγραντήρας", content)
            self.assertIn("3 °C", content)
            self.assertIn("5", content)
            self.assertNotIn(rec.windows[0].name, content)

    async def test_rejected_hub_never_rewrites_or_delivers_locally(self):
        manager = self.manager(True)
        manager.hass.services.accepted = False
        outcome = await manager.async_announce(channels="both")
        self.assertEqual(outcome["submitted"], 0)
        self.assert_ai(manager, True)
        self.assertEqual(len(manager.hass.services.calls), 1)

    async def test_shade_away_and_device_fault_notices_share_the_ai_option(self):
        for enabled in (True, False):
            manager = self.manager(enabled)
            self.assertTrue(await base["shade"].async_announce_before_move(
                manager, area="room", action="close", entity_id="cover.one", required=True))
            self.assert_ai(manager, enabled)
            manager.hass.services.calls.clear()
            manager.settings.update({const.CONF_AWAY_WINDOWS_PERSONS: ["person.owner"],
                                     const.CONF_AWAY_WINDOWS_DELIVERY: ["mobile_notification", "watch_tts"]})
            self.assertTrue(await base["away"].deliver_notice(
                manager, (("binary_sensor.open", "Studio: LeftWindow"),)))
            self.assert_ai(manager, enabled)
            self.assertEqual(len(manager.hass.services.calls), 2)
            for call in manager.hass.services.calls:
                self.assertEqual(call.data["target_person"], ["person.owner"])
                self.assertNotIn("area", call.data)
            manager.hass.services.calls.clear()
            monitor = base["faults"].NativeDeviceFaultMonitor(manager)
            monitor.active = True
            spec = N(identifier="device", name="Dryer", area_id="room", source_device_id="native")
            monitor._fingerprints[spec.identifier] = ("event",)
            await monitor._announce(spec, ("event",), {
                "faults": [{"source_entity_id": "sensor.error", "code": "E07",
                            "severity": "warning", "description": "Original fault details",
                            "info": {}}],
            })
            self.assert_ai(manager, enabled)
            self.assertIn("Original fault details", manager.hass.services.calls[0].data["text"])

    async def test_consumed_device_request_stops_automatic_notices_but_manual_still_works(self):
        manager = self.manager(False)
        manager.window_open_wait = N(should_announce=lambda rec: False,
                                    begin_submission=lambda rec: None,
                                    submitted=lambda rec: None)
        automatic = await manager.async_announce(channels="auto")
        self.assertEqual(automatic, {"submitted": 0, "errors": []})
        self.assertEqual(manager.hass.services.calls, [])
        manual = await manager.async_announce(channels="both")
        self.assertEqual(manual, {"submitted": 1, "errors": []})


class NativeNonresponseNoticeTests(unittest.IsolatedAsyncioTestCase):
    def case(self, *, language="el", use_hub=True, ai_enabled=True):
        manager = fixture(language)
        manager.settings.update({const.CONF_HUB: use_hub, const.CONF_AI_REWRITE: ai_enabled,
                                 const.CONF_AI_AGENT: "ai_task.announcer"})
        manager.hass.hub_installed = use_hub
        spec = N(identifier="dryer", area_id="room", name="HEM controller name",
                 source_entities=("climate.dryer",), source_device_id="physical-dryer")
        manager.hass.states.items["climate.dryer"] = N(
            name="Comfee · Αφυγραντήρας", state="off", attributes={})
        cfg = {"control_mode": "automatic", "announce_device_errors": True}
        pending = {"entity": "climate.dryer", "service": "set_hvac_mode",
                   "data": {"hvac_mode": "dry"}, "expected": {"state": "dry"},
                   "retry_context": {"mode": "dry", "settings": dict(cfg)},
                   "retry_policy": "automatic_minute", "attempts": 4,
                   "nonresponse_attempts": 3, "nonresponse_notified": True}
        record = {"pending": pending}
        manager.equipment = N(_record=lambda spec: record, _active=True, _ready=True)
        return manager, spec, cfg, pending, record

    async def test_all_locales_keep_room_device_actual_operation_and_failed_count(self):
        catalog = importlib.import_module(base["PKG"] + ".device_command_text")
        self.assertEqual(set(catalog.NONRESPONSE_TEXT), set(languages))
        self.assertEqual(set(catalog.OPERATION_LABELS), set(languages))
        for language in languages:
            with self.subTest(language=language):
                manager, spec, cfg, pending, _ = self.case(language=language)
                with patch.object(base["faults"].model, "settings", return_value=cfg):
                    await base["faults"].async_announce_nonresponse(manager, spec, pending)
                self.assertEqual(len(manager.hass.services.calls), 1)
                payload = manager.hass.services.calls[0].data
                self.assertEqual(payload["text"], catalog.NONRESPONSE_TEXT[language].format(
                    name="Comfee · Αφυγραντήρας", room=manager.hass.room_name,
                    operation=catalog.OPERATION_LABELS[language]["dry"], attempts=3))
                self.assertEqual(payload["language"], language)
                self.assertIs(payload["use_ai"], True)
                self.assertEqual(payload["ai_mode"], "rewrite")
                self.assertEqual(payload["ai_agent"], "ai_task.announcer")
                self.assertNotIn(spec.name, payload["text"])
                self.assertNotIn("set_hvac_mode", payload["text"])
                self.assertEqual(manager.hass.rewrites, [])
                self.assertIs(pending, manager.equipment._record(spec)["pending"])

    async def test_stale_disabled_unowned_or_incomplete_episode_does_not_speak(self):
        for reason in ("replaced", "paused", "disabled", "manual", "inactive", "unready", "wrong_source",
                       "unmarked", "too_early", "not_automatic"):
            with self.subTest(reason=reason):
                manager, spec, cfg, pending, record = self.case()
                if reason == "replaced": record["pending"] = dict(pending)
                if reason == "paused": record["paused"] = "physical_manual_override"
                if reason == "disabled": cfg["announce_device_errors"] = False
                if reason == "manual": cfg["control_mode"] = "manual"
                if reason == "inactive": manager.equipment._active = False
                if reason == "unready": manager.equipment._ready = False
                if reason == "wrong_source": pending["entity"] = "climate.other"
                if reason == "unmarked": pending["nonresponse_notified"] = False
                if reason == "too_early": pending["nonresponse_attempts"] = 2
                if reason == "not_automatic": pending.pop("retry_policy")
                with patch.object(base["faults"].model, "settings", return_value=cfg):
                    await base["faults"].async_announce_nonresponse(manager, spec, pending)
                self.assertEqual(manager.hass.services.calls, [])

    async def test_hub_rejection_keeps_ownership_and_disabled_ai_explicit(self):
        manager, spec, cfg, pending, _ = self.case(ai_enabled=False)
        manager.hass.services.accepted = False
        with patch.object(base["faults"].model, "settings", return_value=cfg):
            await base["faults"].async_announce_nonresponse(manager, spec, pending)
        self.assertEqual(len(manager.hass.services.calls), 1)
        call = manager.hass.services.calls[0]
        self.assertEqual((call.domain, call.service), ("notify", "announcement_hub"))
        self.assertIs(call.data["use_ai"], False)
        self.assertNotIn("ai_agent", call.data)
        self.assertEqual(manager.hass.rewrites, [])

    async def test_direct_channels_and_persistent_fallback_keep_the_same_cause(self):
        manager, spec, cfg, pending, _ = self.case(language="en", use_hub=False)
        with patch.object(base["faults"].model, "settings", return_value=cfg):
            await base["faults"].async_announce_nonresponse(manager, spec, pending)
        calls = manager.hass.services.calls
        self.assertEqual([(call.domain, call.service) for call in calls],
                         [("notify", "send_message"), ("tts", "speak")])
        for call in calls:
            self.assertIn("after 3 attempts", call.data["message"])
            self.assertIn("not confirmed", call.data["message"])
            self.assertIn("Automatic control remains enabled", call.data["message"])
            self.assertIn("every minute", call.data["message"])
        manager.hass.services.calls.clear()
        manager.settings[const.CONF_NOTIFY_TARGETS] = []
        manager.settings[const.CONF_AUTO_TTS] = False
        with patch.object(base["faults"].model, "settings", return_value=cfg):
            await base["faults"].async_announce_nonresponse(manager, spec, pending)
        self.assertEqual(len(manager.hass.services.calls), 1)
        call = manager.hass.services.calls[0]
        self.assertEqual((call.domain, call.service), ("persistent_notification", "create"))
        self.assertTrue(call.data["notification_id"].startswith("hem_command_nonresponse_"))

    def test_requested_native_target_retains_its_value_and_physical_unit(self):
        manager, spec, cfg, pending, _ = self.case()
        state = manager.hass.states.get("climate.dryer")
        state.attributes["temperature_unit"] = "°F"
        pending.update(service="set_temperature", data={"temperature": 72},
                       retry_context={"mode": "heat"}, expected={"temperature": 72})
        self.assertEqual(base["faults"]._requested_operation(pending, state, "en", manager.hass),
                         "Heating · 72 °F")
        pending.update(service="set_humidity", data={"humidity": 60},
                       retry_context={"mode": "dry"}, expected={"humidity": 60})
        self.assertEqual(base["faults"]._requested_operation(pending, state, "el", manager.hass),
                         "Αφύγρανση · 60%")


class WindowSchedulerContractTests(unittest.IsolatedAsyncioTestCase):
    def sender(self, pending):
        tree = ast.parse((ROOT / "manager.py").read_text())
        source_class = next(node for node in tree.body
                            if isinstance(node, ast.ClassDef) and node.name == "AirQualityManager")
        method = next(node for node in source_class.body
                      if isinstance(node, ast.AsyncFunctionDef) and node.name == "_send_automatic")
        cls = ast.ClassDef(name="Sender", bases=[], keywords=[], body=[method], decorator_list=[])
        scope = {"asyncio": asyncio, "_LOGGER": logging.getLogger("hem.b6.sender"),
                 "monotonic": lambda: 100.0}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])),
                     str(ROOT / "manager.py"), "exec"), scope)
        sender = scope["Sender"]()
        rec = recommendation(wait_seconds=300, wait_devices=(waiting(),))
        keys = (rec.action_signature, rec.reason_signature)
        sender._active = True
        sender._active_actions = {rec.area_id: keys}
        sender._sending_actions = {rec.area_id: keys}
        sender._last_sent = {}
        sender.plan = N(recommendations=(rec,), climate_recommendations=(), environment={})
        self.calls = []

        async def submit(**kwargs):
            # Another idle device is discovered while the first request is
            # in flight. Its room/cause signatures did not change.
            next_rec = replace(rec, wait_devices=(waiting(), waiting(
                "fan.purifier", "Second device", seconds=180, effect="filtration")))
            sender.plan = N(recommendations=(next_rec,), climate_recommendations=(), environment={
                rec.area_id: {"window_open_wait": {
                    "status": "window_request_pending" if pending else "window_open_wait"}}})
            return {"submitted": 1, "errors": []}

        sender.async_announce = submit
        sender._cancel_pending = lambda area: self.calls.append(("cancel_pending", area))
        sender._cancel_repeat = lambda area: self.calls.append(("cancel_repeat", area))
        sender._queue_automatic = lambda *args, **kwargs: self.calls.append(("queue", args, kwargs))
        sender._schedule_repeat = lambda *args: self.calls.append(("repeat", args))
        return sender, rec, keys

    async def test_second_device_joining_inflight_delivery_gets_immediate_own_request(self):
        sender, rec, keys = self.sender(True)
        await sender._send_automatic(rec.area_id, *keys)
        self.assertEqual([call[0] for call in self.calls], ["cancel_repeat", "cancel_pending", "queue"])
        self.assertEqual(sender._sending_actions, {})

    async def test_accepted_wait_without_new_device_keeps_normal_repeat_schedule(self):
        sender, rec, keys = self.sender(False)
        await sender._send_automatic(rec.area_id, *keys)
        self.assertEqual([call[0] for call in self.calls], ["repeat"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
