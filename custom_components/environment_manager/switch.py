"""Home-wide opt-in announcement switches on the home device."""
from __future__ import annotations

from .room_hubs import async_add_grouped_entities

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import (
    CONF_AUTO_NOTIFY, CONF_AUTO_TTS, CONF_HUB, CONF_AI_REWRITE,
    CONF_SHADE_ANNOUNCE, DOMAIN, SIGNAL_UPDATED,
)
from .device_controls import update_device_setting

CONTROLS = (CONF_AUTO_NOTIFY, CONF_AUTO_TTS, CONF_HUB, CONF_AI_REWRITE,
            CONF_SHADE_ANNOUNCE)


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
        quiet_keys, register_late_capabilities,
    )
    registry = er.async_get(hass)

    def native_quiet_switches():
        return [
            EquipmentQuietSwitch(manager, spec, key)
            for spec in equipment.specs(manager)
            for key in quiet_keys(manager, registry, spec, platform="switch")
        ]

    entities.extend(native_quiet_switches())
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
            for key in ("enabled", "announce"):
                entities.append(ShadeDeviceSwitch(manager, entry.entry_id, area, cover, key))
    async_add_grouped_entities(entry.runtime_data, async_add_entities, entities)
    register_late_capabilities(
        hass, entry, async_add_entities, entities, native_quiet_switches,
    )


class HomeSettingSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager, entry_id, key, *, kind="global_setting", area=None):
        self._manager = manager
        self._key = key
        self._kind = kind
        self._area = area
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
            return None
        room = self._manager.settings.get("environment_rooms", {}).get(self._area, {})
        needed = [key for key in ("radiant_temperature_entity", "met", "clo") if room.get(key) is None]
        if not room.get("air_speed_entity") and room.get("air_speed_m_s") is None:
            needed.append("air_speed")
        return {"missing_configured_inputs": needed,
                "input_validation": "pending_inputs" if needed else "live_measurements_required"}

    async def async_turn_on(self, **kwargs):
        await update_device_setting(self._manager, self._kind, self._key, True, area=self._area)
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


class EquipmentQuietSwitch(EquipmentEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:fan-speed-1"

    def __init__(self, manager, spec, key):
        self._equipment_init(manager, spec, key)
        self._attr_icon = {"sensor_verified": "mdi:check-decagram-outline"}.get(key, "mdi:fan-speed-1")

    @property
    def available(self):
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

    async def async_turn_on(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {self._key: True})

    async def async_turn_off(self, **kwargs):
        await self._manager.equipment.async_update(self._spec, {self._key: False})


class ShadeCoolingSwitch(SwitchEntity):
    """Explicit room-level permission to CLOSE selected window shades only."""

    _attr_has_entity_name = True
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


class ShadeDeviceSwitch(SwitchEntity):
    """Cover-specific automation and advance-announcement permissions."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager, entry_id: str, area: str, cover: str, key: str):
        from .device_hierarchy import controller_device_info
        self._manager, self._area, self._cover, self._key = (
            manager, area, cover, key)
        self._attr_unique_id = (
            f"{entry_id}_area_{area}_shade_{cover.replace('.', '_')}_{key}")
        self._attr_translation_key = f"shade_{'auto_control' if key == 'enabled' else 'announce'}"
        self._attr_icon = "mdi:blinds" if key == "enabled" else "mdi:bullhorn-outline"
        self._attr_device_info = controller_device_info(manager, area, cover)
        if self._attr_device_info is None:
            raise ValueError("Shade controller requires a registered same-room device")

    @property
    def is_on(self) -> bool:
        from .shade_cooling import cover_config
        return cover_config(self._manager.settings, self._area, self._cover)[self._key] is True

    @property
    def extra_state_attributes(self):
        from .shade_cooling import cover_config
        status = getattr(self._manager.shading, "statuses", {}).get(self._area, {})
        per_cover = status.get("covers", {})
        cfg = cover_config(self._manager.settings, self._area, self._cover)
        return {
            "source_cover": self._cover,
            "assigned_window": cfg["window_entity"],
            "cover_status": per_cover.get(self._cover),
            "manual_override_paused": per_cover.get(self._cover) == "manual_override",
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
