"""Regression: HA carbon_dioxide and eCO₂ source discovery, display and safety.

No HA services/network. Execute production classifier and dashboard serializer
without a live Home Assistant instance. eCO₂ remains informational rather
than silently masquerading as measured CO₂ or a ventilation actuator input.
"""
from __future__ import annotations
import ast
import importlib
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace as N

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
# Import the pure production modules without starting the HA integration.
package=ModuleType("hem_eco2_classification")
package.__path__=[str(SRC)]
sys.modules[package.__name__]=package
logic=importlib.import_module(package.__name__+".logic")
dashboard=importlib.import_module(package.__name__+".dashboard")
limits=importlib.import_module(package.__name__+".const").DEFAULT_THRESHOLDS
shown=dashboard._reading(equiv,None,indoor=True)
assert (shown["metric"],shown["value"],shown["unit"])==("eco2",845.0,"ppm")
assert shown["threshold"] is None and shown["exceeded"] is False

def plan_for(readings, *, opened=False, outdoor_pm25=5.0):
    room=logic.Room("living", "Living room",
                    (logic.Window("binary_sensor.window", "Window", opened),), readings)
    return logic.evaluate(
        (logic.Reading("sensor.outdoor_pm25", "Outdoor PM2.5", "pm25", outdoor_pm25),),
        (logic.Weather("weather.home", "sunny", 20.0, 50.0, 1.0),), (), (room,))

basics=(logic.Reading("sensor.temperature", "Temperature", "temperature", 21.0),
        logic.Reading("sensor.humidity", "Humidity", "humidity", 50.0))
for value in (None, 845.0, 25000.0):
    estimate=logic.Reading(equiv.entity_id, equiv.name, "eco2", value)
    # A visible estimate cannot supply either missing basic measurement or
    # suppress the no-indoor-data diagnostic used by ventilation decisions.
    plan=plan_for((estimate,))
    room=dashboard.dashboard_snapshot(plan, limits)["rooms"][0]
    assert room["status"]=="unknown", (value, room)
    assert room["data_availability"]["status"]=="missing"
    assert room["data_availability"]["missing_basic_metrics"]==["temperature", "humidity"]
    assert ("Living room", "no_indoor_data") in plan.diagnostics
    assert not plan.recommendations and plan.outdoor_safe
    assert room["readings"][0]["threshold"] is None
    assert room["readings"][0]["exceeded"] is False

    # Missing or extreme eCO2 remains optional when real basics are present.
    plan=plan_for(basics+(estimate,))
    room=dashboard.dashboard_snapshot(plan, limits)["rooms"][0]
    assert room["status"]=="safe" and room["data_availability"]["status"]=="ready"
    assert not plan.recommendations and not plan.diagnostics
    # An actual extraction controller still requires measured CO2 feedback.
    inputs={"living": [{"controller_id": "fan.extract", "name": "Extractor",
                        "metrics": ["co2"], "missing_metrics": ["co2"]}]}
    room=dashboard.dashboard_snapshot(plan, limits, control_inputs=inputs)["rooms"][0]
    assert room["status"]=="unknown"
    assert room["data_availability"]["missing_required_metrics"]==["co2"]

    # Real measured CO2 still requests airing; eCO2 neither creates nor
    # cancels that demand, and cannot override an outdoor pollution hazard.
    high_co2=logic.Reading(real.entity_id, real.name, "co2", limits["indoor_co2"]+500)
    plan=plan_for(basics+(estimate, high_co2))
    assert len(plan.recommendations)==1 and plan.recommendations[0].action=="open"
    assert {reason.code for reason in plan.recommendations[0].reasons}=={"inside_co2"}
    assert dashboard.dashboard_snapshot(plan, limits)["rooms"][0]["status"]=="attention"
    plan=plan_for(basics+(estimate, high_co2), opened=True, outdoor_pm25=100.0)
    assert not plan.outdoor_safe
    assert len(plan.recommendations)==1 and plan.recommendations[0].action=="close"
    assert {reason.code for reason in plan.recommendations[0].reasons}=={"outside_pm25"}

sources=(SRC/"room_sources.py").read_text(encoding="utf-8")
assert 'metric_ids("co2")' in sources  # never pin an eCO₂ estimate as native CO₂
card=(SRC/"frontend/air-quality-advisor-card.js").read_text(encoding="utf-8")
assert "eCO₂ (estimated)" in card and "eCO₂ (εκτίμηση)" in card
assert "eCO₂ ist eine Schätzung" in card
print("PASS: carbon_dioxide ppm recognized; eCO2 visible informational only; no CO2 control or false room-safe evidence")
