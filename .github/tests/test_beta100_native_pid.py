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
    for mode,expected in (("heat",35.0),("cool",5.0)):
        controlled=SimRuntime("off")
        controlled.now=5000.
        # Native set_temperature may auto-start hardware; it is forbidden
        # until the native mode is already positively observed ON.
        assert not await controlled._native_target(
            SPEC,controlled.manager.cap,mode,
            {"heat":19.,"cool":26.},None,True)
        assert controlled.calls==[]
        controlled.state=fixture["State"](mode,changed=controlled.now)
        # The observed native ON starts the required grace. Neither the
        # ACK itself nor a poll just before 30 seconds may write a target.
        assert not await controlled._native_target(
            SPEC,controlled.manager.cap,mode,
            {"heat":19.,"cool":26.},None,True)
        assert controlled.calls==[]
        assert controlled.statuses[-1][0]=='native_setpoint_startup_grace'
        controlled.now+=29.999
        assert not await controlled._native_target(
            SPEC,controlled.manager.cap,mode,
            {"heat":19.,"cool":26.},None,True)
        assert controlled.calls==[]
        controlled.now=5030.
        assert await controlled._native_target(
            SPEC,controlled.manager.cap,mode,
            {"heat":19.,"cool":26.},None,True)
        assert controlled.calls[-1][2]=={"temperature":expected}
asyncio.run(run())

# The room's comfortable 10–30°C software limits are deliberately irrelevant
# to the binary actuator's physical 5–35°C operating extrema.
# Additional native limits and temperature units work without per-device rules.
async def reported_limits():
    controller=SimRuntime("heat")
    controller.now=5000.
    controller.state.attributes.update(
        min_temp=13.0,max_temp=27.5,target_temp_step=.5,temperature=19.0)
    assert await controller._native_target(
        SPEC,controller.manager.cap,"heat",
        {"heat":20.,"cool":24.},None,True)
    assert controller.calls[-1][2]=={"temperature":27.5}
    controller=SimRuntime("cool")
    controller.now=5000.
    controller.state.attributes.update(
        min_temp=13.0,max_temp=27.5,target_temp_step=.5,temperature=19.0)
    assert await controller._native_target(
        SPEC,controller.manager.cap,"cool",
        {"heat":20.,"cool":24.},None,True)
    assert controller.calls[-1][2]=={"temperature":13.0}
    controller=SimRuntime("heat")
    controller.now=5000.
    controller.state.attributes.update(
        temperature_unit="°F",min_temp=45.0,max_temp=95.0,
        target_temp_step=1.0,temperature=70.0)
    assert await controller._native_target(
        SPEC,controller.manager.cap,"heat",
        {"heat":20.,"cool":24.},None,True)
    assert controller.calls[-1][2]=={"temperature":95.0}
    # Do not guess a missing native bound. Unit/step metadata is optional
    # for copying the exact reported endpoint through HA's service API.
    for key in ("min_temp","max_temp"):
        controller=SimRuntime("heat")
        controller.now=5000.
        controller.state.attributes.pop(key,None)
        assert not await controller._native_target(
            SPEC,controller.manager.cap,"heat",
            {"heat":19.,"cool":26.},None,True)
        assert controller.calls==[]
asyncio.run(reported_limits())

assert 'def _pid_extreme_native_target(' not in runtime
assert 'if state is None or state.state == "off":' in runtime
assert runtime.index('await self._power(spec, cap, desired, automatic=True)') < (
    runtime.index('if (await self._native_target(spec, cap, mode, target,'))
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
print("BETA100_NATIVE_ON_THEN_30S_EXTREMES_AND_NATIVE_ONLY_TELEMETRY=PASS")
