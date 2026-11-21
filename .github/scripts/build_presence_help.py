"""Build complete presence/arrival/Eco explanations from local authoring data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / '.github/translations'
CATALOGS = ROOT / 'custom_components/environment_manager/translations'
OUTPUT = ROOT / '.github/localization/presence_help.json'


def build(check=False, memory_output=None):
    sources = json.loads((DATA / 'presence_help_sources.json').read_text(encoding='utf-8'))
    locales = {path.stem for path in CATALOGS.glob('*.json')}
    missing = locales - {'en', 'el', 'de'}
    expected_fields = [set(), set(), set(), {'away'}, set(), {'home'}, {'eco'}, {'away', 'home'}]
    assert len(sources) == len(expected_fields)
    output = {source['en']: {'en': source['en'], **source['existing']} for source in sources}
    seen = set()
    for line in (DATA / 'presence_help_locales.txt').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        locale, *values = line.split('|')
        assert locale in missing and locale not in seen, locale
        seen.add(locale)
        assert len(values) == len(sources) and all(values), (locale, len(values))
        profiles = json.loads((CATALOGS / f'{locale}.json').read_text(encoding='utf-8'))
        profiles = profiles['entity']['select']['area_manual_profile']['state']
        for source, template, fields in zip(sources, values, expected_fields):
            assert set(re.findall(r'\{([^}]+)\}', template)) == fields, (locale, source['en'])
            text = template.format(**profiles)
            assert not re.findall(r'\{[^}]+\}', text), (locale, source['en'])
            assert text != source['en'], (locale, source['en'])
            for number in re.findall(r'\b\d+\b', source['en']):
                assert number in text, (locale, number, source['en'])
            output[source['en']][locale] = text
    assert seen == missing, missing - seen
    assert all(messages.keys() == locales for messages in output.values())
    serialized = json.dumps(output, ensure_ascii=False, indent=2) + '\n'
    if check:
        assert OUTPUT.read_text(encoding='utf-8') == serialized, 'Presence-help output is stale'
    else:
        OUTPUT.write_text(serialized, encoding='utf-8')
    if memory_output:
        Path(memory_output).write_text(serialized, encoding='utf-8')
    print(json.dumps({'messages': len(output), 'locales': len(locales), 'new_translations': len(output) * len(missing)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--memory-output')
    args = parser.parse_args()
    build(args.check, args.memory_output)
