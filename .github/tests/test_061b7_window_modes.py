"""Window-remedy advice follows the same scoped mode as the single actuator.

Uses the production automatic direction selector, demand predicate and wait
state machine. HA ownership/presence are simulated by the established b6
fixture; no services are sent.
"""
from dataclasses import replace
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
b = runpy.run_path(str(ROOT / ".github/tests/test_061b6_window_wait.py"))
Manager, SPEC, Cap, logic, wait, model = (
    b[key] for key in ("Manager", "SPEC", "Cap", "logic", "wait", "model")
)
activation = sys.modules[model.__name__.rpartition(".")[0] + ".device_activation"]


def room(mode=None, *, method="automatic", reasons=("inside_mold",), enabled=False):
    manager = Manager()
    manager.capabilities[SPEC.identifier] = replace(Cap(),
        modes=("off", "heat", "cool", "dry", "fan_only"), temperature=True)
    manager.settings["climate_rooms"]["room"].pop("dry_climate_entity", None)
    manager.cfg.update(control_mode=method, requested_mode=mode,
                       announce_before_start=enabled)
    if mode is not None:
        manager.cfg["operating_mode"] = mode
    manager.targets.update(heat=20, cool=26, humidity=48.8)
    manager.measurements.update(temperature=22, humidity=55.8, pm25=40, co2=1400)
    climate_plan = manager.original.environment["room"]["climate_plan"]
    climate_plan.update(air_evidence_at=manager.now, air_actions={
        "outdoor_air_verified": True,
        "thresholds": {"pm25_short_term_action_ug_m3": 25, "co2_operational_ppm": 1000},
    })
    rec = replace(manager.original.recommendations[0],
                  reasons=tuple(logic.Reason(code, code, "80") for code in reasons))
    manager.original = replace(manager.original, recommendations=(rec,))
    return manager


class ScopedWindowModes(unittest.TestCase):
    def demand(self, manager):
        return wait._native_demands(manager, "room", manager.original.environment["room"]["climate_plan"])[
            "climate.dry"]

    def test_scoped_automatic_heat_cannot_promise_drying_or_suppress_mold(self):
        for enabled in (False, True):
            manager = room("heat", enabled=enabled)
            manager._recalculate()
            demand = self.demand(manager)
            self.assertEqual(demand.effect, "heat")
            self.assertIs(demand.needed, False, "Selected HEAT is satisfied despite a separate drying need")
            recommendation = manager.plan.recommendations[0]
            self.assertEqual(recommendation.wait_devices, ())
            self.assertTrue(manager.window_open_wait.should_announce(recommendation))
            self.assertEqual(manager.window_open_wait.announcement_request(recommendation).reasons,
                             recommendation.reasons)

    def test_selected_heat_remains_heat_even_when_shared_compressor_has_humidity_demand(self):
        manager = room("heat", reasons=("inside_mold", "climate_window_heat"))
        manager.measurements["temperature"] = 17
        manager._recalculate()
        demand = self.demand(manager)
        self.assertEqual(demand.effect, "heat")
        self.assertIs(demand.needed, True)
        filtered = manager.window_open_wait.announcement_request(manager.plan.recommendations[0])
        self.assertEqual([reason.code for reason in filtered.reasons], ["inside_mold"])

    def test_legacy_unpinned_automatic_still_selects_dry_and_preserves_thermal_priority(self):
        manager = room()
        manager._recalculate()
        self.assertEqual(self.demand(manager).effect, "dry")
        self.assertIs(self.demand(manager).needed, True)
        self.assertFalse(manager.window_open_wait.should_announce(manager.plan.recommendations[0]))
        manager.measurements["temperature"] = 17
        manager._recalculate()
        self.assertEqual(self.demand(manager).effect, "heat")
        self.assertTrue(manager.window_open_wait.should_announce(manager.plan.recommendations[0]))

    def test_multimode_fan_only_uses_qualified_particle_demand_and_preserves_co2(self):
        with patch.object(activation, "effective_device", return_value={
                "auto_control": True, "fan_purpose": "filtration", "sensor_verified": True}):
            for method in ("automatic", "pid"):
                manager = room("fan_only", method=method, reasons=("inside_pm25", "inside_co2"))
                manager._recalculate()
                demand = self.demand(manager)
                self.assertEqual(demand.effect, "filtration")
                self.assertTrue(demand.allowed)
                self.assertIs(demand.needed, True)
                filtered = manager.window_open_wait.announcement_request(manager.plan.recommendations[0])
                self.assertEqual([reason.code for reason in filtered.reasons], ["inside_co2"])

    def test_enabled_multimode_filtration_wait_names_only_matching_remedy(self):
        with patch.object(activation, "effective_device", return_value={
                "auto_control": True, "fan_purpose": "filtration", "sensor_verified": True}):
            manager = room("fan_only", reasons=("inside_pm25",), enabled=True)
            manager._recalculate()
            recommendation = manager.plan.recommendations[0]
            self.assertEqual(len(recommendation.wait_devices), 1)
            self.assertEqual(recommendation.wait_devices[0]["effect"], "filtration")
            self.assertTrue(manager.window_open_wait.should_announce(recommendation))

    def test_wrong_role_unverified_or_missing_particles_never_cover_particle_warning(self):
        for purpose, verified, measured in (("extraction", True, 40), ("auto", True, 40),
                                            ("filtration", False, 40), ("filtration", True, None)):
            with self.subTest(purpose=purpose, verified=verified, measured=measured), \
                    patch.object(activation, "effective_device", return_value={
                        "auto_control": True, "fan_purpose": purpose, "sensor_verified": verified}):
                manager = room("fan_only", reasons=("inside_pm25",), enabled=True)
                manager.measurements["pm25"] = measured
                manager._recalculate()
                recommendation = manager.plan.recommendations[0]
                self.assertEqual(recommendation.wait_devices, ())
                self.assertTrue(manager.window_open_wait.should_announce(recommendation))
                self.assertEqual(manager.window_open_wait.announcement_request(recommendation).reasons,
                                 recommendation.reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
