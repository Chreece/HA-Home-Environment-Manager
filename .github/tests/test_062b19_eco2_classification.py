"""Regression: HA carbon_dioxide and eCO₂ source discovery, display and safety.

No HA services/network. Execute production classifier and dashboard serializer
without a live Home Assistant instance. eCO₂ remains informational rather
than silently masquerading as measured CO₂ or a ventilation actuator input.
"""
from __future__ import annotations
import ast
from pathlib import Path
import re
from types import SimpleNamespace as N

SRC=Path(__file__).resolve().parents[2]/"custom_components/environment_manager"
source=(SRC/"discovery.py").read_text(encoding="utf-8")
tree=ast.parse(source)
assign={"DEVICE_CLASS_METRICS","SUFFIX_METRICS","ECO2_HINT"}
funcs={"_metric","_numeric","_normalize","supported_metric","reading"}
nodes=[node for node in tree.body if
    isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in node.targets)
    or isinstance(node,ast.FunctionDef) and node.name in funcs]
assert len(nodes)==len(assign)+len(funcs),[getattr(n,"name",None) for n in nodes]
from types import SimpleNamespace
scope={
    "re":re,
    "INDOOR_METRICS":("co2","eco2","humidity","pm25"),
    "SUPPORTED_AIR_METRICS":("co2","pm25"),
    "is_pressure_sensor":lambda *_:False,
    "_device_class":lambda _,state:state.attributes.get("device_class",""),
    "is_stale":lambda *_:False,
    "Reading":lambda eid,name,metric,value:N(entity_id=eid,name=name,metric=metric,
                                              value=value,details=None),
}
exec(compile(ast.Module(body=nodes,type_ignores=[]),"discovery.py","exec"),scope)
def state(entity,name,value,device_class="carbon_dioxide",unit="ppm"):
    return N(entity_id=entity,domain="sensor",name=name,state=value,
             attributes={"device_class":device_class,"unit_of_measurement":unit,
                         "state_class":"measurement"})

estimated=state("sensor.living_room_environmental_sensors_eco2",
    "Living Room Environmental Sensors eCO2","845")
measured=state("sensor.living_room_actual_carbon_dioxide","Living room NDIR CO2", "895")
assert scope["supported_metric"](None,estimated,outdoor=False)=="eco2"
assert scope["supported_metric"](None,estimated,outdoor=True) is None
assert scope["supported_metric"](None,measured,outdoor=False)=="co2"
equiv=scope["reading"](N(states=N(get=lambda eid:estimated)),estimated.entity_id,90,outdoor=False)
real=scope["reading"](N(states=N(get=lambda eid:measured)),measured.entity_id,90,outdoor=False)
assert (equiv.metric,equiv.value)==("eco2",845.0)
assert (real.metric,real.value)==("co2",895.0)
assert scope["supported_metric"](None,state("sensor.bad_eco2","eCO2","500",unit="µg/m³"),
                                   outdoor=False) is None
assert scope["reading"](N(states=N(get=lambda eid:state("sensor.foo_eco2","eCO2","unavailable"))),
                        "sensor.foo_eco2",90,outdoor=False).value is None
plain=state("sensor.classless_eco2","CO₂ equivalent",650,device_class="")
assert scope["supported_metric"](None,plain,outdoor=False)=="eco2"

# Neither the real CO2 measurement nor its eCO2 estimate may be conflated.
assert equiv.metric!=real.metric
dashboard=(SRC/"dashboard.py").read_text(encoding="utf-8")
mod=ast.parse(dashboard)
serialize=next(node for node in mod.body if isinstance(node,ast.FunctionDef) and node.name=="_reading")
namespace={"UNIT_LABEL":{"co2":"ppm","eco2":"ppm"}}
exec(compile(ast.Module(body=[serialize],type_ignores=[]),"dashboard.py","exec"),namespace)
shown=namespace["_reading"](equiv,None,indoor=True)
assert (shown["metric"],shown["value"],shown["unit"])==("eco2",845.0,"ppm")
assert shown["threshold"] is None and shown["exceeded"] is False
assert "if item[\"metric\"] not in (\"illuminance\", \"eco2\")" in dashboard
logic=(SRC/"logic.py").read_text(encoding="utf-8")
assert 'reading.metric not in ("illuminance", "eco2")' in logic
sources=(SRC/"room_sources.py").read_text(encoding="utf-8")
assert 'metric_ids("co2")' in sources  # never pin an eCO₂ estimate as native CO₂
card=(SRC/"frontend/air-quality-advisor-card.js").read_text(encoding="utf-8")
assert "eCO₂ (estimated)" in card and "eCO₂ (εκτίμηση)" in card
assert "eCO₂ ist eine Schätzung" in card
print("PASS: carbon_dioxide ppm recognized; eCO2 visible informational only; no CO2 control or false room-safe evidence")
