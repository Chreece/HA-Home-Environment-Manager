from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
import json, ast, pprint
meta=json.loads((ROOT/'manifest.json').read_text())
assert meta['domain']=='environment_manager' and meta['version'] in ('0.6.0b65','0.6.0b66')

def patch(name, old, new):
 p=ROOT/name;s=p.read_text()
 if new in s: return
 assert s.count(old)==1,(name,old[:110],s.count(old));p.write_text(s.replace(old,new))

(ROOT/'equipment_window.py').write_text((ROOT/'.github/patches/equipment_window66.py').read_text())
patch('equipment_model.py','"quiet_sleep": False, "quiet_occupied": False,','"quiet_sleep": False, "quiet_occupied": False,\n            "pause_on_window_open": True,')
patch('equipment_runtime.py', '            cap = model.capabilities(self.manager, spec)\n            if cap is None:', '''            if set(changes) == {"pause_on_window_open"}:
                value = changes["pause_on_window_open"]
                if type(value) is not bool:
                    raise HomeAssistantError("Window pause must be a boolean")
                lock = getattr(self.manager, "_device_settings_write_lock", None)
                if lock is None:
                    lock = self.manager._device_settings_write_lock = asyncio.Lock()
                async with lock:
                    if not self._current_spec(spec):
                        raise HomeAssistantError("Controller sources changed during configuration")
                    options = deepcopy(self.manager.entry.options)
                    profiles = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
                    profiles = profiles if isinstance(profiles, dict) else {}
                    prior = profiles.get(spec.identifier, {})
                    profiles[spec.identifier] = {
                        **(prior if isinstance(prior, dict) else {}),
                        "pause_on_window_open": value,
                    }
                    options[model.SETTINGS] = profiles
                    self.hass.config_entries.async_update_entry(self.manager.entry, options=options)
                # Do not clear manual override or uncertain hardware latches.
                getattr(self, "_window_policy_cache", {}).pop(spec.identifier, None)
                self._status(spec, "settings_updated")
                if getattr(self.manager, "_active", False):
                    self.manager._recalculate(initial=True)
                return
            cap = model.capabilities(self.manager, spec)
            if cap is None:''')
patch('equipment_runtime.py','            allowed = set(model.DEFAULTS) |', '''            if ("pause_on_window_open" in new
                    and type(new["pause_on_window_open"]) is not bool):
                raise HomeAssistantError("Window pause must be a boolean")
            allowed = set(model.DEFAULTS) |''')
patch('equipment_runtime.py','    def _stop_policy_verified(\n', '''    def _window_policy(self, spec, cfg=None):
        from .equipment_window import evaluate
        return evaluate(self, spec, cfg)

    def _stop_policy_verified(
''')
patch('equipment_runtime.py','        if kind == "sleep":\n', '''        if kind == "window":
            return (cfg.get("pause_on_window_open", False) is True
                    and self._window_policy(spec, cfg).get("stop_requested") is True)
        if kind == "sleep":
''')
patch('equipment_runtime.py','              mode: str, *, automatic: bool = True) -> str | None:', '              mode: str, *, automatic: bool = True, window_stop: bool = False) -> str | None:')
patch('equipment_runtime.py','        if mode != "off" and cap.domain != "fan" and not _contact_interlock(self.hass, spec.area_id, plan):', '''        if cfg.get("pause_on_window_open", False):
            window = self._window_policy(spec, cfg)
            if window["blocked"] and not window_stop:
                return window["status"]
        if (mode != "off" and cap.domain != "fan"
                and cfg.get("pause_on_window_open", True)
                and not _contact_interlock(self.hass, spec.area_id, plan)):''')
patch('equipment_runtime.py','                    if not _contact_interlock(self.hass, spec.area_id, plan):','                    if cfg.get("pause_on_window_open", True) and not _contact_interlock(self.hass, spec.area_id, plan):')
patch('equipment_runtime.py','policy_stop not in ("sleep", "idle")','policy_stop not in ("sleep", "idle", "window")')
patch('equipment_runtime.py','elif why := self._gate(spec, cap, cfg, plan, action_mode, automatic=automatic):','elif why := self._gate(spec, cap, cfg, plan, action_mode, automatic=automatic,\n                              window_stop=power and action_mode == "off"):')
patch('equipment_runtime.py','and not self._gate(spec, cap, latest, latest_plan, action_mode, automatic=automatic))','and not self._gate(spec, cap, latest, latest_plan, action_mode, automatic=automatic,\n                                   window_stop=power and action_mode == "off"))')
patch('equipment_runtime.py','        if (auto and power and not output_off(state)\n                and self._stop_policy_verified(spec, cap, "idle")):', '''        if cfg.get("pause_on_window_open", False) and cfg["control_mode"] not in ("existing", "off"):
            window = self._window_policy(spec, cfg)
            if window["blocked"]:
                self._memory.pop(spec.identifier, None)
                self._fan_allocations.pop(spec.identifier, None)
                if (window["stop_requested"] and not output_off(state)
                        and (power or owned)):
                    await self._power(
                        spec, cap, "off", automatic=False, shutdown=bool(owned),
                        policy_stop="window",
                    )
                else:
                    self._status(spec, window["status"],
                                 window_resume_remaining_seconds=window["remaining_seconds"])
                return  # No targets, fan, swing or mode control during hold.
        if (auto and power and not output_off(state)
                and self._stop_policy_verified(spec, cap, "idle")):''')
patch('equipment_power_switch.py','    plan = model.plan_for(runtime.manager, spec)\n    live = effective_device(runtime.manager, spec, cap.primary)', '''    if cfg.get("pause_on_window_open", False):
        from .equipment_window import evaluate as window_policy
        window = window_policy(runtime, spec, cfg)
        if window["blocked"]:
            return None if window["status"] == "window_state_unknown" else False
    plan = model.plan_for(runtime.manager, spec)
    live = effective_device(runtime.manager, spec, cap.primary)''')
patch('equipment_power_switch.py','    if method in ("automatic", "pid", "manual"):\n        if (plan.get("window_safe")', '    if method in ("automatic", "pid", "manual") and cfg.get("pause_on_window_open", True):\n        if (plan.get("window_safe")')
patch('equipment_power_switch.py','    cap = verified_capabilities(runtime, spec)\n    if cap is None:\n        if observed.state != "off":', '''    if cfg.get("pause_on_window_open", False):
        from .equipment_window import evaluate as window_policy
        window = window_policy(runtime, spec, cfg)
        if observed.state == "off" and window["blocked"]:
            runtime._pid_offline_previews.pop(spec.identifier, None)
            runtime._status(spec, window["status"],
                            window_resume_remaining_seconds=window["remaining_seconds"])
            return True  # No supply wake during OPEN/UNKNOWN/post-close hold.
    cap = verified_capabilities(runtime, spec)
    if cap is None:
        if observed.state != "off":''')
patch('switch.py','    entities.extend(native_quiet_switches())','    entities.extend(native_quiet_switches())\n    entities.extend(EquipmentWindowPauseSwitch(manager, spec)\n                    for spec in equipment.specs(manager))')
patch('switch.py','class ShadeCoolingSwitch(SwitchEntity):', '''class EquipmentWindowPauseSwitch(EquipmentEntity, SwitchEntity):
    """Per-controller window stop policy; turning this on never switches hardware."""
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:window-open-variant"

    def __init__(self, manager, spec):
        self._equipment_init(manager, spec, "pause_on_window_open")

    @property
    def available(self):
        return self._manager.equipment._ready

    @property
    def is_on(self):
        return self.controller_settings.get("pause_on_window_open", True) is True

    @property
    def extra_state_attributes(self):
        return {**super().extra_state_attributes, "window_pause_role": "policy",
                "window_resume_delay_seconds": 60}

    async def async_turn_on(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {"pause_on_window_open": True})

    async def async_turn_off(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {"pause_on_window_open": False})


class ShadeCoolingSwitch(SwitchEntity):''')
patch('controller_status_catalog.py','EQUIPMENT_SENSOR_STATUSES = frozenset((', 'EQUIPMENT_SENSOR_STATUSES = frozenset((\n    "window_open_pause", "window_close_warmup", "window_state_unknown",')
patch('equipment_status.py','            "sleep_pause_requested": (','            "window_pause_enabled": cfg.get("pause_on_window_open", True),\n            "window_policy": dict(getattr(runtime, "_window_policy_cache", {}).get(\n                self._spec.identifier, {})),\n            "sleep_pause_requested": (')
patch('.github/tests/test_beta64_sleep_idle.py','    def _gate(self, spec, cap, cfg, plan, mode, *, automatic=True):','    def _gate(self, spec, cap, cfg, plan, mode, *, automatic=True, window_stop=False):')
print('Beta66 runtime patches applied')

keys='windowSwitch windowOpen windowWarmup windowUnknown windowReady rawDetails controller source status aqiSetup aqiHelp outsideIncomplete windowHelp'.split()
labels={}
for row in (ROOT/'.github/patches/card66.tsv').read_text().splitlines():
    lang,*values=row.split('|')
    assert len(values)==len(keys),(lang,len(values))
    labels[lang]=dict(zip(keys,values))
assert set(labels)=={p.stem.lower() for p in (ROOT/'translations').glob('*.json')}
status_fields={'window_open_pause':'windowOpen','window_close_warmup':'windowWarmup','window_state_unknown':'windowUnknown'}
for p in (ROOT/'translations').glob('*.json'):
    data=json.loads(p.read_text());text=labels[p.stem.lower()]
    data['entity']['switch']['equipment_pause_on_window_open']={'name':text['windowSwitch']+' · {channel}'}
    codes=data['entity']['sensor']['equipment_control_status']['state']
    codes.update({key:text[value] for key,value in status_fields.items()})
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
source=ROOT/'strings.json';data=json.loads(source.read_text());text=labels['en']
data['entity']['switch']['equipment_pause_on_window_open']={'name':text['windowSwitch']+' · {channel}'}
data['entity']['sensor']['equipment_control_status']['state'].update({key:text[value] for key,value in status_fields.items()})
source.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
path=ROOT/'equipment_name_catalog.py';text=path.read_text();tree=ast.parse(text)
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(getattr(t,'id','')=='EQUIPMENT_TRANSLATED_NAMES' for t in n.targets))
names=ast.literal_eval(node.value)
for locale,table in names.items():
    table['pause_on_window_open']=labels[locale.lower()]['windowSwitch']+' · {channel}'
lines=text.splitlines(True)
path.write_text(''.join(lines[:node.lineno-1])+'EQUIPMENT_TRANSLATED_NAMES = '+pprint.pformat(names,sort_dicts=False,width=110)+'\n'+''.join(lines[node.end_lineno:]))
path=ROOT/'frontend/air-quality-advisor-card.js';card=path.read_text()
assert '/* HEM_CARD65_END */' in card,'Unexpected frontend baseline'
if '/* HEM_CARD66_START */' not in card:
    old='        measuredTemp+sourceDiagnostic+'
    new="        '<div class=\"hem-room-readings66\">'+measuredTemp+this._roomHumidity66(room)+'</div>'+sourceDiagnostic+"
    assert card.count(old)==1
    card=card.replace(old,new)
    source_js=ROOT/'.github/patches/card66.js'
    template=source_js.read_text().replace('_pendingForceRender66','_pendingForceRender')
    source_js.write_text(template)
    extension=template.replace('__CARD66__',json.dumps(labels,ensure_ascii=False,separators=(',',':')))
    card=card.replace('/* HEM_CARD65_END */','/* HEM_CARD65_END */\n/* HEM_CARD66_START */\n'+extension+'\n/* HEM_CARD66_END */')
    path.write_text(card)
meta['version']='0.6.0b66'
(ROOT/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
print('PASS Beta66 source builder: window policy, 38 catalogs, persistent disclosures, room RH and exact outside blocker')
