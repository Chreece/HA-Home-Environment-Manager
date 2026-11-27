"""Authenticated, read-only full Home Environment Manager dashboard snapshots.

A complete multi-room snapshot is presentation data, not sensor state. Keeping
it off state attributes avoids Home Assistant Recorder's 16384-byte limit
without discarding any measurements, actions or per-device climate details.
"""
from __future__ import annotations

import time
from typing import Any

import probatio

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .dashboard import manager_dashboard_snapshot
from .controller_inventory import controller_inventory
from .environment_history import AVG_ALLOWED, AVG_MAX_AGE, AVG_MIN_SAMPLE_SECONDS
from .control_history import CONTROL_METRICS, CONTROL_MAX_AGE, CONTROL_SAMPLE_SECONDS

COMMAND = f"{DOMAIN}/dashboard"
TREND_COMMAND = f"{DOMAIN}/trend"
CONTROL_TREND_COMMAND = f"{DOMAIN}/control_trend"


def _readable_manager(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> Any | None:
    """Resolve exactly one readable HEM recommendation sensor's active owner."""
    entity_id = msg["entity_id"]
    if not isinstance(entity_id, str) or not entity_id.startswith("sensor."):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "Recommendation sensor not found")
        return

    record = er.async_get(hass).async_get(entity_id)
    entry_id = getattr(record, "config_entry_id", None)
    if (record is None
            or getattr(record, "platform", None) != DOMAIN
            or not isinstance(entry_id, str)
            or getattr(record, "unique_id", None) != f"{entry_id}_recommendation"):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "Recommendation sensor not found")
        return

    # Equivalent to the access checks used for get_states / subscribe_entities.
    # Never expose other people's room details merely because an entry ID was
    # guessed or the requester can read some unrelated Home Assistant entity.
    user = connection.user
    if not (user.is_admin or user.permissions.check_entity(entity_id, POLICY_READ)):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED,
                              "Not authorized to read recommendation sensor")
        return

    manager = hass.data.get(DOMAIN, {}).get(entry_id)
    if (manager is None or manager.entry.entry_id != entry_id
            or getattr(manager, "_stopping", False)):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "Home Environment Manager not loaded")
        return
    return manager


@websocket_api.websocket_command({
    probatio.Required("type"): COMMAND,
    probatio.Required("entity_id"): str,
})
@callback
def websocket_dashboard(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Fetch full state of precisely this accessible recommendation sensor."""
    manager = _readable_manager(hass, connection, msg)
    if manager is None:
        return
    entry_id = manager.entry.entry_id

    # Read-only validated plan and exact configured control measurements;
    # no physical control, registry changes or Recorder/database writes.
    result = manager_dashboard_snapshot(manager)
    # This entry ID has already been verified against the caller's readable
    # recommendation sensor. Disambiguate multiple HEM Home devices without
    # trusting names, registry order, or a sometimes absent frontend entity map.
    result["owner_entry_id"] = entry_id
    result["control_trend_version"] = 1
    # Configured source membership is independent of an unavailable HA state.
    # This is scoped to the already authorized recommendation sensor response.
    result["controllers"] = controller_inventory(manager)
    preparation = getattr(manager, "arrival_preparation", None)
    if preparation is not None:
        result["arrival_preparation"] = preparation.snapshot()
        if hasattr(preparation, "rooms"):
            from homeassistant.helpers import entity_registry as er
            registry = er.async_get(hass)
            result["room_preparation_entities"] = {
                area: registry.async_get_entity_id("button", DOMAIN, f"{entry_id}_area_{area}_prepare_room")
                for area in preparation.rooms.areas
            }
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    probatio.Required("type"): TREND_COMMAND,
    probatio.Required("entity_id"): str,
    probatio.Required("area_id"): str,
    probatio.Required("metric"): probatio.In([*AVG_ALLOWED, "mold"]),
})
@callback
def websocket_trend(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Read one chart's retained samples without decimating the whole week.

    Authorization is identical to the overview; callers cannot choose another
    entry, an unmonitored room or an arbitrary historical contributor set.
    This only copies already-restored bounded data, without I/O or writes.
    """
    manager = _readable_manager(hass, connection, msg)
    if manager is None:
        return
    area, metric = msg["area_id"], msg["metric"]
    plan = manager.plan
    if (not isinstance(area, str) or not area or len(area) > 128
            or not isinstance(metric, str) or metric not in AVG_ALLOWED | {"mold"}
            or not any(room.area_id == area for room in (*plan.rooms, *plan.climate_rooms))):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Trend not found")
        return
    report = plan.environment.get(area, {})
    evidence = (report.get("mold_trend") if metric == "mold"
                else report.get("measurement_evidence", {}).get(metric))
    sources = evidence.get("source_ids") if isinstance(evidence, dict) else None
    count = evidence.get("source_count") if isinstance(evidence, dict) else None
    valid_sources = (isinstance(sources, list) and type(count) is int and len(sources) == count
                     and all(isinstance(source, str) and source.startswith("sensor.")
                             and len(source) <= 255 for source in sources)
                     and len(set(sources)) == len(sources))
    if not valid_sources or not (count == 0 if metric == "mold" else 2 <= count <= 32):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Trend not found")
        return
    # Historical samples remain readable during a missing current reading.
    # No current value is appended, and a different/absent contributor set
    # never grants access to an arbitrary old average series.
    history = manager._environment_history
    now = time.time()
    points = (history.mold_points(area, now=now) if metric == "mold" else
              history.average_points(area, metric, sources, now=now))
    connection.send_result(msg["id"], {
        "area_id": area, "metric": metric,
        "source_ids": list(sources), "source_count": count,
        "trend": points, "retention_seconds": AVG_MAX_AGE,
        "sample_interval_seconds": 300 if metric == "mold" else AVG_MIN_SAMPLE_SECONDS,
    })


@websocket_api.websocket_command({
    probatio.Required("type"): CONTROL_TREND_COMMAND,
    probatio.Required("entity_id"): str,
    probatio.Required("area_id"): str,
    probatio.Required("metric"): probatio.In(sorted(CONTROL_METRICS)),
    probatio.Required("source_ids"): list,
})
@callback
def websocket_control_trend(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Copy target/output observations for this exact readable chart context.

    Physical Recorder charts, HEM contributor means and derived mold keep
    their original measurement transport. This endpoint adds no live sample,
    device command, Recorder query or storage write, and cannot substitute a
    different room's target. Room means can share the recorded setpoint
    across changes in contributors within the same controller configuration.
    """
    manager = _readable_manager(hass, connection, msg)
    if manager is None:
        return
    area, metric, requested = msg["area_id"], msg["metric"], msg["source_ids"]
    plan = manager.plan
    if (not isinstance(area, str) or not area or len(area) > 128
            or not isinstance(metric, str) or metric not in CONTROL_METRICS
            or not any(room.area_id == area for room in (*plan.rooms, *plan.climate_rooms))
            or not isinstance(requested, list) or len(requested) > 32
            or any(not isinstance(source, str) or not source.startswith("sensor.")
                   or len(source) > 255 for source in requested)
            or len(set(requested)) != len(requested)
            or (bool(requested) if metric == "mold" else not requested)):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Control trend not found")
        return
    report = plan.environment.get(area, {})
    report = report if isinstance(report, dict) else {}
    measurements = report.get("measurement_evidence")
    evidence = (report.get("mold_trend") if metric == "mold" else
                measurements.get(metric) if isinstance(measurements, dict) else None)
    sources = evidence.get("source_ids") if isinstance(evidence, dict) else None
    count = evidence.get("source_count") if isinstance(evidence, dict) else None
    valid_evidence = (
        isinstance(sources, list) and type(count) is int and len(sources) == count
        and all(isinstance(source, str) and source.startswith("sensor.")
                and len(source) <= 255 for source in sources)
        and len(set(sources)) == len(sources)
        and (count == 0 if metric == "mold" else 1 <= count <= 32)
    )
    full_context = valid_evidence and sorted(sources) == sorted(requested)
    # A native sensor in a room's displayed mean can still open its own
    # Recorder chart. Authorize that exact contributor without overlaying a
    # mean-controlled target onto it; history.view requires exact feedback IDs.
    # Current configured room readings also retain the sensor's identity while
    # its present value is unavailable, so genuine old samples remain readable.
    single_context = metric != "mold" and len(requested) == 1 and (
        valid_evidence and requested[0] in sources
        or any(getattr(reading, "entity_id", None) == requested[0]
               and getattr(reading, "metric", None) == metric
               for room in (*plan.rooms, *plan.climate_rooms) if room.area_id == area
               for reading in getattr(room, "readings", ()))
    )
    if not (full_context or single_context):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Control trend not found")
        return
    history = manager._environment_history.control
    connection.send_result(msg["id"], {
        "version": 1, "area_id": area, "metric": metric, "source_ids": sorted(requested),
        "controllers": history.view(area, metric, requested, now=time.time()),
        "retention_seconds": CONTROL_MAX_AGE,
        "sample_interval_seconds": CONTROL_SAMPLE_SECONDS,
    })


@callback
def async_register_dashboard_api(hass: HomeAssistant) -> None:
    """Register once when the canonical integration is initialized."""
    websocket_api.async_register_command(hass, websocket_dashboard)
    websocket_api.async_register_command(hass, websocket_trend)
    websocket_api.async_register_command(hass, websocket_control_trend)
