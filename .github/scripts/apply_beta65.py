"""Apply reviewed Beta65 source edits and bundle locale data; no runtime I/O."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]

def patch(name, old, new):
    path = ROOT / name
    text = path.read_text(encoding='utf-8')
    if old not in text and new in text:
        return
    assert text.count(old) == 1, (name, 'unexpected baseline', old[:100], text.count(old))
    path.write_text(text.replace(old, new), encoding='utf-8')

patch('logic.py', '''    for warning in warnings:
        if warning.active is None:
            outside.append(Reason("unavailable_warning", warning.name))
        elif warning.active:
            outside.append(Reason("active_warning", warning.name))''', '''    # Warning availability is optional evidence, not a weather hazard.
    # Keep the unknown source for diagnostics, but never turn it into an
    # active alert or block unrelated ventilation/climate decisions.
    for warning in warnings:
        if warning.active is True:
            outside.append(Reason("active_warning", warning.name))''')
patch('logic.py', '''    active: bool | None  # None means unavailable / ambiguous => fail closed.''', '''    active: bool | None  # None is unavailable/ambiguous and ignored, not an alert.''')
patch('discovery.py', '''    # HA's unknown/unavailable signals still fail closed.
    if state is None or state.state in ("unknown", "unavailable", "none", ""):
        return Warning(entity_id, state.name if state else entity_id, None)
    lowered = str(state.state).strip().casefold()''', '''    # An unavailable warning source is ignored, not treated as an alert.
    lowered = str(state.state).strip().casefold() if state is not None else ""
    if lowered in ("unknown", "unavailable", "none", "null", ""):
        return Warning(entity_id, state.name if state else entity_id, None)''')
patch('dashboard.py', '''            "warnings": [_warning(item) for item in plan.warnings],''', '''            "warnings": [_warning(item) for item in plan.warnings if item.active is not None],
            "ignored_warning_entities": [item.entity_id for item in plan.warnings
                                         if item.active is None],''')
# The unit itself identifies illuminance; no device-name or brightness-% guess.
patch('discovery.py', '''    if metric == "humidity":
        return value if u in ("", "%") else None''', '''    if metric == "humidity":
        return value if u in ("", "%") else None
    if metric == "illuminance":
        return value if u in ("lx", "lux") else None''')
patch('discovery.py', '''    metric = _metric(hass, state)
    if metric not in (SUPPORTED_AIR_METRICS if outdoor else INDOOR_METRICS):''', '''    unit = str(state.attributes.get("unit_of_measurement", "")).strip().casefold()
    if (not outdoor and state.entity_id.startswith("sensor.")
            and unit in ("lx", "lux")):
        return "illuminance"  # Informational only, never an air-quality limit.
    metric = _metric(hass, state)
    if metric not in (SUPPORTED_AIR_METRICS if outdoor else INDOOR_METRICS):''')
patch('discovery.py', '''    if metric == "humidity" and normalized is not None and not 0 < normalized <= 100:
        normalized = None
    return Reading(entity_id, name, metric, normalized)''', '''    if metric == "humidity" and normalized is not None and not 0 < normalized <= 100:
        normalized = None
    if metric == "illuminance" and normalized is not None and not 0 <= normalized <= 300000:
        normalized = None
    return Reading(entity_id, name, metric, normalized)''')
patch('const.py', '''UNIT_LABEL = {
    "mold": "%",''', '''UNIT_LABEL = {
    "illuminance": "lx",  # Read-only light context, not a ventilation criterion.
    "mold": "%",''')
patch('dashboard.py', '''    known = any(item["available"] for item in readings)
    incomplete_air = any(not item["available"] for item in readings)''', '''    air_readings = [item for item in readings if item["metric"] != "illuminance"]
    known = any(item["available"] for item in air_readings)
    incomplete_air = any(not item["available"] for item in air_readings)''')
patch('logic.py', '''        if not any(reading.value is not None for reading in room.readings) and not indoor_reasons:''', '''        if not any(reading.value is not None and reading.metric != "illuminance"
                   for reading in room.readings) and not indoor_reasons:''')
patch('discovery.py', '''                    by_area_readings[area].append(Reading(entity, entity,
                        "humidity" if group == "humidity" else "unknown", None))''', '''                    registered = er.async_get(hass).async_get(entity)
                    sensor_class = (getattr(registered, "device_class", None)
                                    or getattr(registered, "original_device_class", None))
                    missing_metric = ("humidity" if group == "humidity" else
                                      "illuminance" if sensor_class == "illuminance"
                                      else "unknown")
                    by_area_readings[area].append(Reading(entity, entity, missing_metric, None))''')
# Pick up selected room lux values in the existing informational daylight history.
patch('environment.py', '''        indoor_rh = _single_value(room.readings, "humidity")''', '''        light_sources = [r for r in room.readings if r.metric == "illuminance"]
        if light_sources and not profile.get("illuminance_entity"):
            # This transient report flag never changes persisted selections or
            # gives an actuator any new permission. Missing light is not zero.
            profile = {**profile, "_selected_illuminance": True}
            light_value = _single_value(light_sources, "illuminance")
            if light_value is not None:
                optional_data["lux"] = light_value
            optional_sources["illuminance_entities"] = {
                "entities": [r.entity_id for r in light_sources],
                "valid_count": sum(r.value is not None for r in light_sources),
                "status": "selected_mean" if light_value is not None else "unavailable",
            }
        indoor_rh = _single_value(room.readings, "humidity")''')
patch('environment_extended.py', '''    light = daylight_exposure(samples, now) if profile.get("illuminance_entity") else {"status": "not_configured"}''', '''    light = daylight_exposure(samples, now) if (
        profile.get("illuminance_entity") or profile.get("_selected_illuminance")
    ) else {"status": "not_configured"}''')

patch('equipment_status.py', '''            "area_id": self._spec.area_id,
            "status_code": observed.get("status"),''', '''            "area_id": self._spec.area_id,
            "source_entity_ids": list(self._spec.source_entities),
            "status_code": observed.get("status"),''')

keys = 'overview devices calibration details physical target demand supply cooldown sleep reason lux idle mean partialMean inputs ready unconfigured information save apply gain timeConstant deadTime speed capacity stage waiting summaryHelp luxHelp dataHelp calHelp'.split()
locales = {}
for file in sorted((ROOT / '.github/patches').glob('card65-labels*.tsv')):
    for row in file.read_text().splitlines():
        if not row.strip(): continue
        lang, *values = row.split('|')
        assert len(values) == len(keys), (lang, len(values), len(keys))
        assert lang not in locales
        locales[lang] = dict(zip(keys, values))
for file, fields in [('card65-modes.tsv', ['heat','cool','dry','fan','choose']),
                     ('card65-states.tsv', ['on','off','unknown']),
                     ('card65-extra.tsv', ['legacyStrategy','measuredStrategy','estimateHelp']),
                     ('card65-profiles.tsv',['awayProfile','comfortProfile','ecoProfile'])]:
    for row in (ROOT / '.github/patches' / file).read_text().splitlines():
        lang, *values = row.split('|')
        assert len(values) == len(fields)
        locales[lang].update(zip(fields, values))
expected = {p.stem.lower() for p in (ROOT / 'translations').glob('*.json')}
assert set(locales) == expected, (set(locales) ^ expected)

# Reuse translated HA control/profile states and stable existing status keys.
# New concise labels fill gaps that previously leaked humanized English codes.
compact=json.loads((ROOT/'compact_locales.json').read_text())
import ast
catalog=ast.parse((ROOT/'controller_status_catalog.py').read_text())
visible_codes=set()
for node in catalog.body:
    if isinstance(node,ast.Assign) and any(getattr(t,'id','')=='EQUIPMENT_SENSOR_STATUSES' for t in node.targets):
        visible_codes.update(ast.literal_eval(node.value.args[0]))
visible_codes.update(('home','away','sleep','comfort','eco','selected_mean','selected_sensor',
 'selected_partial_mean','selected_partial_sensor','room_selected_mean','idle','ready',
 'complete_measured_stage_capacities_required','not_configured','environment_only_no_hvac'))
bundle = {}
for p in sorted((ROOT / 'translations').glob('*.json')):
    lang = p.stem.lower()
    t = locales[lang]
    data = json.loads(p.read_text())
    entity = data['entity']
    selection = entity['select']
    codes = entity['sensor']['equipment_control_status']['state']
    additions = {
        'idle':t['idle'], 'selected_mean':t['mean'], 'selected_sensor':t['mean'],
        'selected_partial_mean':t['partialMean'], 'selected_partial_sensor':t['partialMean'],
        'room_selected_mean':t['mean'], 'complete_measured_stage_capacities_required':t['inputs'],
        'ready_to_apply_when_physical_off':t['ready'], 'not_configured':t['unconfigured'],
        'environment_only_no_hvac':t['summaryHelp'], 'environment_only_no_primary_hvac':t['summaryHelp'],
    }
    codes.update(additions)
    profiles={'none':compact[p.stem]['automatic'], 'home':compact[p.stem]['house'],
              'sleep':compact[p.stem]['sleep'], 'away':t['awayProfile'],
              'comfort':t['comfortProfile'], 'eco':t['ecoProfile']}
    entity['climate']['equipment_climate'].setdefault('state_attributes',{}).setdefault(
        'preset_mode',{})['state']=profiles
    codes.update({k:profiles[k] for k in ('home','sleep','away','comfort','eco')})
    # Real localization for previously English PID labels and dropdown values.
    number_names = {'pid_process_gain':t['gain'], 'pid_time_constant_minutes':t['timeConstant'],
                    'pid_dead_time_minutes':t['deadTime'], 'pid_lambda_minutes':'IMC λ'}
    for field, label in number_names.items():
        entity['number']['equipment_'+field]['name'] = 'PID · {channel}'+label
    cal = selection['equipment_pid_calibration_method']
    cal['name'] = 'PID · {channel}'+t['calibration']
    manual = selection['equipment_control_mode']['state']['manual']
    cal['state'].update(manual=manual+' Kp/Ki/Kd', imc_lambda='IMC / λ', cohen_coon='Cohen-Coon')
    capacity = selection['equipment_pid_fan_capacity_mode']
    capacity['name'] = 'PID · {channel}'+t['capacity']
    capacity['state'].update(legacy=t['legacyStrategy'], measured=t['measuredStrategy'])
    direction = selection['equipment_pid_fan_capacity_for_mode']
    direction['name'] = 'PID · {channel}'+t['choose']
    direction['state'].update({k:t[k] for k in ('heat','cool','dry','choose')})
    direction['state']['fan_only'] = t['fan']
    for field, info in entity['number'].items():
        if field.startswith('equipment_pid_capacity_'):
            label = (t['speed'] if '_speed_' in field else t['capacity'])
            info['name'] = 'PID · {channel}'+label+' '+field.rsplit('_',1)[-1]+' (%)'
    for name in ('equipment_pid_apply_calibration','equipment_pid_apply_fan_capacity'):
        if name in entity.get('button',{}):
            entity['button'][name]['name']='PID · {channel}'+t['apply']+' · '+t['calibration']
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    # Only card-visible state names; HA has the full enum catalog itself.
    bundle[lang] = {
        'text':t, 'states':{key:value for key,value in codes.items() if key in visible_codes},
        'words':compact[p.stem], 'profiles':entity['climate']['equipment_climate']['state_attributes']['preset_mode']['state'],
        'methods':selection['equipment_control_mode']['state'],
        'methodLabel':selection['equipment_control_mode']['name'].replace('{channel}',''),
    }
# strings.json is the English source of HA translation keys.
source = ROOT / 'strings.json'
base = json.loads(source.read_text())
en = json.loads((ROOT / 'translations/en.json').read_text())
for section in ('number','select','sensor','button','climate'):
    for key, val in en['entity'][section].items():
        if key.startswith('equipment_pid_') or key in ('equipment_control_status','equipment_climate'):
            base['entity'][section][key] = val
source.write_text(json.dumps(base, ensure_ascii=False, indent=2)+'\n')
# The explicit friendly-name catalog must match the HA translation entries.
names_path=ROOT/'equipment_name_catalog.py'
names_source=names_path.read_text()
names_tree=ast.parse(names_source)
node=next(n for n in names_tree.body if isinstance(n,ast.Assign) and any(getattr(t,'id','')=='EQUIPMENT_TRANSLATED_NAMES' for t in n.targets))
labels=ast.literal_eval(node.value)
for path in (ROOT/'translations').glob('*.json'):
    entities=json.loads(path.read_text())['entity']
    text=locales[path.stem.lower()]
    labels.setdefault(path.stem,{})['power_switch_entity']=text['supply']+' · {channel}'+text['physical']
    labels[path.stem]['power_switch_cooldown_seconds']=text['supply']+' · {channel}'+text['cooldown']+' (s)'
    labels[path.stem]['particle_cadr_m3h']='CADR · {channel}(m³/h)'
    for group in ('number','select','button'):
        for key,data in entities[group].items():
            if key.startswith('equipment_pid_') and 'name' in data:
                labels.setdefault(path.stem,{})[key.removeprefix('equipment_')]=data['name']
import pprint
lines=names_source.splitlines(True)
replacement='EQUIPMENT_TRANSLATED_NAMES = '+pprint.pformat(labels,sort_dicts=False,width=110)+'\n'
names_source=''.join(lines[:node.lineno-1])+replacement+''.join(lines[node.end_lineno:])
start=names_source.index('    if key == "particle_cadr_m3h":',names_source.index('def localized_equipment_name('))
end=names_source.index('    template = EQUIPMENT_TRANSLATED_NAMES[canonical].get(key)',start)
names_source=names_source[:start]+names_source[end:]
names_source=names_source.replace('    parameter = _pid_parameter_label(key)',
    '    parameter = _pid_parameter_label(key) if key in ("kp", "ki", "kd", "cycle_seconds") else None')
names_path.write_text(names_source)


card_path = ROOT / 'frontend/air-quality-advisor-card.js'
card = card_path.read_text()
assert '/* HEM_CARD65_START */' not in card, 'builder must run once on the verified baseline'
# Preserve all existing service handlers, entity provenance checks and focus handling.
a = card.index('      const pidLabels={', card.index('    _controllerPanel(room)'))
b = card.index('      const sections=devices.map', a)
card = card[:a] + '''      const pidLabels=this._pidLabels65();
      const fanCapacityLabels=this._fanLabels65();
''' + card[b:]
card = card.replace("const l=CLIMATE_LABELS[this._language()] || CLIMATE_LABELS.en;", "const l=this._climateLabels65();")
card = card.replace("const capacityInput=capVisible && capDirection?.state!=='choose' ?", "const capacityInput=capVisible && capMethod?.state==='measured' && capDirection?.state!=='choose' ?")
card = card.replace("const applyCapacity=capVisible && entry.capacityButtonId ?", "const applyCapacity=capVisible && capMethod?.state==='measured' && entry.capacityButtonId ?")
for expr in ["entry.calibrationButton?.attributes?.calibration_status || ''", "entry.capacityButton?.attributes?.calibration_status || ''"]:
    assert 'escape('+expr+')' in card
    card = card.replace('escape('+expr+')', 'escape(this._controllerStatusLabel('+expr+'))')
# Use explicit anchors, so whitespace never silently drops a control.
a = card.index('          \'<div class="managed-status">\'+escape(entry.entityId)+', card.index('    _controllerPanel'))
b = card.index("          editors.join('')+'</section>';", a)+len("          editors.join('')+'</section>';" )
card = card[:a] + '''          this._deviceSummary65(entry)+method+editors.join('')+
          this._calibrationDetails65(entry,control==='pid' ?
            calibrationMethod+pidInputs+apply+capSelectors+capacityInput+applyCapacity+capacitySummary : '')+
          '</section>';''' + card[b:]
card = card.replace("const title=active ? (p.controller==='environment' ? l.environmentActive : l.active)", "const title=managed.length ? this._l65('overview') : active ? (p.controller==='environment' ? l.environmentActive : l.active)")
card = card.replace("escape(nativeAir.recommended_mode||'')", "escape(this._controllerStatusLabel(nativeAir.recommended_mode||''))")
card = card.replace("escape(String(windowPlan.effect||''))", "escape(this._controllerStatusLabel(windowPlan.effect||''))")
card = card.replace("escape(kind)+': '+", "escape(this._controllerStatusLabel(kind))+': '+")
card = card.replace(": (p.reason || '');", ": (p.reason ? this._controllerStatusLabel(p.reason) : '');")
card = card.replace("filter((item) => item.active !== false)", "filter((item) => item.active === true)")
card = card.replace("' information\" title=\"'", "' '+escape(this._l65('information'))+'\" title=\"'")
card = card.replace('${escape(metric)} information', "${escape(this._l65('information'))}: ${escape(metric)}")
card = card.replace("    humidity:'mdi:water-percent', mold:'mdi:water-alert-outline' };", "    illuminance:'mdi:brightness-5', humidity:'mdi:water-percent', mold:'mdi:water-alert-outline' };")
# Include status-only changes in render signatures, not only native mode changes.
card = card.replace("state.attributes.controller_status?.pid_fan_capacity,", "state.attributes.controller_status, state.attributes.measurements, state.attributes.upstream_power_state,")
card = card.replace("(id.startsWith('select.') || id.startsWith('climate.') ||", "(id.startsWith('select.') || id.startsWith('climate.') || (id.startsWith('sensor.') && state?.attributes?.status_code) ||")
card = card.replace("          state.attributes.physical_source_state,", "          state.attributes.physical_source_state, state.attributes.status_reason_code, state.attributes.status_code, state.attributes.upstream_idle_since,")
# Remember expanded advanced settings across live data renders.
card = card.replace("      this._expanded = new Set();", '''      this._expanded = new Set();
      this._calibrationExpanded65 = new Set();
      this.shadowRoot.addEventListener('toggle', (event)=>{
        const id=event.target?.getAttribute?.('data-calibration-id');
        if (!id || !event.target.isConnected) return;
        if (event.target.open) this._calibrationExpanded65.add(id);
        else this._calibrationExpanded65.delete(id);
      }, true);''')
point = "  if (!customElements.get('air-quality-advisor-card'))"
assert card.count(point) == 1
extras = (ROOT / '.github/patches/card65.js').read_text()
extras = extras.replace('__BUNDLE65__', json.dumps(bundle, ensure_ascii=False, separators=(',',':')))
card = card.replace(point, '/* HEM_CARD65_START */\n'+extras+'\n/* HEM_CARD65_END */\n'+point)
card=card.replace('PID control is planned.', 'Individual device controls are available.')
card_path.write_text(card, encoding='utf-8')
meta = json.loads((ROOT/'manifest.json').read_text()); assert meta['domain']=='environment_manager'
meta['version']='0.6.0b65'; (ROOT/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
print('BETA65_PATCH_APPLIED',len(locales),'locales',len(card.encode()),'card bytes')
