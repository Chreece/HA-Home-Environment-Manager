"""Generic HEM thermal watchdog: integration of room evidence and two OFF retries.

No real device or Zigbee model. All I/O routes through test-only stubs;
the production watchdog module is executed without monkeypatching its body.
"""
import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]/"custom_components/environment_manager"

pkg=ModuleType("test_hem_b21")
pkg.__path__=[str(ROOT)]
sys.modules[pkg.__name__]=pkg


def module(name, file=None):
    fullname=pkg.__name__+"."+name
    obj=ModuleType(fullname)
    obj.__package__=pkg.__name__
    sys.modules[fullname]=obj
    if file:
        loader=importlib.util.spec_from_file_location(fullname,ROOT/file)
        obj.__spec__=loader
        loader.loader.exec_module(obj)
    return obj


model=module("equipment_model")
room_sources=module("room_sources")
# The production module imports its source adapter at module-load time.
room_sources.room_temperature_evidence=lambda *_a,**_kw:(None,{})
discovery=module("discovery")
faults=module("device_faults")
languages=module("languages")
watch=module("off_state_watchdog","off_state_watchdog.py")
runtime_module=module("off_state_runtime","off_state_runtime.py")

spec=SimpleNamespace(identifier="physical_controller",area_id="living",
                     source_device_id="zigbee_device",source_entities=("climate.heater",),
                     name="Generic room heater")
cap=SimpleNamespace(primary="climate.heater",domain="climate",modes=("off","heat"))
cfg={"control_mode":"pid","announce_device_errors":True}
env={"time":100.0,"temp":20.0,"permission":True,"source_available":True,
     "other_heater":False,"sensor_device":"independent_device","samples":0}
model.specs=lambda _manager:(spec,)
model.settings=lambda _manager,_spec:cfg
model.targets=lambda *_args:{"heat":20.0}
model.plan_for=lambda *_args:{}
model.room_config=lambda *_args:{}
model.permission=lambda *_args:(env["permission"],env["permission"])
model.sources_available=lambda *_args:env["source_available"]
room_sources.room_temperature_evidence=lambda *_args,**_kw:(
    env["temp"],{"status":"ready","partial":False,"valid_count":1,
                  "entity_ids":["sensor.room_temperature"]})
runtime_module.room_temperature_evidence=room_sources.room_temperature_evidence
discovery.entity_area=lambda _hass,_entity:"living"
state=SimpleNamespace(state="off",entity_id=cap.primary,attributes={},name="Generic heater",
    context=SimpleNamespace(user_id=None,parent_id=None),
    last_updated=SimpleNamespace(timestamp=lambda:150.0))
states=SimpleNamespace(get=lambda entity:state if entity==cap.primary else None,
    async_all=lambda _domain:(
        [SimpleNamespace(entity_id="climate.other",
          state="heat" if env["other_heater"] else "off",
          attributes={"hvac_modes":["off","heat"]})]
        if env["other_heater"] else []))
hass=SimpleNamespace(states=states)
manager=SimpleNamespace(hass=hass,settings={"temperature_entity":"sensor.room_temperature"},
    entry=SimpleNamespace(entry_id="fake"))
ledger={"entity":cap.primary,"area":spec.area_id,"source_device_id":spec.source_device_id,
        "off_since":100.0,"attempts":0,"last_attempt_at":None,"notified":False}
record={"area":spec.area_id,"sources":list(spec.source_entities),
        "source_device_id":spec.source_device_id,"baseline":{},"power":{},
        "off_at":{},"thermal_off_watch":ledger}
records={spec.identifier:record}
messages=[]
commands=[]
persisted=[]

async def save():
    persisted.append((env["time"],ledger["attempts"],ledger.get("notified"),
                      ledger.get("exhausted_notified")))

async def send(_spec,_cap,entity,service,data,expected,**kwargs):
    assert entity==cap.primary
    assert service=="set_hvac_mode" and data=={"hvac_mode":"off"}
    assert expected=={"state":"off"}
    assert kwargs.get("off_state_recovery") is True
    assert kwargs.get("automatic") is False and kwargs.get("power") is True
    assert state.state=="off", "reported OFF must not be treated as physical OFF confirmation"
    commands.append((env["time"],dict(kwargs)))
    return True

async def notify(_runtime,_spec,kind,evidence):
    messages.append((env["time"],kind,evidence))

runtime=SimpleNamespace(hass=hass,manager=manager,clock=lambda:env["time"],
    records=records,_record=lambda _spec:record,_active=True,_ready=True,
    _thermal_off_sessions={},_save=save,_send=send,
    _native_settle_remaining=lambda _spec:0,
    _current_spec=lambda _spec:True,_identity_ok=lambda _spec:True,
    _gate=lambda *_a,**_kw:None)
runtime_module._notify=notify

homeassistant=ModuleType("homeassistant");homeassistant.__path__=[]
helpers=ModuleType("homeassistant.helpers");helpers.__path__=[]
entity_registry=ModuleType("homeassistant.helpers.entity_registry")
entity_registry.async_get=lambda _hass:SimpleNamespace(async_get=lambda _id:
    SimpleNamespace(device_id=env["sensor_device"]))
sys.modules["homeassistant"]=homeassistant
sys.modules["homeassistant.helpers"]=helpers
sys.modules["homeassistant.helpers.entity_registry"]=entity_registry


async def tick(now,temp):
    env["time"]=float(now);env["temp"]=temp
    return await runtime_module.watchdog_tick(runtime,spec,cap,state)


async def main():
    for now,temp in [(100,20.0),(1600,21.8),(1900,21.0),
                      (2140,21.3),(2380,21.6),(2620,22.1)]:
        assert not await tick(now,temp)
    assert not commands and not messages
    assert await tick(2860,22.6)
    assert len(commands)==1 and ledger["attempts"]==1
    assert [kind for _,kind,_ in messages]==["suspected"]
    assert record["thermal_off_warning"]["physical_output_confirmed"] is False
    assert record["thermal_off_warning"]["native_state"]=="off"
    assert not await tick(2980,22.8)
    assert len(commands)==1
    assert await tick(3460,23.3)
    assert len(commands)==2 and ledger["attempts"]==2
    assert not await tick(4060,23.8)
    assert len(commands)==2
    assert [kind for _,kind,_ in messages]==["suspected","exhausted"]
    # Any activity without renewed HEM-owned OFF must not reset two attempts.
    runtime._thermal_off_sessions.clear()
    assert not await tick(5000,24.2)
    assert len(commands)==2
    assert persisted and all(item[1]<=2 for item in persisted)
    from types import SimpleNamespace as NS
    percent = NS(domain="number")
    zero = NS(state="0",attributes={"unit_of_measurement":"%","min":0,"max":100})
    assert runtime_module._reported_off(percent,zero)
    assert not runtime_module._reported_off(percent,NS(state="5",
        attributes=zero.attributes))
    assert not runtime_module._reported_off(percent,NS(state="0",
        attributes={"unit_of_measurement":"°C","min":0,"max":100}))
    # Explicit manual / no permission / unavailable / foreign ownership blocks
    # even when a completely fresh, qualifying temperature trend is present.
    for reason in ("manual","not_commissioned","unavailable","different_identity",
                   "other_heater","sensor_on_heater"):
        ledger.update(attempts=0,last_attempt_at=None,notified=False,
                      exhausted_notified=False,off_since=100.0)
        record.pop("thermal_off_warning",None)
        runtime._thermal_off_sessions.clear()
        env.update(permission=True,source_available=True,other_heater=False,
                   sensor_device="independent_device")
        cfg["control_mode"]="pid";runtime._current_spec=lambda _spec:True
        if reason=="manual":cfg["control_mode"]="manual"
        if reason=="not_commissioned":env["permission"]=False
        if reason=="unavailable":env["source_available"]=False
        if reason=="different_identity":runtime._current_spec=lambda _spec:False
        if reason=="other_heater":env["other_heater"]=True
        if reason=="sensor_on_heater":env["sensor_device"]="zigbee_device"
        start=len(commands)
        for now,temp in [(1900,21.0),(2200,21.5),(2500,22.2),(2800,23.0)]:
            await tick(now,temp)
        assert len(commands)==start,f"unsafe OFF repeat with {reason}"
        runtime._current_spec=lambda _spec:True
    print("B21_GENERIC_HEM_OFF_MONITOR_GUARDED_REPEAT_NOTICES_AND_PERSISTED_BUDGET=PASS")


asyncio.run(main())
