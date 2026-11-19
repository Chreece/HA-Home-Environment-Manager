"""Bounded completed passive PID evidence for independent operating contexts.

Pure record transforms only: no Home Assistant imports, IO, partial waveform,
review authorization or gain application. ``pid_passive`` remains the active
compatibility projection. ``pid_passive_contexts`` maps exact context strings
to compact cycles plus the metadata needed to recompute that projection.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from typing import Any

from .pid_passive import METRICS, PassiveObserver

MAX_CONTEXTS = 12
MAX_CONTEXT_CHARS = 16384
BANK = "pid_passive_contexts"
ACTIVE = "pid_passive"


def _finite(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _context(context: Any) -> tuple[str, str] | None:
    if not isinstance(context, str) or len(context) > MAX_CONTEXT_CHARS:
        return None
    try:
        parts = json.loads(context)
    except (TypeError, ValueError, RecursionError):
        return None
    if (not isinstance(parts, list) or len(parts) < 5
            or parts[3] not in ("heat", "cool", "dry")
            or not isinstance(parts[4], str) or parts[4] not in METRICS):
        return None
    return parts[3], parts[4]


def _sample(value: Any) -> float | None:
    return float(value) if _finite(value) and 120 <= value <= 3600 else None


def _entry(context: str, raw: Any, now: float) -> dict | None:
    identity = _context(context)
    if identity is None or not isinstance(raw, dict):
        return None
    observer = PassiveObserver({"context": context, "cycles": raw.get("cycles")}, now=now)
    last_used = raw.get("last_used_at")
    if not _finite(last_used) or not 0 <= last_used <= now:
        last_used = observer.cycles[-1]["at"] if observer.cycles else now
    return {
        "cycles": observer.ledger()["cycles"],
        "metric": identity[1],
        "sample_seconds": _sample(raw.get("sample_seconds")),
        "last_used_at": last_used,
    }


def _read(record: dict, now: float) -> tuple[dict, str | None]:
    bank = {}
    saved_bank = record.get(BANK)
    if isinstance(saved_bank, dict):
        for context, raw in saved_bank.items():
            entry = _entry(context, raw, now)
            if entry is not None:
                bank[context] = entry
    active = record.get(ACTIVE)
    context = active.get("context") if isinstance(active, dict) else None
    if _context(context) is None:
        return bank, None
    # Archive/migrate the active compatibility ledger. Existing bank metadata
    # supplies its sampling interval; legacy v0.7.4b1 did not persist one.
    metadata = bank.get(context, {})
    entry = _entry(context, {
        **metadata, "cycles": active.get("cycles"),
        "sample_seconds": metadata.get("sample_seconds", active.get("sample_seconds")),
    }, now)
    bank[context] = entry
    return bank, context


def _projection(context: str, entry: dict, now: float) -> dict:
    observer = PassiveObserver({"context": context, "cycles": entry["cycles"]}, now=now)
    sample = entry["sample_seconds"]
    summary = observer.summary(metric=entry["metric"], sample_seconds=sample or 120)
    if sample is None:
        # Retain identifiable old evidence, but do not guess an interval or
        # trust a persisted recommendation. activate() supplies the real
        # current interval before a restored context becomes actionable.
        summary.pop("suggested_gains", None)
        summary["status"] = "collecting"
        summary["confidence"] = "insufficient"
    return {"context": context, "cycles": deepcopy(entry["cycles"]), "summary": summary}


def _write(record: dict, bank: dict, context: str | None, now: float) -> bool:
    # Empty inactive contexts carry no completed knowledge. Keep the active
    # empty entry only so a subsequent remember() has its sampling metadata.
    bank = {key: entry for key, entry in bank.items()
            if entry["cycles"] or key == context}
    ranked = sorted(bank, key=lambda key: (
        key == context, bank[key]["last_used_at"],
        bank[key]["cycles"][-1]["at"] if bank[key]["cycles"] else -1, key,
    ), reverse=True)
    bank = {key: bank[key] for key in ranked[:MAX_CONTEXTS]}
    active = _projection(context, bank[context], now) if context in bank else None
    changed = False
    for key, value in ((BANK, bank or None), (ACTIVE, active)):
        if value is None:
            if key in record:
                record.pop(key)
                changed = True
        elif record.get(key) != value:
            record[key] = value
            changed = True
    return changed


def activate(record: dict, context: str, now: float,
             metric: str, sample_seconds: float) -> bool:
    """Archive the previous context and restore exact matching valid cycles.

    Repeated unchanged activation is idempotent: ``last_used_at`` is updated
    on a context switch, never on every controller tick. All summaries are
    derived from surviving cycles, never trusted from persisted input.
    """
    identity = _context(context)
    sample = _sample(sample_seconds)
    if (not _finite(now) or now < 0 or identity is None
            or metric != identity[1] or sample is None):
        return False
    bank, previous = _read(record, now)
    entry = bank.get(context)
    if entry is None:
        entry = {"cycles": [], "metric": metric, "sample_seconds": sample,
                 "last_used_at": now}
    else:
        entry["sample_seconds"] = sample
        if previous != context:
            entry["last_used_at"] = now
    bank[context] = entry
    return _write(record, bank, context, now)


def remember(record: dict, ledger: dict, now: float) -> bool:
    """Save one completed ledger for its exact context and refresh the alias.

    The runtime activates the context first, providing metric/sample metadata.
    A legacy direct caller can still preserve cycles; a recommendation is
    withheld until a later activation supplies a verified sampling interval.
    """
    if not _finite(now) or now < 0 or not isinstance(ledger, dict):
        return False
    context = ledger.get("context")
    if _context(context) is None:
        return False
    bank, previous = _read(record, now)
    old = bank.get(context)
    entry = _entry(context, {**(old or {}), "cycles": ledger.get("cycles")}, now)
    if old is None or old["cycles"] != entry["cycles"] or previous != context:
        entry["last_used_at"] = now
    bank[context] = entry
    return _write(record, bank, context, now)


def prune(record: dict, now: float) -> bool:
    """Expire old/future/malformed cycles and recompute the active summary."""
    if not _finite(now) or now < 0:
        return False
    bank, context = _read(record, now)
    return _write(record, bank, context, now)


def invalidate(record: dict, mode: str | None = None) -> bool:
    """Forget completed evidence for an explicitly edited mode, or all modes.

    Reviews and current gains belong to the runtime; this helper changes only
    the completed evidence bank and compatibility projection. Call this for a
    manual gain/reset action, not for an interruption or Suggest/Auto toggle.
    """
    changed = False
    if mode is None:
        for key in (ACTIVE, BANK):
            if key in record:
                record.pop(key)
                changed = True
        return changed
    active = record.get(ACTIVE)
    identity = _context(active.get("context")) if isinstance(active, dict) else None
    if identity is not None and identity[0] == mode:
        record.pop(ACTIVE)
        changed = True
    saved = record.get(BANK)
    if isinstance(saved, dict):
        kept = {key: entry for key, entry in saved.items()
                if (identity := _context(key)) is not None and identity[0] != mode}
        if kept != saved:
            if kept:
                record[BANK] = kept
            else:
                record.pop(BANK)
            changed = True
    return changed
