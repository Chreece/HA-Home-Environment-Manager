"""Compile the full native controller explanations without runtime translation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / '.github/translations'
SOURCES = DATA / 'native_controller_help_sources.json'
# Positions13–25 are authored in native_residual_permissions.json by the shared
# native-help workstream. This compiler owns the other two complete families.
PARTS = {0: 13, 26: 15}


def build(check=False, memory_output=None, part=None):
    sources = json.loads(SOURCES.read_text(encoding='utf-8'))
    locales = {p.stem for p in (ROOT / 'custom_components/environment_manager/translations').glob('*.json')}
    output = {}
    for start, count in PARTS.items():
        if part is not None and part != start:
            continue
        batch = sources[start:start + count]
        part_output = {}
        rows = {}
        path = DATA / f'native_controller_help_locales/{start:03}.txt'
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line or line.startswith('#'):
                continue
            locale, *texts = line.split('|')
            assert locale not in rows and locale in locales - {'en'}, (path, locale)
            assert len(texts) == count and all(text.strip() for text in texts), (path, locale)
            rows[locale] = texts
        assert rows.keys() == locales - {'en'}, (path, (locales - {'en'}) - rows.keys())
        for index, source in enumerate(batch):
            values = {'en': source['en'], **{locale: row[index] for locale, row in rows.items()}}
            if source['id'] == 29:
                for locale in locales - {'en'}:
                    native = json.loads((ROOT / f'custom_components/environment_manager/translations/{locale}.json').read_text(encoding='utf-8'))
                    modes = native['entity']['select']['equipment_control_mode']['state']
                    presence = native['selector']['device_presence_requirement']['options']
                    labels = {'existing': modes['existing'], 'automatic': modes['automatic'],
                              'always': presence['always'], 'room': presence['room'], 'home': presence['home']}
                    assert set(re.findall(r'\{([^}]+)\}', values[locale])) == labels.keys(), locale
                    values[locale] = values[locale].format(**labels)
            for locale, text in values.items():
                assert locale == 'en' or text != source['en'], (source['id'], locale)
                assert not re.search(r'\{[A-Za-z_][^}]*\}', text), (source['id'], locale)
                for token in ('°C', '%', 'CO₂', 'PM2.5', 'µg/m³', 'PMV/PPD', 'ISO 7730', 'NDIR', 'PID', 'PWM', 'fan.*', 'DRY/FAN_ONLY', 'HEAT_COOL'):
                    if token in source['en']:
                        assert token in text, (source['id'], locale, token)
            output[source['en']] = values
            part_output[source['en']] = values
        serialized = json.dumps(part_output, ensure_ascii=False, indent=2) + '\n'
        target = ROOT / f'.github/localization/native_residual_controllers_{start:03}.json'
        if check:
            assert target.read_text(encoding='utf-8') == serialized, f'Native controller help is stale: {start}'
        else:
            temporary = target.with_suffix('.json.tmp')
            temporary.write_text(serialized, encoding='utf-8')
            temporary.replace(target)
    assert len(output) == (sum(PARTS.values()) if part is None else PARTS[part])
    if memory_output:
        Path(memory_output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'messages': len(output), 'locales': len(locales), 'localized_values': len(output) * (len(locales) - 1)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--memory-output')
    parser.add_argument('--part', type=int, choices=list(PARTS))
    args = parser.parse_args()
    build(args.check, args.memory_output, args.part)
