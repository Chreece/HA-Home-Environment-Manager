"""Optional patio/balcony door window inputs with real production AST functions.

No Home Assistant instance or hardware needed. Reuses shipped discovery,
room-source, away-alert and arbitration functions with small HA registries.
"""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
import sys
import types
from types import SimpleNamespace as N

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem_balcony_contact_test"
package = types.ModuleType(PKG)
package.__path__ = []
sys.modules[PKG] = package

ha = types.ModuleType("homeassistant")
helpers = types.ModuleType("homeassistant.helpers")
helpers.entity_registry = N(async_get=lambda hass: hass.entity_registry)
helpers.area_registry = N(async_get=lambda hass: hass.area_registry)
sys.modules["homeassistant"] = ha
sys.modules["homeassistant.helpers"] = helpers

def install(name: str) -> types.ModuleType:
    module = types.ModuleType(PKG + "." + name)
    module.__package__ = PKG
    sys.modules[module.__name__] = module
    return module

def extract(filename: str, names: tuple[str, ...], target: types.ModuleType) -> None:
    path = ROOT / "custom_components/environment_manager" / filename
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    funcs = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name in names]
    assert {node.name for node in funcs} == set(names), (filename, names)
    future = ast.ImportFrom(
        module="__future__", names=[ast.alias(name="annotations")], level=0,
    )
    parsed = ast.fix_missing_locations(ast.Module(
        body=[future, *funcs], type_ignores=[],
    ))
    exec(compile(parsed, str(path), "exec"), target.__dict__)

class States:
    def __init__(self, states):
        self.entities = {item.entity_id: item for item in states}

    def async_all(self, domain=None):
        values = list(self.entities.values())
        return [v for v in values if domain is None or v.domain == domain]

    def get(self, entity):
        return self.entities.get(entity)

def state(entity, device_class, value="off", *, attrs=True):
    return N(entity_id=entity, domain=entity.partition(".")[0],
             state=value, attributes={"device_class": device_class} if attrs else {},
             name=entity.rsplit(".", 1)[-1])

living = "living"
other = "kitchen"
entities = [
    state("binary_sensor.window", "window", "off"),
    state("binary_sensor.patio", "door", "off", attrs=False),
    state("binary_sensor.generic_opening", "opening", "off"),
    state("binary_sensor.garage", "garage_door", "off"),
    state("binary_sensor.motion", "motion", "off"),
    state("binary_sensor.manager_door", "door", "off"),
    state("binary_sensor.foreign_door", "door", "on"),
    state("cover.motorized_window", "window", "open"),
]
area_map = {s.entity_id: living for s in entities}
area_map["binary_sensor.foreign_door"] = other
registry_entries = {
    s.entity_id: N(device_class="door" if s.entity_id == "binary_sensor.patio"
                   else None, original_device_class=None, platform=(
                       "environment_manager" if s.entity_id == "binary_sensor.manager_door"
                       else "test"))
    for s in entities
}
hass = N(
    states=States(entities), area_map=area_map,
    entity_registry=N(async_get=lambda entity: registry_entries.get(entity)),
    area_registry=N(async_get_area=lambda area: N(name="Living room")
                    if area == living else N(name="Kitchen")
                    if area == other else None),
)
def entity_area(hass, entity):
    return hass.area_map.get(entity)

d = install("discovery")
d.__dict__.update(
    er=helpers.entity_registry, ar=helpers.area_registry,
    entity_area=entity_area, Counter=Counter,
    HomeAssistant=object, State=object,
    OPTIONAL_WINDOW_CONTACT_CLASSES=frozenset(("door", "opening")),
    supported_metric=lambda *args, **kwargs: None,
    is_pressure_sensor=lambda *args, **kwargs: False,
    Window=lambda eid, name, opened: N(entity_id=eid, name=name, opened=opened),
    Room=lambda area, name, windows, readings: N(
        area_id=area, name=name, windows=windows, readings=readings,
    ),
)
extract("discovery.py", ("_device_class", "is_window", "is_window_contact",
                         "_window_opened", "rooms"), d)
source_text = (ROOT / "custom_components/environment_manager/discovery.py").read_text()
assert 'OPTIONAL_WINDOW_CONTACT_CLASSES = frozenset(("door", "opening"))' in source_text

by_id = hass.states.entities
assert d._device_class(hass, by_id["binary_sensor.patio"]) == "door", "Use HA registry fallback"
assert d.is_window(hass, by_id["binary_sensor.window"])
assert not d.is_window(hass, by_id["binary_sensor.patio"])
assert not d.is_window_contact(hass, by_id["binary_sensor.patio"])
assert not d.is_window_contact(hass, by_id["binary_sensor.generic_opening"])
for eid in ("binary_sensor.patio", "binary_sensor.generic_opening"):
    assert d.is_window_contact(hass, by_id[eid], explicitly_selected=True), eid
for eid in ("binary_sensor.garage", "binary_sensor.motion", "cover.motorized_window"):
    assert not d.is_window_contact(hass, by_id[eid], explicitly_selected=True), eid

hierarchy = install("device_hierarchy")
hierarchy.configured_sources = lambda *args: []
hierarchy.configured_area_ids = lambda settings: [living]
s = install("room_sources")
s.__dict__.update(
    GROUPS=("windows", "air_quality", "temperature", "humidity", "climate_devices", "shades"),
    CONF_ROOM_SOURCES="room_sources",
    entity_area=entity_area,
    native=lambda h, eid: h.entity_registry.async_get(eid).platform != "environment_manager",
    label=lambda h, eid: eid,
    is_shading_cover=lambda h, st: False,
)
d.__dict__.update(native=s.native)
extract("room_sources.py", ("selected", "category", "choices", "defaults"), s)

options = s.choices(hass, living)
window_ids = {item["value"] for item in options["windows"]}
assert window_ids == {
    "binary_sensor.window", "binary_sensor.patio", "binary_sensor.generic_opening",
}, window_ids
assert next(x["label"] for x in options["windows"] if x["value"] == "binary_sensor.patio").startswith("🚪 ")
assert s.category(hass, by_id["binary_sensor.patio"]) is None, "No global door-to-window reclassification"

initial = s.defaults(hass, {}, living)
assert initial["windows"] == ["binary_sensor.window"], initial["windows"]
assert "binary_sensor.patio" not in initial["windows"]
assert "binary_sensor.generic_opening" not in initial["windows"]
assert s.defaults(hass, {"room_sources": {living: {
    "windows": ["binary_sensor.patio"], "shades": [],
}}}, living)["windows"] == ["binary_sensor.patio"]
assert s.defaults(hass, {"room_sources": {living: {
    "windows": [], "shades": [],
}}}, living)["windows"] == []

auto = d.rooms(hass, [living], 60)
assert [w.entity_id for w in auto[0].windows] == ["binary_sensor.window"], auto[0].windows

selected = {living: {"windows": ["binary_sensor.window", "binary_sensor.patio",
                                 "binary_sensor.generic_opening"]}}
custom = d.rooms(hass, [living], 60, source_selections=selected)
assert {w.entity_id for w in custom[0].windows} == set(selected[living]["windows"])
assert all(w.opened is False for w in custom[0].windows)
by_id["binary_sensor.patio"].state = "on"
assert next(w.opened for w in d.rooms(hass, [living], 60, source_selections=selected)[0].windows
            if w.entity_id == "binary_sensor.patio") is True
by_id["binary_sensor.patio"].state = "unavailable"
assert next(w.opened for w in d.rooms(hass, [living], 60, source_selections=selected)[0].windows
            if w.entity_id == "binary_sensor.patio") is None
by_id["binary_sensor.patio"].state = "off"
assert [w.entity_id for w in d.rooms(hass, [living], 60, source_selections={
    living: {"windows": []},
})[0].windows] == []
# A wrong-room selection must not turn a foreign door into a usable local contact.
wrong = d.rooms(hass, [living], 60, source_selections={
    living: {"windows": ["binary_sensor.foreign_door"]},
})
assert len(wrong[0].windows) == 1 and wrong[0].windows[0].opened is None

away = install("away_windows")
away.__dict__.update(
    Mapping=dict, entity_area=entity_area, is_window=d.is_window,
    is_window_contact=d.is_window_contact, selected=s.selected,
    native=s.native, CONF_EXCLUDED_WINDOWS="excluded_window_entities",
    CONF_OCCUPANCY_GLOBAL="occupancy_global",
)
extract("away_windows.py", ("open_windows", "watched_entities"), away)
by_id["binary_sensor.patio"].state = "on"
settings = {"room_sources": {living: {"windows": ["binary_sensor.patio"]}}}
assert away.open_windows(hass, settings)[0][0] == "binary_sensor.patio"
assert "binary_sensor.patio" in away.watched_entities(hass, settings)
assert away.open_windows(hass, {"room_sources": {living: {"windows": []}}}) == ()
assert away.open_windows(hass, {}) == (), "Legacy window-only discovery must ignore doors"
by_id["binary_sensor.patio"].state = "off"

arb = install("climate_arbitration")
arb.__dict__.update(
    entity_area=entity_area, is_window=d.is_window,
    is_window_contact=d.is_window_contact, Any=object,
)
extract("climate_arbitration.py", ("_contact_interlock",), arb)
plan = {"window_safe": True, "window_contacts": ["binary_sensor.patio"]}
assert not arb._contact_interlock(hass, living, plan), "No opt-in means no door authorization"
plan["selected_window_contacts"] = ["binary_sensor.patio"]
assert arb._contact_interlock(hass, living, plan), "Explicitly selected CLOSED door is valid"
by_id["binary_sensor.patio"].state = "on"
assert not arb._contact_interlock(hass, living, plan)
by_id["binary_sensor.patio"].state = "unknown"
assert not arb._contact_interlock(hass, living, plan)
by_id["binary_sensor.patio"].state = "off"
by_id["binary_sensor.patio"].attributes["device_class"] = "motion"
assert not arb._contact_interlock(hass, living, plan), "Retyped selected door is not valid"
by_id["binary_sensor.patio"].attributes.clear()
assert arb._contact_interlock(hass, living, plan), "Registry-only door is valid"

# The downstream advice and physical window hold must use the shared
# door-aware classifier, but only after the room has enrolled the contact.
for path in ("equipment_window.py", "climate_window.py"):
    tree = ast.parse((ROOT / "custom_components/environment_manager" / path).read_text())
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "is_window_contact"]
    assert calls, (path, "missing classifier revalidation")
manager_text = (ROOT / "custom_components/environment_manager/manager.py").read_text()
assert 'state["selected_window_contacts"] = list(' in manager_text
assert 'selected_room_sources(config, monitored.area_id, "windows")' in manager_text

print("PASS: optional Door/Opening window choices, window-only defaults, exact-area selection, "
      "away alerts, live open/unknown safeguards, no implicit door grants or powered covers")
