"""Beta100: native PID binary setpoint and physical-only source regression."""
from __future__ import annotations

import ast
import math
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
runtime = (ROOT / "equipment_runtime.py").read_text()
card = (ROOT / "frontend/air-quality-advisor-card.js").read_text()
tree = ast.parse(runtime)
methods = [
    item for cls in tree.body if isinstance(cls, ast.ClassDef)
    for item in cls.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
]
helper = next(x for x in methods if x.name == "_pid_extreme_native_target")
namespace = {}
class FakeModel:
    TEMP = 1
    @staticmethod
    def settings(manager, spec):
        return manager.settings
    @staticmethod
    def permission(manager, spec, cap):
        return (True, manager.power_granted)
    @staticmethod
    def features(state):
        return 1
    @staticmethod
    def device_limits(manager, spec, cap):
        return manager.limits
namespace.update(model=FakeModel, Any=object,
    target_to_unit=lambda n, unit: n if unit in ("°C", "C") else None,
    finite=lambda v, low, high: (float(v) if isinstance(v, (int, float))
                                and math.isfinite(v) and low <= v <= high else None),
    quantize_target=lambda v, step, low, high: max(
        low, min(high, round(float(v) / float(step)) * float(step)))
)
module = ast.Module(
    body=[ast.ImportFrom(module="__future__",
                         names=[ast.alias(name="annotations")], level=0), helper],
    type_ignores=[]
)
ast.fix_missing_locations(module)
exec(compile(module, "equipment_runtime.py:pid_native", "exec"), namespace)
fn = namespace["_pid_extreme_native_target"]
manager = SimpleNamespace(
    settings={"control_mode": "pid"}, power_granted=True,
    limits={"temperature_min_limit": 16, "temperature_max_limit": 32})
observed = SimpleNamespace(attributes={
    "temperature_unit": "°C", "min_temp": 5, "max_temp": 30,
    "target_temp_step": .5, "temperature": 21})
controller = SimpleNamespace(manager=manager, _status=lambda *args, **kw: None)
cap = SimpleNamespace(domain="climate", temperature=True)
assert fn(controller, None, cap, observed, "heat") == 30
assert fn(controller, None, cap, observed, "cool") == 16
assert fn(controller, None, cap, observed, "dry") is None
manager.power_granted = False
assert fn(controller, None, cap, observed, "heat") is None
manager.power_granted = True
manager.settings["control_mode"] = "automatic"
assert fn(controller, None, cap, observed, "heat") is None
manager.settings["control_mode"] = "pid"
observed.attributes.pop("max_temp")
assert fn(controller, None, cap, observed, "heat") is None

# Request and verify the physical thermostat setpoint before native ON.
assert runtime.index("# Set the native thermostat to the verified extreme BEFORE") < (
    runtime.index("await self._power(spec, cap, desired, automatic=True)"))
assert 'and (config["control_mode"] == "pid" or' in runtime
assert "NATIVE_STARTUP_STABLE_SECONDS = 60" in runtime
assert "NATIVE_RECONNECT_SETTLE_SECONDS = 30" in runtime
assert "def _pid_extreme_native_target" in runtime
# Live HEM room metrics and PID duty cannot masquerade as physical telemetry.
start = card.index("proto65._deviceSummary65 = function(entry)")
end = card.index("proto65._calibrationDetails65", start)
summary = card[start:end]
assert "this._hass?.states?.[nativeId]" in summary
assert "add(t.demand" not in summary
assert "a.measurements?.humidity" not in summary
assert "d.demand_percent" not in summary
assert "attrs.current_humidity" in summary
assert "attrs.current_temperature" in summary
assert "native.state" in summary
assert "grid-template-columns:repeat(3,minmax(0,1fr))" in card
assert "const actualMode=observedNative" in card
assert "HEM_COMPACT87_START" in card
assert "_recoverUnexpectedScroll92" in card
print("BETA100_NATIVE_PID_EXTREMES_AND_NATIVE_ONLY_COMPACT_TELEMETRY=PASS")
