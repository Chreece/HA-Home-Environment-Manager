"""Compile complete PID explanations into a static exact-source memory.

All authoring inputs are checked in. This script does not invent fallback text,
translate at runtime, or require any network or scratch directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / '.github/translations'
CATALOGS = ROOT / 'custom_components/environment_manager/translations'
OUTPUT = ROOT / '.github/localization/pid_reasons.json'


def build(check=False, memory_output=None):
    sources = json.loads((DATA / 'pid_reason_sources.json').read_text(encoding='utf-8'))
    locales = {path.stem for path in CATALOGS.glob('*.json')}
    missing = locales - {'en', 'el', 'de'}
    assert len(sources) == 90
    assert len({source['english'] for source in sources}) == len(sources)
    output = {source['english']: {'en': source['english'], **source['translations']}
              for source in sources}
    covered = set()
    for path in sorted((DATA / 'pid_reason_locales').glob('*.txt')):
        start = int(path.stem)
        batch = sources[start:start + 30]
        assert len(batch) == 30 and not (covered & set(range(start, start + 30))), path
        covered.update(range(start, start + 30))
        seen = set()
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line or line.startswith('#'):
                continue
            locale, *values = line.split('|')
            assert locale not in seen and locale in missing, (path, locale)
            seen.add(locale)
            assert len(values) == len(batch) and all(values), (path, locale, len(values))
            for source, text in zip(batch, values):
                english = source['english']
                assert text != english, (path, locale, english)
                assert set(re.findall(r'\{[^}]+\}', text)) == set(re.findall(r'\{[^}]+\}', english)), (path, locale, english)
                assert '48' not in english or '48' in text, (path, locale, english)
                assert 'HEM' not in english or 'HEM' in text, (path, locale, english)
                output[english][locale] = text
        assert seen == missing, (path, missing - seen)
    assert covered == set(range(len(sources))), 'Missing explanation batch'
    assert all(messages.keys() == locales for messages in output.values())
    serialized = json.dumps(output, ensure_ascii=False, indent=2) + '\n'
    if check:
        assert OUTPUT.read_text(encoding='utf-8') == serialized, 'PID explanation output is stale'
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
