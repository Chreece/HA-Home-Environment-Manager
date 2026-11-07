"""Home-wide opt-in announcement switches on the home device."""
from __future__ import annotations

from .room_hubs import async_add_grouped_entities
from .settings_help import SettingsMetadata

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import (
    CONF_AUTO_NOTIFY, CONF_AUTO_TTS, CONF_HUB, CONF_AI_REWRITE,
    CONF_SHADE_ANNOUNCE, CONF_AWAY_WINDOWS_ALERT, DOMAIN, SIGNAL_UPDATED,
)
from .device_controls import update_device_setting

CONTROLS = (CONF_AUTO_NOTIFY, CONF_AUTO_TTS, CONF_HUB, CONF_AI_REWRITE,
            CONF_SHADE_ANNOUNCE, CONF_AWAY_WINDOWS_ALERT)


async def async_setup_entry(hass, entry, async_add_entities):
    manager = entry.runtime_data
    from .device_hierarchy import configured_area_ids
    from .device_controls import AREA_ENV_FLAGS, CLIMATE_OPERATING_FLAGS, GLOBAL_ENV_FLAGS
    from .const import CONF_AREAS
    from .device_controls import climate_settings
    entities = [HomeSettingSwitch(manager, entry.entry_id, key) for key in CONTROLS]
    entities.extend(
        HomeSettingSwitch(manager, entry.entry_id, key, kind="global_environment")
        for key in GLOBAL_ENV_FLAGS
    )
    for area in configured_area_ids(manager.settings):
        if area in manager.settings.get(CONF_AREAS, []):
            entities.extend(HomeSettingSwitch(
                manager, entry.entry_id, key, kind="area_environment", area=area,
            ) for key in AREA_ENV_FLAGS)
        if climate_settings(manager.settings, area) is not None:
            entities.extend(HomeSettingSwitch(
                manager, entry.entry_id, key, kind="climate_operating", area=area,
            ) for key in CLIMATE_OPERATING_FLAGS)
    from . import equipment_model as equipment
    from homeassistant.helpers import entity_registry as er
    from .equipment_feature_registration import (
        quiet_keys, register_late_capabilities, remove_legacy_timed_controls, native_full_output_supported,
        window_alternative_settings_supported,
    )
    registry = er.async_get(hass)
    remove_legacy_timed_controls(hass, entry)

    def native_feature_switches():
        from .equipment_mode_entities import scoped_fields
        return [
            EquipmentQuietSwitch(manager, spec, key)
            for spec in equipment.specs(manager)
            for key in quiet_keys(manager, registry, spec, platform="switch")
        ] + [
            EquipmentNativeFullOutputSwitch(manager, spec)
            for spec in equipment.specs(manager)
            if native_full_output_supported(manager, registry, spec)
        ] + [
            EquipmentWindowAnnouncementSwitch(manager, spec)
            for spec in equipment.specs(manager)
            if window_alternative_settings_supported(
                manager, registry, spec, platform="switch")
        ] + [
            EquipmentQuietSwitch(manager, spec, key, operating_mode=mode)
            for spec in equipment.specs(manager)
            for mode, key in scoped_fields(manager, spec, "switch")
        ]

    entities.extend(native_feature_switches())
    entities.extend(EquipmentWindowPauseSwitch(manager, spec)
                    for spec in equipment.specs(manager))
    entities.extend(EquipmentHouseholdSleepSwitch(manager, spec)
                    for spec in equipment.specs(manager))
    # ONLY a per-device announcement setting is new. Error evidence is
    # read directly from the manufacturer's existing HA entities/attributes.
    entities.extend(EquipmentErrorAnnouncementSwitch(manager, spec)
                    for spec in equipment.specs(manager))
    entities.extend(EquipmentQuietSwitch(manager, spec, "sensor_verified")
                    for spec in equipment.specs(manager)
                    if (cap := equipment.capabilities(manager, spec)) is not None
                    and (cap.domain == "fan" or set(cap.modes) == {"off", "fan_only"}))
    from .room_sources import selected
    for area in manager.settings.get(CONF_AREAS, []):
        covers = selected(manager.settings, area, "shades") or ()
        if covers:
            entities.append(ShadeCoolingSwitch(manager, entry.entry_id, area))
        for cover in covers:
            for key in ("enabled", "announce", "lux_enabled"):
                entities.append(ShadeDeviceSwitch(manager, entry.entry_id, area, cover, key))
    async_add_grouped_entities(entry.runtime_data, async_add_entities, entities)
    register_late_capabilities(
        hass, entry, async_add_entities, entities, native_feature_switches,
        policy_changes=True,
    )


class HomeSettingSwitch(SettingsMetadata, SwitchEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager, entry_id, key, *, kind="global_setting", area=None):
        self._manager = manager
        self._key = key
        self._kind = kind
        self._area = area
        if kind == "area_environment" and key == "enable_pmv":
            from .advanced_comfort import advanced_comfort_enabled
            self._attr_entity_registry_enabled_default = advanced_comfort_enabled(
                manager.settings, area,
            )
        self._attr_unique_id = (
            f"{entry_id}_area_{area}_{kind}_{key}" if area else
            f"{entry_id}_home_{kind}_{key}" if kind != "global_setting" else
            f"{entry_id}_home_{key}"
        )
        self._attr_translation_key = (
            f"area_{kind}_{key}" if area else
            f"home_{kind}_{key}" if kind != "global_setting" else f"home_{key}"
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_area_{area}" if area else entry_id)}
        }
        self._attr_icon = {
            CONF_AUTO_NOTIFY: "mdi:message-badge-outline",
            CONF_AUTO_TTS: "mdi:account-voice",
            CONF_HUB: "mdi:home-assistant",
            CONF_AI_REWRITE: "mdi:robot-outline",
            CONF_SHADE_ANNOUNCE: "mdi:blinds-horizontal",
            CONF_AWAY_WINDOWS_ALERT: "mdi:window-open-variant",
            "pollen_avoid_ventilation": "mdi:flower-pollen",
            "sleep_room": "mdi:bed",
            "enable_pmv": "mdi:human-male-board-poll",
            "sleep_active": "mdi:sleep",
            "sleep_schedule_enabled": "mdi:clock-check-outline",
            "window_efficiency_notify": "mdi:window-open-variant",
        }.get(key, "mdi:cog")

    @property
    def is_on(self):
        settings = self._manager.settings
        if self._kind == "global_setting":
            return settings.get(self._key, False) is True
        section = "environment_global" if self._kind == "global_environment" else (
            "environment_rooms" if self._kind == "area_environment" else "climate_rooms"
        )
        cfg = settings.get(section, {})
        if self._area:
            cfg = cfg.get(self._area, {}) if isinstance(cfg, dict) else {}
        return isinstance(cfg, dict) and cfg.get(self._key, False) is True

    @property
    def extra_state_attributes(self):
        if self._key != "enable_pmv" or not self._area:
            return super().extra_state_attributes
        room = self._manager.settings.get("environment_rooms", {}).get(self._area, {})
        needed = [key for key in ("radiant_temperature_entity", "met", "clo") if room.get(key) is None]
        if not room.get("air_speed_entity") and room.get("air_speed_m_s") is None:
            needed.append("air_speed")
        return {**super().extra_state_attributes,
                "missing_configured_inputs": needed,
                "input_validation": "pending_inputs" if needed else "live_measurements_required"}

    async def async_turn_on(self, **kwargs):
        await update_device_setting(self._manager, self._kind, self._key, True, area=self._area)
        if self._kind == "area_environment" and self._key == "enable_pmv":
            from .advanced_comfort import async_enable_advanced_controls
            async_enable_advanced_controls(
                self.hass, self._manager.entry, self._area, include_switch=False,
            )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await update_device_setting(self._manager, self._kind, self._key, False, area=self._area)
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


def _device_option_metadata(entity):
    """Identify shared device policies without parsing a translated entity ID."""
    if getattr(entity, "_operating_mode", None):
        return {}  # Scoped controls already expose their own setting metadata.
    from .equipment_name_catalog import localized_equipment_name
    locale = entity._manager.settings.get("language", "auto")
    if locale == "auto":
        locale = getattr(getattr(entity._manager.hass, "config", None), "language", "en")
    if entity._key == "native_full_output":
        from .equipment_native_target import configuration_modes
        from .equipment_name_catalog import native_full_output_label
        modes = configuration_modes(entity._manager, entity._spec)
        return {"setting_key": entity._key,
                "setting_label": native_full_output_label(modes, locale),
                "native_full_output_modes": list(modes),
                "equipment_option_role": "policy"}
    full = localized_equipment_name(entity._key, locale)
    label = full.partition(" · ")[2] or full.rstrip(" ·")
    return {"setting_key": entity._key, "setting_label": label,
            "equipment_option_role": "policy"}


class EquipmentQuietSwitch(EquipmentEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:fan-speed-1"

    def __init__(self, manager, spec, key, *, operating_mode=None):
        self._equipment_init(manager, spec, key, operating_mode=operating_mode)
        self._attr_icon = {"sensor_verified": "mdi:check-decagram-outline"}.get(key, "mdi:fan-speed-1")

    @property
    def available(self):
        if getattr(self, "_operating_mode", None):
            descriptor = equipment.mode_descriptor(self._manager, self._spec, self._operating_mode)
            return bool(descriptor and self._key in descriptor.get("switch_fields", ()))
        if self._key in equipment.QUIET_FLAGS:
            cap = equipment.capabilities(self._manager, self._spec)
            return bool(cap and cap.fan_modes)
        return super().available

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self._key in equipment.QUIET_FLAGS:
            self._watch_native_updates()

    @property
    def is_on(self):
        return self.controller_settings.get(self._key) is True

    @property
    def extra_state_attributes(self):
        return {**super().extra_state_attributes, **_device_option_metadata(self)}

    async def async_turn_on(self, **kwargs):
        await self._async_update_controller_settings({self._key: True})

    async def async_turn_off(self, **kwargs):
        await self._async_update_controller_settings({self._key: False})


class EquipmentErrorAnnouncementSwitch(EquipmentEntity, SwitchEntity):
    """Default-ON alerts for the physical device's existing HA error sources.

    This switch changes only a stored HEM preference. It remains available
    even if the native device itself temporarily disappears and never sends
    any native device or relay power command.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, manager, spec):
        self._equipment_init(manager, spec, "announce_device_errors")

    @property
    def available(self):
        return self._manager.faults.active

    @property
    def is_on(self):
        return self.controller_settings.get("announce_device_errors", True) is True

    @property
    def extra_state_attributes(self):
        return {
            **super().extra_state_attributes,
            **_device_option_metadata(self),
            "device_fault_role": "announce",
            # Read-only summary of the *original* physical HA fault entity.
            # No additional native/HEM error sensor is registered.
            "native_error": self._manager.faults.details(self._spec),
        }

    async def async_turn_on(self, **kwargs):
        await self._manager.faults.async_set_announcements(self._spec, True)

    async def async_turn_off(self, **kwargs):
        await self._manager.faults.async_set_announcements(self._spec, False)


class EquipmentNativeFullOutputSwitch(EquipmentEntity, SwitchEntity):
    """Choose the optional native full-demand target without operating power."""
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:target-variant"

    def __init__(self, manager, spec):
        self._equipment_init(manager, spec, "native_full_output")

    @property
    def available(self):
        from .equipment_native_target import control_supported
        return bool(self._manager.equipment._ready
                    and control_supported(self._manager, self._spec, cached=True))

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._watch_native_updates()

    @property
    def is_on(self):
        return self.controller_settings.get("native_full_output", True) is True

    @property
    def extra_state_attributes(self):
        from .equipment_native_target import control_supported
        return {**super().extra_state_attributes, **_device_option_metadata(self),
                "native_full_output_role": "policy",
                "native_full_output_supported": control_supported(self._manager, self._spec, cached=True)}

    async def async_turn_on(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {"native_full_output": True})

    async def async_turn_off(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {"native_full_output": False})


class EquipmentHouseholdSleepSwitch(EquipmentEntity, SwitchEntity):
    """Follow household sleep on this controller, independently of other devices."""
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:bed-clock"

    def __init__(self, manager, spec):
        self._equipment_init(manager, spec, "sleep_when_everyone_asleep")

    @property
    def available(self):
        return self._manager.equipment._ready

    @property
    def is_on(self):
        return self.controller_settings.get(self._key) is True

    @property
    def extra_state_attributes(self):
        return {**super().extra_state_attributes, **_device_option_metadata(self)}

    async def async_turn_on(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {self._key: True})

    async def async_turn_off(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {self._key: False})


class EquipmentWindowAnnouncementSwitch(EquipmentEntity, SwitchEntity):
    """Opt this device into a bounded airing request before automatic start."""
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:window-open-variant"

    def __init__(self, manager, spec):
        self._equipment_init(manager, spec, "announce_before_start")

    @property
    def available(self):
        return self._manager.equipment._ready

    @property
    def is_on(self):
        return self.controller_settings.get(self._key) is True

    @property
    def extra_state_attributes(self):
        return {**super().extra_state_attributes, **_device_option_metadata(self),
                "window_announcement_role": "policy"}

    async def async_turn_on(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {self._key: True})

    async def async_turn_off(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {self._key: False})


class EquipmentWindowPauseSwitch(EquipmentEntity, SwitchEntity):
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
        return {**super().extra_state_attributes, **_device_option_metadata(self),
                "window_pause_role": "policy",
                "window_resume_delay_seconds": 60}

    async def async_turn_on(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {"pause_on_window_open": True})

    async def async_turn_off(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {"pause_on_window_open": False})


class ShadeCoolingSwitch(SettingsMetadata, SwitchEntity):
    """Explicit room-level permission to CLOSE selected window shades only."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "area_shading_enabled"
    _attr_icon = "mdi:blinds"

    def __init__(self, manager, entry_id: str, area: str):
        self._manager, self._area = manager, area
        self._attr_unique_id = f"{entry_id}_area_{area}_shade_cooling_enabled"
        self._attr_device_info = {"identifiers": {(DOMAIN, f"{entry_id}_area_{area}")}}

    @property
    def is_on(self) -> bool:
        from .shade_cooling import config
        return config(self._manager.settings, self._area)["enabled"]

    @property
    def extra_state_attributes(self):
        from .room_sources import selected
        status = getattr(self._manager, "shading", None)
        return {
            **super().extra_state_attributes,
            "area_id": self._area,
            "selected_shades": list(selected(self._manager.settings, self._area, "shades") or ()),
            "close_only": True,
            "controller_status": status.statuses.get(self._area) if status else None,
        }

    async def async_turn_on(self, **kwargs):
        await update_device_setting(self._manager, "area_shading", "enabled", True,
                                    area=self._area)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await update_device_setting(self._manager, "area_shading", "enabled", False,
                                    area=self._area)
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


class ShadeDeviceSwitch(SettingsMetadata, SwitchEntity):
    """Cover-specific automation and advance-announcement permissions."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager, entry_id: str, area: str, cover: str, key: str):
        from .device_hierarchy import controller_device_info
        self._manager, self._area, self._cover, self._key = (
            manager, area, cover, key)
        self._attr_unique_id = (
            f"{entry_id}_area_{area}_shade_{cover.replace('.', '_')}_{key}")
        self._attr_translation_key = f"shade_{'auto_control' if key == 'enabled' else 'lux_enabled' if key == 'lux_enabled' else 'announce'}"
        self._attr_icon = ("mdi:brightness-5" if key == "lux_enabled"
                           else "mdi:blinds" if key == "enabled" else "mdi:bullhorn-outline")
        self._attr_device_info = controller_device_info(manager, area, cover)
        if self._attr_device_info is None:
            raise ValueError("Shade controller requires a registered same-room device")

    @property
    def is_on(self) -> bool:
        from .shade_cooling import cover_config
        cfg = cover_config(self._manager.settings, self._area, self._cover)
        if self._key == "enabled" and cfg["enabled"]:
            # A resident override makes the automatic switch appear paused,
            # allowing one deliberate turn-on to rearm this exact cover.
            record = getattr(self._manager.shading, "_records", {}).get(self._cover, {})
            if record.get("phase") in ("manual_override", "legacy_manual_hold"):
                return False
        return cfg[self._key] is True

    @property
    def extra_state_attributes(self):
        from .shade_cooling import cover_config
        status = getattr(self._manager.shading, "statuses", {}).get(self._area, {})
        per_cover = status.get("covers", {})
        cfg = cover_config(self._manager.settings, self._area, self._cover)
        return {
            **super().extra_state_attributes,
            "source_cover": self._cover,
            "assigned_window": cfg["window_entity"],
            "cover_status": per_cover.get(self._cover),
            "manual_override_paused": per_cover.get(self._cover) == "manual_override",
            "lux_sensor": cfg.get("lux_entity"),
            "lux_threshold_lx": cfg.get("min_lux"),
            "lux_enabled": cfg.get("lux_enabled"),
        }

    async def async_turn_on(self, **kwargs):
        await update_device_setting(
            self._manager, "shade_device", self._key, True,
            area=self._area, entity_id=self._cover,
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await update_device_setting(
            self._manager, "shade_device", self._key, False,
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
