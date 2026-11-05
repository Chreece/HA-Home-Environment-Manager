"""Report the same native control field that a pending command expects.

The lifecycle cases reuse Beta106's isolated HA transport fixture and execute
production tick, power/target selection, dispatch, matches, reconciliation and
resume_information. Service completion never fabricates physical feedback.
The pure formatter cases cover other control fields and localized units.

For a diagnostic-only before/after comparison, HEM_TEST_RUNTIME_SOURCE and
HEM_TEST_RESUME_SOURCE can select both source files from an older release.
Optional formatter keywords are omitted only when an older function signature
has no such parameter, so the old baseline fails assertions about diagnostics
rather than failing because the new API did not exist.
"""
from __future__ import annotations

from copy import deepcopy
import inspect
import os
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_onoff_native_extrema.py"))
NativeRuntime, SPEC, PRIMARY, production = (
    fixture[name] for name in ("NativeRuntime", "SPEC", "PRIMARY", "production")
)
resume = fixture["load_pure"](
    "equipment_resume",
    Path(os.environ.get("HEM_TEST_RESUME_SOURCE", ROOT / "equipment_resume.py")),
)
fixture["extract"](fixture["RUNTIME"], ("resume_information",), production.__dict__)
NativeRuntime.resume_information = production.resume_information
NOW = 100000.0


def feedback(expected, state, *, language="en", temperature_unit=None):
    pending = {
        "entity": PRIMARY, "phase": "commanded", "when": NOW - 30,
        "service": "set_temperature", "expected": deepcopy(expected),
        "power": False, "output_on": True,
    }
    optional = {"language": language, "temperature_unit": temperature_unit}
    supported = inspect.signature(resume.check_pending).parameters
    return resume.check_pending(
        pending, state, NOW, None,
        matches_expected=production.matches(state, expected),
        **{key: value for key, value in optional.items() if key in supported},
    )


def native(mode="heat", **attributes):
    return N(state=mode, attributes=attributes)


def config(runtime, language="en", unit="°C"):
    runtime.hass.config = N(language=language, units=N(temperature_unit=unit))


class SetpointLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_heat_and_cool_ack_requires_target_attribute_for_both_methods(self):
        for method in ("pid", "automatic"):
            for mode, original, requested, actual_room in (
                ("heat", 5.0, 30.0, 18.6), ("cool", 30.0, 5.0, 29.0),
            ):
                with self.subTest(method=method, mode=mode):
                    runtime = NativeRuntime(method, mode, low=5.0, high=30.0)
                    config(runtime)
                    runtime.state.attributes["current_temperature"] = actual_room
                    await runtime.tick(SPEC)
                    self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": mode})
                    self.assertFalse(runtime.record["power"])
                    runtime.now += 5
                    runtime.report(mode=mode)
                    await runtime.tick(SPEC)
                    self.assertEqual(len(runtime.calls), 1, "No setpoint during the native ON startup grace")
                    runtime.now += 30
                    await runtime.tick(SPEC)
                    self.assertEqual(runtime.calls[-1], {
                        "domain": "climate", "service": "set_temperature",
                        "data": {"temperature": requested},
                        "target": {"entity_id": PRIMARY},
                    })
                    pending = runtime.record["pending"]
                    self.assertEqual(pending["expected"], {
                        "attributes": {"temperature": requested},
                    })
                    self.assertEqual(runtime.state.attributes["temperature"], original)
                    self.assertFalse(production.matches(runtime.state, pending["expected"]))
                    runtime.now += 5
                    await runtime.tick(SPEC)
                    self.assertIs(runtime.record["pending"], pending)
                    self.assertEqual(runtime.statuses[-1][0], "awaiting_physical_acknowledgement")
                    self.assertEqual(len(runtime.calls), 2)
                    details = runtime.resume_information(SPEC)
                    self.assertEqual(details["requested"], f"Temperature setpoint {requested:g} °C")
                    self.assertEqual(details["observed"], f"Temperature setpoint {original:g} °C")
                    self.assertNotEqual(details["observed"], mode)
                    owned_since = runtime.record["power"][PRIMARY]["since"]
                    runtime.report(temperature=requested)
                    self.assertTrue(production.matches(runtime.state, pending["expected"]))
                    await runtime.tick(SPEC)
                    self.assertIsNone(runtime.record["pending"])
                    self.assertEqual(len(runtime.calls), 2)
                    self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
                    self.assertEqual(runtime.state.attributes["current_temperature"], actual_room)
                    self.assertNotEqual(actual_room, requested, "ACK is the setpoint, not measured room temperature")

    async def test_current_temperature_does_not_acknowledge_a_target_write(self):
        runtime = NativeRuntime("pid", "heat", low=5.0, high=30.0)
        config(runtime)
        runtime.own_running()
        await runtime.tick(SPEC)
        runtime.state.attributes["current_temperature"] = 30.0
        pending = runtime.record["pending"]
        self.assertEqual(runtime.state.state, "heat")
        self.assertEqual(runtime.state.attributes["temperature"], 5.0)
        self.assertFalse(production.matches(runtime.state, pending["expected"]))
        runtime.now += 5
        self.assertFalse(await runtime._reconcile(SPEC))
        self.assertIs(runtime.record["pending"], pending)
        details = runtime.resume_information(SPEC)
        self.assertEqual(details["observed"], "Temperature setpoint 5 °C")
        self.assertEqual(len(runtime.calls), 1)

    async def test_missing_reported_target_stays_pending_and_does_not_show_mode(self):
        runtime = NativeRuntime("pid", "heat", low=5.0, high=30.0)
        config(runtime)
        runtime.own_running()
        await runtime.tick(SPEC)
        pending = runtime.record["pending"]
        runtime.state.attributes.pop("temperature")
        runtime.now += 5
        self.assertFalse(production.matches(runtime.state, pending["expected"]))
        self.assertFalse(await runtime._reconcile(SPEC))
        self.assertIs(runtime.record["pending"], pending)
        details = runtime.resume_information(SPEC)
        self.assertIn("unavailable", details["observed"].lower())
        self.assertNotIn("heat", details["observed"])
        self.assertEqual(len(runtime.calls), 1)

    async def test_runtime_uses_home_assistant_unit_when_native_unit_is_absent(self):
        runtime = NativeRuntime("pid", "heat", low=5.0, high=30.0,
                                absent=("temperature_unit",))
        config(runtime, unit="°C")
        runtime.own_running()
        await runtime.tick(SPEC)
        details = runtime.resume_information(SPEC)
        self.assertEqual(details["requested"], "Temperature setpoint 30 °C")
        self.assertEqual(details["observed"], "Temperature setpoint 5 °C")


class NativeFeedbackFormattingTests(unittest.TestCase):
    def test_temperature_compares_target_to_target(self):
        result = feedback({"attributes": {"temperature": 30.0}}, native(
            temperature=5.0, current_temperature=18.6, temperature_unit="°C",
        ))
        self.assertEqual(result["requested"], "Temperature setpoint 30 °C")
        self.assertEqual(result["observed"], "Temperature setpoint 5 °C")
        self.assertEqual(result["decision"], "settling")

    def test_mode_only_diagnostics_keep_the_existing_mode_strings(self):
        for expected, actual in (("heat", "cool"), ("off", "heat"), ("cool", "cool")):
            with self.subTest(expected=expected, actual=actual):
                result = feedback({"state": expected}, native(actual, temperature=5.0))
                self.assertEqual(result["requested"], expected)
                self.assertEqual(result["observed"], actual)
                self.assertEqual(result["decision"], "confirmed" if expected == actual else "settling")

    def test_each_attribute_reports_its_own_observed_value(self):
        for attribute, desired, actual, suffix in (
            ("humidity", 55, 40, "%"),
            ("percentage", 70, 20, "%"),
            ("preset_mode", "comfort", "away", ""),
            ("fan_mode", "high", "low", ""),
        ):
            with self.subTest(attribute=attribute):
                result = feedback({"attributes": {attribute: desired}},
                                  native(**{attribute: actual, "temperature": 5.0}))
                self.assertIn(str(desired), result["requested"])
                self.assertIn(str(actual), result["observed"])
                self.assertNotEqual(result["observed"], "heat")
                if suffix:
                    self.assertIn(suffix, result["requested"])
                    self.assertIn(suffix, result["observed"])
                self.assertEqual(result["decision"], "settling")

    def test_target_range_reports_both_limits_and_observes_both_limits(self):
        result = feedback({"attributes": {"target_temp_low": 16.0, "target_temp_high": 24.0}},
                          native(target_temp_low=17.0, target_temp_high=23.0,
                                 temperature=5.0, temperature_unit="°C"))
        for value in ("16 °C", "24 °C"):
            self.assertIn(value, result["requested"])
        for value in ("17 °C", "23 °C"):
            self.assertIn(value, result["observed"])
        self.assertNotIn("5 °C", result["observed"])
        self.assertEqual(result["decision"], "settling")

    def test_combined_mode_and_target_reports_all_expected_fields(self):
        result = feedback({"state": "heat", "attributes": {"temperature": 30.0}},
                          native("cool", temperature=5.0, temperature_unit="°C"))
        self.assertIn("heat", result["requested"])
        self.assertIn("30 °C", result["requested"])
        self.assertIn("cool", result["observed"])
        self.assertIn("5 °C", result["observed"])
        self.assertEqual(result["decision"], "settling")

    def test_missing_and_unavailable_feedback_never_substitutes_a_mode(self):
        expected = {"attributes": {"temperature": 30.0}}
        for state in (None, native("unknown", temperature=30.0),
                      native("unavailable", temperature=30.0), native("heat")):
            with self.subTest(state=getattr(state, "state", None)):
                result = feedback(expected, state, temperature_unit="°C")
                self.assertIn("unavailable", result["observed"].lower())
                self.assertNotIn("heat", result["observed"])
                self.assertNotIn("30", result["observed"], "Do not present stale attributes as live feedback")
                self.assertNotEqual(result["decision"], "confirmed")

    def test_native_fahrenheit_and_fallback_celsius_preserve_native_values(self):
        result = feedback({"attributes": {"temperature": 95.0}}, native(
            temperature=41.0, temperature_unit="°F",
        ), temperature_unit="°C")
        self.assertEqual(result["requested"], "Temperature setpoint 95 °F")
        self.assertEqual(result["observed"], "Temperature setpoint 41 °F")
        result = feedback({"attributes": {"temperature": 30.0}},
                          native(temperature=5.0), temperature_unit="°C")
        self.assertEqual(result["requested"], "Temperature setpoint 30 °C")
        self.assertEqual(result["observed"], "Temperature setpoint 5 °C")

    def test_localized_labels_match_on_both_sides(self):
        english = None
        for language in ("en", "de-DE", "el-GR"):
            with self.subTest(language=language):
                result = feedback({"attributes": {"temperature": 30.0}},
                                  native(temperature=5.0, temperature_unit="°C"), language=language)
                self.assertTrue(result["requested"].endswith("30 °C"))
                self.assertTrue(result["observed"].endswith("5 °C"))
                requested_label = result["requested"][:-len("30 °C")]
                observed_label = result["observed"][:-len("5 °C")]
                self.assertEqual(requested_label, observed_label)
                self.assertTrue(requested_label.strip())
                if language == "en":
                    english = requested_label
                else:
                    self.assertNotEqual(requested_label, english)
                if language.startswith("el"):
                    self.assertRegex(requested_label, r"[Α-Ωα-ω]")
                self.assertEqual(result["decision"], "settling")


if __name__ == "__main__":
    unittest.main(verbosity=2)
