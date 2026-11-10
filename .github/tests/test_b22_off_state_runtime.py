"""Execute the real generic OFF watchdog with fake HA services, not vendor IDs."""
import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS

root=Path(__file__).resolve().parents[2]/"custom_components/environment_manager"
pkg=ModuleType("b22_runtime")
pkg.__path__=[str(root)]
sys.modules[pkg.__name__]=pkg

def module(name, load=False):
    name_full=pkg.__name__+"."+name
    result=ModuleType(name_full)
    result.__package__=pkg.__name__
    sys.modules[name_full]=result
    if load:
        spec=importlib.util.spec_from_file_location(name_full,root/(name+".py"))
        result.__spec__=spec
        spec.loader.exec_module(result)
    return result

model=module("equipment_model")
room=module("room_sources")
discovery=module("discovery")
module("device_faults")
module("languages")
profiles=module("off_state_profiles",True)
module("off_state_watchdog",True)
watchdog=module("off_state_runtime",True)

spec=NS(identifier="generic",area_id="room",source_device_id="physical-device",
        source_entities=("climate.output",),name="Managed output")
config={"control_mode":"pid","announce_device_errors":True}
state=NS(entity_id="climate.output",state="off",attributes={},name="Managed output",
         context=NS(user_id=None,parent_id=None),
         last_updated=NS(timestamp=lambda:120))
env=NS(time=100.,temp=20.,rh=50.,available=True,permission=True,
       external=False,sensor_device="another-device",windows=None)
hass=NS(states=NS())
hass.states.get=lambda e:state if e==spec.source_entities[0] else None
hass.states.async_all=lambda domain:(
    [NS(entity_id="climate.other",state="cool",attributes={"hvac_modes":["off","cool","dry"]})]
    if env.external and domain=="climate" else [])
manager=NS(hass=hass,settings={},entry=NS(entry_id="test"))
cap=NS(primary="climate.output",domain="climate",modes=("off","cool"))
model.specs=lambda _: (spec,)
model.capabilities=lambda *_:cap
model.settings=lambda *_:config
model.targets=lambda *_:{"heat":20., "cool":22., "humidity":50.}
model.plan_for=lambda *_:{}
model.room_config=lambda *_:{}
model.device_config=lambda *_:{}
model.permission=lambda *_:(env.permission,env.permission)
model.sources_available=lambda *_:env.available
room.room_temperature_evidence=lambda *_args,**_kwargs:(
    env.temp,{"status":"ready","partial":False,"valid_count":1,
              "entity_ids":["sensor.room_temp"]})
watchdog.room_temperature_evidence=room.room_temperature_evidence
room.selected=lambda *_args:env.windows if _args[-1]=="windows" else (
    ("sensor.room_rh",) if _args[-1]=="humidity" else None)
room.numeric=lambda *_args:env.rh
room.native=lambda *_args:True
discovery.entity_area=lambda *_:"room"

fakehome=ModuleType("homeassistant");fakehome.__path__=[]
helpers=ModuleType("homeassistant.helpers");helpers.__path__=[]
registry=ModuleType("homeassistant.helpers.entity_registry")
registry.async_get=lambda _hass:NS(async_get=lambda _id:
    NS(device_id=env.sensor_device))
sys.modules["homeassistant"]=fakehome
sys.modules["homeassistant.helpers"]=helpers
sys.modules["homeassistant.helpers.entity_registry"]=registry

commands=[]; alerts=[];saved=[]
records={}
async def store():
    ledger=records["generic"]["thermal_off_watch"]
    saved.append((ledger["attempts"],ledger["last_attempt_at"]))
async def send(_spec,_cap,entity,service,data,expected,**kwargs):
    assert kwargs["off_state_recovery"] is True and kwargs["power"] is True
    assert kwargs["automatic"] is False and kwargs["mode"]=="off"
    assert entity==spec.source_entities[0]
    if cap.domain=="climate":
        assert (service,data,expected)==("set_hvac_mode",{"hvac_mode":"off"},{"state":"off"})
    elif cap.domain=="humidifier":
        assert (service,data,expected)==("turn_off",{},{"state":"off"})
    elif cap.domain=="number":
        assert (service,data,expected)==("set_value",{"value":0.},{"state":"0.0"})
    assert state.state in ("off","0"),"native OFF is not physical ACK"
    commands.append(env.time)
    return True
async def notify(_runtime,_spec,kind,evidence):
    alerts.append((kind,evidence["direction"],evidence["metric"]))
watchdog._notify=notify
runtime=NS(hass=hass,manager=manager,clock=lambda:env.time,records=records,
    _record=lambda _spec:records["generic"],_active=True,_ready=True,
    _thermal_off_sessions={},_save=store,_send=send,
    _native_settle_remaining=lambda *_:0,
    _current_spec=lambda *_:True,_identity_ok=lambda *_:True,
    _gate=lambda *_a,**_kw:None)

async def observe(at,value,effect):
    env.time=at
    if effect in ("heat","cool"):env.temp=value
    else:env.rh=value
    return await watchdog.watchdog_tick(runtime,spec,cap,state)

async def scenario(effect,domain,points, *,external=False, available=True,
                   permission=True,sensor_device="another-device"):
    env.time=100.;env.external=external;env.available=available
    env.permission=permission;env.sensor_device=sensor_device
    env.windows=None
    cap.domain=domain
    cap.modes=("off",effect if effect!="humidify" else "auto")
    cap.humidifying=effect=="humidify"
    state.state="off"
    state.attributes=({"unit_of_measurement":"%","min":0,"max":100} if domain=="number" else {})
    if domain=="number":state.state="0"
    spec.source_entities=(("number.output",) if domain=="number" else
                          ("humidifier.output",) if domain=="humidifier" else ("climate.output",))
    cap.primary=spec.source_entities[0]
    state.entity_id=cap.primary
    ledger={"entity":cap.primary,"area":"room","source_device_id":"physical-device",
            "direction":effect,"off_since":100.,
            "attempts":0,"last_attempt_at":None,"notified":False}
    records["generic"]={"thermal_off_watch":ledger,"power":{},
                        "baseline":{},"off_at":{},"sources":list(spec.source_entities)}
    runtime._thermal_off_sessions={}
    commands.clear();alerts.clear();saved.clear()
    for at,value in points:
        await observe(at,value,effect)
    return ledger

async def main():
    cool=[(1900,23.2),(2140,22.8),(2380,22.4),(2620,21.6),(2860,20.5)]
    rh_up=[(2900,53),(3200,55),(3500,57),(3800,60),(4100,62)]
    rh_down=[(2900,56),(3200,53),(3500,49),(3800,45),(4100,41)]
    await scenario("cool","climate",cool)
    assert len(commands)==1 and alerts==[("suspected","cool","temperature")]
    await scenario("humidify","humidifier",rh_up)
    assert len(commands)==1 and alerts==[("suspected","humidify","humidity")]
    await scenario("dry","humidifier",rh_down)
    assert len(commands)==1 and alerts==[("suspected","dry","humidity")]
    await scenario("dry","climate",rh_down)
    assert len(commands)==1 and alerts==[("suspected","dry","humidity")]
    await scenario("cool","number",cool)
    assert len(commands)==1 and alerts==[("suspected","cool","temperature")]
    for block,kwargs in (
        ("other_cooling",{"external":True}),
        ("unavailable",{"available":False}),
        ("not_commissioned",{"permission":False}),
        ("sensor_on_appliance",{"sensor_device":"physical-device"}),
    ):
        await scenario("cool","climate",cool,**kwargs)
        assert not commands,block
    await scenario("dry","climate",rh_down,external=True)
    assert not commands
    await scenario("dry","humidifier",rh_down)
    ledger=records["generic"]["thermal_off_watch"]
    assert len(commands)==1
    for at,value in [(4700,36),(5300,34),(5900,32)]:
        await observe(at,value,"dry")
    assert len(commands)==2 and ledger["attempts"]==2
    runtime._thermal_off_sessions={}
    for at,value in [(6500,29),(7100,26)]:
        await observe(at,value,"dry")
    assert len(commands)==2 and [a[0] for a in alerts]==["suspected","exhausted"]
    assert saved and max(a for a,_ in saved)<=2
    print("B22_REAL_RUNTIME_COOL_DRY_HUMIDIFY_OFF_ONLY_CONFIDENCE_AND_BUDGET=PASS")

asyncio.run(main())
