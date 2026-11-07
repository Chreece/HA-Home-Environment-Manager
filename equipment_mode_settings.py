"""Pure, backwards-compatible storage for one actuator's operating profiles.

The physical controller keeps its identifier, authorization and output history.
Operating profiles are configuration only; creating one never selects an HVAC
mode, acquires another owner, or sends a native command.  The old flat profile
is a fallback until a user explicitly writes a scoped setting.
"""
from __future__ import annotations

from .config_data import mutable_copy as deepcopy
from .pid_calibration import MODEL_FIELDS
from .pid_fan_capacity import CAPACITY_FIELDS

MODE_SETTINGS_VERSION = 1
MODE_KEYS = ("heat", "cool", "dry", "humidify", "fan_only", "auto", "heat_cool")
PROFILE_NAMES = ("manual", "home", "comfort", "away", "sleep", "eco")
MODE_METADATA_KEYS = frozenset(("mode_settings_version", "mode_settings"))
# The transient key deliberately participates in an effective command context:
# the same setpoint in another direction is not the same outstanding intent.
EFFECTIVE_MODE_KEY = "operating_mode"

# Every other accepted setting remains physical/global: identity and exact
# provenance grants, power supply, physical dwell, presence, window protection,
# announcements, rated CADR and device speed limits.  requested_mode is also
# global: editing an inactive profile must never select it for operation.
MODE_FIELDS = frozenset((
    "control_mode", "preset", "kp", "ki", "kd", "sample_seconds", "cycle_seconds",
    "pid_calibration_method", "pid_adaptation_mode", "pid_last_calibration",
    "pid_fan_capacity_mode", "pid_fan_capacity_for_mode", "pid_fan_capacity_models",
    "profile_targets", "profile_fans", "fan_mode", "swing_mode",
    "swing_horizontal_mode", "quiet_sleep", "quiet_occupied",
    "quiet_percentage", "quiet_fan_mode", *MODEL_FIELDS, *CAPACITY_FIELDS,
))


def has_mode_settings(raw: dict) -> bool:
    return (type(raw.get("mode_settings_version")) is int
            and raw["mode_settings_version"] == MODE_SETTINGS_VERSION
            and isinstance(raw.get("mode_settings"), dict))


def persist_changes(raw: dict, changes: dict, *, operating_mode: str | None = None) -> dict:
    """Apply a validated PATCH, without flattening a resolved profile into raw.

    Validation of actual native capabilities and parameter values belongs to
    the caller.  Unknown persisted fields are retained for compatibility.  A
    caller must pass only intentional edits and intentional normalization
    fields, never its complete effective settings dictionary.
    """
    if not isinstance(raw, dict) or not isinstance(changes, dict):
        raise ValueError("invalid_equipment_settings")
    if MODE_METADATA_KEYS & changes.keys():
        raise ValueError("mode_settings_must_be_edited_through_operating_mode")
    result = deepcopy(raw)
    patch = {key: deepcopy(value) for key, value in changes.items()
             if key != EFFECTIVE_MODE_KEY}
    if operating_mode is None:
        result.update(patch)
        return result
    if operating_mode not in MODE_KEYS:
        raise ValueError("unsupported_operating_mode")
    version = raw.get("mode_settings_version")
    if version is not None and (type(version) is not int or version != MODE_SETTINGS_VERSION):
        raise ValueError("unsupported_mode_settings_version")
    if "mode_settings" in raw and not isinstance(raw["mode_settings"], dict):
        raise ValueError("invalid_mode_settings")
    profiles = result.setdefault("mode_settings", {})
    previous = profiles.get(operating_mode, {})
    if not isinstance(previous, dict):
        raise ValueError("invalid_operating_mode_profile")
    profile = deepcopy(previous)
    for key, value in patch.items():
        if key in MODE_FIELDS:
            profile[key] = value
        else:
            result[key] = value
    profiles[operating_mode] = profile
    result["mode_settings_version"] = MODE_SETTINGS_VERSION
    return result


def _bound_evidence(value: object, mode: str) -> bool:
    """Only an explicit direction proves that old learned evidence belongs here."""
    if not isinstance(value, dict):
        return False
    evidence_mode = value.get("operating_mode", value.get("direction"))
    return evidence_mode == mode


def resolve_settings(base: dict, raw: dict, mode: str, *, native_mode: str,
                     target_keys: tuple[str, ...]) -> dict:
    """Produce an isolated effective profile, with no inactive-table metadata.

    Old hand-tuned gains remain a compatibility fallback.  Unbound learned
    plant/capacity evidence does not become evidence for every new direction.
    Manual room targets retain their old fallback; new automatic-profile
    overrides are accepted only from the explicitly scoped profile.
    """
    if mode not in MODE_KEYS:
        raise ValueError("unsupported_operating_mode")
    profiles = raw.get("mode_settings", {}) if has_mode_settings(raw) else {}
    scoped = profiles.get(mode, {})
    scoped = scoped if isinstance(scoped, dict) else {}
    scoped = {key: deepcopy(value) for key, value in scoped.items() if key in MODE_FIELDS}
    result = {key: deepcopy(value) for key, value in base.items()
              if key not in MODE_METADATA_KEYS and key != EFFECTIVE_MODE_KEY}
    result.update(scoped)
    result[EFFECTIVE_MODE_KEY] = mode
    result["requested_mode"] = native_mode

    legacy_targets = base.get("profile_targets", {})
    legacy_targets = legacy_targets if isinstance(legacy_targets, dict) else {}
    mode_targets = scoped.get("profile_targets", {})
    mode_targets = mode_targets if isinstance(mode_targets, dict) else {}
    targets = {}
    for profile in PROFILE_NAMES:
        old = legacy_targets.get(profile, {}) if profile == "manual" else {}
        old = old if isinstance(old, dict) else {}
        local = mode_targets.get(profile, {})
        local = local if isinstance(local, dict) else {}
        values = {key: deepcopy(value) for key, value in {**old, **local}.items()
                  if key in target_keys}
        if values:
            targets[profile] = values
    result["profile_targets"] = targets

    old_fans = base.get("profile_fans", {})
    new_fans = scoped.get("profile_fans", {})
    result["profile_fans"] = {
        key: deepcopy(value) for key, value in {
            **(old_fans if isinstance(old_fans, dict) else {}),
            **(new_fans if isinstance(new_fans, dict) else {}),
        }.items() if key in PROFILE_NAMES
    }

    evidence = scoped.get("pid_last_calibration")
    if "pid_last_calibration" not in scoped:
        evidence = base.get("pid_last_calibration")
        if not _bound_evidence(evidence, mode):
            evidence = None
    elif isinstance(evidence, dict):
        direction = evidence.get("operating_mode", evidence.get("direction"))
        if direction is not None and direction != mode:
            evidence = None
    result["pid_last_calibration"] = deepcopy(evidence)
    for key in MODEL_FIELDS:
        if key not in scoped and not _bound_evidence(base.get("pid_last_calibration"), mode):
            result[key] = 0.0

    # Curves already contain direction and endpoint provenance.  Keeping only
    # this mode avoids unrelated curve edits invalidating a pending command.
    curves = result.get("pid_fan_capacity_models")
    curve = curves.get(native_mode) if isinstance(curves, dict) else None
    result["pid_fan_capacity_models"] = (
        {native_mode: deepcopy(curve)}
        if isinstance(curve, dict) and curve.get("direction") == native_mode else {}
    )
    for key in CAPACITY_FIELDS:
        if key not in scoped and base.get("pid_fan_capacity_for_mode") != native_mode:
            result[key] = 0.0
    if native_mode in ("heat", "cool", "dry", "fan_only"):
        result["pid_fan_capacity_for_mode"] = native_mode
    else:
        result["pid_fan_capacity_for_mode"] = "choose"
    return result
