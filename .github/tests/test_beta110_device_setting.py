"""Per-device timed setpoint preferences against the real model, switch and writer.

Only HA entity/registry storage, notifications and native state are simulated.
The test manager intentionally has no physical service interface.
"""
from __future__ import annotations

import ast
import asyncio
import importlib
import sys
import unittest
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem_beta110_setting"


def module(name, **attrs):
    obj = ModuleType(name)
    obj.__dict__.update(attrs)
    sys.modules[name] = obj
    return obj


@dataclass(frozen=True)
class Device:
    identifier: str
    area_id: str
    name: str
    source_device_id: str
    source_entities: tuple


package = module(PKG, __path__=[str(ROOT)])
keys = ("CONF_AREAS CONF_AUTO_NOTIFY CONF_AUTO_TTS CONF_HUB CONF_AI_REWRITE "
        "CONF_SHADE_ANNOUNCE CONF_AWAY_WINDOWS_ALERT SIGNAL_UPDATED").split()
module(PKG+".const", DOMAIN="environment_manager", **{k: k.lower() for k in keys})
module(PKG+".device_hierarchy", ManagedDevice=Device, configured_area_ids=lambda cfg: (),
       configured_sources=lambda cfg, area: cfg["sources"][area])
module(PKG+".room_hubs", async_add_grouped_entities=lambda manager, add, items: add(list(items)))
module(PKG+".room_sources", selected=lambda *args: ())
module(PKG+".device_controls", update_device_setting=None, AREA_ENV_FLAGS=(),
       CLIMATE_OPERATING_FLAGS=(), GLOBAL_ENV_FLAGS=(), climate_settings=lambda *args: None)
module("homeassistant", __path__=[])
module("homeassistant.core", callback=lambda cb: cb)
module("homeassistant.components", __path__=[])
module("homeassistant.components.switch", SwitchEntity=type("SwitchEntity", (), {}))
module("homeassistant.helpers", __path__=[])
module("homeassistant.helpers.dispatcher", async_dispatcher_connect=lambda hass, signal, cb:
       (setattr(hass, "policy_change", cb), lambda: None)[1])
module("homeassistant.helpers.entity", EntityCategory=NS(CONFIG="config"))
module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry)
module("homeassistant.helpers.event", async_track_state_change_event=lambda h,ids,cb:
       (setattr(h, "capability_change", cb), lambda: None)[1])
model = importlib.import_module(PKG+".equipment_model")
features = importlib.import_module(PKG+".equipment_feature_registration")
platform = importlib.import_module(PKG+".switch")
names = importlib.import_module(PKG+".equipment_name_catalog")
# Isolate the hardware runtime from its unrelated HA platform dependencies.
# Execute its unmodified method body; the fake has no command lock or service
# transport. It must save without either while a tick/ACK is outstanding.
code = ast.parse((ROOT/"equipment_runtime.py").read_text())
method = next(n for cls in code.body if getattr(cls, "name", None)=="EquipmentRuntime"
              for n in cls.body if getattr(n,"name",None)=="async_update")
ns = dict(asyncio=asyncio, model=model, HomeAssistantError=ValueError, deepcopy=deepcopy, finite=model.finite)
exec(compile(ast.Module([method], []), "equipment_runtime.py", "exec"), ns)


class Manager:
    @property
    def settings(self):
        return {**self.entry.data, **self.entry.options}


class SettingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.a = Device("thermostat_a", "room", "A", "deviceA", ("climate.a",))
        self.b = Device("thermostat_b", "room", "B", "deviceB", ("climate.b",))
        self.manager = m = Manager()
        self.devices = [self.a, self.b]
        m._device_hierarchy = {"controllers": {x.identifier: {"spec": x} for x in self.devices}}
        profiles = {self.a.identifier: {"control_mode": "existing", "other": 12},
                    self.b.identifier: {"control_mode": "pid", "_native_authorization": {"grant": "B"}}}
        m.entry = NS(entry_id="test", options={"unrelated": {"keep": 123}, model.SETTINGS:profiles},
                     data={"sources":{"room":["climate.a","climate.b"]}},
                     runtime_data=m, async_on_unload=lambda f: None)
        self.states = {x.source_entities[0]: NS(state="heat",attributes={
            "supported_features":model.TEMP, "hvac_modes":["heat","off"]}) for x in self.devices}
        self.native_ids=set()
        m.hass=NS(states=self.states, config=NS(language="el"),
            registry=NS(async_get_entity_id=lambda plat,dom,id: id if id in self.native_ids else None),
            config_entries=NS(async_update_entry=lambda entry,options: setattr(entry,"options",options)))
        self.holds={"thermostat_a":{"pending":{"phase":"intent"}, "paused":"physical_manual_override"}}
        self.signals=[]
        rt = NS(manager=m,hass=m.hass,_ready=True,_active=True,_tasks={},
                _current_spec=lambda spec:spec in self.devices, statuses={}, records=self.holds,
                _presentation_updates=NS(request=self.signals.append))
        rt.async_update=lambda spec,values: ns["async_update"](rt,spec,values)
        m.equipment=rt

    def switch(self, device):
        return platform.EquipmentTimedSetpointSwitch(self.manager, device)

    async def test_default_invalid_off_then_write_only_chosen_device(self):
        a,b=self.switch(self.a),self.switch(self.b)
        profiles=self.manager.entry.options[model.SETTINGS]
        self.assertFalse(model.DEFAULTS["timed_setpoint_sequence"])
        self.assertFalse(a.is_on)
        for invalid in (None,1,"true",[],{}):
            profiles[self.a.identifier]["timed_setpoint_sequence"]=invalid
            self.assertFalse(a.is_on)
        baseline=deepcopy(self.manager.entry.options)
        holds=deepcopy(self.holds)
        self.states.clear()  # Both native appliances offline.
        rt=self.manager.equipment
        rt._tasks[self.a.identifier]=NS(done=lambda: False)
        self.assertTrue(a.available)
        await a.async_turn_on()
        baseline[model.SETTINGS][self.a.identifier]["timed_setpoint_sequence"]=True
        self.assertEqual(self.manager.entry.options, baseline)
        self.assertTrue(self.switch(self.a).is_on)  # Reconstruction from stored profile.
        self.assertFalse(b.is_on)
        self.assertEqual(rt._setpoint_rerun,{self.a.identifier})
        await a.async_turn_off()
        self.assertFalse(a.is_on)
        self.assertEqual(self.holds,holds)
        self.assertEqual(self.signals,[self.a.identifier,self.a.identifier])
        self.assertEqual(a.extra_state_attributes["timed_setpoint_role"], "policy")
        self.assertEqual(a._attr_device_info["identifiers"], {("environment_manager",self.a.identifier)})
        self.assertIn("Χρονισμός στόχων",a._attr_name)

    async def test_bad_value_mixed_authority_and_stale_identity_rejected(self):
        m=self.manager
        before=deepcopy(m.entry.options)
        for payload in ({"timed_setpoint_sequence":"false"},
                        {"timed_setpoint_sequence":True,"control_mode":"automatic"}):
            with self.assertRaises(ValueError):
                await m.equipment.async_update(self.a,payload)
        m._device_settings_write_lock = asyncio.Lock()
        async with m._device_settings_write_lock:
            saving=asyncio.create_task(self.switch(self.a).async_turn_on())
            await asyncio.sleep(0)
            self.devices.remove(self.a)
        with self.assertRaises(ValueError):
            await saving
        self.assertEqual(before,m.entry.options)
        self.assertEqual(self.signals,[])

    async def test_platform_registers_only_verifiable_capabilities_and_late_arrivals(self):
        a,b=self.a,self.b
        m=self.manager
        self.states[b.source_entities[0]].attributes={"hvac_modes":["dry","off"],"supported_features":0}
        added=[]
        await platform.async_setup_entry(m.hass,m.entry,added.extend)
        controls=lambda:[e._spec for e in added if isinstance(e, platform.EquipmentTimedSetpointSwitch)]
        self.assertEqual(controls(),[a])
        old=self.states[b.source_entities[0]]
        self.states[b.source_entities[0]]=NS(state="dry",attributes={
            "hvac_modes":["dry","off"],"supported_features":model.HUMIDITY})
        event=NS(data={"entity_id":"climate.b","old_state":old,"new_state":self.states["climate.b"]})
        m.hass.capability_change(event)
        m.hass.capability_change(event)
        self.assertEqual(controls(),[a,b])
        self.states.clear()
        self.assertFalse(features.timed_setpoint_supported(m,m.hass.registry,a))
        self.native_ids.add(a.identifier+"_timed_setpoint_sequence")
        self.assertTrue(features.timed_setpoint_supported(m,m.hass.registry,a))
        self.assertFalse(features.timed_setpoint_supported(m,m.hass.registry,b))

    async def test_independent_preference_survives_concurrent_full_profile_save(self):
        m=self.manager
        rt=m.equipment
        self.states.clear()
        rt._record=lambda spec: self.holds[spec.identifier]
        rt._lock=lambda key: device_lock
        rt._status=lambda *a,**kw: None
        device_lock=asyncio.Lock()
        m._device_settings_write_lock=asyncio.Lock()
        async with m._device_settings_write_lock:
            enabling=asyncio.create_task(self.switch(self.a).async_turn_on())
            await asyncio.sleep(0)
            # The cooldown editor reads the original (OFF) settings before
            # waiting behind the switch writer for the shared options lock.
            cooldown=asyncio.create_task(rt.async_update(self.a,{"power_switch_cooldown_seconds":180}))
            await asyncio.sleep(0)
            self.assertTrue(device_lock.locked())
        await asyncio.gather(enabling,cooldown)
        cfg=model.settings(m,self.a)
        self.assertTrue(cfg["timed_setpoint_sequence"])
        self.assertEqual(cfg["power_switch_cooldown_seconds"],180)
        self.assertEqual(cfg["control_mode"],"existing")

    def test_temperature_range_humidifier_and_unrelated_outputs(self):
        for name,attrs,expected in (
            ("climate.range",{"hvac_modes":["off","heat_cool"],"supported_features":model.RANGE},True),
            ("humidifier.h",{"device_class":"dehumidifier"},True),
            ("climate.vent",{"hvac_modes":["fan_only","off"],"supported_features":model.FAN},False),
            ("fan.vent",{"supported_features":1},False),
            ("switch.heater",{},False),
        ):
            with self.subTest(name=name):
                m=self.manager
                m.entry.data["sources"]["room"].append(name)
                self.states[name]=NS(state="off",attributes=attrs)
                if name.startswith("switch."):
                    m.entry.data["climate_rooms"]={"room":{"heat_actuator":name}}
                spec=Device(name,"room",name,"physical_"+name,(name,))
                self.assertEqual(features.timed_setpoint_supported(m,m.hass.registry,spec),expected)

    def test_cached_capability_bound_to_original_offline_device(self):
        from dataclasses import asdict
        m=self.manager
        rec=m.equipment.records[self.a.identifier]
        rec.update(area="room",source_device_id="deviceA",sources=["climate.a"],
                   capabilities=asdict(model.capabilities(m,self.a)),baseline={
                       "climate.a":{"attributes":{"supported_features":model.TEMP}}})
        self.states.clear()
        self.assertTrue(features.timed_setpoint_supported(m,m.hass.registry,self.a))
        rec["source_device_id"]="different"
        self.assertFalse(features.timed_setpoint_supported(m,m.hass.registry,self.a))


if __name__=="__main__":
    unittest.main()
