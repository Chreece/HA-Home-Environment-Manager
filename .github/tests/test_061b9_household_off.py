"""Keep-off preference uses live household proof, independently of sleep targets."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import importlib
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_beta120_device_sleep.py"))
policy, model = base["policy"], base["model"]
FLAG, PRESENCE, SLEEP = base["FLAG"], base["PRESENCE"], base["SLEEP"]


class HouseholdOff(unittest.TestCase):
    setUp = base["DeviceSleep"].setUp
    facts = base["DeviceSleep"].facts

    def device(self, **changes):
        return {FLAG: True, "auto_control": True, "presence_requirement": "always",
                "sleep_behavior": "normal", **changes}

    def permission(self, device=None, plan=None):
        return policy.live_device_permission(
            self.hass, "living", self.manager.settings["climate_rooms"]["living"],
            self.facts(self.a) if plan is None else plan,
            self.device() if device is None else device,
        )

    def test_all_sleeping_keeps_each_normal_or_target_policy_off(self):
        self.assertEqual(self.facts(self.a)["occupancy"], "unoccupied")
        for behavior in ("normal", "sleep_targets", "pause"):
            with self.subTest(behavior=behavior):
                self.assertEqual(self.permission(self.device(sleep_behavior=behavior)),
                                 ("held", "sleep_room_control_paused"))
        self.assertFalse(self.plan["sleeping"], "Device policy must not mutate the shared room plan")

    def test_option_off_leaves_normal_and_target_policies_alone(self):
        for behavior in ("normal", "sleep_targets"):
            with self.subTest(behavior=behavior):
                self.assertEqual(self.permission(self.device(**{FLAG: False, "sleep_behavior": behavior}))[0],
                                 "eligible")

    def test_new_awake_occupant_releases_cached_household_hold(self):
        cached = self.facts(self.a)
        self.assertEqual(self.permission(plan=cached)[1], "sleep_room_control_paused")
        self.hass.put(PRESENCE, '["Living room","Bathroom"]')
        self.assertEqual(self.permission(plan=cached)[0], "eligible")

    def test_one_sleeping_room_does_not_mean_everyone_asleep(self):
        self.hass.put(PRESENCE, '["Living room","Bathroom"]')
        self.hass.put(SLEEP, '["Living room"]')
        self.assertTrue(self.facts(self.a)["sleeping"])
        self.assertEqual(self.permission()[0], "eligible")
        self.assertEqual(self.permission(self.device(sleep_behavior="pause"))[1],
                         "sleep_room_control_paused", "Independent room pause still applies")

    def test_empty_unknown_and_away_do_not_prove_everyone_asleep(self):
        self.hass.put(PRESENCE, '[]')
        self.assertEqual(self.permission()[0], "eligible")
        self.hass.put(PRESENCE, '["Bathroom"]')
        self.hass.put(SLEEP, "unavailable")
        self.assertEqual(self.permission()[0], "eligible")
        self.hass.put(SLEEP, '["Bathroom"]')
        self.shared["home_trackers"] = [base["fixture"]["PERSON"]]
        self.hass.put(base["fixture"]["PERSON"], "not_home")
        self.assertEqual(self.permission()[0], "eligible")

    def test_alarm_preparation_releases_keep_off_even_with_normal_room_behavior(self):
        alarm, lead = "sensor.phone_alarm", "input_number.wake_minutes"
        self.shared.update(wake_alarm_entity=alarm, wake_lead_minutes_entity=lead,
                           _wake_entry_id="entry")
        wake = base["wake"]
        self.hass.data = {wake._TRACKERS: {"entry": wake.WakeAlarm((alarm, lead), None)}}
        self.hass.put(alarm, datetime.fromtimestamp(self.now + 3600, timezone.utc).isoformat(),
                      attributes={"device_class": "timestamp"})
        self.hass.put(lead, "30", attributes={"unit_of_measurement": "min"})
        with patch("time.time", return_value=self.now + 1799):
            cached = self.facts(self.a)
            self.assertEqual(self.permission(plan=cached)[1], "sleep_room_control_paused")
        with patch("time.time", return_value=self.now + 1800):
            self.assertEqual(self.permission(plan=cached)[0], "eligible")
            self.assertEqual(self.facts(self.a)["sleep_schedule_evidence"], "wake_before_alarm")

    def test_inactive_control_and_unproven_sleep_never_gain_authority(self):
        self.assertEqual(self.permission(self.device(auto_control=False)),
                         ("held", "device_auto_control_disabled"))
        self.assertEqual(policy.device_permission(self.device(), "unoccupied", "home", True)[0],
                         "eligible", "A bare sleeping flag does not prove the household condition")
        self.assertEqual(policy.device_permission(self.device(), "unoccupied", "away", True,
                                                 household_sleeping=True)[0], "eligible")

    def test_runtime_stop_verifier_accepts_only_current_household_pause(self):
        tree = ast.parse((ROOT / "equipment_runtime.py").read_text())
        method = next(node for cls in tree.body if isinstance(cls, ast.ClassDef)
                      for node in cls.body if isinstance(node, ast.FunctionDef)
                      and node.name == "_stop_policy_verified")
        namespace = {"__package__": base["package"], "model": model,
                     "live_device_permission": policy.live_device_permission}
        exec(compile(ast.Module(body=[ast.parse("from __future__ import annotations").body[0], method],
                                type_ignores=[]), "household_stop_verifier", "exec"), namespace)
        activation = importlib.import_module(base["package"] + ".device_activation")
        runtime = N(manager=self.manager, hass=self.hass)
        cap = model.Capabilities("climate.first", "climate", ("off", "heat"), temperature=True)
        check = namespace["_stop_policy_verified"]
        with patch.object(activation, "effective_device", return_value=self.device()):
            self.assertTrue(check(runtime, self.a, cap, "sleep"))
            self.hass.put(PRESENCE, '["Living room","Bathroom"]')
            self.assertFalse(check(runtime, self.a, cap, "sleep"))
        with patch.object(activation, "effective_device", return_value=self.device(**{FLAG: False})):
            self.assertFalse(check(runtime, self.a, cap, "sleep"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
