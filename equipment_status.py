"""Read-only operational status on each managed physical controller device.

The managed climate facade reports the *selected supervisory HVAC mode*,
while keeping its actual physical source state in separate attributes. When
PID/Automatic is armed and the physical HVAC output is OFF, its climate action
is IDLE. This read-only sensor explains whether there is no demand, a
minimum-OFF hold, a missing input, or a safety pause. Neither entity can
bypass hardware safety decisions or write a physical HA service from status.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .controller_status_catalog import EQUIPMENT_SENSOR_STATUSES
from .equipment_entity import EquipmentEntity
from . import equipment_model as equipment


class ControllerStatusSensor(EquipmentEntity, SensorEntity):
    """Show the evaluated controller state beside its native climate facade."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = sorted(EQUIPMENT_SENSOR_STATUSES)
    _attr_icon = "mdi:information-outline"
    _attr_should_poll = False

    def __init__(self, manager: Any, spec: equipment.ManagedDevice) -> None:
        self._equipment_init(manager, spec, "control_status")

    @property
    def native_value(self) -> str:
        runtime = self._manager.equipment
        observed = runtime.statuses.get(self._spec.identifier, {})
        if isinstance(observed, dict) and isinstance(observed.get("status"), str):
            return (observed["status"] if observed["status"] in EQUIPMENT_SENSOR_STATUSES
                    else "unrecognized_status")
        mode = self.controller_settings.get("control_mode", "existing")
        if mode in ("existing", "off"):
            return mode
        if not getattr(runtime, "_active", False):
            return "inactive"
        if not getattr(runtime, "_ready", False):
            return "storage_unavailable"
        return "awaiting_evaluation"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        runtime = self._manager.equipment
        cfg = self.controller_settings
        observed = runtime.statuses.get(self._spec.identifier, {})
        observed = observed if isinstance(observed, dict) else {}
        record = runtime.records.get(self._spec.identifier, {})
        record = record if isinstance(record, dict) else {}
        physical = {
            entity_id: (
                state.state if (state := self._manager.hass.states.get(entity_id))
                is not None else "unavailable"
            )
            for entity_id in self._spec.source_entities
        }
        # HA may request a diagnostic state during partial setup, or an
        # external status consumer may expose only states.get (not async_all).
        # A read-only status must never crash setup or fabricate a room plan.
        # In the fully running integration, compute the real live room plan.
        states = getattr(self._manager.hass, "states", None)
        plan = (equipment.plan_for(self._manager, self._spec)
                if callable(getattr(states, "async_all", None)) else {})
        shared = self._manager.settings.get("occupancy_global") or {}
        sleep_id = shared.get("sleep_rooms_entity") if isinstance(shared, dict) else None
        sleep_source = self._manager.hass.states.get(sleep_id) if (
            isinstance(sleep_id, str) and sleep_id not in ("", "none")
        ) else None
        effective = equipment.profile_name(cfg, plan)
        # Surface both pieces of an externally powered controller. The HA
        # native appliance may be unavailable precisely BECAUSE the supply
        # is OFF. Neither observation implies that the logical controller
        # is disabled or that an unsafe power command should be attempted.
        supply_id = cfg.get("power_switch_entity")
        upstream = record.get("upstream", {})
        upstream = upstream if isinstance(upstream, dict) else {}
        supply = self._manager.hass.states.get(supply_id) if (
            isinstance(supply_id, str) and supply_id) else None
        return {
            "area_id": self._spec.area_id,
            "status_code": observed.get("status"),
            "status_reason_code": observed.get("reason"),
            "control_method": cfg.get("control_mode", "existing"),
            "selected_preset": (effective if cfg.get("control_mode")
                                in ("automatic", "pid") else cfg.get("preset", "none")),
            "preset_override": cfg.get("preset", "none"),
            "effective_preset": effective,
            "home_presence_status": plan.get("away", "unknown"),
            "home_presence_reason": plan.get("away_evidence", "unknown"),
            "room_occupancy": plan.get("occupancy", "unknown"),
            "sleep_behavior": cfg.get("sleep_behavior", "normal"),
            "sleep_rooms_entity": sleep_id,
            "sleep_rooms_source_state": (sleep_source.state if sleep_source is not None
                                         else "not_configured" if sleep_id in (None, "", "none")
                                         else "unavailable"),
            "sleeping": plan.get("sleeping"),
            "sleep_evidence": plan.get("sleep_schedule_evidence"),
            "status_reason": observed.get("reason") or (
                observed.get("status") if observed.get("status") ==
                "sleep_room_evidence_unknown" else None),
            "last_evaluated_mode": observed.get("mode"),
            "demand_percent": observed.get("demand_percent"),
            "pid_calibration_method": cfg.get("pid_calibration_method", "manual"),
            "pid_last_calibration": cfg.get("pid_last_calibration"),
            "pid_fan_capacity_strategy": cfg.get("pid_fan_capacity_mode", "legacy"),
            "pid_fan_capacity_selected_direction": cfg.get("pid_fan_capacity_for_mode", "choose"),
            "pid_fan_capacity_calibrated_modes": sorted(cfg.get("pid_fan_capacity_models", {})),
            "pid_fan_capacity_allocation": getattr(runtime, "_fan_allocations", {}).get(
                self._spec.identifier),
            "pid_prepared_while_unpowered": getattr(
                runtime, "_pid_offline_previews", {}
            ).get(self._spec.identifier),
            "pid_output_strategy": (
                "continuous_percentage_fan" if (cap := equipment.capabilities(self._manager, self._spec))
                is not None and cap.domain == "fan" and cap.fan_percentage else
                "discrete_fan_stages" if cap is not None and cap.domain == "fan"
                and bool(cap.fan_modes) else
                "continuous_percentage_valve" if cap is not None
                and cap.domain in ("number", "input_number") else
                "binary_duty_cycle"
            ) if cfg.get("control_mode") == "pid" else "not_pid",
            "physical_entity_states": physical,
            "controller_owns_power": bool(record.get("power")),
            "paused_reason": record.get("paused"),
            "command_pending": bool(record.get("pending")),
            "upstream_power_switch": supply_id,
            "upstream_power_state": supply.state if supply is not None else "unavailable",
            "upstream_owned_by_controller": upstream.get("owned") is True,
            "upstream_pending_command": (
                upstream.get("pending", {}).get("desired")
                if isinstance(upstream.get("pending"), dict) else None
            ),
            "upstream_pause_reason": upstream.get("paused"),
            "previous_native_capabilities_cached": isinstance(
                record.get("capabilities"), dict),
            "native_sources_available": equipment.sources_available(
                self._manager, self._spec),
        }
