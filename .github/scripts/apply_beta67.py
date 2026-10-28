"""Build the narrow AQI recovery release on the known pre-Beta66 source.

Run only in development/CI, never inside Home Assistant. Runtime code uses
in-memory locale constants. No automatic schema migration or service calls.
"""
from pathlib import Path
import ast
import json
import pprint

ROOT = Path(__file__).resolve().parents[2]


def patch(name, old, new):
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    assert text.count(old) == 1, (name, "unexpected baseline", old[:100], text.count(old))
    path.write_text(text.replace(old, new), encoding="utf-8")


patch('device_controls.py', 'AQI_SCALES = ("not_configured", "us_epa", "eea_category", "custom")',
      'from .aqi_sources import AQI_SCALES')
path = ROOT/'device_controls.py'
text = path.read_text()
a = text.index('def configured_aqi_entities(')
b = text.index('\n\ndef _finite(', a)
text = text[:a] + '''def configured_aqi_entities(manager: Any) -> tuple[str, ...]:
    """Selected AQI inventory is independent of provider startup ordering."""
    from .aqi_sources import configured_sources
    return configured_sources(manager.hass, manager.settings)
''' + text[b:]
path.write_text(text)
patch('device_controls.py', '                if value == "not_configured":\n                    scales.pop(entity_id, None)',
      '                if value == "auto":\n                    scales.pop(entity_id, None)')

patch('environment_extended.py', '''def global_aqi(reading: Any, profile: dict) -> dict:
    selectors = profile.get("aqi_scales", {})
    entry = selectors.get(reading.entity_id, {}) if isinstance(selectors, dict) else {}
    scale = entry.get("scale") if isinstance(entry, dict) else entry
    limit = entry.get("custom_limit") if isinstance(entry, dict) else None
    return aqi_category(reading.value, scale, custom_limit=limit)''', '''def global_aqi(reading: Any, profile: dict, *, hass: Any = None) -> dict:
    from .aqi_sources import resolve_scale
    evidence = resolve_scale(hass, profile, reading.entity_id)
    result = aqi_category(reading.value, evidence["scale"],
                          custom_limit=evidence.get("custom_limit"))
    return {**result, "scale_source": evidence["scale_source"]}''')
patch('manager.py', '                aqi = global_aqi(item, environment_global)',
      '                aqi = global_aqi(item, environment_global, hass=self.hass)')

patch('select.py', '''    async_add_grouped_entities(entry.runtime_data, async_add_entities, entities)
    register_late_capabilities(''', '''    async_add_grouped_entities(entry.runtime_data, async_add_entities, entities)
    from .aqi_sources import register_late_sources
    register_late_sources(manager, entry, async_add_entities, entities,
        lambda source: ConfigSelect(manager, entry.entry_id, None, "aqi_scale", AQI_SCALES,
                                     setting_key="scale", entity_id=source))
    register_late_capabilities(''')
patch('select.py', '''            self._attr_name = f"{entity_id} · {self._setting_key.replace('_', ' ')}"''', '''            self._attr_name = f"{entity_id} · {self._setting_key.replace('_', ' ')}"
            if kind == "aqi_scale":
                self._attr_translation_key = "home_aqi_scale"
                self._attr_has_entity_name = False
                self._attr_icon = "mdi:air-filter"''')
patch('select.py', '''            return cfg.get("scale", "not_configured") if isinstance(cfg, dict) else "not_configured"''', '''            from .aqi_sources import scale_selection
            return scale_selection(env, self._entity_id)''')
# Insert only into ConfigSelect, not native device selectors.
path=ROOT/'select.py';text=path.read_text()
a=text.index('    @property\n    def current_option(self):', text.index('class ConfigSelect('))
new='''    @property
    def name(self):
        if self._kind == "aqi_scale":
            from .aqi_sources import control_name
            return control_name(self._manager, self._entity_id, "scale")
        return super().name

    @property
    def extra_state_attributes(self):
        if self._kind == "aqi_scale":
            from .aqi_sources import resolve_scale
            profile = self._manager.settings.get("environment_global", {})
            return {"aqi_source_entity_id": self._entity_id,
                    **resolve_scale(self._manager.hass, profile, self._entity_id)}
        return super().extra_state_attributes

'''
if '"aqi_source_entity_id": self._entity_id' not in text:
    path.write_text(text[:a]+new+text[a:])

patch('number.py', '''    async_add_grouped_entities(entry.runtime_data, async_add_entities, numbers)
''', '''    async_add_grouped_entities(entry.runtime_data, async_add_entities, numbers)
    from .aqi_sources import register_late_sources
    register_late_sources(manager, entry, async_add_entities, numbers,
        lambda source: ConfigNumber(manager, entry.entry_id, None, "aqi_limit",
            "custom_limit", (0.0, 10000.0, 1.0, None), entity_id=source))
''')
patch('number.py', '''            self._attr_name = f"{entity_id} · {key.replace('_', ' ')}"''', '''            self._attr_name = f"{entity_id} · {key.replace('_', ' ')}"
            if kind == "aqi_limit":
                self._attr_has_entity_name = False''')
path=ROOT/'number.py';text=path.read_text()
a=text.index('    def _sync_room_limit_bounds(',text.index('class ConfigNumber('))
new='''    @property
    def name(self):
        if self._kind == "aqi_limit":
            from .aqi_sources import control_name
            return control_name(self._manager, self._entity_id, "limit")
        return super().name

'''
if 'return control_name(self._manager, self._entity_id, "limit")' not in text:
    path.write_text(text[:a]+new+text[a:])

patch('compact_options.py', 'menu_options=["weather", "outdoor", "pollen"],',
      'menu_options=["weather", "outdoor", "outside_aqi", "pollen"],')
path=ROOT/'compact_options.py';text=path.read_text()
a=text.index('        selected = self._values.get(CONF_OUTDOOR, [])', text.index('async def async_step_outside_aqi'))
b=text.index('        errors = {}',a)
text=text[:a]+'''        from .aqi_sources import configured_sources, source_name, scale_selection
        aqis = list(configured_sources(self.hass, self._values))
'''+text[b:]
text=text.replace('details.get("scale", "not_configured")','scale_selection(current, chosen)')
text=text.replace('details.get("scale","not_configured")','scale_selection(current, chosen)')
text=text.replace('"not_configured", "us_epa", "eea_category", "custom"','"auto", "not_configured", "us_epa", "eea_category", "custom"')
text=text.replace('["not_configured","us_epa","eea_category","custom"]','["auto","not_configured","us_epa","eea_category","custom"]')
text=text.replace('                if scale == "not_configured":','                if scale == "auto":')
text=text.replace('{"value":e,"label":e} for e in aqis]','{"value":e,"label":source_name(self.hass, e)} for e in aqis]')
path.write_text(text)

labels={}
for row in (ROOT/'.github/patches/aqi67.tsv').read_text().splitlines():
    lang, *values=row.split('|')
    assert len(values)==5
    labels[lang]=dict(zip(('scale','limit','auto','not_configured','custom'),values))
assert set(labels)=={p.stem.lower() for p in (ROOT/'translations').glob('*.json')}
(ROOT/'aqi_names.py').write_text('"""Bundled AQI configuration labels; no runtime filesystem reads."""\nAQI_NAMES = '+pprint.pformat(labels,width=105,sort_dicts=False)+'\n')
for path in [ROOT/'strings.json', *sorted((ROOT/'translations').glob('*.json'))]:
    lang='en' if path.name=='strings.json' else path.stem.lower()
    data=json.loads(path.read_text()); t=labels[lang]
    choices={'auto':t['auto'],'not_configured':t['not_configured'],
             'us_epa':'US EPA AQI (0-500)','eea_category':'EEA AQI (1-6)','custom':t['custom']}
    data.setdefault('selector',{}).setdefault('outside_aqi_scale',{})['options']=choices
    data['entity']['select']['home_aqi_scale']={'name':t['scale'],'state':choices}
    # Existing source-aware options form is now reachable from its menu.
    for kind in ('options','config'):
        step=data.get(kind,{}).get('step',{})
        if 'outside_aqi' in step:
            step['outside_aqi']['data']['outside_aqi_scale']=t['scale']
            step['outside_aqi']['data']['outside_aqi_limit']=t['limit']
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
meta=json.loads((ROOT/'manifest.json').read_text())
assert meta['domain']=='environment_manager'
meta['version']='0.6.0b67'
(ROOT/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
print('PASS Beta67 recovery AQI edits, explicit registry-provider detection, 38 localized controls')
