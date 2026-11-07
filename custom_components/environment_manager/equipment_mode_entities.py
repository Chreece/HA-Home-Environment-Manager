"""Native configuration metadata for independent operating-mode profiles.

These are settings for one physical controller. They never create another
runtime, claim an actuator, or infer a capability from a friendly name.
"""
from __future__ import annotations

from . import equipment_model as model
from .equipment_name_catalog import localized_equipment_name
from .operating_mode_catalog import (
    mode_locale, mode_option_labels, operating_mode_label,
    operating_mode_ui_labels,
)
from .settings_name_catalog import localized_setting_name

TARGET_PROFILES = ("manual", "home", "comfort", "away", "sleep", "eco")


def saved_display_settings(manager, spec, mode: str) -> dict:
    """Render a former mode safely while its native capability is unavailable.

    HA reads attributes even on unavailable entities. This is a saved display
    view only; runtime writers still reject unsupported or replaced sources.
    """
    base = model.base_settings(manager, spec)
    profiles = model.raw_settings(manager, spec).get("mode_settings", {})
    local = profiles.get(mode, {}) if isinstance(profiles, dict) else {}
    local = local if isinstance(local, dict) else {}
    return {**base, **{key: value for key, value in local.items() if key in model.MODE_FIELDS},
            "operating_mode": mode}


def scoped_fields(manager, spec, platform: str):
    """Yield only settings advertised for a proven physical operating mode."""
    field_key = {"select": "select_fields", "number": "number_fields",
                 "switch": "switch_fields"}.get(platform)
    for mode in model.operating_modes(manager, spec):
        descriptor = model.mode_descriptor(manager, spec, mode)
        if descriptor is None:
            continue
        for key in descriptor.get(field_key, ()) if field_key else ():
            yield mode, key
        if platform == "number":
            for profile in TARGET_PROFILES:
                for target in descriptor.get("target_keys", ()):
                    yield mode, f"target_{profile}_{target}"
        if platform == "button" and descriptor.get("pid_supported"):
            for key in ("pid_apply_calibration", "pid_review_approve", "pid_review_discard"):
                yield mode, key
            if "pid_fan_capacity_mode" in descriptor.get("select_fields", ()):
                yield mode, "pid_apply_fan_capacity"


def target_field(key: str):
    """Decode our explicit setting key, never a Home Assistant entity ID."""
    if not key.startswith("target_"):
        return None
    parts = key.split("_")
    if (len(parts) == 3 and parts[1] in TARGET_PROFILES
            and parts[2] in ("heat", "cool", "humidity")):
        return parts[1], parts[2]
    return None


def setting_label(key: str, language: str) -> str:
    if key in ("kp", "ki", "kd"):
        # The thermal legacy name includes °C. Scoped humidity/air-quality
        # loops use their own metric; never label those gains as degrees.
        return f"PID · {key[0].upper()}{key[1:]}"
    target = target_field(key)
    if target:
        profile, direction = target
        inherited = localized_setting_name(
            f"area_climate_profile_{'home' if profile == 'manual' else profile}_{direction}",
            language,
        )
        if inherited:
            if profile == "manual":
                label = mode_option_labels("control_mode", language).get("manual", "Manual")
                return f"{label} · {inherited.rsplit(' · ', 1)[-1]}"
            return inherited.partition(" · ")[2] or inherited
    if key == "preset":
        return localized_setting_name("area_manual_profile", language) or "Profile"
    return localized_equipment_name(key, language)


def scoped_help(key: str, language: str, ordinary: str) -> str:
    language = mode_locale(language)
    if key == "control_mode":
        prefix = {
            "en": "This method belongs only to this operating mode. Changing another mode does not overwrite it. The device still has one physical controller and shared minimum ON/OFF times.",
            "el": "Η μέθοδος αφορά μόνο αυτή τη λειτουργία. Η αλλαγή άλλης λειτουργίας δεν την αντικαθιστά. Η συσκευή διατηρεί έναν φυσικό ελεγκτή και κοινούς ελάχιστους χρόνους λειτουργίας και παύσης.",
            "de": "Dieses Verfahren gilt nur für diese Betriebsart. Änderungen einer anderen Betriebsart überschreiben es nicht. Das Gerät behält einen physischen Regler und gemeinsame Mindestlauf- und Stillstandszeiten.",
        }
    elif target_field(key):
        prefix = {
            "en": "Target for this mode and profile. Until explicitly edited, it follows the room profile. Native limits and room safety limits still apply; a qualified mold demand can require a lower humidity target.",
            "el": "Στόχος για αυτή τη λειτουργία και το προφίλ. Μέχρι να αλλάξει, ακολουθεί το προφίλ του δωματίου. Ισχύουν τα όρια της συσκευής και του δωματίου· επιβεβαιωμένος κίνδυνος μούχλας μπορεί να απαιτεί χαμηλότερο στόχο υγρασίας.",
            "de": "Sollwert für diese Betriebsart und dieses Profil. Bis zur ersten Änderung folgt er dem Raumprofil. Geräte- und Raumgrenzen gelten weiter; bestätigter Schimmelbedarf kann einen niedrigeren Feuchtesollwert erfordern.",
        }
    else:
        return ordinary
    return prefix.get(language, prefix["en"]) + ("\n" + ordinary if ordinary else "")


def scoped_metadata(manager, spec, mode: str, key: str, language: str) -> dict:
    descriptor = model.mode_descriptor(manager, spec, mode) or {}
    return {
        "settings_scope": "operating_mode",
        "setting_key": key,
        "operating_mode": mode,
        "operating_mode_label": operating_mode_label(mode, language),
        "operating_mode_ui_labels": operating_mode_ui_labels(language),
        "setting_label": setting_label(key, language),
        "option_labels": mode_option_labels(key, language),
        "native_operating_mode": descriptor.get("native_mode"),
        "pid_supported": descriptor.get("pid_supported", False),
        "target_metric": descriptor.get("metric"),
    }
