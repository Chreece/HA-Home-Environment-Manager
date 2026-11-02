"""Safely reconcile an interrupted native HA command on explicit Resume.

Pure, read-only state classification: NO Home Assistant service calls, no
output changes, no adoption of a foreign source. An unconfirmed command never
disappears merely because a timeout elapsed. If feedback is contradictory or
not freshly confirmed, the user must verify the *physical* appliance and
press Check and Continue twice with a full minute of unchanged observations.

The controller owns persistence and the final before/after-Store state guards.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import hashlib
import json
import math
from typing import Any

COMMAND_SETTLE_SECONDS = 120.0
TWO_CHECK_SECONDS = 60.0
_CONTROL_FIELDS = (
    "temperature", "target_temp_low", "target_temp_high", "humidity",
    "fan_mode", "percentage", "preset_mode", "swing_mode",
    "swing_horizontal_mode", "hvac_action",
)
_FORBIDDEN_ACTIONS_WHEN_OFF = frozenset((
    "heating", "cooling", "drying", "defrosting", "preheating",
    "fan", "fan_only", "humidifying",
))


def _number(value: Any, minimum: float, maximum: float) -> float | None:
    if type(value) not in (int, float):
        return None
    number = float(value)
    return number if math.isfinite(number) and minimum <= number <= maximum else None


def _stamp(state: Any, attribute: str, now: float) -> float | None:
    dt = getattr(state, attribute, None)
    try:
        timestamp = dt.timestamp() if isinstance(dt, datetime) else None
    except (OverflowError, ValueError, TypeError):
        timestamp = None
    return _number(timestamp, 0, now) if timestamp is not None else None


def _recent_feedback(state: Any, command_at: float, now: float) -> bool:
    """A live HA entity update *after* dispatch is enough for an exact ACK.

    A restored last_changed before dispatch is not a post-command ACK.
    Use last_reported where available (HA versions that implement it),
    otherwise last_updated / last_changed.
    """
    return any(
        (timestamp := _stamp(state, field, now)) is not None
        and timestamp >= command_at
        for field in ("last_reported", "last_updated", "last_changed")
    )


def _fingerprint(state: Any) -> dict | None:
    if state is None or getattr(state, "state", None) in (
        None, "unknown", "unavailable"
    ):
        return None
    attrs = getattr(state, "attributes", {})
    if not isinstance(attrs, Mapping):
        return None
    if state.state == "off" and attrs.get("hvac_action") in _FORBIDDEN_ACTIONS_WHEN_OFF:
        return None
    if not isinstance(state.state, str) or len(state.state) > 64:
        return None
    return {
        "state": state.state,
        "attributes": {
            key: attrs[key] for key in _CONTROL_FIELDS if key in attrs
        },
    }


def _command_key(pending: Any) -> str | None:
    if not isinstance(pending, dict):
        return None
    values = {
        key: pending.get(key) for key in (
            "entity", "phase", "when", "service", "expected", "power", "output_on"
        )
    }
    try:
        packed = json.dumps(values, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError, OverflowError):
        return None
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()[:32]


def _requested(expected: Any) -> str:
    if not isinstance(expected, dict):
        return "unverified command"
    state = expected.get("state")
    if isinstance(state, str) and len(state) < 65:
        return state
    attributes = expected.get("attributes")
    if isinstance(attributes, dict):
        for key in ("temperature", "target_temp_low", "target_temp_high",
                    "humidity", "fan_mode", "percentage", "preset_mode"):
            value = attributes.get(key)
            if isinstance(value, (str, int, float)) and len(str(value)) <= 32:
                return f"{key}={value}"
    return "the requested output"


def check_pending(pending: Any, state: Any, now: float,
                  probe: Any, *, matches_expected: bool) -> dict:
    """Return immutable decision, bounded diagnostic fields and next action.

    'confirmed': an actual ACK is verified; phase 'commanded' was already
       acknowledged by HA, or the interrupted intent has fresh feedback
       explicitly matching the requested state after the physical settle.
    'verified': a user has twice checked the *same* reported current state,
       separated by >=60s, after the command has been settled >=120s.
    Other decisions never clear a command nor permit Resume.
    """
    entity = pending.get("entity") if isinstance(pending, dict) else None
    requested = _requested(
        pending.get("expected") if isinstance(pending, dict) else None
    )
    current = getattr(state, "state", None)
    outcome = {
        "decision": "invalid",
        "entity": entity if isinstance(entity, str) and len(entity) <= 160 else None,
        "requested": requested,
        "observed": current if isinstance(current, str) and len(current) <= 64
                    else "unavailable",
        "remaining_seconds": None,
        "phase": pending.get("phase") if isinstance(pending, dict) else None,
        "needs_physical_check": True,
    }
    if not isinstance(pending, dict) or not isinstance(entity, str):
        return outcome
    expected = pending.get("expected")
    phase = pending.get("phase")
    if (phase not in ("intent", "commanded") or not isinstance(expected, dict)
            or not expected or _command_key(pending) is None):
        return outcome
    live = _fingerprint(state)
    if live is None:
        return {**outcome, "decision": "unavailable"}
    if phase == "commanded" and matches_expected:
        return {**outcome, "decision": "confirmed",
                "needs_physical_check": False}
    when = _number(pending.get("when"), 0, now)
    if when is None:
        return {**outcome, "decision": "unknown_dispatch_time"}
    age = now - when
    if age < COMMAND_SETTLE_SECONDS:
        return {**outcome, "decision": "settling",
                "remaining_seconds": math.ceil(COMMAND_SETTLE_SECONDS-age)}
    if phase == "intent" and matches_expected and _recent_feedback(
        state, when, now
    ):
        return {**outcome, "decision": "confirmed",
                "needs_physical_check": False}
    key = _command_key(pending)
    if (not isinstance(probe, dict)
            or probe.get("command") != key
            or probe.get("observed") != live):
        return {**outcome, "decision": "first_check",
                "command": key, "observation": live}
    began = _number(probe.get("at"), 0, now)
    if began is None:
        return {**outcome, "decision": "first_check",
                "command": key, "observation": live}
    remaining = max(0.0, TWO_CHECK_SECONDS - (now - began))
    if remaining > 0:
        return {**outcome, "decision": "second_check_wait",
                "remaining_seconds": math.ceil(remaining)}
    return {**outcome, "decision": "verified"}


def instructions(result: dict, *, language: str = "en") -> str:
    """Clear HA button error in the server language; no cryptic ACK jargon."""
    code = result.get("decision")
    entity = result.get("entity") or "the physical device"
    current = result.get("observed") or "unavailable"
    target = result.get("requested") or "unknown"
    seconds = result.get("remaining_seconds")
    suffix = (
        f"Requested {target}; device reports {current}. "
        f"Native entity: {entity}. "
    )
    if language.replace("_", "-").split("-")[0].lower() == "de":
        if code == "settling" or code == "second_check_wait":
            return (f"HEM wartet noch {seconds} Sekunden, bevor es den vorherigen "
                    f"Gerätebefehl sicher prüfen kann. Ist-Zustand: {current}, "
                    f"angefordert: {target} ({entity}). Gerät bitte nicht aus- "
                    f"und wieder einschalten. Danach 'Prüfen und fortsetzen' erneut drücken.")
        if code == "first_check":
            return (f"Ein früherer Gerätebefehl ist nicht bestätigt. {entity} zeigt "
                    f"{current} statt angefordertem {target}. Prüfe am echten Gerät, "
                    "dass sein Zustand zur Home-Assistant-Anzeige passt. "
                    "Warte 60 Sekunden ohne Änderung und drücke "
                    "'Prüfen und fortsetzen' erneut. Kein Befehl gesendet.")
        return (f"HEM kann den vorherigen Befehl noch nicht sicher prüfen. "
                f"{entity}: gemeldet {current}, angefordert {target}. "
                "Prüfe die Erreichbarkeit und den echten Betriebszustand. "
                "Den Strom nicht zum Zurücksetzen abschalten.")
    if language.replace("_", "-").split("-")[0].lower() == "el":
        if code in ("settling", "second_check_wait"):
            return (f"Το HEM χρειάζεται ακόμη {seconds} δευτερόλεπτα πριν επιβεβαιώσει "
                    f"με ασφάλεια την κατάσταση της συσκευής {entity}. "
                    f"Τρέχουσα: {current}, ζητήθηκε: {target}. "
                    "Έλεγξε την πραγματική συσκευή χωρίς να διακόψεις το ρεύμα "
                    "και πάτησε ξανά «Έλεγχος και συνέχεια».")
        if code == "first_check":
            return (f"Μια προηγούμενη εντολή δεν επιβεβαιώθηκε. Η {entity} αναφέρει "
                    f"{current} ενώ ζητήθηκε {target}. Βεβαιώσου ότι η πραγματική "
                    "συσκευή συμφωνεί με το Home Assistant. Περίμενε 60 "
                    "δευτερόλεπτα χωρίς αλλαγή και πάτησε ξανά "
                    "«Έλεγχος και συνέχεια». Δεν εστάλη καμία νέα εντολή.")
        return (f"Το HEM δεν μπορεί ακόμη να επαληθεύσει με ασφάλεια "
                f"τη συσκευή {entity}: αναφέρει {current}, ζητήθηκε {target}. "
                "Έλεγξε τη σύνδεση και την πραγματική λειτουργία της, "
                "χωρίς επανεκκίνηση της παροχής ρεύματος.")
    if code in ("settling", "second_check_wait"):
        return (f"HEM is waiting another {seconds} seconds to verify the previous "
                f"command safely. {suffix}Check the actual device, leave its "
                "power alone, then press Check and Continue again. No command sent.")
    if code == "first_check":
        return ("A previous device command was not confirmed. " + suffix +
                "Check that the real appliance agrees with Home Assistant. "
                "Leave it unchanged for 60 seconds, then press Check and "
                "Continue again. No device command has been sent.")
    if code == "unavailable":
        return ("The physical device is unavailable or reports contradictory "
                "activity. " + suffix + "Check its native Home Assistant "
                "entity and connectivity; do not power-cycle it to clear this pause.")
    return ("HEM cannot safely verify the previous native command yet. " +
            suffix + "Check the device's real state and its native Home "
            "Assistant entity; do not power-cycle it. If this persists, "
            "collect the controller's read-only recovery diagnostics. "
            "(interrupted native command)")
