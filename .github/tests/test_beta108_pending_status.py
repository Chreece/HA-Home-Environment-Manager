"""Pending-command guidance must describe the actual execution stage.

Use the existing native-transport fixture with the real production tick,
dispatch, ACK matcher and resume_information. Service transport succeeds
without changing the reported device target, reproducing a dispatched 30 C
request whose native entity still reports 5 C in HEAT mode. Reading status
must neither send another command nor create a recovery probe or clear a hold.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_onoff_native_extrema.py"),
                         run_name="hem_pending_status_fixture")
fixture["load_pure"]("equipment_resume", "equipment_resume.py")
production = fixture["production"]
fixture["extract"](fixture["RUNTIME"], ("resume_information",), production.__dict__)
SPEC, PRIMARY = fixture["SPEC"], fixture["PRIMARY"]


class StatusRuntime(fixture["NativeRuntime"]):
    resume_information = production.resume_information


class PendingStatusTests(unittest.IsolatedAsyncioTestCase):
    async def dispatched_target(self, *, method="pid", age=10, language="en"):
        runtime = StatusRuntime(method, "heat", low=5.0, high=30.0,
                                absent=("temperature_unit", "target_temp_step"))
        runtime.hass.config = N(language=language, units=N(temperature_unit="°C"))
        runtime.state.attributes["current_temperature"] = 18.6
        runtime.own_running()
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls, [{
            "domain": "climate", "service": "set_temperature",
            "data": {"temperature": 30.0}, "target": {"entity_id": PRIMARY},
        }], runtime.statuses)
        self.assertEqual(runtime.record["pending"]["phase"], "commanded")
        self.assertEqual(runtime.record["pending"]["expected"],
                         {"attributes": {"temperature": 30.0}})
        self.assertEqual(runtime.state.state, "heat")
        self.assertEqual(runtime.state.attributes["temperature"], 5.0)
        runtime.now += age
        return runtime

    def read_without_side_effects(self, runtime):
        before = {
            "records": deepcopy(runtime.records),
            "state": deepcopy(vars(runtime.state)),
            "settings": deepcopy(runtime.manager.settings),
            "calls": deepcopy(runtime.calls),
            "persisted": deepcopy(runtime.persisted),
            "statuses": deepcopy(runtime.statuses),
        }
        result = runtime.resume_information(SPEC)
        self.assertEqual(runtime.resume_information(SPEC), result)
        self.assertEqual(runtime.records, before["records"])
        self.assertEqual(vars(runtime.state), before["state"])
        self.assertEqual(runtime.manager.settings, before["settings"])
        self.assertEqual(runtime.calls, before["calls"])
        self.assertEqual(runtime.persisted, before["persisted"])
        self.assertEqual(runtime.statuses, before["statuses"])
        return result

    def assert_target_feedback(self, result, *, language="en"):
        label = {
            "en": "Temperature setpoint",
            "de": "Temperatur-Sollwert",
            "el": "Επιθυμητή θερμοκρασία",
        }[language]
        self.assertEqual(result["requested"], f"{label} 30 °C")
        self.assertEqual(result["observed"], f"{label} 5 °C")
        self.assertIn(result["requested"], result["instructions"])
        self.assertIn(result["observed"], result["instructions"])
        self.assertIn(PRIMARY, result["instructions"])

    async def test_normal_pending_feedback_does_not_require_manual_checks(self):
        for method in ("automatic", "pid"):
            for age, decision in ((10, "settling"), (121, "first_check")):
                with self.subTest(method=method, age=age):
                    runtime = await self.dispatched_target(method=method, age=age)
                    self.assertIsNone(runtime.record.get("paused"))
                    self.assertNotIn("automatic_continue_requested", runtime.record)
                    result = self.read_without_side_effects(runtime)
                    self.assert_target_feedback(result)
                    self.assertEqual(result["decision"], decision)
                    self.assertIs(result["requires_user_repeated_check"], False)
                    self.assertNotIn("settings_saved", result)
                    text = result["instructions"].casefold()
                    self.assertIn("automatically", text)
                    self.assertNotIn("press check and continue again", text)
                    self.assertNotIn("no command sent", text)
                    self.assertNotIn("no device command has been sent", text)
                    self.assertNotIn("pending_resume_probe", runtime.record)

    async def test_normal_pending_feedback_uses_the_ha_language_and_unit(self):
        for language in ("de", "el"):
            with self.subTest(language=language):
                runtime = await self.dispatched_target(age=121, language=language)
                result = self.read_without_side_effects(runtime)
                self.assert_target_feedback(result, language=language)
                self.assertIs(result["requires_user_repeated_check"], False)
                self.assertNotIn("settings_saved", result)

    async def test_queued_automatic_recovery_retains_its_saved_choice_guidance(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method):
                runtime = await self.dispatched_target(method=method, age=121)
                runtime.record["paused"] = "physical_acknowledgement_missing"
                runtime.record["automatic_continue_requested"] = {
                    "at": runtime.now, "method": method,
                    "awaiting_physical_verification": True,
                }
                result = self.read_without_side_effects(runtime)
                self.assert_target_feedback(result)
                self.assertEqual(result["decision"], "first_check")
                self.assertIs(result["settings_saved"], True)
                self.assertIs(result["requires_user_repeated_check"], False)
                self.assertIn("Settings and Automatic/PID are saved", result["instructions"])
                self.assertIn("you do not need to press the button again", result["instructions"])
                self.assertNotIn("pending_resume_probe", runtime.record)

    async def test_latched_authority_hold_retains_explicit_physical_checks(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method):
                runtime = await self.dispatched_target(method=method, age=121)
                runtime.record["paused"] = "native_retry_authority_or_state_changed"
                result = self.read_without_side_effects(runtime)
                self.assert_target_feedback(result)
                self.assertEqual(result["decision"], "first_check")
                self.assertIs(result["needs_physical_check"], True)
                self.assertIsNot(result.get("requires_user_repeated_check"), False)
                self.assertNotIn("settings_saved", result)
                self.assertIn("60 seconds", result["instructions"])
                self.assertIn("press Check and Continue again", result["instructions"])
                self.assertNotIn("pending_resume_probe", runtime.record)
                self.assertNotIn("automatic_continue_requested", runtime.record)
                before = deepcopy(runtime.record)
                calls = deepcopy(runtime.calls)
                await runtime.tick(SPEC)
                self.assertEqual(runtime.record, before)
                self.assertEqual(runtime.calls, calls)
                self.assertEqual(runtime.statuses[-1], (
                    "paused", {"reason": "native_retry_authority_or_state_changed"},
                ))

    async def test_retained_target_keeps_its_count_and_explicit_recovery_button(self):
        tree = ast.parse((ROOT / "button.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "EquipmentResumeButton")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                      and node.name == "available")
        namespace = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), "button.py", "exec"), namespace)
        available = namespace["available"].fget
        for language in ("en", "de", "el"):
            with self.subTest(language=language):
                runtime = await self.dispatched_target(age=240, language=language)
                failed = deepcopy(runtime.record["pending"])
                failed["attempts"] = 4
                runtime.record["unconfirmed_native_target"] = failed
                runtime.record["pending"] = None
                result = self.read_without_side_effects(runtime)
                self.assert_target_feedback(result, language=language)
                self.assertEqual(result["command_attempts"], 4)
                self.assertIs(result["retry_limit_reached"], True)
                self.assertIs(result["requires_user_repeated_check"], False)
                self.assertIn("4", result["instructions"])
                button = N(_manager=N(equipment=runtime), _spec=SPEC,
                           controller_settings=runtime.manager.settings)
                self.assertTrue(available(button))
                runtime.record.pop("unconfirmed_native_target")
                self.assertFalse(available(button))


if __name__ == "__main__":
    unittest.main(verbosity=2)
