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
from .backend_text import presentation_languages, translated_text

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
            "en": "Target for this operating mode and profile. It follows the room profile until edited; profiles keep separate values.",
            "el": "Στόχος για τη συγκεκριμένη λειτουργία και το προφίλ. Μέχρι να τον αλλάξεις, ακολουθεί το προφίλ του δωματίου· κάθε προφίλ διατηρεί τη δική του τιμή.",
            "de": "Sollwert für diese Betriebsart und dieses Profil. Bis zur ersten Änderung gilt der Wert des Raumprofils; jedes Profil behält seinen eigenen Wert.",
        }
        if target_field(key)[1] == "humidity":
            detail = {
                "en": "Automatic/PID dehumidification uses surface relative humidity (%) when mold indication is enabled for this monitored room; otherwise it uses room relative humidity (%). Device and room RH limits apply after conversion. Missing mold data pauses drying.",
                "el": "Στην αφύγρανση με Αυτόματο έλεγχο ή PID, ο στόχος αφορά τη σχετική υγρασία της επιφάνειας (%) όταν η ένδειξη μούχλας είναι ενεργή για το δωμάτιο που παρακολουθείται· διαφορετικά αφορά τη σχετική υγρασία του αέρα (%). Τα όρια υγρασίας της συσκευής και του δωματίου εφαρμόζονται μετά τη μετατροπή. Αν λείπουν δεδομένα για την ένδειξη μούχλας, η αφύγρανση τίθεται σε παύση.",
                "de": "Bei automatischer oder PID-geregelter Entfeuchtung gilt die relative Oberflächenfeuchte (%), wenn der Schimmelindikator für diesen überwachten Raum aktiviert ist; andernfalls gilt die relative Raumluftfeuchte (%). Die Feuchtegrenzen von Gerät und Raum greifen nach der Umrechnung. Fehlen Daten für den Schimmelindikator, pausiert die Entfeuchtung.",
            }
        else:
            detail = {
                "en": "Device and room limits apply.",
                "el": "Ισχύουν τα όρια της συσκευής και του δωματίου.",
                "de": "Die Grenzwerte von Gerät und Raum gelten weiterhin.",
            }
        return (prefix.get(language, translated_text(prefix["en"], language)) + "\n"
                + detail.get(language, translated_text(detail["en"], language)))
    else:
        return ordinary
    return prefix.get(language, translated_text(prefix["en"], language)) + ("\n" + ordinary if ordinary else "")


def scoped_metadata(manager, spec, mode: str, key: str, language: str) -> dict:
    descriptor = model.mode_descriptor(manager, spec, mode) or {}
    locales = presentation_languages(language)
    return {
        "settings_scope": "operating_mode",
        "setting_key": key,
        "operating_mode": mode,
        "operating_mode_label": operating_mode_label(mode, language),
        "operating_mode_label_locales": {locale: operating_mode_label(mode, locale) for locale in locales},
        "operating_mode_ui_labels": operating_mode_ui_labels(language),
        "operating_mode_ui_labels_locales": {locale: operating_mode_ui_labels(locale) for locale in locales},
        "setting_label": setting_label(key, language),
        "setting_label_locales": {locale: setting_label(key, locale) for locale in locales},
        "option_labels": mode_option_labels(key, language),
        "option_labels_locales": {locale: mode_option_labels(key, locale) for locale in locales},
        "native_operating_mode": descriptor.get("native_mode"),
        "pid_supported": descriptor.get("pid_supported", False),
        "target_metric": descriptor.get("metric"),
    }
