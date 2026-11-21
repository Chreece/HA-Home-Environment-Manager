"""Guard real native translation coverage, including safe shared vocabulary.

Key parity alone cannot detect English prose copied into every language. These
checks intentionally distinguish accepted international terms and cognates from
untranslated UI text, and verify room-context interpolation independently.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import runpy

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'custom_components/environment_manager'


def flatten(value, path=()):
    if isinstance(value, dict):
        return {key: leaf for name, child in value.items()
                for key, leaf in flatten(child, path + (name,)).items()}
    return {'.'.join(path): value}


def placeholders(value):
    return set(re.findall(r'(?<!\{)\{([A-Za-z_][A-Za-z_0-9]*)\}(?!\})', value))


def help_fingerprint(key, text, values):
    for description, label in (('.data_description.', '.data.'),
                               ('.menu_option_descriptions.', '.menu_options.')):
        if description in key:
            field_label = values.get(key.replace(description, label), '')
            if field_label:
                text = text.replace(field_label, '{label}')
    text = re.sub(r'[„“«「『][^”"»」』\n]{1,140}[”"»」』]', '{label}', text)
    text = re.sub(r'"[^"\n]{1,140}"', '{label}', text)
    return re.sub(r'AQI\s*#\d+', 'AQI #{n}', text)


builder = runpy.run_path(str(ROOT / '.github/scripts/build_native_translations.py'))
builder['runtime_catalogs']()
runtime_text = builder['importlib'].import_module('_hem_native_translation_build.backend_text_catalog').TEXT
repaired_forms = json.loads((ROOT / '.github/localization/native_forms.json').read_text(encoding='utf-8'))
rejected_templates = json.loads((ROOT / '.github/translations/native_rejected_help_templates.json').read_text(encoding='utf-8'))
audited_help = json.loads((ROOT / '.github/translations/native_help_audit_sources.json').read_text(encoding='utf-8'))
room_selector_review = json.loads((ROOT / '.github/translations/native_room_selector_review.json').read_text(encoding='utf-8'))
residual_help = {}
for path in (ROOT / '.github/localization').glob('native_residual_*.json'):
    residual_help.update(json.loads(path.read_text(encoding='utf-8')))
approved_help = {**runtime_text, **residual_help, **repaired_forms}
missing_authored = [entry['id'] for entry in audited_help if entry['en'] not in approved_help]
assert not missing_authored, ('Audited native explanations lack complete authored replacements', missing_authored)
audited_sources = {entry['en'] for entry in audited_help}
RAW_LABEL_RESIDUE = (
    'PID_OFFSET_C', 'MIN TARGET', 'MAX TARGET', 'AUTOMATIC_NOTIFICATIONS',
    'NO VENT', 'Target speed (%)', 'Custom AQI limit', 'Away · cooldown',
)
CONFIG_KEY_TOKEN = re.compile(r'\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b')
# Native HVAC mode identifiers are legitimate technical names. Other uppercase
# configuration IDs must not leak into translated prose or field captions.
NATIVE_MODES = {'FAN_ONLY', 'HEAT_COOL'}


english_object = json.loads((SRC / 'translations/en.json').read_text(encoding='utf-8'))
english = flatten(english_object)
assert json.loads((SRC / 'strings.json').read_text(encoding='utf-8')) == english_object, 'Canonical strings.json drift'
files = sorted((SRC / 'translations').glob('*.json'))
assert len(files) == 38
LANGUAGE_AUTONYMS = {
    f'selector.output_language.options.{code}': label
    for code, label in english_object['selector']['output_language']['options'].items()
    if code != 'auto'
}
assert len(LANGUAGE_AUTONYMS) == len(files), 'Language selector must cover every locale'
assert len(set(LANGUAGE_AUTONYMS.values())) == len(files), 'Language choices must remain distinct'

# Technical identifiers, established names and a delegated HA common reference.
INTERNATIONAL = {
    'Home Environment Manager', 'PID · {channel}IMC λ', 'PID', 'IMC / λ',
    'Cohen-Coon', 'US EPA AQI (0-500)', 'EEA AQI (1-6)',
    '[%key:common::config_flow::abort::already_configured%]',
}
# These are valid native words, not untranslated English. Limit each exception
# to the languages where it was reviewed instead of accepting it globally.
COGNATES = {
    'Eco': {'es', 'nl', 'pt', 'pt-BR', 'ro', 'sv'},
    'Manual': {'es', 'id', 'pt', 'pt-BR', 'ro'},
    'Manual Kp/Ki/Kd': {'es', 'id', 'pt', 'pt-BR', 'ro'},
    'Action': {'fr'}, 'Comfort': {'it', 'nl'}, 'Fan': {'tr'},
}
room_steps = ('environment_room_air', 'environment_room_exposure',
              'environment_room_comfort', 'pid_room', 'pid_tuning')

for file in files:
    locale = file.stem
    values = flatten(json.loads(file.read_text(encoding='utf-8')))
    assert values.keys() == english.keys(), (locale, 'key mismatch')
    for key, label in LANGUAGE_AUTONYMS.items():
        assert values[key] == label, (locale, key, 'language choice must retain its autonym')
    for key, value in values.items():
        assert isinstance(value, str) and value.strip(), (locale, key, 'empty/non-string')
        assert placeholders(value) == placeholders(english[key]), (locale, key, 'placeholder mismatch')
        if locale != 'en' and value == english[key]:
            assert (key in LANGUAGE_AUTONYMS or value in INTERNATIONAL
                    or locale in COGNATES.get(value, set())), (
                locale, key, 'untranslated English UI text', value)
        if locale != 'en':
            assert not any(token in value for token in RAW_LABEL_RESIDUE), (
                locale, key, 'legacy raw English label fragment', value)
            leaked_keys = set(CONFIG_KEY_TOKEN.findall(value)) - set(CONFIG_KEY_TOKEN.findall(english[key])) - NATIVE_MODES
            assert not leaked_keys, (locale, key, 'untranslated configuration key', sorted(leaked_keys))
            if english[key] in repaired_forms:
                assert value == repaired_forms[english[key]][locale], (locale, key, 'form meaning lost')
            is_help = ('.data_description.' in key or '.menu_option_descriptions.' in key
                       or key.endswith('.description'))
            if is_help and english[key] in audited_sources:
                assert value == approved_help[english[key]][locale], (
                    locale, key, 'audited explanation differs from complete authored meaning')
            if is_help and (english[key] in approved_help):
                if english[key] == room_selector_review['source']:
                    review = room_selector_review['locales'][locale]
                    assert value == review['approved_text'], (locale, key)
                assert help_fingerprint(key, value, values) not in rejected_templates.get(locale, []), (
                    locale, key, 'generic label template replaced the actual explanation', value)
    for section in ('config', 'options'):
        for step in room_steps:
            assert '{area_name}' in values[f'{section}.step.{step}.title'], (locale, step)

# Checked-in authoring resources must reproduce the shipped files without any
# scratch directory, network request, or additional translation step.
result = builder['build'](check=True)
assert result['status_codes'] == 419
print('HEM_NATIVE_TRANSLATION_COVERAGE_ALL_38_LANGUAGES=PASS')
