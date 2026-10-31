"""Beta73 real restart/recovery/ON-observation/power safety regression.

The actual EquipmentRuntime async_start, _verify_restart_power,
_observe_native_running and _power methods execute against isolated
native HA state, durable-Store and service stubs. No real HA commands.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
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
nodes=[n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name in methods]
assert {n.name for n in nodes}==set(methods)
namespace={
 '__name__':'beta73_fixture.equipment_runtime',
 '__package__':'beta73_fixture',
 'asyncio':asyncio, 'deepcopy':deepcopy,
 'HomeAssistantError':HomeAssistantError,
 'model':ExtendedModel, 'snapshot':snap, 'output_off':off,
 'finite':finite, '_manual_output_changes':physical_changes,
 'foreign_owner_hold':lambda hass,owner,e: hass.manager.foreign_owner,
 'DOMAIN':'environment_manager',
}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'equipment_runtime.py','exec'),namespace)

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
    async_start=namespace['async_start']
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
        self.manager.native_permission=True
        self.manager.source_valid=True
        self.status=None
        self.actual_commands=[]
        self._store=None
        self._ready=False
        self._started=NOW-800
        self._profile_wake={}
        self._pid_offline_previews={}
        self._fan_allocations={}
        self._saved=[]
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
        self.actual_commands.append((service,dict(data),dict(expected),kwargs))
        return True


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
    assert r.actual_commands[-1][0]=='set_hvac_mode'
    assert r.actual_commands[-1][1]=={'hvac_mode':'off'}

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
    print('PASS Beta73: persisted heat runtime survives fake HA restart timestamp; immediate eligible OFF; real short minimum-ON remains held; verified automatic ownership; no power commands during verification; uncertainty fail-closed; durable real OFF->ON transition; no repeated Store writes')


asyncio.run(run())
