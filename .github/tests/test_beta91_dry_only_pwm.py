"""Beta91: real managed PID tick with ONLY native DRY/OFF; small safe pulses.

The production EquipmentRuntime.tick(), PID calculations, phase_decision(),
binary PWM planner and physical minimum-ON/OFF simulator are executed.
It never makes Home Assistant API calls or powers a real device.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import runpy
from types import SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
baseline=runpy.run_path(str(ROOT/'.github/tests/test_beta70_pid_profile.py'))
Harness, tick, model, settings, spec = (
    baseline[key] for key in ('Harness','tick','model','settings','spec')
)
pwm=runpy.run_path(str(ROOT/'pid_phase.py'))
cycle=pwm['safe_binary_pwm_cycle']
decision=pwm['binary_pwm_off_phase']

@dataclass(frozen=True)
class DryCap:
    primary: str='climate.wohnzimmer'
    domain: str='climate'
    modes: tuple=('off','dry')
    temperature: bool=False
    humidity: bool=True
    humidifying: bool=False
    fan_entity: str|None=None
    fan_modes: tuple=()
    fan_percentage: bool=False

# An actual DRY-only climate must never inherit heat/cool capability from
# a temperature value present in its generic device attributes.
dry=DryCap()
model.capabilities=lambda manager,endpoint:dry
model.targets=lambda manager,endpoint,cap,cfg,plan: {
    'heat':18.,'cool':28.,'humidity':60.,
}
model.timing=lambda manager,endpoint,cap:(600.,600.,7200.)

class DryHarness(Harness):
    def __init__(self,demand_humidity=62.,off_age=1500):
        super().__init__(off_age=off_age)
        self.manager.settings={**settings,
            'control_mode':'pid','requested_mode':'dry',
            'kp':10.,'ki':0.,'kd':0.,
            'cycle_seconds':1200.,'sample_seconds':300.,
        }
        self.plan={'away':'home','occupancy':'occupied'}
        self.humidity=demand_humidity
        self._clock_observations=[]
        self._native_events=[]
    def measurements(self,endpoint,cap):
        return {'temperature':19.8,'humidity':self.humidity,
                'co2':None,'pm25':None}
    async def _power(self,endpoint,cap,desired,**kwargs):
        assert desired in cap.modes,('unsupported physical command',desired,cap.modes)
        # Same physical minimum-OFF and minimum-ON guards as the native
        # controller; the tick never earns authority to bypass them.
        now=self.now
        if desired=='dry' and self.state.state=='off':
            if now-self._last_physical_off<600:
                self._status(endpoint,'minimum_off_hold')
                return False
            self._native_events.append((now,'dry'))
            self.state.state='dry'
            self._physical_on_at=now
        elif desired=='off' and self.state.state!='off':
            if now-getattr(self,'_physical_on_at',now)<600:
                self._status(endpoint,'minimum_on_hold')
                return False
            self._native_events.append((now,'off'))
            self.state.state='off'
            self._last_physical_off=now
        return True
    async def _native_target(self,*args):
        self._clock_observations.append(('target',self.now,args[2]))
        return False
    async def _fan(self,*args):
        return False

async def simulate():
    # A dehumidifier with 62% RH, 60% goal, 20% PID demand and short cycle
    # used to have a 240s pulse < minimum ON 600s and could NEVER start.
    r=DryHarness(62.)
    assert cycle(20.,1200.,600.,600.)==3600.
    assert decision(20.,0.,1200.,600.,600.,starting=True)['state']=='on_window'
    await tick(r,spec)
    assert [mode for _,mode in r._native_events]==['dry'],r._native_events
    assert r.state.state=='dry'
    assert not any(mode in ('heat','cool','auto') for _,mode in r._native_events)
    assert r._memory[spec.identifier][1].demand==20.
    # Sampled within native minimum ON: must NOT issue a second physical write.
    r.now+=300
    await tick(r,spec)
    assert [mode for _,mode in r._native_events]==['dry']
    # After the full 20% pulse and 600s minimum ON, a scheduled OFF is safe.
    r.now+=600
    await tick(r,spec)
    assert [mode for _,mode in r._native_events]==['dry','off'],r._native_events
    # The physical minimum OFF remains an absolute guard.
    r.now+=300
    await tick(r,spec)
    assert r.state.state=='off'
    # Long-period low demand is binned into a full minimum-ON pulse instead
    # of being discarded entirely. No unsupported thermal mode exists.
    low=DryHarness(60.8)
    assert cycle(8.,1200.,600.,600.)==8400.
    await tick(low,spec)
    assert low._native_events==[(low.now,'dry')],low._native_events
    low.now+=900
    await tick(low,spec)
    assert low._native_events[-1][1]=='off'
    low.now+=300
    await tick(low,spec)
    assert low.state.state=='off'
    # No demand: should never request DRY. Below one safe pulse per 24h:
    # intentionally no ON event rather than an unsafe short compressor run.
    zero=DryHarness(60.)
    await tick(zero,spec)
    assert not zero._native_events,zero._native_events
    assert cycle(0.,1200.,600.,600.) is None
    assert cycle(0.1,1200.,600.,600.) is None
    # Unqualified/missing measured humidity must never lead to an ON.
    missing=DryHarness()
    missing.humidity=None
    await tick(missing,spec)
    assert not missing._native_events
    assert missing.status[0]=='control_measurement_missing_or_stale'
    # Physical minimum OFF takes precedence even for a newly scheduled
    # full compressor pulse, with no guessed output state.
    short=DryHarness(63.,off_age=120)
    await tick(short,spec)
    assert short.state.state=='off'
    assert not short._native_events
    assert short.status[0]=='minimum_off_hold'
    assert all(event[1] in ('dry','off') for machine in (r,low,zero,missing,short)
               for event in machine._native_events)
    print('BETA91_DRY_ONLY_PID_TRUE_NATIVE_MODES_SAFE_ACCUMULATED_PWM=PASS')

asyncio.run(simulate())
