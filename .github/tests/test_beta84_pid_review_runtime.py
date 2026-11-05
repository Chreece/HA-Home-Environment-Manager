"""Beta84 real runtime approval guard and one-time review decisions.

Runs the unchanged production methods using an isolated HA-compatible fixture.
No physical HA services, relays or devices are touched.
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS

ROOT=Path(__file__).resolve().parents[2]
package=ModuleType("hem_beta84_runtime")
package.__path__=[str(ROOT)]
sys.modules[package.__name__]=package
for name in ("pid_calibration","pid_passive","pid_review"):
    item=importlib.util.spec_from_file_location(package.__name__+"."+name,ROOT/(name+".py"))
    module=importlib.util.module_from_spec(item)
    sys.modules[item.name]=module
    item.loader.exec_module(module)
passive=sys.modules[package.__name__+".pid_passive"]
helper=sys.modules[package.__name__+".pid_review"]

# Safe native OFF helper is the real code, not a permissive stub.
tree=ast.parse((ROOT/"equipment_power_switch.py").read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
        and n.name=="observed_output_off")
offns={"Mapping":Mapping,"finite":lambda v,a,b: float(v) if isinstance(v,(int,float,str)) and a<=float(v)<=b else None,
       "_IDLE_HVAC_ACTIONS":frozenset(("off","idle"))}
exec(compile(ast.Module(body=[fn],type_ignores=[]),"equipment_power_switch.py","exec"),offns)
power=ModuleType(package.__name__+".equipment_power_switch")
power.observed_output_off=offns["observed_output_off"]
sys.modules[power.__name__]=power

tree=ast.parse((ROOT/"equipment_runtime.py").read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="EquipmentRuntime")
methods=[n for n in cls.body
         if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
         and n.name in ("_pid_review_authorized","async_review_pid")]
assert {n.name for n in methods}=={"_pid_review_authorized","async_review_pid"}
now=2_000_000.
cfg={"control_mode":"pid","pid_calibration_method":"adaptive_suggest",
     "requested_mode":"heat","kp":20.,"ki":.2,"kd":3.}
spec=NS(identifier="controller1",area_id="bathroom",
        source_entities=("climate.a",),name="Heating")
cap=NS(primary="climate.a",domain="climate")
native=NS(state="off",domain="climate",attributes={
    "hvac_action":"idle","fan_mode":None,"percentage":None,
})
states={"climate.a":native}
ctx=passive.identity(spec.area_id,list(spec.source_entities),cap.primary,
                     "heat","temperature","sensor.room","home",21.,None,None)
token="a"*32
review={
    "state":"pending","id":token,"context":ctx,
    "created_at":now-100, "cycle_at":now-200,
    "current":{"kp":20.,"ki":.2,"kd":3.},
    "apply":{"kp":22.,"ki":.22,"kd":3.},
    "recommended":{"kp":80.,"ki":1.,"kd":0.},
    "confidence":"medium","valid_cycles":3,
}
record={
    "pid_passive_review":review,"power":{}, "pending":None,
    "upstream":{"pending":None},
    "pid_passive":{
        "context":ctx, "cycles":[{"at":now-200} for _ in range(3)],
        "summary":{"last_cycle_at":now-200,"status":"suggestion_only",
                   "confidence":"medium"},
    }
}
model=NS(settings=lambda manager,spec:cfg,
         capabilities=lambda manager,spec:cap,
         targets=lambda *a,**kw:{"heat":21.,"cool":26.,"humidity":50.},
         plan_for=lambda *args:{},
         permission=lambda *args:(True,True),
         profile_name=lambda *args:"home")
clock=[now]
ns={
    "__name__":package.__name__+".equipment_runtime",
    "__package__":package.__name__,
    "model":model,"STARTUP_SECONDS":300,
    "passive_identity":passive.identity,
    "finite":lambda x,lo,hi:float(x) if isinstance(x,(float,int)) and lo<=x<=hi else None,
    "HomeAssistantError":RuntimeError,
    "asyncio":asyncio,
    "_LOGGER":NS(debug=lambda *a,**kw:None),
}
exec(compile(ast.Module(body=methods,type_ignores=[]),"equipment_runtime.py","exec"),ns)
guard=ns["_pid_review_authorized"]
changes={
    "kp":22.,"ki":.22,"kd":3.,
    "pid_last_calibration":{
        "method":"passive_approved_imc_lambda","proposal_id":token,
        "cycle_at":now-200,"previous_gains":review["current"],
    },
}
notifications=[]
class Fixture:
    _active=True
    _ready=True
    _started=now-600
    def __init__(self):
        self.manager=NS()
        self.records={spec.identifier:record}
        self.hass=NS(states=NS(get=lambda id:states.get(id)))
        self._lock_obj=asyncio.Lock()
        self._presentation_updates=NS(request=lambda id:notifications.append(("update",id)))
        self.saves=0
        self.config_changes=[]
    def clock(self):return clock[0]
    def _current_spec(self,sp):return True
    def _gate(self,*args,**kwargs):return None
    def measurements(self,*args):return {"temperature":20.,"temperature_selected_entities":["sensor.room"]}
    def _record(self,sp):return record
    def _lock(self,key):return self._lock_obj
    async def _save(self):self.saves+=1
    async def async_update(self,sp,new,**kwargs):
        if not guard(self,sp,new,kwargs["passive_review"]):
            raise RuntimeError("unsafe")
        self.config_changes.append(new)
        cfg.update((key,new[key]) for key in ("kp","ki","kd"))
runtime=Fixture()

assert guard(runtime,spec,changes,token)
native.attributes["hvac_action"]="drying"
assert not guard(runtime,spec,changes,token)
native.attributes["hvac_action"]="idle"
native.state="heat"
assert not guard(runtime,spec,changes,token)
native.state="off"
model.targets=lambda *args,**kw:{"heat":24.,"cool":26.,"humidity":50.}
assert not guard(runtime,spec,changes,token)
model.targets=lambda *args,**kw:{"heat":21.,"cool":26.,"humidity":50.}
cfg["pid_calibration_method"]="cohen_coon"
assert not guard(runtime,spec,changes,token)
cfg["pid_calibration_method"]="adaptive_suggest"
record["power"]={"climate.a":{"since":clock[0]-100}}
assert not guard(runtime,spec,changes,token)
record["power"]={}
record["pending"]={"desired":"on"}
assert not guard(runtime,spec,changes,token)
record["pending"]=None
assert not guard(runtime,spec,changes,"f"*32)
clock[0]=now+49*3600
assert not guard(runtime,spec,changes,token)
clock[0]=now
assert guard(runtime,spec,changes,token)

async def no_service_clear(hass,manager,sp):
    notifications.append(("cleared",sp.identifier))
helper.async_clear_review=no_service_clear

async def tests():
    action=ns["async_review_pid"]
    assert not await action(runtime,spec,"approve",token="f"*32)
    assert not runtime.config_changes
    assert await action(runtime,spec,"discard",token=token)
    assert record["pid_passive_review"]["state"]=="discarded"
    assert not await action(runtime,spec,"discard",token=token)
    assert not await action(runtime,spec,"approve",token=token)
    # A new cycle produces a new immutable token; the old event is stale.
    record["pid_passive_review"]={**review,"state":"pending","id":"b"*32}
    changes["pid_last_calibration"]["proposal_id"]="b"*32
    assert not await action(runtime,spec,"approve",token=token)
    assert await action(runtime,spec,"approve",token="b"*32)
    assert record["pid_passive_review"]["state"]=="applied"
    assert cfg["kp"]==22. and abs(cfg["ki"]-.22)<1e-8
    assert len(runtime.config_changes)==1
    assert not await action(runtime,spec,"approve",token="b"*32)

asyncio.run(tests())
print("BETA84_REAL_PID_APPROVAL_GUARD_REJECT_CONTEXT_REPLAY_DISCARD=PASS")
