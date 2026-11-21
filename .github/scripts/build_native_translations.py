"""Build complete native HA messages from checked-in, reviewed translation sources.

The runtime only reads the resulting translations/*.json. No network, dynamic
translation, language guessing, or fallback message generation is involved.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import re
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'custom_components/environment_manager'
DATA = ROOT / '.github/translations'


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def flatten(value, prefix=()):
    if isinstance(value, dict):
        return {key: leaf for name, child in value.items()
                for key, leaf in flatten(child, prefix + (name,)).items()}
    return {'.'.join(prefix): value}


def assign(value, key, text):
    parts = key.split('.')
    for part in parts[:-1]:
        value = value.setdefault(part, {})
    value[parts[-1]] = text


def placeholders(value):
    return set(re.findall(r'(?<!\{)\{([A-Za-z_][A-Za-z_0-9]*)\}(?!\})', value))


def runtime_catalogs():
    """Read pure presentation catalogs without importing Home Assistant.

    The same setting can appear in a native form and an entity attribute. Its
    checked-in runtime translation is the authority for both presentations.
    This import is only part of the build; generated native JSON stays static.
    """
    package_name = '_hem_native_translation_build'
    if package_name not in sys.modules:
        package = ModuleType(package_name)
        package.__path__ = [str(SRC)]
        sys.modules[package_name] = package
    return (importlib.import_module(package_name + '.settings_name_catalog'),
            importlib.import_module(package_name + '.settings_help'))


def synchronize_setting_metadata(obj, locale, names, help_catalog):
    for domain in ('number', 'select', 'switch', 'button', 'time'):
        for key, entry in obj['entity'][domain].items():
            if key.startswith('equipment_'):
                continue
            translated = names.localized_setting_name(key, locale)
            assert isinstance(translated, str) and translated.strip(), (locale, key)
            entry['name'] = translated
    for flow in ('config', 'options'):
        for step in obj[flow]['step'].values():
            descriptions = step.get('data_description', {})
            if 'general_home_policy' in descriptions:
                translated = help_catalog.configuration_help(
                    'home_global_policy_home_policy', locale)
                assert isinstance(translated, str) and translated.strip(), locale
                descriptions['general_home_policy'] = translated


def parse_rows(path, terms, locales):
    rows = {}
    for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line or line.startswith('#'):
            continue
        locale, *values = line.split('|')
        assert locale not in rows, (path, line_number, 'duplicate locale', locale)
        assert len(values) == len(terms), (path, locale, len(values), len(terms))
        assert all(value.strip() for value in values), (path, locale, 'empty value')
        for source, text in zip(terms, values):
            assert placeholders(source) == placeholders(text), (path, locale, source)
        rows[locale] = dict(zip(terms, values))
    assert rows.keys() == locales, (path, locales - rows.keys(), rows.keys() - locales)
    return rows


def catalog_sources(locales):
    terms = read(DATA / 'native_status_terms.json')
    atom_memory = read(DATA / 'native_status_existing_atoms.json')
    for path in sorted((DATA / 'native_status_locales').glob('*.txt')):
        start = int(path.stem)
        batch = terms[start:start + 80]
        for locale, messages in parse_rows(path, batch, locales).items():
            for source, text in messages.items():
                atom_memory.setdefault(source, {})[locale] = text
    short_terms = read(DATA / 'native_short_terms.json')
    short_rows = parse_rows(DATA / 'native_short_locales.txt', short_terms, locales)
    short_memory = {source: {locale: values[source] for locale, values in short_rows.items()}
                    for source in short_terms}
    patterns = {}
    for line in (DATA / 'native_status_patterns.txt').read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            code, *parts = line.split('|')
            assert code not in patterns, code
            assert parts and all(part in atom_memory for part in parts), (code, parts)
            patterns[code] = parts
    return atom_memory, short_memory, patterns


def form_repair_sources(locales):
    """Read complete replacements for obsolete label-based form templates."""
    sources = read(DATA / 'native_form_repair_sources.json')
    memory = {source: {'en': source} for source in sources}
    seen = set()
    fields = [set(), set(), {'away'}, set(), {'away'}, *[set()] * 7]
    assert len(fields) == len(sources)
    for line in (DATA / 'native_form_repair_locales.txt').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        locale, *values = line.split('|')
        assert locale in locales and locale not in seen, locale
        seen.add(locale)
        assert len(values) == len(sources) and all(values), locale
        profiles = read(SRC / f'translations/{locale}.json')['entity']['select']['area_manual_profile']['state']
        for source, template, expected in zip(sources, values, fields):
            assert placeholders(template) == expected, (locale, source)
            text = template.format(**profiles)
            assert not placeholders(text) and text != source, (locale, source)
            assert ('°C' in text) == ('°C' in source), (locale, source)
            assert ('PID' in text) == ('PID' in source), (locale, source)
            memory[source][locale] = text
    assert seen == locales, locales - seen
    return memory


def build(check=False, memory_output=None):
    names, help_catalog = runtime_catalogs()
    runtime_text = importlib.import_module('_hem_native_translation_build.backend_text_catalog').TEXT
    files = sorted((SRC / 'translations').glob('*.json'))
    locales = {path.stem for path in files} - {'en'}
    assert len(locales) == 37
    # Some old messages shared a generic English source despite describing
    # different actions. Repair those by exact native key, including missing
    # error messages, without changing unrelated uses of the old source.
    keyed = {}
    for source_file in sorted((ROOT / '.github/localization').glob('native_keyed_*.json')):
        for key, variants in read(source_file).items():
            assert all(key.split('.')) and '.' in key, (source_file, key)
            assert set(variants) == locales | {'en'}, (source_file, key, 'incomplete locales')
            assert all(isinstance(value, str) and value.strip()
                       for value in variants.values()), (source_file, key, 'empty translation')
            assert key not in keyed or keyed[key] == variants, (source_file, key, 'conflicting translations')
            keyed[key] = variants
    english = read(SRC / 'translations/en.json')
    synchronize_setting_metadata(english, 'en', names, help_catalog)
    for key, variants in keyed.items():
        assign(english, key, variants['en'])
    english_flat = flatten(english)
    # Keep language choices recognizable even when the UI uses a different
    # language. These are autonyms, not English fallback text to translate.
    language_autonyms = {
        f'selector.output_language.options.{code}': label
        for code, label in english['selector']['output_language']['options'].items()
        if code != 'auto'
    }
    atoms, short, patterns = catalog_sources(locales)
    preserved = read(DATA / 'native_status_existing_labels.json')
    exact = read(DATA / 'native_exact_fixes.json')
    prose = read(ROOT / '.github/localization/native_help.json')
    forms = form_repair_sources(locales)
    final_terms = read(DATA / 'native_final_label_sources.json')
    final_rows = parse_rows(DATA / 'native_final_label_locales.txt', final_terms, locales)
    forms.update({source: {'en': source, **{locale: values[source]
                  for locale, values in final_rows.items()}} for source in final_terms})
    residual = {}
    for source_file in sorted((ROOT / '.github/localization').glob('native_residual_*.json')):
        for source, variants in read(source_file).items():
            assert set(variants) == locales | {'en'}, (source_file, source, 'incomplete locales')
            assert variants['en'] == source, (source_file, source, 'changed English source')
            assert source not in residual or residual[source] == variants, (source_file, source, 'conflicting translations')
            residual[source] = variants
    status_source = english['entity']['sensor']['equipment_control_status']['state']
    assert patterns.keys() == status_source.keys()
    memory = {}
    changed_files = []
    changed_values = 0
    form_output = ROOT / '.github/localization/native_forms.json'
    if not form_output.exists() or read(form_output) != forms:
        changed_files.append(str(form_output.relative_to(ROOT)))
        if not check:
            write(form_output, forms)
    for path in files:
        locale = path.stem
        if locale == 'en':
            original = read(path)
            if original != english:
                changed_files.append(str(path.relative_to(ROOT)))
                changed_values += sum(flatten(original).get(key) != value
                                      for key, value in english_flat.items())
                if not check:
                    write(path, english)
            continue
        obj = read(path)
        before = flatten(obj)
        states = obj['entity']['sensor']['equipment_control_status']['state']
        for code, parts in patterns.items():
            if code in preserved[locale]:
                states[code] = preserved[locale][code]
            else:
                translated = [atoms[part][locale] for part in parts]
                states[code] = ': '.join(translated)
        for key, source in english_flat.items():
            if key.startswith('entity.sensor.equipment_control_status.state.'):
                continue
            if key in keyed:
                assign(obj, key, keyed[key][locale])
            elif key in language_autonyms:
                assign(obj, key, language_autonyms[key])
            elif source in forms:
                assign(obj, key, forms[source][locale])
            elif source in residual:
                assign(obj, key, residual[source][locale])
            elif (source in runtime_text and ('.data_description.' in key
                    or '.menu_option_descriptions.' in key or key.endswith('.description'))):
                assign(obj, key, runtime_text[source][locale])
            elif source in prose:
                assign(obj, key, prose[source][locale])
            elif source in short:
                assign(obj, key, short[source][locale])
            elif key in exact['targets'] and locale in exact['sources'][source]:
                assign(obj, key, exact['sources'][source][locale])
            elif re.fullmatch(r'(config.step.reconfigure|options.step.init).menu_options.room_\d+', key):
                parameter = next(iter(placeholders(source)))
                assign(obj, key, short['Settings · {area_name}'][locale].replace('{area_name}', '{' + parameter + '}'))
        synchronize_setting_metadata(obj, locale, names, help_catalog)
        for key, variants in keyed.items():
            assign(obj, key, variants[locale])
        after = flatten(obj)
        assert after.keys() == english_flat.keys(), locale
        for key, value in after.items():
            assert isinstance(value, str) and value.strip(), (locale, key)
            assert placeholders(value) == placeholders(english_flat[key]), (locale, key, value)
            if value != english_flat[key]:
                memory.setdefault(english_flat[key], {}).setdefault(locale, value)
        if after != before:
            changed_files.append(str(path.relative_to(ROOT)))
            changed_values += sum(before.get(key) != value for key, value in after.items())
            if not check:
                write(path, obj)
    master = SRC / 'strings.json'
    if read(master) != english:
        changed_files.append(str(master.relative_to(ROOT)))
        if not check:
            write(master, english)
    if memory_output:
        write(Path(memory_output), memory)
    if check:
        assert not changed_files, f'Native catalogs need regeneration: {changed_files}'
    return {'locales': len(locales) + 1, 'keys_per_locale': len(english_flat),
            'status_codes': len(patterns), 'changed_files': len(changed_files),
            'changed_values': changed_values}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--memory-output', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.check, args.memory_output), ensure_ascii=False))
