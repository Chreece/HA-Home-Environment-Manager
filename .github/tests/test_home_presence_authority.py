"""Whole-home presence owns room occupancy, including live writes and restart.

Loads the production policy, room planner and presence-continuity modules in
an isolated package. Only HA state/area/store access and unrelated equipment
planning are stubbed. No Home Assistant service or physical device is used.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
NOW = datetime.now(timezone.utc)
PACKAGE = "hem_presence_regression"
AREA = "living"
ROOMS = "input_text.occupied_rooms"
MOTION = "binary_sensor.living_presence"
PERSON = "person.alice"
HOME = "binary_sensor.somebody_home"
TRACKER = "device_tracker.bob"
COUNT = "sensor.people_at_home"


def module(name: str, **members):
    result = ModuleType(name)
    result.__dict__.update(members)
    sys.modules[name] = result
    return result


module(PACKAGE, __path__=[str(ROOT)])
discovery = module(
    PACKAGE + ".discovery",
    entity_area=lambda hass, entity: hass.entity_areas.get(entity),
    _device_class=lambda hass, state: state.attributes.get("device_class", ""),
    temperature_sensor_c=lambda *args: None,
)
# Exercise the real alias resolver against a small Home Assistant registry.
module("homeassistant", __path__=[])
module("homeassistant.helpers", __path__=[])
module("homeassistant.helpers.area_registry", async_get=lambda hass: hass.areas)
occupancy = importlib.import_module(PACKAGE + ".occupancy_policy")
continuity = importlib.import_module(PACKAGE + ".presence_continuity")
discovery.is_stale = lambda state, minutes: not occupancy._fresh(state, minutes)
# Equipment discovery/dispatch is unrelated to presence and must not run.
# The actual gather function and its profile-selection policy still execute.
module(
    PACKAGE + ".climate_coordination",
    assigned_entities=lambda settings: set(),
    device_inventory=lambda *args: [],
    planning_capabilities=lambda capability, inventory: capability,
    room_equipment_plan=lambda *args, **kwargs: {},
)
climate = importlib.import_module(PACKAGE + ".climate_rooms")


def source_module(name, filename, names, *, class_name=None, **members):
    """Execute selected production methods without unrelated HA imports."""
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    body = tree.body
    if class_name is not None:
        body = next(node for node in body if isinstance(node, ast.ClassDef)
                    and node.name == class_name).body
    selected = [node for node in body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in names]
    assert {node.name for node in selected} == set(names)
    future = ast.parse("from __future__ import annotations").body[0]
    result = module(PACKAGE + "." + name, __package__=PACKAGE, **members)
    exec(compile(ast.Module(body=[future, *selected], type_ignores=[]),
                 str(ROOT / filename), "exec"), result.__dict__)
    return result


source_module("room_sources", "room_sources.py", ("selected",),
              CONF_ROOM_SOURCES="room_sources")
equipment = source_module(
    "equipment_model", "equipment_model.py", ("room_config", "plan_for"),
    specs=lambda manager: manager.device_specs, settings=lambda manager, spec: {},
)
runtime = source_module(
    "equipment_runtime", "equipment_runtime.py", ("_quiet_context",),
    class_name="EquipmentRuntime", model=equipment,
    room_presence=occupancy.room_presence,
)


class States:
    def __init__(self):
        self.data = {}
        self.reads = []
        self.blocked = set()
        self.forbid_discovery = False

    def get(self, entity):
        self.reads.append(entity)
        if entity in self.blocked:
            raise AssertionError(f"Room source must be ignored: {entity}")
        return self.data.get(entity)

    def async_all(self, domain=None):
        if self.forbid_discovery:
            raise AssertionError("Room presence discovery must be skipped while away")
        return [state for state in self.data.values()
                if domain is None or state.domain == domain]


class Hass:
    def __init__(self):
        self.states = States()
        self.entity_areas = {}
        records = {
            AREA: N(id=AREA, name="Living room", aliases=("Wohnzimmer",)),
            "bath": N(id="bath", name="Bathroom", aliases=()),
        }
        self.areas = N(async_list_areas=lambda: list(records.values()),
                       async_get_area=records.get)
        self.config = N(time_zone="UTC")

    def put(self, entity, value, *, age=1, changed_age=None,
            updated_age=None, area=None, attributes=None):
        attributes = dict(attributes or {})
        if entity == MOTION:
            attributes.setdefault("device_class", "occupancy")
            area = area or AREA
        state = N(
            entity_id=entity, domain=entity.split(".", 1)[0], state=value,
            attributes=attributes,
            last_reported=NOW - timedelta(minutes=age),
            last_updated=NOW - timedelta(minutes=age if updated_age is None else updated_age),
            last_changed=NOW - timedelta(minutes=age if changed_age is None else changed_age),
        )
        self.states.data[entity] = state
        if area is not None:
            self.entity_areas[entity] = area
        return state

    def forbid_room_reads(self):
        self.states.blocked.update((ROOMS, MOTION))
        self.states.forbid_discovery = True


class Store:
    def __init__(self, saved=None):
        self.saved = deepcopy(saved)
        self.pending = None

    async def async_load(self):
        return deepcopy(self.saved)

    def async_delay_save(self, snapshot, delay):
        self.pending = snapshot

    async def async_save(self, snapshot):
        self.saved = deepcopy(snapshot)


def room_config(**values):
    return {"occupied_rooms_entity": ROOMS,
            "occupied_rooms_attribute": "__state__",
            "source_stale_minutes": 240,
            "away_cooldown_minutes": 10, **values}


def device(requirement="occupied", **values):
    return {"auto_control": True, "sleep_behavior": "normal",
            "presence_requirement": requirement, **values}


class HomeAuthorityTests(unittest.TestCase):
    def test_verified_away_ignores_every_room_source_state(self):
        room_states = (
            ("Living room", 1, "on", 1),
            ("Living room", 400, "on", 400),
            ("", 1, "on", 1),
            ("", 400, "unavailable", 1),
            ("[]", 1, "off", 1),
            ("[broken", 1, "unknown", 1),
            ('["Unknown area"]', 1, "on", 1),
            ("unavailable", 1, "on", 1),
            (None, 1, None, 1),
        )
        for listed, list_age, motion, motion_age in room_states:
            with self.subTest(listed=listed, list_age=list_age, motion=motion):
                hass = Hass()
                # Direct absence has no room-motion cooldown, even when the
                # fresh tracker timestamps were recreated a moment ago.
                for entity, value in ((PERSON, "not_home"), (HOME, "off"),
                                      (COUNT, "0"), (TRACKER, "work")):
                    hass.put(entity, value, changed_age=0)
                if listed is not None:
                    hass.put(ROOMS, listed, age=list_age)
                if motion is not None:
                    hass.put(MOTION, motion, age=motion_age)
                config = room_config(
                    home_trackers=[PERSON, HOME, COUNT, PERSON],
                    room_occupancy_sensors=[MOTION], away_cooldown_minutes=240,
                )
                fallback = [TRACKER, PERSON]
                hass.forbid_room_reads()
                self.assertEqual(
                    occupancy.home_presence(hass, config, fallback),
                    ("away", "all_selected_home_trackers_away",
                     [PERSON, HOME, COUNT, TRACKER]),
                )
                self.assertEqual(
                    occupancy.room_presence(
                        hass, AREA, {"away_entities": fallback}, config,
                        known_areas={AREA, "bath"},
                    ),
                    ("unoccupied", "verified_home_away", []),
                )

    def test_positive_direct_presence_wins_and_unknown_is_not_away(self):
        cases = (
            ("home", "off", "unavailable", "home"),
            ("not_home", "on", "unavailable", "home"),
            ("unavailable", "off", "2", "home"),
            ("not_home", "unknown", "0", "unknown"),
            ("unknown", "unavailable", "unknown", "unknown"),
            ("not_home", "off", "0", "away"),
        )
        config = room_config(home_trackers=[PERSON, HOME, COUNT],
                             room_occupancy_sensors=[MOTION], home_policy="all_home")
        for person, home, count, expected in cases:
            with self.subTest(person=person, home=home, count=count):
                hass = Hass()
                for entity, value in ((PERSON, person), (HOME, home), (COUNT, count)):
                    hass.put(entity, value)
                hass.put(ROOMS, "Living room")
                hass.put(MOTION, "on")
                hass.forbid_room_reads()
                actual = occupancy.home_presence(hass, config)
                self.assertEqual(actual[0], expected, actual)
                self.assertEqual(actual[2], [PERSON, HOME, COUNT])
        # A missing or stale tracker is not a verified negative, even when
        # room motion is ON and another direct tracker is away.
        for value, age in ((None, 1), ("home", 400), ("not_home", 400)):
            with self.subTest(missing_or_stale=value, age=age):
                hass = Hass()
                hass.put(HOME, "off")
                if value is not None:
                    hass.put(PERSON, value, age=age)
                hass.forbid_room_reads()
                actual = occupancy.home_presence(
                    hass, room_config(home_trackers=[PERSON, HOME],
                                      room_occupancy_sensors=[MOTION]),
                )
                self.assertEqual(actual[:2], ("unknown", "unverified_home_trackers"))

    def test_legacy_area_trackers_are_real_home_sources(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(TRACKER, "home")
        hass.forbid_room_reads()
        config = room_config(home_trackers=[PERSON], room_occupancy_sensors=[MOTION])
        self.assertEqual(occupancy.home_presence(hass, config, [TRACKER])[0], "home")
        hass.put(TRACKER, "not_home")
        self.assertEqual(occupancy.home_presence(hass, config, [TRACKER])[0], "away")
        self.assertEqual(
            occupancy.room_presence(hass, AREA, {"away_entities": [TRACKER]},
                                    room_config(), known_areas={AREA})[:2],
            ("unoccupied", "verified_home_away"),
        )
        # A caller that already resolved home can avoid re-reading its room
        # sources, even when those sources are missing or malformed.
        self.assertEqual(
            occupancy.room_presence(hass, AREA, {}, room_config(),
                                    known_areas={AREA}, home_status="away"),
            ("unoccupied", "verified_home_away", []),
        )

    def test_room_only_fallback_and_explicit_empty_values_remain_supported(self):
        hass = Hass()
        self.assertEqual(occupancy.home_presence(hass, {}),
                         ("home", "no_trackers_assume_home", []))
        self.assertEqual(occupancy.room_presence(hass, AREA, {}, {},
                                               known_areas={AREA})[0], "unoccupied")
        config = room_config()
        hass.put(ROOMS, "Living room")
        self.assertEqual(occupancy.home_presence(hass, config)[:2],
                         ("home", "occupied_rooms_present"))
        self.assertEqual(occupancy.room_presence(hass, AREA, {}, config,
                                               known_areas={AREA})[0], "occupied")
        for empty in ("", "[]", "none"):
            with self.subTest(empty=empty):
                hass.put(ROOMS, empty)
                self.assertEqual(occupancy.home_presence(hass, config)[:2],
                                 ("home", "no_occupied_rooms_cooldown"))
                self.assertEqual(
                    occupancy.room_presence(hass, AREA, {}, config, known_areas={AREA})[:2],
                    ("unoccupied", "verified_room_list_unoccupied"),
                )
        # An available event-driven list still means empty overnight.
        hass.put(ROOMS, "", age=400)
        self.assertEqual(occupancy.home_presence(hass, config)[0], "away")
        self.assertEqual(occupancy.room_presence(hass, AREA, {"occupancy_sensors": []},
                                               config, known_areas={AREA})[0], "unoccupied")
        hass.put(ROOMS, "unavailable")
        hass.put(MOTION, "on")
        sensor_config = {"room_occupancy_sensors": [MOTION]}
        self.assertEqual(occupancy.home_presence(hass, sensor_config)[:2],
                         ("home", "room_sensor_occupied"))
        self.assertEqual(occupancy.room_presence(hass, AREA, {}, config,
                                               known_areas={AREA})[0], "occupied")
        self.assertEqual(occupancy.room_presence(hass, AREA, {"occupancy_sensors": []},
                                               config, known_areas={AREA})[0], "unknown")
        hass.put(MOTION, "on", age=400)
        self.assertEqual(occupancy.home_presence(hass, sensor_config)[0], "home")

    def test_room_only_cooldown_uses_the_relevant_change_timestamp(self):
        hass = Hass()
        config = room_config()
        hass.put(ROOMS, "", changed_age=20)
        self.assertEqual(occupancy.home_presence(hass, config)[:2],
                         ("away", "occupied_rooms_empty"))
        hass.put(ROOMS, "", changed_age=1)
        self.assertEqual(occupancy.home_presence(hass, config)[:2],
                         ("home", "no_occupied_rooms_cooldown"))
        attr_config = room_config(occupied_rooms_attribute="rooms")
        hass.put(ROOMS, "ready", changed_age=20, updated_age=1, attributes={"rooms": []})
        self.assertEqual(occupancy.home_presence(hass, attr_config)[0], "home")
        hass.put(ROOMS, "ready", changed_age=1, updated_age=20, attributes={"rooms": []})
        self.assertEqual(occupancy.home_presence(hass, attr_config)[0], "away")
        sensor_config = {"room_occupancy_sensors": [MOTION], "away_cooldown_minutes": 10}
        for changed_age, expected in ((1, "home"), (20, "away")):
            hass.put(MOTION, "off", changed_age=changed_age)
            self.assertEqual(occupancy.home_presence(hass, sensor_config)[0], expected)

    def test_actual_live_gate_rechecks_home_and_ignores_mixed_plan_provenance(self):
        expected = {
            "occupied": ("held", "room_not_occupied"),
            "absent": ("eligible", "device_policy_approved"),
            "room": ("absent", "room_unoccupied"),
            "home": ("absent", "house_unoccupied"),
            "always": ("eligible", "device_policy_approved"),
        }
        hass = Hass()
        hass.put(PERSON, "home")
        hass.put(MOTION, "on")
        hass.put(ROOMS, "Living room")
        config = room_config(home_trackers=[PERSON], room_occupancy_sensors=[MOTION])
        settings = {"occupancy_sensors": [MOTION]}
        # Old plans contain room-source IDs in tracker_entities. Those IDs
        # must never be promoted into direct whole-home evidence at dispatch.
        plan = {"global_presence": config, "known_presence_areas": [AREA],
                "tracker_entities": [ROOMS, MOTION, PERSON], "occupancy": "occupied",
                "away": "home", "presence_entities": [MOTION]}
        self.assertEqual(occupancy.live_device_permission(
            hass, AREA, settings, plan, device()), ("eligible", "device_policy_approved"))
        hass.put(PERSON, "not_home", changed_age=0)
        hass.forbid_room_reads()
        for requirement, result in expected.items():
            with self.subTest(requirement=requirement):
                self.assertEqual(occupancy.live_device_permission(
                    hass, AREA, settings, plan, device(requirement)), result)
                # Also protect callers that pass an older room result to the
                # shared permission policy after establishing home absence.
                for stale_room in ("occupied", "unknown"):
                    self.assertEqual(occupancy.device_permission(
                        device(requirement), stale_room, "away", False), result)
        self.assertEqual(occupancy.device_permission(
            device("absent", sleep_behavior="pause"), "occupied", "away", True),
            ("held", "sleep_room_control_paused"))
        self.assertEqual(occupancy.device_permission(
            device("absent", sleep_behavior="pause"), "unknown", "away", None),
            ("eligible", "device_policy_approved"))
        # Legacy rooms have their own real away_entities, independently of
        # whether the cached plan has a General settings dictionary.
        legacy_plan = {**plan, "global_presence": None}
        self.assertEqual(occupancy.live_device_permission(
            hass, AREA, {**settings, "away_entities": [PERSON]}, legacy_plan, device()),
            ("held", "room_not_occupied"))

    def test_actual_room_plan_uses_away_without_motion_reads_or_vacancy_dwell(self):
        for value, age in (("Living room", 1), ("", 1), ("", 400), ("[broken", 1)):
            with self.subTest(value=value, age=age):
                hass = Hass()
                hass.put(PERSON, "not_home", changed_age=0)
                hass.put(ROOMS, value, age=age)
                hass.put(MOTION, "on", changed_age=0)
                hass.forbid_room_reads()
                settings = {"enabled": True, "controller": "environment",
                            "occupancy_sensors": [MOTION], "unoccupied_delay_minutes": 240}
                plan, sources = climate.gather(
                    hass, N(area_id=AREA, windows=[], readings=[]), settings,
                    global_presence=room_config(home_trackers=[PERSON],
                                                room_occupancy_sensors=[MOTION]),
                    known_areas={AREA}, now=NOW.timestamp(),
                )
                self.assertEqual((plan["away"], plan["occupancy"], plan["profile"]),
                                 ("away", "unoccupied", "away"))
                self.assertEqual(plan["occupancy_evidence"], "verified_home_away")
                self.assertNotIn(MOTION, sources)
                self.assertNotIn(ROOMS, sources)
        # When someone really is home, an explicit empty list remains valid
        # room absence and must not receive a second vacancy dwell either.
        hass = Hass()
        hass.put(PERSON, "home")
        hass.put(ROOMS, "")
        hass.put(MOTION, "on", changed_age=0)
        plan, _ = climate.gather(
            hass, N(area_id=AREA, windows=[], readings=[]),
            {"enabled": True, "controller": "environment", "occupancy_sensors": [MOTION],
             "unoccupied_delay_minutes": 240},
            global_presence=room_config(home_trackers=[PERSON]),
            known_areas={AREA}, now=NOW.timestamp(),
        )
        self.assertEqual((plan["away"], plan["occupancy"], plan["profile"]),
                         ("home", "unoccupied", "home"))
        self.assertEqual(plan["occupancy_evidence"], "verified_room_list_unoccupied")

    def test_returning_home_revalidates_a_missing_room_source(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(ROOMS, "", age=400)
        config = room_config(home_trackers=[PERSON])
        settings = {"occupancy_sensors": []}
        hass.forbid_room_reads()
        self.assertEqual(occupancy.room_presence(
            hass, AREA, settings, config, known_areas={AREA})[:2],
            ("unoccupied", "verified_home_away"))
        # A return invalidates the derived empty-room result. A now-
        # unavailable list cannot tell us which room the person entered.
        hass.put(ROOMS, "unavailable")
        hass.put(PERSON, "home", changed_age=0)
        hass.states.blocked.clear()
        hass.states.forbid_discovery = False
        self.assertEqual(occupancy.room_presence(
            hass, AREA, settings, config, known_areas={AREA})[:2],
            ("unknown", "room_occupancy_source_unknown"))
        plan = {"global_presence": config, "known_presence_areas": [AREA],
                "tracker_entities": [PERSON], "away": "away", "occupancy": "unoccupied"}
        for requirement in ("occupied", "absent"):
            self.assertEqual(occupancy.live_device_permission(
                hass, AREA, settings, plan, device(requirement)),
                ("held", "room_occupancy_unknown"))
        # The selected sensor resumes its normal fallback role immediately
        # when it reports fresh occupancy after somebody returns home.
        hass.put(MOTION, "on", changed_age=0)
        settings["occupancy_sensors"] = [MOTION]
        self.assertEqual(occupancy.room_presence(
            hass, AREA, settings, config, known_areas={AREA})[:2],
            ("occupied", "selected_room_sensor_on"))
        self.assertEqual(occupancy.live_device_permission(
            hass, AREA, settings, plan, device()),
            ("eligible", "device_policy_approved"))
        result, _ = climate.gather(
            hass, N(area_id=AREA, windows=[], readings=[]),
            {**settings, "enabled": True, "controller": "environment"},
            global_presence=config, known_areas={AREA}, now=NOW.timestamp(),
        )
        self.assertEqual((result["away"], result["occupancy"], result["profile"]),
                         ("home", "occupied", "comfort"))

    def test_quiet_fan_context_ignores_stale_room_plan_when_away(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(ROOMS, "Living room")
        hass.put(MOTION, "on")
        settings = {"occupancy_sensors": [MOTION], "away_entities": [PERSON]}
        manager = N(settings={"climate_rooms": {AREA: settings}})
        controller = N(hass=hass, manager=manager, clock=lambda: NOW.timestamp())
        spec = N(area_id=AREA)
        plan = {"global_presence": room_config(home_trackers=[PERSON]),
                "known_presence_areas": [AREA], "away": "home", "occupancy": "occupied",
                "tracker_entities": [ROOMS, MOTION, PERSON],
                "presence_entities": [MOTION], "sleeping": False}
        hass.forbid_room_reads()
        for quiet_sleep in (False, True):
            self.assertFalse(runtime._quiet_context(
                controller, spec, {"quiet_sleep": quiet_sleep, "quiet_occupied": True}, plan))
        # Legacy room trackers have the same authority even without General
        # configuration or trustworthy occupancy in the cached room plan.
        self.assertFalse(runtime._quiet_context(
            controller, spec, {"quiet_sleep": False, "quiet_occupied": True},
            {**plan, "global_presence": None}))

    def test_fallback_device_plan_includes_real_legacy_home_sources(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(TRACKER, "not_home")
        hass.put(ROOMS, "Living room")
        hass.put(MOTION, "on")
        spec = N(area_id=AREA)
        settings = {"occupancy_sensors": [MOTION], "away_entities": [TRACKER]}
        manager = N(hass=hass, plan=N(environment={}), device_specs=(spec,), settings={
            "climate_rooms": {AREA: settings},
            "occupancy_global": room_config(home_trackers=[PERSON],
                                           room_occupancy_sensors=[MOTION]),
            "room_sources": {AREA: {"windows": []}},
        })
        # plan_for still discovers window contacts; forbid only reads of the
        # room-presence entities, so unrelated window safeguards stay active.
        hass.states.blocked.update((ROOMS, MOTION))
        plan = equipment.plan_for(manager, spec)
        self.assertEqual((plan["away"], plan["occupancy"], plan["occupancy_evidence"]),
                         ("away", "unoccupied", "verified_home_away"))
        self.assertEqual(plan["presence_entities"], [])
        self.assertEqual(plan["tracker_entities"], [PERSON, TRACKER])
        self.assertFalse(plan["sleeping"])
        hass.put(TRACKER, "home")
        hass.states.blocked.clear()
        plan = equipment.plan_for(manager, spec)
        self.assertEqual((plan["away"], plan["occupancy"]), ("home", "occupied"))
        self.assertEqual(plan["tracker_entities"], [PERSON, TRACKER])

    def test_legacy_return_refreshes_room_sources_missing_from_cached_away_plan(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(MOTION, "on")
        spec = N(area_id=AREA)
        settings = {"enabled": True, "controller": "environment",
                    "away_entities": [PERSON], "occupancy_sensors": [MOTION]}
        manager = N(settings={"climate_rooms": {AREA: settings}})
        controller = N(hass=hass, manager=manager, clock=lambda: NOW.timestamp())
        hass.forbid_room_reads()
        plan, _ = climate.gather(
            hass, N(area_id=AREA, windows=[], readings=[]), settings,
            global_presence=None, known_areas={AREA}, now=NOW.timestamp(),
        )
        self.assertEqual(plan["occupancy"], "unoccupied")
        self.assertEqual(plan["presence_entities"], [])
        # The old plan intentionally contains no room sources while away.
        # Return-home command gates must resolve the configured sensors again.
        hass.put(PERSON, "home")
        hass.states.blocked.clear()
        hass.states.forbid_discovery = False
        self.assertEqual(occupancy.live_device_permission(
            hass, AREA, settings, plan, device("absent")),
            ("held", "room_not_absent"))
        self.assertEqual(occupancy.live_device_permission(
            hass, AREA, settings, plan, device("occupied")),
            ("eligible", "device_policy_approved"))
        self.assertTrue(runtime._quiet_context(
            controller, spec, {"quiet_sleep": False, "quiet_occupied": True}, plan))
        # A restored placeholder after returning is unknown, never permission
        # for absence-only control based on the previously verified away plan.
        hass.put(MOTION, "on", age=400, attributes={"restored": True})
        for requirement in ("occupied", "absent"):
            self.assertEqual(occupancy.live_device_permission(
                hass, AREA, settings, plan, device(requirement)),
                ("held", "room_occupancy_unknown"))

    def test_return_home_keeps_missing_selected_sources_unknown(self):
        missing = "binary_sensor.missing_selected_presence"
        for missing_area in (AREA, None):
            with self.subTest(missing_area=missing_area):
                hass = Hass()
                hass.put(PERSON, "not_home")
                hass.put(MOTION, "off")
                if missing_area is not None:
                    hass.entity_areas[missing] = missing_area
                settings = {"enabled": True, "controller": "environment",
                            "away_entities": [PERSON],
                            "occupancy_sensors": [MOTION, missing]}
                hass.forbid_room_reads()
                plan, _ = climate.gather(
                    hass, N(area_id=AREA, windows=[], readings=[]), settings,
                    global_presence=None, known_areas={AREA}, now=NOW.timestamp(),
                )
                self.assertEqual(plan["occupancy"], "unoccupied")
                self.assertEqual(plan["presence_entities"], [])
                hass.put(PERSON, "home")
                hass.states.blocked.clear()
                hass.states.forbid_discovery = False
                result = occupancy.room_presence(
                    hass, AREA, settings, {}, known_areas={AREA})
                self.assertEqual(result[0], "unknown")
                self.assertIn(missing, result[2])
                for requirement in ("occupied", "absent"):
                    self.assertEqual(occupancy.live_device_permission(
                        hass, AREA, settings, plan, device(requirement)),
                        ("held", "room_occupancy_unknown"))
                # A genuine selected positive remains sufficient even when
                # a different selected source has not reported after startup.
                hass.put(MOTION, "on")
                self.assertEqual(occupancy.room_presence(
                    hass, AREA, settings, {}, known_areas={AREA})[0], "occupied")
                self.assertEqual(occupancy.live_device_permission(
                    hass, AREA, settings, plan, device("occupied")),
                    ("eligible", "device_policy_approved"))
                self.assertEqual(occupancy.live_device_permission(
                    hass, AREA, settings, plan, device("absent")),
                    ("held", "room_not_absent"))
                # A source explicitly assigned to a different room remains
                # irrelevant; uncertainty cannot cross an established area.
                hass.entity_areas[missing] = "bath"
                hass.put(MOTION, "off")
                result = occupancy.room_presence(
                    hass, AREA, settings, {}, known_areas={AREA, "bath"})
                self.assertEqual(result[0], "unoccupied")
                self.assertNotIn(missing, result[2])


class ContinuityTests(unittest.IsolatedAsyncioTestCase):
    async def test_room_only_absence_survives_restart_only_after_fresh_revalidation(self):
        hass = Hass()
        config = room_config()
        state = hass.put(ROOMS, "", changed_age=30)
        store = Store()
        initial = continuity.PresenceContinuity(hass, "entry", store=store)
        await initial.async_start()
        context = initial.context(config)
        since = state.last_changed.timestamp()
        self.assertEqual(context["_verified_absence_since"], since)
        await initial.async_stop()
        # HA recreates the same current empty state with a new change time.
        hass.put(ROOMS, "", changed_age=0)
        restored = continuity.PresenceContinuity(hass, "entry", store=store)
        await restored.async_start()
        self.assertEqual(occupancy.home_presence(hass, config)[0], "home")
        context = restored.context(config)
        self.assertEqual(context["_verified_absence_since"], since)
        self.assertEqual(occupancy.home_presence(hass, context)[0], "away")
        for value, age in (("unknown", 1), ("unavailable", 1), ("[malformed", 400)):
            with self.subTest(value=value, age=age):
                hass.put(ROOMS, value, age=age)
                context = restored.context(config)
                self.assertNotIn("_verified_absence_since", context)
                self.assertEqual(occupancy.home_presence(hass, context)[0], "unknown")
                self.assertEqual(restored._since, since)
        hass.put(ROOMS, "Living room")
        self.assertNotIn("_verified_absence_since", restored.context(config))
        self.assertIsNone(restored._since)
        hass.put(ROOMS, "", changed_age=0)
        context = restored.context(config)
        self.assertEqual(occupancy.home_presence(hass, context)[0], "home")
        self.assertGreater(context["_verified_absence_since"], since)

    async def test_away_home_sources_ignore_room_activity_through_restart(self):
        hass = Hass()
        home = hass.put(PERSON, "not_home", changed_age=30)
        hass.put(ROOMS, "Living room", changed_age=0)
        hass.put(MOTION, "on", changed_age=0)
        config = room_config(home_trackers=[PERSON], room_occupancy_sensors=[MOTION])
        hass.forbid_room_reads()
        store = Store()
        initial = continuity.PresenceContinuity(hass, "entry", store=store)
        await initial.async_start()
        since = home.last_changed.timestamp()
        self.assertEqual(initial.context(config)["_verified_absence_since"], since)
        await initial.async_stop()
        hass.put(PERSON, "not_home", changed_age=0)
        restored = continuity.PresenceContinuity(hass, "entry", store=store)
        await restored.async_start()
        self.assertEqual(restored.context(config)["_verified_absence_since"], since)
        hass.put(ROOMS, "", age=400)
        hass.put(MOTION, "unavailable")
        context = restored.context(config)
        self.assertEqual(context["_verified_absence_since"], since)
        self.assertEqual(occupancy.home_presence(hass, context)[0], "away")
        hass.put(PERSON, "unknown")
        self.assertNotIn("_verified_absence_since", restored.context(config))
        self.assertEqual(restored._since, since)
        hass.put(PERSON, "home")
        self.assertNotIn("_verified_absence_since", restored.context(config))
        self.assertIsNone(restored._since)

    async def test_source_changes_and_untrusted_context_cannot_reuse_old_absence(self):
        hass = Hass()
        hass.put(PERSON, "not_home", changed_age=30)
        hass.put(ROOMS, "", changed_age=0, attributes={"rooms": []})
        config = room_config(home_trackers=[PERSON])
        instance = continuity.PresenceContinuity(hass, "entry", store=Store())
        old = instance.context(config)["_verified_absence_since"]
        # Removing the authoritative home source starts a room-only interval
        # at its own observed timestamp, not the old tracker-away timestamp.
        room_only = room_config()
        context = instance.context(room_only)
        self.assertGreater(context["_verified_absence_since"], old)
        self.assertEqual(occupancy.home_presence(hass, context)[0], "home")
        self.assertNotEqual(continuity.source_signature(config),
                            continuity.source_signature(room_only))
        attribute_config = room_config(occupied_rooms_attribute="rooms")
        self.assertNotEqual(continuity.source_signature(room_only),
                            continuity.source_signature(attribute_config))
        # Neither externally supplied internal context nor a changed source
        # attribute can import a previously verified absence timestamp.
        supplied = {**attribute_config, "_verified_absence_since": old}
        context = instance.context(supplied)
        self.assertGreater(context["_verified_absence_since"], old)
        self.assertEqual(occupancy.home_presence(hass, context)[0], "home")
        missing_source = room_config(occupied_rooms_entity="input_text.other_rooms")
        context = instance.context(missing_source)
        self.assertNotIn("_verified_absence_since", context)
        self.assertIsNone(instance._since)


if __name__ == "__main__":
    unittest.main(verbosity=2)
