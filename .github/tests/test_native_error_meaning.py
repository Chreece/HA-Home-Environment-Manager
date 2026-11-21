"""Native validation errors must identify the failure and retain its constraints.

Several unrelated errors previously rendered as the same generic settings
message. Check the bundled config and options messages rather than only the
authoring catalog, and preserve the technical requirements users must satisfy.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRANSLATIONS = ROOT / 'custom_components/environment_manager/translations'
CATALOG = json.loads((ROOT / '.github/localization/native_residual_errors.json').read_text(encoding='utf-8'))
ENGLISH = json.loads((TRANSLATIONS / 'en.json').read_text(encoding='utf-8'))
ERROR_KEYS = (
    'invalid_environment_scale', 'invalid_environment_measurement',
    'pmv_requires_explicit_inputs', 'pid_climate_required',
    'pid_temperature_required', 'pid_invalid_target', 'pid_duplicate_climate',
    'pid_invalid_parameters', 'climate_temperature_required',
    'climate_target_required', 'climate_direct_actuator_not_ready',
    'climate_controller_invalid', 'climate_mode_invalid',
    'climate_occupancy_invalid', 'climate_away_invalid',
    'climate_deadband_invalid', 'climate_attestation_required',
    'climate_direct_targets_invalid', 'climate_direct_timing_invalid',
)
files = sorted(TRANSLATIONS.glob('*.json'))
locales = {path.stem for path in files}
assert len(locales) == 38
assert len(ERROR_KEYS) == len(CATALOG) == 19
assert set(CATALOG) == {ENGLISH['config']['error'][key] for key in ERROR_KEYS}
for source, variants in CATALOG.items():
    assert variants.keys() == locales, ('Incomplete error catalog', source)
    assert variants['en'] == source

for path in files:
    locale = path.stem
    obj = json.loads(path.read_text(encoding='utf-8'))
    for section in ('config', 'options'):
        errors = obj[section]['error']
        rendered = [errors[key] for key in ERROR_KEYS]
        assert len(set(rendered)) == len(ERROR_KEYS), (locale, section, 'Different failures have identical explanations')
        for key in ERROR_KEYS:
            source = ENGLISH[section]['error'][key]
            value = errors[key]
            assert isinstance(value, str) and value.strip(), (locale, section, key)
            assert value == CATALOG[source][locale], (locale, section, key, 'Authored error explanation was lost')
            if locale != 'en':
                assert value != source, (locale, section, key, 'English fallback')
        assert '1°C' in errors['climate_deadband_invalid'], (locale, section, 'Missing heat/cool gap')
        assert 'PWM' in errors['climate_direct_timing_invalid'], (locale, section, 'Missing PWM timing requirement')
        for term in ('PMV', 'clo', 'met'):
            assert term in errors['pmv_requires_explicit_inputs'], (locale, section, 'Missing PMV input', term)
        assert 'PID' in errors['pid_temperature_required'], (locale, section, 'Missing PID prerequisite')
        assert 'AQI' in errors['invalid_environment_scale'], (locale, section, 'Missing scale context')

# This shared error is emitted for climate mode, profile, unknown occupancy,
# and humidity validation; a heat/cool-only instruction is misleading.
mode_source = ENGLISH['config']['error']['climate_mode_invalid']
for concept in ('climate mode', 'operating profile', 'unknown-occupancy', 'humidity limits', 'allowed ranges'):
    assert concept in mode_source, ('Shared climate validation guidance is incomplete', concept)

# Presence validation shares this error with policy/profile/target selection;
# blaming the selected sensor alone would hide the actual invalid choice.
occupancy_source = ENGLISH['config']['error']['climate_occupancy_invalid']
for concept in ('occupancy sensors', 'presence settings', 'this room', 'policy, profile and target options'):
    assert concept in occupancy_source, ('Shared presence validation guidance is incomplete', concept)

print('PASS: 19 distinct, complete native validation errors in both flows across all 38 languages')
