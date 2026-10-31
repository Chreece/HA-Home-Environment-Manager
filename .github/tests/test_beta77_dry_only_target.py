"""Regression: native DRY/FAN_ONLY must never publish a temperature target.

Runs the actual model.capabilities() extracted with AST; needs no Home Assistant
process, actuators or network. The source is production code, not a copy.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
tree = ast.parse((ROOT / "equipment_model.py").read_text(encoding="utf-8"))
names = {"Capabilities", "_strings", "features", "capabilities"}
functions = [
    item for item in tree.body
    if isinstance(item, (ast.ClassDef, ast.FunctionDef)) and item.name in names
]
assert len(functions) == len(names)
ns = {
    "dataclass": dataclass, "Any": Any, "ManagedDevice": object,
    "HVAC_MODES": frozenset(("off", "heat", "cool", "heat_cool", "auto", "dry", "fan_only")),
    "TEMP": 1, "RANGE": 2, "HUMIDITY": 4, "FAN": 8, "SWING": 32, "SWING_H": 512,
    "configured_sources": lambda settings, area: ("climate.test",),
    "room_config": lambda manager, spec: {},
    "finite": lambda value, lower, upper: (
        float(value) if value is not None and lower <= float(value) <= upper else None
    ),
    "target_from_unit": lambda value, unit: (
        float(value) if value is not None and unit == "°C" else None
    ),
}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(ROOT / "equipment_model.py"), "exec"), ns)

spec = SimpleNamespace(area_id="test", source_entities=("climate.test",))

def cap(modes, bits):
    native = SimpleNamespace(attributes={
        "hvac_modes": modes, "supported_features": bits,
        "temperature_unit": "°C", "min_temp": 5, "max_temp": 35,
        "min_humidity": 20, "max_humidity": 80,
    })
    hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity: native))
    manager = SimpleNamespace(hass=hass, settings={})
    return ns["capabilities"](manager, spec)

for modes, bits in [
    (["off", "dry"], 1 | 4),
    (["off", "dry", "fan_only"], 1 | 2 | 4),
    (["off", "fan_only"], 1),
]:
    c = cap(modes, bits)
    assert not c.temperature and not c.temperature_range, (modes, c)
    assert c.humidity == ("dry" in modes), (modes, c)

for modes, bits in [
    (["off", "heat"], 1),
    (["off", "cool"], 1),
    (["off", "heat_cool"], 2),
    (["off", "auto"], 1),
    (["off", "heat", "dry"], 1 | 4),
]:
    c = cap(modes, bits)
    assert c.temperature or c.temperature_range, (modes, c)

frontend = (ROOT / "frontend/air-quality-advisor-card.js").read_text(encoding="utf-8")
assert "kind==='temperature' && !thermalModes" in frontend
assert "thermalTarget && numeric(a.temperature)" in frontend
assert "thermalTarget && numeric(a.target_temp_low)" in frontend
print("BETA77_DRY_ONLY_CAPABILITIES_AND_FRONTEND_GATES=PASS")
