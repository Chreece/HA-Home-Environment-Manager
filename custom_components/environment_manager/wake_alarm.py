"""Leave automatic Sleep ahead of a configured local or timestamp alarm.

Reads HA states only. The manager arms one timer using alarm_evidence(); the
sleep policy rechecks live inputs and never issues device commands from here.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, time, timedelta
import logging
import math
import re
from time import time as clock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_LOGGER = logging.getLogger(__name__)
_ALARM = "wake_alarm_entity"
_LEAD = "wake_lead_minutes_entity"
_TRACKERS = "environment_manager.wake_alarm_trackers"
_ALARM_DOMAINS = {"sensor", "input_datetime", "time", "datetime"}
_LEAD_DOMAINS = {"sensor", "number", "input_number"}
_TIME = re.compile(r"\d\d:\d\d(?::\d\d(?:\.\d{1,6})?)?\Z")
_DATE_TIME = re.compile(r"\d{4}-\d\d-\d\d[Tt ]\d\d:\d\d")
# A scheduled callback may run just after the phone has published tomorrow's
# alarm. Accept only a recently crossed, previously witnessed ringing instant.
_LATE_RING_SECONDS = 120
# Do not restore an old wake latch after e.g. a holiday shutdown during which
# the previous sleep episode may have ended and a different one started.
_RESTORE_MAX_AGE = 24 * 3600


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _pair(settings):
    if isinstance(settings, Mapping):
        alarm, lead = settings.get(_ALARM), settings.get(_LEAD)
        if (isinstance(alarm, str) and alarm.partition('.')[0] in _ALARM_DOMAINS
                and isinstance(lead, str) and lead.partition('.')[0] in _LEAD_DOMAINS
                and alarm != lead and '.' in alarm and '.' in lead):
            return alarm, lead
    return None


def _lead_minutes(state):
    if state is None or state.attributes.get("restored") is True:
        return None
    unit = state.attributes.get("unit_of_measurement")
    if unit is not None and str(unit).strip().casefold() not in ("", "min", "minute", "minutes"):
        return None
    value = _number(state.state)
    return value if value is not None and value >= 0 and math.isfinite(value*60) else None


def _local_epoch(moment, zone, preferred=None):
    # Round-tripping rejects the nonexistent local hour when clocks jump.
    # In a repeated hour follow the helper's exact timestamp when provided;
    # otherwise choose the first occurrence, so a daily alarm rings only once.
    epochs = set()
    for fold in (0, 1):
        candidate = moment.replace(tzinfo=zone, fold=fold).timestamp()
        if datetime.fromtimestamp(candidate, zone).replace(tzinfo=None) == moment:
            epochs.add(candidate)
    return preferred if preferred in epochs else min(epochs, default=None)


def _alarm_epoch(hass, state, now):
    if (state is None or state.attributes.get("restored") is True
            or not isinstance(state.state, str)):
        return None
    value = state.state.strip()
    try:
        if _DATE_TIME.match(value):
            moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if moment.tzinfo is not None:
                return moment.timestamp()
            zone = ZoneInfo(hass.config.time_zone)
            return _local_epoch(moment, zone, _number(state.attributes.get('timestamp')))
        if _TIME.fullmatch(value):
            wall = time.fromisoformat(value)
            zone = ZoneInfo(hass.config.time_zone)
            today = datetime.fromtimestamp(now, zone).date()
            # Tomorrow's local hour may not exist (spring DST change).
            for offset in range(3):
                target = _local_epoch(datetime.combine(today + timedelta(days=offset), wall), zone)
                if target is not None and target >= now:
                    return target
    except (AttributeError, OverflowError, OSError, ValueError, TypeError, ZoneInfoNotFoundError):
        pass
    return None


def alarm_evidence(hass, settings, *, now=None):
    """Resolve source states to UTC seconds, including past dated alarms.

    A time-only source names the next real occurrence in HA's local timezone.
    Missing or invalid data has no deadline and cannot activate pre-wake.
    """
    result = dict(status='not_configured', alarm_at=None, wake_at=None, lead_minutes=None)
    pair = _pair(settings)
    if not pair:
        return result
    now = _number(clock() if now is None else now)
    if now is None:
        return {**result, 'status': 'invalid_clock'}
    lead = _lead_minutes(hass.states.get(pair[1]))
    if lead is None:
        return {**result, 'status': 'invalid_wake_lead'}
    target = _alarm_epoch(hass, hass.states.get(pair[0]), now)
    if target is None:
        return {**result, 'status': 'invalid_wake_alarm', 'lead_minutes': lead}
    start = target - 60 * lead
    return dict(status='past_alarm' if now > target else 'wake_window' if now >= start
                else 'scheduled', alarm_at=target, wake_at=start, lead_minutes=lead)


def wake_source_options(hass, saved_config):
    """Offer time-bearing alarm entities and minute or unitless numeric inputs."""
    alarms, leads = set(), set()
    now = clock()
    for domain in sorted(_ALARM_DOMAINS | _LEAD_DOMAINS):
        for state in hass.states.async_all(domain):
            entity, attrs = state.entity_id, state.attributes
            if domain in _ALARM_DOMAINS and (
                domain in ('time', 'datetime') or
                (domain == 'input_datetime' and attrs.get('has_time') is True) or
                (domain == 'sensor' and attrs.get('device_class') == 'timestamp') or
                _alarm_epoch(hass, state, now) is not None
            ):
                alarms.add(entity)
            unit = str(attrs.get('unit_of_measurement') or '').strip().casefold()
            if domain in _LEAD_DOMAINS and (unit in ('min', 'minute', 'minutes') or
                    not unit and (domain in ('number', 'input_number') or
                                  _lead_minutes(state) is not None)):
                leads.add(entity)
    if isinstance(saved_config, Mapping):
        for field, options in ((_ALARM, alarms), (_LEAD, leads)):
            value = saved_config.get(field)
            if isinstance(value, str) and '.' in value:
                options.add(value)
    return sorted(alarms), sorted(leads)


class WakeAlarm:
    """One config entry's per-room and household sleep episodes."""
    def __init__(self, pair=None, store=None):
        self.pair = pair
        self.store = store
        self.active = {}  # scope -> previously triggered alarm instant
        self.armed = {}   # volatile: previously seen, eligible imminent/future alarm
        self.dirty = False

    def snapshot(self):
        return {'pair': list(self.pair or ()), 'active': self.active.copy()}

    def changed(self):
        self.dirty = True
        if self.store is not None:
            try:
                self.store.async_delay_save(self.snapshot, 1)
            except Exception:
                _LOGGER.exception('Could not schedule wake alarm history save')

    def discard(self, scope):
        self.armed.pop(scope, None)
        if self.active.pop(scope, None) is not None:
            self.changed()

    async def restore(self, now):
        data = await self.store.async_load()
        if not isinstance(data, dict):
            return
        active = data.get('active')
        if self.pair and data.get('pair') == list(self.pair) and isinstance(active, dict):
            self.active = {scope: float(at) for scope, at in active.items()
                           if isinstance(scope, str) and type(at) in (float, int)
                           and math.isfinite(at) and at >= now - _RESTORE_MAX_AGE}
        if data != self.snapshot():
            self.changed()

    def override(self, hass, settings, scope, raw_sleep, now):
        pair = _pair(settings)
        if pair != self.pair:
            self.pair = pair
            self.armed.clear()
            self.active.clear()
            self.changed()
        if not pair or raw_sleep is False:
            self.discard(scope)
            return False
        if raw_sleep is not True or _number(now) is None:
            self.armed.pop(scope, None)
            return False
        active = self.active.get(scope)
        if active is not None and now >= active:
            # Already woke for this episode. The phone may now clear its alarm
            # or report tomorrow's; neither should put the device back to sleep.
            return True
        info = alarm_evidence(hass, settings, now=now)
        target = info['alarm_at']
        old = self.armed.get(scope)
        crossed = (old is not None and old <= now <= old + _LATE_RING_SECONDS
                   and (target == old or target is not None and target > now
                        or info['status'] == 'invalid_wake_alarm'))
        if info['status'] == 'wake_window' or crossed:
            # Phone alarm sensors may immediately clear at the ringing instant.
            # An already witnessed alarm still counts during the short callback
            # allowance; an invalid lead value or an unwitnessed alarm does not.
            ring = old if crossed else target
            if active != ring:
                self.active[scope] = ring
                self.changed()
            if target is None:
                self.armed.pop(scope, None)
            else:
                self.armed[scope] = target
            return True
        # Postponement, shorter lead time or cancellation BEFORE the alarm
        # re-evaluates Sleep immediately. A stale past timestamp cannot arm it.
        self.discard(scope)
        if target is not None and target > now:
            self.armed[scope] = target
        return False


async def async_start_wake(hass, entry_id, settings):
    """Install one tracker; restore already-started wake episodes on reload."""
    from homeassistant.helpers.storage import Store
    tracker = WakeAlarm(_pair(settings), Store(hass, 1, f'environment_manager.wake_alarm_{entry_id}'))
    hass.data.setdefault(_TRACKERS, {})[entry_id] = tracker
    try:
        await tracker.restore(clock())
    except Exception:
        _LOGGER.exception('Could not restore wake alarm history')


async def async_stop_wake(hass, entry_id):
    trackers = hass.data.get(_TRACKERS, {})
    tracker = trackers.pop(entry_id, None)
    if not trackers:
        hass.data.pop(_TRACKERS, None)
    if tracker is not None and tracker.store is not None and tracker.dirty:
        await tracker.store.async_save(tracker.snapshot())


def wake_override(hass, settings, scope, raw_sleep, *, now=None):
    """Suppress Sleep only, using the entry's tracker; never grant occupancy."""
    if not isinstance(settings, Mapping):
        return False
    entry = settings.get('_wake_entry_id')
    if not isinstance(entry, str):
        return False
    tracker = getattr(hass, 'data', {}).get(_TRACKERS, {}).get(entry)
    if tracker is None:
        return False
    return tracker.override(hass, settings, scope, raw_sleep, clock() if now is None else now)


def observe_wake_episodes(hass, entry_id, settings, known_areas, *,
                          home_status, room_settings, observed_rooms=None, now=None):
    """Keep episode boundaries current even while no device consumes Sleep.

    The manager calls this once per capture, independent of device modes and
    household opt-ins. Otherwise disabling all consumers during daytime could
    preserve yesterday's wake latch into a new night's sleep. Remembered room
    scopes also remain observed when their controller or monitored area is
    temporarily removed. Only current negative sleep evidence or a changed
    source pair ends an episode; elapsed time alone never clears a live one.
    """
    tracker = getattr(hass, 'data', {}).get(_TRACKERS, {}).get(entry_id)
    if tracker is None:
        return
    stamp = clock() if now is None else now
    if not _pair(settings):
        if tracker.pair or tracker.active or tracker.armed:
            tracker.override(hass, settings, 'household', False, stamp)
        return
    if _number(stamp) is None:
        return
    from .occupancy_policy import (
        controlled_sleep_presence, household_sleep_presence, room_presence,
    )
    from .climate_schedule import scheduled_sleep

    # Reuse the raw policy without applying wake suppression a second time.
    raw_settings = {key: value for key, value in settings.items()
                    if key not in (_ALARM, _LEAD)}
    household, _ = household_sleep_presence(
        hass, raw_settings, known_areas, home_status=home_status)
    tracker.override(hass, settings, 'household', household, stamp)
    areas = {area for area in known_areas if isinstance(area, str) and area}
    areas.update(scope[5:] for scope in set(tracker.active) | set(tracker.armed)
                 if scope.startswith('room:') and scope[5:])
    room_settings = room_settings if isinstance(room_settings, Mapping) else {}
    observed_rooms = observed_rooms if isinstance(observed_rooms, Mapping) else {}
    zone = getattr(getattr(hass, 'config', None), 'time_zone', None) or 'UTC'
    for area in areas:
        cfg = room_settings.get(area)
        cfg = cfg if isinstance(cfg, Mapping) else {}
        observation = observed_rooms.get(area)
        if not isinstance(observation, (tuple, list)) or not observation:
            observation = room_presence(hass, area, cfg, raw_settings,
                                        known_areas=areas, home_status=home_status)
        local, reason = scheduled_sleep(cfg, stamp, zone)
        sleeping, _ = controlled_sleep_presence(
            hass, area, raw_settings, areas, home_status=home_status,
            room_status=observation[0], local_sleeping=local, local_reason=reason,
            now=stamp,
        )
        tracker.override(hass, settings, 'room:' + area, sleeping, stamp)
