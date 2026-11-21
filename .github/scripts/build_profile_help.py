"""Expand fully localized profile-help templates into exact-source messages.

The repeated permission disclaimer is authored once per locale.  Profile names
come from the native catalog, and the occupied-room qualification is retained
for the Comfort profile. This is a build-time tool, never a runtime fallback.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / '.github/translations'
CATALOGS = ROOT / 'custom_components/environment_manager/translations'
OUTPUT = ROOT / '.github/localization/backend_profile_help.json'


def build(check=False, memory_output=None):
    sources = json.loads((DATA / 'profile_help_sources.json').read_text(encoding='utf-8'))
    locales = {path.stem for path in CATALOGS.glob('*.json')}
    missing = locales - {'en', 'el', 'de'}
    templates = {}
    for line in (DATA / 'profile_help_locales.txt').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        locale, *values = line.split('|')
        assert locale not in templates and len(values) == 5, (locale, len(values))
        assert all(values), locale
        assert all(value.count('{profile}') == 1 for value in values[:3]), locale
        templates[locale] = values
    assert templates.keys() == missing, (missing - templates.keys(), templates.keys() - missing)
    profiles = {
        locale: json.loads((CATALOGS / f'{locale}.json').read_text(encoding='utf-8'))
        ['entity']['select']['area_manual_profile']['state']
        for locale in missing
    }
    output = {}
    for english, spec in sources.items():
        messages = {'en': english, **spec['existing']}
        index = {'cool': 0, 'heat': 1, 'humidity': 2}[spec['kind']]
        for locale in sorted(missing):
            row = templates[locale]
            profile = profiles[locale][spec['profile']]
            if spec['profile'] == 'comfort':
                profile += f' ({row[4]})'
            messages[locale] = row[index].format(profile=profile) + ' ' + row[3]
        assert messages.keys() == locales, english
        for locale, text in messages.items():
            assert '{profile}' not in text, (locale, english)
            assert ('°C' in text) == ('°C' in english), (locale, english)
            assert ('%' in text) == ('%' in english), (locale, english)
            assert locale == 'en' or text != english, (locale, english)
        output[english] = messages
    serialized = json.dumps(output, ensure_ascii=False, indent=2) + '\n'
    if check:
        assert OUTPUT.read_text(encoding='utf-8') == serialized, 'Profile help output is stale'
    else:
        OUTPUT.write_text(serialized, encoding='utf-8')
    if memory_output:
        Path(memory_output).write_text(serialized, encoding='utf-8')
    print(json.dumps({'messages': len(output), 'locales': len(locales)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--memory-output')
    args = parser.parse_args()
    build(args.check, args.memory_output)
