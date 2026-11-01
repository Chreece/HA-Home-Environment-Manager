"""Deterministic, no-hardware passive PID identification and safety regression."""
import asyncio
import importlib.util
import math
import sys
from pathlib import Path
from types import ModuleType

ROOT=Path(__file__).resolve().parents[2]
pkg=ModuleType("hem_passive_test");pkg.__path__=[str(ROOT)]
sys.modules[pkg.__name__]=pkg
for name in ("pid_calibration","pid_passive"):
    spec=importlib.util.spec_from_file_location(
        pkg.__name__+"."+name,ROOT/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
passive=sys.modules["hem_passive_test.pid_passive"]

def wave(metric="temperature", direction=1, cycle_count=5):
    p=passive.PassiveObserver()
    context=passive.identity("controller","room",["climate.a"],"heat" if direction>0 else "cool",
                             metric,"sensor.room", "home",21.0)
    t=1730000000.
    gain=4. if metric=="temperature" else 15.
    start=20. if metric=="temperature" else 60.
    for k in range(cycle_count):
        for n in range(6):
            p.observe(context=context,at=t,value=start,on=False,owned=False,
                metric=metric,sample_seconds=300,safe=True)
            t+=300
        for n in range(42):
            dt=n*5.
            response=gain*(1-math.exp(-max(0,dt-10)/28))
            p.observe(context=context,at=t,value=start+direction*response,
                on=True,owned=True,metric=metric,sample_seconds=300,safe=True)
            t+=300
        accepted=p.observe(context=context,at=t,value=start+direction*gain,
            on=False,owned=False,metric=metric,sample_seconds=300,safe=True)
        assert accepted,(k,p.ledger())
        t+=300
    result=p.summary(metric=metric,sample_seconds=300)
    return p, result,t,context

p,r,t,context=wave()
assert r["status"]=="validated",r
assert r["confidence"]=="high" and r["valid_cycles"]==5,r
assert 3.6<r["identified_model"]["process_gain"]<4.4,r
assert "suggested_gains" in r and r["suggested_gains"]["kd"]==0,r
assert all(math.isfinite(v) for v in r["suggested_gains"].values())
assert len(str(p.ledger()))<1300
# Stored cycles survive restart, but no in-flight ON period is restored.
restored=passive.PassiveObserver(p.ledger())
assert not restored.on and restored.last_on is None
assert restored.summary(metric="temperature",sample_seconds=300)["valid_cycles"]==5
# The same sensor and device in opposite direction is a distinct plant.
restored.observe(context=context+"cool",at=t,value=20.,on=False,owned=False,
                 metric="temperature",sample_seconds=300,safe=True)
assert not restored.cycles
# No learning from unowned or interrupted runs, or from unknown sensors.
a=passive.PassiveObserver()
ctx=passive.identity("no-owner","heat")
for n in range(8):
    a.observe(context=ctx,at=t+n*300,value=20.,on=False,owned=False,
              metric="temperature",sample_seconds=300,safe=True)
for n in range(35):
    a.observe(context=ctx,at=t+(8+n)*300,value=20.+n*.1,on=True,owned=False,
              metric="temperature",sample_seconds=300,safe=True)
assert not a.cycles
a.observe(context=ctx,at=t+44*300,value=None,on=False,owned=False,
          metric="temperature",sample_seconds=300,safe=False)
assert not a.cycles and not a.on
# No false inference from a ramp without plateau, regardless of duration.
assert passive._fit_episode(
    [(i*300.,20.+i*.1) for i in range(35)],20.,1,"temperature") is None
# UI selection is explicit and automatic updates are capped, never actuating.
assert passive.MODES==("disabled","observe","bounded")
bounded=passive.bounded_gains({"kp":20.,"ki":0.2,"kd":3.},
                             {"kp":80.,"ki":1.,"kd":0.})
assert bounded["kp"]==22. and abs(bounded["ki"]-0.22)<1e-6,bounded
assert bounded["kd"]==3.
assert passive.bounded_gains({"kp":-1.,"ki":0.,"kd":0.},
                             {"kp":80.,"ki":1.}) is None
# Humidity decreasing for the ON phase identifies a separate drying plant.
humid, result,_,_=wave("humidity",direction=-1)
assert result["confidence"]=="high",result
print("BETA82_PASSIVE_IDENTIFICATION_CONFIDENCE_AND_BOUNDED_GAINS=PASS")
