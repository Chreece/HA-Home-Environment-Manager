"""Distance evidence for the selected members of one HEM household."""
from __future__ import annotations

from collections.abc import Mapping
from math import asin, cos, isfinite, radians, sin, sqrt


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def radius(settings, key):
    meters = _number(settings.get(key))
    return meters if meters is not None and 0 < meters <= 1_000_000 else 0


def trackers(settings):
    selected = settings.get("proximity_trackers")
    if not isinstance(selected, list):
        return ()
    return tuple(sorted({entity for entity in selected if isinstance(entity, str)
                         and entity.startswith(("person.", "device_tracker."))}))


def coordinates(attributes):
    lat = _number(attributes.get("latitude"))
    lon = _number(attributes.get("longitude"))
    if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180:
        return None
    return lat, lon


def home_center(hass):
    zone = hass.states.get("zone.home")
    if zone is None or zone.state in ("unknown", "unavailable") or zone.attributes.get("restored"):
        return None
    return coordinates(zone.attributes)


def boundary(hass, settings, selected, center, meters):
    """One certain inside fix wins. All fixes must be beyond the exit margin to rearm."""
    from .freshness_policy import configured_limit
    from .occupancy_policy import _fresh

    if not selected or center is None or not meters:
        return "unknown"
    limit = configured_limit(settings, family="home_presence", minutes_key="source_stale_minutes",
                             mode_key="source_freshness_mode")
    lat, lon = map(radians, center)
    result = "outside"
    for entity in selected:
        state = hass.states.get(entity)
        if not _fresh(state, limit):
            result = "unknown"
            continue
        attrs = state.attributes
        point = coordinates(attrs)
        accuracy = _number(attrs.get("gps_accuracy", 0))
        if point is None or accuracy is None or accuracy < 0:
            result = "unknown"
            continue
        other_lat, other_lon = map(radians, point)
        half_lat = sin((other_lat - lat) / 2)
        half_lon = sin((other_lon - lon) / 2)
        chord = half_lat ** 2 + cos(lat) * cos(other_lat) * half_lon ** 2
        distance = 2 * 6_371_000 * asin(sqrt(min(1.0, chord)))
        if distance + accuracy <= meters:
            return "inside"
        if distance - accuracy <= meters + min(50, meters * 0.1) and result != "unknown":
            result = "boundary"
    return result


def active_trackers(settings):
    if not isinstance(settings, Mapping) or not settings.get("proximity_trackers"):
        return ()
    # Native Home reports are household evidence even with both GPS radii off.
    return trackers(settings)
