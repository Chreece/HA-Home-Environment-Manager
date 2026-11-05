"""One authoritative PID tuning mode and actionable passive-gain reviews.

Persistent HA notifications cannot embed service-call buttons. A persistent
notification exposes the exact recommendation and HEM's two native button
entities; explicitly selected Companion mobile notify targets additionally
receive real Approve/Discard action buttons. No implicit broadcast.
"""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
from typing import Any

from .pid_passive import bounded_gains

_LOGGER = logging.getLogger(__name__)

CLASSICAL_METHODS = ("manual", "imc_lambda", "cohen_coon")
ADAPTIVE_METHODS = ("adaptive_suggest", "adaptive_auto")
ALL_METHODS = (*CLASSICAL_METHODS, *ADAPTIVE_METHODS)
ACTION_PREFIX = "HEM_PID_REVIEW_"
_ACTION_PATTERN = re.compile(r"^HEM_PID_REVIEW_(APPROVE|DISCARD)_([a-f0-9]{32})$")


def selected_method(raw: dict) -> str:
    """Map Beta82's two overlapping selectors to one authoritative choice.

    A saved explicit classic method wins over legacy passive adaptation, so
    legacy Cohen-Coon and passive bounded can NEVER become two gain writers.
    Once a unified selector is edited, its legacy passive field is stored as
    disabled; subsequent selection of Manual remains Manual.
    """
    name = raw.get("pid_calibration_method", "manual")
    if name in ADAPTIVE_METHODS:
        return name
    if name in ("imc_lambda", "cohen_coon"):
        return name
    legacy = raw.get("pid_adaptation_mode", "observe")
    return {"observe": "adaptive_suggest", "bounded": "adaptive_auto"}.get(
        legacy, "manual"
    )


def legacy_mode(name: str) -> str:
    return {
        "adaptive_suggest": "observe", "adaptive_auto": "bounded",
    }.get(name, "disabled")


def proposal_for(cfg: dict, summary: dict, context: str, now: float) -> dict | None:
    """Build an immutable single-cycle review with the exact gains to apply."""
    if (cfg.get("pid_calibration_method") != "adaptive_suggest"
            or summary.get("status") not in ("suggestion_only", "validated")
            or summary.get("confidence") not in ("medium", "high")
            or not isinstance(summary.get("valid_cycles"), int)
            or summary["valid_cycles"] < 3
            or not isinstance(summary.get("suggested_gains"), dict)
            or not isinstance(summary.get("last_cycle_at"), (int, float))):
        return None
    current = {key: cfg.get(key) for key in ("kp", "ki", "kd")}
    target = summary["suggested_gains"]
    applied = bounded_gains(current, target)
    if applied is None:
        return None
    return {
        "id": secrets.token_hex(16),
        "state": "pending",
        "context": context,
        "cycle_at": summary["last_cycle_at"],
        "created_at": now,
        "current": current,
        "apply": applied,
        "recommended": {key: target.get(key) for key in ("kp", "ki", "kd")},
        "confidence": summary["confidence"],
        "valid_cycles": summary["valid_cycles"],
        "metric": summary.get("metric"),
    }


def is_pending(review: Any) -> bool:
    return (isinstance(review, dict) and review.get("state") == "pending"
            and isinstance(review.get("id"), str)
            and bool(re.fullmatch(r"[a-f0-9]{32}", review["id"])))


def decode_mobile_action(action: Any) -> tuple[str, str] | None:
    match = _ACTION_PATTERN.fullmatch(action) if isinstance(action, str) else None
    if not match:
        return None
    return match.group(1).lower(), match.group(2)


def notification_id(entry_id: str, identifier: str) -> str:
    digest = hashlib.sha256(f"{entry_id}:{identifier}".encode()).hexdigest()[:24]
    return f"hem_pid_review_{digest}"


def mobile_tag(entry_id: str, identifier: str) -> str:
    return notification_id(entry_id, identifier)


def _review_locale(language: str) -> dict:
    base = language.replace("_", "-").split("-", 1)[0].lower()
    return {
        "de": {
            "title": "HEM · PID-Kalibrierung bestätigen",
            "device": "PID-Vorschlag für",
            "model": "Modellziel",
            "confidence": "Konfidenz",
            "cycles": "geprüfte normale Betriebszyklen",
            "instructions": (
                "Mit den Schaltflächen **Vorschlag annehmen** oder "
                "**Vorschlag verwerfen** am HEM-Gerät entscheiden. "
                "Konfigurierte Companion-App-Benachrichtigungen haben "
                "ebenfalls Aktionsschaltflächen."
            ),
            "safety": (
                "Die Übernahme speichert nur den angezeigten kleinen "
                "Anpassungsschritt, nicht sofort das volle Modellziel. "
                "Das Gerät muss sicher AUS sein. Keine Testschaltungen."
            ),
            "approve": "Übernehmen", "discard": "Verwerfen",
        },
        "el": {
            "title": "HEM · Έγκριση βαθμονόμησης PID",
            "device": "Πρόταση PID για",
            "model": "στόχος μοντέλου",
            "confidence": "Αξιοπιστία",
            "cycles": "επαληθευμένοι φυσιολογικοί κύκλοι",
            "instructions": (
                "Επίλεξε **Έγκριση πρότασης** ή **Απόρριψη πρότασης** "
                "από τα δύο κουμπιά της συσκευής HEM. Οι επιλεγμένες "
                "ειδοποιήσεις Companion διαθέτουν επίσης κουμπιά."
            ),
            "safety": (
                "Η έγκριση αποθηκεύει μόνο το μικρό προτεινόμενο βήμα, "
                "όχι άμεσα τον τελικό στόχο του μοντέλου. Η συσκευή "
                "πρέπει να είναι ασφαλώς ΚΛΕΙΣΤΗ. Δεν εκτελείται δοκιμαστική λειτουργία."
            ),
            "approve": "Έγκριση", "discard": "Απόρριψη",
        },
    }.get(base, {
        "title": "HEM · PID calibration approval",
        "device": "PID calibration recommendation for",
        "model": "model target",
        "confidence": "Confidence",
        "cycles": "verified normal operating cycles",
        "instructions": (
            "Approve or Discard using the two **PID review** button "
            "entities on this HEM managed device. Explicitly configured "
            "Companion-app notifications have action buttons too."
        ),
        "safety": (
            "Approve saves only the shown conservative next-step gains, "
            "not the more distant mathematical target. It requires the "
            "device safely OFF and a current proposal. No hardware "
            "is switched for calibration."
        ),
        "approve": "Approve", "discard": "Discard",
    })


def notification_text(spec: Any, review: dict, language: str = "en") -> str:
    labels = _review_locale(language)
    def values(name: str) -> str:
        old = review["current"][name]
        chosen = review["apply"][name]
        target = review["recommended"][name]
        return (f"**{name.upper()}**: {old:.5g} → {chosen:.5g} "
                f"({labels['model']} {target:.5g})")
    return (
        f"{labels['device']} **{str(spec.name)[:96]}**.\n\n"
        f"{values('kp')}\n\n{values('ki')}\n\n{values('kd')}\n\n"
        f"{labels['confidence']}: **{review['confidence']}**, "
        f"{review['valid_cycles']} {labels['cycles']}.\n\n"
        f"{labels['instructions']}\n\n{labels['safety']}"
    )


def _mobile_targets(hass: Any, manager: Any) -> list[tuple[str, str]]:
    """Only previously user-selected mobile-app targets; no household fanout."""
    from .const import CONF_NOTIFY_TARGETS
    targets = manager.settings.get(CONF_NOTIFY_TARGETS, ())
    if not isinstance(targets, (list, tuple)):
        return []
    found = []
    for target in dict.fromkeys(t for t in targets if isinstance(t, str)):
        if not target.startswith("notify."):
            continue
        service = target.partition(".")[2]
        if service.startswith("mobile_app_") and hass.services.has_service("notify", service):
            found.append(("service", service))
            continue
        # New-style notify entities are acceptable only if the entity
        # registry verifies mobile_app provenance. Never attach action
        # tokens to generic home groups or third-party notify services.
        if not hass.services.has_service("notify", "send_message"):
            continue
        try:
            from homeassistant.helpers import entity_registry as er
            entry = er.async_get(hass).async_get(target)
        except (ImportError, AttributeError, TypeError):
            entry = None
        if entry is not None and entry.platform == "mobile_app":
            found.append(("entity", target))
    return found


async def async_publish_review(hass: Any, manager: Any, spec: Any, review: dict) -> bool:
    """Notify HA and user-configured phones without blocking physical actuation.

    Caller persists the exact pending review BEFORE dispatch. Failure to
    deliver never auto-approves a recommendation.
    """
    if not is_pending(review):
        return False
    locale = (manager.settings.get("language") or "auto")
    if locale == "auto":
        locale = getattr(getattr(hass, "config", None), "language", "en")
    labels = _review_locale(str(locale))
    title = labels["title"]
    body = notification_text(spec, review, str(locale))
    sent = False
    if hass.services.has_service("persistent_notification", "create"):
        try:
            await hass.services.async_call(
                "persistent_notification", "create", {
                    "notification_id": notification_id(manager.entry.entry_id, spec.identifier),
                    "title": title, "message": body,
                }, blocking=True,
            )
            sent = True
        except Exception:
            _LOGGER.exception("HEM PID persistent recommendation notification failed")
    actions = [
        {"action": f"{ACTION_PREFIX}APPROVE_{review['id']}",
         "title": labels["approve"], "authenticationRequired": True},
        {"action": f"{ACTION_PREFIX}DISCARD_{review['id']}",
         "title": labels["discard"], "authenticationRequired": True},
    ]
    for kind, target in _mobile_targets(hass, manager):
        try:
            data = {
                "title": title, "message": body,
                "data": {
                    "tag": mobile_tag(manager.entry.entry_id, spec.identifier),
                    "actions": actions,
                },
            }
            if kind == "entity":
                await hass.services.async_call(
                    "notify", "send_message", data,
                    target={"entity_id": target}, blocking=True,
                )
            else:
                await hass.services.async_call(
                    "notify", target, data, blocking=True,
                )
            sent = True
        except Exception:
            _LOGGER.exception("HEM PID actionable mobile notification failed: %s", target)
    return sent


async def async_clear_review(hass: Any, manager: Any, spec: Any) -> None:
    if hass.services.has_service("persistent_notification", "dismiss"):
        try:
            await hass.services.async_call(
                "persistent_notification", "dismiss", {
                    "notification_id": notification_id(manager.entry.entry_id, spec.identifier)
                }, blocking=True,
            )
        except Exception:
            _LOGGER.debug("Unable to clear PID review from HA notifications", exc_info=True)
    for kind, target in _mobile_targets(hass, manager):
        try:
            data = {
                "message": "clear_notification",
                "data": {"tag": mobile_tag(manager.entry.entry_id, spec.identifier)},
            }
            if kind == "entity":
                await hass.services.async_call(
                    "notify", "send_message", data,
                    target={"entity_id": target}, blocking=True,
                )
            else:
                await hass.services.async_call(
                    "notify", target, data, blocking=True,
                )
        except Exception:
            _LOGGER.debug("Unable to clear mobile PID review", exc_info=True)
