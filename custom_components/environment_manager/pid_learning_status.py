"""Read-only, mode-bound explanation of passive PID calibration.

This module never observes hardware, schedules work, or authorizes a change.
It describes the existing evidence, including why learning cannot progress.
"""
from __future__ import annotations

import json
import math
from typing import Any

from .pid_passive import AUTO_INTERVAL_S, AUTO_MIN_CYCLES, bounded_gains

ADAPTIVE = ("adaptive_suggest", "adaptive_auto")
SUPPORTED_MODES = ("heat", "cool", "dry")
SUPPORTED_DOMAINS = ("climate", "humidifier", "switch", "input_boolean")


def eligibility(cfg: dict, domain: str | None) -> tuple[str, str] | None:
    """Return a descriptive hold, not permission to operate an appliance."""
    if cfg.get("pid_calibration_method") not in ADAPTIVE:
        return "disabled", "manual_calibration"
    if cfg.get("control_mode") != "pid":
        return "inactive", "pid_not_active"
    if cfg.get("requested_mode") not in SUPPORTED_MODES:
        return "unsupported", "unsupported_operating_mode"
    if domain is None:
        return "waiting", "device_unavailable"
    if domain not in SUPPORTED_DOMAINS:
        return "unsupported", "unsupported_output"
    return None


def context_mode(context: Any) -> str | None:
    try:
        values = json.loads(context)
        return values[3] if isinstance(values, list) and len(values) > 3 else None
    except (TypeError, ValueError):
        return None


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def snapshot(*, cfg: dict, domain: str | None, record: dict,
             progress: dict | None, observer_context: str | None,
             hold: dict | None, observed: dict, native_state: str | None,
             active: bool, ready: bool, now: float) -> dict:
    """Describe this active mode without leaking another mode's evidence."""
    method = cfg.get("pid_calibration_method", "manual")
    mode = cfg.get("operating_mode") or cfg.get("requested_mode")
    saved = record.get("pid_passive")
    saved = saved if isinstance(saved, dict) else {}
    summary = saved.get("summary") if context_mode(saved.get("context")) == mode else {}
    summary = summary if isinstance(summary, dict) else {}
    progress = progress if context_mode(observer_context) == mode and isinstance(progress, dict) else {}
    count = progress.get("valid_cycles", summary.get("valid_cycles", 0))
    result = {
        "status": "collecting", "reason": "waiting_for_complete_cycles",
        "eligible": False, "operating_mode": mode,
        "valid_cycles": count if type(count) is int and count >= 0 else 0,
        "required_cycles": AUTO_MIN_CYCLES if method == "adaptive_auto" else 3,
    }

    def finish(status: str, reason: str, **extra: Any) -> dict:
        return {**result, "status": status, "reason": reason, **extra}

    if blocked := eligibility(cfg, domain):
        return finish(*blocked)
    if not active or not ready:
        return finish("inactive", "controller_inactive")
    if native_state in (None, "unknown", "unavailable"):
        return finish("waiting", "device_unavailable")
    result["eligible"] = True
    if record.get("paused"):
        return finish("waiting", "controller_paused")
    upstream = record.get("upstream")
    upstream = upstream if isinstance(upstream, dict) else {}
    if record.get("pending") or upstream.get("pending"):
        return finish("waiting", "pending_command")
    state = str(observed.get("status", ""))
    if (state.startswith(("window_", "sleep_room_", "waiting_for_"))
            or state in ("paused", "control_measurement_missing_or_stale",
                         "awaiting_physical_acknowledgement")):
        return finish("waiting", "controller_paused", detail=observed.get("reason") or state)
    if (isinstance(hold, dict) and hold.get("operating_mode") == mode
            and hold.get("reason")):
        return finish("waiting", hold["reason"])

    review = record.get("pid_passive_review")
    if (method == "adaptive_suggest" and isinstance(review, dict)
            and review.get("operating_mode") == mode and review.get("state") == "pending"
            and review.get("context") == saved.get("context")
            and review.get("cycle_at") == summary.get("last_cycle_at")
            and (observer_context is None or observer_context == review.get("context"))):
        return finish("ready_for_review", "recommendation_pending")

    last = cfg.get("pid_last_calibration")
    last = last if isinstance(last, dict) else {}
    if last.get("operating_mode", last.get("direction", mode)) != mode:
        last = {}
    if method == "adaptive_auto" and last.get("method") == "passive_imc_lambda":
        at = last.get("at")
        if _finite(at) and _finite(now) and 0 <= now - at < AUTO_INTERVAL_S:
            return finish("cooldown", "calibration_cooldown",
                          next_application_at=at + AUTO_INTERVAL_S)
        old_cycle = last.get("cycle_at")
        cycles = saved.get("cycles", []) if context_mode(saved.get("context")) == mode else []
        if _finite(old_cycle) and isinstance(cycles, list) and sum(
            isinstance(c, dict) and _finite(c.get("at")) and c["at"] > old_cycle
            for c in cycles
        ) < 2:
            return finish("collecting", "new_cycles_required")

    proposed = summary.get("suggested_gains")
    if isinstance(proposed, dict) and summary.get("status") in ("validated", "suggestion_only"):
        if bounded_gains(cfg, proposed) is None:
            return finish("no_change", "no_gain_change")
        if (method == "adaptive_auto" and summary.get("status") == "validated"
                and (native_state != "off" or record.get("power"))):
            return finish("waiting_for_safe_off", "waiting_for_safe_off")
    if summary.get("status") in ("inconsistent_plant_response", "identified_gains_outside_safe_bounds"):
        return finish("collecting", summary["status"])
    if progress.get("last_rejection_reason"):
        return finish("collecting", progress["last_rejection_reason"])
    if (last and method == "adaptive_suggest" and isinstance(review, dict)
            and review.get("state") == "applied" and review.get("operating_mode") == mode):
        return finish("applied", "applied")
    return result
