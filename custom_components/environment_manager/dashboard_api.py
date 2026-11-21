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
from .dashboard import dashboard_snapshot
from .controller_inventory import controller_inventory
from .environment_history import AVG_ALLOWED, AVG_MAX_AGE, AVG_MIN_SAMPLE_SECONDS

COMMAND = f"{DOMAIN}/dashboard"
TREND_COMMAND = f"{DOMAIN}/trend"


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

    # Pure transformation of the latest validated Plan; no I/O, no physical
    # control, no registry changes, and no Recorder/database writes.
    result = dashboard_snapshot(manager.plan, manager.thresholds)
    # This entry ID has already been verified against the caller's readable
    # recommendation sensor. Disambiguate multiple HEM Home devices without
    # trusting names, registry order, or a sometimes absent frontend entity map.
    result["owner_entry_id"] = entry_id
    # Configured source membership is independent of an unavailable HA state.
    # This is scoped to the already authorized recommendation sensor response.
    result["controllers"] = controller_inventory(manager)
    preparation = getattr(manager, "arrival_preparation", None)
    if preparation is not None:
        result["arrival_preparation"] = preparation.snapshot()
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


@callback
def async_register_dashboard_api(hass: HomeAssistant) -> None:
    """Register once when the canonical integration is initialized."""
    websocket_api.async_register_command(hass, websocket_dashboard)
    websocket_api.async_register_command(hass, websocket_trend)
