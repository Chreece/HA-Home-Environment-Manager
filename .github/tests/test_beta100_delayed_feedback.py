"""Beta100 feedback latency: native OFF is not a manual override or quick retry.

Tests the real pure production decision helper and source-bound safeguards.
Nothing here sends HA services.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'equipment_runtime.py').read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body
          if isinstance(n, ast.FunctionDef) and n.name == 'native_retry_decision')
scope = {
    'finite': lambda v, lo, hi: float(v) if isinstance(v, (int, float))
              and lo <= v <= hi else None,
    'NATIVE_COMMAND_MAX_ATTEMPTS': 4,
    'NATIVE_RECONNECT_EXTRA_ATTEMPTS': 2,
    'NATIVE_COMMAND_RETRY_SECONDS': 30,
    'NATIVE_OFF_FEEDBACK_GRACE_SECONDS': 60,
}
ast.fix_missing_locations(fn)
exec(compile(ast.Module(body=[fn],type_ignores=[]),
             'equipment_runtime.py:native_retry_decision', 'exec'), scope)
decision = scope['native_retry_decision']
pending = dict(phase='commanded', attempts=1, when=1000.,
               last_attempt_at=1000., power=True,
               expected={'state':'off'}, service='set_hvac_mode')
stale = SimpleNamespace(
    last_updated=datetime.fromtimestamp(990., timezone.utc),
    last_reported=None, last_changed=None)
fresh = SimpleNamespace(
    last_updated=datetime.fromtimestamp(990., timezone.utc),
    last_reported=datetime.fromtimestamp(1020., timezone.utc),
    last_changed=None)
assert decision(pending, 1030., stale) == 'waiting'
# Safety-critical OFF remains on the original 30-second retry cadence.
urgent = {**pending, 'retry_context':{'policy_stop':'window','shutdown':False}}
assert decision(urgent, 1030., stale) == 'retry'
shutdown = {**pending, 'retry_context':{'policy_stop':None,'shutdown':True}}
assert decision(shutdown, 1030., stale) == 'retry'
assert decision(pending, 1059., stale) == 'waiting'
assert decision(pending, 1060., stale) == 'retry'
# Once HA has actually reported the same still-ON state, allow the original
# rate-limited retry. This is NOT an ACK, as _reconcile must compare first.
assert decision(pending, 1030., fresh) == 'retry'
power_on = {**pending,'expected':{'state':'heat'}}
assert decision(power_on, 1030., stale) == 'retry'
setpoint = {**pending,'power':False, 'expected':{'attributes':{'temperature':30}}}
assert decision(setpoint, 1030., stale) == 'retry'
exhausted = {**pending,'attempts':4}
assert decision(exhausted, 1030., stale) == 'waiting'
assert decision(exhausted, 1060., stale) == 'exhausted'
assert 'if matches(state, pending["expected"]):' in source
assert source.index('if matches(state, pending["expected"]):') < source.index('await self._retry_pending(spec, pending, now)')
assert 'minimum_on_remaining_seconds=' in source
assert 'minimum_on_until=' in source
assert 'minimum_off_until=' in source
assert 'now-stamp < on_min' in source
assert 'NATIVE_STARTUP_STABLE_SECONDS = 60' in source
assert 'NATIVE_RECONNECT_SETTLE_SECONDS = 30' in source
status = (ROOT / 'equipment_status.py').read_text()
assert '"native_minimum_on_until": observed.get("minimum_on_until")' in status
assert '"native_minimum_off_until": observed.get("minimum_off_until")' in status
card = (ROOT / 'frontend/air-quality-advisor-card.js').read_text()
assert "state==='minimum_on_hold'" in card
assert "state==='minimum_off_hold'" in card
assert "const label=this._controllerStatusLabel(state)+untilLabel;" in card
print('BETA100_DELAYED_NATIVE_OFF_AND_MINIMUM_ON_COUNTDOWN=PASS')
