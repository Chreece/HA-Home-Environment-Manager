"""Synchronize reviewed additions without rewriting unrelated README content."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / '.github/localization/readme_updates.json').read_text())['translations']
SCOPES = 'different-settings-for-the-home-each-room-and-each-device'
VENTILATION = 'ventilation-advice-windows-doors-and-shading'
REWRITTEN = {'en', 'el', 'de', 'fr', 'es'}


def marker(key: str) -> str:
    return f'<!-- HEM-I18N:{key} -->'


def section(page: str, anchor: str) -> tuple[int, int, str]:
    start = page.index(f'<a id="{anchor}"></a>')
    end = page.find('<a id="', start + 10)
    end = len(page) if end < 0 else end
    return start, end, page[start:end]


def update(locale: str, page: str) -> str:
    text = CATALOG[locale]
    if locale == 'en':
        for key in ('levels', 'aqi', 'balcony'):
            value = text[key]
            prefix = '- ' if key != 'levels' else ''
            expected = prefix + value
            assert page.count(expected) == 1, (locale, key, 'English source changed; update all language variants')
            # The marker records the paragraph identity, never a translated token.
            line = expected + ' ' + marker(key)
            page = page.replace(expected + ' ' + marker(key), expected)
            page = page.replace(expected, line)
        return page

    start, end, block = section(page, SCOPES)
    paragraphs = block.strip().split('\n\n')
    assert paragraphs[-1] and not paragraphs[-1].startswith(('#', '|', '<')), (locale, 'settings paragraph')
    paragraphs[-1] = text['levels'] + ' ' + marker('levels')
    page = page[:start] + '\n\n'.join(paragraphs) + '\n\n\n' + page[end:]

    start, end, block = section(page, VENTILATION)
    lines = [line for line in block.splitlines() if marker('aqi') not in line and marker('balcony') not in line]
    indexes = [i for i, line in enumerate(lines) if line.startswith('- ')]
    assert len(indexes) == 5, (locale, 'Unexpected ventilation section; review the source update')
    lines.insert(indexes[1] + 1, '- ' + text['balcony'] + ' ' + marker('balcony'))
    lines.insert(indexes[0] + 1, '- ' + text['aqi'] + ' ' + marker('aqi'))
    page = page[:start] + '\n'.join(lines) + '\n' + page[end:]

    if locale not in REWRITTEN:
        warning = '> ⚠️ ' + text['warning']
        page, count = re.subn(
            r'(<!-- HEM-TRANSLATION-UNREVIEWED-START -->\n).*?(\n<!-- HEM-TRANSLATION-UNREVIEWED-END -->)',
            lambda match: match[1] + warning + match[2], page, flags=re.S)
        assert count == 1, (locale, 'review notice')
    return page


def main() -> None:
    locales = {p.stem for p in (ROOT / 'custom_components/environment_manager/translations').glob('*.json')}
    assert set(CATALOG) == locales and len(locales) == 38
    changed = 0
    for locale in sorted(locales):
        path = ROOT / ('README.md' if locale == 'en' else f'docs/i18n/README.{locale}.md')
        old = path.read_text()
        new = update(locale, old)
        if new != old:
            path.write_text(new)
            changed += 1
    print(f'PASS: synchronized 38 README languages; {changed} files updated')


if __name__ == '__main__':
    main()
