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
    """Session-local samples bound to one real OFF command and sensor set."""

    source_ids: tuple[str, ...]
    off_since: float
    samples: list[tuple[float, float]] = field(default_factory=list)

    def observe(self, *, now: float, temperature_c: float | None,
                target_c: float | None, source_ids: tuple[str, ...],
                off_since: float, other_heat_sources_clear: bool,
                independent_heat_output: bool | None = None) -> str:
        """Return none/suspected/confirmed; never assert heat from temperature alone."""
        if (not isfinite(now) or not isfinite(off_since) or now < off_since
                or now - off_since > MAX_WATCH_SECONDS
                or source_ids != self.source_ids
                or abs(off_since - self.off_since) > 1):
            self.samples.clear()
            return "none"
        if (temperature_c is None or target_c is None
                or not isfinite(temperature_c) or not isfinite(target_c)
                or not -30 <= temperature_c <= 60
                or not 5 <= target_c <= 40 or not other_heat_sources_clear):
            self.samples.clear()
            return "none"
        # A hot radiator may continue warming a room for some time after a
        # valid shutdown. Start the trend only *after* that settling window.
        if now - off_since < MIN_OFF_SECONDS:
            self.samples.clear()
            return "none"
        if self.samples and (now < self.samples[-1][0]
                or now - self.samples[-1][0] > MAX_SAMPLE_AGE_SECONDS):
            self.samples.clear()
        if (not self.samples
                or now - self.samples[-1][0] >= MIN_SAMPLE_STEP_SECONDS):
            self.samples.append((now, temperature_c))
            self.samples = self.samples[-MAX_SAMPLES:]
        if len(self.samples) < 2:
            return "none"
        first_time, first_temp = self.samples[0]
        if (now - first_time < MIN_SAMPLE_SPAN_SECONDS
                or temperature_c - target_c < MIN_EXCESS_C
                or temperature_c - first_temp < MIN_RISE_C):
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
