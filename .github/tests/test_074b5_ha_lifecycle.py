"""HEM lifecycle regressions using shipped entry and manager methods.

Default mode uses strict event/task boundaries and fake controller/storage I/O.
--with-ha runs the same startup/stop tests through an actual HomeAssistant
instance and its event bus/task tracking. It never calls a physical service.
"""
from __future__ import annotations

import ast
import asyncio
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import importlib
import inspect
import logging
from pathlib import Path
import sys
import tempfile
from time import monotonic, time
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
REAL_HA = "--with-ha" in sys.argv
sys.argv = [arg for arg in sys.argv if arg != "--with-ha"]
PACKAGE = "hem_074b5_lifecycle"
package = ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package


def install_module(name, **members):
    module = ModuleType(name)
    module.__dict__.update(members)
    sys.modules[name] = module
    return module


if REAL_HA:
    from homeassistant.core import CoreState, HomeAssistant, SupportsResponse, callback
    from homeassistant.config_entries import ConfigEntry, ConfigEntryState
    from homeassistant.exceptions import ConfigEntryNotReady
    from homeassistant.const import (
        EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STARTED,
        EVENT_HOMEASSISTANT_STOP, EVENT_HOMEASSISTANT_FINAL_WRITE,
        EVENT_STATE_CHANGED,
    )
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers import storage
    from homeassistant.helpers.event import async_track_time_interval, async_call_later
else:
    class ConfigEntryNotReady(Exception):
        pass

    class CoreState(Enum):
        not_running = "NOT_RUNNING"
        starting = "STARTING"
        running = "RUNNING"
        stopping = "STOPPING"
        final_write = "FINAL_WRITE"

    def callback(function):
        return function

    SupportsResponse = NS(OPTIONAL="optional")
    EVENT_HOMEASSISTANT_START = "homeassistant_start"
    EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"
    EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
    EVENT_HOMEASSISTANT_FINAL_WRITE = "homeassistant_final_write"
    EVENT_STATE_CHANGED = "state_changed"
    install_module("homeassistant")
    install_module("homeassistant.core", CoreState=CoreState, callback=callback)
    install_module("homeassistant.exceptions", ConfigEntryNotReady=ConfigEntryNotReady)
    install_module("homeassistant.const", **{
        key: value for key, value in globals().copy().items() if key.startswith("EVENT_")
    })
    install_module("homeassistant.helpers")
    er = install_module("homeassistant.helpers.entity_registry")
    storage = install_module("homeassistant.helpers.storage")

    def async_track_time_interval(hass, action, interval, *, cancel_on_shutdown=False):
        return lambda: None

    def async_call_later(hass, delay, action):
        handle = hass.loop.call_later(delay, action, None)
        return handle.cancel

    install_module("homeassistant.helpers.event",
        async_track_time_interval=async_track_time_interval, async_call_later=async_call_later)


class EventBus:
    def __init__(self, hass):
        self.hass = hass
        self.listeners = defaultdict(list)

    def async_listen(self, event_type, listener):
        self.listeners[event_type].append(listener)
        def remove():
            if listener in self.listeners[event_type]:
                self.listeners[event_type].remove(listener)
        return remove

    def async_listen_once(self, event_type, listener):
        def once(event):
            remove()
            return listener(event)
        remove = self.async_listen(event_type, once)
        return remove

    def async_fire(self, event_type, data=None):
        event = NS(event_type=event_type, data=data or {})
        for listener in tuple(self.listeners[event_type]):
            result = listener(event)
            if inspect.isawaitable(result):
                self.hass.async_create_task(result)


class LocalHass:
    """Keep tracked startup work distinct from cancellable background work."""
    def __init__(self, config_dir):
        self.loop = asyncio.get_running_loop()
        self.state = CoreState.not_running
        self.data = {}
        self.config = NS(config_dir=config_dir, language="en")
        self.bus = EventBus(self)
        self._tasks, self._background_tasks = set(), set()
        self.services = NS(has_service=lambda *args: True, async_remove=lambda *args: None)
        self.states = NS(get=lambda entity_id: None)

    def set_state(self, state):
        self.state = state

    def async_create_task(self, target, name=None, eager_start=False):
        task = asyncio.create_task(target, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def async_create_background_task(self, target, name, eager_start=True):
        task = asyncio.create_task(target, name=name)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def async_add_executor_job(self, target, *args):
        return await asyncio.to_thread(target, *args)

    async def async_block_till_done(self):
        await asyncio.sleep(0)
        current = asyncio.current_task()
        while pending := [task for task in self._tasks if task is not current and not task.done()]:
            await asyncio.gather(*pending, return_exceptions=True)

    async def async_start(self):
        self.set_state(CoreState.starting)
        self.bus.async_fire(EVENT_HOMEASSISTANT_START)
        await self.async_block_till_done()
        self.set_state(CoreState.running)
        self.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await asyncio.sleep(0)

    async def async_stop(self, *, force=False):
        for task in tuple(self._background_tasks):
            task.cancel()
        self.set_state(CoreState.stopping)
        self.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
        await self.async_block_till_done()
        self.set_state(CoreState.final_write)
        self.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
        await self.async_block_till_done()
        self.set_state(CoreState.not_running)


class LocalEntry:
    def __init__(self):
        self.entry_id = "lifecycle-test"
        self.data, self.options, self.subentries = {}, {}, {}
        self.unload = []

    def async_on_unload(self, callback):
        self.unload.append(callback)

    def async_create_background_task(self, hass, target, name, eager_start=True):
        return hass.async_create_background_task(target, name, eager_start)


class ProbeStore:
    def __init__(self, hass, version, key, **kwargs):
        self.hass, self.key = hass, key
        self.saves = 0

    async def async_load(self):
        await asyncio.sleep(0)
        return None

    async def async_save(self, value):
        self.saves += 1
        await asyncio.sleep(0)

    def async_delay_save(self, *args, **kwargs):
        pass


class SnapshotStore(ProbeStore):
    """Control restore order while preserving the saved user-owned deadline."""
    def __init__(self, payload, *, gate=None):
        self.payload, self.gate = payload, gate
        self.load_entered = asyncio.Event()
        self.saved_values = []

    async def async_load(self):
        self.load_entered.set()
        if self.gate is not None:
            await self.gate.wait()
        return self.payload

    async def async_save(self, value):
        self.saved_values.append(dict(value))


class Controller:
    def __init__(self, *args, **kwargs):
        self.active = self._active = False
        self.starts, self.stops, self.quiesces, self.schedules = 0, [], [], 0
        self.start_gate = self.stop_gate = None
        self.start_entered = asyncio.Event()
        self.stop_entered = asyncio.Event()
        self.ready = self._ready = False
        self.retry_calls = 0
        self.refreshes = 0
        self.state_changes = 0
        self.statuses, self.records = {}, {}

    async def async_start(self):
        self.starts += 1
        self.start_entered.set()
        if self.start_gate is not None:
            await self.start_gate.wait()
        await asyncio.sleep(0)
        self.active = self._active = self.ready = self._ready = True

    def quiesce(self, *, shutdown=False):
        self.quiesces.append(shutdown)
        self.active = self._active = False

    async def async_stop(self, *, shutdown=False):
        self.stops.append(shutdown)
        self.stop_entered.set()
        self.quiesce(shutdown=shutdown)
        if self.stop_gate is not None:
            await self.stop_gate.wait()

    def start(self):
        self.active = self._active = True
        self.refreshes += 1

    def stop(self):
        self.active = self._active = False

    def clear(self):
        pass

    def refresh(self, **kwargs):
        self.refreshes += 1

    def schedule(self, *args, **kwargs):
        self.schedules += 1

    def observe(self, **kwargs):
        pass

    def observe_current(self):
        pass

    def state_changed(self, *args):
        self.state_changes += 1

    def observe_native_availability(self, *args):
        pass

    def prepare(self, plan):
        return plan

    def retry_pending_reviews(self):
        self.retry_calls += 1


const = importlib.import_module(PACKAGE + ".const")
logic = importlib.import_module(PACKAGE + ".logic")
history = importlib.import_module(PACKAGE + ".environment_history")
lifecycle = importlib.import_module(PACKAGE + ".lifecycle")
install_module(PACKAGE + ".device_faults", NativeDeviceFaultMonitor=Controller)
install_module(PACKAGE + ".shade_cooling", ShadeCoolingController=Controller)
install_module(PACKAGE + ".room_sources", native=lambda *args: True)
install_module(PACKAGE + ".advanced_comfort", async_migrate_advanced_comfort=lambda *args: None)
install_module(PACKAGE + ".room_hubs", async_sync_room_hubs=lambda *args: {},
    async_watch_room_hubs=lambda *args: lambda: None, home_subentry_id=lambda *args: None)
install_module(PACKAGE + ".device_hierarchy", async_register_hierarchy=lambda *args: None)
install_module(PACKAGE + ".pid_review", decode_mobile_action=lambda *args: None,
    is_pending=lambda *args: False)
install_module(PACKAGE + ".equipment_model", specs=lambda *args: ())
install_module(PACKAGE + ".discovery", entity_area=lambda *args: None,
    _device_class=lambda state: getattr(state, "attributes", {}).get("device_class"))


async def no_work(*args, **kwargs):
    return None


install_module(PACKAGE + ".wake_alarm", async_start_wake=no_work, async_stop_wake=no_work,
    quiesce_wake=lambda *args, **kwargs: None)


def production_namespace(path, wanted_class=None, wanted_functions=()):
    """Keep production methods/hook registration; isolate unrelated I/O ports."""
    namespace = {
        "__name__": PACKAGE + "." + path.stem, "__package__": PACKAGE,
        "asyncio": asyncio, "logging": logging, "callback": callback,
        "replace": replace, "timedelta": timedelta, "time": time, "monotonic": monotonic,
        "Plan": logic.Plan, "EnvironmentHistory": history.EnvironmentHistory,
        "EVENT_STATE_CHANGED": EVENT_STATE_CHANGED,
        "EVENT_HOMEASSISTANT_STOP": EVENT_HOMEASSISTANT_STOP,
        "EVENT_HOMEASSISTANT_STARTED": EVENT_HOMEASSISTANT_STARTED,
        "async_track_time_interval": async_track_time_interval, "async_call_later": async_call_later,
        "async_dispatcher_send": lambda *args: None,
        "equipment_legacy_settings": lambda *args: ({}, {}),
        "SupportsResponse": SupportsResponse,
        "SERVICE_SCHEMA": None, "PID_CONTROL_SCHEMA": None,
        "NATIVE_CLIMATE_SCHEMA": None, "CLIMATE_DIAGNOSTICS_SCHEMA": None,
    }
    namespace.update({key: value for key, value in vars(const).items() if key.isupper()})
    for name in ("AwayWindowAlert", "PresenceContinuity", "ArrivalPreparation",
                 "RoomVentilationMonitor", "WindowOpeningWait", "EquipmentRuntime",
                 "ClimatePidCoordinator", "NativeClimateControl", "DirectClimateControl",
                 "HumiditySetpointControl", "HumidityPowerControl", "SecondaryClimateSetpoint",
                 "RunningFanSpeedControl", "FanPowerControl", "NativeAirModeControl"):
        namespace[name] = Controller
    tree = ast.parse(path.read_text())
    body = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "lifecycle":
            body.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if all(isinstance(target, ast.Name) and
                   (target.id.isupper() or target.id == "_LOGGER") for target in targets):
                # Config schemas are unrelated to the lifecycle boundary and
                # their constructors are intentionally not substituted.
                if not any(target.id.endswith("SCHEMA") for target in targets):
                    body.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == wanted_class:
            body.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted_functions:
            body.append(node)
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), str(path), "exec"), namespace)
    return namespace


MANAGER_NS = production_namespace(SOURCE / "manager.py", wanted_class="AirQualityManager")
Manager = MANAGER_NS["AirQualityManager"]
ENTRY_NS = production_namespace(SOURCE / "__init__.py",
    wanted_functions=("async_setup_entry", "async_unload_entry"))


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.directory.name) if REAL_HA else LocalHass(self.directory.name)
        if REAL_HA:
            self.entry = ConfigEntry(version=1, minor_version=1,
                domain=const.DOMAIN, title="HEM lifecycle fixture", data={}, options={},
                source="user", unique_id=None, discovery_keys={}, subentries_data=None,
                state=ConfigEntryState.SETUP_IN_PROGRESS)
        else:
            self.entry = LocalEntry()
        self.forwarded, self.unloaded = 0, 0
        async def forward(*args):
            self.forwarded += 1
        async def unload(*args):
            self.unloaded += 1
            return True
        self.hass.config_entries = NS(async_forward_entry_setups=forward, async_unload_platforms=unload)
        self.manager = Manager(self.hass, self.entry)
        self.captures = 0
        def capture():
            self.captures += 1
            return logic.Plan("blocked", False, (), (), ())
        self.manager._capture = capture
        self.manager._tracked.add("sensor.native")
        ENTRY_NS["AirQualityManager"] = lambda hass, entry: self.manager
        self.storage_patch = patch.object(storage, "Store", ProbeStore, create=True)
        self.registry_patch = patch.object(er, "async_get",
            lambda hass: NS(async_get=lambda entity_id: NS(platform="native")), create=True)
        self.storage_patch.start()
        self.registry_patch.start()
        self.extras = []

    async def asyncTearDown(self):
        for task in self.extras:
            if not task.done():
                task.cancel()
        if self.extras:
            await asyncio.gather(*self.extras, return_exceptions=True)
        if hasattr(self.entry, "runtime_data"):
            await self.manager.async_stop(shutdown=True)
        await self.hass.async_stop(force=True)
        self.registry_patch.stop()
        self.storage_patch.stop()
        self.directory.cleanup()

    async def setup_entry(self):
        self.assertTrue(await ENTRY_NS["async_setup_entry"](self.hass, self.entry))

    async def started(self):
        await self.hass.async_start()
        await self.hass.async_block_till_done()
        await asyncio.sleep(0)

    def observe_lifecycle_unsubscribe(self):
        """Record redundant releases while retaining the real event bus hooks."""
        bus_class = type(self.hass.bus)
        original = bus_class.async_listen_once
        manual, duplicates = [], []
        def listen_once(bus, event_type, listener, *args, **kwargs):
            if (bus is not self.hass.bus
                    or getattr(listener, "__self__", None) is not self.manager
                    or event_type not in (EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP)):
                return original(bus, event_type, listener, *args, **kwargs)
            fired = released = False
            @callback
            def observed(event):
                nonlocal fired
                fired = True  # The bus has already removed its one-shot hook.
                return listener(event)
            unsubscribe = original(bus, event_type, observed, *args, **kwargs)
            def release():
                nonlocal released
                manual.append(event_type)
                if fired or released:
                    duplicates.append(event_type)
                released = True
                unsubscribe()
            return release
        return patch.object(bus_class, "async_listen_once", listen_once), manual, duplicates

    async def test_one_shot_lifecycle_events_do_not_repeat_unsubscribe(self):
        observe, manual, duplicates = self.observe_lifecycle_unsubscribe()
        with observe:
            await self.setup_entry()
            await self.started()
            # Direct replay must also be harmless once STARTED consumed its hook.
            self.manager._on_ha_started()
            await self.hass.async_stop(force=True)
            await self.manager.async_stop(shutdown=True)
        self.assertEqual(manual, [], "Consumed one-shot listeners were released again")
        self.assertEqual(duplicates, [])

    async def test_reload_after_running_releases_started_listener_only_once(self):
        await self.started()
        observe, manual, duplicates = self.observe_lifecycle_unsubscribe()
        with observe:
            await self.setup_entry()
            self.manager._on_ha_started()
            await self.hass.async_stop(force=True)
            await self.manager.async_stop(shutdown=True)
        self.assertEqual(manual, [EVENT_HOMEASSISTANT_STARTED])
        self.assertEqual(duplicates, [])

    async def test_global_homeassistant_stop_reaches_manager_without_entry_unload(self):
        await self.setup_entry()
        self.assertEqual(self.manager.equipment.retry_calls, 0)
        await self.started()
        self.assertGreater(self.manager.equipment.retry_calls, 0)
        self.assertTrue(self.manager._active)
        await asyncio.wait_for(self.hass.async_stop(force=True), 2)
        self.assertFalse(self.manager._active)
        self.assertEqual(self.unloaded, 0, "Core shutdown must not depend on an entry unload")
        self.assertEqual(self.manager.equipment.stops, [True])
        self.assertEqual(self.manager.direct_climate.stops, [True])
        self.assertFalse(self.manager._unsubs)

    async def test_startup_background_work_does_not_enter_core_startup_barrier(self):
        await self.setup_entry()
        gate = asyncio.Event()
        self.manager.equipment.retry_pending_reviews = lambda: self.extras.append(
            lifecycle.create_background_task(self.hass, self.entry, gate.wait(), "blocked review transport"))
        await asyncio.wait_for(self.started(), 1)
        self.assertIs(self.hass.state, CoreState.running)
        self.assertEqual(len(self.extras), 1)
        self.assertFalse(self.extras[0].done())
        await asyncio.wait_for(self.hass.async_stop(force=True), 2)
        self.assertTrue(self.extras[0].done())

    async def test_registry_burst_coalesces_fault_index_and_stop_cancels_pending_refresh(self):
        await self.setup_entry()
        self.hass.set_state(CoreState.starting)
        baseline = self.manager.faults.refreshes
        for _ in range(200):
            self.manager._on_registry_changed(NS(data={"entity_id": "sensor.foreign"}))
        self.assertEqual(self.manager.faults.refreshes, baseline)
        await asyncio.sleep(.85)
        self.assertEqual(self.manager.faults.refreshes, baseline + 1)
        self.manager._on_registry_changed(NS(data={"entity_id": "sensor.foreign"}))
        self.manager.quiesce(shutdown=True)
        await asyncio.sleep(.85)
        self.assertEqual(self.manager.faults.refreshes, baseline + 1)

    async def test_late_state_registry_and_clock_callbacks_cannot_reschedule_after_stop(self):
        await self.setup_entry()
        await self.started()
        await self.manager.async_stop(shutdown=True)
        captures, faults = self.captures, self.manager.faults.refreshes
        schedules = self.manager.equipment.schedules
        self.manager._on_state_changed(NS(data={"entity_id": "sensor.native",
            "old_state": NS(state="19", attributes={}), "new_state": NS(state="20", attributes={})}))
        self.manager._on_registry_changed(NS(data={"entity_id": "sensor.foreign"}))
        self.manager._on_interval(None)
        self.manager._on_fast_climate_interval(None)
        await asyncio.sleep(.02)
        self.assertEqual((self.captures, self.manager.faults.refreshes, self.manager.equipment.schedules),
                         (captures, faults, schedules))

    async def test_concurrent_stop_is_idempotent_and_normal_unload_keeps_reload_semantics(self):
        await self.setup_entry()
        await self.started()
        results = await asyncio.gather(*(self.manager.async_stop() for _ in range(5)))
        self.assertEqual(results, [True] * 5)
        self.assertEqual(self.manager.equipment.stops, [False])
        self.assertEqual(self.manager.direct_climate.stops, [False])
        self.assertTrue(await ENTRY_NS["async_unload_entry"](self.hass, self.entry))
        self.assertEqual(self.unloaded, 1)
        self.assertEqual(self.manager.direct_climate.stops, [False])

    async def test_global_stop_escalates_an_already_running_entry_reload(self):
        await self.setup_entry()
        await self.started()
        gate = self.manager.equipment.stop_gate = asyncio.Event()
        unload = asyncio.create_task(ENTRY_NS["async_unload_entry"](self.hass, self.entry))
        self.extras.append(unload)
        await asyncio.wait_for(self.manager.equipment.stop_entered.wait(), 1)
        stop = asyncio.create_task(self.hass.async_stop(force=True))
        self.extras.append(stop)
        # The STOP hook must remain attached until ordinary reload completes.
        # Each controller receives the escalated shutdown mode synchronously.
        for _ in range(5):
            await asyncio.sleep(0)
        self.assertTrue(self.manager._shutdown_requested)
        self.assertIn(True, self.manager.direct_climate.quiesces)
        gate.set()
        await asyncio.wait_for(asyncio.gather(unload, stop), 2)
        self.assertEqual(self.manager.equipment.stops, [False], "Cleanup ran twice")
        self.assertFalse(self.manager._active)

    async def test_global_stop_is_registered_before_first_blocking_startup_await(self):
        gate, entered = asyncio.Event(), asyncio.Event()
        original = self.manager.async_start
        async def blocked_start():
            entered.set()
            await gate.wait()
            await original()
        self.manager.async_start = blocked_start
        setup_task = asyncio.create_task(ENTRY_NS["async_setup_entry"](self.hass, self.entry))
        self.extras.append(setup_task)
        await asyncio.wait_for(entered.wait(), 1)
        self.hass.set_state(CoreState.starting)
        await asyncio.wait_for(self.hass.async_stop(force=True), 2)
        # Only production async_setup_entry's hook registration can satisfy
        # this; the manager's startup method has not been allowed to execute.
        self.assertTrue(self.manager._stopping)
        gate.set()
        result = (await asyncio.gather(setup_task, return_exceptions=True))[0]
        self.assertIsInstance(result, BaseException)
        self.assertEqual(self.forwarded, 0)

    async def test_stop_interrupts_inflight_restoration_without_forwarding_platforms(self):
        gate = asyncio.Event()
        self.manager.presence_continuity.start_gate = gate
        setup_task = asyncio.create_task(ENTRY_NS["async_setup_entry"](self.hass, self.entry))
        self.extras.append(setup_task)
        await asyncio.wait_for(self.manager.presence_continuity.start_entered.wait(), 1)
        self.hass.set_state(CoreState.starting)
        await asyncio.wait_for(self.hass.async_stop(force=True), 2)
        self.assertTrue(self.manager._stopping)
        self.assertFalse(self.manager._active)
        gate.set()
        result = (await asyncio.gather(setup_task, return_exceptions=True))[0]
        self.assertIsInstance(result, BaseException)
        self.assertEqual(self.forwarded, 0)
        self.assertFalse(self.manager._active)
        self.assertNotIn(self.entry.entry_id, self.hass.data.get(const.DOMAIN, {}))

    async def test_arrival_deadline_survives_slower_presence_continuity_restore(self):
        presence = importlib.import_module(PACKAGE + ".presence_continuity")
        arrival = importlib.import_module(PACKAGE + ".arrival_preparation")
        occupancy = importlib.import_module(PACKAGE + ".occupancy_policy")
        entity_id = "binary_sensor.room_presence"
        stamp = datetime.now(timezone.utc)
        if REAL_HA:
            self.hass.states.async_set(entity_id, "off", {"device_class": "occupancy"})
        else:
            state = NS(entity_id=entity_id, domain="binary_sensor", state="off",
                attributes={"device_class": "occupancy"}, last_changed=stamp,
                last_updated=stamp, last_reported=stamp)
            self.hass.states.get = lambda selected: state if selected == entity_id else None
        shared = {"room_occupancy_sensors": [entity_id], "away_cooldown_minutes": 10}
        options = {const.CONF_OCCUPANCY_GLOBAL: shared}
        gate = asyncio.Event()
        presence_store = SnapshotStore({"version": 1,
            "source_signature": presence.source_signature(occupancy.shared_home_settings(shared, {})),
            "verified_absence_since": stamp.timestamp() - 3600}, gate=gate)
        deadline = stamp.timestamp() + 3600
        arrival_store = SnapshotStore({"started_at": stamp.timestamp() - 300, "expires_at": deadline})
        self.manager.presence_continuity = presence.PresenceContinuity(
            self.hass, self.entry.entry_id, store=presence_store)
        self.manager.arrival_preparation = arrival.ArrivalPreparation(self.manager, store=arrival_store)
        with patch.object(Manager, "settings", property(lambda manager: options)):
            setup = asyncio.create_task(ENTRY_NS["async_setup_entry"](self.hass, self.entry))
            self.extras.append(setup)
            await asyncio.wait_for(presence_store.load_entered.wait(), 1)
            # The other Store can finish first. Freshly recreated OFF states
            # cannot be used to discard an already verified Away interval.
            await asyncio.sleep(.02)
            gate.set()
            self.assertTrue(await asyncio.wait_for(setup, 1))
            self.assertEqual(self.manager.arrival_preparation.home_status(), "away")
            self.assertTrue(self.manager.arrival_preparation.armed)
            self.assertEqual(self.manager.arrival_preparation.expires_at, deadline)

    async def test_stop_during_arrival_restore_preserves_unread_deadline(self):
        arrival = importlib.import_module(PACKAGE + ".arrival_preparation")
        stamp = time()
        gate = asyncio.Event()
        stored = SnapshotStore({"started_at": stamp - 300, "expires_at": stamp + 3600}, gate=gate)
        self.manager.arrival_preparation = arrival.ArrivalPreparation(self.manager, store=stored)
        setup = asyncio.create_task(ENTRY_NS["async_setup_entry"](self.hass, self.entry))
        self.extras.append(setup)
        await asyncio.wait_for(stored.load_entered.wait(), 1)
        self.hass.set_state(CoreState.starting)
        await asyncio.wait_for(self.hass.async_stop(force=True), 2)
        gate.set()
        result = (await asyncio.gather(setup, return_exceptions=True))[0]
        self.assertIsInstance(result, BaseException)
        self.assertEqual(stored.saved_values, [], "STOP overwrote an unread arrival deadline")
        self.assertFalse(self.manager.arrival_preparation.armed)

    async def test_cleanup_deadline_refuses_reload_when_storage_never_finishes(self):
        await self.setup_entry()
        await self.started()
        self.manager.equipment.stop_gate = asyncio.Event()
        with patch.dict(MANAGER_NS, STOP_TIMEOUT_SECONDS=.02, STOP_CANCEL_GRACE_SECONDS=.01):
            with self.assertLogs(MANAGER_NS["_LOGGER"], level="ERROR"):
                result = await asyncio.wait_for(
                    ENTRY_NS["async_unload_entry"](self.hass, self.entry), .5)
        self.assertFalse(result)
        self.assertEqual(self.unloaded, 0)
        self.assertIs(self.hass.data[const.DOMAIN][self.entry.entry_id], self.manager)
        self.assertFalse(self.manager._active)
        self.assertEqual(self.manager.equipment.stops, [False])
        self.assertFalse(await self.manager.async_stop())
        self.assertEqual(self.manager.equipment.stops, [False])

    async def test_global_stop_deadline_does_not_await_cancellation_resistant_writer(self):
        await self.setup_entry()
        await self.started()
        release, cancelled = asyncio.Event(), asyncio.Event()
        async def stubborn_cleanup(*, shutdown=False):
            while not release.is_set():
                try:
                    await release.wait()
                except asyncio.CancelledError:
                    cancelled.set()
        self.manager.equipment.async_stop = stubborn_cleanup
        try:
            with patch.dict(MANAGER_NS, STOP_TIMEOUT_SECONDS=.02, STOP_CANCEL_GRACE_SECONDS=.01):
                with self.assertLogs(MANAGER_NS["_LOGGER"], level="ERROR"):
                    await asyncio.wait_for(self.hass.async_stop(force=True), .5)
            self.assertTrue(cancelled.is_set())
            self.assertFalse(await self.manager.async_stop(shutdown=True))
            self.assertTrue(self.manager._stop_pending, "Uncertain writer ownership was lost")
            self.assertFalse(self.manager._active)
        finally:
            late = tuple(self.manager._stop_pending)
            release.set()
            await asyncio.gather(*late, return_exceptions=True)
            await asyncio.sleep(0)
        self.assertFalse(self.manager._stop_pending)

    async def test_failed_setup_cannot_replace_an_incomplete_cleanup_writer(self):
        release, cancelled = asyncio.Event(), asyncio.Event()
        created = []
        def construct(hass, entry):
            created.append(self.manager)
            if len(created) != 1:
                raise AssertionError("Setup constructed a replacement before cleanup completed")
            return self.manager
        async def fail_start():
            await asyncio.sleep(0)
            raise RuntimeError("fixture startup failed")
        async def stubborn_cleanup(*, shutdown=False):
            while not release.is_set():
                try:
                    await release.wait()
                except asyncio.CancelledError:
                    cancelled.set()
        ENTRY_NS["AirQualityManager"] = construct
        self.manager.native_climate.async_start = fail_start
        self.manager.equipment.async_stop = stubborn_cleanup
        try:
            with patch.dict(MANAGER_NS, STOP_TIMEOUT_SECONDS=.02, STOP_CANCEL_GRACE_SECONDS=.01):
                with self.assertLogs(MANAGER_NS["_LOGGER"], level="ERROR"):
                    with self.assertRaisesRegex(RuntimeError, "fixture startup failed"):
                        await asyncio.wait_for(ENTRY_NS["async_setup_entry"](self.hass, self.entry), .5)
            self.assertTrue(cancelled.is_set())
            self.assertTrue(self.manager._stop_pending)
            with self.assertRaisesRegex(ConfigEntryNotReady, "Previous HEM cleanup did not finish"):
                await asyncio.wait_for(ENTRY_NS["async_setup_entry"](self.hass, self.entry), .5)
            self.assertEqual(len(created), 1)
            self.assertIs(self.entry.runtime_data, self.manager)
            self.assertEqual(self.forwarded, 0)
            self.assertNotIn(self.entry.entry_id, self.hass.data.get(const.DOMAIN, {}))
        finally:
            late = tuple(self.manager._stop_pending)
            release.set()
            await asyncio.gather(*late, return_exceptions=True)
            await asyncio.sleep(0)

    async def test_failed_setup_can_retry_after_complete_cleanup(self):
        async def fail_start():
            raise RuntimeError("fixture startup failed")
        self.manager.native_climate.async_start = fail_start
        with self.assertRaisesRegex(RuntimeError, "fixture startup failed"):
            await ENTRY_NS["async_setup_entry"](self.hass, self.entry)
        previous = self.manager
        self.assertTrue(await previous.async_stop())
        self.manager = Manager(self.hass, self.entry)
        self.manager._capture = lambda: logic.Plan("blocked", False, (), (), ())
        await self.setup_entry()
        self.assertIs(self.entry.runtime_data, self.manager)
        self.assertIsNot(self.manager, previous)
        self.assertTrue(self.manager._active)
        self.assertFalse(previous._active)
        self.assertEqual(self.forwarded, 1)

    async def test_one_cleanup_failure_does_not_skip_other_controllers(self):
        await self.setup_entry()
        async def fail_cleanup(*, shutdown=False):
            raise OSError("fixture storage unavailable")
        self.manager.equipment.async_stop = fail_cleanup
        with self.assertLogs(MANAGER_NS["_LOGGER"], level="ERROR"):
            self.assertFalse(await self.manager.async_stop(shutdown=True))
        self.assertEqual(self.manager.fan_power.stops, [True])
        self.assertEqual(self.manager.pid.stops, [True])
        self.assertEqual(self.manager.shading.stops, [True])
        self.assertFalse(self.manager._unsubs)

    async def test_independent_restores_overlap_but_control_waits_for_all(self):
        active = maximum = finished = 0
        controllers = [controller for name, controller in self.manager._controllers()
                       if name != "fault_monitor"]
        for controller in controllers:
            original = controller.async_start
            async def restore(original=original):
                nonlocal active, maximum, finished
                active += 1
                maximum = max(maximum, active)
                try:
                    await asyncio.sleep(.01)
                    await original()
                    finished += 1
                finally:
                    active -= 1
            controller.async_start = restore
        original_capture = self.manager._capture
        def capture():
            self.assertEqual(finished, len(controllers), "Control observed a partially restored manager")
            return original_capture()
        self.manager._capture = capture
        await self.setup_entry()
        self.assertGreater(maximum, 1)
        self.assertLessEqual(maximum, 4)
        self.assertGreater(self.captures, 0)


if __name__ == "__main__":
    print("Lifecycle test transport:", "actual HomeAssistant startup/stop" if REAL_HA else "strict local adapter")
    unittest.main(verbosity=2)
