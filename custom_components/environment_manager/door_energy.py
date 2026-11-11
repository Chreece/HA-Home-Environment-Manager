"""Measured, source-bound door-state energy intervals, never savings claims.

No recorder queries, persistence, extra polling, control permissions or service
calls. Meter reports and door epochs bound each interval; gaps are not filled.
"""
from __future__ import annotations

from datetime import datetime
import math

FACTORS = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0}
MAX_GAP = 330
MIN_COVERAGE = 900
MAX_CONTACTS = 128
MAX_POWER_KW = 100  # Reject implausible room-meter jumps, not an appliance rating.


def stamp(value):
    return value.timestamp() if isinstance(value, datetime) and value.tzinfo is not None else None


def meter_type(state):
    if state is None:
        return False
    a = state.attributes
    return (state.entity_id.startswith("sensor.") and a.get("device_class") == "energy"
            and a.get("state_class") in ("total", "total_increasing")
            and a.get("unit_of_measurement") in FACTORS)


def choices(hass, area, previous=None):
    from .discovery import entity_area
    from .room_sources import native, label
    result = {s.entity_id: label(hass, s.entity_id) for s in hass.states.async_all("sensor")
              if meter_type(s) and entity_area(hass, s.entity_id) == area and native(hass, s.entity_id)}
    if (isinstance(previous, str) and previous.startswith("sensor.")
            and entity_area(hass, previous) == area and native(hass, previous)):
        current = hass.states.get(previous)
        if current is None or current.state in ("unavailable", "unknown"):
            result[previous] = label(hass, previous)
    return {entity: result[entity] for entity in sorted(result, key=lambda e: (result[e], e))}


def sample(hass, area, entity, now):
    from .discovery import entity_area
    from .room_sources import native
    state = hass.states.get(entity)
    if not meter_type(state) or entity_area(hass, entity) != area or not native(hass, entity):
        return None
    a = state.attributes
    if a.get("restored") or isinstance(state.state, bool):
        return None
    try:
        value = float(state.state) * FACTORS[a["unit_of_measurement"]]
    except (ValueError, TypeError, OverflowError):
        return None
    at = stamp(getattr(state, "last_reported", None) or getattr(state, "last_updated", None))
    if not math.isfinite(value) or value < 0 or at is None or not 0 <= now - at <= MAX_GAP:
        return None
    return {"value": value, "at": at, "unit": a["unit_of_measurement"],
            "state_class": a["state_class"], "reset": str(a.get("last_reset", ""))}


class DoorEnergyMonitor:
    def __init__(self):
        self.records = {}

    def observe(self, key, signature, reading, boundary, changed, now):
        entry = self.records.get(key)
        if entry is None or entry["signature"] != signature:
            if entry is None and len(self.records) >= MAX_CONTACTS:
                return {"status": "capacity_limit", "savings_estimate": None}
            entry = {"signature": signature, "last": None, "skipped": 0,
                     "open": {"kwh": 0.0, "seconds": 0.0, "intervals": 0},
                     "closed": {"kwh": 0.0, "seconds": 0.0, "intervals": 0}}
            self.records[key] = entry
        prior = entry["last"]
        current = None
        reason = "awaiting_samples"
        if reading is not None and boundary in ("open", "closed") and changed is not None and changed <= reading["at"]:
            current = {**reading, "boundary": boundary, "changed": changed}
            if prior is not None:
                seconds = reading["at"] - prior["at"]
                delta = reading["value"] - prior["value"]
                if seconds == 0 and current == prior:
                    return self.report(entry, "observing")  # Recalculation is not a meter sample.
                valid = (0 < seconds <= MAX_GAP and delta >= 0
                         and current["unit"] == prior["unit"] and current["reset"] == prior["reset"]
                         and current["state_class"] == prior["state_class"]
                         and boundary == prior["boundary"] and changed == prior["changed"]
                         and changed <= prior["at"] and delta <= MAX_POWER_KW * seconds / 3600)
                if valid:
                    bucket = entry[boundary]
                    bucket["kwh"] += delta
                    bucket["seconds"] += seconds
                    bucket["intervals"] += 1
                    reason = "observing"
                else:
                    entry["skipped"] += 1
                    reason = "interval_excluded"
        else:
            if prior is not None:
                entry["skipped"] += 1
            reason = "evidence_unavailable"
        entry["last"] = current
        return self.report(entry, reason)

    @staticmethod
    def report(entry, status):
        result = {"status": status, "excluded_intervals": entry["skipped"],
                  "session_only": True, "savings_estimate": None,
                  "comparison_ready": all(entry[mode]["seconds"] >= MIN_COVERAGE for mode in ("open", "closed"))}
        for mode in ("open", "closed"):
            item = entry[mode]
            result[mode] = {"kwh": round(item["kwh"], 6),
                            "observed_minutes": round(item["seconds"] / 60, 1),
                            "mean_power_w": round(item["kwh"] * 3600000 / item["seconds"], 1)
                                            if item["seconds"] else None,
                            "intervals": item["intervals"]}
        return result

    def update(self, hass, settings, area, contacts, signature, now):
        from .discovery import entity_area
        results, tracked, active = [], set(), set()
        for contact in contacts[:MAX_CONTACTS]:
            entity = contact.get("energy_meter")
            if not isinstance(entity, str) or not entity:
                continue
            key = (area, contact["entity_id"])
            active.add(key)
            if entity_area(hass, entity) == area:
                tracked.add(entity)
            native = hass.states.get(contact["entity_id"])
            changed = stamp(getattr(native, "last_changed", None))
            boundary = contact["state"] if contact["health"] == "ok" else "unknown"
            reading = sample(hass, area, entity, now)
            source_key = (entity, signature, contact.get("kind"), contact.get("target_area"))
            report = self.observe(key, source_key, reading, boundary, changed, now)
            results.append({"contact": contact["entity_id"], "meter": entity, **report})
        for key in list(self.records):
            if key[0] == area and key not in active:
                del self.records[key]
        return results, tracked
