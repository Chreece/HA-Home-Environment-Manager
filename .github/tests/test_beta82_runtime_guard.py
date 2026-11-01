"""Beta82: exercise the real production passive auto-gain safety gate.

No Home Assistant import, hardware service or physical device is required.
The actual _pid_passive_auto_authorized() method is AST-compiled unchanged.
"""
from __future__ import annotations
import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
pkg=ModuleType("hem_pid_runtime_test")
pkg.__path__=[str(ROOT)]
sys.modules[pkg.__name__]=pkg
for name in ("pid_calibration","pid_passive"):
    spec=importlib.util.spec_from_file_location(pkg.__name__+"."+name,ROOT/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
passive=sys.modules[pkg.__name__+".pid_passive"]
tree=ast.parse((ROOT/"equipment_runtime.py").read_text(encoding="utf-8"))
klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="EquipmentRuntime")
method=next(n for n in klass.body if isinstance(n,ast.FunctionDef)
            and n.name=="_pid_passive_auto_authorized")
# The actual function body must remain intact. Annotation names are stubs.
source=compile(ast.Module(body=[method],type_ignores=[]),"equipment_runtime.py","exec")
now=2_000_000.
cfg={"control_mode":"pid","pid_adaptation_mode":"bounded","requested_mode":"heat",
     "kp":20.,"ki":0.2,"kd":0.,"pid_last_calibration":None}
cap=N(primary="climate.unit")
state=N(state="off",attributes={})
record={"pid_passive":{
  "context":"valid-heat-room-controller",
  "cycles":[{"at":now-4000+i*700,"gain":4.,"tau":28.,"dead":10.,"r2":.99}
            for i in range(5)],
  "summary":{"confidence":"high","status":"validated",
             "last_cycle_at":now-120,
             "valid_cycles":5,
             "suggested_gains":{"kp":80.,"ki":1.,"kd":0.},
             "identified_model":{"process_gain":4.,"time_constant_minutes":28.,
                                 "dead_time_minutes":10.}},
}}
native=N(state="off",attributes={})
source_context=record["pid_passive"]["context"]
settings=lambda manager,spec:cfg
state_map={"climate.unit":state}
model=N(settings=settings,capabilities=lambda manager,spec:cap,
        permission=lambda manager,spec,c:(True,True),
        plan_for=lambda manager,spec:{})
ns={
    "model":model,"STARTUP_SECONDS":300,
    "AUTO_INTERVAL_S":passive.AUTO_INTERVAL_S,
    "passive_bounded_gains":passive.bounded_gains,
    "output_off":lambda s:s.state=="off",
}
exec(source,ns)
guard=ns["_pid_passive_auto_authorized"]
class GuardRuntime:
    _active=True
    _ready=True
    _started=now-7200
    records={"unit":record}
    manager=N()
    hass=N(states=N(get=lambda entity:state_map.get(entity)))
    def clock(self):return now
    def _current_spec(self,spec):return True
    def _gate(self,*args,**kwargs):return None
runtime=GuardRuntime()
spec=N(identifier="unit")
proof=(source_context,now-120,{"kp":20.,"ki":0.2,"kd":0.})
candidate={"kp":22.,"ki":0.22,"kd":0.,
           "pid_last_calibration":{"method":"passive_imc_lambda",
                                   "cycle_at":now-120}}
def allowed():return guard(runtime,spec,candidate,proof)
assert allowed(),"valid high-confidence fully-OFF cycle should allow bounded gains"
state.state="heat"
assert not allowed(),"running physical output must block tuning"
state.state="off"
record["pending"]={"command":"on"}
assert not allowed(),"in-flight command must block tuning"
record.pop("pending")
record["power"]={"climate.unit":{"since":now-600}}
assert not allowed(),"owned ON means not physically quiescent"
record["power"]={}
record["paused"]="window"
assert not allowed(),"manual/safety pause must block"
record.pop("paused")
cfg["pid_adaptation_mode"]="observe"
assert not allowed(),"observe-only can never mutate gains"
cfg["pid_adaptation_mode"]="bounded"
cfg["kp"]=25.
assert not allowed(),"concurrent gain change must not be overwritten"
cfg["kp"]=20.
record["pid_passive"]["context"]="moved_sensor"
assert not allowed(),"model must belong to the exact current feedback source"
record["pid_passive"]["context"]=source_context
candidate["ki"]=0.26
assert not allowed(),"more than 10 percent gain adjustment is forbidden"
candidate["ki"]=.22
cfg["pid_last_calibration"]={
  "method":"passive_imc_lambda","at":now-1800,"cycle_at":now-3600}
assert not allowed(),"never repeat a gain change less than 24 h later"
cfg["pid_last_calibration"]["at"]=now-90000
assert (sum(c["at"]>now-3600 for c in record["pid_passive"]["cycles"])>=2)
assert allowed(),"two fresh cycles and one full day allow another bounded update"
record["pid_passive"]["summary"]["confidence"]="medium"
assert not allowed(),"medium confidence is suggestion-only"
record["pid_passive"]["summary"]["confidence"]="high"
# Ensure the runtime applies the guard before and immediately before the
# config-entry write. It may not trust a stale observation across awaits.
source_text=ast.get_source_segment((ROOT/"equipment_runtime.py").read_text(),klass)
update=next(n for n in klass.body if isinstance(n,ast.AsyncFunctionDef)
            and n.name=="async_update")
rechecks=[n for n in ast.walk(update)
          if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
          and n.func.attr=="_pid_passive_auto_authorized"]
assert len(rechecks)==2,"guard must run twice under the controller lock"
observer=next(n for n in klass.body if isinstance(n,ast.AsyncFunctionDef)
              and n.name=="_pid_passive_observe")
assert not any(isinstance(n,ast.Attribute) and n.attr=="async_call"
               for n in ast.walk(observer)),"observer must never call physical services"
print("BETA82_PRODUCTION_OFF_LOCK_AUTHORITY_AND_REPLAY_GUARDS=PASS")
