"""Reproducible settings catalog, not an unreferenced-string dead-code detector.

Inventories static native setting translations and config/options form fields.
A catalog entry is not proof that a particular device exposes the setting.
Dynamic mode targets and per-door controls are listed as explicit families.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'custom_components/environment_manager'
POLICY=SOURCE/'frontend/settings-audit-policy.json'
DOMAINS=('number','select','switch','time','button')

def inventory():
    catalog=json.loads((SOURCE/'strings.json').read_text())
    policy=json.loads(POLICY.read_text())
    paths={}
    for path in SOURCE.glob('*.py'):
        if path.name.endswith('_catalog.py') or path.name.endswith('_help.py'):
            continue
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                paths.setdefault(node.value,set()).add(f'{path.relative_to(ROOT)}:{node.lineno}')
    records=[]
    for domain in DOMAINS:
        for key,values in catalog['entity'].get(domain,{}).items():
            reason=policy['advanced'].get(key)
            records.append({'kind':'native_catalog','platform':domain,'key':key,
                'name':values.get('name',key),
                'presentation':'primary' if domain=='button' or not reason else 'advanced',
                'reason':reason or ('explicit_action' if domain=='button' else 'retain'),
                'same_property_options_alias':policy['home_aliases'].get(key),
                'catalog_path':f'strings.json/entity/{domain}/{key}',
                'literal_references':sorted(paths.get(key,()))[:6],
                'consumer_status':'runtime_and_dynamic_generation_not_exhaustively_proven'})
    for section in ('config','options'):
        for step,values in catalog.get(section,{}).get('step',{}).items():
            for key,name in values.get('data',{}).items():
                advanced=section=='options' and step=='setup_general' and key in policy['advanced_options']
                records.append({'kind':'form_catalog','surface':section,'step':step,
                    'key':key,'name':name,
                    'presentation':'advanced' if advanced else 'retain',
                    'catalog_path':f'strings.json/{section}/step/{step}/data/{key}',
                    'literal_references':sorted(paths.get(key,()))[:6],
                    'consumer_status':'catalog_only_step_reachability_not_proven'})
    for key in ('target_area','kind','report_timeout_minutes','coordination','energy_meter'):
        records.append({'kind':'dynamic_door','key':'door_'+key,
            'presentation':'advanced' if 'door_'+key in policy['advanced'] else 'primary',
            'definition':'custom_components/environment_manager/door_entities.py:select_entities/number_entities',
            'consumer':'custom_components/environment_manager/door_settings.py:async_update'})
    for profile in ('manual','home','comfort','away','sleep','eco'):
        for metric in ('heat','cool','humidity'):
            records.append({'kind':'dynamic_mode_target','key':f'target_{profile}_{metric}',
                'presentation':'primary','definition':'equipment_mode_entities.py:scoped_fields/target_field',
                'consumer':'equipment_mode_settings.py:resolve_settings'})
    known={r['key'] for r in records if r['kind'] in ('native_catalog','dynamic_door')}
    assert not set(policy['advanced'])-known, set(policy['advanced'])-known
    text=(SOURCE/'frontend/air-quality-advisor-card.js').read_text()
    start=text.index('const auditPolicyB8=')+len('const auditPolicyB8=')
    embedded,_=json.JSONDecoder().raw_decode(text[start:])
    assert embedded==policy,'Embedded UI policy and audit source differ'
    critical=('equipment_min_on_seconds','equipment_min_off_seconds','equipment_max_on_seconds',
              'equipment_sensor_verified','equipment_pause_on_window_open','equipment_off_state_watchdog_mode')
    assert not set(critical)&set(policy['advanced']), 'Protection settings must remain primary'
    return {'baseline':'365f81082111b6bcd0fb2b1976eee60805ddc8b7',
        'scope':'Source-verified presentation pass; completed external research report unavailable',
        'limitations':['Catalog entries are not counts of controls shown on any device.',
            'Literal references are navigation aids, not proof of use or non-use.',
            'Legacy form reachability and dynamic consumers require separate review.',
            'No stored configuration, authorization, runtime or native entity was removed.'],
        'counts':dict(Counter(r['kind'] for r in records)),
        'policy':policy,'settings':records}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true')
    args=parser.parse_args();result=inventory()
    output=ROOT/'docs/settings-inventory.json'
    encoded=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.check:
        assert output.read_text()==encoded,'Regenerate settings inventory after changing catalog or code references'
    else:
        output.parent.mkdir(exist_ok=True);output.write_text(encoded)
    print('PASS: settings inventory',result['counts'],'advanced identities',len(result['policy']['advanced']))
