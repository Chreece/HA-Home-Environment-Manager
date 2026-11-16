"""B23: persisted derived surface-RH history is source-faithful and bounded.

Load the actual EnvironmentHistory.mold_trend implementation, without HA.
The fake samples represent persisted Store snapshots, not fabricated sensors.
"""
from __future__ import annotations

import ast
import math
from pathlib import Path
from types import SimpleNamespace as N

SOURCE = Path(__file__).resolve().parents[2] / "custom_components/environment_manager/environment_history.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EnvironmentHistory")
method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "mold_trend")
standalone = ast.fix_missing_locations(ast.Module(
    body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
          method], type_ignores=[],
))
ns = {"math": math, "DAY_S": 86400}
exec(compile(standalone, str(SOURCE), "exec"), ns)
calculate = ns["mold_trend"]

NOW = 1794200000.0


def read(samples, *, area="living", limit=96):
    room = N(samples=lambda id: samples if id == area else [])
    return calculate(room, area, now=NOW, limit=limit)

# A stored estimate remains associated with its original time and calibration.
rows = [{"t": NOW - 1200, "surface_rh": 61.25},
        {"t": NOW - 900, "surface_rh": 61.25},
        {"t": NOW - 600},  # Real missing/uncalibrated observation
        {"t": NOW - 300, "surface_rh": 64.5},
        {"t": NOW, "surface_rh": 65.75}]
assert read(rows) == [
    {"t": NOW - 1200, "v": 61.25},
    {"t": NOW - 900, "v": 61.25},
    {"t": NOW - 300, "v": 64.5, "break_before": True},
    {"t": NOW, "v": 65.75},
]
assert read(rows, area="another") == []
assert read([{"t": NOW - 4000, "surface_rh": 45}, {"t": NOW, "surface_rh": 50}]) == [
    {"t": NOW - 4000, "v": 45},
    {"t": NOW, "v": 50, "break_before": True},
]

bad = [{"t": NOW - 900, "surface_rh": math.nan},
       {"t": NOW - 600, "surface_rh": 999},
       {"t": NOW - 300, "surface_rh": -1}]
assert read(bad) == [], "Invalid values became historical measurements"
assert read([{"t": NOW - 8 * 86400, "surface_rh": 33}]) == []
assert read(rows, limit=1) == []

many = [{"t": NOW - 1800 * (359 - i), "surface_rh": float(40 + i % 20)}
        for i in range(360)]
retained = read(many)
assert 2 <= len(retained) <= 96, len(retained)
assert retained[0]["t"] == many[0]["t"]
assert retained[-1]["t"] == many[-1]["t"]
assert all(a["t"] < b["t"] for a,b in zip(retained, retained[1:]))
assert all(p["v"] in {item["surface_rh"] for item in many} for p in retained)
assert not any("source_id" in p for p in retained)
print("PASS: real bounded mold-history method preserves values, gaps and chronological Store evidence")
