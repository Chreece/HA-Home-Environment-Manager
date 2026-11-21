"""Build complete presence/freshness selector explanations from local sources."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / '.github/translations'
CATALOGS = ROOT / 'custom_components/environment_manager/translations'
OUTPUT = ROOT / '.github/localization/presence_options.json'


def write_atomic(path, serialized):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(serialized, encoding='utf-8')
    temporary.replace(path)


def build(check=False, memory_output=None):
    sources = json.loads((DATA / 'presence_option_sources.json').read_text(encoding='utf-8'))
    locales = {path.stem for path in CATALOGS.glob('*.json')}
    missing = locales - {'en', 'el', 'de'}
    fields = [{'home', 'away'}, {'home', 'away', 'any_home'}, set(), set(), set(), set(), {'home'}, set()]
    assert len(sources) == len(fields)
    output = {source['en']: {'en': source['en'], **source['existing']} for source in sources}
    seen = set()
    for line in (DATA / 'presence_option_locales.txt').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        locale, *values = line.split('|')
        assert locale in missing and locale not in seen, locale
        seen.add(locale)
        assert len(values) == len(sources) and all(values), (locale, len(values))
        native = json.loads((CATALOGS / f'{locale}.json').read_text(encoding='utf-8'))
        replacements = {**native['entity']['select']['area_manual_profile']['state'],
                        'any_home': native['selector']['general_home_policy']['options']['any_home']}
        for source, template, expected in zip(sources, values, fields):
            assert set(re.findall(r'\{([^}]+)\}', template)) == expected, (locale, source['en'])
            text = template.format(**replacements)
            assert text != source['en'] and not re.findall(r'\{[^}]+\}', text), (locale, source['en'])
            output[source['en']][locale] = text
    assert seen == missing, missing - seen
    assert all(messages.keys() == locales for messages in output.values())
    serialized = json.dumps(output, ensure_ascii=False, indent=2) + '\n'
    if check:
        assert OUTPUT.read_text(encoding='utf-8') == serialized, 'Presence-option output is stale'
    else:
        write_atomic(OUTPUT, serialized)
    if memory_output:
        write_atomic(Path(memory_output), serialized)
    print(json.dumps({'messages': len(output), 'locales': len(locales), 'new_translations': len(output) * len(missing)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--memory-output')
    args = parser.parse_args()
    build(args.check, args.memory_output)
