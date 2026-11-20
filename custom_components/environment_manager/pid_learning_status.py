"""Read-only, mode-bound explanations of PID calibration.

This module never observes hardware, schedules work, or authorizes a change.
It describes the existing evidence, including why learning cannot progress.
"""
from __future__ import annotations

import json
import math
from typing import Any

from .pid_passive import AUTO_INTERVAL_S, AUTO_MIN_CYCLES, bounded_gains
from .pid_review import (
    calibration_hold, is_pending, review_application_matches, review_projection,
)

ADAPTIVE = ("adaptive_suggest", "adaptive_auto")
SUPPORTED_MODES = ("heat", "cool", "dry")
SUPPORTED_DOMAINS = ("climate", "humidifier", "switch", "input_boolean")

PERFORMANCE_STATUSES = frozenset((
    "disabled", "inactive", "waiting", "collecting", "retained", "limited",
    "candidate", "verifying", "verified", "rollback", "applied",
    "evaluating", "reverted", "ready_for_review", "no_change", "unsupported",
))


def adaptive_snapshot(*, cfg: dict, payload: dict | None) -> dict:
    """Project the runtime's current performance evidence without authorizing it.

    The runtime resolves the same input and actuator used by PID. This layer
    must not fall back to a passive cycle ledger or invent elapsed progress
    when the current observation cannot be verified.
    """
    mode = cfg.get("operating_mode") or cfg.get("requested_mode")
    result = {
        "schema_version": 1, "engine": "performance", "operating_mode": mode,
        "status": "waiting", "reason": "awaiting_observation",
        "context_verified": False,
    }
    if cfg.get("pid_calibration_method") not in ADAPTIVE:
        return {**result, "status": "disabled", "reason": "manual_calibration"}
    if cfg.get("control_mode") != "pid":
        return {**result, "status": "inactive", "reason": "pid_not_active"}
    if not isinstance(payload, dict):
        return result
    if payload.get("operating_mode") != mode:
        return {**result, "reason": "context_changed"}
    state = payload.get("status")
    result["status"] = (state if isinstance(state, str) and state in PERFORMANCE_STATUSES
                        else "waiting")
    reason = payload.get("reason")
    result["reason"] = (reason if isinstance(reason, str) and reason
                        else "awaiting_observation")
    result["context_verified"] = payload.get("context_verified") is True
    # Current inputs remain useful diagnostics even while learning is paused.
    # Copy containers so presentation cannot mutate a live observer snapshot.
    for key in ("algorithm", "metric", "unit", "increasing", "measured", "target", "band",
                "target_semantics", "actuator_kind", "output_kind", "physical_activity",
                "outcome", "last_change", "last_application"):
        if key in payload:
            value = payload[key]
            result[key] = dict(value) if isinstance(value, dict) else value
    for key in ("feedback", "constraints"):
        value = payload.get(key)
        if isinstance(value, dict):
            result[key] = {name: list(item) if isinstance(item, (tuple, list))
                           else item for name, item in value.items()}
        elif isinstance(value, (tuple, list)):
            result[key] = list(value)
    if result["context_verified"]:
        result["fresh_evidence"] = payload.get("fresh_evidence") is True
        if isinstance(payload.get("evidence_id"), str):
            result["evidence_id"] = payload["evidence_id"]
        if _finite(payload.get("evidence_at")):
            result["evidence_at"] = payload["evidence_at"]
        for key in ("samples", "observed_seconds"):
            value = payload.get(key)
            if _finite(value) and value >= 0:
                result[key] = value
        for key in ("performance", "model", "candidate", "verification", "review"):
            value = payload.get(key)
            if isinstance(value, dict):
                result[key] = dict(value)
    elif result["status"] in ("candidate", "ready_for_review", "verifying",
                               "verified", "retained", "rollback", "evaluating"):
        result.update(status="waiting", reason="context_changed")
    return result


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
             active: bool, ready: bool, now: float,
             live_context: str | None = None, state_lookup=None) -> dict:
    """Describe this active mode without leaking another mode's evidence."""
    method = cfg.get("pid_calibration_method", "manual")
    mode = cfg.get("operating_mode") or cfg.get("requested_mode")
    saved = record.get("pid_passive")
    saved = saved if isinstance(saved, dict) else {}
    context_verified = isinstance(live_context, str) and context_mode(live_context) == mode
    context_matches = (context_verified and saved.get("context") == live_context)
    summary = saved.get("summary") if context_matches else {}
    summary = summary if isinstance(summary, dict) else {}
    progress = (progress if context_verified and observer_context == live_context
                and isinstance(progress, dict) else {})
    # Completed cycles are persisted before presentation. Maintenance can
    # prune those records while a paused observer still has an older count.
    count = summary.get("valid_cycles", 0)
    result = {
        "status": "collecting", "reason": "waiting_for_complete_cycles",
        "eligible": False, "operating_mode": mode,
        "context_verified": context_verified,
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
    if blocked := calibration_hold(record, cfg, state_lookup):
        return finish("waiting", blocked)
    state = str(observed.get("status", ""))
    if (state.startswith(("window_", "sleep_room_", "waiting_for_"))
            or state in ("paused", "control_measurement_missing_or_stale",
                         "awaiting_physical_acknowledgement")):
        return finish("waiting", "controller_paused", detail=observed.get("reason") or state)
    if (isinstance(hold, dict) and hold.get("operating_mode") == mode
            and hold.get("reason")):
        return finish("waiting", hold["reason"])

    raw_review = record.get("pid_passive_review")
    review_mode = (raw_review.get("operating_mode") or context_mode(raw_review.get("context"))
                   if isinstance(raw_review, dict) else None)
    review = (review_projection(raw_review, cfg, now, context=live_context, saved=saved)
              if review_mode == mode else {"state": "none"})
    if method == "adaptive_suggest":
        # The configuration write may have committed before the review's
        # bookkeeping was saved. Exact history + effective gains outrank a
        # leftover pending flag, and cannot offer the same change twice.
        if review_application_matches(raw_review, cfg) and review_mode == mode:
            return finish("applied", "applied")
        if review.get("state") in ("expired", "discarded"):
            return finish("collecting", review.get("reason") or "recommendation_stale")

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
        cycles = saved.get("cycles", []) if context_matches else []
        if _finite(old_cycle) and isinstance(cycles, list) and sum(
            isinstance(c, dict) and _finite(c.get("at")) and c["at"] > old_cycle
            for c in cycles
        ) < 2:
            return finish("collecting", "new_cycles_required")

    if method == "adaptive_suggest" and review.get("state") == "pending":
        if not is_pending(review):
            return finish("collecting", "recommendation_stale")
        if live_context is None:
            return finish("waiting", "unsafe_or_invalid_observation")
        if (review.get("context") != live_context
                or summary.get("confidence") not in ("medium", "high")
                or review.get("confidence") not in ("medium", "high")):
            return finish("collecting", "recommendation_stale")
        if native_state != "off" or record.get("power"):
            return finish("waiting_for_safe_off", "waiting_for_safe_off")
        return finish("ready_for_review", "recommendation_pending")

    # A still-valid user proposal survives an ordinary pause/restart. Fresh
    # complete evidence is required to calculate a new proposal or auto tune.
    if progress.get("fresh_cycle_required") is True and result["valid_cycles"] > 0:
        return finish("collecting", "new_cycle_required")

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
    return result
