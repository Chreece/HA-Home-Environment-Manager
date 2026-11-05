"""Beta94: physical DRY/OFF and an HEM-owned relay do not invent user touch.

Execute real EquipmentRuntime._reconcile with the same HA-state/context,
native baseline and persisted physical output history as prior Beta89 tests.
No actual HA service calls or physical commands occur.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import runpy
from types import SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
b=runpy.run_path(str(ROOT/'.github/tests/test_beta89_automatic.py'))
FakeController=b['FakeController']
FakeState=b['FakeState']
Model=b['Model']
SPEC=b['SPEC']
sn=b['sn']

def owned_dry():
    r=FakeController('pid')
    r.manager.settings[Model.SETTINGS][SPEC.identifier].update(
        requested_mode='dry',power_switch_entity='switch.comfee',
    )
    r.manager.cap=N(primary='climate.native',domain='climate',
                    modes=('off','dry'))
    r.states_by_id={}
    r.state=FakeState('dry',humidity=60)
    r.states_by_id['climate.native']=r.state
    r.supply=FakeState('on')
    r.supply.domain='switch'
    r.states_by_id['switch.comfee']=r.supply
    r.hass.states=N(get=lambda entity:r.states_by_id.get(entity))
    r.record['baseline']={'climate.native':sn(r.state)}
    r.record['upstream']={
        'entity':'switch.comfee','owned':True,
        'pending':None,'paused':None,
        'on_at':900.,'off_at':200.,'identity':{'native':'confirmed'},
    }
    r.record['power']={'climate.native':{
        'since':900.,'min_on':600.,'max_on':7200.,
    }}
    r.record['off_at']={}
    r.record['pending']=None
    r._native_offline_under_owned_supply=set()
    return r

async def scenarios():
    # A dry-only compressor may report OFF as internal humidity demand ends.
    # With the same verified HEM-owned supply ON and NO user context, this
    # must not permanently demote the saved PID control method to Manual.
    r=owned_dry()
    r.state=FakeState('off',humidity=60)
    r.states_by_id['climate.native']=r.state
    assert await r._reconcile(SPEC)
    assert Model.settings(r.manager,SPEC)['control_mode']=='pid'
    assert not r.record.get('paused')
    assert not r.record['power']
    assert r.record['off_at']['climate.native']==r.clock()
    assert r.record['baseline']['climate.native']['state']=='off'
    assert r.record['upstream']['owned'] is True
    assert not r.calls,'no native or relay service can be sent in reconciliation'

    # Real HA user intervention carries explicit context. It must still stop
    # automatic commands and demote *only* the affected controller.
    person=owned_dry()
    person.state=FakeState('off',humidity=60)
    person.state.context=N(user_id='native-ha-user')
    person.states_by_id['climate.native']=person.state
    assert not await person._reconcile(SPEC)
    assert person.record['paused']=='physical_manual_override'
    assert Model.settings(person.manager,SPEC)['control_mode']=='manual'

    # An authenticated direct HA target change remains a real manual
    # intervention. Anonymous firmware target changes are not evidence of a user.
    physical=owned_dry()
    physical.state=FakeState('dry',humidity=54)
    physical.state.context=N(user_id='explicit-ha-user',parent_id=None)
    physical.states_by_id['climate.native']=physical.state
    assert not await physical._reconcile(SPEC)
    assert physical.record['paused']=='physical_manual_override'
    assert Model.settings(physical.manager,SPEC)['control_mode']=='manual'

    # Native state disappeared and came back while the outlet never lost its
    # HEM-owned ON. Auto-rebuild the baseline, but do not invent new native
    # ON ownership, shorten compressor minimums or invoke physical services.
    recovered=owned_dry()
    recovered._native_offline_under_owned_supply.add(SPEC.identifier)
    recovered.record['power']={}
    recovered.state=FakeState('dry',humidity=25)
    recovered.states_by_id['climate.native']=recovered.state
    assert await recovered._reconcile(SPEC)
    assert recovered.record.get('paused') is None
    assert not recovered.record['power'], 'native ON cannot be adopted from a reconnection'
    assert recovered.record['baseline']['climate.native']['state']=='dry'
    assert SPEC.identifier not in recovered._native_offline_under_owned_supply
    assert Model.settings(recovered.manager,SPEC)['control_mode']=='pid'

    anonymous=owned_dry()
    anonymous.state=FakeState('dry',humidity=51)
    anonymous.states_by_id['climate.native']=anonymous.state
    assert await anonymous._reconcile(SPEC)
    assert Model.settings(anonymous.manager,SPEC)['control_mode']=='pid'
    assert not anonymous.record.get('paused')
    assert anonymous.record['baseline']['climate.native']['attributes']['humidity']==51

    # Explicitly reported local physical-button evidence also counts.
    button=owned_dry()
    button.state=FakeState('off',humidity=60,operation_source='physical_button')
    button.states_by_id['climate.native']=button.state
    assert not await button._reconcile(SPEC)
    assert button.record.get('paused')=='physical_manual_override'

    # Existing non-DRY devices retain their real native manual override
    # detection; this is not a blanket permission to ignore user changes.
    heat=owned_dry()
    heat.manager.cap=N(primary='climate.native',domain='climate',
                       modes=('off','heat','cool'))
    heat.state=FakeState('cool',humidity=60)
    heat.state.context=N(user_id='explicit-ha-user',parent_id=None)
    heat.states_by_id['climate.native']=heat.state
    assert not await heat._reconcile(SPEC)
    assert heat.record['paused']=='physical_manual_override'
    assert Model.settings(heat.manager,SPEC)['control_mode']=='manual'

    # A dehumidifier with NO authenticated HEM-controlled upstream switch
    # retains normal physical native change detection.
    unowned=owned_dry()
    unowned.record['upstream']['owned']=False
    unowned.state=FakeState('off',humidity=60)
    unowned.state.context=N(user_id='explicit-ha-user',parent_id=None)
    unowned.states_by_id['climate.native']=unowned.state
    assert not await unowned._reconcile(SPEC)
    assert unowned.record['paused']=='physical_manual_override'

    # The real relay observer—not a test-supplied flag—must record an
    # actual native HA disconnect with the dedicated supply still owned ON.
    supply_test=runpy.run_path(str(ROOT/'.github/tests/test_beta83_supply_safety.py'))
    case=supply_test['PowerSafetyTests'](methodName='test_tick_starts_cooldown_on_verified_native_stop')
    case.setUp()
    case.states.values['climate.native']=supply_test['State']('climate','unavailable')
    await case.ns['before_tick'](case.runtime,case.spec)
    assert case.spec.identifier in case.runtime._native_offline_under_owned_supply
    assert not case.sent, 'unknown downstream source must never cause relay ON'
    print('BETA94_DRY_SUPPLY_AUTO_CONTINUITY_TRUE_USER_ONLY_MANUAL=PASS')

asyncio.run(scenarios())
