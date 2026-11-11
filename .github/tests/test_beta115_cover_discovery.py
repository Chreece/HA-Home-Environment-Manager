"""Actual room cover discovery/defaults and Options save, without appliance I/O.

Compile production registry helpers and flow methods around small HA boundary
fixtures. Source inventory, classification and selection are the real module.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = "beta115_cover_fixture"


def module(name, **values):
    result = ModuleType(name)
    result.__package__ = name.rpartition(".")[0]
    result.__dict__.update(values)
    sys.modules[name] = result
    return result


def production_nodes(filename, names, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name in names
    ) or (isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id in names
        for target in node.targets
    ))]
    assert len(nodes) == len(names), (filename, names)
    exec(compile(ast.Module(nodes, type_ignores=[]), filename, "exec"), namespace)


package = module(PKG)
package.__path__ = [str(ROOT)]
module(PKG + ".const", DOMAIN="environment_manager", CONF_AREAS="areas",
       CONF_CLIMATE_ROOMS="climate_rooms", CONF_PID_ROOMS="pid_rooms",
       CONF_OCCUPANCY_GLOBAL="occupancy_global")
# This is a cover-only fixture. Actual DOOR classification and its area
# authority are exercised separately by test_062b1_room_doors.py.
module(PKG + ".room_doors", door_choices=lambda hass, area, previous=None: [])
# Import the real pure-Python config-copy and inventory modules without loading
# the integration's HA setup module.
def load(name):
    spec = importlib.util.spec_from_file_location(PKG + "." + name, ROOT / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


ha = module("homeassistant")
ha.__path__ = []
helpers = module("homeassistant.helpers")
helpers.__path__ = []
er = module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.entities)
dr = module("homeassistant.helpers.device_registry", async_get=lambda hass: hass.devices)
ar = module("homeassistant.helpers.area_registry", async_get=lambda hass: hass.areas)
helpers.entity_registry, helpers.device_registry = er, dr
helpers.area_registry = ar

discovery = module(PKG + ".discovery", er=er, dr=dr,
                   HomeAssistant=object, State=object,
                   is_window=lambda hass, state: False,
                   supported_metric=lambda hass, state, outdoor=False: None)
production_nodes("discovery.py", {"entity_area", "_device_class", "is_pressure_sensor"}, discovery.__dict__)
sources = load("room_sources")
hierarchy = load("device_hierarchy")
compact = module(PKG + ".compact_options")
production_nodes("compact_options.py", {"_MANAGED_DEVICE_ROLES", "_reconcile_device_selection"}, compact.__dict__)
module(PKG + ".occupancy_policy", room_sensor_choices=lambda hass, area: [])

class Field(str):
    def __new__(cls, name, default):
        value = super().__new__(cls, name)
        value.default = deepcopy(default)
        return value


flow_module = module(PKG + ".reconfigure_rooms", Any=object, ar=ar,
                     CONF_AREAS="areas", CONF_CLIMATE_ROOMS="climate_rooms",
                     sources=sources, deepcopy=deepcopy, field=Field,
                     select=lambda options, multiple=False: {
                         "options": options, "multiple": multiple},
                     probatio=N(Schema=lambda fields: fields))
production_nodes("reconfigure_rooms.py", {"ReconfigureRoomsMixin"}, flow_module.__dict__)

setup_module = module(PKG + ".room_setup", Any=object, ar=ar,
                      CONF_AREAS="areas", sources=sources, deepcopy=deepcopy,
                      field=Field, select=flow_module.select,
                      probatio=flow_module.probatio)
production_nodes("room_setup.py", {"RoomSetupMixin"}, setup_module.__dict__)

runtime = module(PKG + ".shade_cooling", Any=object,
                 native=sources.native, category=sources.category)
production_nodes("shade_cooling.py", {"eligible_shade"}, runtime.__dict__)

EXAMPLES = {
    "cover.ksenonas_rolo_aristera": "ksenonas",
    "cover.wohnzimmer_rollo_links_rolo_3": "wohnzimmer",
    "cover.wohnzimmer_rollo_rechts": "wohnzimmer",
    "cover.gastezimmer_rollo_rechts_rolo_5": "gastezimmer",
    "cover.schlafzimmer_rollo_rolo": "schlafzimmer",
    "cover.kuche_rollo": "kuche",
}
LEFT = "cover.wohnzimmer_rollo_links_rolo_3"
RIGHT = "cover.wohnzimmer_rollo_rechts"
KITCHEN = "cover.kuche_rollo"


class Fixture:
    def __init__(self):
        self.registry = {}
        self.device_records = {}
        self.state_records = {}
        names = set(EXAMPLES.values()) | {"other"}
        self.hass = N(
            entities=N(async_get=self.registry.get),
            devices=N(async_get=self.device_records.get),
            areas=N(async_get_area=lambda area: N(name=area) if area in names else None),
            states=N(async_get=self.state_records.get, get=self.state_records.get,
                     async_all=lambda: list(self.state_records.values())),
        )
        for entity, area in EXAMPLES.items():
            self.add(entity, area, state="unknown" if entity == KITCHEN else "open")

    def add(self, entity, area, *, state="open", features=15, klass=None,
            device_area=None, **entry_values):
        device_id = "device:" + entity if device_area is not None else None
        if device_id:
            self.device_records[device_id] = N(area_id=device_area, name="Native device", name_by_user=None)
        values = dict(entity_id=entity, area_id=area, device_id=device_id,
                      platform="native_cover", device_class=None,
                      original_device_class=None, disabled_by=None, hidden_by=None,
                      name=None, original_name=entity, id="entry:" + entity)
        values.update(entry_values)
        self.registry[entity] = N(**values)
        attributes = {"supported_features": features}
        if state == "unknown":
            attributes["is_closed"] = None
        else:
            attributes["current_position"] = 100
        if klass is not None:
            attributes["device_class"] = klass
        self.state_records[entity] = N(entity_id=entity, domain=entity.split(".")[0],
                                       name=entity, state=state, attributes=attributes)

    def shade_choices(self, area, previous=None):
        return {item["value"] for item in sources.choices(self.hass, area, previous)["shades"]}


class Flow(flow_module.ReconfigureRoomsMixin):
    def __init__(self, fixture, settings, area="wohnzimmer"):
        self.hass = fixture.hass
        self._values = deepcopy(settings)
        self._room_edit_area = area
        self.saved = []

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_abort(self, **kwargs):
        return {"type": "abort", **kwargs}

    async def _finish(self):
        self.saved.append(deepcopy(self._values))
        return {"type": "create_entry", "data": self.saved[-1]}


class SetupFlow(setup_module.RoomSetupMixin):
    async_show_form = Flow.async_show_form
    async_abort = Flow.async_abort
    _finish = Flow._finish

    def __init__(self, fixture):
        self.hass = fixture.hass
        self._values = {"areas": ["wohnzimmer"]}
        self._setup_order = ["wohnzimmer"]
        self._setup_index = 0
        self._edit_room_area = "wohnzimmer"
        self.saved = []

    async def async_step_setup_general(self):
        return {"type": "general"}


def form_defaults(form):
    return {str(field): deepcopy(field.default) for field in form["data_schema"]}


class CoverDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()

    def test_user_classless_covers_and_unknown_startup_are_discovered(self):
        for area in set(EXAMPLES.values()):
            expected = {entity for entity, assigned in EXAMPLES.items() if assigned == area}
            with self.subTest(area=area):
                self.assertEqual(self.fixture.shade_choices(area), expected)
                self.assertEqual(set(sources.defaults(self.fixture.hass, {}, area)["shades"]), expected)
        # Inventory is available while the kitchen cover awaits live feedback;
        # the actual movement eligibility gate remains closed.
        self.assertEqual(runtime.eligible_shade(
            self.fixture.hass, "kuche", KITCHEN, (KITCHEN,)),
            (False, "cover_unavailable"))

    def test_registry_room_override_and_native_enabled_scope(self):
        f = self.fixture
        f.add("cover.device_area", None, device_area="wohnzimmer")
        f.add("cover.wohnzimmer_name_only", None)
        f.add("cover.override_other", "other", device_area="wohnzimmer")
        f.add("cover.override_living", "wohnzimmer", device_area="other")
        f.add("cover.disabled", "wohnzimmer", disabled_by="user")
        f.add("cover.hidden", "wohnzimmer", hidden_by="user")
        f.add("cover.generated", "wohnzimmer", platform="environment_manager")
        self.assertEqual(f.shade_choices("wohnzimmer"),
                         {LEFT, RIGHT, "cover.device_area", "cover.override_living"})
        self.assertIn("cover.override_other", f.shade_choices("other"))
        self.assertEqual(f.shade_choices("wohnzimmer", {"shades": [
            "cover.disabled", "cover.hidden", "cover.generated", "cover.override_other"]}),
            {LEFT, RIGHT, "cover.device_area", "cover.override_living"})

    def test_explicit_non_shades_and_no_close_capability_are_not_selected(self):
        f = self.fixture
        for klass in ("door", "garage", "gate", "awning", "window", "damper"):
            f.add("cover." + klass, "wohnzimmer", klass=klass)
        f.add("cover.registry_garage", "wohnzimmer", original_device_class="garage")
        for number, bits in enumerate((0, 1, -1, None, "invalid")):
            f.add("cover.no_close_" + str(number), "wohnzimmer", features=bits)
        for klass in ("blind", "shade", "shutter", "curtain"):
            f.add("cover." + klass, "wohnzimmer", klass=klass)
        self.assertEqual(f.shade_choices("wohnzimmer"),
                         {LEFT, RIGHT, *["cover." + klass for klass in ("blind", "shade", "shutter", "curtain")]})

    def test_saved_empty_subset_and_legacy_missing_group(self):
        f = self.fixture
        for chosen in ([], [LEFT]):
            settings = {"room_sources": {"wohnzimmer": {
                "temperature": [], "windows": [], "shades": chosen}}}
            before = deepcopy(settings)
            self.assertEqual(sources.defaults(f.hass, settings, "wohnzimmer")["shades"], chosen)
            self.assertEqual(settings, before)
        # Only the absent cover group gains discovery defaults. Explicitly
        # deselected sensor groups remain empty and no config is mutated.
        legacy = {"room_sources": {"wohnzimmer": {"temperature": [], "windows": []}}}
        before = deepcopy(legacy)
        default = sources.defaults(f.hass, legacy, "wohnzimmer")
        self.assertEqual(set(default["shades"]), {LEFT, RIGHT})
        self.assertEqual(default["temperature"], [])
        self.assertEqual(default["windows"], [])
        self.assertEqual(legacy, before)
        excluded = {"excluded_indoor_entities": {"wohnzimmer": [LEFT]}}
        self.assertEqual(sources.defaults(f.hass, excluded, "wohnzimmer")["shades"], [RIGHT])

    def test_open_is_read_only_and_save_revokes_stale_cover_grants(self):
        settings = {"areas": ["wohnzimmer"], "shade_rooms": {
            "wohnzimmer": {"enabled": True, "covers": {
                LEFT: {"enabled": True, "min_lux": 900}}},
            "kuche": {"enabled": True, "covers": {KITCHEN: {"enabled": True}}}}}
        flow = Flow(self.fixture, settings)
        form = asyncio.run(flow.async_step_room_settings())
        draft = form_defaults(form)
        self.assertEqual(set(draft["shades"]), {LEFT, RIGHT})
        self.assertEqual(flow._values, settings)
        self.assertEqual(flow.saved, [])
        saved = asyncio.run(flow.async_step_room_settings(draft))
        self.assertEqual(saved["type"], "create_entry")
        cfg = saved["data"]
        self.assertEqual(set(cfg["room_sources"]["wohnzimmer"]["shades"]), {LEFT, RIGHT})
        self.assertFalse(cfg["shade_rooms"]["wohnzimmer"]["enabled"])
        self.assertFalse(cfg["shade_rooms"]["wohnzimmer"]["covers"][LEFT]["enabled"])
        self.assertEqual(cfg["shade_rooms"]["wohnzimmer"]["covers"][LEFT]["min_lux"], 900)
        self.assertEqual(cfg["shade_rooms"]["kuche"], settings["shade_rooms"]["kuche"])
        self.assertEqual(settings["shade_rooms"]["wohnzimmer"]["enabled"], True)
        # Explicit clear remains clear on reopen, even with valid local covers.
        draft["shades"] = []
        asyncio.run(flow.async_step_room_settings(draft))
        reopened = form_defaults(asyncio.run(flow.async_step_room_settings()))
        self.assertEqual(reopened["shades"], [])

    def test_initial_and_legacy_setup_omit_cleared_cover_field(self):
        for method in ("async_step_setup_room_sources", "async_step_edit_room"):
            with self.subTest(method=method):
                flow = SetupFlow(self.fixture)
                step = getattr(flow, method)
                draft = form_defaults(asyncio.run(step()))
                self.assertEqual(set(draft.pop("shades")), {LEFT, RIGHT})
                asyncio.run(step(draft))
                self.assertEqual(flow._values["room_sources"]["wohnzimmer"]["shades"], [])
                self.assertEqual(sources.defaults(
                    self.fixture.hass, flow._values, "wohnzimmer")["shades"], [])

    def test_cross_room_or_moved_cover_cannot_be_saved(self):
        flow = Flow(self.fixture, {"areas": ["wohnzimmer"]})
        draft = form_defaults(asyncio.run(flow.async_step_room_settings()))
        original = deepcopy(flow._values)
        draft["shades"] = [KITCHEN]
        rejected = asyncio.run(flow.async_step_room_settings(draft))
        self.assertEqual(rejected["errors"]["shades"], "invalid_room_source")
        self.assertEqual(flow._values, original)
        self.assertEqual(flow.saved, [])
        # Room membership must be checked again when an open form is saved.
        draft["shades"] = [LEFT]
        self.fixture.registry[LEFT].area_id = "other"
        rejected = asyncio.run(flow.async_step_room_settings(draft))
        self.assertEqual(rejected["errors"]["shades"], "invalid_room_source")
        self.assertEqual(flow._values, original)
        self.assertEqual(flow.saved, [])


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if not result.result.wasSuccessful():
        sys.exit(1)
    print("BETA115_ROOM_COVER_DEFAULTS_SCOPE_DESELECTION_AND_GRANTS=PASS")
