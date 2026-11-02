"""Beta91: actual managed PID restart checkpoint and source-bound continuity.

Executes source-defined checkpoint/restore and EquipmentRuntime's actual
checkpoint methods with an isolated .storage stub. No live HA device or
network is needed.
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass
import math
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT=Path(__file__).resolve().parents[2]
r=runpy.run_path(str(ROOT/'pid_restart.py'))
checkpoint=r['checkpoint']
restore=r['restore']

@dataclass(frozen=True)
class PIDMemory:
    integral: float=0.
    measured: float|None=None
    stamp: float|None=None
    derivative: float=0.
    demand: float=0.

def methods():
    t=ast.parse((ROOT/'equipment_runtime.py').read_text(encoding='utf-8'))
    cls=next(x for x in t.body if isinstance(x,ast.ClassDef)
             and x.name=='EquipmentRuntime')
    names={'_resume_pid_checkpoint','_checkpoint_pid'}
    nodes=[x for x in cls.body if isinstance(x,ast.AsyncFunctionDef)
           or isinstance(x,ast.FunctionDef)]
    nodes=[x for x in nodes if x.name in names]
    assert {x.name for x in nodes}==names
    pkg=ModuleType('test_beta91')
    pkg.__path__=[]
    mod=ModuleType('test_beta91.pid_restart')
    mod.checkpoint=checkpoint
    mod.restore=restore
    sys.modules[pkg.__name__]=pkg
    sys.modules[mod.__name__]=mod
    scope={'__name__':'test_beta91.equipment_runtime',
           '__package__':'test_beta91',
           'model':N(PIDMemory=PIDMemory)}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),
                 'equipment_runtime.py','exec'),scope)
    return scope

ns=methods()
spec=N(identifier='bathroom',area_id='bathroom',
       source_device_id='physical-comfee',
       source_entities=('climate.comfee',))
signature=('humidity',60.,False,'home','dry','none',
           10.,0.2,0.,3600.,600.,600.)
cfg={'sample_seconds':300.,'kp':10.,'ki':0.2,'kd':0.}
NOW=1_800_000_000.

class TestPidRestart(unittest.IsolatedAsyncioTestCase):
    async def test_pid_integral_and_phase_restored_offline_without_hardware_commands(self):
        source=N(clock=lambda:NOW)
        source.saved=0
        async def save():source.saved+=1
        source._save=save
        record={'area':spec.area_id,'sources':list(spec.source_entities),
                'power':{},'off_at':{'climate.comfee':NOW-740},
                'upstream':{'on_at':NOW-4000,'off_at':NOW-4700,'owned':True}}
        memory=PIDMemory(integral=36.,measured=65.,stamp=NOW-240,
                         derivative=-0.8,demand=85.)
        await ns['_checkpoint_pid'](source,spec,record,cfg,signature,memory,NOW-600)
        self.assertEqual(source.saved,1)
        snapshot=record['pid_checkpoint']
        self.assertEqual(snapshot['integral'],36.)
        self.assertEqual(snapshot['anchor'],NOW-600)
        self.assertEqual(snapshot['signature'],list(signature))
        # A second tick inside the same sampling period does not write Store.
        await ns['_checkpoint_pid'](source,spec,record,cfg,signature,memory,NOW-600)
        self.assertEqual(source.saved,1)
        restarted=N(clock=lambda:NOW+270)
        result=ns['_resume_pid_checkpoint'](
            restarted,spec,record,cfg,64.5,60.,False
        )
        self.assertIsNotNone(result)
        recovered_signature,recovered_memory,recovered_anchor=result
        self.assertEqual(recovered_signature,signature)
        self.assertEqual(recovered_anchor,NOW-600)
        self.assertEqual(recovered_memory.integral,36.)
        self.assertEqual(recovered_memory.measured,64.5)
        self.assertEqual(recovered_memory.stamp,NOW+270)
        # PID derivative is reseeded and OFF-line interval cannot wind up I.
        self.assertEqual(recovered_memory.derivative,0.)
        self.assertAlmostEqual(recovered_memory.demand,81.)
        self.assertEqual(record['pid_restart_status'],'integral_and_phase_restored')
        # The actual native OFF/supply times and command ownership are untouched.
        self.assertEqual(record['off_at']['climate.comfee'],NOW-740)
        self.assertEqual(record['upstream']['on_at'],NOW-4000)
        self.assertEqual(record['upstream']['owned'],True)
        self.assertEqual(record['power'],{})

    async def test_stale_foreign_or_changed_sample_never_resumes(self):
        memory=PIDMemory(integral=30.,measured=21.,stamp=NOW-120,
                         derivative=0.,demand=30.)
        saved=checkpoint(signature,memory,NOW-900,
                         spec.source_entities,spec.source_device_id,
                         cfg['sample_seconds'],NOW)
        self.assertIsNotNone(saved)
        valid=dict(sources=spec.source_entities,
                   source_device_id=spec.source_device_id,
                   now=NOW+200,sample=300.,measured=21.,
                   goal=20.,increasing=True,kp=10.)
        self.assertIsNotNone(restore(saved,**valid))
        self.assertIsNone(restore(saved,**{**valid,'sources':('climate.other',)}))
        self.assertIsNone(restore(saved,**{**valid,'source_device_id':'another-device'}))
        self.assertIsNone(restore(saved,**{**valid,'sample':600.}))
        self.assertIsNone(restore(saved,**{**valid,'now':NOW+3600}))
        self.assertIsNone(restore({**saved,'integral':120.},**valid))
        self.assertIsNone(restore({**saved,'anchor':-5.},**valid))
        self.assertIsNone(restore({**saved,'integral':'NaN'},**valid))
        self.assertIsNone(restore({**saved,'signature':['wrong']},**valid))

    async def test_true_configuration_change_rebases_logical_phase(self):
        saved=checkpoint(signature,PIDMemory(25.,64.,NOW-240,0.,45.),
                         NOW-1200,spec.source_entities,
                         spec.source_device_id,300.,NOW)
        previous, _, anchor=restore(
            saved,sources=spec.source_entities,
            source_device_id=spec.source_device_id,
            now=NOW+200,sample=300.,measured=64.,
            goal=60.,increasing=False,kp=10.,
        )
        phase=runpy.run_path(str(ROOT/'pid_phase.py'))['phase_decision']
        unchanged,reset,_=phase(
            previous,metric='humidity',target=60.,
            increasing=False,profile='home',mode='dry',preset='none',
            kp=10.,ki=0.2,kd=0.,cycle_s=3600.,
            min_on_s=600.,min_off_s=600.,measured=64.,
        )
        self.assertFalse(reset)
        self.assertEqual(unchanged,signature)
        updated,reset,_=phase(
            previous,metric='humidity',target=57.,
            increasing=False,profile='home',mode='dry',preset='none',
            kp=10.,ki=0.2,kd=0.,cycle_s=3600.,
            min_on_s=600.,min_off_s=600.,measured=64.,
        )
        self.assertTrue(reset)
        self.assertNotEqual(updated,signature)

if __name__=='__main__':
    unittest.main(verbosity=2)
