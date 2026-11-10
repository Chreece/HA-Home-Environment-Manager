"""Unit-aware OFF-response profiles derived solely from advertised HA capabilities.

No brand, radio protocol, per-device identifier or registry workaround here.
A room trend is circumstantial evidence, never a physical actuator ACK.
"""
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class OutputEffect:
    key: str
    metric: str
    rising: bool
    unit: str
    excess: float
    change: float
    settle_seconds: float
    trend_seconds: float
    minimum: float
    maximum: float
    goal_min: float
    goal_max: float

EFFECTS = {
    "heat": OutputEffect("heat", "temperature", True, "°C", 1.5, 0.7,
                         1800, 900, -30, 60, 5, 40),
    "cool": OutputEffect("cool", "temperature", False, "°C", 1.5, 0.7,
                         1800, 900, -30, 60, 5, 40),
    # Relative humidity can fluctuate with room temperature or outdoor air.
    # Use a longer settle window and larger relative-percentage-point changes.
    "humidify": OutputEffect("humidify", "humidity", True, "%RH", 8.0, 6.0,
                             2700, 1200, 0, 100, 10, 90),
    "dry": OutputEffect("dry", "humidity", False, "%RH", 8.0, 6.0,
                        2700, 1200, 0, 100, 10, 90),
}

ACTION_EFFECT = {
    "heating": "heat",
    "cooling": "cool",
    "drying": "dry",
    "dehumidifying": "dry",
    "humidifying": "humidify",
}


def supported(cap, effect: str) -> bool:
    """Use the physical output capability, not a guessed vendor capability."""
    modes = tuple(getattr(cap, "modes", ()) or ())
    if "off" not in modes or effect not in EFFECTS:
        return False
    domain = getattr(cap, "domain", None)
    if domain == "humidifier":
        return (effect == "humidify" and getattr(cap, "humidifying", False) is True
                or effect == "dry" and "dry" in modes
                and getattr(cap, "humidifying", False) is False)
    if domain == "climate":
        return effect in modes or (
            effect in ("heat", "cool") and bool(set(modes) & {"auto", "heat_cool"})
        )
    if domain in ("switch", "input_boolean", "number", "input_number"):
        return effect in ("heat", "cool") and effect in modes
    return False


def shutdown_effect(cap, previous_state: str | None, hvac_action: str | None) -> str | None:
    """Qualify only an observed HEM-commanded ON→OFF in a known direction."""
    domain = getattr(cap, "domain", None)
    modes = tuple(getattr(cap, "modes", ()) or ())
    if "off" not in modes or previous_state in (None, "off", "unknown", "unavailable"):
        return None
    if domain == "climate":
        if previous_state in EFFECTS and supported(cap, previous_state):
            return previous_state
        if previous_state in ("auto", "heat_cool"):
            effect = ACTION_EFFECT.get(hvac_action)
            if effect and supported(cap, effect):
                return effect
        return None
    if domain == "humidifier":
        effect = "humidify" if getattr(cap, "humidifying", False) else "dry"
        return effect if previous_state in ("on", "auto") and supported(cap, effect) else None
    if domain in ("switch", "input_boolean", "number", "input_number"):
        active = previous_state not in ("0", "0.0")
        possible = tuple(e for e in ("heat", "cool") if supported(cap, e))
        return possible[0] if active and len(possible) == 1 else None
    return None


# The two native thermal directions reuse the existing published v0.6.1b21
# heating text without changing its translation contract.
TEXT = {
    "en": {
        "title": "Possible {effect} after shutdown",
        "suspected": ("HEM commanded {name} OFF in {room}, but the independently "
                      "measured room {metric} continued {trend} from {first:.1f}{unit} "
                      "to {current:.1f}{unit} (target {target:.1f}{unit}). "
                      "Home Assistant still reports OFF; actual physical output "
                      "is not confirmed. Residual effects, outdoor air and other "
                      "sources may explain this. HEM will attempt no more than "
                      "two guarded OFF repeats while the device is available."),
        "exhausted": ("Possible unwanted {effect} persists for {name} in {room}: "
                      "{current:.1f}{unit} versus target {target:.1f}{unit}. "
                      "HEM reached its limit of {attempts} OFF repeats. "
                      "The HA OFF report does not prove the physical output has "
                      "stopped. Please inspect the equipment."),
        "effects": {"heat":"heating", "cool":"cooling",
                    "humidify":"humidifying", "dry":"dehumidifying"},
        "trend_up": "rising", "trend_down": "falling",
        "metric_temperature":"temperature", "metric_humidity":"humidity",
    },
    "de": {
        "title": "Mögliche {effect} trotz Abschaltung",
        "suspected": ("HEM hat {name} in {room} ausgeschaltet. Trotzdem ist die "
                      "gemessene Raum-{metric} von {first:.1f}{unit} auf "
                      "{current:.1f}{unit} {trend} (Sollwert {target:.1f}{unit}). "
                      "Home Assistant meldet AUS, aber die tatsächliche "
                      "Abschaltung ist nicht bestätigt. Restwirkung, Außenluft "
                      "oder andere Ursachen sind möglich. HEM wiederholt AUS "
                      "höchstens zweimal unter gesicherten Bedingungen."),
        "exhausted": ("Mögliche {effect} bei {name} in {room}: {current:.1f}{unit} "
                      "statt {target:.1f}{unit}. Das Limit von {attempts} "
                      "AUS-Wiederholungen wurde erreicht. Die Anzeige AUS "
                      "bestätigt nicht den tatsächlichen Gerätezustand. "
                      "Bitte Gerät kontrollieren."),
        "effects": {"heat":"Heizung", "cool":"Kühlung",
                    "humidify":"Befeuchtung", "dry":"Entfeuchtung"},
        "trend_up": "gestiegen", "trend_down": "gesunken",
        "metric_temperature":"Temperatur", "metric_humidity":"Luftfeuchtigkeit",
    },
    "el": {
        "title": "Πιθανή {effect} μετά την απενεργοποίηση",
        "suspected": ("Το HEM έδωσε εντολή OFF στη συσκευή {name} στο δωμάτιο "
                      "{room}, αλλά η {metric} συνέχισε να {trend} από "
                      "{first:.1f}{unit} σε {current:.1f}{unit} (στόχος "
                      "{target:.1f}{unit}). Το Home Assistant αναφέρει OFF, "
                      "αλλά δεν επιβεβαιώνει ότι η συσκευή σταμάτησε πραγματικά. "
                      "Μπορεί να ευθύνονται υπολειπόμενη επίδραση ή άλλες πηγές. "
                      "Το HEM θα επαναλάβει την εντολή OFF έως δύο φορές, "
                      "μόνο όταν οι έλεγχοι ασφάλειας το επιτρέπουν."),
        "exhausted": ("Πιθανή ανεπιθύμητη {effect} από τη συσκευή {name} στο "
                      "{room}: {current:.1f}{unit} αντί στόχου {target:.1f}{unit}. "
                      "Το όριο των {attempts} επαναλήψεων OFF εξαντλήθηκε. "
                      "Η ένδειξη OFF δεν αποδεικνύει φυσική διακοπή. "
                      "Ελέγξτε τη συσκευή."),
        "effects": {"heat":"θέρμανση", "cool":"ψύξη",
                    "humidify":"ύγρανση", "dry":"αφύγρανση"},
        "trend_up": "αυξάνεται", "trend_down": "μειώνεται",
        "metric_temperature":"θερμοκρασία", "metric_humidity":"υγρασία",
    },
}


def notice(effect: str, language: str, kind: str, *,
           name: str, room: str, first: float, current: float,
           target: float, attempts: int = 0) -> tuple[str, str]:
    """Localized advisory; never claim that physical output was confirmed."""
    profile = EFFECTS[effect]
    words = TEXT.get(language, TEXT["en"])
    common = dict(
        effect=words["effects"][effect], name=name, room=room,
        first=first, current=current, target=target,
        unit=profile.unit, attempts=attempts,
        metric=words["metric_" + profile.metric],
        trend=words["trend_up" if profile.rising else "trend_down"],
    )
    return words["title"].format(**common), words[kind].format(**common)
