"""Device fan limits through the actual model, Number platform and writer.

HA state/registry/options storage is simulated. Production _fan selects the
native request; its final dispatch boundary is captured without operating
hardware. Existing runtime suites exercise that boundary's power/ACK gates.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from dataclasses import asdict
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem_beta112_fan_limits"


def module(name, **values):
    value = ModuleType(name)
    value.__dict__.update(values)
    sys.modules[name] = value
    return value


class NumberEntity:
    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def available(self):
        return True


module(PKG, __path__=[str(ROOT)])
module("homeassistant", __path__=[])
module("homeassistant.core", callback=lambda f: f)
module("homeassistant.const", EVENT_STATE_CHANGED="state_changed")
module("homeassistant.exceptions", HomeAssistantError=ValueError)
module("homeassistant.components", __path__=[])
module("homeassistant.components.number", NumberEntity=NumberEntity, NumberMode=N(BOX="box"))
module("homeassistant.helpers", __path__=[])
module("homeassistant.helpers.entity", EntityCategory=N(CONFIG="config"))
module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry)
module("homeassistant.helpers.dispatcher", async_dispatcher_connect=lambda *a: lambda: None)
module("homeassistant.helpers.event", async_track_state_change_event=lambda *a: lambda: None)
# Shading has no role in this numeric-entity platform regression.
module(PKG+".shade_cooling", SHADE_NUMBERS={})
model = importlib.import_module(PKG+".equipment_model")
numbers = importlib.import_module(PKG+".number")
allocator = importlib.import_module(PKG+".pid_output_allocator")

tree = ast.parse((ROOT/"equipment_runtime.py").read_text())
runtime = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EquipmentRuntime")
methods = [n for n in runtime.body if getattr(n, "name", None) in ("async_update", "_fan")]
scope = dict(__name__=PKG+".equipment_runtime", __package__=PKG,
             asyncio=asyncio, deepcopy=deepcopy, model=model,
             HomeAssistantError=ValueError, finite=model.finite,
             fan_speed_for_pid=allocator.fan_speed_for_pid)
exec(compile(ast.Module(methods, []), "equipment_runtime.py", "exec"), scope)


class Registry:
    def __init__(self):
        self.ids, self.removed = {}, []

    def async_get_entity_id(self, platform, domain, unique_id):
        return self.ids.get(unique_id)

    def async_remove(self, entity_id):
        self.removed.append(entity_id)
        self.ids = {key: value for key, value in self.ids.items() if value != entity_id}


class Manager:
    @property
    def settings(self):
        return {**self.entry.data, **self.entry.options}


class FanLimitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.a = model.ManagedDevice("fan_a", "room", "A", "physical_a", ("fan.a",))
        self.b = model.ManagedDevice("fan_b", "room", "B", "physical_b", ("fan.b",))
        self.fixed = model.ManagedDevice("fan_fixed", "room", "Fixed", "physical_fixed", ("fan.fixed",))
        self.devices = [self.a, self.b, self.fixed]
        self.manager = m = Manager()
        m.entry = N(entry_id="test", data={"areas":["room"], "climate_rooms":{
            "room":{"selected_devices":["fan.a", "fan.b", "fan.fixed"]}}},
            options={model.SETTINGS:{self.a.identifier:{"control_mode":"pid", "preserve":"A"},
                                     self.b.identifier:{"control_mode":"automatic", "preserve":"B"}},
                     "unrelated":{"keep":42}}, runtime_data=m,
            async_on_unload=lambda callback: None)
        m._device_hierarchy = {"controllers": {s.identifier:{"spec":s} for s in self.devices}}
        self.states = {"fan.a":N(state="on",attributes={"supported_features":1,
                                  "percentage_step":10,"percentage":100}),
                       "fan.b":N(state="on",attributes={"supported_features":1,
                                  "percentage_step":25,"percentage":100}),
                       "fan.fixed":N(state="on",attributes={"supported_features":0})}
        self.registry = Registry()
        self.listeners = {}
        m.hass = N(states=self.states, registry=self.registry, config=N(language="en"),
            config_entries=N(async_update_entry=lambda entry,options: setattr(entry,"options",options)),
            bus=N(async_listen=lambda event,callback: self.listeners.setdefault(event,callback)))
        self.signals, self.calls, self.statuses = [], [], []
        self.records = {s.identifier:{"pending":{"phase":"commanded","attempts":2},
                            "paused":"physical_manual_override",
                            "power":{s.source_entities[0]:{"since":123,"min_on":600}}}
                        for s in self.devices}
        rt = N(manager=m,hass=m.hass,_ready=True,_active=True,records=self.records,
               statuses={},_current_spec=lambda spec:spec in self.devices,
               _presentation_updates=N(request=self.signals.append),
               _record=lambda spec:self.records[spec.identifier],
               _quiet_context=lambda *args:False,
               _status=lambda spec,status,**extra:self.statuses.append(status))
        # The independent settings path must never acquire a hardware lock.
        rt._lock = lambda identifier: self.fail("Fan configuration waited for the actuator lock")
        rt.async_update = lambda spec,values: scope["async_update"](rt,spec,values)

        async def capture(spec,cap,entity,service,data,expected,**kwargs):
            self.calls.append((spec.identifier,entity,service,deepcopy(data)))
            return True

        rt._send = capture
        m.equipment = self.runtime = rt

    def old_room(self, minimum=40, maximum=80):
        self.manager.entry.options["environment_rooms"] = {"room":{
            "equipment_limits":{"fan_min_percentage":minimum,"fan_max_percentage":maximum}}}

    def limits(self, device):
        cap = model.capabilities(self.manager,device)
        return model.device_limits(self.manager,device,cap)

    def entities(self, device):
        return {e._key:e for e in numbers._equipment_numbers(self.manager,device,self.registry)
                if e._key in model.FAN_LIMIT_FIELDS}

    async def fan(self, device, demand):
        cfg = model.settings(self.manager,device)
        cfg["control_mode"] = "pid"
        return await scope["_fan"](self.runtime,device,model.capabilities(self.manager,device),
                                   cfg,{},demand,True)

    async def test_independent_limits_drive_actual_fan_selection_without_waiting_for_ack(self):
        self.old_room()
        before = deepcopy(self.manager.entry.options)
        evidence = deepcopy(self.records)
        await self.entities(self.a)["fan_max_percentage"].async_set_native_value(60)
        self.assertEqual(self.manager.entry.options[model.SETTINGS][self.a.identifier]["fan_speed_limits"],
                         {"fan_min_percentage":40,"fan_max_percentage":60})
        self.assertEqual(self.manager.entry.options[model.SETTINGS][self.b.identifier],
                         before[model.SETTINGS][self.b.identifier])
        self.assertEqual(self.manager.entry.options["environment_rooms"],before["environment_rooms"])
        self.assertEqual(self.records,evidence)
        self.assertEqual(self.calls,[])
        for device,expected in ((self.a,60),(self.b,75)):
            self.assertTrue(await self.fan(device,100))
            self.assertEqual(self.calls[-1],(device.identifier,device.source_entities[0],
                                           "set_percentage",{"percentage":expected}))
        for device,expected in ((self.a,40),(self.b,50)):
            self.assertTrue(await self.fan(device,1))
            self.assertEqual(self.calls[-1][3],{"percentage":expected})
        self.states["fan.a"].state = "off"
        count = len(self.calls)
        self.assertFalse(await self.fan(self.a,100))
        self.assertEqual(len(self.calls),count,"A nonzero minimum must not turn a fan on")

    async def test_fresh_defaults_use_each_native_fan_and_old_room_values_survive(self):
        self.assertEqual(self.limits(self.a)["fan_min_percentage"],10)
        self.assertEqual(self.limits(self.b)["fan_min_percentage"],25)
        self.assertFalse(set(model.available_room_limit_fields(self.manager,"room"))
                         & set(model.FAN_LIMIT_FIELDS))
        self.old_room()
        for device in (self.a,self.b):
            self.assertEqual({key:self.limits(device)[key] for key in model.FAN_LIMIT_FIELDS},
                             {"fan_min_percentage":40,"fan_max_percentage":80})
        # Beta17's old per-device keys had been merged conservatively since
        # Beta18. Preserve that effective policy until a new explicit edit.
        self.manager.entry.options.pop("environment_rooms")
        profiles = self.manager.entry.options[model.SETTINGS]
        profiles[self.a.identifier].update(fan_min_percentage=30,fan_max_percentage=90)
        profiles[self.b.identifier].update(fan_min_percentage=40,fan_max_percentage=80)
        self.assertEqual(self.limits(self.a)["fan_min_percentage"],40)
        self.assertEqual(self.limits(self.a)["fan_max_percentage"],80)
        await self.runtime.async_update(self.a,{"fan_min_percentage":20,"fan_max_percentage":60})
        self.assertEqual(self.limits(self.a)["fan_min_percentage"],20)
        self.assertEqual(self.limits(self.a)["fan_max_percentage"],60)
        self.assertEqual(self.limits(self.b)["fan_min_percentage"],40)
        self.assertEqual(self.limits(self.b)["fan_max_percentage"],80)

    async def test_invalid_native_ranges_and_mixed_authority_are_rejected_atomically(self):
        self.old_room()
        baseline = deepcopy(self.manager.entry.options)
        for payload in ({"fan_max_percentage":39},{"fan_max_percentage":45},
                        {"fan_min_percentage":10},{"fan_max_percentage":101},
                        {"fan_max_percentage":float("nan")},{"fan_max_percentage":True},
                        {"fan_max_percentage":75,"control_mode":"automatic"}):
            with self.subTest(payload=payload),self.assertRaises(ValueError):
                await self.runtime.async_update(self.b,payload)
            self.assertEqual(self.manager.entry.options,baseline)
        self.assertEqual(self.entities(self.fixed),{})
        with self.assertRaises(ValueError):
            await self.runtime.async_update(self.fixed,{"fan_min_percentage":10})
        self.assertEqual(self.manager.entry.options,baseline)

    async def test_platform_moves_only_fan_controls_and_preserves_room_fallback_data(self):
        self.old_room()
        prefix = "test_area_room_room_equipment_limit_"
        for key in (*model.FAN_LIMIT_FIELDS,"temperature_min_limit"):
            self.registry.ids[prefix+key] = "number.room_"+key
        self.registry.ids[self.a.identifier+"_fan_min_percentage"] = "number.saved_device_min"
        before = deepcopy(self.manager.entry.options)
        added = []
        await numbers.async_setup_entry(self.manager.hass,self.manager.entry,added.extend)
        self.assertEqual(set(self.registry.removed),{
            "number.room_fan_min_percentage","number.room_fan_max_percentage"})
        self.assertIn(self.a.identifier+"_fan_min_percentage",self.registry.ids)
        device_controls = [e for e in added if isinstance(e,numbers.EquipmentNumber)
                           and e._key in model.FAN_LIMIT_FIELDS]
        self.assertEqual(len(device_controls),4)
        self.assertFalse(any(getattr(e,"_kind",None)=="room_equipment_limit"
                             and e._key in model.FAN_LIMIT_FIELDS for e in added))
        for e in device_controls:
            self.assertEqual(e._attr_device_info["identifiers"],
                             {("environment_manager",e._spec.identifier)})
            self.assertTrue(e._attr_name.startswith("Fan · "))
            self.assertEqual(e.extra_state_attributes["fan_limit_scope"],"device")
        self.assertEqual(self.manager.entry.options,before)

    async def test_offline_numbers_and_writes_preserve_exact_controller_configuration(self):
        self.old_room()
        await self.runtime.async_update(self.a,{"fan_min_percentage":20,"fan_max_percentage":60})
        for key in model.FAN_LIMIT_FIELDS:
            self.registry.ids[self.b.identifier+"_"+key] = "number.b_"+key
        self.states.clear()
        a,b = self.entities(self.a),self.entities(self.b)
        self.assertEqual({key:e.native_value for key,e in a.items()},
                         {"fan_min_percentage":20,"fan_max_percentage":60})
        self.assertEqual({key:e.native_value for key,e in b.items()},
                         {"fan_min_percentage":40,"fan_max_percentage":80})
        self.assertTrue(all(e.available for e in (*a.values(),*b.values())))
        before = deepcopy(self.records)
        await a["fan_max_percentage"].async_set_native_value(70)
        await b["fan_max_percentage"].async_set_native_value(75)
        self.assertEqual(self.entities(self.a)["fan_max_percentage"].native_value,70)
        self.assertEqual(self.entities(self.b)["fan_max_percentage"].native_value,75)
        self.assertEqual(self.records,before)
        self.assertEqual(self.calls,[])

    async def test_exact_saved_capability_and_late_native_fan_restore(self):
        cap = model.capabilities(self.manager,self.b)
        self.records[self.b.identifier].update(area=self.b.area_id,
            source_device_id=self.b.source_device_id,sources=list(self.b.source_entities),
            capabilities=asdict(cap))
        old = self.states.pop("fan.b")
        self.assertEqual(set(self.entities(self.b)),set(model.FAN_LIMIT_FIELDS))
        self.assertEqual(self.entities(self.b)["fan_min_percentage"]._attr_native_min_value,25)
        self.records[self.b.identifier]["source_device_id"] = "different_device"
        self.assertEqual(self.entities(self.b),{})
        added = []
        await numbers.async_setup_entry(self.manager.hass,self.manager.entry,added.extend)
        self.states["fan.b"] = old
        event = N(data={"entity_id":"fan.b","old_state":None,"new_state":old})
        self.listeners["state_changed"](event)
        self.listeners["state_changed"](event)
        b = [e for e in added if isinstance(e,numbers.EquipmentNumber)
             and e._spec==self.b and e._key in model.FAN_LIMIT_FIELDS]
        self.assertEqual(len(b),2,"Late native capabilities register each limit exactly once")

    async def test_settings_lock_rechecks_identity_and_preserves_simultaneous_options(self):
        lock = self.manager._device_settings_write_lock = asyncio.Lock()
        async with lock:
            saving = asyncio.create_task(self.runtime.async_update(self.a,{"fan_max_percentage":60}))
            await asyncio.sleep(0)
            self.manager.entry.options["unrelated"]["keep"] = 43
        await saving
        self.assertEqual(self.manager.entry.options["unrelated"]["keep"],43)
        baseline = deepcopy(self.manager.entry.options)
        async with lock:
            saving = asyncio.create_task(self.runtime.async_update(self.a,{"fan_max_percentage":70}))
            await asyncio.sleep(0)
            self.devices.remove(self.a)
        with self.assertRaises(ValueError):
            await saving
        self.assertEqual(self.manager.entry.options,baseline)


if __name__ == "__main__":
    unittest.main(verbosity=2)
