"""Home language and room policy selectors; never direct equipment modes."""
from __future__ import annotations

from .room_hubs import async_add_grouped_entities
from .room_pid_name_catalog import localized_room_pid_name

from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, SIGNAL_UPDATED, LANGUAGES
from .device_hierarchy import controller_device_info
from .device_controls import (
    climate_settings, pid_settings, tuning_source, update_device_setting,
    CLIMATE_POLICY_OPTIONS, DEVICE_POLICY_OPTIONS, GLOBAL_POLICY_OPTIONS,
    configured_aqi_entities, AQI_SCALES,
)
from .device_hierarchy import configured_area_ids

PROFILE_OPTIONS = ("auto", "comfort", "home", "away", "sleep", "eco")
GAIN_SOURCE_OPTIONS = ("defaults", "manual")


async def async_setup_entry(hass, entry, async_add_entities):
    manager = entry.runtime_data
    entities = [TTSLanguageSelect(manager, entry.entry_id)]
    for area in configured_area_ids(manager.settings):
        if climate_settings(manager.settings, area) is not None:
            entities.append(ConfigSelect(manager, entry.entry_id, area, "manual_profile",
                                         PROFILE_OPTIONS))
        if pid_settings(manager.settings, area) is not None:
            entities.append(ConfigSelect(manager, entry.entry_id, area, "pid_gain_source",
                                         GAIN_SOURCE_OPTIONS))
    entities.extend(
        ConfigSelect(manager, entry.entry_id, None, "aqi_scale", AQI_SCALES,
                     setting_key="scale", entity_id=source)
        for source in configured_aqi_entities(manager)
    )
    entities.extend(
        ConfigSelect(manager, entry.entry_id, None, "global_policy",
                     GLOBAL_POLICY_OPTIONS["home_policy"], setting_key="home_policy")
        for _ in (0,)
    )
    for area in configured_area_ids(manager.settings):
        if climate_settings(manager.settings, area) is None:
            continue
        for key, values in CLIMATE_POLICY_OPTIONS.items():
            entities.append(ConfigSelect(
                manager, entry.entry_id, area, "climate_policy", values, setting_key=key
            ))
    from . import equipment_model as equipment
    entities.extend(EquipmentSelect(manager, spec, "control_mode")
                    for spec in equipment.specs(manager))
    # A dedicated optional physical relay for EVERY managed output, including
    # switch, numeric, fan, humidifier and climate devices. Never auto-enroll.
    entities.extend(EquipmentPowerSwitchSelect(manager, spec)
                    for spec in equipment.specs(manager))
    from homeassistant.helpers import entity_registry as er
    from .equipment_feature_registration import (
        quiet_keys, register_late_capabilities, registered_control,
        pid_calibration_supported,
    )
    registry = er.async_get(hass)

    def native_feature_selects():
        selection = []
        for spec in equipment.specs(manager):
            if pid_calibration_supported(manager, registry, spec, platform="select"):
                selection.append(EquipmentSelect(manager, spec, "pid_calibration_method"))
            selection.extend(EquipmentSelect(manager, spec, key)
                for key in quiet_keys(manager, registry, spec, platform="select"))
            cap = equipment.capabilities(manager, spec)
            active = bool(
                cap and cap.domain in ("climate", "humidifier")
                and cap.fan_modes and "pid" in equipment.control_modes(manager, spec)
            )
            for key in ("pid_fan_capacity_mode", "pid_fan_capacity_for_mode"):
                if active or registered_control(registry, "select", spec, key):
                    selection.append(EquipmentSelect(manager, spec, key))
        return selection

    entities.extend(native_feature_selects())
    from .const import CONF_AREAS
    entities.extend(AreaScienceSource(manager, entry.entry_id, area, key)
                    for area in manager.settings.get(CONF_AREAS, [])
                    for key in ("radiant_temperature_entity", "air_speed_entity"))
    entities.extend(EquipmentSelect(manager, spec, key)
                    for spec in equipment.specs(manager)
                    for key in equipment.DEVICE_SELECTS
                    if key != "fan_purpose" or (cap := equipment.capabilities(manager, spec)) is not None
                    and (cap.domain == "fan" or set(cap.modes) == {"off", "fan_only"}))
    from .room_sources import selected
    from .const import CONF_AREAS
    for area in manager.settings.get(CONF_AREAS, []):
        for cover in selected(manager.settings, area, "shades") or ():
            entities.append(ShadeWindowSelect(manager, entry.entry_id, area, cover))
    async_add_grouped_entities(entry.runtime_data, async_add_entities, entities)
    register_late_capabilities(
        hass, entry, async_add_entities, entities, native_feature_selects,
    )


class TTSLanguageSelect(SelectEntity):
    """Show human language names while persisting provider-compatible BCP47 tags."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "home_language"
    _attr_icon = "mdi:translate"

    def __init__(self, manager, entry_id):
        self._manager = manager
        self._attr_unique_id = f"{entry_id}_home_language"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry_id)}}

    def _choices(self):
        from .tts_languages import language_options
        return language_options(self._manager.hass, self._manager.settings.get("tts_engine"))

    @property
    def options(self):
        return [item["label"] for item in self._choices()]

    @property
    def current_option(self):
        from .tts_languages import preferred_language
        value = preferred_language(
            self._manager.hass, self._manager.settings.get("tts_engine"),
            self._manager.settings.get("language", "auto"))
        return next((item["label"] for item in self._choices() if item["value"] == value),
                    self.options[0] if self.options else None)

    async def async_select_option(self, option: str):
        match = next((item for item in self._choices() if item["label"] == option), None)
        if match is None:
            raise ValueError("Unknown TTS language")
        await update_device_setting(self._manager, "global_setting", "language", match["value"])
        self.async_write_ha_state()


class ConfigSelect(SelectEntity):
    """Only supervisor profile/gain-source and language, never native HVAC mode."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager, entry_id, area, kind, options, *,
                 setting_key=None, entity_id=None):
        self._manager = manager
        self._area_id = area
        self._kind = kind
        self._setting_key = setting_key or kind
        self._entity_id = entity_id
        self._attr_options = list(options)
        if kind == "pid_gain_source":
            self._attr_has_entity_name = False
            locale = getattr(getattr(manager.hass, "config", None), "language", "en")
            self._attr_name = localized_room_pid_name(
                "area_pid_gain_source", locale
            )
        suffix = f"{kind}_{self._setting_key}" if setting_key else kind
        if entity_id:
            suffix = f"{kind}_{entity_id.replace('.', '_')}_{self._setting_key}"
            self._attr_name = f"{entity_id} · {self._setting_key.replace('_', ' ')}"
        else:
            self._attr_translation_key = (
                f"home_{suffix}" if area is None else f"area_{suffix}"
            )
        self._attr_unique_id = (
            f"{entry_id}_home_{suffix}" if area is None else
            f"{entry_id}_area_{area}_{suffix}"
        )
        self._attr_device_info = {"identifiers": {
            (DOMAIN, entry_id if area is None else f"{entry_id}_area_{area}")
        }}
        if kind == "device_policy" and entity_id:
            child = controller_device_info(manager, area, entity_id)
            if child is None:
                raise ValueError("Controller source is not registered in this area hub")
            self._attr_device_info = child
        self._attr_icon = (
            "mdi:translate" if area is None else
            "mdi:tune-variant" if kind == "pid_gain_source" else
            "mdi:home-thermometer"
        )

    @property
    def current_option(self):
        settings = self._manager.settings
        if self._kind == "language":
            lang = settings.get("language", "auto")
            return lang if lang in LANGUAGES else "auto"
        if self._kind == "manual_profile":
            config = climate_settings(settings, self._area_id)
            option = config.get("manual_profile", "auto") if config else "auto"
            return option if option in PROFILE_OPTIONS else "auto"
        if self._kind == "pid_gain_source":
            config = pid_settings(settings, self._area_id)
            return tuning_source(config) if config else "defaults"
        if self._kind == "aqi_scale":
            env = settings.get("environment_global", {})
            scales = env.get("aqi_scales", {}) if isinstance(env, dict) else {}
            cfg = scales.get(self._entity_id, {}) if isinstance(scales, dict) else {}
            return cfg.get("scale", "not_configured") if isinstance(cfg, dict) else "not_configured"
        if self._kind == "global_policy":
            cfg = settings.get("occupancy_global", {})
            return cfg.get(self._setting_key, "any_home") if isinstance(cfg, dict) else "any_home"
        cfg = settings.get("climate_rooms", {}).get(self._area_id, {})
        if self._kind == "device_policy":
            devices = cfg.get("device_settings", {}) if isinstance(cfg, dict) else {}
            dev = devices.get(self._entity_id, {}) if isinstance(devices, dict) else {}
            fallback = "always" if self._setting_key == "presence_requirement" else "normal"
            return dev.get(self._setting_key, fallback) if isinstance(dev, dict) else fallback
        defaults = {
            "unknown_occupancy": "occupied",
            "away_policy": "any_home",
            "target_source": "temperature",
        }
        return cfg.get(self._setting_key, defaults[self._setting_key]) if isinstance(cfg, dict) else defaults[self._setting_key]

    async def async_select_option(self, option: str):
        if option not in self._attr_options:
            raise ValueError("Unknown selectable device option")
        if self._kind == "language":
            await update_device_setting(self._manager, "global_setting", "language", option)
        elif self._kind == "manual_profile":
            await update_device_setting(self._manager, "profile", "manual_profile", option,
                                        area=self._area_id)
        elif self._kind == "pid_gain_source":
            await update_device_setting(self._manager, "pid_gain_source",
                                        "tuning_source", option, area=self._area_id)
        else:
            await update_device_setting(
                self._manager, self._kind, self._setting_key, option,
                area=self._area_id, entity_id=self._entity_id
            )
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


from .equipment_entity import EquipmentEntity
from . import equipment_model as equipment


class EquipmentSelect(EquipmentEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager, spec, key):
        self._equipment_init(manager, spec, key)

    @property
    def available(self):
        if self._key == "quiet_fan_mode":
            cap = equipment.capabilities(self._manager, self._spec)
            return bool(cap and cap.fan_modes and not cap.fan_percentage)
        if self._key == "pid_calibration_method":
            # Show persisted setup across device startup, but allow edits only
            # after the physical endpoint re-advertises native DRY/PID support.
            cap = equipment.capabilities(self._manager, self._spec)
            return bool(cap is not None and
                        self.controller_settings["control_mode"] == "pid"
                        and "pid" in equipment.control_modes(self._manager, self._spec))
        if self._key in ("pid_fan_capacity_mode", "pid_fan_capacity_for_mode"):
            cap = equipment.capabilities(self._manager, self._spec)
            return bool(cap and cap.fan_modes
                        and cap.domain in ("climate", "humidifier")
                        and self.controller_settings["control_mode"] == "pid")
        return super().available

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self._key in ("control_mode", "quiet_fan_mode",
                         "pid_calibration_method", "pid_fan_capacity_mode",
                         "pid_fan_capacity_for_mode"):
            # Native mode/feature changes can turn DRY-only PID support on
            # after integration setup. Refresh selector options immediately.
            self._watch_native_updates()

    @property
    def options(self):
        if self._key == "control_mode":
            return list(equipment.control_modes(self._manager, self._spec))
        if self._key == "pid_calibration_method":
            return list(equipment.PID_CALIBRATION_METHODS)
        if self._key == "pid_fan_capacity_mode":
            return list(equipment.PID_FAN_CAPACITY_METHODS)
        if self._key == "pid_fan_capacity_for_mode":
            cap = equipment.capabilities(self._manager, self._spec)
            return ["choose", *(mode for mode in (cap.modes if cap else ())
                if mode in equipment.PID_FAN_DIRECTIONS)]
        if self._key in equipment.DEVICE_SELECTS:
            return list(equipment.DEVICE_SELECTS[self._key])
        cap = equipment.capabilities(self._manager, self._spec)
        return list(cap.fan_modes) if cap else []

    @property
    def extra_state_attributes(self):
        attributes = super().extra_state_attributes
        if self._key in ("pid_fan_capacity_mode", "pid_fan_capacity_for_mode"):
            return {**attributes, "pid_fan_capacity_role":
                "strategy" if self._key == "pid_fan_capacity_mode" else "direction"}
        if self._key == "pid_calibration_method":
            return {**attributes, "pid_calibration_role": "method"}
        return attributes

    @property
    def current_option(self):
        value = self.controller_settings.get(self._key)
        if self._key == "quiet_fan_mode" and value is None and "low" in self.options:
            return "low"
        return value if value in self.options else None

    async def async_select_option(self, option):
        await self._manager.equipment.async_update(self._spec, {self._key: option})


class EquipmentPowerSwitchSelect(EquipmentSelect):
    """Dynamic friendly labels, with stable persisted native switch entity IDs.

    Discover candidates once; only state changes for these exact candidate
    switches invalidate the displayed options. Avoid global event listeners
    and repeated whole-registry scans during HA startup and state updates.
    """

    _attr_icon = "mdi:power-plug"

    def __init__(self, manager, spec):
        super().__init__(manager, spec, "power_switch_entity")
        self._power_switch_entity_ids: tuple[str, ...] | None = None
        self._power_switch_display_options: tuple[str, ...] | None = None
        self._power_switch_id_to_label: dict[str, str] = {}
        self._power_switch_label_to_id: dict[str, str] = {}

    @property
    def available(self):
        return True

    def _entity_ids(self) -> tuple[str, ...]:
        if self._power_switch_entity_ids is None:
            from .equipment_power_switch import supply_options
            self._power_switch_entity_ids = supply_options(self._manager, self._spec)
        return self._power_switch_entity_ids

    def _display_options(self) -> tuple[str, ...]:
        if self._power_switch_display_options is None:
            from .equipment_power_switch import supply_option_labels
            labels = supply_option_labels(self._manager.hass, self._entity_ids())
            self._power_switch_id_to_label = labels
            self._power_switch_label_to_id = {
                label: entity for entity, label in labels.items()
            }
            self._power_switch_display_options = (
                "none", *(labels[entity] for entity in self._entity_ids())
            )
        return self._power_switch_display_options

    @property
    def options(self):
        return list(self._display_options())

    @property
    def current_option(self):
        self._display_options()
        selected = self.controller_settings.get("power_switch_entity")
        return self._power_switch_id_to_label.get(selected, "none")

    @property
    def extra_state_attributes(self):
        return {
            **super().extra_state_attributes,
            "selected_power_switch_entity_id": (
                self.controller_settings.get("power_switch_entity")
            ),
        }

    async def async_select_option(self, option):
        self._display_options()
        if option == "none":
            entity = None
        else:
            entity = self._power_switch_label_to_id.get(option)
            # Support existing service callers supplying the native ID.
            if entity is None and option in self._entity_ids():
                entity = option
            if entity is None:
                raise ValueError("Unrecognized upstream power switch")
        await self._manager.equipment.async_update(
            self._spec, {"power_switch_entity": entity}
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        entities = self._entity_ids()
        if not entities:
            return
        from homeassistant.helpers.event import async_track_state_change_event

        @callback
        def _supply_state_changed(event):
            previous = event.data.get("old_state")
            current = event.data.get("new_state")
            if (previous is not None and current is not None
                    and previous.state == current.state
                    and previous.name == current.name):
                return
            self._power_switch_display_options = None
            self.async_write_ha_state()

        self.async_on_remove(async_track_state_change_event(
            self.hass, entities, _supply_state_changed
        ))


class AreaScienceSource(ConfigSelect):
    """Optional measured radiant/air-speed pins; never invent PMV inputs."""

    def __init__(self, manager, entry_id, area, key):
        super().__init__(manager, entry_id, area, "area_science", (), setting_key=key)

    @property
    def options(self):
        from .device_controls import science_source_options
        return list(science_source_options(self._manager, self._area_id, self._setting_key))

    @property
    def current_option(self):
        return self._manager.settings.get("environment_rooms", {}).get(self._area_id, {}).get(self._setting_key) or "none"

    async def async_select_option(self, option):
        await update_device_setting(self._manager, "area_science", self._setting_key, option, area=self._area_id)
        self.async_write_ha_state()


class ShadeWindowSelect(SelectEntity):
    """Select the exact physical window contact assigned to one motorized cover."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "shade_window_entity"
    _attr_icon = "mdi:window-closed-variant"

    def __init__(self, manager, entry_id: str, area: str, cover: str):
        self._manager, self._area, self._cover = manager, area, cover
        self._attr_unique_id = (
            f"{entry_id}_area_{area}_shade_{cover.replace('.', '_')}_window")
        self._attr_device_info = controller_device_info(manager, area, cover)
        if self._attr_device_info is None:
            raise ValueError("No registered per-cover controller for this room")

    def _window_options(self) -> dict[str, str | None]:
        from .shade_cooling import selectable_windows
        # Include the entity_id to disambiguate two identically named windows.
        result: dict[str, str | None] = {"Not assigned": None}
        for entity in selectable_windows(
                self._manager.hass, self._manager.settings, self._area):
            state = self._manager.hass.states.get(entity)
            name = getattr(state, "name", None) or entity
            result[f"{name} ({entity})"] = entity
        return result

    @property
    def options(self):
        return list(self._window_options())

    @property
    def current_option(self):
        from .shade_cooling import cover_config
        saved = cover_config(
            self._manager.settings, self._area, self._cover)["window_entity"]
        return next((label for label, item in self._window_options().items()
                     if item == saved), "Not assigned")

    @property
    def extra_state_attributes(self):
        from .shade_cooling import cover_config
        contact_id = cover_config(
            self._manager.settings, self._area, self._cover)["window_entity"]
        state = self._manager.hass.states.get(contact_id) if contact_id else None
        raw = getattr(state, "state", None)
        window_status = (
            "open" if raw == "on" else "closed" if raw == "off"
            else "unknown")
        return {"window_entity_id": contact_id, "window_state": window_status,
                "source_cover": self._cover}

    async def async_select_option(self, option: str):
        choices = self._window_options()
        if option not in choices:
            raise ValueError("Select a real Window-class contact assigned to this room")
        await update_device_setting(
            self._manager, "shade_device", "window_entity", choices[option],
            area=self._area, entity_id=self._cover,
        )
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
