"""Pure, versioned authority for normal-operation PID recommendations.

The observer supplies evidence, never write authority. These helpers bind an
immutable proposal to the exact gains, operating mode, controller timing and
evidence used to validate it. The runtime separately rechecks current input,
actuator acknowledgement, ownership and interruption generation under its lock.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re
import secrets
from typing import Any

ALGORITHM = "performance_v1"
VERSION = 1
REVIEW_MAX_AGE_S = 48 * 3600
GAINS = ("kp", "ki", "kd")
METHODS = ("performance_adaptive", "performance_approved", "performance_rollback")


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _gains(value: Any) -> dict | None:
    if not isinstance(value, dict) or any(
        not _finite(value.get(key)) or value[key] < 0 for key in GAINS
    ):
        return None
    return {key: value[key] for key in GAINS}


def _signature(cfg: dict) -> dict:
    # Import lazily: pid_review delegates the versioned lifecycle back here.
    from .pid_review import tuning_signature
    return tuning_signature(cfg)


def _mode(cfg: dict, context: str | None) -> str | None:
    if cfg.get("operating_mode"):
        return cfg["operating_mode"]
    # The live observation binds an inferred direction to its native mode,
    # physical device, sources and target. An explicit request must still match.
    try:
        observed = json.loads(context) if context else None
    except (TypeError, ValueError):
        observed = None
    if isinstance(observed, dict) and observed.get("operating_mode"):
        if cfg.get("requested_mode") not in (None, observed.get("mode")):
            return None
        return observed["operating_mode"]
    return cfg.get("requested_mode")


def _evidence_age(cfg: dict) -> float:
    sample = cfg.get("sample_seconds")
    sample = sample if _finite(sample) and sample > 0 else 300
    return max(1800, min(10800, 3 * sample))


def _bounded(current: dict, applied: dict) -> bool:
    """Each new trial is at most ten percent; zero gains remain disabled."""
    return any(current[key] != applied[key] for key in GAINS) and all(
        abs(applied[key] - current[key]) <= abs(current[key]) * .100000001
        for key in GAINS
    )


def saved_snapshot(saved: Any) -> dict:
    """Read either the runtime namespace or its versioned observer ledger."""
    if not isinstance(saved, dict):
        return {}
    ledger = saved.get("ledger", saved)
    if (not isinstance(ledger, dict) or ledger.get("version") != VERSION
            or ledger.get("algorithm") != ALGORITHM):
        return {}
    assessment = ledger.get("assessment")
    if not isinstance(assessment, dict):
        return {}
    return {**assessment, "context": ledger.get("context")}


def _candidate(snapshot: dict, *, rollback: bool = False) -> dict | None:
    if not isinstance(snapshot, dict):
        return None
    if rollback:
        result = snapshot.get("verification")
        if not isinstance(result, dict) or result.get("state") != "rollback_recommended":
            return None
        applied = _gains(result.get("revert_gains"))
    else:
        result = snapshot.get("candidate")
        if (not isinstance(result, dict) or result.get("validated") is not True
                or type(result.get("validated_windows")) is not int
                or result["validated_windows"] < 1
                or not _finite(result.get("predicted_improvement"))
                or result["predicted_improvement"] <= 0):
            return None
        applied = _gains(result)
    previous = _gains(result.get("previous_gains"))
    evidence = result.get("evidence_id")
    if (previous is None or applied is None
            or not isinstance(evidence, str)
            or re.fullmatch(r"[a-f0-9]{32,64}", evidence) is None
            or not _finite(result.get("evidence_at"))):
        return None
    if not rollback and (
        not _bounded(previous, applied) or applied["kd"] != previous["kd"]
    ):
        return None
    if rollback and previous == applied:
        return None
    return {**result, "current": previous, "apply": applied}


def make_proof(cfg: dict, snapshot: dict, context: str, now: float, *,
               approved_id: str | None = None, rollback: bool = False) -> dict | None:
    """Make a write request only from a fresh, successfully validated decision."""
    candidate = _candidate(snapshot, rollback=rollback)
    method = cfg.get("pid_calibration_method")
    verification = snapshot.get("verification") if isinstance(snapshot, dict) else None
    if (candidate is None or snapshot.get("algorithm") != ALGORITHM
            or snapshot.get("fresh_evidence") is not True
            or not isinstance(context, str) or not context
            or snapshot.get("context") != context
            or not _finite(now)
            or not 0 <= now - candidate["evidence_at"] <= _evidence_age(cfg)
            or candidate["current"] != _gains(cfg)
            or method not in ("adaptive_auto", "adaptive_suggest")
            or not _mode(cfg, context)):
        return None
    if (not rollback and isinstance(verification, dict)
            and verification.get("state") in ("evaluating", "rollback_recommended")):
        return None
    if not rollback and (method == "adaptive_suggest") != (approved_id is not None):
        return None
    if approved_id is not None and (
        not isinstance(approved_id, str)
        or re.fullmatch(r"[a-f0-9]{32}", approved_id) is None
    ):
        return None
    baseline = candidate.get("baseline", snapshot.get("performance", {}))
    proof = {
        "algorithm": ALGORITHM,
        "context": context,
        "evidence_id": candidate["evidence_id"],
        "evidence_at": candidate["evidence_at"],
        "created_at": now,
        "current": candidate["current"],
        "apply": candidate["apply"],
        "operating_mode": _mode(cfg, context),
        "settings_scope": cfg.get("operating_mode"),  # Recheck flat/scoped settings under the write lock.
        "tuning_settings": _signature(cfg),
        "approved_id": approved_id,
        "rollback": rollback,
        "baseline": deepcopy(baseline) if isinstance(baseline, dict) else {},
        "model": deepcopy(candidate.get("model", snapshot.get("model", {}))),
        "confidence": candidate.get("confidence", "validated"),
        "validated_windows": candidate.get("validated_windows", 1),
        "predicted_improvement": candidate.get("predicted_improvement"),
        "reason": candidate.get("reason", snapshot.get("reason")),
    }
    if rollback:
        # The exact original gains are authorized only by the matching trial,
        # never by arbitrary values inserted into a verification dictionary.
        verification = snapshot.get("verification", {})
        receipt = verification.get("application")
        if not isinstance(receipt, dict):
            receipt = snapshot.get("last_application")
        if (not isinstance(receipt, dict)
                or receipt.get("method") not in METHODS[:2]
                or receipt.get("context") != context
                or receipt.get("applied_gains") != candidate["current"]
                or receipt.get("previous_gains") != candidate["apply"]
                or cfg.get("pid_last_calibration") != receipt):
            return None
        proof["trial_evidence_id"] = receipt.get("evidence_id")
    return proof


def validate_proof(proof: Any, cfg: dict, snapshot: dict, context: str, now: float) -> bool:
    """Reconstruct evidence-bound fields; runtime continuity fields may follow."""
    if (not isinstance(proof, dict) or proof.get("algorithm") != ALGORITHM
            or type(proof.get("rollback")) is not bool
            or not _finite(proof.get("created_at")) or not _finite(now)
            or not 0 <= now - proof["created_at"] <= _evidence_age(cfg)):
        return False
    expected = make_proof(
        cfg, snapshot, context, now,
        approved_id=proof.get("approved_id"), rollback=proof["rollback"],
    )
    if expected is None:
        return False
    # created_at is the request timestamp, not the later lock recheck time.
    return all(proof.get(key) == value for key, value in expected.items()
               if key != "created_at")


def calibration_receipt(proof: dict, now: float) -> dict:
    """Persist beside the gains so interrupted bookkeeping is recoverable."""
    method = ("performance_rollback" if proof.get("rollback") else
              "performance_approved" if proof.get("approved_id") else
              "performance_adaptive")
    receipt = {
        "method": method,
        "algorithm": ALGORITHM,
        "at": now,
        "context": proof["context"],
        "evidence_id": proof["evidence_id"],
        "evidence_at": proof["evidence_at"],
        "previous_gains": deepcopy(proof["current"]),
        "applied_gains": deepcopy(proof["apply"]),
        "operating_mode": proof["operating_mode"],
        "tuning_settings": deepcopy(proof["tuning_settings"]),
        "baseline": deepcopy(proof.get("baseline", {})),
        "model": deepcopy(proof.get("model", {})),
        "confidence": proof.get("confidence", "validated"),
        "predicted_improvement": proof.get("predicted_improvement"),
        "rate_limit": "verified_10_percent_trial" if not proof.get("rollback") else "restore_previous_gains",
    }
    if proof.get("approved_id"):
        receipt["proposal_id"] = proof["approved_id"]
    if proof.get("trial_evidence_id"):
        receipt["trial_evidence_id"] = proof["trial_evidence_id"]
    return receipt


def proposal_for(cfg: dict, snapshot: dict, context: str, now: float) -> dict | None:
    """Freeze an already simulated candidate for the existing approval UI."""
    token = secrets.token_hex(16)
    proof = make_proof(cfg, snapshot, context, now, approved_id=token)
    if proof is None or cfg.get("pid_calibration_method") != "adaptive_suggest":
        return None
    return {
        "id": token, "state": "pending", "algorithm": ALGORITHM,
        "context": context, "evidence_id": proof["evidence_id"],
        "evidence_at": proof["evidence_at"], "created_at": now,
        "current": proof["current"], "apply": proof["apply"],
        "recommended": deepcopy(proof["apply"]),
        "confidence": proof["confidence"],
        "validated_windows": proof["validated_windows"],
        "predicted_improvement": proof["predicted_improvement"],
        "metric": snapshot.get("metric"),
        "baseline": proof["baseline"],
        "tuning_settings": proof["tuning_settings"],
        "operating_mode": proof["operating_mode"],
    }


def application_matches(review: Any, cfg: dict) -> bool:
    """Exact committed receipt wins over a stale pending bookkeeping record."""
    if not isinstance(review, dict) or review.get("algorithm") != ALGORITHM:
        return False
    receipt = cfg.get("pid_last_calibration")
    current, applied = _gains(review.get("current")), _gains(review.get("apply"))
    return bool(
        isinstance(receipt, dict) and current is not None and applied is not None
        and isinstance(review.get("id"), str)
        and receipt.get("method") == "performance_approved"
        and receipt.get("algorithm") == ALGORITHM
        and receipt.get("proposal_id") == review["id"]
        and receipt.get("context") == review.get("context")
        and receipt.get("evidence_id") == review.get("evidence_id")
        and receipt.get("evidence_at") == review.get("evidence_at")
        and _finite(receipt.get("at")) and _finite(receipt.get("evidence_at"))
        and receipt["at"] >= receipt["evidence_at"]
        and receipt.get("previous_gains") == current
        and receipt.get("applied_gains") == applied
        and receipt.get("operating_mode") == review.get("operating_mode")
        and receipt.get("tuning_settings") == review.get("tuning_settings")
        and _gains(cfg) == applied
    )


def review_projection(review: Any, cfg: dict, now: float, *,
                      context: str | None = None, saved: dict | None = None) -> dict:
    """Read-only pending/applied/expired lifecycle for versioned evidence."""
    if not isinstance(review, dict) or review.get("algorithm") != ALGORITHM:
        return {"state": "none"}
    result = deepcopy(review)
    if application_matches(review, cfg):
        result.update(state="applied", reason="applied")
        return result
    if result.get("state") == "discarded":
        result["reason"] = "recommendation_discarded"
        return result
    if result.get("state") != "pending":
        return result
    created = result.get("created_at")
    reason = None
    if not _finite(created) or not _finite(now) or not 0 <= now - created <= REVIEW_MAX_AGE_S:
        reason = "recommendation_expired"
    elif result.get("tuning_settings") != _signature(cfg):
        reason = "tuning_settings_changed"
    elif (cfg.get("pid_calibration_method") != "adaptive_suggest"
          or _gains(cfg) != _gains(result.get("current"))
          or _mode(cfg, context or result.get("context")) != result.get("operating_mode")):
        reason = "recommendation_stale"
    elif context is not None and context != result.get("context"):
        reason = "recommendation_stale"
    elif saved is not None:
        snapshot = saved_snapshot(saved)
        candidate = _candidate(snapshot)
        if (snapshot.get("context") != result.get("context") or candidate is None
                or candidate["evidence_id"] != result.get("evidence_id")
                or candidate["evidence_at"] != result.get("evidence_at")
                or candidate["current"] != result.get("current")
                or candidate["apply"] != result.get("apply")):
            reason = "recommendation_stale"
    if _finite(created):
        result["expires_at"] = created + REVIEW_MAX_AGE_S
    if reason:
        result.update(state="expired", reason=reason)
    return result
