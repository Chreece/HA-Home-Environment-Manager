"""Add opt-in per-cover lux evidence without changing existing shade controls.

Guarded/idempotent source transformation for GitHub validation. No network,
no hardware commands, and no backend registration side effects at import.
"""
from __future__ import annotations
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
def patch(path, old, new):
    target=ROOT/path
    source=target.read_text(encoding='utf-8')
    if new in source:
        return
    assert source.count(old)==1, (path,source.count(old),old[:120])
    target.write_text(source.replace(old,new),encoding='utf-8')

patch('shade_cooling.py', 'COOLING_HYSTERESIS_C = 1.0\n', '''COOLING_HYSTERESIS_C = 1.0
# Lux is optional extra evidence to CLOSE; never an independent reason to OPEN.
# Default disabled ensures existing shades are unchanged after upgrading.
LUX_BOUNDS = (100., 100000., 100., "lx", 1000.)
LUX_ROOM_MEAN = "room_selected_mean"
''')
patch('shade_cooling.py', '        "authorization_revision": revision,\n    }\n\n\ndef selectable_windows', '''        "authorization_revision": revision,
        "lux_enabled": saved.get("lux_enabled") is True,
        "lux_entity": saved.get("lux_entity") if isinstance(
            saved.get("lux_entity"), str) else None,
        "min_lux": _numeric(saved.get("min_lux"), LUX_BOUNDS[0], LUX_BOUNDS[1])
            or LUX_BOUNDS[4],
    }


def _lux_candidate(hass: Any, area: str, entity: str) -> bool:
    """A real same-room illuminance sensor, even if currently unavailable."""
    if (not isinstance(entity, str) or not entity.startswith("sensor.")
            or not native(hass, entity)):
        return False
    from .discovery import entity_area
    if entity_area(hass, entity) != area:
        return False
    from homeassistant.helpers import entity_registry as er
    registered = er.async_get(hass).async_get(entity)
    state = hass.states.get(entity)
    attrs = state.attributes if state is not None else {}
    kind = (str(attrs.get("device_class") or getattr(registered, "device_class", None)
                or getattr(registered, "original_device_class", None) or "").casefold())
    unit = str(attrs.get("unit_of_measurement") or getattr(
        registered, "unit_of_measurement", None) or getattr(
        registered, "original_unit_of_measurement", None) or "").strip().casefold()
    return kind == "illuminance" or unit in ("lx", "lux")


def selectable_lux_sensors(hass: Any, area: str) -> tuple[str, ...]:
    """Configuration inventory only; never called during shade tick/render.

    Registry-backed lookup keeps temporarily offline physical lux sources in
    the selector. This is intentionally NOT a repeated whole-home scan.
    """
    from homeassistant.helpers import entity_registry as er
    registered = er.async_get(hass)
    ids = {e.entity_id for e in registered.entities.values()
           if e.entity_id.startswith("sensor.")}
    # Some local template sensors have a live state without a registry entry.
    ids.update(s.entity_id for s in hass.states.async_all("sensor"))
    return tuple(sorted(e for e in ids if _lux_candidate(hass, area, e)))


def lux_evidence(hass: Any, settings: dict, area: str, cfg: dict) -> dict:
    """Read only exact selected source IDs; no global scans or lux->solar guess."""
    result = {"enabled": cfg.get("lux_enabled") is True,
              "entity": cfg.get("lux_entity"), "threshold_lx": cfg.get("min_lux", LUX_BOUNDS[4]),
              "value_lx": None, "sources": [], "valid_count": 0,
              "status": "lux_not_enabled"}
    if not result["enabled"]:
        return result
    chosen = cfg.get("lux_entity")
    if chosen == LUX_ROOM_MEAN:
        # Average only explicitly selected, same-room real lux sensors.
        candidates = selected(settings, area, "air_quality") or ()
        ids = tuple(e for e in candidates if _lux_candidate(hass, area, e))
    elif isinstance(chosen, str) and _lux_candidate(hass, area, chosen):
        ids = (chosen,)
    else:
        ids = ()
    result["sources"] = list(ids)
    if not ids:
        result["status"] = "lux_sensor_not_selected_or_ineligible"
        return result
    from .discovery import reading
    values = [r.value for e in ids if (r := reading(
        hass, e, 10, outdoor=False)).metric == "illuminance" and r.value is not None]
    result["valid_count"] = len(values)
    if not values:
        result["status"] = "lux_sensor_unavailable_or_stale"
        return result
    level = round(sum(values) / len(values), 1)
    result["value_lx"] = level
    result["status"] = ("lux_threshold_met" if level >= result["threshold_lx"]
                        else "lux_below_threshold")
    return result


def lux_signature(cfg: dict) -> tuple:
    """Disallow an in-flight close after a user changed lux evidence policy."""
    return cfg.get("lux_enabled"), cfg.get("lux_entity"), cfg.get("min_lux")


def selectable_windows''')
patch('shade_cooling.py', '''        if entity and not cfg["legacy"] and not linked:
            close_reason = "window_not_assigned"''', '''        if entity and cfg["lux_enabled"]:
            # Extra permission for a new CLOSE only. Do not use lux for OPEN:
            # the closed shade itself can darken the measured room.
            measured_lux = lux_evidence(self.hass, settings, area, cfg)
            details["illuminance"] = measured_lux
            if close_reason == "closing_recommended" and measured_lux["status"] != "lux_threshold_met":
                close_reason = measured_lux["status"]
        if entity and not cfg["legacy"] and not linked:
            close_reason = "window_not_assigned"''')
patch('shade_cooling.py', '''            now = self.clock()
            latest = self.manager.settings
            revision = cover_config(latest, area, entity)["authorization_revision"]''', '''            now = self.clock()
            latest = self.manager.settings
            revision = cover_config(latest, area, entity)["authorization_revision"]
            evidence_signature = lux_signature(cfg)''')
patch('shade_cooling.py', '''                    or not new_details["window_safe"] or newer is None
                    or newer.state != "open" or''', '''                    or not new_details["window_safe"] or newer is None
                    or lux_signature(new_cfg) != evidence_signature
                    or newer.state != "open" or''')
patch('shade_cooling.py', '''                    or not fresh_allowed or physical is None
                    or physical.state != "open" or not fresh_evidence["window_safe"]
                    or fresh_reason != "closing_recommended"):''', '''                    or not fresh_allowed or physical is None
                    or lux_signature(latest_cfg) != evidence_signature
                    or physical.state != "open" or not fresh_evidence["window_safe"]
                    or fresh_reason != "closing_recommended"):
''')
# No reason to re-open a confirmed owned shade just because its sensor darkens.

patch('device_controls.py', '''                CONF_SHADE_ROOMS, SHADE_NUMBERS, eligible_shade, selectable_windows,
''', '''                CONF_SHADE_ROOMS, SHADE_NUMBERS, LUX_BOUNDS, LUX_ROOM_MEAN,
                eligible_shade, selectable_windows, selectable_lux_sensors,
''')
patch('device_controls.py', '''            if not eligible_shade(manager.hass, area, entity_id, enrolled)[0]:
                raise HomeAssistantError("Only native indoor shades assigned to this room are supported")
''', '''            # Lux settings are configuration-only and remain editable when
            # the physical shade has not restored its live state.
            if key in ("lux_enabled", "lux_entity", "min_lux"):
                from .discovery import entity_area
                from .room_sources import native
                if (not native(manager.hass, entity_id)
                        or entity_area(manager.hass, entity_id) != area):
                    raise HomeAssistantError("Lux settings require a registered same-room shade")
            elif not eligible_shade(manager.hass, area, entity_id, enrolled)[0]:
                raise HomeAssistantError("Only native indoor shades assigned to this room are supported")
''')
patch('device_controls.py', '''            if key not in ("enabled", "window_entity", "announce", "close_above_c"):
''', '''            if key not in ("enabled", "window_entity", "announce", "close_above_c",
                           "lux_enabled", "lux_entity", "min_lux"):
''')
patch('device_controls.py', '''            elif key == "announce":
                if type(value) is not bool:
                    raise HomeAssistantError("Pre-movement announcement must be on or off")
                draft["announce"] = value
            else:
                draft["close_above_c"] = _finite(value, SHADE_NUMBERS["close_above_c"])''', '''            elif key == "announce":
                if type(value) is not bool:
                    raise HomeAssistantError("Pre-movement announcement must be on or off")
                draft["announce"] = value
            elif key == "lux_entity":
                available = selectable_lux_sensors(manager.hass, area)
                room_selected = selected(current, area, "air_quality") or ()
                if value in ("none", None):
                    chosen = None
                elif value == LUX_ROOM_MEAN and any(e in available for e in room_selected):
                    chosen = LUX_ROOM_MEAN
                elif isinstance(value, str) and value in available:
                    chosen = value
                else:
                    raise HomeAssistantError("Choose a real, same-room illuminance sensor")
                draft["lux_entity"] = chosen
            elif key == "lux_enabled":
                if type(value) is not bool:
                    raise HomeAssistantError("Use lux must be on or off")
                if value:
                    available = selectable_lux_sensors(manager.hass, area)
                    chosen = draft.get("lux_entity")
                    if (chosen not in available and not (
                            chosen == LUX_ROOM_MEAN and any(e in available for e in (
                                selected(current, area, "air_quality") or ())))):
                        raise HomeAssistantError("Choose a same-room lux sensor before enabling")
                draft["lux_enabled"] = value
            elif key == "min_lux":
                draft["min_lux"] = _finite(value, LUX_BOUNDS)
            else:
                draft["close_above_c"] = _finite(value, SHADE_NUMBERS["close_above_c"])''')
# No authorization re-arming or old ownership mutation for tuning values.

patch('select.py', '''            entities.append(ShadeWindowSelect(manager, entry.entry_id, area, cover))
''', '''            entities.append(ShadeWindowSelect(manager, entry.entry_id, area, cover))
            entities.append(ShadeIlluminanceSelect(manager, entry.entry_id, area, cover))
''')
patch('select.py', '\n\nclass ShadeWindowSelect(SelectEntity):', '''

class ShadeIlluminanceSelect(SelectEntity):
    """Select one exact room sensor or the selected-room lux mean per cover."""
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "shade_lux_entity"
    _attr_icon = "mdi:brightness-5"

    def __init__(self, manager, entry_id: str, area: str, cover: str):
        from .shade_cooling import selectable_lux_sensors, LUX_ROOM_MEAN
        from .room_sources import selected
        from .device_hierarchy import controller_device_info
        from homeassistant.helpers import entity_registry as er, device_registry as dr
        self._manager, self._area, self._cover = manager, area, cover
        self._attr_unique_id = (
            f"{entry_id}_area_{area}_shade_{cover.replace('.', '_')}_lux_entity")
        self._attr_device_info = controller_device_info(manager, area, cover)
        if self._attr_device_info is None:
            raise ValueError("No registered child device for this window shade")
        locale = str(getattr(getattr(manager.hass, "config", None), "language", "en")).split("-")[0]
        self._none_label = {"el":"Χωρίς αισθητήρα", "de":"Kein Sensor", "en":"No sensor"}.get(locale, "No sensor")
        self._mean_label = {"el":"Μέσος όρος επιλεγμένων lux δωματίου",
                            "de":"Mittelwert der ausgewählten Raum-Lux-Sensoren",
                            "en":"Selected room lux sensor mean"}.get(locale,"Selected room lux sensor mean")
        # Inventory scan once per room and initial registration, never once
        # per controller state update or each additional cover in this room.
        inventory = getattr(manager, "_shade_lux_inventory_cache", None)
        if inventory is None:
            inventory = manager._shade_lux_inventory_cache = {}
        if area not in inventory:
            inventory[area] = selectable_lux_sensors(manager.hass, area)
        valid = inventory[area]
        self._options_map = {self._none_label: None}
        if any(entity in valid for entity in (selected(manager.settings, area, "air_quality") or ())):
            self._options_map[self._mean_label] = LUX_ROOM_MEAN
        registry, devices = er.async_get(manager.hass), dr.async_get(manager.hass)
        for entity in valid:
            entry = registry.async_get(entity)
            device = devices.async_get(entry.device_id) if (
                entry is not None and entry.device_id) else None
            device_name = (getattr(device, "name_by_user", None)
                           or getattr(device, "name", None))
            state = manager.hass.states.get(entity)
            sensor_name = (getattr(entry, "name", None) or getattr(entry, "original_name", None)
                           or getattr(state, "name", None) or entity)
            friendly = " - ".join(part for part in (device_name, sensor_name) if part)
            self._options_map[f"{friendly} [{entity}]"] = entity
        from .shade_cooling import cover_config
        saved = cover_config(manager.settings, area, cover)["lux_entity"]
        if saved and saved not in self._options_map.values():
            self._options_map[f"{saved} ({saved})"] = saved

    @property
    def options(self):
        return list(self._options_map)

    @property
    def current_option(self):
        from .shade_cooling import cover_config
        source = cover_config(self._manager.settings, self._area, self._cover)["lux_entity"]
        return next((text for text, entity in self._options_map.items()
                     if entity == source), self._none_label)

    @property
    def extra_state_attributes(self):
        from .shade_cooling import cover_config
        cfg = cover_config(self._manager.settings, self._area, self._cover)
        return {"source_cover": self._cover, "lux_entity": cfg["lux_entity"],
                "minimum_lux": cfg["min_lux"], "use_lux_for_shading": cfg["lux_enabled"]}

    async def async_select_option(self, option):
        if option not in self._options_map:
            raise ValueError("Unknown lux sensor option")
        await update_device_setting(self._manager, "shade_device", "lux_entity",
                                    self._options_map[option], area=self._area,
                                    entity_id=self._cover)
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, f"{SIGNAL_UPDATED}_{self._manager.entry.entry_id}",
            self._update,
        ))

    @callback
    def _update(self):
        self.async_write_ha_state()


class ShadeWindowSelect(SelectEntity):''')

patch('switch.py', '''            for key in ("enabled", "announce"):
''', '''            for key in ("enabled", "announce", "lux_enabled"):
''')
patch('switch.py', '''        self._attr_translation_key = f"shade_{'auto_control' if key == 'enabled' else 'announce'}"
        self._attr_icon = "mdi:blinds" if key == "enabled" else "mdi:bullhorn-outline"''', '''        self._attr_translation_key = f"shade_{'auto_control' if key == 'enabled' else 'lux_enabled' if key == 'lux_enabled' else 'announce'}"
        self._attr_icon = ("mdi:brightness-5" if key == "lux_enabled"
                           else "mdi:blinds" if key == "enabled" else "mdi:bullhorn-outline")''')
patch('switch.py', '''            "manual_override_paused": per_cover.get(self._cover) == "manual_override",
''', '''            "manual_override_paused": per_cover.get(self._cover) == "manual_override",
            "lux_sensor": cfg.get("lux_entity"),
            "lux_threshold_lx": cfg.get("min_lux"),
            "lux_enabled": cfg.get("lux_enabled"),
''')

patch('number.py', '''        numbers.extend(ShadeDeviceNumber(manager, entry.entry_id, area_id, cover)
                       for cover in covers)
''', '''        numbers.extend(ShadeDeviceNumber(manager, entry.entry_id, area_id, cover)
                       for cover in covers)
        numbers.extend(ShadeIlluminanceNumber(manager, entry.entry_id, area_id, cover)
                       for cover in covers)
''')
patch('number.py', '\n\nclass ShadeDeviceNumber(NumberEntity):', '''

class ShadeIlluminanceNumber(NumberEntity):
    """Minimum measured indoor illuminance before this cover can auto-close."""
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "shade_min_lux"
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:brightness-5"

    def __init__(self, manager, entry_id: str, area: str, cover: str):
        from .shade_cooling import LUX_BOUNDS
        self._manager, self._area, self._cover = manager, area, cover
        self._attr_unique_id = (
            f"{entry_id}_area_{area}_shade_{cover.replace('.', '_')}_min_lux")
        self._attr_device_info = controller_device_info(manager, area, cover)
        if self._attr_device_info is None:
            raise ValueError("No registered child device for this window shade")
        self._attr_native_min_value, self._attr_native_max_value = LUX_BOUNDS[:2]
        self._attr_native_step = LUX_BOUNDS[2]
        self._attr_native_unit_of_measurement = LUX_BOUNDS[3]

    @property
    def native_value(self):
        from .shade_cooling import cover_config
        return cover_config(self._manager.settings, self._area, self._cover)["min_lux"]

    async def async_set_native_value(self, value):
        await update_device_setting(self._manager, "shade_device", "min_lux", value,
                                    area=self._area, entity_id=self._cover)
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, f"{SIGNAL_UPDATED}_{self._manager.entry.entry_id}", self._update))

    @callback
    def _update(self):
        self.async_write_ha_state()


class ShadeDeviceNumber(NumberEntity):''')
# Source entity writes may be stored while off, but cannot grant motion or
# change a different cover's settings. Actual lux always reverified at dispatch.

translations={
'en': ('Use lux sensor for solar shading','Solar-shading lux sensor','Minimum illuminance to close'),
'el': ('Χρήση αισθητήρα φωτεινότητας για σκίαση','Αισθητήρας φωτεινότητας σκίασης','Ελάχιστη φωτεινότητα για κλείσιμο'),
'de': ('Luxsensor für Sonnenschutz verwenden','Luxsensor für Beschattung','Mindestbeleuchtungsstärke zum Schließen'),
'fr': ('Utiliser le capteur de luminosité pour les stores','Capteur de luminosité pour les stores','Éclairement minimal pour fermer'),
'es': ('Usar sensor de luz para sombreado solar','Sensor de luz para sombreado','Iluminancia mínima para cerrar'),
'it': ('Usa il sensore di luce per la schermatura solare','Sensore di illuminamento per schermatura','Illuminamento minimo per chiudere'),
'nl': ('Luxsensor gebruiken voor zonwering','Luxsensor voor zonwering','Minimale verlichtingssterkte voor sluiten'),
'pt': ('Usar sensor de luz para sombreamento solar','Sensor de luminosidade para sombreamento','Iluminância mínima para fechar'),
'pt-br': ('Usar sensor de luz no sombreamento solar','Sensor de luminosidade do sombreamento','Iluminância mínima para fechar'),
'ru': ('Использовать датчик освещённости для затенения','Датчик освещённости для штор','Минимальная освещённость для закрытия'),
'uk': ('Використовувати датчик освітленості для затінення','Датчик освітленості для штор','Мінімальна освітленість для закриття'),
'bg': ('Използване на сензор за осветеност за засенчване','Сензор за осветеност за щори','Минимална осветеност за затваряне'),
'cs': ('Použít čidlo osvětlení pro stínění','Čidlo osvětlení pro stínění','Minimální osvětlení pro zavření'),
'sk': ('Použiť snímač osvetlenia pre tienenie','Snímač osvetlenia pre tienenie','Minimálne osvetlenie na zatvorenie'),
'pl': ('Użyj czujnika natężenia światła do zacieniania','Czujnik światła do zacieniania','Minimalne natężenie światła do zamknięcia'),
'da': ('Brug luxsensor til solafskærmning','Luxsensor til solafskærmning','Mindste belysningsstyrke for lukning'),
'sv': ('Använd luxsensor för solskydd','Luxsensor för solskydd','Minsta belysningsstyrka för stängning'),
'nb': ('Bruk lyssensor for solskjerming','Lyssensor for solskjerming','Minste lysstyrke for lukking'),
'fi': ('Käytä luksianturia aurinkosuojaukseen','Luksianturi aurinkosuojaukseen','Sulkemisen vähimmäisvalaistus'),
'hu': ('Fényérzékelő használata árnyékoláshoz','Árnyékolási fényérzékelő','Minimális megvilágítás záráshoz'),
'ro': ('Folosește senzorul de lumină pentru umbrire','Senzor de iluminare pentru umbrire','Iluminare minimă pentru închidere'),
'hr': ('Koristi senzor osvijetljenosti za zasjenjivanje','Senzor osvijetljenosti za sjenila','Minimalna osvijetljenost za zatvaranje'),
'sr': ('Користи сензор осветљења за сенчење','Сензор осветљења за сенчење','Минимално осветљење за затварање'),
'he': ('השתמש בחיישן תאורה להצללה','חיישן תאורה להצללה','רמת תאורה מינימלית לסגירה'),
'ar': ('استخدام مستشعر الإضاءة للتظليل الشمسي','مستشعر الإضاءة للتظليل','الحد الأدنى للإضاءة للإغلاق'),
'fa': ('استفاده از حسگر روشنایی برای سایه‌بان','حسگر روشنایی سایه‌بان','حداقل روشنایی برای بستن'),
'hi': ('धूप से बचाव के लिए प्रकाश सेंसर उपयोग करें','छायांकन के लिए प्रकाश सेंसर','बंद करने के लिए न्यूनतम प्रकाश'),
'bn': ('সূর্যের ছায়ার জন্য আলোর সেন্সর ব্যবহার করুন','ছায়ার জন্য আলোর সেন্সর','বন্ধ করার ন্যূনতম আলোকমাত্রা'),
'ur': ('سولر شیڈنگ کے لیے روشنی کا سینسر استعمال کریں','شیڈنگ کا لکس سینسر','بند کرنے کے لیے کم از کم روشنی'),
'ta': ('சூரிய நிழலுக்கான ஒளி உணரியைப் பயன்படுத்து','நிழலுக்கான ஒளி உணரி','மூடுவதற்கான குறைந்தபட்ச ஒளி அளவு'),
'id': ('Gunakan sensor cahaya untuk peneduh surya','Sensor cahaya peneduh surya','Pencahayaan minimum untuk menutup'),
'vi': ('Dùng cảm biến ánh sáng cho che nắng','Cảm biến ánh sáng cho che nắng','Độ rọi tối thiểu để đóng'),
'tr': ('Güneş gölgelemesinde ışık sensörü kullan','Gölgeleme için ışık sensörü','Kapanma için asgari aydınlık'),
'th': ('ใช้เซ็นเซอร์แสงสำหรับม่านกันแดด','เซ็นเซอร์แสงสำหรับม่านกันแดด','ความสว่างขั้นต่ำในการปิด'),
'ja': ('日よけ制御に照度センサーを使用','日よけ用照度センサー','閉じるための最低照度'),
'ko': ('차양에 조도 센서 사용','차양 조도 센서','닫기 위한 최소 조도'),
'zh-hans': ('使用照度传感器进行遮阳','遮阳照度传感器','关闭时的最低照度'),
'zh-hant': ('使用照度感測器進行遮陽','遮陽照度感測器','關閉所需最低照度'),
}
locales=list((ROOT/'translations').glob('*.json'))
assert {p.stem.lower() for p in locales}==set(translations),(set(translations)-{p.stem.lower() for p in locales})
for locale in [*locales,ROOT/'strings.json']:
    lang=locale.stem.lower()
    keys=translations[lang] if lang in translations else translations['en']
    data=json.loads(locale.read_text(encoding='utf-8'))
    entities=data['entity']
    entities['switch']['shade_lux_enabled']={'name':keys[0]}
    entities['select']['shade_lux_entity']={'name':keys[1]}
    entities['number']['shade_min_lux']={'name':keys[2]+' (lx)'}
    locale.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest=ROOT/'manifest.json'
m=json.loads(manifest.read_text())
assert m['version'] in ('0.6.0b68','0.6.0b69'),m['version']
m['version']='0.6.0b69'
manifest.write_text(json.dumps(m,indent=2)+'\n')
print('PASS patch beta69 applied to all shade controls and',len(locales),'locales')
