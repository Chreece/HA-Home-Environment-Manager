"""Beta89 source-driven controller automatic/physical-override regression tests.

No Home Assistant installation, real devices, or network access required.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as Obj
import unittest

ROOT=Path(__file__).resolve().parents[2]

class HomeAssistantError(Exception):
    pass

class FakeState:
    def __init__(self, value, **attrs):
        self.state=value
        self.domain='climate'
        self.attributes=attrs

class Model:
    SETTINGS='equipment_controllers'
    @staticmethod
    def settings(manager, spec):
        return manager.settings[Model.SETTINGS][spec.identifier]
    @staticmethod
    def capabilities(manager,spec):
        return manager.cap
    @staticmethod
    def control_modes(manager,spec):
        return ('existing','automatic','pid','manual','off')

def extract(path, name, klass):
    parsed=ast.parse((ROOT/path).read_text(encoding='utf-8'))
    cl=next(n for n in parsed.body if isinstance(n,ast.ClassDef) and n.name==klass)
    f=next(n for n in cl.body if isinstance(n,(ast.AsyncFunctionDef,ast.FunctionDef)) and n.name==name)
    return f

def compile_fn(node, namespace):
    module=ast.Module(body=[node],type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), '<beta89>', 'exec'),namespace)
    return namespace[node.name]

async_set_mode=compile_fn(extract('climate.py','async_set_hvac_mode','ManagedClimate'),{
    'HomeAssistantError':HomeAssistantError
})

button_ns={}
available=compile_fn(extract('button.py','available','EquipmentResumeButton'),button_ns)
available=available.fget if isinstance(available,property) else available
pause=compile_fn(extract('equipment_runtime.py','_pause','EquipmentRuntime'),{
    'model':Model,'asyncio':asyncio,'deepcopy':deepcopy
})
def sn(s):
    if s is None or s.state in ('unknown','unavailable'):return None
    return {'state':s.state,'attributes':dict(s.attributes)}
def changes(before,after):
    if before.get('state')!=after.get('state'):return ('state',)
    keys=('temperature','humidity','fan_mode','percentage','preset_mode')
    return tuple(k for k in keys if k in before['attributes'] and k in after['attributes']
                 and before['attributes'][k]!=after['attributes'][k])
reconcile=compile_fn(extract('equipment_runtime.py','_reconcile','EquipmentRuntime'),{
    'model':Model,'snapshot':sn,'matches':lambda state,expected:
        state is not None and all((state.state==v if k=='state' else True)
            for k,v in expected.items()),
    '_manual_output_changes':changes
})
prefix='beta89_runtime'
pkg=ModuleType(prefix);pkg.__path__=[]
auth=ModuleType(prefix+'.device_activation')
auth.authority_context=lambda manager,spec: {'area':spec.area_id,
    'sources':list(spec.source_entities)}
sys.modules[prefix]=pkg
sys.modules[auth.__name__]=auth
continue_auto=compile_fn(extract('equipment_runtime.py','async_continue_automatic','EquipmentRuntime'),{
    '__name__':prefix+'.equipment_runtime',
    '__package__':prefix,
    'HomeAssistantError':HomeAssistantError,
    'model':Model,'asyncio':asyncio,'deepcopy':deepcopy
})

SPEC=Obj(identifier='managed-1',area_id='room1',
         source_entities=('climate.native',),source_device_id='real-1')
class FakeController:
    async_continue_automatic=continue_auto
    _pause=pause
    _reconcile=reconcile
    def __init__(self, method='pid'):
        self.cap=Obj(primary='climate.native',domain='climate')
        self.manager=Obj(
            cap=self.cap,
            settings={Model.SETTINGS:{SPEC.identifier:{
                'control_mode':method,
                '_native_authorization':{'area':SPEC.area_id,
                                         'sources':list(SPEC.source_entities)},
            }}},
        )
        self.manager.entry=Obj(options=deepcopy(self.manager.settings))
        self.calls=[]
        self.hass=Obj(
            states=Obj(get=lambda entity:self.state),
            config_entries=Obj(async_update_entry=self._update),
        )
        self.manager.hass=self.hass
        self.state=FakeState('off',temperature=20)
        self._ready=True
        self.record={
            'baseline':{'climate.native':sn(self.state)},
            'power':{},'pending':None,
        }
        self.records={SPEC.identifier:self.record}
        self._restart_baseline_pending=set()
        self.status=[]
        self.saves=0
        self._locked=asyncio.Lock()
    def _update(self,entry,*,options):
        entry.options=deepcopy(options)
        self.manager.settings=deepcopy(options)
    def _current_spec(self,spec):return True
    def _record(self,spec):return self.record
    def _status(self,spec,status,**kw):self.status.append((status,kw))
    def _lock(self,k):return self._locked
    def clock(self):return 1000.0
    async def _save(self):self.saves+=1
    async def async_resume(self,spec):
        raise HomeAssistantError('Native command requires physical acknowledgement')

class TestAutomatic(unittest.IsolatedAsyncioTestCase):
    async def test_hem_facade_never_demotes_automatic_or_pid(self):
        for mode,physical in (('automatic','cool'),('pid','off')):
            with self.subTest(mode=mode,physical=physical):
                seen=[]
                async def update(spec,data):seen.append(data)
                obj=Obj(
                    controller_settings={'control_mode':mode},
                    hvac_modes=['off','heat','cool'],
                    _manager=Obj(equipment=Obj(async_update=update)),
                    _spec=SPEC,
                )
                await async_set_mode(obj,physical)
                self.assertEqual(seen,[{'requested_mode':physical}])
        seen=[]
        async def update(spec,data):seen.append(data)
        obj=Obj(controller_settings={'control_mode':'manual'},
                hvac_modes=['off','heat','cool'],
                _manager=Obj(equipment=Obj(async_update=update)),_spec=SPEC)
        await async_set_mode(obj,'off')
        self.assertEqual(seen,[{'requested_mode':'off','control_mode':'off'}])

    async def test_only_real_native_intervention_demotes_to_manual(self):
        r=FakeController()
        await r._pause(SPEC,'physical_manual_override')
        self.assertEqual(Model.settings(r.manager,SPEC)['control_mode'],'manual')
        self.assertEqual(r.record['resume_control_mode'],'pid')
        self.assertEqual(r.record['paused'],'physical_manual_override')
        other=FakeController()
        await other._pause(SPEC,'controller_exception')
        self.assertEqual(Model.settings(other.manager,SPEC)['control_mode'],'pid')
        self.assertEqual(other.record['paused'],'controller_exception')

    async def test_restart_rebuilds_native_baseline_without_manual_demote(self):
        r=FakeController('automatic')
        r._restart_baseline_pending.add(SPEC.identifier)
        r.state=FakeState('heat',temperature=21)
        result=await r._reconcile(SPEC)
        self.assertTrue(result)
        self.assertNotIn(SPEC.identifier,r._restart_baseline_pending)
        self.assertEqual(r.record['baseline']['climate.native']['state'],'heat')
        self.assertEqual(Model.settings(r.manager,SPEC)['control_mode'],'automatic')
        # A later real native mode change, unlike the first HA restore,
        # must still stop the supervisor and switch only that device to Manual.
        r.state=FakeState('cool',temperature=21)
        self.assertFalse(await r._reconcile(SPEC))
        self.assertEqual(Model.settings(r.manager,SPEC)['control_mode'],'manual')
        self.assertEqual(r.record['paused'],'physical_manual_override')

    async def test_explicit_continue_selects_prior_pid_without_dispatch(self):
        r=FakeController('manual')
        r.record['resume_control_mode']='pid'
        r.record['paused']='physical_manual_override'
        r.record['pending']={'entity':'climate.native','phase':'intent'}
        result=await r.async_continue_automatic(SPEC)
        self.assertFalse(result)  # selected; physical reconciliation still pending
        self.assertEqual(Model.settings(r.manager,SPEC)['control_mode'],'pid')
        self.assertEqual(r.record['paused'],'physical_manual_override')
        self.assertIsNotNone(r.record['pending'])
        self.assertEqual(r.record['automatic_continue_requested']['method'],'pid')
        self.assertEqual(r.calls,[])
        self.assertFalse(r.status[-1][1]['physical_output_confirmed'])

    async def test_explicit_continue_defaults_to_automatic(self):
        r=FakeController('manual')
        r.record['paused']='physical_manual_override'
        await r.async_continue_automatic(SPEC)
        self.assertEqual(Model.settings(r.manager,SPEC)['control_mode'],'automatic')
        self.assertEqual(r.record['paused'],'physical_manual_override')

    async def test_button_disabled_when_automatic_active(self):
        r=FakeController('pid')
        obj=Obj(_manager=Obj(equipment=r),_spec=SPEC,
                controller_settings=Model.settings(r.manager,SPEC))
        self.assertFalse(available(obj))
        r.record['paused']='physical_manual_override'
        # Beta98: selected PID is not proof the physical controller is
        # running. A paused controller's button MUST remain actionable.
        self.assertTrue(available(obj))
        r.record['paused']=None
        r.record['pending']={'entity':'climate.native'}
        self.assertTrue(available(obj))
        r.record['pending']=None
        r.manager.settings[Model.SETTINGS][SPEC.identifier]['control_mode']='manual'
        obj.controller_settings=Model.settings(r.manager,SPEC)
        self.assertTrue(available(obj))

if __name__=='__main__':
    unittest.main(verbosity=2)
