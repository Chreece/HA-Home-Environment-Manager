"""Room-local, evidence-qualified ventilation advice; never device actuation.

An absent indoor pollutant sensor is not a polluted-air measurement. Reminders
are based on a *verified transition* out of sleep or after a sufficiently
long verified room vacancy; no event is fabricated on Home Assistant startup.

Window energy advice needs a verified local OPEN contact, a fresh physical room
temperature, a configured heat/cool setpoint, and a sustained observed trend.
All per-room state is bounded and advisory-only. Existing device/window/sleep
safety controllers remain the sole owners of physical hardware.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import time
from typing import Any, Callable

from .logic import Reason, Recommendation, Window

VACANCY_SECONDS = 2 * 3600
REFRESH_OPPORTUNITY_SECONDS = 35 * 60
REFRESH_COOLDOWN_SECONDS = 4 * 3600
WINDOW_OPEN_MIN_SECONDS = 180
WINDOW_TREND_DELTA_C = 0.20
NEAR_TARGET_C = 0.80
ENERGY_RESET_MARGIN_C = 1.50
MAX_ROOMS = 128


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    v = float(value)
    return v if isfinite(v) and -60 <= v <= 85 else None


@dataclass
class _State:
    occupancy: str = "unknown"
    sleeping: bool | None = None
    vacancy_since: float | None = None
    pending: str | None = None
    pending_until: float = 0.0
    last_refresh_notice: float = float("-inf")
    observed_open_at: float | None = None
    base_temperature: float | None = None
    last_temperature: float | None = None
    energy_kind: str | None = None


class RoomVentilationMonitor:
    """No timer, sensor, HA I/O or service calls; called on manager plan ticks."""

    def __init__(self, clock: Callable[[], float] = time) -> None:
        self.clock = clock
        self._rooms: dict[str, _State] = {}

    def clear(self) -> None:
        self._rooms.clear()

    def acknowledge(self, area: str, reason: str) -> None:
        """Only a successfully submitted air-refresh notification consumes a trigger."""
        s = self._rooms.get(area)
        if s and s.pending == reason:
            s.pending = None
            s.pending_until = 0.0
            s.last_refresh_notice = self.clock()

    def prune(self, areas: set[str]) -> None:
        for area in tuple(self._rooms):
            if area not in areas:
                self._rooms.pop(area, None)

    def observe(
        self, *, area: str, name: str, windows: tuple[Window, ...],
        occupancy: str, sleeping: bool | None,
        has_air_sensor: bool, outside_safe: bool,
        temperature_c: float | None,
        heat_target_c: float | None,
        cool_target_c: float | None,
    ) -> tuple[dict, Recommendation | None]:
        now = self.clock()
        if not isinstance(now, (int, float)) or not isfinite(now) or now < 0:
            return {"air_refresh_status": "clock_unverified",
                    "window_energy_status": "clock_unverified"}, None
        if not isinstance(area, str) or not area:
            return {"air_refresh_status": "invalid_room",
                    "window_energy_status": "invalid_room"}, None
        if area not in self._rooms and len(self._rooms) >= MAX_ROOMS:
            return {"air_refresh_status": "room_limit",
                    "window_energy_status": "room_limit"}, None

        first = area not in self._rooms
        s = self._rooms.setdefault(area, _State())
        occupied = occupancy if occupancy in ("occupied", "unoccupied") else "unknown"
        sleep = sleeping if sleeping in (True, False) else None
        opened = tuple(w for w in windows if w.opened is True)
        closed = tuple(w for w in windows if w.opened is False)
        unknown_window = any(w.opened is None for w in windows)

        # Never infer a wake/arrival from a newly discovered state at startup.
        # Unknown presence breaks a continuous, verified vacancy interval.
        if first:
            if occupied == "unoccupied":
                s.vacancy_since = now
        else:
            if occupied == "unoccupied":
                if s.occupancy != "unoccupied":
                    s.vacancy_since = now
                s.pending = None
            elif occupied == "unknown":
                s.vacancy_since = None
                s.pending = None
            elif occupied == "occupied":
                returned = (s.occupancy == "unoccupied"
                            and s.vacancy_since is not None
                            and 0 <= now - s.vacancy_since <= 30 * 86400
                            and now - s.vacancy_since >= VACANCY_SECONDS)
                woke = s.sleeping is True and sleep is False
                if (returned or woke) and not has_air_sensor:
                    if now - s.last_refresh_notice >= REFRESH_COOLDOWN_SECONDS:
                        s.pending = "air_refresh_wake" if woke else "air_refresh_return"
                        s.pending_until = now + REFRESH_OPPORTUNITY_SECONDS
                s.vacancy_since = None
        s.occupancy = occupied
        s.sleeping = sleep

        temp = _number(temperature_c)
        heat = _number(heat_target_c)
        cool = _number(cool_target_c)
        energy_status = "window_closed"
        energy: Recommendation | None = None

        if not opened:
            s.observed_open_at = None
            s.base_temperature = None
            s.last_temperature = None
            s.energy_kind = None
        elif unknown_window:
            # A local unknown contact cannot certify the total open/closed
            # configuration. Still observe verified opened windows, but don't
            # infer a stable closed air refresh.
            energy_status = "window_contacts_incomplete"
            s.observed_open_at = None
            s.base_temperature = None
            s.last_temperature = None
            s.energy_kind = None
        elif temp is None or heat is None and cool is None:
            energy_status = "temperature_or_thermal_target_unavailable"
            s.observed_open_at = None
            s.base_temperature = None
            s.last_temperature = None
            s.energy_kind = None
        else:
            if (s.observed_open_at is None or now < s.observed_open_at
                    or now - s.observed_open_at > 86400):
                s.observed_open_at = now
                s.base_temperature = temp
                s.energy_kind = None
            base = s.base_temperature
            elapsed = now - s.observed_open_at
            s.last_temperature = temp
            energy_status = "observing_open_temperature"
            if elapsed >= WINDOW_OPEN_MIN_SECONDS and base is not None:
                delta = temp - base
                if heat is not None and temp <= heat + NEAR_TARGET_C and delta <= -WINDOW_TREND_DELTA_C:
                    s.energy_kind = "window_heat_loss"
                elif cool is not None and temp >= cool - NEAR_TARGET_C and delta >= WINDOW_TREND_DELTA_C:
                    s.energy_kind = "window_cooling_loss"
                elif s.energy_kind == "window_heat_loss" and (
                        heat is None or temp >= heat + ENERGY_RESET_MARGIN_C):
                    s.energy_kind = None
                elif s.energy_kind == "window_cooling_loss" and (
                        cool is None or temp <= cool - ENERGY_RESET_MARGIN_C):
                    s.energy_kind = None
                if s.energy_kind:
                    target = heat if s.energy_kind == "window_heat_loss" else cool
                    energy_status = "close_window_to_save_energy"
                    energy = Recommendation(
                        "close", area, name, opened,
                        (Reason(s.energy_kind, value=f"{temp:.1f} °C / {target:.1f} °C"),),
                    )

        if opened:
            # Someone is already airing: don't tell them to open again. The
            # energy monitor can still ask for closure after measured loss.
            s.pending = None
            air_status = "window_open"
        elif has_air_sensor:
            s.pending = None
            air_status = "indoor_air_sensor_present"
        elif s.pending and (now > s.pending_until or occupied != "occupied"
                            or sleep is not False):
            s.pending = None
            air_status = "opportunity_expired_or_room_unverified"
        elif s.pending:
            air_status = ("refresh_recommended" if outside_safe and not unknown_window
                          else "outdoor_or_window_not_verified")
        elif sleep is True:
            air_status = "sleeping"
        elif occupied == "unknown":
            air_status = "room_presence_unknown"
        else:
            air_status = "time_based_monitoring"

        notice: Recommendation | None = energy
        if (notice is None and s.pending and outside_safe
                and occupied == "occupied" and sleep is False
                and not opened and not unknown_window):
            notice = Recommendation(
                "open", area, name, closed,
                (Reason(s.pending),),
            )
        return ({
            "air_refresh_status": air_status,
            "window_energy_status": energy_status,
            "method": "occupancy_sleep_timing_without_indoor_air_measurement",
            "has_indoor_pollutant_sensor": bool(has_air_sensor),
            "heat_target_c": round(heat, 2) if heat is not None else None,
            "cool_target_c": round(cool, 2) if cool is not None else None,
            "measured_room_temperature_c": round(temp, 2) if opened and temp is not None else None,
            "open_window_entities": [w.entity_id for w in opened],
            "pending_reason": s.pending,
            "automatic_device_actuation": False,
        }, notice)
