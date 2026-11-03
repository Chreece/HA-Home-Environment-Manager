"""Beta100: binary PID drives native temperature only after an ACKed ON.

Test the actual production _native_target through the inherited Beta88
harness: no service call to an OFF native climate, extrema only after ON.
"""
from __future__ import annotations
import asyncio
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
runtime=(ROOT/"equipment_runtime.py").read_text()
card=(ROOT/"frontend/air-quality-advisor-card.js").read_text()
fixture=runpy.run_path(str(ROOT/".github/tests/test_beta88_power_startup_and_retries.py"))
SimRuntime,SPEC=fixture["SimRuntime"],fixture["SPEC"]

async def run():
    for mode,expected in (("heat",30.0),("cool",10.0)):
        controlled=SimRuntime("off")
        controlled.now=5000.
        # Native set_temperature may auto-start hardware; it is forbidden
        # until the native mode is already positively observed ON.
        assert not await controlled._native_target(
            SPEC,controlled.manager.cap,mode,
            {"heat":19.,"cool":26.},None,True)
        assert controlled.calls==[]
        controlled.state.state=mode
        assert await controlled._native_target(
            SPEC,controlled.manager.cap,mode,
            {"heat":19.,"cool":26.},None,True)
        assert controlled.calls[-1][2]=={"temperature":expected}
asyncio.run(run())

assert 'and (config["control_mode"] == "pid" or' in runtime
assert 'def _pid_extreme_native_target(' not in runtime
assert 'if state is None or state.state == "off":' in runtime
assert runtime.index('await self._power(spec, cap, desired, automatic=True)') < (
    runtime.index('if await self._native_target(spec, cap, mode, target,'))
assert 'NATIVE_STARTUP_STABLE_SECONDS = 60' in runtime
assert 'NATIVE_RECONNECT_SETTLE_SECONDS = 30' in runtime
start=card.index("proto65._deviceSummary65 = function(entry)")
end=card.index("proto65._calibrationDetails65",start)
summary=card[start:end]
assert "this._hass?.states?.[nativeId]" in summary
assert "add(t.demand" not in summary
assert "a.measurements?.humidity" not in summary
assert "d.demand_percent" not in summary
assert "attrs.current_humidity" in summary
assert "attrs.current_temperature" in summary
assert "native.state" in summary
assert "grid-template-columns:repeat(3,minmax(0,1fr))" in card
assert "const actualMode=observedNative" in card
assert "dehumidifying:t.dry" in card
assert "el:{heating:'Θερμαίνει',cooling:'Ψύχει',drying:'Αφυγραίνει'" in card
assert "['heating','cooling','drying','dehumidifying','fan','fan_only','humidifying']" in card
assert "HEM_COMPACT87_START" in card
assert "_recoverUnexpectedScroll92" in card
print("BETA100_NATIVE_ON_FIRST_EXTREMES_AND_NATIVE_ONLY_TELEMETRY=PASS")
