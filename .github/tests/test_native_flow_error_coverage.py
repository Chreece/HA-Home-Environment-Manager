"""Require translated messages for errors actually emitted by native forms.

Comparing locale keys against English alone cannot find messages missing from
every catalog. Read error references from production forms, with the room
subentry's own namespace, without importing Home Assistant or changing controls.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'custom_components/environment_manager'


def error_references(path):
    references = set()
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        values = []
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if (isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == 'errors'):
                    values.append(node.value)
                elif (isinstance(target, ast.Name) and target.id == 'errors'
                      and isinstance(node.value, ast.Dict)):
                    values.extend(node.value.values)
        elif (isinstance(node, ast.keyword) and node.arg == 'errors'
              and isinstance(node.value, ast.Dict)):
            values.extend(node.value.values)
        for value in values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                references.add(value.value)
    return references


references = {path.name: error_references(path) for path in SOURCE.glob('*.py')}
main_errors = set().union(*(values for name, values in references.items()
                           if name != 'room_hub_flow.py'))
room_errors = references['room_hub_flow.py']
assert 'climate_invalid_sleep_schedule' in main_errors
assert 'device_conflicting_control' in main_errors
assert 'invalid_freshness_mode' in main_errors
assert 'invalid_area' in room_errors

files = sorted((SOURCE / 'translations').glob('*.json'))
assert len(files) == 38
for path in files:
    locale = path.stem
    catalog = json.loads(path.read_text(encoding='utf-8'))
    for flow in ('config', 'options'):
        errors = catalog[flow]['error']
        assert not main_errors - errors.keys(), (locale, flow, sorted(main_errors - errors.keys()))
        assert all(isinstance(errors[key], str) and errors[key].strip()
                   for key in main_errors), (locale, flow, 'blank error message')

        # These limits and technical requirements tell users how to correct
        # rejected input. Keep them present even if prose is edited later.
        schedule = errors['climate_invalid_sleep_schedule']
        assert 'HH:MM' in schedule and '24' in schedule, (locale, flow, schedule)
        timing = errors['climate_invalid_occupancy_timing']
        assert {'0', '240', '10', '1440'} <= set(re.findall(r'\d+', timing)), (locale, flow, timing)
        adjustment = errors['climate_invalid_comfort_adjustment'].replace(',', '.')
        assert '2.5' in adjustment and '°C' in adjustment, (locale, flow, adjustment)
        proportional = errors['climate_proportional_requires_percent']
        assert all(token in proportional for token in ('number', '%', '0', '100')), (locale, flow)
        assert 'DRY' in errors['device_dry_advisory_only'], (locale, flow)
        assert 'PID' in errors['climate_pid_separate_configuration'], (locale, flow)

    translated_room_errors = catalog['config_subentries']['room']['error']
    assert not room_errors - translated_room_errors.keys(), (locale, 'room', room_errors)

print(f'PASS: {len(main_errors)} native form errors and {len(room_errors)} room-subentry errors in all 38 languages')
