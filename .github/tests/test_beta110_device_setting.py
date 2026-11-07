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
from dataclasses import asdict, dataclass
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
module("homeassistant.exceptions", HomeAssistantError=ValueError)
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
sequence = importlib.import_module(PKG+".equipment_setpoint_sequence")
native_target = importlib.import_module(PKG+".equipment_native_target")
activation = importlib.import_module(PKG+".device_activation")
# Isolate the hardware runtime from its unrelated HA platform dependencies.
# Execute its unmodified method body; the fake has no command lock or service
# transport. It must save without either while a tick/ACK is outstanding.
code = ast.parse((ROOT/"equipment_runtime.py").read_text())
method = next(n for cls in code.body if getattr(cls, "name", None)=="EquipmentRuntime"
              for n in cls.body if getattr(n,"name",None)=="async_update")
active_mode = next(n for cls in code.body if getattr(cls, "name", None)=="EquipmentRuntime"
                   for n in cls.body if getattr(n,"name",None)=="active_control_mode")
ns = dict(asyncio=asyncio, model=model, HomeAssistantError=ValueError, deepcopy=deepcopy,
          finite=model.finite, __package__=PKG)
exec(compile(ast.Module([method,active_mode], []), "equipment_runtime.py", "exec"), ns)


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
        profiles = {self.a.identifier: {"control_mode": "automatic", "other": 12},
                    self.b.identifier: {"control_mode": "pid"}}
        m.entry = NS(entry_id="test", options={"unrelated": {"keep": 123}, model.SETTINGS:profiles},
                     data={"sources":{"room":["climate.a","climate.b"]}},
                     runtime_data=m, async_on_unload=lambda f: None)
        self.states = {x.source_entities[0]: NS(state="heat",attributes={
            "supported_features":model.TEMP, "hvac_modes":["heat","off"],
            "min_temp":5.0, "max_temp":35.0}) for x in self.devices}
        self.native_ids=set()
        self.registry_entries={x.source_entities[0]:NS(id=x.identifier+"_registry",
            unique_id=x.identifier+"_native") for x in self.devices}
        m.hass=NS(states=self.states, config=NS(language="el"),
            registry=NS(async_get_entity_id=lambda plat,dom,id: id if id in self.native_ids else None,
                        async_get=self.registry_entries.get),
            config_entries=NS(async_update_entry=lambda entry,options: setattr(entry,"options",options)))
        self.holds={"thermostat_a":{"pending":{"phase":"intent"}, "paused":"physical_manual_override"}}
        self.signals=[]
        rt = NS(manager=m,hass=m.hass,_ready=True,_active=True,_tasks={},
                _current_spec=lambda spec:spec in self.devices, statuses={}, records=self.holds,
                _presentation_updates=NS(request=self.signals.append))
        rt.async_update=lambda spec,values: ns["async_update"](rt,spec,values)
        rt.active_control_mode=lambda spec: ns["active_control_mode"](rt,spec)
        m.equipment=rt
        for spec in self.devices:
            profiles[spec.identifier]["_native_authorization"]=activation.authority_context(m,spec)

    def cache(self, device):
        """The same exact native identity and attributes persisted by runtime."""
        record=self.holds.setdefault(device.identifier,{})
        record.update(area=device.area_id, source_device_id=device.source_device_id,
            sources=list(device.source_entities),
            capabilities=asdict(model.capabilities(self.manager,device)),
            capabilities_authority=activation.authority_context(self.manager,device),
            baseline={entity:{"attributes":deepcopy(self.states[entity].attributes)}
                      for entity in device.source_entities})
        return record

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
        self.cache(self.a)
        self.cache(self.b)
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
        self.states[b.source_entities[0]]=NS(state="cool",attributes={
            "hvac_modes":["cool","off"],"supported_features":model.TEMP,
            "min_temp":4.0,"max_temp":32.0})
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
        self.cache(self.a)
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
        self.assertEqual(cfg["control_mode"],"automatic")

    def test_temperature_range_humidifier_and_unrelated_outputs(self):
        for name,attrs,expected in (
            ("climate.range",{"hvac_modes":["off","heat_cool"],"supported_features":model.RANGE},False),
            ("humidifier.h",{"device_class":"dehumidifier"},False),
            ("climate.vent",{"hvac_modes":["fan_only","off"],"supported_features":model.FAN},False),
            ("fan.vent",{"supported_features":1},False),
            ("switch.heater",{},False),
            ("number.heater",{"min":0,"max":100},False),
            ("input_number.heater",{"min":0,"max":100},False),
        ):
            with self.subTest(name=name):
                m=self.manager
                m.entry.data["sources"]["room"].append(name)
                self.states[name]=NS(state="off",attributes=attrs)
                if name.startswith(("switch.","number.","input_number.")):
                    m.entry.data["climate_rooms"]={"room":{"heat_actuator":name}}
                spec=Device(name,"room",name,"physical_"+name,(name,))
                self.assertEqual(features.timed_setpoint_supported(m,m.hass.registry,spec),expected)

    def test_cached_capability_bound_to_original_offline_device(self):
        m=self.manager
        rec=self.cache(self.a)
        self.states.clear()
        self.assertTrue(features.timed_setpoint_supported(m,m.hass.registry,self.a))
        self.assertTrue(self.switch(self.a).available)
        rec["source_device_id"]="different"
        self.assertFalse(features.timed_setpoint_supported(m,m.hass.registry,self.a))
        self.assertFalse(self.switch(self.a).available)

    async def test_registered_inactive_control_becomes_usable_without_reload(self):
        m=self.manager
        raw=m.entry.options[model.SETTINGS][self.a.identifier]
        grant=raw.pop("_native_authorization")
        raw["control_mode"]="existing"
        added=[]
        await platform.async_setup_entry(m.hass,m.entry,added.extend)
        control=next(e for e in added if isinstance(e,platform.EquipmentTimedSetpointSwitch)
                     and e._spec==self.a)
        self.assertFalse(control.available)
        self.assertFalse(control.extra_state_attributes["timed_setpoint_supported"])
        for method in ("manual","automatic","pid"):
            raw["control_mode"]=method
            self.assertFalse(control.available,"A method alone must not grant native power")
        raw["_native_authorization"]=grant
        for method in ("automatic","pid"):
            raw["control_mode"]=method
            self.assertTrue(control.available)
            self.assertTrue(control.extra_state_attributes["timed_setpoint_supported"])
        raw["control_mode"]="manual"
        self.assertFalse(control.available)
        self.assertEqual(sum(isinstance(e,platform.EquipmentTimedSetpointSwitch)
                             and e._spec==self.a for e in added),1)

    def test_effective_mode_and_method_change_eligibility_immediately(self):
        m=self.manager
        state=self.states["climate.a"]
        state.attributes.update(hvac_modes=["heat","cool","dry","fan_only","auto","heat_cool","off"],
                                supported_features=model.TEMP|model.RANGE|model.HUMIDITY)
        raw=m.entry.options[model.SETTINGS][self.a.identifier]
        raw.update(mode_settings_version=1,mode_settings={
            "heat":{"control_mode":"pid"},"cool":{"control_mode":"automatic"},
            "dry":{"control_mode":"automatic"},"fan_only":{"control_mode":"automatic"},
            "auto":{"control_mode":"automatic"},"heat_cool":{"control_mode":"automatic"}})
        control=self.switch(self.a)
        for mode,expected in (("heat",True),("cool",True),("dry",False),
                              ("fan_only",False),("auto",False),("heat_cool",False)):
            with self.subTest(mode=mode):
                raw["requested_mode"]=mode
                self.assertEqual(control.available,expected)
                self.assertEqual(control.extra_state_attributes["timed_setpoint_supported"],expected)
        raw["requested_mode"]="heat"
        raw["mode_settings"]["heat"]["control_mode"]="manual"
        self.assertFalse(control.available)
        raw["mode_settings"]["heat"]["control_mode"]="automatic"
        state.state="off"  # Native OFF does not remove a selected HEAT policy.
        self.assertTrue(control.available)

    def test_native_feature_off_and_actual_limits_are_required(self):
        m=self.manager
        native=self.states["climate.a"]
        valid=deepcopy(native.attributes)
        invalid=(
            {**valid,"supported_features":0},
            {**valid,"supported_features":model.RANGE},
            {**valid,"hvac_modes":["heat"]},
            {**valid,"hvac_modes":["dry","off"]},
            {key:value for key,value in valid.items() if key!="min_temp"},
            {key:value for key,value in valid.items() if key!="max_temp"},
            {**valid,"min_temp":35,"max_temp":5},
            {**valid,"max_temp":float("nan")},
        )
        self.cache(self.a)
        for attrs in invalid:
            with self.subTest(attributes=attrs):
                native.attributes=attrs
                self.assertFalse(sequence.configuration_supported(m,self.a))
                self.assertFalse(self.switch(self.a).available,
                                 "Old capability cache must not override withdrawn live support")
        native.attributes=valid
        self.assertTrue(self.switch(self.a).available)

    def test_offline_evidence_requires_identity_bounds_and_current_authority(self):
        m=self.manager
        rec=self.cache(self.a)
        self.states.clear()
        control=self.switch(self.a)
        self.assertTrue(control.available)
        self.assertFalse(sequence.control_supported(m,self.a),"Offline cache is editor evidence only")
        original=self.registry_entries["climate.a"].unique_id
        self.registry_entries["climate.a"].unique_id="replacement_native"
        self.assertFalse(control.available)
        self.registry_entries["climate.a"].unique_id=original
        low=rec["baseline"]["climate.a"]["attributes"].pop("min_temp")
        self.assertFalse(control.available)
        rec["baseline"]["climate.a"]["attributes"]["min_temp"]=low
        self.assertTrue(control.available)
        m.entry.options[model.SETTINGS][self.a.identifier].pop("_native_authorization")
        self.assertTrue(sequence.configuration_supported(m,self.a))
        self.assertFalse(control.available,"Capability history cannot restore a revoked power grant")

    async def test_unsupported_legacy_flag_is_preserved_but_cannot_be_enabled(self):
        m=self.manager
        raw=m.entry.options[model.SETTINGS][self.a.identifier]
        raw.update(control_mode="manual",timed_setpoint_sequence=True)
        control=self.switch(self.a)
        self.assertTrue(control.is_on)
        self.assertFalse(control.available)
        before=deepcopy(m.entry.options)
        with self.assertRaises(ValueError):
            await control.async_turn_on()
        with self.assertRaises(ValueError):
            await m.equipment.async_update(self.a,{"timed_setpoint_sequence":True})
        self.assertEqual(m.entry.options,before)
        await control.async_turn_off()
        self.assertFalse(control.is_on)
        self.assertEqual(model.settings(m,self.a)["control_mode"],"manual")

    async def test_enable_rechecks_native_capability_after_options_lock(self):
        m=self.manager
        before=deepcopy(m.entry.options)
        m._device_settings_write_lock=asyncio.Lock()
        async with m._device_settings_write_lock:
            saving=asyncio.create_task(self.switch(self.a).async_turn_on())
            await asyncio.sleep(0)
            self.states["climate.a"].attributes["supported_features"]=0
        with self.assertRaises(ValueError):
            await saving
        self.assertEqual(m.entry.options,before)

    def test_global_flag_metadata_and_scoped_flag_identity(self):
        m=self.manager
        m.faults=NS(active=True,details=lambda spec:None)
        controls=[
            (platform.EquipmentQuietSwitch(m,self.a,"sensor_verified"),"sensor_verified"),
            (platform.EquipmentQuietSwitch(m,self.a,"quiet_sleep"),"quiet_sleep"),
            (platform.EquipmentQuietSwitch(m,self.a,"quiet_occupied"),"quiet_occupied"),
            (platform.EquipmentErrorAnnouncementSwitch(m,self.a),"announce_device_errors"),
            (self.switch(self.a),"timed_setpoint_sequence"),
            (platform.EquipmentNativeFullOutputSwitch(m,self.a),"native_full_output"),
            (platform.EquipmentHouseholdSleepSwitch(m,self.a),"sleep_when_everyone_asleep"),
            (platform.EquipmentWindowAnnouncementSwitch(m,self.a),"announce_before_start"),
            (platform.EquipmentWindowPauseSwitch(m,self.a),"pause_on_window_open"),
        ]
        for control,key in controls:
            with self.subTest(key=key):
                attrs=control.extra_state_attributes
                self.assertEqual(attrs["setting_key"],key)
                self.assertEqual(attrs["equipment_option_role"],"policy")
                self.assertTrue(attrs["setting_label"])
                self.assertTrue(attrs["configuration_help"])
                self.assertEqual(attrs["source_entity_ids"],["climate.a"])
        timed=self.switch(self.a).extra_state_attributes
        self.assertEqual(timed["timed_setpoint_transition_seconds"],30)
        self.states["climate.a"].attributes.update(supported_features=model.TEMP|model.FAN,
                                                   fan_modes=["low","high"])
        scoped=platform.EquipmentQuietSwitch(m,self.a,"quiet_sleep",operating_mode="heat")
        self.assertEqual(scoped.extra_state_attributes["settings_scope"],"operating_mode")
        self.assertEqual(scoped.extra_state_attributes["operating_mode"],"heat")
        self.assertNotIn("equipment_option_role",scoped.extra_state_attributes)

    async def test_full_output_is_shared_per_device_and_disables_new_timed_use(self):
        m=self.manager
        a=platform.EquipmentNativeFullOutputSwitch(m,self.a)
        b=platform.EquipmentNativeFullOutputSwitch(m,self.b)
        raw=m.entry.options[model.SETTINGS][self.a.identifier]
        raw['timed_setpoint_sequence']=True
        self.assertTrue(a.is_on and a.available and b.is_on)
        self.assertTrue(self.switch(self.a).available)
        before=deepcopy(self.holds)
        await a.async_turn_off()
        self.assertFalse(a.is_on)
        self.assertTrue(b.is_on)
        self.assertTrue(a.available,'The supported preference remains editable while disabled')
        self.assertTrue(self.switch(self.a).is_on,'Preserve the saved timed preference')
        self.assertFalse(self.switch(self.a).available,'Full-output OFF makes new timed writes inapplicable')
        self.assertEqual(self.holds,before,'Preference writes cannot acknowledge native commands')
        self.cache(self.a)
        self.states.pop('climate.a')
        await a.async_turn_on()
        self.assertTrue(a.is_on and self.switch(self.a).available)
        self.assertTrue(a.extra_state_attributes['native_full_output_supported'])
        self.assertEqual(a.extra_state_attributes['setting_key'],'native_full_output')
        raw=m.entry.options[model.SETTINGS][self.a.identifier]
        raw['control_mode']='manual'
        self.assertFalse(a.available)
        with self.assertRaises(ValueError):
            await a.async_turn_on()
        await a.async_turn_off()
        self.assertEqual(model.settings(m,self.a)['control_mode'],'manual')

    async def test_full_output_registration_and_live_direction_capability_gates(self):
        m=self.manager
        raw=m.entry.options[model.SETTINGS][self.a.identifier]
        raw['control_mode']='existing'
        added=[]
        await platform.async_setup_entry(m.hass,m.entry,added.extend)
        control=next(e for e in added if isinstance(e,platform.EquipmentNativeFullOutputSwitch)
                     and e._spec==self.a)
        self.assertFalse(control.available)
        raw['control_mode']='pid'
        self.assertTrue(control.available,'Existing to PID needs no platform reload')
        native=self.states['climate.a']
        native.attributes.update(hvac_modes=['off','heat','cool','dry','fan_only'],
            supported_features=model.TEMP|model.HUMIDITY|model.FAN,min_humidity=30,max_humidity=80)
        for mode,supported in (('heat',True),('cool',True),('dry',True),('fan_only',False)):
            raw['requested_mode']=mode
            self.assertEqual(control.available,supported,mode)
            self.assertEqual(control.extra_state_attributes['native_full_output_supported'],supported)
        raw['requested_mode']='dry'
        native.attributes.pop('min_humidity')
        self.assertFalse(control.available,'No invented humidity endpoint')
        native.attributes['min_humidity']=30
        self.assertTrue(control.available)
        native.attributes['hvac_modes']=['dry']
        self.assertFalse(control.available,'A setpoint-only device has no binary full-output option')


if __name__=="__main__":
    unittest.main()
