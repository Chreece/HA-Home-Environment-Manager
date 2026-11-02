"""Opt-in per-area manual mold calibration. No actuator services."""
from __future__ import annotations

from .room_hubs import async_add_grouped_entities

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .const import CONF_AREAS, CONF_USE_MOLD, CONF_MOLD_ROOMS, DOMAIN
from .mold_controls import async_recalculate_mold_factor


async def async_setup_entry(hass, entry, async_add_entities):
    settings = entry.runtime_data.settings
    manager = entry.runtime_data
    from . import equipment_model as equipment
    from .equipment_feature_registration import (
        pid_calibration_supported, registered_control, register_late_capabilities,
    )
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    controllers = equipment.specs(manager)

    def native_calibration_buttons():
        result = []
        for spec in equipment.specs(manager):
            if pid_calibration_supported(manager, registry, spec, platform="button"):
                result.append(EquipmentCalibrationButton(manager, spec))
                result.extend(
                    EquipmentPIDReviewButton(manager, spec, action)
                    for action in ("approve", "discard")
                )
            cap = equipment.capabilities(manager, spec)
            if (cap is not None and cap.domain in ("climate", "humidifier")
                    and cap.fan_modes and "pid" in equipment.control_modes(manager, spec)
                    or registered_control(registry, "button", spec,
                                          "pid_apply_fan_capacity")):
                result.append(EquipmentFanCapacityButton(manager, spec))
        return result

    buttons = [
        *(EquipmentResumeButton(manager, spec) for spec in controllers),
        *native_calibration_buttons(),
    ]
    async_add_grouped_entities(manager, async_add_entities, buttons)
    # The physical climate/humidity attributes may arrive after platform
    # forwarding. Register only newly qualified controls, never duplicate IDs.
    register_late_capabilities(
        hass, entry, async_add_entities, buttons, native_calibration_buttons,
    )
    if settings.get(CONF_USE_MOLD) is not True:
        return
    async_add_grouped_entities(entry.runtime_data, async_add_entities, [
        AreaMoldCalibrationButton(entry.runtime_data, entry.entry_id, area)
        for area in settings.get(CONF_AREAS, [])
        if isinstance(area, str)
    ])


class AreaMoldCalibrationButton(ButtonEntity):
    """Recalculate using fresh room/outside sensors and user-measured surface °C."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "area_recalculate_mold"
    _attr_icon = "mdi:calculator-variant-outline"

    def __init__(self, manager, entry_id, area):
        self._manager = manager
        self._area = area
        self._attr_unique_id = f"{entry_id}_area_{area}_mold_recalibrate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_area_{area}")},
        }

    async def async_press(self):
        await async_recalculate_mold_factor(self._manager, self._area)

    @property
    def extra_state_attributes(self):
        rooms = self._manager.settings.get(CONF_MOLD_ROOMS, {})
        saved = rooms.get(self._area, {}) if isinstance(rooms, dict) else {}
        if not isinstance(saved, dict):
            saved = {}
        return {
            "calibration_factor": saved.get("calibration_factor"),
            "calibrated_at": saved.get("calibrated_at"),
            "indoor_temperature_entity": saved.get("indoor_temperature_entity"),
            "indoor_temperature_entities": saved.get("indoor_temperature_entities"),
            "outdoor_weather_entity": saved.get("outdoor_weather_entity"),
            "outdoor_weather_entities": saved.get("outdoor_weather_entities"),
            "calibrated_room_mean_c": saved.get("calibrated_indoor_c"),
            "calibrated_outdoor_mean_c": saved.get("calibrated_outdoor_c"),
            "measured_cold_surface_c": saved.get("critical_temperature_c"),
            "status": "calibrated" if saved.get("calibration_factor") is not None
                      else "needs_calibration",
        }


from .equipment_entity import EquipmentEntity


class EquipmentResumeButton(EquipmentEntity, ButtonEntity):
    """Explicitly choose Automatic/PID; no physical output is forced."""
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, manager, spec):
        # Preserve the existing entity ID and automation subscriptions.
        self._equipment_init(manager, spec, "resume")

    @property
    def available(self):
        runtime = self._manager.equipment
        cfg = self.controller_settings
        record = runtime.records.get(self._spec.identifier, {})
        upstream = record.get("upstream", {}) if isinstance(record, dict) else {}
        blocked = bool(record.get("paused") or record.get("pending")
                       or isinstance(upstream, dict) and (
                           upstream.get("paused") or upstream.get("pending")))
        return bool(getattr(runtime, "_ready", False)
                    and (cfg["control_mode"] not in ("automatic", "pid") or blocked))

    @property
    def extra_state_attributes(self):
        cfg = self.controller_settings
        return {
            **super().extra_state_attributes,
            "controller_resume_role": "continue_automatic",
            "automatic_already_selected": (
                cfg["control_mode"] in ("automatic", "pid")
                and not self.available
            ),
            "native_resume_recovery": self._manager.equipment.resume_information(
                self._spec
            ),
        }

    async def async_press(self):
        await self._manager.equipment.async_continue_automatic(self._spec)


class EquipmentCalibrationButton(EquipmentEntity, ButtonEntity):
    """Apply a measured-model mathematical tune to one physical device.

    No step test, actuator pulse or service call occurs. Calibration requires
    known plant gain/time/delay and a physically OFF, reconciled controller.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:calculator-variant-outline"

    def __init__(self, manager, spec):
        self._equipment_init(manager, spec, "pid_apply_calibration")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._watch_native_updates()

    @property
    def available(self):
        cfg = self.controller_settings
        from . import equipment_model as equipment
        return (cfg["control_mode"] == "pid"
                and cfg["pid_calibration_method"] in ("imc_lambda","cohen_coon")
                and equipment.capabilities(self._manager, self._spec) is not None
                and "pid" in equipment.control_modes(self._manager, self._spec))

    @property
    def extra_state_attributes(self):
        from . import equipment_model as model
        from .pid_calibration import tune
        result = {**super().extra_state_attributes,
                  "pid_calibration_role": "apply",
                  "calibration_method": self.controller_settings["pid_calibration_method"],
                  "manual_gains": {
                      key: self.controller_settings[key] for key in ("kp", "ki", "kd")
                  },
                  "measured_model": {
                      key: self.controller_settings[key] for key in model.PID_MODEL_FIELDS
                  },
                  "last_applied": self.controller_settings.get("pid_last_calibration")}
        if not self.available:
            result["calibration_status"] = "select_pid_and_nonmanual_method"
            return result
        try:
            calculated = tune(
                self.controller_settings["pid_calibration_method"],
                self.controller_settings,
                sample_seconds=self.controller_settings["sample_seconds"],
                constraints=model.NUMBER_FIELDS,
            )
        except ValueError as error:
            result["calibration_status"] = str(error)
        else:
            result["calibration_status"] = "ready_to_apply_when_physical_off"
            result["proposed_gains"] = {
                "kp": calculated.kp, "ki": calculated.ki, "kd": calculated.kd,
            }
        return result

    async def async_press(self):
        await self._manager.equipment.async_apply_pid_calibration(self._spec)


class EquipmentPIDReviewButton(EquipmentEntity, ButtonEntity):
    """Approve or discard an exact persisted PID suggestion from Home Assistant.

    These are genuine HA button entities, not unsafe GET links in the
    persistent-notification Markdown. A second press cannot replay a
    previously consumed proposal.
    """

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager, spec, action):
        self._action = action
        self._equipment_init(manager, spec, f"pid_review_{action}")
        self._attr_icon = "mdi:check-circle-outline" if action == "approve" else "mdi:close-circle-outline"

    @property
    def available(self):
        from .pid_review import is_pending
        record = self._manager.equipment.records.get(self._spec.identifier, {})
        return (self.controller_settings["control_mode"] == "pid"
                and self.controller_settings["pid_calibration_method"] == "adaptive_suggest"
                and is_pending(record.get("pid_passive_review")))

    @property
    def extra_state_attributes(self):
        from .pid_review import is_pending
        record = self._manager.equipment.records.get(self._spec.identifier, {})
        review = record.get("pid_passive_review")
        return {**super().extra_state_attributes,
                "pid_review_role": self._action,
                "pending": is_pending(review),
                "current_gains": review.get("current") if is_pending(review) else None,
                "next_gains": review.get("apply") if is_pending(review) else None,
                "confidence": review.get("confidence") if is_pending(review) else None}

    async def async_press(self):
        from homeassistant.exceptions import HomeAssistantError
        if not await self._manager.equipment.async_review_pid(
            self._spec, self._action,
        ):
            raise HomeAssistantError(
                "PID recommendation is no longer pending or cannot be safely applied"
            )


class EquipmentFanCapacityButton(EquipmentEntity, ButtonEntity):
    """Explicitly apply observed fan/output capacity; never start hardware."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:chart-bell-curve"

    def __init__(self, manager, spec):
        self._equipment_init(manager, spec, "pid_apply_fan_capacity")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._watch_native_updates()

    @property
    def available(self):
        from . import equipment_model as equipment
        cap = equipment.capabilities(self._manager, self._spec)
        return bool(cap and cap.fan_modes and cap.domain in ("climate", "humidifier")
                    and self.controller_settings["control_mode"] == "pid")

    @property
    def extra_state_attributes(self):
        from . import equipment_model as equipment
        from .pid_fan_capacity import build_model
        attributes = {**super().extra_state_attributes,
            "pid_fan_capacity_role": "apply",
            "strategy": self.controller_settings["pid_fan_capacity_mode"],
            "direction": self.controller_settings["pid_fan_capacity_for_mode"],
            "saved_directions": sorted(self.controller_settings["pid_fan_capacity_models"]),
        }
        cap = equipment.capabilities(self._manager, self._spec)
        if not self.available or cap is None:
            attributes["calibration_status"] = "select_pid_and_supported_native_fan"
            return attributes
        try:
            if self.controller_settings["pid_fan_capacity_for_mode"] not in cap.modes or (
                    self.controller_settings["pid_fan_capacity_for_mode"] == "choose"):
                raise ValueError("select_native_heating_cooling_or_drying_direction")
            evidence = build_model(
                percentage=cap.fan_percentage, advertised_modes=cap.fan_modes,
                measured=self.controller_settings,
                min_speed=equipment.device_limits(
                    self._manager, self._spec, cap)["fan_min_percentage"],
            )
        except ValueError as error:
            attributes["calibration_status"] = str(error)
        else:
            attributes["calibration_status"] = "ready_to_apply_when_physical_off"
            attributes["relative_capacity_model"] = evidence
        return attributes

    async def async_press(self):
        await self._manager.equipment.async_apply_fan_capacity(self._spec)
