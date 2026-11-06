"""Restart placeholders cannot create heating demand from old measurements."""
from __future__ import annotations

import ast
from contextlib import redirect_stdout
from io import StringIO
import importlib
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
with redirect_stdout(StringIO()):
    fixture = runpy.run_path(str(ROOT / ".github/tests/test_beta65_data.py"))
discovery = fixture["dis"]
sources = importlib.import_module("hem65test.room_sources")

klass = next(node for node in ast.parse((ROOT / "equipment_runtime.py").read_text()).body
             if isinstance(node, ast.ClassDef) and node.name == "EquipmentRuntime")
method = next(node for node in klass.body if getattr(node, "name", None) == "measurements")
scope = {"__package__": "hem65test", "model": N(room_config=lambda *args: {},
           device_config=lambda *args: {}), "entity_area": discovery.entity_area,
         "temperature_sensor_c": discovery.temperature_sensor_c,
         "reading": discovery.reading, "CONF_EXCLUDED_INDOOR": "excluded_indoor_entities"}
exec(compile(ast.Module(body=[ast.parse("from __future__ import annotations").body[0], method],
                        type_ignores=[]), "equipment_runtime.py", "exec"), scope)


class RestartMeasurements(unittest.TestCase):
    def setUp(self):
        self.hass = fixture["hass"]
        self.cold, self.live, self.humidity = (
            "sensor.restart_temperature", "sensor.live_temperature", "sensor.restart_humidity")
        for entity, value, unit, metric in (
            (self.cold, 8, "°C", "temperature"),
            (self.live, 22, "°C", "temperature"),
            (self.humidity, 35, "%", "humidity"),
        ):
            state = fixture["state"](entity, value, unit, metric)
            if entity != self.live:
                state.attributes["restored"] = True
            fixture["states"][entity] = state
            fixture["entities"][entity] = N(entity_id=entity, area_id="room", device_id=None,
                platform="test", device_class=None, original_device_class=None)

    def test_fresh_restart_timestamp_does_not_make_restored_temperature_live(self):
        self.assertIsNone(discovery.temperature_sensor_c(self.hass, self.cold, 10))
        self.assertEqual(discovery.temperature_sensor_c(self.hass, self.live, 10), 22)

    def test_old_cold_placeholder_cannot_lower_the_actual_control_average(self):
        manager = N(settings={"room_sources": {"room": {
            "temperature": [self.cold, self.live], "humidity": [self.humidity],
            "air_quality": [], "windows": []}}})
        runtime = N(hass=self.hass, manager=manager)
        measured = scope["measurements"](runtime, N(area_id="room"), N(primary="climate.heater"))
        # Before the fix, restored 8°C + current 22°C averaged to 15°C,
        # creating heat demand even with an Away target of 16°C.
        self.assertEqual(measured["temperature"], 22)
        self.assertIsNone(measured["humidity"])

    def test_all_restored_selected_inputs_are_missing_not_zero_or_old_values(self):
        self.assertIsNone(sources.aggregate(self.hass, [self.cold], "room", "temperature", 10)[0])
        self.assertIsNone(sources.aggregate(self.hass, [self.humidity], "room", "humidity", 10)[0])
        self.assertIsNone(discovery.reading(self.hass, self.humidity, 10, outdoor=False).value)

    def test_actual_report_restores_normal_measurement_automatically(self):
        fixture["states"][self.cold] = fixture["state"](self.cold, 18, "°C", "temperature")
        fixture["states"][self.humidity].attributes["restored"] = False
        self.assertEqual(sources.aggregate(self.hass, [self.cold, self.live], "room", "temperature", 10)[0], 20)
        self.assertEqual(discovery.reading(self.hass, self.humidity, 10, outdoor=False).value, 35)


if __name__ == "__main__":
    unittest.main(verbosity=2)
