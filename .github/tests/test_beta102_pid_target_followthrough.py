"""Beta102: live binary PID follow-through for antifrost native setpoints.

Uses the production EquipmentRuntime.tick extracted by Beta70's real PID
harness. Exercises an acknowledged HEM-owned HEAT/COOL output which is still
at 4-5°C during a mandatory minimum-ON interval. No real HA service calls.
"""
from __future__ import annotations
import asyncio
import runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta70_pid_profile.py'))
Harness,tick,model,spec,Cap=(base[k] for k in
    ('Harness','tick','model','spec','Cap'))
source=(ROOT/'equipment_runtime.py').read_text()
assert 'HEM_B102_NATIVE_PID_FOLLOWTHROUGH' in source
assert source.index('HEM_B102_NATIVE_PID_FOLLOWTHROUGH') < (
    source.index('await self._power(spec, cap, desired, automatic=True)'))
assert source.index('if why := self._gate(spec, cap, cfg, plan, mode') < (
    source.index('HEM_B102_NATIVE_PID_FOLLOWTHROUGH'))
assert source.index('if self._stop_policy_verified(spec, cap, "sleep")') < (
    source.index('HEM_B102_NATIVE_PID_FOLLOWTHROUGH'))
assert source.index('if cfg.get("pause_on_window_open", False)') < (
    source.index('HEM_B102_NATIVE_PID_FOLLOWTHROUGH'))

class NativeHarness(Harness):
    def __init__(self, *, mode='heat', temperature=18.6,
                 owned=True, age=100, selected='pid'):
        super().__init__()
        self.manager.settings['control_mode']=selected
        self.manager.settings['requested_mode']=mode
        self.plan={'away':'home','occupancy':'occupied'}
        self.measurement=temperature
        self.state.state=mode
        self.state.attributes.update({
            'hvac_action':'heating' if mode=='heat' else 'cooling',
            'temperature':5.0 if mode=='heat' else 35.0,
            'min_temp':4.0,'max_temp':35.0,'target_temp_step':.5,
            'supported_features':1,'temperature_unit':'°C'})
        self._native_writes=[]
        self._power_requests=[]
        if owned:
            self.records['power'][Cap().primary]={
                'since':self.now-age,'min_on':600.,'max_on':7200.}
    async def _native_target(self, endpoint, cap, mode, targets, demand, automatic):
        assert automatic is True and demand is None
        assert self.state.state==mode  # NEVER set the thermostat while OFF
        bound=self.state.attributes['max_temp' if mode=='heat' else 'min_temp']
        if self.state.attributes['temperature']==bound:return False
        self._native_writes.append((mode,bound))
        self.state.attributes['temperature']=bound
        return True
    async def _power(self, endpoint, cap, desired, **kwargs):
        self._power_requests.append(desired)
        return False
    def _window_policy(self,*args):
        return {'blocked':True,'stop_requested':True,
                'status':'window_open_pause','remaining_seconds':0}

async def scenarios():
    original_duty=model.duty_on
    original_cap=model.capabilities
    # Force the PWM duty into an OFF phase, even though a previous ON must
    # finish its minimum-ON dwell. The old code returned at _power(off)
    # leaving the actual heating thermostat at 5°C.
    model.duty_on=lambda *args,**kwargs:False
    try:
        heat=NativeHarness()
        await tick(heat,spec)
        assert heat._native_writes==[('heat',35.0)],(
            'OWNED_HEAT_NATIVE_5C_NEVER_RAISED',heat._native_writes,heat._power_requests)
        assert heat._power_requests==[],heat._power_requests
        # Once the real hardware target is correct, allow the original PWM
        # OFF request to proceed under its unchanged minimum-ON safety.
        await tick(heat,spec)
        assert heat._native_writes==[('heat',35.0)]
        assert heat._power_requests==['off'],heat._power_requests
        # An expired minimum ON must take the permitted OFF, not write a
        # fresh full-heat setpoint and postpone stopping a heater.
        expired=NativeHarness(age=900)
        await tick(expired,spec)
        assert expired._native_writes==[],expired._native_writes
        assert expired._power_requests==['off'],expired._power_requests
        # A mode-armed but unowned thermostat can NEVER be adopted silently.
        foreign=NativeHarness(owned=False)
        await tick(foreign,spec)
        assert not foreign._native_writes and not foreign._power_requests
        assert foreign.status[0]=='running_device_requires_off_before_automatic_power_ownership'
        # Room goal already met: don't force a native heating/cooling extreme.
        satisfied=NativeHarness(temperature=23.0)
        await tick(satisfied,spec)
        assert not satisfied._native_writes
        # Active window safety: request the original guarded OFF, never a
        # new maximum-heat setpoint, even while the minimum ON is pending.
        window=NativeHarness()
        window.manager.settings['pause_on_window_open']=True
        await tick(window,spec)
        assert window._native_writes==[],window._native_writes
        assert window._power_requests==['off'],window._power_requests
        # Cooling must correct to the reported native minimum (4°C), not
        # the room soft target or a hard-coded device-specific temperature.
        model.capabilities=lambda manager,endpoint:Cap(modes=('off','cool'))
        cool=NativeHarness(mode='cool',temperature=30.0)
        await tick(cool,spec)
        assert cool._native_writes==[('cool',4.0)],cool._native_writes
    finally:
        model.duty_on=original_duty
        model.capabilities=original_cap
    # Native source is physically OFF: no temperature write may bypass the
    # source-bound minimum OFF protection or cause an implicit startup.
    off=NativeHarness(owned=False)
    off.state.state='off'
    await tick(off,spec)
    assert not off._native_writes
    # No PID method selected: do not impose binary PID targets.
    old=NativeHarness(selected='existing')
    await tick(old,spec)
    assert not old._native_writes
asyncio.run(scenarios())
print('BETA102_NATIVE_HEAT_MAX_COOL_MIN_AFTER_ACK_AND_SAFE_PID_HOLD=PASS')
