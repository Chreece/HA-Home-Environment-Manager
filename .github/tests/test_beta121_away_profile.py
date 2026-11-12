"""Restart and command-time Home/Away targets use verified live presence.

The production presence policy, continuity store logic and complete equipment
model run against the existing simulated HA state/area registry. No HA service
or physical equipment is used. Runtime dispatch guards have their own tests.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib.util
from pathlib import Path
import runpy
import sys
from types import MappingProxyType, SimpleNamespace as N
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(Path(__file__).with_name("test_home_presence_authority.py")))
package = fixture["PACKAGE"]
module_spec = importlib.util.spec_from_file_location(
    package + ".away_profile_model", ROOT / "equipment_model.py",
)
model = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = model
module_spec.loader.exec_module(model)

AREA, ROOMS = fixture["AREA"], fixture["ROOMS"]
PERSON = fixture["PERSON"]
TEMPERATURE = 19.0
LIMITS = {
    "temperature_min_limit": 5.0, "temperature_max_limit": 35.0,
    "humidity_min_limit": 20.0, "humidity_max_limit": 80.0,
}


class AwayProfileTests(unittest.TestCase):
    def setUp(self):
        self.hass = fixture["Hass"]()
        self.shared = {"home_trackers": [PERSON], "occupied_rooms_entity": ROOMS,
                       "source_stale_minutes": 240}
        self.room = {
            "occupancy_sensors": [],
            "profiles": {
                "away": {"heat_c": 10.0, "cool_c": 30.0},
                "home": {"heat_c": 21.0, "cool_c": 25.0},
                "comfort": {"heat_c": 22.0, "cool_c": 24.0},
            },
        }
        self.cached = {
            "status": "ready", "away": "home", "occupancy": "occupied",
            "sleeping": False, "profile": "comfort",
            "global_presence": deepcopy(self.shared),
            "known_presence_areas": [AREA], "window_safe": True,
            "air_evidence_at": 123.0,
        }
        self.spec = model.ManagedDevice(
            "heater", AREA, "Heater", "native_heater", ("climate.heater",),
        )
        self.cap = model.Capabilities(
            "climate.heater", "climate", ("off", "heat"), temperature=True,
        )
        self.manager = N(
            hass=self.hass,
            settings={"occupancy_global": self.shared,
                      "climate_rooms": {AREA: self.room},
                      model.SETTINGS: {"heater": {"control_mode": "pid", "preset": "none"}}},
            plan=N(environment={AREA: {"climate_plan": self.cached}}),
            presence_continuity=fixture["continuity"].PresenceContinuity(
                self.hass, "entry", store=fixture["Store"](),
            ),
        )
        self.hass.put(ROOMS, "[]")
        self.hass.put(PERSON, "not_home")

    def evaluate(self):
        config = model.settings(self.manager, self.spec)
        facts = model.plan_for(self.manager, self.spec)
        with patch.object(model, "device_limits", return_value=LIMITS):
            target = model.targets(self.manager, self.spec, self.cap, config, facts)["heat"]
        return facts, model.profile_name(config, facts), target, model.automatic_profile_reason(config, facts)

    def test_restored_missing_unavailable_and_old_home_sources_cannot_authorize_home_heat(self):
        for entity, away_state in (
            (PERSON, "not_home"),
            ("device_tracker.phone", "work"),
            ("binary_sensor.somebody_home", "off"),
            ("sensor.people_at_home", "0"),
        ):
            self.shared["home_trackers"] = [entity]
            for condition in ("restored", "missing", "unavailable", "unknown", "old"):
                with self.subTest(entity=entity, condition=condition):
                    self.hass.put(entity, away_state)
                    facts, profile, target, hold = self.evaluate()
                    self.assertEqual((facts["away"], profile, target, hold),
                                     ("away", "away", 10.0, None))
                    self.assertGreater(TEMPERATURE, target)
                    if condition == "missing":
                        self.hass.states.data.pop(entity)
                    else:
                        self.hass.put(
                            entity, condition if condition in ("unavailable", "unknown") else away_state,
                            attributes={"restored": True} if condition == "restored" else {},
                            age=400 if condition == "old" else 1,
                        )
                    facts, profile, target, hold = self.evaluate()
                    self.assertEqual(facts["away"], "unknown")
                    self.assertEqual(facts["away_evidence"], "unverified_home_trackers")
                    self.assertEqual(facts["occupancy"], "unoccupied")
                    # The display fallback remains Home, not fabricated Away.
                    # Its higher target MUST NOT authorize heat at 19 degrees.
                    self.assertEqual((profile, target), ("home", 21.0))
                    self.assertLess(TEMPERATURE, target)
                    self.assertEqual(hold, "house_occupancy_unknown")

    def test_live_away_target_recovers_without_changing_the_controller_mode(self):
        self.hass.put(PERSON, "unavailable")
        self.assertEqual(self.evaluate()[3], "house_occupancy_unknown")
        self.hass.put(PERSON, "not_home")
        facts, profile, target, hold = self.evaluate()
        self.assertEqual((facts["away"], profile, target, hold), ("away", "away", 10.0, None))
        self.assertGreater(TEMPERATURE, target)
        self.assertEqual(self.manager.settings[model.SETTINGS]["heater"]["control_mode"], "pid")

    def test_cached_home_refreshes_away_without_sleep_or_alarm_settings(self):
        original = deepcopy(self.cached)
        self.hass.forbid_room_reads()
        facts, profile, target, hold = self.evaluate()
        self.assertEqual((facts["away"], facts["occupancy"], profile, target, hold),
                         ("away", "unoccupied", "away", 10.0, None))
        self.assertIsNot(facts, self.cached)
        self.assertEqual(self.cached, original)
        self.assertEqual(facts["air_evidence_at"], 123.0)
        self.assertTrue(facts["window_safe"])

    def test_return_home_refreshes_room_presence_missing_from_cached_away(self):
        self.cached.update(away="away", occupancy="unoccupied", profile="away")
        self.hass.put(PERSON, "home")
        self.hass.put(ROOMS, AREA)
        facts, profile, target, hold = self.evaluate()
        self.assertEqual((facts["away"], facts["occupancy"], profile, target, hold),
                         ("home", "occupied", "comfort", 22.0, None))
        self.assertEqual(self.cached["away"], "away")

    def test_current_source_selection_supersedes_cached_tracker(self):
        replacement = "person.replacement"
        self.hass.put(PERSON, "home")
        self.hass.put(replacement, "not_home")
        self.manager.settings["occupancy_global"] = MappingProxyType({"home_trackers": [replacement]})
        self.hass.states.blocked.add(PERSON)
        facts, profile, target, hold = self.evaluate()
        self.assertEqual((facts["away"], profile, target, hold), ("away", "away", 10.0, None))
        self.assertEqual(facts["tracker_entities"], [replacement])

    def test_current_freshness_setting_wins_over_cached_configuration(self):
        self.hass.put(PERSON, "not_home", age=20)
        self.manager.settings["occupancy_global"] = {"home_trackers": [PERSON], "source_stale_minutes": 10}
        self.assertEqual(self.evaluate()[0]["away"], "away", "Automatic uses the type-based 240-minute limit")
        self.manager.settings["occupancy_global"]["source_freshness_mode"] = "custom"
        facts, _, _, hold = self.evaluate()
        self.assertEqual((facts["away"], hold), ("unknown", "house_occupancy_unknown"))
        self.manager.settings["occupancy_global"]["source_stale_minutes"] = 60
        self.assertEqual(self.evaluate()[1:], ("away", 10.0, None))

    def test_intentionally_empty_current_configuration_discards_cached_sources(self):
        self.manager.settings["occupancy_global"] = {}
        self.cached["global_presence"].update(
            sleep_rooms_entity="sensor.old_sleep", wake_alarm_entity="sensor.old_alarm",
            wake_lead_minutes_entity="input_number.old_lead",
        )
        self.hass.states.blocked.update((PERSON, ROOMS, "sensor.old_sleep", "sensor.old_alarm"))
        facts, profile, target, hold = self.evaluate()
        self.assertEqual((facts["away"], profile, target, hold), ("home", "home", 21.0, None))
        self.assertEqual(facts["away_evidence"], "no_trackers_assume_home")
        self.assertEqual(facts["tracker_entities"], [])
        self.assertNotIn("home_trackers", facts["global_presence"])
        self.assertNotIn("wake_alarm_entity", facts["global_presence"])

    def test_legacy_caller_without_current_configuration_can_supply_plan_context(self):
        self.manager.settings.pop("occupancy_global")
        self.assertEqual(self.evaluate()[1:], ("away", 10.0, None))

    def test_persisted_absence_is_revalidated_after_reload_and_never_fabricates_away(self):
        self.evaluate()
        saved = self.manager.presence_continuity._snapshot()
        self.assertIsNotNone(saved["verified_absence_since"])
        restarted = fixture["continuity"].PresenceContinuity(
            self.hass, "entry", store=fixture["Store"](saved),
        )
        asyncio.run(restarted.async_start())
        self.manager.presence_continuity = restarted
        self.hass.put(PERSON, "not_home", attributes={"restored": True})
        facts, profile, _, hold = self.evaluate()
        self.assertEqual((facts["away"], profile, hold), ("unknown", "home", "house_occupancy_unknown"))
        self.assertNotIn("_verified_absence_since", facts["global_presence"])
        self.assertEqual(restarted._since, saved["verified_absence_since"])
        self.hass.put(PERSON, "not_home", changed_age=0)
        facts, profile, target, hold = self.evaluate()
        self.assertEqual((facts["away"], profile, target, hold), ("away", "away", 10.0, None))
        self.assertEqual(facts["global_presence"]["_verified_absence_since"], saved["verified_absence_since"])

    def test_explicit_presets_and_manual_control_keep_their_authority(self):
        self.hass.put(PERSON, "unavailable")
        profile = self.manager.settings[model.SETTINGS]["heater"]
        for mode in ("automatic", "pid"):
            for requested in ("home", "comfort", "away", "sleep", "eco"):
                with self.subTest(mode=mode, requested=requested):
                    profile.update(control_mode=mode, preset=requested)
                    facts, selected, _, hold = self.evaluate()
                    self.assertEqual(facts["away"], "unknown")
                    self.assertEqual(selected, requested)
                    self.assertIsNone(hold)
            profile.update(control_mode=mode, preset="none")
            self.assertEqual(self.evaluate()[3], "house_occupancy_unknown")
        profile.update(control_mode="manual", preset="none")
        self.assertEqual(self.evaluate()[1], "manual")
        self.assertIsNone(self.evaluate()[3])
        for mode in ("existing", "off"):
            self.assertIsNone(model.automatic_profile_reason({"control_mode": mode}, {"away": "unknown"}))

    def test_missing_or_invalid_implicit_profile_evidence_is_not_home_authority(self):
        for mode in ("automatic", "pid"):
            for requested in ("none", "invalid"):
                self.assertEqual(model.automatic_profile_reason(
                    {"control_mode": mode, "preset": requested}, {},
                ), "house_occupancy_unknown")
            for home in ("home", "away"):
                self.assertIsNone(model.automatic_profile_reason({"control_mode": mode}, {"away": home}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
