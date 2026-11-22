"""Remove only one HEM entry's owned data after its writers have stopped.

Reloads and disabled entries retain their recovery journals. Permanent config
entry removal deletes exact Store keys; it never scans a directory, removes
source devices, edits user dashboards, or purges Home Assistant Recorder.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import logging
from typing import Any

from .const import DOMAIN
from .device_hierarchy import configured_area_ids

_LOGGER = logging.getLogger(__name__)
DATA_CLEANUP = f"{DOMAIN}_entry_cleanup"
DATA_FRONTEND = f"{DOMAIN}_frontend_resource"
STORE_REMOVE_TIMEOUT_SECONDS = 10.0

# Every persistent journal owned by a single config entry. Keep this explicit:
# a prefix/suffix glob could delete another entry or somebody else's file.
STORE_NAMES = (
    "environment_history", "equipment", "pid", "climate_native", "direct",
    "humidity_native", "humidity_power", "secondary_native", "running_fan",
    "fan_power", "native_dry_fan", "shade_cooling", "presence_absence",
    "arrival_preparation", "wake_alarm", "window_close_cooldown",
)


@dataclass
class EntryCleanup:
    """Retain Store handles, not the manager, across HA's runtime_data removal."""

    stores: dict[str, Any] = field(default_factory=dict)
    notifications: set[str] = field(default_factory=set)
    areas: set[str] = field(default_factory=set)
    stopped: bool = False


def store_keys(entry_id: str) -> tuple[str, ...]:
    return tuple(f"{DOMAIN}.{name}_{entry_id}" for name in STORE_NAMES)


def _notice_ids(entry_id: str, identifier: str, physical: str | None) -> set[str]:
    review = hashlib.sha256(f"{entry_id}:{identifier}".encode()).hexdigest()[:24]
    device = hashlib.sha256(f"{entry_id}:{physical or identifier}".encode()).hexdigest()[:24]
    return {
        f"hem_pid_review_{review}",
        *(f"hem_{kind}_{device}" for kind in
          ("native_fault", "native_unavailable", "command_nonresponse")),
    }


def _collect_records(state: EntryCleanup, entry_id: str, records: Any) -> None:
    if not isinstance(records, dict):
        return
    for identifier, record in records.items():
        if not isinstance(identifier, str) or not isinstance(record, dict):
            continue
        physical = record.get("source_device_id")
        state.notifications.update(_notice_ids(
            entry_id, identifier, physical if isinstance(physical, str) else None,
        ))
        if isinstance(area := record.get("area"), str) and area:
            state.areas.add(area)


def capture_entry_runtime(hass: Any, entry: Any) -> EntryCleanup:
    """Capture handles before teardown clears wake tracking and fault specs."""
    state = hass.data.setdefault(DATA_CLEANUP, {}).setdefault(entry.entry_id, EntryCleanup())
    state.areas.update(configured_area_ids({**entry.data, **entry.options}))
    manager = getattr(entry, "runtime_data", None)
    if manager is None:
        manager = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if manager is None:
        return state
    allowed = set(store_keys(entry.entry_id))
    stores = [getattr(manager, "_environment_store", None)]
    controllers = getattr(manager, "_controllers", None)
    if callable(controllers):
        stores.extend(getattr(controller, "_store", None) for _, controller in controllers())
    wake = hass.data.get(f"{DOMAIN}.wake_alarm_trackers", {}).get(entry.entry_id)
    stores.append(getattr(wake, "store", None))
    for store in stores:
        if getattr(store, "key", None) in allowed:
            state.stores[store.key] = store
    _collect_records(state, entry.entry_id, getattr(getattr(manager, "equipment", None), "records", None))
    for spec in getattr(getattr(manager, "faults", None), "_specs", {}).values():
        identifier = getattr(spec, "identifier", None)
        if isinstance(identifier, str):
            state.notifications.update(_notice_ids(
                entry.entry_id, identifier, getattr(spec, "source_device_id", None),
            ))
    return state


def remember_frontend_resource(hass: Any, url: str) -> None:
    """Remember the exact integration-added URL, without touching Lovelace."""
    resource = hass.data.get(DATA_FRONTEND)
    if resource is None:
        hass.data[DATA_FRONTEND] = {"url": url, "urls": [url], "registered": True}
        return
    urls = resource.setdefault("urls", [resource["url"]])
    if url not in urls:
        urls.append(url)
    resource["registered"] = True


def prepare_entry_setup(hass: Any, entry: Any) -> None:
    """Release stopped handles and restore JS after same-process reinstallation."""
    pending = hass.data.get(DATA_CLEANUP, {})
    pending.pop(entry.entry_id, None)
    if not pending:
        hass.data.pop(DATA_CLEANUP, None)
    resource = hass.data.get(DATA_FRONTEND)
    if resource and not resource["registered"]:
        from homeassistant.components.frontend import add_extra_js_url

        for url in resource.get("urls", [resource["url"]]):
            add_extra_js_url(hass, url)
        resource["registered"] = True


async def _async_remove_store(store: Any) -> None:
    """Drain existing writes even on HA 2026.10's non-locking async_remove."""
    # Permanent removal only: revoke queued writes before waiting for an
    # already-started executor write. 2026.10's public async_remove cancels
    # future callbacks but can otherwise race that executor write. Its Store
    # has no public write barrier; use the same lock as async_save, releasing
    # it before async_remove for newer HA versions that lock internally.
    store.make_read_only()
    async with asyncio.timeout(STORE_REMOVE_TIMEOUT_SECONDS):
        async with store._write_lock:
            pass
        await store.async_remove()


def _saved_equipment_records(path: str, key: str) -> Any:
    """Read ownership without Store loading/migrating/renaming a corrupt file."""
    try:
        with open(path, encoding="utf-8") as handle:
            envelope = json.load(handle)
    except FileNotFoundError:
        return None
    if (not isinstance(envelope, dict) or envelope.get("key") != key
            or envelope.get("version") != 1):
        return None
    data = envelope.get("data")
    return data.get("records") if isinstance(data, dict) else None


async def async_remove_owned_data(hass: Any, entry: Any) -> None:
    """Delete one entry's owned storage and local notices on permanent removal."""
    from homeassistant.helpers.storage import Store

    manager = getattr(entry, "runtime_data", None)
    if manager is None:
        manager = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    state = capture_entry_runtime(hass, entry)
    if manager is not None:
        # HA can call removal after an unsuccessful unload. Never race a late
        # journal writer or erase safety ownership while a controller is active.
        if not await manager.async_stop():
            raise RuntimeError("HEM writers did not stop; owned data was retained")
        state.stopped = True
    elif state.stores and not state.stopped:
        raise RuntimeError("HEM teardown was not confirmed; owned data was retained")
    state.stopped = True

    # A failed platform unload may still leave the now-stopped manager in the
    # routing map. Removal must not keep its service routes alive.
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        for service in ("announce", "pid_control", "climate_control", "climate_diagnostics"):
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)

    for key in store_keys(entry.entry_id):
        if key not in state.stores:
            state.stores[key] = Store(hass, 1, key)

    # A disabled entry has no manager. Its journal still identifies old owned
    # PID/fault notices, including retired equipment and renamed entities.
    try:
        key = f"{DOMAIN}.equipment_{entry.entry_id}"
        records = await hass.async_add_executor_job(_saved_equipment_records, state.stores[key].path, key)
        _collect_records(state, entry.entry_id, records)
    except Exception:
        _LOGGER.warning("Could not read HEM notification ownership before removal", exc_info=True)

    remaining = tuple(other for other in hass.config_entries.async_entries(DOMAIN)
                      if other.entry_id != entry.entry_id)
    shared_areas = set()
    for other in remaining:
        shared_areas.update(configured_area_ids({**other.data, **other.options}))
        other_state = hass.data.get(DATA_CLEANUP, {}).get(other.entry_id)
        if other_state is not None:
            shared_areas.update(other_state.areas)
    # Older ventilation/shade notices use area IDs, not entry IDs. Remove only
    # exact known areas that no remaining HEM entry also owns.
    for area in state.areas - shared_areas:
        state.notifications.update((f"{DOMAIN}_{area}",
                                    f"{DOMAIN}_shades_{area}_open",
                                    f"{DOMAIN}_shades_{area}_close"))

    failed = []
    for key, store in state.stores.items():
        try:
            # Use the original handle so its delayed/final writes are revoked,
            # including work deferred while HA itself was stopping.
            await _async_remove_store(store)
        except Exception:
            failed.append(key)
            _LOGGER.exception("Could not remove HEM owned store %s", key)
    if hass.services.has_service("persistent_notification", "dismiss"):
        for notification in sorted(state.notifications):
            try:
                await hass.services.async_call("persistent_notification", "dismiss",
                                               {"notification_id": notification}, blocking=True)
            except Exception:
                _LOGGER.warning("Could not dismiss HEM notification %s", notification, exc_info=True)

    if not remaining:
        resource = hass.data.get(DATA_FRONTEND)
        if resource and resource["registered"]:
            from homeassistant.components.frontend import remove_extra_js_url

            for url in resource.get("urls", [resource["url"]]):
                remove_extra_js_url(hass, url)
            resource["registered"] = False
    if failed:
        raise RuntimeError(f"Could not remove {len(failed)} HEM owned storage file(s)")
    cleanup = hass.data.get(DATA_CLEANUP, {})
    cleanup.pop(entry.entry_id, None)
    if not cleanup:
        hass.data.pop(DATA_CLEANUP, None)
    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)
    if not hass.data.get(f"{DOMAIN}_arrival_preparation"):
        hass.data.pop(f"{DOMAIN}_arrival_preparation", None)
