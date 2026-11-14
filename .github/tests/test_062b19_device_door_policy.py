"""B19 exact per-device door policy, safe legacy migration and bounded starts.

No Home Assistant instance is touched. Reuse the door coordination fixtures to
exercise the real runtime gate with mocked native states and explicit ownership.
"""
from __future__ import annotations
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"custom_components/environment_manager"
fixture=runpy.run_path(str(ROOT/".github/tests/test_062b5_door_coordination.py"),
                       run_name="hem_b19_imported_fixture")
Engine=fixture["EngineTests"]
pkg="hem_b5_fixture"
case=Engine("test_observe_is_noop_and_shared_requires_verified_active_peer")
case.setUp()
# Engine.setUp installs its isolated equipment_model/door_settings stubs.
policy=fixture["load"]("equipment_door_policy")
model=sys.modules[pkg+".equipment_model"]

def room_config(manager,spec):
    return manager.settings["climate_rooms"].get(spec.area_id,{})
model.room_config=room_config
door_settings=sys.modules[pkg+".door_settings"]
door_settings.editable_contact=lambda hass,settings,area,entity: (
    entity in settings.get("climate_rooms",{}).get(area,{}).get("door_sensors",[]) and
    case.areas.get(entity)==area and
    case.states.get(entity) is not None and
    case.states[entity].attributes.get("device_class")=="door"
)
assert policy.configured(case.manager,case.local)
assert not policy.configured(case.manager,case.peer)
assert not policy.configured(case.manager,SimpleNamespace(area_id="outside"))

# Newly installed settings inherit the old room-owned Eco without changing it.
case.settings["climate_rooms"]["a"]["closed_door_eco"]=True
assert policy.effective_eco(case.manager,case.local,{}) is True
assert policy.effective_eco(case.manager,case.local,{"door_closed_eco":False}) is False
assert policy.effective_eco(case.manager,case.local,{"door_closed_eco":True}) is True
case.settings["climate_rooms"]["a"]["closed_door_eco"]=False
assert policy.effective_eco(case.manager,case.local,{}) is False
assert policy.effective_coordination({})=="inherit"
assert policy.effective_coordination({"door_start_coordination":"shared"})=="shared"
assert policy.effective_coordination({"door_start_coordination":"bogus"})=="observe"

# A per-controller explicit coordination choice overrides the old door policy
# only for this controller and only across a verified OPEN interior connection.
legacy=case.settings["climate_rooms"]["a"]["door_settings"]["binary_sensor.door"]
legacy["coordination"]="observe"
case.cfg["door_start_coordination"]="shared"
assert case.call() is not None
case.runtime._door_start_budget=fixture["coord"].StartBudget()
case.cfg["door_start_coordination"]="observe"
legacy["coordination"]="shared"
assert case.call() is None

# A missing or moved door blocks the override even if a saved selection persists.
case.cfg["door_start_coordination"]="shared"
case.runtime._door_start_budget=fixture["coord"].StartBudget()
case.settings["climate_rooms"]["a"]["door_sensors"]=[]
assert not policy.configured(case.manager,case.local)
assert case.call() is None
case.settings["climate_rooms"]["a"]["door_sensors"]=["binary_sensor.door"]
case.areas["binary_sensor.door"]="b"
assert not policy.configured(case.manager,case.local)
assert case.call() is None
case.areas["binary_sensor.door"]="a"
case.states["binary_sensor.door"].state="off"
assert case.call() is None, "A closed door must never create an open-door start hold"
case.states["binary_sensor.door"].state="on"
case.states["binary_sensor.door"].attributes["restored"]=True
assert case.call() is None, "Restored door state must not authorize coordination"

# Source policies only contain registry / configuration operations, no direct
# control of an actuator or a physical switch at any point in the update path.
runtime=(SRC/"equipment_runtime.py").read_text(encoding="utf-8")
model_src=(SRC/"equipment_model.py").read_text(encoding="utf-8")
assert 'if set(changes) & {"door_closed_eco", "door_start_coordination"}:' in runtime
branch=runtime.split('if set(changes) & {"door_closed_eco", "door_start_coordination"}:',1)[1]
branch=branch.split('if "off_state_watchdog_mode" in changes:',1)[0]
assert "async_update_entry" in branch
assert "async_apply" not in branch and "call_service" not in branch
assert 'cfg.get("door_closed_eco") is True' in model_src
assert '"closed_door_eco": cfg.get("door_closed_eco") is True' in model_src

print("PASS: exact per-device door authority, inherited Eco, controller override, no-door/no-window actuation and live closed-door safety")
