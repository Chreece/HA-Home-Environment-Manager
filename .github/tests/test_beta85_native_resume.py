"""Beta85 actual Resume: safe interrupted native-command verification.

Uses production EquipmentRuntime.async_resume unmodified with the established
Beta72 physical-state fixture. All HA service actions are disabled in fixture.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta72_resume_running.py'))
Runtime=base["Runtime"]
spec=base["spec"]
state=base["state"]
NOW=base["NOW"]
HomeAssistantError=base["HomeAssistantError"]

def pending(*, phase="intent", requested="heat", when=NOW-400,
            powered=True, expected=None):
    return {
        "phase": phase, "entity": "climate.heater",
        "service": "set_hvac_mode",
        "expected": expected or {"state": requested},
        "when": when, "power": powered, "output_on": requested!="off",
        "min_on": 600, "max_on": 7200,
    }

async def expect_hold(runtime, snippet):
    before=deepcopy(runtime.record["pending"])
    try:
        await runtime.async_resume(spec)
    except HomeAssistantError as exc:
        message=str(exc)
        assert snippet in message,(snippet,message)
        assert "Check" in message or "native command" in message or "device" in message,message
    else:
        raise AssertionError("Unsafe pending native command incorrectly resumed")
    assert runtime.calls==[],runtime.calls
    assert runtime.record["pending"]==before
    return message

async def tests():
    # The user's exact stuck condition: persisted intent, HA now reports
    # the requested HEAT, and an independent state update followed dispatch.
    auto=Runtime(prior_owned=True)
    auto.record["paused"]="native_command_failed_or_uncertain"
    auto.record["pending"]=pending()
    auto.states["climate.heater"]=state("heat", changed=NOW-220)
    prior=auto.record["power"]["climate.heater"]["since"]
    await auto.async_resume(spec)
    assert auto.record["pending"] is None
    assert auto.record["paused"] is None
    assert auto.record["power"]["climate.heater"]["since"]>=prior
    # Intent ON changed during an uncertain async service: do not shorten the
    # device's safety minimum ON from a timestamp that might predate the call.
    assert auto.record["power"]["climate.heater"]["since"]==NOW
    assert auto.record["last_resume_reconciliation"]["method"]=="fresh_native_ack"
    assert auto.calls==[] and auto.scheduled==1

    # An intent that matches but was NOT freshly reported cannot prove that
    # HA ever issued it. It needs two deliberate checks, 60 seconds apart.
    stale=Runtime(prior_owned=True)
    stale.record["paused"]="restart_reconciliation_required"
    stale.record["pending"]=pending()
    stale.states["climate.heater"]=state("heat",changed=NOW-900)
    msg=await expect_hold(stale,"60 seconds")
    assert "reports heat" in msg and "climate.heater" in msg
    assert stale.record["pending_resume_probe"]["at"]==NOW
    stale.now=NOW+59
    msg=await expect_hold(stale,"1 seconds")
    stale.now=NOW+60
    await stale.async_resume(spec)
    assert stale.record["pending"] is None
    assert stale.record["last_resume_reconciliation"]["method"]=="two_physical_checks"
    assert stale.calls==[]

    # An old failed ON request that never executed is recoverable without
    # turning the appliance OFF/ON, but only after real human verification.
    mismatched=Runtime(native="off")
    mismatched.states["climate.heater"].attributes["hvac_action"]="idle"
    mismatched.record["paused"]="native_command_failed_or_uncertain"
    mismatched.record["pending"]=pending()
    await expect_hold(mismatched,"reports off")
    mismatched.now=NOW+60
    await mismatched.async_resume(spec)
    assert mismatched.record["pending"] is None
    assert mismatched.record["off_at"]["climate.heater"]==NOW+60
    assert mismatched.record["power"]=={}
    assert mismatched.record["paused"] is None
    assert mismatched.calls==[]

    # A changed native output during the verification minute must restart
    # the interval; no stale proof or one-click bypass.
    changed=Runtime(native="off")
    changed.states["climate.heater"].attributes["hvac_action"]="idle"
    changed.record["paused"]="restart_reconciliation_required"
    changed.record["pending"]=pending(requested="cool")
    await expect_hold(changed,"60 seconds")
    changed.now=NOW+40
    changed.states["climate.heater"]=state("heat",changed=NOW+40)
    await expect_hold(changed,"60 seconds")
    assert changed.record["pending_resume_probe"]["at"]==NOW+40
    changed.now=NOW+99
    await expect_hold(changed,"1 seconds")
    changed.now=NOW+100
    await changed.async_resume(spec)
    assert changed.record["power"]["climate.heater"]["since"]==NOW+100
    assert changed.calls==[]

    # In-flight native call still inside its settle window cannot be cleared
    # even when its observed mode appears to match the requested mode.
    early=Runtime()
    early.record["paused"]="native_command_failed_or_uncertain"
    early.record["pending"]=pending(when=NOW-30)
    early.states["climate.heater"]=state("heat",changed=NOW-1)
    await expect_hold(early,"90 seconds")
    assert "pending_resume_probe" not in early.record
    early.now=NOW+90
    await early.async_resume(spec)
    assert early.record["pending"] is None

    # A contradictory OFF/hvac_action=heating is not safe OFF.
    contradictory=Runtime(native="off")
    contradictory.states["climate.heater"].attributes["hvac_action"]="idle"
    contradictory.record["paused"]="native_command_failed_or_uncertain"
    contradictory.record["pending"]=pending()
    await expect_hold(contradictory,"60 seconds")
    contradictory.states["climate.heater"].attributes["hvac_action"]="heating"
    contradictory.now=NOW+65
    await expect_hold(contradictory,"unavailable or reports contradictory")
    assert contradictory.record["pending"] is not None

    # No timestamp / unexpected source / unexpected phase must never erase
    # the original journal or synthesize ownership.
    missing=Runtime(prior_owned=True)
    missing.record["pending"]=pending()
    missing.record["pending"].pop("when")
    await expect_hold(missing,"interrupted native command")
    wrong=Runtime(prior_owned=True)
    wrong.record["pending"]=pending()
    wrong.record["pending"]["entity"]="climate.other_device"
    await expect_hold(wrong,"original device")
    phase=Runtime(prior_owned=True)
    phase.record["pending"]=pending(phase="mystery")
    await expect_hold(phase,"interrupted native command")

    # No Resume attempt may send a physical Home Assistant service.
    for r in (auto,stale,mismatched,changed,early,contradictory,missing,wrong,phase):
        assert not r.calls

    print("BETA85_SAFE_INTERRUPTED_NATIVE_RESUME=PASS")

asyncio.run(tests())
