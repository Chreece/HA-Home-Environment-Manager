"""Guard source additions, actual localized paragraphs and untranslated notices."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / '.github/localization/readme_updates.json').read_text())['translations']
LOCALES = {p.stem for p in (ROOT / 'custom_components/environment_manager/translations').glob('*.json')}
REWRITTEN = {'en', 'el', 'de', 'fr', 'es'}
assert set(CATALOG) == LOCALES and len(LOCALES) == 38
SOURCE = (ROOT / 'README.md').read_text()

for locale, entries in CATALOG.items():
    page = SOURCE if locale == 'en' else (ROOT / f'docs/i18n/README.{locale}.md').read_text()
    for key in ('levels', 'aqi', 'balcony'):
        marker = f'<!-- HEM-I18N:{key} -->'
        matches = [line for line in page.splitlines() if marker in line]
        assert len(matches) == 1, (locale, key, 'missing or duplicated content')
        expected = ('- ' if key != 'levels' else '') + entries[key] + ' ' + marker
        assert matches[0] == expected, (locale, key, 'catalog/source drift')
        assert entries[key].strip(), (locale, key, 'blank')
        if locale != 'en':
            assert entries[key] != CATALOG['en'][key], (locale, key, 'English copy')
    assert 'AQI' in entries['aqi'], locale
    assert '`door`' in entries['balcony'] and '`opening`' in entries['balcony'], locale
    assert 'PID' in entries['levels'] and re.search(r'Home[ -]Assistant', entries['levels']), locale
    assert len(entries['level_labels']) == 3, locale
    assert all('**' + label + '**' in entries['levels'] for label in entries['level_labels']), locale
    if locale not in REWRITTEN:
        notice = re.search(r'HEM-TRANSLATION-UNREVIEWED-START -->\n(.*?)\n<!-- HEM-TRANSLATION-UNREVIEWED-END', page, re.S)[1]
        assert notice == '> ⚠️ ' + entries['warning'], locale
        assert entries['warning'] != CATALOG['en']['warning'], (locale, 'English-only review notice')
        assert 'href="../../README.md"' in notice, locale
    if locale != 'en':
        block = page.split('<a id="ventilation-advice-windows-doors-and-shading"></a>', 1)[1].split('<a id="', 1)[0]
        english = SOURCE.split('### Ventilation advice, windows, doors and shading', 1)[1].split('\n### ', 1)[0]
        assert len(re.findall(r'^- ', block, re.M)) == len(re.findall(r'^- ', english, re.M)), (locale, 'ventilation content drift')

print('PASS: all 38 README languages include settings levels, optional AQI and balcony-door inputs; review notices are localized')
