"""Device-independent thermal watchdog for a HEM-authorized OFF episode.

Thermal trend evidence is *not* proof of physical valve/relay state. The
physical command path may only repeat a genuine OFF operation through HEM's
existing durable journal and live authority checks. This module has no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

MIN_OFF_SECONDS = 30 * 60
MIN_SAMPLE_SPAN_SECONDS = 15 * 60
MIN_SAMPLE_STEP_SECONDS = 120
MAX_SAMPLE_AGE_SECONDS = 10 * 60
MIN_EXCESS_C = 1.5
MIN_RISE_C = 0.7
MAX_SAMPLES = 20
MAX_WATCH_SECONDS = 24 * 60 * 60
MIN_RECOVERY_INTERVAL_SECONDS = 10 * 60
MAX_OFF_RECOVERY_ATTEMPTS = 2

MESSAGES = {
    "en": {
        "title": "Possible heating after shutdown",
        "suspected": (
            "HEM commanded {name} OFF in {room}, but the room temperature rose "
            "from {first:.1f}°C to {current:.1f}°C after it should have stopped "
            "(heating target {target:.1f}°C). The device still reports OFF. "
            "Residual heat or other heat sources are possible; physical heating "
            "is not confirmed. HEM will attempt at most two guarded OFF repeats "
            "while the device remains available."
        ),
        "exhausted": (
            "Possible heating fault persists for {name} in {room}: "
            "{current:.1f}°C versus heating target {target:.1f}°C. "
            "HEM has reached its limit of {attempts} OFF repeats. "
            "Home Assistant still reports OFF, which does not confirm "
            "that the valve or relay actually stopped. Please check the heater."
        ),
    },
    "de": {
        "title": "Mögliche Heizleistung nach Abschaltung",
        "suspected": (
            "HEM hat {name} in {room} ausgeschaltet. Die Raumtemperatur stieg "
            "trotzdem nach der Abschaltung von {first:.1f}°C auf {current:.1f}°C "
            "(Heiz-Sollwert {target:.1f}°C). Das Gerät meldet weiterhin AUS. "
            "Restwärme oder andere Wärmequellen sind möglich; eine tatsächliche "
            "Heizleistung ist nicht bestätigt. HEM versucht maximal zwei "
            "abgesicherte AUS-Befehle, sofern das Gerät erreichbar bleibt."
        ),
        "exhausted": (
            "Möglicher Heizfehler bei {name} in {room}: {current:.1f}°C bei "
            "Sollwert {target:.1f}°C. HEM hat {attempts} AUS-Wiederholungen "
            "ausgeschöpft. Die AUS-Meldung bestätigt nicht den tatsächlichen "
            "Ventil- oder Relaiszustand. Bitte Heizgerät kontrollieren."
        ),
    },
    "el": {
        "title": "Πιθανή θέρμανση μετά την απενεργοποίηση",
        "suspected": (
            "Το HEM έδωσε εντολή OFF στη συσκευή {name} στο δωμάτιο {room}, "
            "όμως η θερμοκρασία αυξήθηκε από {first:.1f}°C σε {current:.1f}°C "
            "μετά τη διακοπή (στόχος θέρμανσης {target:.1f}°C). "
            "Η συσκευή εξακολουθεί να αναφέρει OFF. Μπορεί να υπάρχει "
            "υπολειπόμενη θερμότητα ή άλλη πηγή θέρμανσης· η πραγματική "
            "λειτουργία δεν έχει επιβεβαιωθεί. Το HEM θα επαναλάβει την εντολή "
            "OFF έως δύο φορές, μόνο όταν η συσκευή είναι διαθέσιμη και ασφαλής."
        ),
        "exhausted": (
            "Παραμένει πιθανό πρόβλημα θέρμανσης στη συσκευή {name} στο {room}: "
            "{current:.1f}°C έναντι στόχου {target:.1f}°C. Το HEM εξάντλησε "
            "{attempts} επαναλήψεις OFF. Η αναφορά OFF δεν επιβεβαιώνει φυσική "
            "διακοπή της βαλβίδας ή του ρελέ. Ελέγξτε τη συσκευή."
        ),
    },
}


def verified_heat_shutdown(domain: str, modes: tuple[str, ...],
                           previous_state: str | None,
                           hvac_action: str | None) -> bool:
    """Only observe a heating direction that HEM actually turned OFF."""
    if "heat" not in modes or "off" not in modes:
        return False
    if domain == "climate":
        return previous_state == "heat" or (
            previous_state in ("auto", "heat_cool") and hvac_action == "heating"
        )
    return (domain in ("switch", "input_boolean", "number", "input_number")
            and previous_state not in (None, "off", "unknown", "unavailable", "0", "0.0"))


@dataclass
class ThermalWatch:
    """Session-local samples bound to one genuine OFF, room sensors and effect."""

    source_ids: tuple[str, ...]
    off_since: float
    samples: list[tuple[float, float]] = field(default_factory=list)
    effect: str = "heat"
    sampled_target: float | None = None
    moisture_samples: list[tuple[float, float]] = field(default_factory=list)

    def observe(self, *, now: float, temperature_c: float | None,
                target_c: float | None, source_ids: tuple[str, ...],
                off_since: float, other_heat_sources_clear: bool,
                independent_heat_output: bool | None = None,
                direction: str = "heat",
                room_temperature_c: float | None = None) -> str:
        """Return none/suspected/confirmed; temperature or RH is not proof of ON.

        The old keyword names remain for binary compatibility with the
        published heating watchdog. For humidity they carry relative humidity
        percentage points and the caller also provides the direction.
        """
        if direction == "heat":
            # Keep b21 heating thresholds as-is, including standalone tests.
            rising, settle, span, excess, rise = (
                True, MIN_OFF_SECONDS, MIN_SAMPLE_SPAN_SECONDS,
                MIN_EXCESS_C, MIN_RISE_C,
            )
            lower, upper, target_min, target_max = -30, 60, 5, 40
        else:
            from .off_state_profiles import EFFECTS
            profile = EFFECTS.get(direction)
            if profile is None:
                self.samples.clear()
            self.moisture_samples.clear()
                return "none"
            rising, settle, span, excess, rise = (
                profile.rising, profile.settle_seconds,
                profile.trend_seconds, profile.excess, profile.change,
            )
            lower, upper = profile.minimum, profile.maximum
            target_min, target_max = profile.goal_min, profile.goal_max
        if (not isfinite(now) or not isfinite(off_since) or now < off_since
                or now - off_since > MAX_WATCH_SECONDS
                or source_ids != self.source_ids
                or abs(off_since - self.off_since) > 1):
            self.samples.clear()
            self.moisture_samples.clear()
            return "none"
        if (temperature_c is None or target_c is None
                or not isfinite(temperature_c) or not isfinite(target_c)
                or not lower <= temperature_c <= upper
                or not target_min <= target_c <= target_max
                or not other_heat_sources_clear):
            self.samples.clear()
            self.moisture_samples.clear()
            return "none"
        moisture = None
        if direction in ("humidify", "dry"):
            # Natural room cooling can raise RH without adding moisture. Do
            # not accuse an appliance or repeat OFF unless water vapor itself
            # also changed in the suspicious direction.
            from .off_state_profiles import absolute_humidity_gm3
            moisture = absolute_humidity_gm3(room_temperature_c, temperature_c)
            if moisture is None:
                self.samples.clear()
                self.moisture_samples.clear()
                return "none"
        # A new mode or effective target invalidates the old trend. Otherwise
        # changing an away/comfort/mold target could fabricate a false alarm.
        if (self.effect != direction
                or self.sampled_target is not None and abs(self.sampled_target-target_c) > .05):
            self.samples.clear()
            self.moisture_samples.clear()
        self.effect = direction
        self.sampled_target = target_c
        # Residual heater/cooler output, humidity buffering and sensor
        # equilibration must finish before ANY trend sample is admitted.
        if now - off_since < settle:
            self.samples.clear()
            self.moisture_samples.clear()
            return "none"
        if self.samples and (now < self.samples[-1][0]
                or now - self.samples[-1][0] > MAX_SAMPLE_AGE_SECONDS):
            self.samples.clear()
            self.moisture_samples.clear()
        if (not self.samples
                or now - self.samples[-1][0] >= MIN_SAMPLE_STEP_SECONDS):
            self.samples.append((now, temperature_c))
            self.samples = self.samples[-MAX_SAMPLES:]
            if moisture is not None:
                self.moisture_samples.append((now, moisture))
                self.moisture_samples = self.moisture_samples[-MAX_SAMPLES:]
        if len(self.samples) < 2:
            return "none"
        first_time, first_value = self.samples[0]
        polarity = 1 if rising else -1
        if (now - first_time < span
                or polarity * (temperature_c - target_c) < excess
                or polarity * (temperature_c - first_value) < rise):
            return "none"
        if moisture is not None and (
            not self.moisture_samples or
            polarity * (moisture - self.moisture_samples[0][1]) < 0.45
        ):
            return "none"
        return "confirmed" if independent_heat_output is True else "suspected"


def recovery_due(watch: dict, now: float, *, guarded: bool) -> bool:
    """Deterministic two-attempt limit, with no reset on HA restart."""
    if not guarded or not isinstance(watch, dict) or not isfinite(now):
        return False
    attempts = watch.get("attempts", 0)
    off = watch.get("off_since")
    last = watch.get("last_attempt_at")
    if (type(attempts) is not int or not 0 <= attempts < MAX_OFF_RECOVERY_ATTEMPTS
            or type(off) not in (int, float) or not isfinite(off)
            or not MIN_OFF_SECONDS <= now - off <= MAX_WATCH_SECONDS):
        return False
    return last is None or (
        type(last) in (int, float) and isfinite(last)
        and 0 <= last <= now and now - last >= MIN_RECOVERY_INTERVAL_SECONDS
    )
