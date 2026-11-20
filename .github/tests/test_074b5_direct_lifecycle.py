"""Actual direct controller teardown, ownership and cancellation regressions.

Only registry/state, service and storage transport are isolated. The shipped
controller and its ownership journals execute unchanged; no hardware is used.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "hem_074b5_direct_lifecycle"
package = ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components/environment_manager")]
sys.modules[PACKAGE] = package


def transport_module(name, **members):
    module = ModuleType(name)
    module.__dict__.update(members)
    sys.modules[name] = module
    return module


transport_module(PACKAGE + ".discovery",
    entity_area=lambda hass, entity: hass.areas.get(entity),
    temperature_sensor_c=lambda *args: 18.0)
transport_module(PACKAGE + ".climate_arbitration", new_command_gate=lambda *args, **kwargs: None)
transport_module(PACKAGE + ".climate_entry_ownership", foreign_owner_hold=lambda *args: None)
production = importlib.import_module(PACKAGE + ".climate_direct")


class MemoryStore:
    def __init__(self):
        self.saved = []

    async def async_save(self, value):
        self.saved.append(deepcopy(value))

    def async_delay_save(self, snapshot, delay):
        pass  # The final explicit save is checked below.


class DirectLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def controller(self, *, count=1):
        calls, states, areas = [], {}, {}

        async def service_call(domain, service, data, *, target, blocking):
            entity = target["entity_id"]
            calls.append((domain, service, entity))
            states[entity].state = "off" if service == "turn_off" else "on"

        hass = N(is_stopping=False, states=states, areas=areas,
                 services=N(has_service=lambda *args: True, async_call=service_call),
                 async_create_task=asyncio.create_task)
        controller = production.DirectClimateControl(hass, "entry", clock=lambda: 10_000.0)
        controller._active = controller._ready = True
        controller._store = MemoryStore()
        for index in range(count):
            entity, area = f"switch.heater_{index}", f"room_{index}"
            states[entity], areas[entity] = N(state="on"), area
            controller.expected[entity] = {
                "state": True, "when": 9000.0, "phase": "commanded", "area": area,
            }
            controller.energized_since[entity] = 9000.0
            controller._last_config[area] = {
                "controller": "on_off", "heat_actuator": entity,
                "direct_hardware_confirmed": True, "allow_actuation": True,
            }
        return controller, calls

    async def test_whole_ha_stop_preserves_owned_outputs_without_safe_off(self):
        controller, calls = self.controller(count=2)
        journal = controller._snapshot()
        controller.hass.is_stopping = True
        controller.quiesce(shutdown=True)
        await controller.async_stop(shutdown=True)
        await controller.async_stop(shutdown=True)
        self.assertFalse(controller._active)
        self.assertEqual(calls, [])
        self.assertEqual(controller._snapshot(), journal)
        self.assertEqual(controller._store.saved[-1], journal)

    async def test_entry_reload_still_safely_turns_off_confirmed_owned_outputs(self):
        controller, calls = self.controller(count=2)
        await controller.async_stop()
        await controller.async_stop()
        self.assertEqual(calls, [("switch", "turn_off", "switch.heater_0"),
                                 ("switch", "turn_off", "switch.heater_1")])
        self.assertTrue(all(row["phase"] == "commanded" and row["state"] is False
                            for row in controller.expected.values()))
        self.assertEqual(controller.energized_since, {})

    async def test_stop_cancels_and_drains_evaluations_and_retirements(self):
        controller, calls = self.controller()
        entered, drained = [], []

        async def pending(label):
            entered.append(label)
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                drained.append(label)

        evaluation = asyncio.create_task(pending("evaluation"))
        retirement = asyncio.create_task(pending("retirement"))
        controller._tasks["room_0"] = evaluation
        controller._retiring["room_0"] = retirement
        evaluation.add_done_callback(lambda task: controller._tasks.pop("room_0", None))
        retirement.add_done_callback(lambda task: controller._retiring.pop("room_0", None))
        await asyncio.sleep(0)
        self.assertEqual(len(entered), 2)
        controller.quiesce(shutdown=True)
        await asyncio.sleep(0)
        # Repeated quiesce must not interrupt a cancellation cleanup await.
        controller.quiesce(shutdown=True)
        await controller.async_stop(shutdown=True)
        self.assertEqual(sorted(drained), ["evaluation", "retirement"])
        self.assertTrue(evaluation.cancelled() and retirement.cancelled())
        self.assertEqual(calls, [])
        self.assertEqual(controller._stop_tasks, set())

    async def test_stop_upgrade_prevents_later_reload_commands(self):
        controller, calls = self.controller(count=2)
        entered, release = asyncio.Event(), asyncio.Event()
        original = controller.hass.services.async_call

        async def blocked_first(*args, **kwargs):
            await original(*args, **kwargs)
            entered.set()
            await release.wait()

        controller.hass.services.async_call = blocked_first
        stopping = asyncio.create_task(controller.async_stop())
        await asyncio.wait_for(entered.wait(), 1)
        controller.hass.is_stopping = True
        controller.quiesce(shutdown=True)
        release.set()
        await asyncio.wait_for(stopping, 1)
        self.assertEqual(calls, [("switch", "turn_off", "switch.heater_0")])
        self.assertFalse(controller.expected["switch.heater_0"]["state"])
        self.assertTrue(controller.expected["switch.heater_1"]["state"])

    async def test_late_schedule_and_retire_callbacks_do_not_create_tasks(self):
        controller, calls = self.controller()
        controller.hass.is_stopping = True
        controller.hass.async_create_task = lambda coroutine: self.fail("Created work while stopping")
        controller.schedule(controller._last_config, {})
        controller._retire_room("room_0", controller._last_config["room_0"])
        self.assertEqual(controller._tasks, {})
        self.assertEqual(controller._retiring, {})
        self.assertEqual(calls, [])

    async def test_interrupted_restore_never_overwrites_unread_ownership(self):
        controller, calls = self.controller()
        controller._ready = False
        started = asyncio.Event()
        store = MemoryStore()

        async def load():
            started.set()
            await asyncio.Event().wait()

        store.async_load = load
        storage = ModuleType("homeassistant.helpers.storage")
        storage.Store = lambda *args, **kwargs: store
        with patch.dict(sys.modules, {storage.__name__: storage}):
            startup = asyncio.create_task(controller.async_start())
            await started.wait()
            controller.quiesce(shutdown=True)
            startup.cancel()
            await asyncio.gather(startup, return_exceptions=True)
        await controller.async_stop(shutdown=True)
        self.assertEqual(store.saved, [])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
