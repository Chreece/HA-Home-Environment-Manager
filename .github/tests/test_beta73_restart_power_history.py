"""Beta73 real restart/recovery/ON-observation/power safety regression.

The actual EquipmentRuntime async_start, _verify_restart_power,
_observe_native_running and _power methods execute against isolated
native HA state, durable-Store and service stubs. No real HA commands.
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
from copy import deepcopy
from dataclasses import asdict, dataclass
import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta72_resume_running.py'))
Parent=base['Runtime']
spec=base['spec']
state=base['state']
NOW=base['NOW']
HomeAssistantError=base['HomeAssistantError']
off=base['off']
snap=base['snapshot']
finite=base['finite']
Model=base['Model']


class ExtendedModel(Model):
    TEMP = 1

    @staticmethod
    def features(state):
        return state.attributes.get("supported_features", 0)

    @staticmethod
    def plan_for(manager, spec):
        return manager.plan

    @staticmethod
    def sources_available(manager, spec):
        return all(
            (state := manager.hass.states.get(e)) is not None
            and state.state not in ("unknown","unavailable")
            for e in spec.source_entities
        )


def physical_changes(before, after):
    if before.get('state') != after.get('state'):
        return ('state',)
    for key in ('temperature','humidity','fan_mode','percentage',
                'preset_mode','swing_mode','swing_horizontal_mode'):
        if (key in before.get('attributes',{}) and
                key in after.get('attributes',{}) and
                before['attributes'][key] != after['attributes'][key]):
            return (key,)
    return ()


package = ModuleType('beta73_fixture')
package.__path__=[]
switch = ModuleType('beta73_fixture.equipment_power_switch')
switch.permitted_supply = sys.modules['beta72_fixture.equipment_power_switch'].permitted_supply
sys.modules.update({
 'beta73_fixture':package,
 'beta73_fixture.equipment_power_switch':switch,
})

root=ast.parse((ROOT/'equipment_runtime.py').read_text(encoding='utf-8'))
cls=next(n for n in root.body if isinstance(n,ast.ClassDef) and n.name=='EquipmentRuntime')
methods=('async_start','_verify_restart_power','_observe_native_running','_power')
methods=(*methods, '_send')
nodes=[n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name in methods]
assert {n.name for n in nodes}==set(methods)
helpers=[n for n in root.body if isinstance(n,ast.FunctionDef)
         and n.name in ('native_retry_decision','snapshot','matches',
                        '_manual_output_changes')]
constants=[n for n in root.body if isinstance(n,ast.Assign)
           and any(isinstance(target,ast.Name) and (
               target.id.startswith('NATIVE_')
               or target.id in ('MONITORED','SETTABLE_OUTPUT_ATTRIBUTES'))
               for target in n.targets)]
namespace={
 '__name__':'beta73_fixture.equipment_runtime',
 '__package__':'beta73_fixture',
 'asyncio':asyncio, 'deepcopy':deepcopy,
 'asdict':asdict,
 'HomeAssistantError':HomeAssistantError,
 'model':ExtendedModel, 'snapshot':snap, 'output_off':off,
 'finite':finite, 'matches':base['matches'],
 '_manual_output_changes':physical_changes,
 'foreign_owner_hold':lambda hass,owner,e: hass.manager.foreign_owner,
 'entity_area':lambda hass,entity:spec.area_id,
 'DOMAIN':'environment_manager',
}
exec(compile(ast.Module(body=[*constants,*helpers,*nodes],type_ignores=[]),
             'equipment_runtime.py','exec'),namespace)
sys.modules['beta73_fixture.equipment_model']=ExtendedModel
package.equipment_model=ExtendedModel
runtime_module=ModuleType('beta73_fixture.equipment_runtime')
runtime_module.__dict__.update(namespace)
sys.modules[runtime_module.__name__]=runtime_module
for helper in ('pid_math','equipment_setpoint_sequence','equipment_pid_safety',
               'equipment_native_target'):
    helper_spec=importlib.util.spec_from_file_location(
        f'beta73_fixture.{helper}',ROOT/f'{helper}.py')
    helper_module=importlib.util.module_from_spec(helper_spec)
    sys.modules[helper_spec.name]=helper_module
    helper_spec.loader.exec_module(helper_module)
sequence=sys.modules['beta73_fixture.equipment_setpoint_sequence']


@dataclass(frozen=True)
class Capabilities:
    primary: str='climate.heater'
    domain: str='climate'
    modes: tuple=('off','heat','cool')
    temperature: bool=True
    humidity: bool=False

storage = ModuleType('homeassistant.helpers.storage')
class Store:
    def __init__(self,hass,version,key):
        self.hass=hass
    async def async_load(self):
        return deepcopy(self.hass.manager.original_store)
storage.Store=Store
ha=ModuleType('homeassistant')
ha.__path__=[]
helpers=ModuleType('homeassistant.helpers')
helpers.__path__=[]
sys.modules.update({
    'homeassistant':ha,'homeassistant.helpers':helpers,
    'homeassistant.helpers.storage':storage,
})


class Controller(Parent):
    async def async_start(self):
        await namespace['async_start'](self)
        # Real async_start restores records from the durable Store and swaps
        # the dictionary. Keep the simulator's convenience alias in sync.
        self.record = self.records[spec.identifier]
    _verify_restart_power=namespace['_verify_restart_power']
    _observe_native_running=namespace['_observe_native_running']
    _power=namespace['_power']
    def __init__(self,*,owned=True,known_since=NOW-750,
                 native='heat', native_report_age=20,
                 previous_pause=None, pending=None,
                 supply=None, supply_owned=False):
        super().__init__(native=native,supply=supply,
                         prior_owned=owned,supply_owned=supply_owned)
        self.states['climate.heater']=state(
            native, changed=NOW-native_report_age
        ) if native is not None else None
        if native is None:
            self.states.pop('climate.heater',None)
        self.record['paused']=previous_pause
        self.record['pending']=deepcopy(pending)
        if owned:
            self.record['power']['climate.heater']['since']=known_since
        self.record['baseline']={
            'climate.heater':snap(state('heat',changed=NOW-1500))
        }
        self.records={spec.identifier:self.record}
        self.manager.original_store={'version':1,'records':deepcopy(self.records)}
        self.manager.settings[Model.SETTINGS][spec.identifier]["timed_setpoint_sequence"]=True
        self.manager.native_permission=True
        self.manager.source_valid=True
        self.manager.cap=Capabilities()
        self.manager.plan={}
        if self.states.get('climate.heater') is not None:
            self.states['climate.heater'].attributes.update(
                temperature=21., min_temp=5., max_temp=35.,
                supported_features=1)
        self.status=None
        self.actual_commands=[]
        self._store=None
        self._ready=False
        self._started=NOW-800
        self._profile_wake={}
        self._pid_offline_previews={}
        self._fan_allocations={}
        self._saved=[]
        self._commands=asyncio.Semaphore(1)
        self._invalidated=set()
        async def service_call(*args,**kwargs):
            # Transport accepts the payload; feedback stays unchanged until
            # a test supplies a real native state. A call is never an ACK.
            return None
        self.hass.services=N(has_service=lambda domain,service:True,
                             async_call=service_call)
    def measurements(self,*args):
        return {'temperature':20.}
    def _quiet_context(self,*args):
        return False
    def _gate(self,*args,**kwargs):
        return None if (self._ready and self._active
                        and self.manager.source_valid
                        and self.manager.native_permission) else 'not_authorized'
    def _identity_ok(self, spec):
        return self.manager.source_valid
    def _current_spec(self,spec):
        return self.manager.source_valid
    async def _save(self):
        self._saved.append(deepcopy(self.records))
    async def _pause(self,spec,reason):
        self.record['paused']=reason
        self._status(spec,'paused',reason=reason)
        await self._save()
    def _shutdown_allowed(self,spec,entity,expected):
        owner=self.record['power'].get(entity)
        return bool(
            owner and expected.get('state')=='off'
            and self.now-owner['since']>=owner['min_on']
            and self.manager.source_valid
            and self.manager.foreign_owner is None
        )
    async def _send(self,spec,cap,entity,service,data,expected,**kwargs):
        sent=await namespace['_send'](
            self,spec,cap,entity,service,data,expected,**kwargs)
        if sent:
            self.actual_commands.append((service,dict(data),dict(expected),kwargs))
        return sent


async def run():
    # Confirmed ON for ~13 min before reboot; HA last_changed was RESET
    # 20s ago. True persisted ON time MUST survive restart and Resume.
    r=Controller()
    await r.async_start()
    assert r.record.get('restart_power_verification') is True
    assert r.record.get('paused') is None
    assert r.record['power']['climate.heater']['since']==NOW-750
    assert await r._verify_restart_power(spec), {
        "record":r.record,"status":r.status,
        "settings":r.manager.settings,
        "state":r.states.get("climate.heater"),
    }
    assert r.record.get('restart_power_verification') is None
    assert r.record['power']['climate.heater']['since']==NOW-750
    assert r.actual_commands==[]
    assert await r._power(
        spec,r.manager.cap,'off',automatic=False,shutdown=True
    )
    assert r.actual_commands[-1][0]=='set_temperature'
    assert r.actual_commands[-1][1]=={'temperature':5.}
    assert r.record['power']['climate.heater']['since']==NOW-750
    assert r.record['pending']['expected']=={'attributes':{'temperature':5.}}
    r.now=NOW+29.999
    assert await sequence.progress_stop(r,spec)
    assert len(r.actual_commands)==1
    r.now=NOW+30.
    assert await sequence.progress_stop(r,spec)
    assert r.actual_commands[-1][0]=='set_hvac_mode'
    assert r.actual_commands[-1][1]=={'hvac_mode':'off'}
    assert len(r.actual_commands)==2
    assert r.record['power']['climate.heater']['since']==NOW-750
    assert r.record['native_setpoint_stop']['target_confirmed'] is False
    assert r.record['pending']['expected']=={'state':'off'}

    # A persisted OFF observation can be stale after an acknowledged
    # physical ON operation immediately before the HA process stopped.
    # The first post-restart ON reading must keep confirmed owned runtime.
    resumed=Controller()
    resumed.record['native_power_observations']={
        'climate.heater':{'state':'off','since':NOW-1000}
    }
    resumed.manager.original_store={'version':1,'records':deepcopy(resumed.records)}
    await resumed.async_start()
    assert await resumed._verify_restart_power(spec)
    await resumed._observe_native_running(
        spec,resumed.manager.cap,resumed.states['climate.heater']
    )
    assert resumed.record['power']['climate.heater']['since']==NOW-750

    # A REAL recently switched-ON device must still complete its minimum
    # ON duration even after a restart, regardless of thermostat setpoint.
    recent=Controller(known_since=NOW-120)
    await recent.async_start()
    assert await recent._verify_restart_power(spec)
    assert not await recent._power(
        spec,recent.manager.cap,'off',automatic=False,shutdown=True
    )
    assert recent.actual_commands==[]
    assert recent.status[0]=='minimum_on_hold'

    # After a restart, a previously OWNED heater which now verifiably
    # reports OFF is not proof of a human Manual override. Retire its old
    # ON ownership and conservatively restart the minimum-OFF interval.
    off_restored=Controller(native='off')
    await off_restored.async_start()
    assert off_restored.record.get('restart_power_verification') is True
    assert await off_restored._verify_restart_power(spec)
    assert off_restored.record['power']=={}
    assert off_restored.record['off_at']['climate.heater']==NOW
    assert off_restored.record['baseline']['climate.heater']['state']=='off'
    assert off_restored.record.get('paused') is None
    assert off_restored.actual_commands==[]

    # A previous native ON with a user-selected Manual mode is kept
    # supervised; Resume itself must not send physical services.
    manual=Controller(previous_pause='physical_manual_override')
    await manual.async_start()
    assert not manual.record.get('restart_power_verification')
    assert manual.record['paused']=='physical_manual_override'

    # Unresolved persisted INTENT must NOT be automatically assumed
    # successful even when the currently observed state happens to match.
    p={'entity':'climate.heater','phase':'intent',
       'expected':{'state':'heat'},'power':True}
    ambiguous=Controller(pending=p)
    await ambiguous.async_start()
    assert ambiguous.record['paused']=='restart_reconciliation_required'
    assert not ambiguous.record.get('restart_power_verification')

    # Cold source initially unavailable: wait without toggling anything;
    # then verify exact previous state when the actual source comes online.
    missing=Controller(native=None)
    await missing.async_start()
    assert not await missing._verify_restart_power(spec)
    assert missing.status[0]=='waiting_for_physical_device'
    assert missing.actual_commands==[]
    missing.states['climate.heater']=state('heat',changed=NOW-2)
    assert await missing._verify_restart_power(spec)
    assert missing.record['power']['climate.heater']['since']==NOW-750

    # An actual conflicting state after restart fails closed and stays
    # latched even if the HA process restarts again.
    wrong=Controller(native='cool')
    await wrong.async_start()
    assert not await wrong._verify_restart_power(spec)
    assert wrong.record.get('restart_recovery_blocked') is True
    assert wrong.record.get('paused')=='restart_reconciliation_required'
    assert wrong.actual_commands==[]
    wrong.manager.original_store={'version':1,'records':deepcopy(wrong.records)}
    await wrong.async_start()
    assert not wrong.record.get('restart_power_verification')

    foreign=Controller()
    foreign.manager.foreign_owner='another-integration'
    await foreign.async_start()
    assert not await foreign._verify_restart_power(spec)
    assert foreign.record.get('paused')=='restart_reconciliation_required'

    invalid_identity=Controller()
    invalid_identity.manager.source_valid=False
    await invalid_identity.async_start()
    assert not await invalid_identity._verify_restart_power(spec)
    assert invalid_identity.actual_commands==[]

    # Physical OFF->ON actually observed by runtime starts NEW physical
    # minimum-ON; a mere repeated ON state refresh does not.
    changed=Controller()
    changed._ready=True
    changed.record['native_power_observations']={
       'climate.heater':{'state':'off','since':NOW-90}
    }
    # First observe OFF inside this process. A later real ON transition
    # differs from a stale persisted OFF snapshot restored at startup.
    changed.states['climate.heater']=state('off',changed=NOW-90)
    await changed._observe_native_running(spec,changed.manager.cap,
                                          changed.states['climate.heater'])
    changed.states['climate.heater']=state('heat',changed=NOW-20)
    await changed._observe_native_running(spec,changed.manager.cap,
                                          changed.states['climate.heater'])
    assert changed.record['power']['climate.heater']['since']==NOW
    n=len(changed._saved)
    changed.states['climate.heater']=state('heat',changed=NOW)
    await changed._observe_native_running(spec,changed.manager.cap,
                                          changed.states['climate.heater'])
    assert len(changed._saved)==n, 'Repeated unchanged ON must not write Store'
    assert not await changed._power(
       spec,changed.manager.cap,'off',automatic=False,shutdown=True
    ), 'Genuine recently observed ON must retain min-on'
    assert changed.status[0]=='minimum_on_hold'

    # No previous native power OWNERSHIP: a durable ON observation can be
    # used for explicit Resume, even after HA refreshes last_changed.
    observed=Parent()
    observed.record['native_power_observations']={
       'climate.heater':{'state':'on','since':NOW-1200}
    }
    observed.states['climate.heater']=state('heat',changed=NOW-5)
    await observed.async_resume(spec)
    assert observed.record['power']['climate.heater']['since']==NOW-1200

    # Key runtime integration points must remain in real tick/Resume code.
    src=(ROOT/'equipment_runtime.py').read_text()
    assert 'if not await self._verify_restart_power(spec)' in src
    assert 'await self._observe_native_running(spec, cap, state)' in src
    assert 'native_power_observations' in src
    print('PASS Beta73: persisted heat runtime survives fake HA restart timestamp; reverse target then 30s eligible OFF without false ACK; real short minimum-ON remains held; verified automatic ownership; no power commands during verification; uncertainty fail-closed; durable real OFF->ON transition; no repeated Store writes')


asyncio.run(run())
