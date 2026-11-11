"""B1 scientific door boundary, area authority and non-actuating Eco policy.

Pure deterministic regression fixtures. No physical device, live Home Assistant
instance, network, or writable registry is involved.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[2] / "custom_components/environment_manager"
PACKAGE = "hem_062_fixture"
pkg = ModuleType(PACKAGE)
pkg.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = pkg
discovery = ModuleType(PACKAGE + ".discovery")
sources = ModuleType(PACKAGE + ".room_sources")
sys.modules[discovery.__name__] = discovery
sys.modules[sources.__name__] = sources

AREAS = {
    "binary_sensor.door_a": "area_a", "binary_sensor.door_b": "area_b",
    "binary_sensor.window_a": "area_a",
    "binary_sensor.motion_a": "area_a",
}
discovery.entity_area = lambda hass, entity: AREAS.get(entity)
discovery._device_class = lambda hass, state: state.attributes.get("device_class", "")
sources.native = lambda hass, entity: True
sources.label = lambda hass, entity: entity

homeassistant = ModuleType("homeassistant")
helpers = ModuleType("homeassistant.helpers")
registry = ModuleType("homeassistant.helpers.entity_registry")
class Registry:
    def async_get(self, entity):
        return SimpleNamespace(entity_id=entity) if entity in AREAS else None

registry.async_get = lambda hass: Registry()
helpers.entity_registry = registry
sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.helpers"] = helpers
sys.modules["homeassistant.helpers.entity_registry"] = registry

def load(name, path):
    spec = importlib.util.spec_from_file_location(PACKAGE + "." + name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

door = load("room_doors", ROOT / "room_doors.py")
now = datetime(2026, 11, 10, 20, 0, tzinfo=timezone.utc)
class States(dict):
    def async_all(self, domain=None):
        return [value for value in self.values()
                if domain is None or value.domain == domain]
class Hass:
    states = States()
hass = Hass()
def state(entity, state, klass, age=180, restored=False):
    return SimpleNamespace(entity_id=entity, domain=entity.partition(".")[0],
                           state=state, attributes={"device_class": klass,
                                                    "restored": restored},
                           last_changed=now - timedelta(seconds=age))
hass.states.update({
    "binary_sensor.door_a": state("binary_sensor.door_a", "off", "door"),
    "binary_sensor.door_b": state("binary_sensor.door_b", "off", "door"),
    "binary_sensor.window_a": state("binary_sensor.window_a", "off", "window"),
    "binary_sensor.motion_a": state("binary_sensor.motion_a", "off", "motion"),
})

choices = door.door_choices(hass, "area_a")
assert [item["value"] for item in choices] == ["binary_sensor.door_a"], choices
assert "binary_sensor.door_b" not in {item["value"] for item in choices}
assert door.door_choices(hass, "area_b")[0]["value"] == "binary_sensor.door_b"

cfg = {"door_sensors": ["binary_sensor.door_a"], "closed_door_eco": True}
base = dict(occupancy="unoccupied",
            occupancy_evidence="all_selected_room_sensors_off",
            home="home", sleeping=False, temperature_c=20,
            humidity_rh=42, window_safe=True, now=now)
def evaluate(config=None, **overrides):
    return door.observe(hass, "area_a", cfg if config is None else config,
                        **{**base, **overrides})

ok = evaluate()
assert ok["boundary"] == "closed" and ok["eco_active"], ok
assert ok["eco_reason"] == "verified_closed_and_empty"
assert not evaluate({"door_sensors": ["binary_sensor.door_a"]})["eco_active"]
assert not evaluate({"door_sensors": [], "closed_door_eco": True})["eco_active"]
assert not evaluate(occupancy="occupied")["eco_active"]
assert not evaluate(occupancy_evidence="no_room_presence_sensors")["eco_active"]
assert not evaluate(home="away")["eco_active"]
assert not evaluate(home="unknown")["eco_active"]
assert not evaluate(sleeping=True)["eco_active"]
assert not evaluate(preparing_arrival=True)["eco_active"]
assert not evaluate(window_safe=False)["eco_active"]
assert not evaluate(humidity_rh=None)["eco_active"]
assert not evaluate(humidity_rh=63)["eco_active"]
assert evaluate(humidity_rh=63)["advisory"] == "closed_door_high_humidity"
assert not evaluate(temperature_c=14)["eco_active"]
assert evaluate(co2_ppm=1300)["advisory"] == "closed_door_high_co2"

hass.states["binary_sensor.door_a"] = state("binary_sensor.door_a", "on", "door")
assert evaluate()["boundary"] == "open"
assert not evaluate()["eco_active"]
hass.states["binary_sensor.door_a"] = state("binary_sensor.door_a", "off", "door", age=30)
assert evaluate()["boundary"] == "settling"
assert not evaluate()["eco_active"]
hass.states["binary_sensor.door_a"] = state("binary_sensor.door_a", "unavailable", "door")
assert evaluate()["boundary"] == "unknown"
assert not evaluate()["eco_active"]
hass.states["binary_sensor.door_a"] = state("binary_sensor.door_a", "off", "door", restored=True)
assert evaluate()["boundary"] == "unknown"
assert not evaluate()["eco_active"]
hass.states["binary_sensor.door_a"] = state("binary_sensor.door_a", "off", "door")
assert evaluate({"door_sensors": ["binary_sensor.door_a", "binary_sensor.door_b"],
                 "closed_door_eco": True})["boundary"] == "unknown"
assert not evaluate({"door_sensors": ["binary_sensor.door_a", "binary_sensor.door_b"],
                     "closed_door_eco": True})["eco_active"]
assert evaluate({"door_sensors": ["binary_sensor.window_a"],
                 "closed_door_eco": True})["boundary"] == "unknown"
assert not evaluate({"door_sensors": ["binary_sensor.window_a"],
                     "closed_door_eco": True})["eco_active"]

# Pure climate-profile function: no device can bypass manual, sleep, arrival,
# or household away just because a contact is closed.
sys.modules[PACKAGE + ".climate_equipment"] = ModuleType(PACKAGE + ".climate_equipment")
sys.modules[PACKAGE + ".climate_equipment"].classify_hvac = lambda *args: {}
sys.modules[PACKAGE + ".comfort_targets"] = ModuleType(PACKAGE + ".comfort_targets")
sys.modules[PACKAGE + ".comfort_targets"].has_minimum_deadband = lambda *args: True
strategy = load("climate_strategy", ROOT / "climate_strategy.py")
def profile(**kwargs):
    return strategy.select_profile({}, at_home="home", occupied="unoccupied",
                                   door_eco_active=True, **kwargs)
assert profile() == ("eco", "closed_door_verified_vacancy")
assert profile(manual="comfort")[0] == "comfort"
assert profile(sleeping=True)[0] == "sleep"
assert strategy.select_profile({}, at_home="away", occupied="unoccupied",
                               door_eco_active=True)[0] == "away"
assert strategy.select_profile({}, at_home="home", occupied="occupied",
                               door_eco_active=True)[0] == "comfort"
assert strategy.select_profile({}, at_home="home", occupied="unoccupied",
                               door_eco_active=False)[0] == "home"

print("PASS: b1 exact-area door inventory, safe Eco gate, live changes and profile priority")
