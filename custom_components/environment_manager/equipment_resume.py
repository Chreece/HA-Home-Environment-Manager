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
    # Probe values go into Home Assistant's persistent Store. Reject
    # non-JSON and unbounded native attributes rather than corrupting the
    # safety journal or turning Recorder into a raw device-data dump.
    controls = {}
    for key in _CONTROL_FIELDS:
        if key not in attrs:
            continue
        value = attrs[key]
        if isinstance(value, str):
            if len(value) > 96:
                return None
        elif type(value) in (int, float):
            if not math.isfinite(value):
                return None
        elif value is not None and type(value) is not bool:
            return None
        controls[key] = value
    return {"state": state.state, "attributes": controls}


def _command_key(pending: Any) -> str | None:
    if not isinstance(pending, dict):
        return None
    values = {
        key: pending.get(key) for key in (
            "entity", "phase", "when", "last_attempt_at", "attempts",
            "service", "expected", "power", "output_on"
        )
    }
    try:
        packed = json.dumps(values, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError, OverflowError):
        return None
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()[:32]


def _command_feedback(expected: Any, state: Any, *, language: str = "en",
                      temperature_unit: str | None = None) -> tuple[str, str]:
    """Describe the exact fields the ACK matcher checks, on both sides.

    A climate entity's state (``heat``/``cool``) is its selected mode, not
    its temperature setpoint or measured room temperature. Attribute
    commands must be compared with the same native attributes, including
    missing feedback. These strings are presentation only: no ACK, probe,
    ownership or retry decision depends on them.
    """
    locale = language.replace("_", "-").split("-")[0].lower()
    labels = {
        "en": ("Temperature setpoint", "Lower temperature setpoint",
               "Upper temperature setpoint", "Humidity setpoint", "Fan mode",
               "Percentage", "Preset", "Swing mode", "Horizontal swing mode",
               "Operating mode", "unavailable"),
        "de": ("Temperatur-Sollwert", "Unterer Temperatur-Sollwert",
               "Oberer Temperatur-Sollwert", "Feuchte-Sollwert", "Lüftermodus",
               "Prozentwert", "Voreinstellung", "Schwenkmodus",
               "Horizontaler Schwenkmodus", "Betriebsmodus", "nicht verfügbar"),
        "el": ("Επιθυμητή θερμοκρασία", "Κατώτερη επιθυμητή θερμοκρασία",
               "Ανώτερη επιθυμητή θερμοκρασία", "Επιθυμητή υγρασία",
               "Λειτουργία ανεμιστήρα", "Ποσοστό", "Προεπιλογή",
               "Λειτουργία ταλάντωσης", "Οριζόντια ταλάντωση",
               "Τρόπος λειτουργίας", "μη διαθέσιμη"),
    }
    words = labels.get(locale, labels["en"])
    fields = _CONTROL_FIELDS[:-1]  # hvac_action is feedback, never a target.
    names = dict(zip(fields, words[:9]))
    unavailable = words[-1]
    if not isinstance(expected, dict):
        return "unverified command", unavailable
    current = getattr(state, "state", None)
    live = isinstance(current, str) and current not in ("unknown", "unavailable")
    native = getattr(state, "attributes", {})
    native = native if live and isinstance(native, Mapping) else {}
    # HA's set_temperature accepts the HA temperature unit. Many native
    # entities do not duplicate that unit in their own state attributes.
    unit = native.get("temperature_unit")
    if unit not in ("°C", "°F", "K"):
        unit = temperature_unit if temperature_unit in ("°C", "°F", "K") else None

    def bounded(value: Any, *, numeric: bool = False) -> str | None:
        if numeric:
            if type(value) not in (int, float, str):
                return None
            try:
                value = float(value)
            except (ValueError, TypeError, OverflowError):
                return None
            if not math.isfinite(value) or not -1e8 <= value <= 1e8:
                return None
        if isinstance(value, str) and 0 < len(value) <= 96:
            return value if value not in ("unknown", "unavailable") else None
        if (type(value) in (int, float) and -1e8 <= value <= 1e8
                and math.isfinite(value)):
            text = f"{value:g}"
            return text.replace(".", ",") if locale in ("de", "el") else text
        return None

    desired, observed = [], []
    target_mode = bounded(expected.get("state"))
    attributes = expected.get("attributes")
    attributes = attributes if isinstance(attributes, dict) else {}
    commanded = [field for field in fields if field in attributes]
    if target_mode is not None:
        # Retain the existing concise mode-only diagnostics. When a single
        # command includes both mode and attributes, name every field.
        prefix = words[-2] + " " if commanded else ""
        desired.append(prefix + target_mode)
        observed.append(prefix + ((bounded(current) if live else None) or unavailable))
    for field in commanded:
        numeric = field in ("temperature", "target_temp_low", "target_temp_high",
                            "humidity", "percentage")
        requested = bounded(attributes[field], numeric=numeric)
        actual = bounded(native.get(field), numeric=numeric)
        suffix = (" " + unit if unit else "") if field in (
            "temperature", "target_temp_low", "target_temp_high"
        ) else " %" if field in ("humidity", "percentage") else ""
        desired.append(names[field] + " " + (
            requested + suffix if requested is not None else unavailable
        ))
        observed.append(names[field] + " " + (
            actual + suffix if actual is not None else unavailable
        ))
    return ("; ".join(desired) or "the requested output",
            "; ".join(observed) or unavailable)


def check_pending(pending: Any, state: Any, now: float,
                  probe: Any, *, matches_expected: bool,
                  language: str = "en", temperature_unit: str | None = None) -> dict:
    """Return immutable decision, bounded diagnostic fields and next action.

    'confirmed': an actual ACK is verified; phase 'commanded' was already
       acknowledged by HA, or the interrupted intent has fresh feedback
       explicitly matching the requested state after the physical settle.
    'verified': a user has twice checked the *same* reported current state,
       separated by >=60s, after the command has been settled >=120s.
    Other decisions never clear a command nor permit Resume.
    """
    entity = pending.get("entity") if isinstance(pending, dict) else None
    requested, observed = _command_feedback(
        pending.get("expected") if isinstance(pending, dict) else None,
        state, language=language, temperature_unit=temperature_unit,
    )
    outcome = {
        "decision": "invalid",
        "entity": entity if isinstance(entity, str) and len(entity) <= 160 else None,
        "requested": requested,
        "observed": observed,
        "remaining_seconds": None,
        "phase": pending.get("phase") if isinstance(pending, dict) else None,
        "needs_physical_check": True,
    }
    if not isinstance(pending, dict) or not isinstance(entity, str):
        return outcome
    expected = pending.get("expected")
    phase = pending.get("phase")
    if (phase not in ("intent", "retry_intent", "commanded") or not isinstance(expected, dict)
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
    if phase == "retry_intent" or "last_attempt_at" in pending:
        # A retry's original command may be hours old. Only the most recent
        # reserved dispatch can start its settle window or authenticate ACK.
        when = _number(pending.get("last_attempt_at"), when, now)
        if when is None:
            return {**outcome, "decision": "unknown_dispatch_time"}
    age = now - when
    if age < COMMAND_SETTLE_SECONDS:
        return {**outcome, "decision": "settling",
                "remaining_seconds": math.ceil(COMMAND_SETTLE_SECONDS-age)}
    if phase in ("intent", "retry_intent") and matches_expected and _recent_feedback(
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


def pending_feedback_message(result: dict, *, language: str = "en") -> str:
    """Describe normal in-flight feedback without invoking manual recovery.

    Reading a pending command is not a Resume attempt. The regular runtime
    still owns ACK checks and bounded retries; this text changes no policy.
    """
    entity = str(result.get("entity") or "the physical device")[:160]
    desired = str(result.get("requested") or "unknown")[:512]
    actual = str(result.get("observed") or "unavailable")[:512]
    locale = language.replace("_", "-").split("-")[0].lower()
    if locale == "el":
        return (
            f"Το HEM περιμένει επιβεβαίωση για το αίτημα {desired} στη "
            f"συσκευή {entity}. Το Home Assistant αναφέρει {actual}. "
            "Το HEM ελέγχει αυτόματα την αναφορά της συσκευής. "
            "Δεν χρειάζεται να ξαναπατήσεις κουμπί."
        )
    if locale == "de":
        return (
            f"HEM wartet auf die Bestätigung der Anforderung {desired} "
            f"für {entity}. Home Assistant meldet {actual}. "
            "HEM prüft die Geräterückmeldung automatisch. "
            "Erneutes Drücken ist nicht erforderlich."
        )
    return (
        f"HEM is waiting for confirmation of the request {desired} "
        f"for {entity}. Home Assistant reports {actual}. "
        "HEM checks the device feedback automatically; "
        "you do not need to press the button again."
    )


def exhausted_target_message(result: dict, *, language: str = "en") -> str:
    """Keep a failed setpoint visible after safe current-state reconciliation."""
    entity = str(result.get("entity") or "the physical device")[:160]
    desired = str(result.get("requested") or "unknown")[:512]
    actual = str(result.get("observed") or "unavailable")[:512]
    attempts = result.get("command_attempts")
    count = str(attempts) if type(attempts) is int and 1 <= attempts <= 6 else "—"
    locale = language.replace("_", "-").split("-")[0].lower()
    if locale == "el":
        return (
            f"Ζητήθηκε {desired} στη συσκευή {entity}, αλλά το Home Assistant αναφέρει {actual}. "
            f"Η ρύθμιση δεν επιβεβαιώθηκε μετά από {count} προσπάθειες. "
            "Το HEM παρακολουθεί την αναφορά της συσκευής χωρίς να ξεκινά "
            "ξανά τις ίδιες προσπάθειες. Οι προστατευτικές εντολές "
            "απενεργοποίησης παραμένουν διαθέσιμες. Έλεγξε την αρχική "
            "συσκευή στο Home Assistant πριν ζητήσεις νέα προσπάθεια."
        )
    if locale == "de":
        return (
            f"Für {entity} angefordert: {desired}; Home Assistant meldet {actual}. "
            f"Der Sollwert wurde nach {count} Versuchen nicht bestätigt. "
            "HEM überwacht die Rückmeldung, ohne dieselben Versuche neu "
            "zu starten. Schutzbedingtes Ausschalten bleibt möglich. "
            "Prüfe das Originalgerät in Home Assistant, bevor du einen "
            "neuen Versuch anforderst."
        )
    return (
        f"Requested {desired} for {entity}; Home Assistant reports {actual}. "
        f"The target was not confirmed after {count} attempts. "
        "HEM monitors feedback without restarting the same retry sequence. "
        "Protective OFF commands remain available. Check the original "
        "device in Home Assistant before requesting another attempt."
    )


def automatic_recovery_message(result: dict, *, language: str = "en") -> str:
    """Plain-language status for user-requested queued Automatic/PID.

    This changes only the diagnostic text: it never treats HA availability
    as a physical ACK or invents output verification.
    """
    entity = str(result.get("entity") or "the physical device")[:160]
    desired = str(result.get("requested") or "unknown")[:512]
    actual = str(result.get("observed") or "unavailable")[:512]
    locale = language.replace("_", "-").split("-")[0].lower()
    if locale == "el":
        return (
            f"Οι ρυθμίσεις και η Αυτόματη λειτουργία αποθηκεύτηκαν. "
            f"Το HEM ζήτησε {desired} στη συσκευή {entity}, αλλά το "
            f"Home Assistant αναφέρει {actual}. Η συσκευή είναι διαθέσιμη, "
            f"όμως αυτό δεν επιβεβαιώνει ότι εκτέλεσε την προηγούμενη εντολή. "
            f"Το HEM θα επανελέγχει αυτόματα και θα συνεχίσει μόλις "
            f"επαληθευτεί με ασφάλεια. Δεν χρειάζεται να ξαναπατήσεις κουμπί."
        )
    if locale == "de":
        return (
            f"Einstellungen und Automatik sind gespeichert. HEM hat "
            f"{desired} für {entity} angefordert; Home Assistant meldet "
            f"{actual}. Erreichbarkeit allein bestätigt die Ausführung "
            f"nicht. HEM prüft selbstständig weiter und setzt die "
            f"Steuerung erst nach sicherer Bestätigung fort. "
            f"Erneutes Drücken ist nicht erforderlich."
        )
    return (
        f"Settings and Automatic/PID are saved. HEM requested {desired} "
        f"from {entity}, while Home Assistant reports {actual}. An online "
        f"entity does not confirm the earlier physical command was applied. "
        f"HEM will check automatically and resume control when verified; "
        f"you do not need to press the button again."
    )


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
                    "'Prüfen und fortsetzen' erneut. Diese Prüfung hat "
                    "keinen neuen Gerätebefehl gesendet.")
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
                "power alone, then press Check and Continue again. "
                "This check sent no new device command.")
    if code == "first_check":
        return ("A previous device command was not confirmed. " + suffix +
                "Check that the real appliance agrees with Home Assistant. "
                "Leave it unchanged for 60 seconds, then press Check and "
                "Continue again. This check sent no new device command.")
    if code == "unavailable":
        return ("The physical device is unavailable or reports contradictory "
                "activity. " + suffix + "Check its native Home Assistant "
                "entity and connectivity; do not power-cycle it to clear this pause.")
    return ("HEM cannot safely verify the previous native command yet. " +
            suffix + "Check the device's real state and its native Home "
            "Assistant entity; do not power-cycle it. If this persists, "
            "collect the controller's read-only recovery diagnostics. "
            "(interrupted native command)")


def unconfirmed_dispatch_message(info: dict, *, language: str = "en") -> str:
    """Describe intent without claiming either delivery or device failure."""
    requested = info.get("requested") or "?"
    entity = info.get("entity") or "?"
    observed = info.get("observed") or "?"
    if language.split("-", 1)[0] == "el":
        return (f"Δεν έχει επιβεβαιωθεί η αποστολή του αιτήματος {requested} στη συσκευή {entity}. "
                f"Το HEM ελέγχει το αίτημα και την τρέχουσα αναφορά ({observed}). "
                "Αυτό δεν αποτελεί επιβεβαιωμένη αποτυχία απόκρισης της συσκευής.")
    if language.split("-", 1)[0] == "de":
        return (f"Der Versand der Anforderung {requested} an {entity} ist nicht bestätigt. "
                f"HEM prüft die Anforderung und den gemeldeten Zustand ({observed}). "
                "Dies ist kein bestätigter Antwortfehler des Geräts.")
    return (f"Dispatch of the {requested} request to {entity} is not confirmed. "
            f"HEM is checking the request and reported state ({observed}). "
            "This is not a confirmed device nonresponse.")
