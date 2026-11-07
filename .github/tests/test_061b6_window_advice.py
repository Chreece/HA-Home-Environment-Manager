"""Proven indoor remedies require a matching, measured outside alternative."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]
b = runpy.run_path(str(Path(__file__).with_name("test_061b5_window_advice.py")))
logic, climate, physics, Weather, Reading, OUTDOOR, room = (
    b[key] for key in ("logic", "climate", "physics", "Weather", "Reading", "OUTDOOR", "room")
)


class IndoorAlternatives(unittest.TestCase):
    def setUp(self):
        self.fixture = b["MeasuredSubstitution"]()
        self.fixture.setUp()
        self.f = self.fixture
        self.f.plan.update(status="advisory", temperature_c=21., equipment_plan={}, humidity_management={})

    def humidify(self, *, inside_rh=30., outside_c=21., outside_rh=65.):
        self.f.add("humidifier.moisture", "off", device_class="humidifier")
        self.f.settings = {"enabled": True, "selected_devices": ["humidifier.moisture"]}
        self.f.weather = (Weather("weather.home", "sunny", outside_c, outside_rh, 5),)
        self.f.science = {"moisture": physics.moisture_potential(21., inside_rh, outside_c, outside_rh)}
        self.f.pending = ({"entity_id": "humidifier.moisture", "effect": "humidify", "temperature_c": 21.,
                           "humidity_percent": inside_rh, "target_humidity": 45.},)

    def filtration(self):
        self.f.add("fan.purifier", "off")
        self.f.settings = {"enabled": True, "selected_devices": ["fan.purifier"]}
        self.f.pending = ({"entity_id": "fan.purifier", "effect": "filtration", "temperature_c": 21.,
                           "pm25_ug_m3": 55., "target_pm25": 15., "fan_purpose": "filtration"},)

    def evaluate(self, *, outdoor=OUTDOOR, **kwargs):
        return climate.window_substitution(
            self.f.hass, room(), self.f.settings, self.f.plan, self.f.science,
            self.f.weather, outdoor, outside_safe=kwargs.pop("outside_safe", True),
            pending_demands=self.f.pending, **kwargs)

    def test_humidifier_has_opportunity_only_from_measured_moisture_gain(self):
        self.humidify()
        advice = self.evaluate()
        self.assertEqual(advice["effect"], "humidify")
        self.assertEqual(advice["devices"], ("humidifier.moisture",))
        self.assertGreaterEqual(advice["evidence"]["humidity_ratio_advantage_g_kg"], 1.5)
        self.assertGreaterEqual(advice["evidence"]["outside_rh_when_warmed_percent"], 47.)
        self.assertEqual(climate.window_reason(advice).code, "climate_window_humidify")
        self.assertIn("g/kg", climate.window_reason(advice).value)
        self.assertEqual(self.f.states["humidifier.moisture"].state, "off")
        self.assertFalse(advice["automatic_control"])

    def test_cold_high_outdoor_relative_humidity_is_not_a_humidification_benefit(self):
        self.humidify(outside_c=2., outside_rh=95.)
        self.assertNotEqual(self.evaluate()["status"], "opportunity")
        self.humidify(outside_c=21., outside_rh=65.)
        self.f.science = {"moisture": {"status": "unavailable"}}
        self.assertEqual(self.evaluate()["status"], "measured_outdoor_humidifying_not_verified")
        self.humidify(inside_rh=45.)
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")

    def test_wrong_humidity_device_class_cannot_supply_the_opposite_remedy(self):
        self.humidify()
        self.f.states["humidifier.moisture"].attributes["device_class"] = "dehumidifier"
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")

    def test_purifier_opportunity_compares_same_measured_pollutant_and_target(self):
        self.filtration()
        advice = self.evaluate()
        self.assertEqual(advice["status"], "opportunity")
        self.assertEqual(advice["effect"], "filtration")
        self.assertEqual(advice["evidence"]["pm25_advantage_ug_m3"], 50.)
        self.assertEqual(advice["evidence"]["outdoor_pm25_ug_m3"], 5.)
        self.assertEqual(climate.window_reason(advice).code, "climate_window_filtration")
        self.assertEqual(climate.window_reason(advice).value, "50 µg/m³")
        self.assertEqual(self.f.states["fan.purifier"].state, "off")
        self.assertFalse(advice["automatic_control"])

    def test_unrelated_outdoor_aqi_co2_or_missing_pm_do_not_prove_particle_benefit(self):
        self.filtration()
        alternatives = (
            (), (Reading("sensor.co2", "Outdoor CO2", "co2", 400.),),
            (Reading("sensor.aqi", "Outdoor AQI", "aqi", 2.),),
            (Reading("sensor.pm", "Outdoor PM2.5", "pm25", None),),
        )
        for outdoor in alternatives:
            self.assertEqual(self.evaluate(outdoor=outdoor)["status"],
                             "measured_outdoor_particle_benefit_not_verified")
        for concentration in (14., 30., 55., 80.):
            self.assertEqual(self.evaluate(outdoor=(Reading("sensor.pm", "Outdoor PM2.5", "pm25", concentration),))["status"],
                             "outside_particles_not_low_enough")

    def test_particle_reading_must_be_above_its_real_control_target(self):
        self.filtration()
        for value in (None, 0., 15., 16., 17.):
            self.f.pending[0]["pm25_ug_m3"] = value
            self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")

    def test_filtration_role_is_explicit_and_extraction_is_never_a_substitute(self):
        self.filtration()
        self.f.pending[0].pop("fan_purpose")
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")
        self.f.settings["purifier_fan_entity"] = "fan.purifier"
        self.assertEqual(self.evaluate()["status"], "opportunity")
        self.f.settings["extraction_fan_entity"] = "fan.purifier"
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")

    def test_resolved_controller_role_precedes_old_room_assignment(self):
        self.filtration()
        self.f.settings["extraction_fan_entity"] = "fan.purifier"
        self.assertEqual(self.evaluate()["status"], "opportunity")
        self.f.pending[0]["fan_purpose"] = "extraction"
        self.f.settings["purifier_fan_entity"] = "fan.purifier"
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")
        self.f.pending[0].pop("fan_purpose")
        self.f.settings["device_settings"] = {"fan.purifier": {"fan_purpose": "filtration"}}
        self.assertEqual(self.evaluate()["status"], "opportunity")

    def test_both_new_alternatives_generate_normal_room_advice_with_cautions(self):
        for prepare in (self.humidify, self.filtration):
            prepare()
            caution = (logic.Reason("weather_cold", value="7 °C"),)
            option = self.evaluate(outside_safe=False, outside_reasons=caution)
            self.assertEqual(option["status"], "opportunity")
            self.assertFalse(option["outside_safe"])
            option["notify_enabled"] = True
            environment = {"room": {"climate_plan": {"window_efficiency": option}}}
            plan = logic.evaluate(OUTDOOR, self.f.weather, (), (room(),), environment=environment)
            self.assertEqual(len(plan.recommendations), 1)
            rec = plan.recommendations[0]
            self.assertEqual(rec.action, "open")
            self.assertIn("climate_window_" + option["effect"], [reason.code for reason in rec.reasons])
            self.assertIn(caution[0], rec.cautions)


if __name__ == "__main__":
    unittest.main()
