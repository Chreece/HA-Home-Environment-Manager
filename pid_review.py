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


def notification_text(spec: Any, review: dict) -> str:
    def values(name: str) -> str:
        old = review["current"][name]
        chosen = review["apply"][name]
        target = review["recommended"][name]
        return f"**{name.upper()}**: {old:.5g} → {chosen:.5g} (model target {target:.5g})"
    return (
        f"PID calibration recommendation for **{str(spec.name)[:96]}**.\n\n"
        f"{values('kp')}\n\n{values('ki')}\n\n{values('kd')}\n\n"
        f"Confidence: **{review['confidence']}**, "
        f"{review['valid_cycles']} verified normal operating cycles.\n\n"
        "Approve or Discard using the two **PID review** button entities "
        "on this HEM managed device. If an explicitly configured Home "
        "Assistant Companion mobile target is available, its notification "
        "also includes **Approve** and **Discard** action buttons.\n\n"
        "Approve saves only the shown conservative next-step gains, not "
        "the more distant mathematical target. It requires the physical "
        "device to be safely OFF and the proposal to remain current. "
        "No device is switched ON or OFF for calibration."
    )


def _mobile_targets(hass: Any, manager: Any) -> list[tuple[str, str]]:
    """Only previously user-selected mobile-app targets; no household fanout."""
    from .const import CONF_NOTIFY_TARGETS
    targets = manager.settings.get(CONF_NOTIFY_TARGETS, ())
    if not isinstance(targets, (list, tuple)):
        return []
    found = []
    for target in dict.fromkeys(targets):
        if not isinstance(target, str) or not target.startswith("notify."):
            continue
        service = target.partition(".")[2]
        if service.startswith("mobile_app_") and hass.services.has_service("notify", service):
            found.append(("service", service))
    return found


async def async_publish_review(hass: Any, manager: Any, spec: Any, review: dict) -> bool:
    """Notify HA and user-configured phones without blocking physical actuation.

    Caller persists the exact pending review BEFORE dispatch. Failure to
    deliver never auto-approves a recommendation.
    """
    if not is_pending(review):
        return False
    title = "HEM · PID calibration approval"
    body = notification_text(spec, review)
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
         "title": "Approve", "authenticationRequired": True},
        {"action": f"{ACTION_PREFIX}DISCARD_{review['id']}",
         "title": "Discard", "authenticationRequired": True},
    ]
    for kind, target in _mobile_targets(hass, manager):
        try:
            await hass.services.async_call(
                "notify", target, {
                    "title": title, "message": body,
                    "data": {
                        "tag": mobile_tag(manager.entry.entry_id, spec.identifier),
                        "actions": actions,
                    },
                }, blocking=True,
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
    for _, target in _mobile_targets(hass, manager):
        try:
            await hass.services.async_call(
                "notify", target, {
                    "message": "clear_notification",
                    "data": {"tag": mobile_tag(manager.entry.entry_id, spec.identifier)},
                }, blocking=True,
            )
        except Exception:
            _LOGGER.debug("Unable to clear mobile PID review", exc_info=True)
