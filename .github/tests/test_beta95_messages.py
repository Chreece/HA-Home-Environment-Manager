"""Beta95: localized notification wording, with no invented indoor air quality.

Exercise the production message module against small Recommendation fixtures;
the full locale extension is loaded along with the original three languages.
"""
from __future__ import annotations
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N

root=Path(__file__).resolve().parents[2]
package=ModuleType('hem_beta95_messages')
package.__path__=[str(root)]
sys.modules[package.__name__]=package
messages=importlib.import_module(package.__name__+'.messages')
announce=messages.announcement
explain=messages.explain
for lang in ('en','de','el','fr'):
    for code in ('air_refresh_wake','air_refresh_return',
                 'window_heat_loss','window_cooling_loss'):
        value='20.7 °C / 20.0 °C' if code=='window_heat_loss' else '24.3 °C / 25.0 °C'
        rec=N(area_name='Badezimmer',
              action='open' if code.startswith('air_refresh') else 'close',
              windows=(N(name='Bathroom Window', opened=code.startswith('window_')),),
              reasons=(N(code=code,value=value,label=''),))
        title,body=announce(rec,lang)
        assert title and body and 'Badezimmer' in body,(lang,code,title,body)
        assert not ('CO₂' in body or 'measured indoor CO2' in body)
        if code.startswith('window_'):
            assert 'Bathroom Window' in body and value in body,(lang,code,body)
            assert value in explain(rec.reasons[0],lang)
        else:
            assert 'Bathroom Window' not in body
            assert any(term in body.casefold() for term in (
                'sensor','αισθητήρα','measured','measurement','μέτρηση','mesur')), (lang,code,body)
        if lang=='el':
            assert any('\u0370'<=c<='\u03ff' for c in title)
        if lang=='de':
            assert 'Fenster' in title or 'Frischluft' in title
        if lang=='fr':
            assert title in messages.ROOM_VENTILATION_TEXT['fr'].values()
            assert title not in messages.ROOM_VENTILATION_TEXT['en'].values()
print('BETA95_HUB_NOTIFICATION_WAKE_ENERGY_LOCALIZED_NO_FAKE_POLLUTANTS=PASS')
