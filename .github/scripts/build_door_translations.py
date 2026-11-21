"""Build complete door labels/help from checked-in, locale-specific sentences."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / '.github/translations'
CATALOGS = ROOT / 'custom_components/environment_manager/translations'
OUTPUT = ROOT / '.github/localization'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build(check=False, frontend_only=False, frontend_memory_output=None, backend_memory_output=None):
    spec = read(DATA / 'door_sources.json')
    sources = spec['frontend'] + spec['backend']
    groups = read(DATA / 'door_indices.json')
    policies = read(DATA / 'door_policy_labels.json')
    locales = {path.stem for path in CATALOGS.glob('*.json')}
    missing = locales - {'en', 'el', 'de'}
    output = {source['en']: {'en': source['en'], **source['existing']} for source in sources}
    fields_by_index = {
        0: {'eco'}, 4: {'eco'}, 52: {'coordinate'},
        54: {'existing_rule', 'no_coordination'}, 55: {'eco', 'home'},
    }
    covered = set()
    for name, indices in groups.items():
        if frontend_only and name == 'backend_help':
            continue
        path = DATA / f'door_{name}_locales.txt'
        seen = set()
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line or line.startswith('#'):
                continue
            locale, *values = line.split('|')
            assert locale in missing and locale not in seen, (path, locale)
            seen.add(locale)
            assert len(values) == len(indices) and all(values), (path, locale, len(values))
            profiles = read(CATALOGS / f'{locale}.json')['entity']['select']['area_manual_profile']['state']
            replacements = {**profiles,
                            'coordinate': policies['Coordinate starts'][locale],
                            'existing_rule': policies["Use each door's existing rule"][locale],
                            'no_coordination': policies['No coordination'][locale]}
            for index, template in zip(indices, values):
                assert set(re.findall(r'\{([^}]+)\}', template)) == fields_by_index.get(index, set()), (path, locale, index)
                text = template.format(**replacements).replace(' ¶ ', '\n\n')
                english = sources[index]['en']
                assert text != english, (path, locale, index)
                assert not re.findall(r'\{[^}]+\}', text), (path, locale, index)
                for number in re.findall(r'\b\d+\b', english):
                    assert number in text, (path, locale, index, number)
                for token in ('CO₂', 'HEM', 'Wh/kWh/MWh', 'total_increasing'):
                    assert token not in english or token in text, (path, locale, index, token)
                assert text.count('\n\n') == english.count('\n\n'), (path, locale, index, 'paragraphs')
                output[english][locale] = text
        assert seen == missing, (path, missing - seen)
        assert not covered.intersection(indices), name
        covered.update(indices)
    assert covered == set(range(52 if frontend_only else len(sources)))
    for section, rows, memory_output in [
        ('frontend', spec['frontend'], frontend_memory_output),
        ('backend', spec['backend'], backend_memory_output),
    ]:
        if frontend_only and section == 'backend':
            continue
        messages = {row['en']: output[row['en']] for row in rows}
        assert all(values.keys() == locales for values in messages.values())
        serialized = json.dumps(messages, ensure_ascii=False, indent=2) + '\n'
        destination = OUTPUT / f'door_{section}.json'
        if check:
            assert destination.read_text(encoding='utf-8') == serialized, f'{section} door output is stale'
        else:
            destination.write_text(serialized, encoding='utf-8')
        if memory_output:
            Path(memory_output).write_text(serialized, encoding='utf-8')
        print(json.dumps({'section': section, 'sources': len(messages), 'locales': len(locales)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--frontend-only', action='store_true')
    parser.add_argument('--frontend-memory-output')
    parser.add_argument('--backend-memory-output')
    args = parser.parse_args()
    build(args.check, args.frontend_only, args.frontend_memory_output, args.backend_memory_output)
