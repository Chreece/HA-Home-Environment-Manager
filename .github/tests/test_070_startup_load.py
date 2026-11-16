"""v0.7.0: coalesced HA STARTING updates and cheap shade-only clock ticks.

Load the shipped manager callbacks, not replacements. No physical writes.
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
import sys
import time
from types import ModuleType, SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2]
PKG = ModuleType("hem070"); PKG.__path__ = []; sys.modules[PKG.__name__] = PKG
sources = ModuleType("hem070.room_sources")
sources.native = lambda hass, eid: eid == "sensor.native"
sources.selected = lambda config, area, name: ("cover.test",) if name == "shades" else ()
sys.modules[sources.__name__] = sources
shading = ModuleType("hem070.shade_cooling")
shading.cover_config = lambda config, area, cover: {"enabled": True}
sys.modules[shading.__name__] = shading
scope = {"__name__": "hem070.manager", "__package__": "hem070",
         "callback": lambda fn: fn, "Event": object, "time": time.time,
         "CONF_AREAS": "areas",
         "claimed_sources": lambda m: m.settings.get("_claimed", False),
         "equipment_legacy_settings": lambda m: (m.settings.get("_legacy", {}), {})}
tree = ast.parse((ROOT / "custom_components/environment_manager/manager.py").read_text())
klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AirQualityManager")
names = ("_queue_source_refresh", "_flush_source_refresh", "_on_state_changed",
         "_on_fast_climate_interval")
methods = [n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name in names]
assert {n.name for n in methods} == set(names)
exec(compile(ast.Module(body=methods, type_ignores=[]), "manager.py", "exec"), scope)


class Manager:
    pass


for name in names:
    setattr(Manager, name, scope[name])


async def verify():
    m = Manager()
    loop = asyncio.get_running_loop()
    m._active = True
    m._source_refresh_handle = None
    m._startup_refresh_pending = False
    m._tracked = {"sensor.native"}
    m.hass = NS(loop=loop, state=NS(value="STARTING"))
    recalc, checked, faults, arrivals, shades = [], [], [], [], []
    m._recalculate = lambda: recalc.append(time.monotonic())
    m.faults = NS(state_changed=lambda eid: faults.append(eid))
    m.equipment = NS(observe_native_availability=lambda *args: checked.append(args))
    m.arrival_preparation = NS(observe_current=lambda: arrivals.append(True))
    m.settings = {"areas": ["room"], "_claimed": False, "_legacy": {}}
    m.shading = NS(schedule=lambda: shades.append(True))
    m.plan = NS(environment={})
    for n in range(20):
        m._on_state_changed(NS(data={"entity_id": "sensor.native",
                             "old_state": NS(state=str(n), attributes={}),
                             "new_state": NS(state=str(n+1), attributes={})}))
        await asyncio.sleep(0)  # 20 separate loop turns while HA starts
    assert len(checked) == 20 and len(faults) == 20 and len(arrivals) == 20
    assert not recalc and m._startup_refresh_pending, "Startup source burst built the whole home"
    await asyncio.sleep(0.85)
    assert len(recalc) == 1 and not m._startup_refresh_pending, len(recalc)
    m.hass.state = NS(value="RUNNING")
    for n in range(40):
        m._on_state_changed(NS(data={"entity_id": "sensor.native",
                             "old_state": NS(state=str(n), attributes={}),
                             "new_state": NS(state=str(n+1), attributes={})}))
    await asyncio.sleep(0)
    assert len(recalc) == 2, "Running HA must retain immediate native-source refresh"
    m.hass.state = NS(value="STARTING")
    m._queue_source_refresh()
    assert m._startup_refresh_pending
    m.hass.state = NS(value="RUNNING")
    m._queue_source_refresh()  # Escalate the stale startup deadline.
    await asyncio.sleep(0)
    assert len(recalc) == 3 and not m._startup_refresh_pending
    m._on_fast_climate_interval(None)
    assert len(shades) == 1 and len(recalc) == 3, "Shade-only fast tick rebuilt indoor science"
    m.settings["_claimed"] = True
    m._on_fast_climate_interval(None)
    assert len(recalc) == 4, "Safety-sensitive per-device fast tick was skipped"
    m.settings["_claimed"] = False
    m.settings["_legacy"] = {"room": {"enabled": True}}
    m._on_fast_climate_interval(None)
    assert len(recalc) == 5, "Mixed legacy and shade controllers were skipped"
    m._active = False
    m._queue_source_refresh()
    await asyncio.sleep(0)
    assert len(recalc) == 5
    print("PASS 0.7 startup: 20 cross-turn source changes -> 1 rebuild; live evidence immediate; shade-only 30s tick bypasses full science; device safety unchanged")


asyncio.run(verify())
