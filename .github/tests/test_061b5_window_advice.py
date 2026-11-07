"""Conditional manual airing: real benefit, named cautions and pending demand.

The recommendation, psychrometric and native capability code is production
code. Only HA's state/area access is replaced. Any attempted service call fails.
No physical output is controlled by these advisory calculations.
"""
from __future__ import annotations

from dataclasses import replace
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem061b5windowadvice"
package = ModuleType(PKG)
package.__path__ = [str(ROOT)]
sys.modules[PKG] = package


def no_service(*args, **kwargs):
    raise AssertionError("Manual airing advice must not operate hardware")


discovery = ModuleType(PKG + ".discovery")
discovery.entity_area = lambda hass, entity: hass.areas.get(entity)
discovery.is_window = lambda hass, state: (
    state.domain == "binary_sensor" and state.attributes.get("device_class") == "window")
discovery.reading = no_service
sys.modules[discovery.__name__] = discovery

logic = importlib.import_module(PKG + ".logic")
climate = importlib.import_module(PKG + ".climate_window")
physics = importlib.import_module(PKG + ".building_physics")

Reading, Weather, Window = logic.Reading, logic.Weather, logic.Window
Room, Reason, Warning = logic.Room, logic.Reason, logic.Warning
OUTDOOR = (Reading("sensor.outside_pm", "Outside PM2.5", "pm25", 5.0),)
WEATHER = (Weather("weather.home", "sunny", 18.0, 60.0, 5.0),)
CLOSED = Window("binary_sensor.window", "Room window", False)


def room(*readings, windows=(CLOSED,)):
    return Room("room", "Bathroom", windows, tuple(readings))


def codes(reasons):
    return {reason["code"] if isinstance(reason, dict) else reason.code for reason in reasons}


class ConditionalRecommendations(unittest.TestCase):
    def test_cold_rain_and_humidity_are_named_without_marking_outdoors_safe(self):
        weather = (Weather("weather.home", "rainy", 3.0, 93.0, 40.0),)
        humid = Reading("sensor.rh", "Room RH", "humidity", 72.0)
        science = {"room": {"moisture": physics.moisture_potential(21, 72, 3, 93)}}
        plan = logic.evaluate(OUTDOOR, weather, (Warning("sensor.alert", "Strong wind alert", True),),
                              (room(humid),), environment=science)
        self.assertFalse(plan.outdoor_safe)
        self.assertEqual(plan.status, "open")
        self.assertEqual(len(plan.recommendations), 1)
        advice = plan.recommendations[0]
        self.assertEqual(codes(advice.reasons), {"inside_humidity"})
        self.assertEqual(codes(advice.cautions), {
            "weather_cold", "weather_humid", "weather_wind", "weather_condition", "active_warning"})
        self.assertIn(Reason("weather_cold", "Average weather temperature", "3 °C"), advice.cautions)

    def test_open_contact_gets_only_close_warning_in_severe_weather(self):
        need = Reading("sensor.co2", "CO2", "co2", 1600.0)
        windows = (replace(CLOSED, opened=True), Window("binary_sensor.other", "Other", False))
        plan = logic.evaluate(OUTDOOR, (Weather("weather.home", "lightning-rainy", 18, 60, 5),), (),
                              (room(need, windows=windows),))
        self.assertEqual([advice.action for advice in plan.recommendations], ["close"])
        self.assertEqual(plan.recommendations[0].windows, (windows[0],))

    def test_following_cautious_open_is_not_immediately_countermanded_for_soft_weather(self):
        need = Reading("sensor.co2", "CO2", "co2", 1600.0)
        opened = (replace(CLOSED, opened=True),)
        soft_weather = (("rainy", 3, 93), ("fog", 3, 93), ("sunny", 35, 60),
                        ("sunny", 18, 93), ("sunny", 3, 60))
        for condition, temperature, humidity in soft_weather:
            with self.subTest(condition=condition, temperature=temperature, humidity=humidity):
                weather = (Weather("weather.home", condition, temperature, humidity, 5),)
                before = logic.evaluate(OUTDOOR, weather, (), (room(need),))
                self.assertEqual(before.recommendations[0].action, "open")
                self.assertTrue(before.recommendations[0].cautions)
                while_airing = logic.evaluate(OUTDOOR, weather, (), (room(need, windows=opened),))
                self.assertFalse(while_airing.outdoor_safe)
                self.assertEqual(while_airing.outside_reasons, before.outside_reasons)
                self.assertEqual(while_airing.recommendations, ())
                resolved = logic.evaluate(OUTDOOR, weather, (),
                                          (room(replace(need, value=600), windows=opened),))
                self.assertEqual([rec.action for rec in resolved.recommendations], ["close"])

    def test_soft_weather_exception_requires_a_remaining_helpful_need(self):
        opened = (replace(CLOSED, opened=True),)
        humid = Reading("sensor.rh", "RH", "humidity", 72.0)
        weather = (Weather("weather.home", "rainy", 3, 93, 5),)
        science = {"room": {"moisture": physics.moisture_potential(21, 72, 3, 93)}}
        self.assertEqual(logic.evaluate(OUTDOOR, weather, (), (room(humid, windows=opened),),
                                        environment=science).recommendations, ())
        # A humidity reading remains high, but warmer wetter outside air no
        # longer supplies the claimed drying benefit: the close rule resumes.
        weather = (Weather("weather.home", "sunny", 35, 80, 5),)
        science["room"]["moisture"] = physics.moisture_potential(21, 72, 35, 80)
        resolved = logic.evaluate(OUTDOOR, weather, (), (room(humid, windows=opened),),
                                  environment=science)
        self.assertEqual([rec.action for rec in resolved.recommendations], ["close"])

    def test_hard_hazards_and_unknown_outside_evidence_still_close_immediately(self):
        need = Reading("sensor.co2", "CO2", "co2", 1600.0)
        opened = (replace(CLOSED, opened=True),)
        cases = [
            (OUTDOOR, (Weather("weather.home", condition, 3, 93, 5),), ())
            for condition in ("lightning", "lightning-rainy", "hail", "exceptional", "pouring")
        ]
        cases.extend((
            (OUTDOOR, (Weather("weather.home", "rainy", 3, 93, 40),), ()),
            (OUTDOOR, (Weather("weather.home", "rainy", 3, 93, 5),),
             (Warning("sensor.alert", "Severe weather alert", True),)),
            ((Reading("sensor.pm", "Outside PM", "pm25", 60),), WEATHER, ()),
            ((), WEATHER, ()),
            (OUTDOOR, (), ()),
            (OUTDOOR, (Weather("weather.home", None, 3, 93, 5),), ()),
        ))
        for outdoor, weather, warnings in cases:
            with self.subTest(outdoor=outdoor, weather=weather, warnings=warnings):
                plan = logic.evaluate(outdoor, weather, warnings, (room(need, windows=opened),))
                self.assertFalse(plan.outdoor_safe)
                self.assertEqual([rec.action for rec in plan.recommendations], ["close"])

    def test_existing_energy_close_remains_available_during_useful_cold_airing(self):
        # The manager merges this monitor's CLOSE after the pure air plan.
        # Keeping the latter empty leaves the real measured energy warning
        # authoritative; no new timer or duration is introduced here.
        ventilation = importlib.import_module(PKG + ".room_ventilation")
        now = [1000.0]
        monitor = ventilation.RoomVentilationMonitor(clock=lambda: now[0])
        opened = (replace(CLOSED, opened=True),)
        weather = (Weather("weather.home", "rainy", 3, 93, 5),)
        need = Reading("sensor.co2", "CO2", "co2", 1600.0)
        plan = logic.evaluate(OUTDOOR, weather, (), (room(need, windows=opened),))
        self.assertEqual(plan.recommendations, ())
        args = dict(area="room", name="Bathroom", windows=opened,
                    occupancy="occupied", sleeping=False, has_air_sensor=True,
                    outside_safe=plan.outdoor_safe, heat_target_c=20, cool_target_c=26)
        _status, first = monitor.observe(**args, temperature_c=21)
        self.assertIsNone(first)
        now[0] += ventilation.WINDOW_OPEN_MIN_SECONDS
        status, warning = monitor.observe(**args, temperature_c=20.5)
        self.assertEqual(status["window_energy_status"], "close_window_to_save_energy")
        self.assertEqual(warning.action, "close")
        self.assertEqual(codes(warning.reasons), {"window_heat_loss"})

    def test_bad_weather_without_indoor_need_does_not_create_a_request(self):
        plan = logic.evaluate(OUTDOOR, (Weather("weather.home", "rainy", 3, 93, 40),), (),
                              (room(Reading("sensor.co2", "CO2", "co2", 500)),))
        self.assertFalse(plan.outdoor_safe)
        self.assertEqual(plan.recommendations, ())

    def test_unknown_window_does_not_claim_every_contact_is_closed(self):
        windows = (CLOSED, Window("binary_sensor.unknown", "Unknown", None))
        plan = logic.evaluate(OUTDOOR, WEATHER, (),
                              (room(Reading("sensor.co2", "CO2", "co2", 1500), windows=windows),))
        self.assertEqual(plan.recommendations, ())
        self.assertIn(("Bathroom", "unknown_window_state"), plan.diagnostics)

    def test_missing_outside_data_is_disclosed_not_reported_as_suitable(self):
        plan = logic.evaluate((), (), (), (room(Reading("sensor.co2", "CO2", "co2", 1500)),))
        self.assertFalse(plan.outdoor_safe)
        self.assertEqual(codes(plan.recommendations[0].cautions), {"no_outdoor_data", "no_weather_data"})
        stale = (Reading("sensor.pm", "Outside PM", "pm25", None),)
        plan = logic.evaluate(stale, WEATHER, (), (room(Reading("sensor.co2", "CO2", "co2", 1500)),))
        self.assertIn("unavailable_outdoor", codes(plan.recommendations[0].cautions))

    def test_wetter_or_equally_moist_outside_air_does_not_claim_drying(self):
        humid = Reading("sensor.rh", "RH", "humidity", 72.0)
        mold = Reading("sensor.mold", "Surface RH", "mold", 85.0)
        for outside_c, outside_rh in ((30, 80), (21, 72)):
            with self.subTest(outside_c=outside_c, outside_rh=outside_rh):
                moisture = physics.moisture_potential(21, 72, outside_c, outside_rh)
                plan = logic.evaluate(OUTDOOR, WEATHER, (), (room(humid, mold),),
                                      environment={"room": {"moisture": moisture}})
                self.assertEqual(plan.recommendations, ())

    def test_co2_need_survives_moisture_tradeoff_with_explicit_caution(self):
        moisture = physics.moisture_potential(21, 72, 30, 80)
        plan = logic.evaluate(OUTDOOR, WEATHER, (),
                              (room(Reading("sensor.rh", "RH", "humidity", 72),
                                    Reading("sensor.co2", "CO2", "co2", 1600)),),
                              environment={"room": {"moisture": moisture}})
        self.assertEqual(codes(plan.recommendations[0].reasons), {"inside_co2"})
        self.assertIn("outside_more_moisture", codes(plan.recommendations[0].cautions))

    def test_measured_worse_pollutant_is_not_presented_as_a_benefit(self):
        outside = (Reading("sensor.pm", "Outside PM", "pm25", 60),)
        indoor = Reading("sensor.pm_in", "Indoor PM", "pm25", 35)
        plan = logic.evaluate(outside, WEATHER, (), (room(indoor),))
        self.assertEqual(plan.recommendations, ())
        self.assertIn(("Bathroom", "outdoor_pm25_not_lower_than_indoor"), plan.diagnostics)
        plan = logic.evaluate(outside, WEATHER, (),
                              (room(indoor, Reading("sensor.co2", "CO2", "co2", 1600)),))
        self.assertEqual(codes(plan.recommendations[0].reasons), {"inside_co2"})
        self.assertIn("outside_pm25", codes(plan.recommendations[0].cautions))

    def test_pollutant_comparison_uses_valid_sensor_mean(self):
        outside = (Reading("sensor.pm1", "Outside PM1", "pm25", 10),
                   Reading("sensor.pm2", "Outside PM2", "pm25", 30),
                   Reading("sensor.pm3", "Outside PM3", "pm25", None))
        plan = logic.evaluate(outside, WEATHER, (),
                              (room(Reading("sensor.pm_in", "Indoor PM", "pm25", 35)),))
        self.assertEqual(codes(plan.recommendations[0].reasons), {"inside_pm25"})
        self.assertIn("unavailable_outdoor", codes(plan.recommendations[0].cautions))

    def test_only_comparable_verified_aqi_scales_are_numerically_compared(self):
        def aqi(entity, value, scale):
            return Reading(entity, entity, "aqi", value,
                           {"aqi": {"status": "ready", "scale": scale, "operational_unsafe": True}})
        indoor = aqi("sensor.inside", 120, "us_epa")
        for outside, suppressed in ((aqi("sensor.outside", 150, "us_epa"), True),
                                    (aqi("sensor.outside", 150, "other_scale"), False)):
            with self.subTest(scale=outside.details["aqi"]["scale"]):
                plan = logic.evaluate((outside,), WEATHER, (), (room(indoor),))
                self.assertEqual(not bool(plan.recommendations), suppressed)

    def test_overheating_can_get_a_cautious_manual_cooling_request(self):
        report = {"thermal_comfort": {"status": "above_band"},
                  "passive_cooling": {"status": "outdoors_blocked", "cooling_delta_c": 7.0}}
        weather = (Weather("weather.home", "rainy", 20, 60, 5),)
        plan = logic.evaluate(OUTDOOR, weather, (), (room(),), environment={"room": report})
        self.assertFalse(plan.outdoor_safe)
        self.assertEqual(codes(plan.recommendations[0].reasons), {"inside_passive_cooling"})
        report["thermal_comfort"]["status"] = "within_band"
        self.assertEqual(logic.evaluate(OUTDOOR, weather, (), (room(),),
                                       environment={"room": report}).recommendations, ())

    def test_numeric_updates_and_wait_seconds_do_not_restart_notice_identity(self):
        rec = logic.Recommendation("open", "room", "Bathroom", (CLOSED,),
                                   (Reason("inside_co2", "CO2", "1600 ppm"),),
                                   (Reason("weather_wind", "Wind", "40 km/h"),), 300)
        update = replace(rec, reasons=(Reason("inside_co2", "CO2", "1700 ppm"),),
                         cautions=(Reason("weather_wind", "Wind", "45 km/h"),), wait_seconds=120)
        self.assertEqual(rec.action_signature, update.action_signature)
        self.assertEqual(rec.reason_signature, update.reason_signature)
        self.assertNotEqual(rec.reason_signature,
                            replace(rec, cautions=(*rec.cautions, Reason("weather_cold", value="3 °C"))).reason_signature)
        rain = replace(rec, cautions=(Reason("weather_condition", "weather.home", "rainy"),))
        snow = replace(rec, cautions=(Reason("weather_condition", "weather.home", "snowy"),))
        self.assertNotEqual(rain.reason_signature, snow.reason_signature)


class MeasuredSubstitution(unittest.TestCase):
    def setUp(self):
        self.states = {}
        self.hass = N(states=N(get=self.states.get), areas={},
                      services=N(async_call=no_service))
        self.add("binary_sensor.window", "off", device_class="window")
        self.add("climate.ac", "off", hvac_modes=["off", "heat", "cool"], supported_features=1)
        self.settings = {"enabled": True, "climate_entity": "climate.ac",
                         "selected_devices": ["climate.ac"]}
        self.plan = {"status": "ready", "mode": "cool", "away": "home", "sleeping": False,
                     "occupancy": "occupied", "temperature_c": 29.0, "temperature_target_c": 26.0,
                     "equipment_plan": {"thermal": {"status": "selected", "mode": "cool",
                                                      "entity_id": "climate.ac"}}}
        self.science = {}
        self.weather = WEATHER
        self.pending = ()

    def add(self, entity, state, area="room", **attributes):
        self.states[entity] = N(entity_id=entity, domain=entity.partition(".")[0], name=entity,
                                state=state, attributes=attributes)
        self.hass.areas[entity] = area

    def evaluate(self, **kwargs):
        return climate.window_substitution(
            self.hass, room(), self.settings, self.plan, self.science,
            self.weather, OUTDOOR, outside_safe=kwargs.pop("outside_safe", True),
            pending_demands=self.pending, **kwargs)

    def test_measured_pending_cooling_is_available_before_appliance_starts(self):
        advice = self.evaluate()
        self.assertEqual(advice["status"], "opportunity")
        self.assertTrue(advice["pending_demand"])
        self.assertEqual(advice["effect"], "cool")
        self.assertEqual(advice["devices"], ("climate.ac",))
        self.assertFalse(advice["automatic_control"])
        self.assertEqual(self.states["climate.ac"].state, "off")
        json.dumps(advice, allow_nan=False)

    def test_requested_mode_and_old_effort_do_not_replace_measured_demand(self):
        for temperature in (26, 25, None):
            with self.subTest(temperature=temperature):
                self.plan.update(temperature_c=temperature, pid_demand=90)
                self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")

    def test_running_hvac_does_not_claim_benefit_after_known_target_is_met(self):
        self.states["climate.ac"].state = "cool"
        self.states["climate.ac"].attributes["hvac_action"] = "cooling"
        self.plan.update(temperature_c=26, temperature_target_c=26)
        self.assertEqual(self.evaluate()["status"], "no_verified_cooling_demand")
        self.states["climate.ac"].state = "heat"
        self.states["climate.ac"].attributes["hvac_action"] = "heating"
        self.plan.update(temperature_c=21, temperature_target_c=21, mode="heat")
        self.plan["equipment_plan"]["thermal"]["mode"] = "heat"
        self.weather = (Weather("weather.home", "sunny", 24, 60, 5),)
        self.assertEqual(self.evaluate()["status"], "no_verified_heating_demand")

    def test_bad_weather_is_a_separate_caution_not_permission_for_intake(self):
        warning = (Reason("weather_condition", "weather.home", "rainy"),)
        advice = self.evaluate(outside_safe=False, outside_reasons=warning)
        self.assertEqual(advice["status"], "opportunity")
        self.assertFalse(advice["outside_safe"])
        self.assertEqual(climate.window_cautions(advice), warning)
        self.assertEqual(codes(self.evaluate(outside_safe=False)["cautions"]),
                         {"outside_conditions_not_verified"})

    def test_cautious_climate_opportunity_serializes_through_real_dashboard(self):
        self.weather = (Weather("weather.home", "rainy", 18, 60, 5),)
        advice = self.evaluate(outside_safe=False,
                               outside_reasons=(Reason("weather_condition", "weather.home", "rainy"),))
        advice["notify_enabled"] = True
        environment = {"room": {"climate_plan": {"window_efficiency": advice}}}
        plan = logic.evaluate(OUTDOOR, self.weather, (), (room(),), environment=environment)
        self.assertEqual(len(plan.recommendations), 1)
        self.assertEqual(codes(plan.recommendations[0].cautions), {"weather_condition"})
        dashboard = importlib.import_module(PKG + ".dashboard")
        snapshot = dashboard.dashboard_snapshot(plan, logic.DEFAULT_THRESHOLDS)
        self.assertFalse(snapshot["outdoor"]["safe_to_ventilate"])
        self.assertEqual(snapshot["rooms"][0]["action"], "open")
        json.dumps(snapshot, allow_nan=False)

    def test_a_person_home_can_air_an_empty_room_but_not_known_away_or_sleep(self):
        self.plan["occupancy"] = "unoccupied"
        self.assertEqual(self.evaluate()["status"], "opportunity")
        self.plan["away"] = "away"
        self.assertEqual(self.evaluate()["status"], "nobody_available_to_open_window")
        self.plan.update(away="home", sleeping=True)
        self.assertEqual(self.evaluate()["status"], "sleep_room_control_paused")

    def test_capability_identity_and_source_selection_are_rechecked(self):
        self.states["climate.ac"].attributes["hvac_modes"] = ["off", "heat"]
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")
        self.states["climate.ac"].attributes["hvac_modes"] = ["off", "heat", "cool"]
        self.hass.areas["climate.ac"] = "other"
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")
        self.hass.areas["climate.ac"] = "room"
        self.settings["selected_devices"] = []
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")
        self.settings["selected_devices"] = ["climate.ac"]
        self.states["climate.ac"].state = "unavailable"
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")

    def test_live_contact_cannot_be_replaced_by_an_earlier_closed_snapshot(self):
        self.states["binary_sensor.window"].state = "on"
        self.assertEqual(self.evaluate()["status"], "window_already_open")
        self.states["binary_sensor.window"].state = "unavailable"
        self.assertEqual(self.evaluate()["status"], "window_state_unknown")
        self.states["binary_sensor.window"].state = "off"
        self.hass.areas["binary_sensor.window"] = "other"
        self.assertEqual(self.evaluate()["status"], "window_wrong_room")

    def test_cooling_requires_real_outdoor_temperature_advantage(self):
        self.weather = (Weather("weather.home", "sunny", 28.0, 60, 5),)
        self.assertEqual(self.evaluate()["status"], "insufficient_free_cooling")
        self.weather = (Weather("weather.home", "sunny", None, 60, 5),)
        self.assertEqual(self.evaluate()["status"], "outdoor_temperature_unknown")

    def test_extreme_valid_temperature_delta_cannot_break_announcement_formatting(self):
        self.weather = (Weather("weather.home", "snowy", -35.0, 60, 5),)
        advice = self.evaluate(outside_safe=False,
                               outside_reasons=(Reason("weather_cold", value="-35 °C"),))
        self.assertEqual(climate.window_reason(advice).value, "64 °C")

    def test_heating_opportunity_can_reach_the_actual_pending_target(self):
        self.plan.update(temperature_c=18.0, temperature_target_c=21.0, mode="heat")
        self.plan["equipment_plan"]["thermal"]["mode"] = "heat"
        self.weather = (Weather("weather.home", "sunny", 23.0, 60, 5),)
        self.assertEqual(self.evaluate()["effect"], "heat")
        self.weather = (Weather("weather.home", "sunny", 20.0, 60, 5),)
        self.assertEqual(self.evaluate()["status"], "insufficient_free_warming")

    def test_native_range_uses_the_measured_side_of_its_band(self):
        self.states["climate.ac"].attributes.update(hvac_modes=["off", "heat_cool"], supported_features=2)
        self.plan.update(mode="heat_cool", temperature_target_c=None, low_target_c=20, high_target_c=26)
        self.plan["equipment_plan"]["thermal"]["mode"] = "heat_cool"
        self.assertEqual(self.evaluate()["effect"], "cool")
        self.plan["temperature_c"] = 23
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")

    def dry(self, *, outside_c=4, outside_rh=90):
        self.add("humidifier.dry", "off", device_class="dehumidifier")
        self.settings = {"enabled": True, "selected_devices": ["humidifier.dry"]}
        self.plan.update(status="advisory", temperature_c=21, equipment_plan={},
                         humidity_management={})
        self.weather = (Weather("weather.home", "rainy", outside_c, outside_rh, 5),)
        self.science = {"moisture": physics.moisture_potential(21, 72, outside_c, outside_rh)}
        self.pending = ({"entity_id": "humidifier.dry", "effect": "dry", "temperature_c": 21,
                         "humidity_percent": 72, "target_humidity": 65},)

    def test_managed_off_dehumidifier_has_measured_pending_drying_opportunity(self):
        self.dry()
        cautions = (Reason("weather_cold", value="4 °C"), Reason("weather_humid", value="90 %"))
        advice = self.evaluate(outside_safe=False, outside_reasons=cautions)
        self.assertEqual(advice["effect"], "dry")
        self.assertEqual(advice["devices"], ("humidifier.dry",))
        self.assertGreaterEqual(advice["evidence"]["humidity_ratio_advantage_g_kg"], 1.5)
        self.assertIn("weather_heat_loss", codes(advice["cautions"]))
        self.assertIn("weather_cold", codes(advice["cautions"]))
        self.assertTrue(advice["pending_demand"])

    def test_relative_humidity_alone_is_not_proof_of_drying(self):
        self.dry()
        self.science = {"moisture": {"status": "unavailable"}}
        self.assertEqual(self.evaluate()["status"], "measured_outdoor_drying_not_verified")
        self.dry(outside_c=30, outside_rh=70)
        self.assertEqual(self.evaluate()["status"], "measured_outdoor_drying_not_verified")

    def test_already_satisfied_humidity_cannot_create_a_prestart_request(self):
        self.dry()
        self.pending[0]["humidity_percent"] = 65
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")

    def test_configured_direct_thermal_role_can_supply_pending_evidence(self):
        self.add("switch.heater", "off")
        self.settings.update(heat_actuator="switch.heater", selected_devices=["switch.heater"])
        self.plan.update(status="advisory", temperature_c=18, equipment_plan={})
        self.pending = ({"entity_id": "switch.heater", "effect": "heat",
                         "temperature_c": 18, "target_c": 21},)
        self.weather = (Weather("weather.home", "sunny", 24, 60, 5),)
        self.assertEqual(self.evaluate()["effect"], "heat")
        self.settings.pop("heat_actuator")
        self.assertEqual(self.evaluate()["status"], "no_verified_equipment_demand")

    def test_multiple_weather_sources_average_only_valid_temperatures(self):
        self.weather = (Weather("weather.a", "sunny", 18, 60, 5),
                        Weather("weather.b", "sunny", 20, 60, 5),
                        Weather("weather.offline", None, None, None, None))
        self.assertEqual(self.evaluate()["evidence"]["outdoor_temperature_c"], 19)


if __name__ == "__main__":
    unittest.main()
