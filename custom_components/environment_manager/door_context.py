"""Bounded, passive door connectivity, diagnostics and environmental evidence.

An edge means a POSSIBLE connection, never measured airflow or occupancy.
This module has no service calls, actuator targets, notification sends or
persistent occupant history. Device permissions remain with existing drivers.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import math
from typing import Any, Mapping

from .building_physics import humidity_ratio_g_kg, rh_at_temperature_from_ratio
from .room_doors import observe

MAX_CONTACTS = 128
MAX_GAP_SECONDS = 330


def finite(value: Any, low: float, high: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) and low <= result <= high else None


def _fresh_values(room: Any, metric: str, low: float, high: float) -> list[float]:
    """Room readings already passed HEM's native/source/unit/freshness checks."""
    values = []
    for reading in getattr(room, "readings", ()):
        if getattr(reading, "metric", None) != metric or getattr(reading, "available", False) is not True:
            continue
        value = finite(getattr(reading, "value", None), low, high)
        if value is not None:
            values.append(value)
    return values


def _source_signature(settings: Mapping, area: str) -> tuple:
    rooms = settings.get("room_sources", {})
    selected = rooms.get(area, {}) if isinstance(rooms, Mapping) else {}
    selected = selected if isinstance(selected, Mapping) else {}
    configs = settings.get("climate_rooms", {})
    config = configs.get(area, {}) if isinstance(configs, Mapping) else {}
    config = config if isinstance(config, Mapping) else {}
    return (config.get("temperature_entity"), config.get("humidity_entity"),
            tuple((group, tuple(sorted(value for value in selected.get(group, [])
                                      if isinstance(value, str)))
                   if isinstance(selected.get(group), (list, tuple)) else None)
                  for group in ("temperature", "humidity", "air_quality")))


def _advice(code: str, *, other: str | None = None, **evidence: Any) -> dict:
    return {"code": code, **({"related_area": other} if other else {}),
            **({"evidence": evidence} if evidence else {})}


def topology(reports: Mapping[str, dict]) -> tuple[dict[str, list], dict[str, list]]:
    """Deterministic undirected potential connections, never inferred links.

    The selected contact remains owned by its effective native Area. Only an
    explicit second endpoint connects it to a different monitored Area.
    Fire/exterior/unknown-role doors never supply a transfer-air path.
    """
    links = {area: [] for area in reports}
    graph = {area: set() for area in reports}
    count = 0
    for owner in sorted(reports):
        for contact in reports[owner].get("contacts", ()):
            target = contact.get("target_area")
            if not target or target == owner or target not in reports:
                continue
            count += 1
            if count > MAX_CONTACTS:
                # A bounded graph must not silently look complete.
                for report in reports.values():
                    report["topology_complete"] = False
                return links, {area: [] for area in reports}
            allowed = contact.get("kind") == "interior"
            status = contact.get("state", "unknown")
            if contact.get("health") != "ok":
                status = "unknown"
            link = {"contact": contact["entity_id"], "owner_area": owner,
                    "kind": contact.get("kind"), "state": status,
                    "potential_exchange": allowed and status == "open"}
            links[owner].append({**link, "other_area": target})
            links[target].append({**link, "other_area": owner})
            if link["potential_exchange"]:
                graph[owner].add(target)
                graph[target].add(owner)
    reachable = {}
    for area in sorted(graph):
        seen = {area}
        pending = deque([area])
        while pending:
            node = pending.popleft()
            for neighbor in sorted(graph[node] - seen):
                seen.add(neighbor)
                pending.append(neighbor)
        reachable[area] = sorted(seen - {area})
    return links, reachable


def enrich(reports: dict[str, dict], *, outside_safe: bool = False) -> None:
    """Read-only moisture/air/quiet context; no changed controller authority."""
    links, reachable = topology(reports)
    for area, report in reports.items():
        notes = []
        own = report.get("measurements", {})
        for contact in report.get("contacts", ()):
            if contact.get("health") != "ok":
                notes.append(_advice("contact_unverified", contact=contact["entity_id"],
                                     reason=contact.get("health", "unknown")))
            if contact.get("kind") == "fire" and contact.get("state") == "open":
                notes.append(_advice("fire_door_open", contact=contact["entity_id"]))
            target = contact.get("target_area")
            if target and (target == area or target not in reports):
                notes.append(_advice("invalid_connection", contact=contact["entity_id"]))
        co2 = finite(own.get("co2_ppm"), 0, 50000)
        target = finite(report.get("co2_threshold"), 400, 5000) or 1000.0
        if co2 is not None and co2 >= target:
            # Particle cleaning is not fresh-air supply. This never dispatches
            # a purifier or an unverified fan as a CO2 remediation device.
            notes.append(_advice("fresh_air_needed", co2_ppm=round(co2), threshold=target))
        humidity = finite(own.get("humidity_rh"), 0, 100)
        if humidity is not None and humidity >= 60:
            notes.append(_advice("remove_moisture_locally", humidity_rh=round(humidity, 1)))
        transfer = []
        for link in links[area]:
            peer = reports[link["other_area"]]
            measurements = peer.get("measurements", {})
            temp = finite(own.get("temperature_c"), -40, 65)
            peer_temp = finite(measurements.get("temperature_c"), -40, 65)
            peer_rh = finite(measurements.get("humidity_rh"), 0, 100)
            item = {**link, "other_name": peer.get("name", link["other_area"])}
            if temp is not None and peer_temp is not None:
                item["temperature_difference_c"] = round(temp - peer_temp, 2)
            # Relative humidity alone cannot rank the moisture content of
            # rooms at different temperatures. Reuse HEM's psychrometrics.
            if all(value is not None for value in (temp, peer_temp, humidity, peer_rh)):
                ratio = humidity_ratio_g_kg(temp, humidity)
                peer_ratio = humidity_ratio_g_kg(peer_temp, peer_rh)
                projected = rh_at_temperature_from_ratio(ratio, peer_temp) if ratio is not None else None
                if ratio is not None and peer_ratio is not None:
                    item["moisture_difference_g_kg"] = round(ratio - peer_ratio, 2)
                if (link["kind"] == "interior" and link["state"] in ("open", "closed")
                        and projected is not None and ratio is not None and peer_ratio is not None
                        and temp - peer_temp >= 3 and ratio - peer_ratio >= 0.5 and projected >= 70):
                    notes.append(_advice("moisture_transfer_risk", other=link["other_area"],
                                         projected_rh=round(projected, 1),
                                         temperature_difference_c=round(temp - peer_temp, 1)))
            transfer.append(item)
        routes = []
        if outside_safe is True and report.get("topology_complete", True):
            # An open path to an open window is only a possible route. No air
            # change rate or safe/clean whole-room air claim follows from it.
            routes = [other for other in reachable[area]
                      if reports[other].get("window_open") is True
                      and reports[other].get("window_evidence_complete") is True]
        report.update(connections=transfer, connected_rooms=reachable[area],
                      possible_outdoor_paths=routes,
                      quiet_boundary=(report.get("sleeping") is True
                                      and report.get("boundary") == "closed"),
                      advisories=notes[:12], advisory_only=True)


class DoorContextMonitor:
    """Per-entry, bounded session observations; no added polling or storage."""

    def __init__(self) -> None:
        self._members: dict[str, str] = {}
        self._events: dict[str, deque] = {}
        self._sessions: dict[str, dict] = {}
        self._links: dict[tuple, dict] = {}
        self._next_deadline: float | None = None

    def should_refresh(self, now: float) -> bool:
        """Reuse the manager's existing fast tick; do not create a poller."""
        return self._next_deadline is not None and now >= self._next_deadline

    def state_changed(self, entity_id: str, old: Any, new: Any, now: float) -> None:
        if entity_id not in self._members or old is None or new is None:
            return
        if old.state == new.state or old.state not in ("on", "off") or new.state not in ("on", "off"):
            return
        if (old.attributes or {}).get("restored") or (new.attributes or {}).get("restored"):
            return
        events = self._events.setdefault(entity_id, deque(maxlen=32))
        events.append((now, new.state))

    def _session(self, area: str, signature: tuple, boundary: str, now: float) -> dict:
        item = self._sessions.get(area)
        if item is None or item["signature"] != signature or now < item["last"]:
            item = {"signature": signature, "last": now, "state": boundary,
                    "open": 0.0, "closed": 0.0, "unknown": 0.0, "unobserved": 0.0}
            self._sessions[area] = item
        elapsed = now - item["last"]
        if 0 < elapsed <= MAX_GAP_SECONDS and item["state"] == boundary:
            bucket = boundary if boundary in ("open", "closed") else "unknown"
            item[bucket] += elapsed
        elif elapsed > 0:
            # Do not retrospectively fill gaps or assign a state-change
            # interval to either state when the transition time is uncertain.
            item["unobserved"] += elapsed
        item.update(last=now, state=boundary)
        return {key + "_minutes": round(item[key] / 60, 1)
                for key in ("open", "closed", "unknown", "unobserved")}

    def update(self, hass: Any, settings: Mapping, environment: dict,
               rooms: list, presence: Mapping, home_status: str,
               *, outside_safe: bool = False, now: float | None = None) -> tuple[dict, set]:
        from .room_sources import room_temperature_evidence
        from .discovery import entity_area
        from homeassistant.helpers import area_registry as ar
        now = datetime.now(timezone.utc).timestamp() if now is None else now
        moment = datetime.fromtimestamp(now, timezone.utc)
        configs = settings.get("climate_rooms", {})
        configs = configs if isinstance(configs, Mapping) else {}
        global_presence = settings.get("occupancy_global", {})
        global_presence = global_presence if isinstance(global_presence, Mapping) else {}
        areas = ar.async_get(hass)
        reports, tracked, members = {}, set(), {}
        raw = {room.area_id: room for room in rooms if areas.async_get_area(room.area_id) is not None}
        # Include potential peers even without selected doors, but never
        # invent a monitoring room from a stale saved connection alone.
        for area, room in raw.items():
            cfg = configs.get(area, {})
            cfg = cfg if isinstance(cfg, Mapping) else {}
            plan = environment.get(area, {}).get("climate_plan", {})
            occupancy, evidence, sources = presence.get(area, (
                plan.get("occupancy", "unknown"), plan.get("occupancy_evidence", ""),
                plan.get("presence_entities", [])))
            sleeping = plan.get("sleeping")
            if sleeping is None:
                from .occupancy_policy import controlled_sleep_presence, shared_home_settings
                from .climate_schedule import scheduled_sleep
                shared = shared_home_settings(global_presence, configs)
                zone = getattr(getattr(hass, "config", None), "time_zone", None) or "UTC"
                local, local_reason = scheduled_sleep(cfg, now, zone)
                sleeping, _ = controlled_sleep_presence(
                    hass, area, shared, set(raw), home_status=home_status,
                    room_status=occupancy, local_sleeping=local, local_reason=local_reason, now=now)
            temperature, _ = room_temperature_evidence(
                hass, settings, area, pinned=cfg.get("temperature_entity"), age_minutes=10)
            rh = _fresh_values(room, "humidity", 0, 100)
            co2 = _fresh_values(room, "co2", 0, 50000)
            windows = list(getattr(room, "windows", ()))
            window_safe = all(win.opened is False for win in windows)
            observed = observe(hass, area, cfg, occupancy=occupancy,
                               occupancy_evidence=evidence,
                               occupancy_sources=[source for source in sources if source !=
                                   global_presence.get("occupied_rooms_entity")],
                               home=home_status, sleeping=sleeping,
                               temperature_c=temperature,
                               humidity_rh=max(rh) if rh else None,
                               co2_ppm=max(co2) if co2 else None,
                               window_safe=window_safe,
                               preparing_arrival=plan.get("arrival_preparing") is True,
                               now=moment)
            limits = settings.get("thresholds", {})
            threshold = limits.get("indoor_co2", 1000) if isinstance(limits, Mapping) else 1000
            reports[area] = {**observed, "name": room.name,
                "occupancy": occupancy, "sleeping": sleeping,
                "co2_threshold": threshold,
                "window_open": any(win.opened is True for win in windows),
                "window_evidence_complete": bool(windows) and all(win.opened is not None for win in windows),
                "measurements": {"temperature_c": temperature,
                                 "humidity_rh": max(rh) if rh else None,
                                 "co2_ppm": max(co2) if co2 else None},
                "topology_complete": True}
            for contact in observed["contacts"]:
                entity = contact["entity_id"]
                tracked.add(entity)
                if entity_area(hass, entity) == area and len(members) < MAX_CONTACTS:
                    members[entity] = area
        enrich(reports, outside_safe=outside_safe)
        self._events = {entity: events for entity, events in self._events.items()
                        if entity in members and self._members.get(entity) == members[entity]}
        self._members = members
        active_areas = {area for area, report in reports.items()
                        if report["contacts"] or report["connections"]}
        self._sessions = {area: item for area, item in self._sessions.items() if area in active_areas}
        deadlines = []
        active_links = set()
        for area, report in reports.items():
            contacts = report["contacts"]
            if not contacts and not report["connections"]:
                environment.get(area, {}).pop("door_context", None)
                continue
            signature = tuple((c["entity_id"], c["kind"], c["target_area"], c["report_timeout_minutes"])
                              for c in contacts) + (_source_signature(settings, area),)
            report["session"] = self._session(area, signature, report["boundary"], now)
            report["presence_recheck_hint"] = False
            for contact in contacts:
                age = contact.get("state_age_seconds")
                if contact.get("state") == "closed" and isinstance(age, (int, float)) and age < 120:
                    deadlines.append(now + 120 - age)
                report_due = contact.get("report_due_epoch")
                if contact.get("health") == "ok" and isinstance(report_due, (int, float)) and report_due > now:
                    deadlines.append(report_due)
                events = self._events.get(contact["entity_id"], ())
                recent = [stamp for stamp, _ in events if 0 <= now - stamp <= 60]
                if recent:
                    deadlines.append(max(recent) + 61)
                    report["presence_recheck_hint"] = True
                    if home_status == "away":
                        report["advisories"].append(_advice("door_activity_while_away",
                                                          contact=contact["entity_id"]))
                if len(recent) >= 6:
                    report["advisories"].append(_advice("contact_chattering",
                                                      contact=contact["entity_id"]))
            for link in report["connections"]:
                if link["owner_area"] != area:
                    continue  # One sample per physical edge, not per endpoint.
                key = (area, link["contact"], link["other_area"], link["kind"],
                       _source_signature(settings, area), _source_signature(settings, link["other_area"]))
                active_links.add(key)
                if link["state"] not in ("open", "closed") or "temperature_difference_c" not in link:
                    continue
                history = self._links.setdefault(key, {"last": None, "open": deque(maxlen=240),
                                                       "closed": deque(maxlen=240)})
                if history["last"] is None or now - history["last"] >= 60:
                    history[link["state"]].append((now, abs(link["temperature_difference_c"])))
                    history["last"] = now
                observations = {}
                for mode in ("open", "closed"):
                    values = [value for stamp, value in history[mode] if 0 <= now - stamp <= 86400]
                    observations[mode] = {"samples": len(values),
                        "mean_absolute_temperature_difference_c": round(sum(values) / len(values), 2) if values else None}
                link["observations"] = observations
                link["observation_note"] = "Not a causal heat-transfer or energy-savings estimate"
            report["advisories"] = report["advisories"][:12]
            report["no_energy_savings_estimate"] = True
            environment.setdefault(area, {})["door_context"] = report
        self._links = {key: value for key, value in self._links.items() if key in active_links}
        self._next_deadline = min(deadlines) if deadlines else None
        return reports, tracked
