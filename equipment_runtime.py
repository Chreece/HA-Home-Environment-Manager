"""One serialized, durable command owner per managed physical device.

All new control is opt-in through the controller-mode selector. Existing room
owners are never silently replaced. Power commands require the original
commissioning grant, native capabilities, dwell and live room evidence. PID
uses slow time proportioning for binary outputs, percentages for modulating
outputs, or bounded native setpoint trim when only setpoint control is granted.
"""
from __future__ import annotations

import asyncio
from .config_data import mutable_copy as deepcopy
from dataclasses import asdict
import logging
import time
from typing import Any, Callable

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, SIGNAL_UPDATED, CONF_EXCLUDED_INDOOR
from .device_hierarchy import configured_sources
from .discovery import entity_area, reading, temperature_sensor_c
from .climate_arbitration import _contact_interlock, _physical_climate_conflict
from .climate_entry_ownership import foreign_owner_hold
from .occupancy_policy import live_device_permission, room_presence, sleep_presence
from .pid_math import finite, target_from_unit, target_to_unit, quantize_target
from .pid_output_allocator import fan_speed_for_pid, ordered_fan_stages, percentage_output_requested
from .pid_fan_capacity import (
    allocate as allocate_fan_capacity,
    build_model as build_fan_capacity_model,
    model_is_valid as fan_capacity_model_is_valid,
)
from .pid_calibration import tune as tune_pid
from .pid_passive import (
    PassiveObserver, identity as passive_identity,
    bounded_gains as passive_bounded_gains, AUTO_INTERVAL_S,
)
from . import equipment_model as model

_LOGGER = logging.getLogger(__name__)
ACK_SECONDS = 120
STARTUP_SECONDS = 300
# Readiness is distinct from the existing five-minute physical ON gate:
# do not inspect restored outputs for manual overrides until HA is fully
# running and this controller's native sources have stabilized.
HA_READY_COOLDOWN_SECONDS = 60
NATIVE_STARTUP_STABLE_SECONDS = 60
# Initial command + three fresh, independently authorized retries.
NATIVE_COMMAND_MAX_ATTEMPTS = 4
NATIVE_COMMAND_RETRY_SECONDS = 30
# Home Assistant may report a successful native OFF late. Give a still-
# unreported power-OFF transition one bounded feedback grace before replaying
# the identical durable command. Other commands keep the 30-second retry.
NATIVE_OFF_FEEDBACK_GRACE_SECONDS = 60
# A restored native entity may load cached/default HVAC values, reconnect
# accessory channels, or run firmware automations before its state settles.
NATIVE_RECONNECT_SETTLE_SECONDS = 30
# Up to two extra attempts, ONLY across independently observed reconnects.
# A service that keeps failing while continuously online must not spam output.
NATIVE_RECONNECT_EXTRA_ATTEMPTS = 2


def native_retry_decision(pending: dict, now: float, state=None) -> str:
    """Never mistake a service call for a physical acknowledgement."""
    attempts = pending.get("attempts")
    first = finite(pending.get("when"), 0, now)
    last = finite(pending.get("last_attempt_at"), 0, now)
    if pending.get("phase") != "commanded":
        verified = pending.get("retry_state_verified_at")
        if (pending.get("phase") != "retry_intent"
                or type(verified) not in (int, float) or last is None
                or finite(verified, last, now) is None):
            return "uncertain"
    extension = pending.get("reconnect_retry_grant") is True
    used = pending.get("reconnect_retry_uses", 0)
    if (type(attempts) is not int
            or not 1 <= attempts <= NATIVE_COMMAND_MAX_ATTEMPTS + NATIVE_RECONNECT_EXTRA_ATTEMPTS
            or type(used) is not int or not 0 <= used <= NATIVE_RECONNECT_EXTRA_ATTEMPTS
            or first is None or last is None or last < first):
        return "uncertain"
    if now - last < NATIVE_COMMAND_RETRY_SECONDS:
        return "waiting"
    # The native integration can accept OFF while its HA state still reads
    # HEAT/COOL for a short while. Avoid unnecessary duplicate OFF calls when
    # there has been NO fresh native report since this attempt. An actual
    # post-command report still showing ON permits the normal bounded retry.
    if (pending.get("power") is True
            and isinstance(pending.get("expected"), dict)
            and pending["expected"].get("state") == "off"
            # Safety-critical shutdowns/window/sleep/idle stops must retain
            # their original fast retry. Grace applies only to ordinary
            # duty-cycle OFF where waiting for HA's native report is safe.
            and not (isinstance(pending.get("retry_context"), dict)
                     and (pending["retry_context"].get("policy_stop") is not None
                          or pending["retry_context"].get("shutdown") is True))
            and now - last < NATIVE_OFF_FEEDBACK_GRACE_SECONDS):
        reported = False
        for key in ("last_reported", "last_updated", "last_changed"):
            value = getattr(state, key, None)
            try:
                stamp = value.timestamp() if value is not None else None
            except (AttributeError, TypeError, ValueError, OverflowError):
                stamp = None
            if stamp is not None and last < stamp <= now:
                reported = True
                break
        if not reported:
            return "waiting"
    return ("exhausted" if attempts >= NATIVE_COMMAND_MAX_ATTEMPTS
            and not extension else "retry")
# Changes in passive device metadata are not evidence of a manual override.
# Only physical mode/power and user-adjustable targets, speed and swing qualify.
SETTABLE_OUTPUT_ATTRIBUTES = frozenset((
    "temperature", "target_temp_low", "target_temp_high", "humidity",
    "fan_mode", "percentage", "preset_mode", "swing_mode", "swing_horizontal_mode",
))
MONITORED = ("temperature", "target_temp_low", "target_temp_high", "humidity",
             "fan_mode", "percentage", "preset_mode", "swing_mode", "swing_horizontal_mode",
             "supported_features", "temperature_unit", "target_temp_step", "min_temp", "max_temp",
             "hvac_modes", "fan_modes", "swing_modes", "swing_horizontal_modes", "preset_modes",
             "min_humidity", "max_humidity", "percentage_step", "min", "max", "step", "unit_of_measurement")
LEGACY_DRIVERS = ("pid", "native_climate", "direct_climate", "native_humidity",
                  "humidity_power", "secondary_climate", "running_fans", "fan_power", "native_air_mode")


def output_off(state: Any) -> bool:
    if state is None:
        return False
    if getattr(state, "domain", "") in ("number", "input_number"):
        return finite(state.state, 0, 100) == 0
    return state.state == "off"


def snapshot(state: Any) -> dict | None:
    if state is None or state.state in ("unknown", "unavailable"):
        return None
    return {"state": state.state, "attributes": {
        k: state.attributes[k] for k in MONITORED if k in state.attributes}}


def _manual_output_changes(previous: dict, observed: dict) -> tuple[str, ...]:
    """Ignore passive capability metadata, but never hide a changed physical command.

    Missing optional attributes do not constitute an observed override. Malformed
    stored baselines still require reconciliation rather than assuming permission.
    """
    if not isinstance(previous, dict) or not isinstance(observed, dict):
        return ("invalid_baseline",)
    if previous.get("state") != observed.get("state"):
        return ("state",)
    old, new = previous.get("attributes"), observed.get("attributes")
    if not isinstance(old, dict) or not isinstance(new, dict):
        return ("invalid_baseline",)
    return tuple(sorted(
        key for key in SETTABLE_OUTPUT_ATTRIBUTES
        if key in old and key in new and old[key] != new[key]
    ))


def matches(state: Any, expected: dict) -> bool:
    if state is None:
        return False
    if "state" in expected and state.state != expected["state"]:
        if getattr(state, "domain", "") not in ("number", "input_number") or (
            finite(state.state, 0, 100) is None or finite(expected["state"], 0, 100) is None
            or abs(float(state.state)-float(expected["state"])) > .05
        ):
            return False
    for key, value in expected.get("attributes", {}).items():
        actual = state.attributes.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if finite(actual, -1e8, 1e8) is None or abs(float(actual)-value) > (.5 if key == "percentage" else .05):
                return False
        elif actual != value:
            return False
    return True


class EquipmentRuntime:
    """Independent tasks for independent devices; one pending command each."""

    def __init__(self, manager: Any, *, clock: Callable[[], float] | None = None) -> None:
        self.manager, self.hass = manager, manager.hass
        self.clock = clock or time.time
        self.records: dict[str, dict] = {}
        self.statuses: dict[str, dict] = {}
        self._presentation_context: dict[str, tuple] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._memory: dict[str, tuple[Any, model.PIDMemory, float]] = {}
        # A short, bounded request to re-evaluate comfort immediately after
        # a verified profile/target rise. Never owns physical power by itself.
        self._profile_wake: dict[str, dict] = {}
        # Session-local observations distinguish a real ON transition
        # recorded by HEM from an HA-restored native State at startup.
        self._native_session_observations: dict[tuple[str, str], str] = {}
        self._native_on_epoch: dict[str, float] = {}
        # The first verified source snapshot after HA restart is a recovery
        # baseline, not evidence that the user touched the physical device.
        self._restart_baseline_pending: set[str] = set()
        self._ha_running_since: float | None = None
        self._startup_source_observed: dict[tuple[str, str], dict] = {}
        self._startup_source_since: dict[tuple[str, str], float] = {}
        self._startup_source_done: set[tuple[str, str]] = set()
        self._automatic_recovery_tasks: dict[str, asyncio.Task] = {}
        # Source entities can disappear and return while HEM's dedicated
        # upstream supply remains ON. This is recovery, not user interaction.
        self._native_offline_under_owned_supply: set[str] = set()
        self._native_ready_since: dict[str, float] = {}
        self._native_reconnect_epoch: dict[str, float] = {}
        self._native_settled_for: dict[tuple[str, str], float] = {}
        self._fan_allocations: dict[str, dict] = {}
        # Diagnostic-only snapshots while an independently powered device is
        # OFF: PID P-term prepared, I held at zero, D reseeded from live sensor.
        self._pid_offline_previews: dict[str, dict] = {}
        # Partial natural response waveforms stay in memory, never persisted
        # into HA Recorder or its entity attributes. Only a handful of
        # completed, verified cycle statistics are saved on completion.
        self._pid_passive_observers: dict[str, PassiveObserver] = {}
        self._pid_passive_tasks: dict[str, asyncio.Task] = {}
        self._store = None
        self._ready = False
        self._active = False
        self._started = self.clock()
        self._save_lock = asyncio.Lock()
        self._commands = asyncio.Semaphore(8)
        self._invalidated: set[str] = set()
        from .equipment_updates import EquipmentUpdates
        self._presentation_updates = EquipmentUpdates(self)

    def _status(self, spec: Any, status: str, **data: Any) -> None:
        key = spec if isinstance(spec, str) else spec.identifier
        value = {"status": status, **data}
        from .equipment_pid_safety import status_details
        value.update(status_details(self.records.get(key, {})))
        if key in self._fan_allocations:
            value["pid_fan_capacity"] = self._fan_allocations[key]
        if key in self._pid_offline_previews:
            value["pid_prepared_while_unpowered"] = self._pid_offline_previews[key]
        if self.statuses.get(key) == value:
            return
        self.statuses[key] = value
        if self._active:
            # A status change belongs to this controller, not every room and
            # configuration entity in the installation. Keep runtime evidence
            # immediate; batch only its outward presentation until next turn.
            self._presentation_updates.request(key)

    def _resume_pid_checkpoint(
        self, spec: model.ManagedDevice, record: dict, cfg: dict,
        value: float, goal: float, increasing: bool,
    ) -> tuple | None:
        """Restore bounded PID I/PWM phase, not any physical actuator state."""
        from .pid_restart import restore
        raw = record.get("pid_checkpoint")
        if not isinstance(raw, dict):
            return None
        restored = restore(
            raw, sources=tuple(spec.source_entities),
            source_device_id=spec.source_device_id, now=self.clock(),
            sample=cfg["sample_seconds"], measured=value, goal=goal,
            increasing=increasing, kp=cfg["kp"],
        )
        if restored is None:
            # A bad or stale checkpoint must not be reused after another
            # restart. It is superseded by the next fresh PID sample.
            record["pid_restart_status"] = "safe_reseed"
            return None
        signature, values, anchor = restored
        record["pid_restart_status"] = "integral_and_phase_restored"
        # Reset derivative on restart, and never integrate the offline gap.
        return signature, model.PIDMemory(**values), anchor

    async def _checkpoint_pid(
        self, spec: model.ManagedDevice, record: dict, cfg: dict,
        signature: tuple, memory: model.PIDMemory, anchor: float,
    ) -> None:
        """Persist no more than once per PID sample or changed logical phase."""
        from .pid_restart import checkpoint
        current = checkpoint(
            signature, memory, anchor, tuple(spec.source_entities),
            spec.source_device_id, cfg["sample_seconds"], self.clock(),
        )
        if current is None:
            return
        saved = record.get("pid_checkpoint")
        if (isinstance(saved, dict)
                and saved.get("signature") == current["signature"]
                and saved.get("stamp") == current["stamp"]
                and saved.get("anchor") == current["anchor"]):
            return
        record["pid_checkpoint"] = current
        await self._save()

    async def _save(self) -> None:
        if self._store is None or not self._ready:
            raise HomeAssistantError("Controller storage is unavailable")
        async with self._save_lock:
            try:
                await self._store.async_save({"version": 1, "records": deepcopy(self.records)})
            except Exception as error:
                self._ready = False
                raise HomeAssistantError("Controller state could not be persisted; no command sent") from error

    async def async_start(self) -> None:
        self._active = True
        self._started = self.clock()
        self._ha_running_since = None
        getattr(self, "_startup_source_observed", {}).clear()
        getattr(self, "_startup_source_since", {}).clear()
        getattr(self, "_startup_source_done", set()).clear()
        self._native_session_observations = {}
        self._native_on_epoch = {}
        getattr(self, "_restart_baseline_pending", set()).clear()
        getattr(self, "_native_offline_under_owned_supply", set()).clear()
        getattr(self, "_native_ready_since", {}).clear()
        getattr(self, "_native_reconnect_epoch", {}).clear()
        getattr(self, "_native_settled_for", {}).clear()
        try:
            from homeassistant.helpers.storage import Store
            self._store = Store(
                self.hass, 1, f"{DOMAIN}.equipment_{self.manager.entry.entry_id}"
            )
            saved = await self._store.async_load()
            if saved is not None and (not isinstance(saved, dict) or saved.get("version") != 1
                                      or not isinstance(saved.get("records"), dict)):
                raise ValueError("Unknown equipment state schema")
            self.records = deepcopy(saved["records"]) if saved else {}
            for key, record in self.records.items():
                if (not isinstance(key, str) or not isinstance(record, dict)
                    or not isinstance(record.get("area"), str)
                    or not isinstance(record.get("sources"), list)
                    or not all(isinstance(e, str) for e in record["sources"])
                    or not isinstance(record.get("baseline"), dict)
                    or not isinstance(record.get("power"), dict)
                    or not isinstance(record.get("off_at"), dict)):
                    raise ValueError("Invalid equipment recovery records")
                # An ACKed relay can remain ON across HA restarts, but we
                # cannot prove native continuity while HEM was offline.
                # Clear any pre-restart OFF-credit; ordinary persisted relay
                # minimums still survive. This prevents bypassing a genuine
                # intervening native ON->OFF during HA downtime.
                upstream = record.get("upstream", {})
                if isinstance(upstream, dict):
                    upstream.pop("native_wake", None)
                for entity, owned in record["power"].items():
                    if (entity not in record["sources"] or not isinstance(owned, dict)
                        or any(finite(owned.get(k), 0, 1e13) is None for k in ("since", "min_on", "max_on"))
                        or owned["max_on"] <= owned["min_on"]):
                        raise ValueError("Invalid power recovery history")
            self._ready = True
            # Discard stale pre-restart physical attribute baselines only
            # after fresh native source verification and absent pending
            # commands. Never erase an explicit physical manual override.
            self._restart_baseline_pending = {
                key for key, record in self.records.items()
                if not record.get("pending")
                and record.get("paused") != "physical_manual_override"
            }
            for key, record in self.records.items():
                # HA setup may interrupt an intent before the device command
                # executes. Preserve the original journal, but do NOT create
                # an endless user-facing pause. A previously authorized PID/
                # Automatic choice is itself consent for SAFE, read-only
                # reconciliation once HA/native startup has fully settled.
                # Never auto-rearm genuinely user-initiated Manual or Off.
                record.pop("pending_resume_probe", None)
                upstream = record.get("upstream", {})
                pending = bool(
                    record.get("pending") or
                    isinstance(upstream, dict) and upstream.get("pending")
                )
                profiles = self.manager.settings.get(model.SETTINGS, {})
                user_cfg = profiles.get(key, {}) if isinstance(profiles, dict) else {}
                configured_auto = (
                    isinstance(user_cfg, dict)
                    and user_cfg.get("control_mode") in ("automatic", "pid")
                )
                if pending:
                    if record.get("paused") != "physical_manual_override":
                        record["paused"] = "restart_reconciliation_required"
                        record.pop("restart_power_verification", None)
                        if configured_auto:
                            record["automatic_continue_requested"] = {
                                "at": self.clock(),
                                "method": user_cfg["control_mode"],
                                "awaiting_physical_verification": True,
                                "origin": "automatic_restart_reconciliation",
                            }
                elif (record.get("power")
                        and not record.get("restart_recovery_blocked")
                        and record.get("paused") in (
                            None, "restart_reconciliation_required")):
                    record["restart_power_verification"] = True
                    record.pop("paused", None)
            await self._save()
        except Exception:
            self._ready = False
            _LOGGER.exception("Equipment controller storage unavailable; new control stays inactive")

    async def async_stop(self) -> None:
        self._active = False
        from .equipment_setpoint_sequence import cancel_wakeups
        cancel_wakeups(self)
        self._presentation_updates.close()
        tasks = tuple((*self._tasks.values(), *getattr(
            self, "_automatic_recovery_tasks", {}
        ).values()))
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        getattr(self, "_presentation_context", {}).clear()
        getattr(self, "_automatic_recovery_tasks", {}).clear()
        self._profile_wake.clear()
        self._native_session_observations.clear()
        getattr(self, "_native_on_epoch", {}).clear()
        self._ha_running_since = None
        getattr(self, "_startup_source_observed", {}).clear()
        getattr(self, "_startup_source_since", {}).clear()
        getattr(self, "_startup_source_done", set()).clear()
        getattr(self, "_restart_baseline_pending", set()).clear()
        getattr(self, "_native_offline_under_owned_supply", set()).clear()
        getattr(self, "_native_ready_since", {}).clear()
        getattr(self, "_native_reconnect_epoch", {}).clear()
        getattr(self, "_native_settled_for", {}).clear()
        self._pid_offline_previews.clear()
        tasks = tuple(self._pid_passive_tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._pid_passive_tasks.clear()
        self._pid_passive_observers.clear()
        if self._ready:
            await self._save()

    def _record(self, spec: model.ManagedDevice) -> dict:
        return self.records.setdefault(spec.identifier, {"area": spec.area_id,
            "sources": list(spec.source_entities), "source_device_id": spec.source_device_id,
            "baseline": {}, "power": {}, "off_at": {}})

    def _observed_off_since(self, entity: str, now: float | None = None) -> float:
        """Best known physical OFF timestamp, not the selector-click time."""
        now = self.clock() if now is None else now
        state = self.hass.states.get(entity)
        changed = getattr(state, "last_changed", None) if state is not None else None
        try:
            stamp = changed.timestamp() if changed is not None else None
        except (AttributeError, TypeError, ValueError, OverflowError):
            stamp = None
        stamp = finite(stamp, 0, 1e13)
        return stamp if stamp is not None and stamp <= now else now

    async def _observe_native_running(
        self, spec: model.ManagedDevice, cap: model.Capabilities, state: Any,
    ) -> None:
        """Persist transition-based ON evidence without per-tick Store writes.

        HA 'last_changed' at startup often means *restored entity*, not
        physical power ON. A prior durable ON observation is retained across
        HA restarts; only an ACTUALLY OBSERVED OFF->ON transition in our own
        polling history starts a fresh physical dwell.
        """
        record = self._record(spec)
        snapshots = record.setdefault("native_power_observations", {})
        if not isinstance(snapshots, dict):
            raise HomeAssistantError("Invalid persisted physical observation history")
        current = "off" if output_off(state) else "on"
        wake = record.get("upstream", {}).get("native_wake")
        if isinstance(wake, dict) and wake.get("reconciled"):
            if current == "on":
                # Once this appliance has appeared ON, its prior supply-OFF
                # credit is permanently consumed for this power cycle.
                record["upstream"].pop("native_wake", None)
            elif wake.get("native_state") == "off":
                try:
                    stamp = finite(state.last_changed.timestamp(), 0, self.clock())
                except (AttributeError, TypeError, ValueError, OverflowError):
                    stamp = None
                if stamp is None or stamp != wake.get("native_off_stamp"):
                    # A later OFF last_changed may hide an ON->OFF transition
                    # between controller ticks. Do not reuse an older dwell.
                    record["upstream"].pop("native_wake", None)
                    await self._save()
        old = snapshots.get(cap.primary)
        observed_in_session = getattr(self, "_native_session_observations", None)
        if observed_in_session is None:
            observed_in_session = self._native_session_observations = {}
        key = (spec.identifier, cap.primary)
        prior_live = observed_in_session.get(key)
        observed_in_session[key] = current
        on_epoch = finite(
            getattr(self, "_native_on_epoch", {}).get(cap.primary), 0, self.clock()
        )
        if (isinstance(old, dict) and old.get("state") == current
                and (current != "on" or on_epoch is None
                     or on_epoch <= old.get("since", 0))):
            return
        # No reason to write the entire durable controller Store merely to
        # record the first OFF observation or repeat an ON timestamp already
        # saved under confirmed power ownership. Session evidence above is
        # enough to recognize a later real OFF->ON transition.
        if old is None and current == "off":
            return
        now = self.clock()
        if current == "on":
            owned = record.get("power", {}).get(cap.primary)
            if prior_live == "off":
                # A genuine OFF->ON transition observed in THIS process,
                # not just an OFF snapshot retained from before a restart.
                since = now
            elif isinstance(owned, dict):
                # Previously confirmed owned ON across HA startup: preserve
                # the durable timestamp even if the older observation cache
                # was still OFF when the application stopped.
                since = finite(owned.get("since"), 0, now) or now
            else:
                changed = getattr(state, "last_changed", None)
                try:
                    since = finite(changed.timestamp(), 0, now) if changed else None
                except (AttributeError, TypeError, ValueError, OverflowError):
                    since = None
                since = since if since is not None else now
            if on_epoch is not None:
                since = max(since, on_epoch)
            snapshots[cap.primary] = {"state": "on", "since": since}
            if (old is None and isinstance(owned, dict)
                    and since == owned.get("since")):
                # The already persisted ownership interval IS our durable
                # evidence; no extra full-store write is needed at startup.
                return
            if isinstance(owned, dict) and since > owned.get("since", now):
                # Source OFF->ON transition supersedes any earlier ownership
                # interval without claiming an uninterrupted run.
                owned["since"] = since
        else:
            snapshots[cap.primary] = {"state": "off", "since": now}
        await self._save()

    async def _reconcile_native_after_supply_wake(
        self, spec: model.ManagedDevice, cap: model.Capabilities,
    ) -> bool:
        """Bridge a HEM-ACKed supply ON to its newly reconnected native device.

        This is not general-purpose adoption of manually operated hardware.
        HEM must itself have previously switched ON and ACKed the exact,
        dedicated supply for qualified demand. A verified dedicated supply
        held OFF for the entire native minimum-OFF interval, so a new HA
        State.last_changed at reconnect is NOT a new physical OFF moment.
        No service is sent by this reconciliation.
        """
        record = self._record(spec)
        relay = record.get("upstream", {})
        wake = relay.get("native_wake") if isinstance(relay, dict) else None
        if not isinstance(wake, dict) or wake.get("reconciled"):
            return True
        cfg = model.settings(self.manager, spec)
        supply = cfg.get("power_switch_entity")
        if not supply or not relay.get("owned") or relay.get("pending"):
            self._status(spec, "waiting_for_physical_device",
                         reason="native_supply_wake_not_acknowledged")
            return False
        from .equipment_power_switch import (
            permitted_supply, device_supply_dwell,
        )
        identity = wake.get("identity")
        if (not isinstance(identity, dict)
                or identity != relay.get("identity")
                or permitted_supply(self.manager, spec, supply, identity) is None):
            self._status(spec, "paused",
                         reason="native_supply_wake_identity_changed")
            return False
        switch = self.hass.states.get(supply)
        on_at = finite(wake.get("on_at"), 0, self.clock())
        off_at = finite(wake.get("off_at"), 0, self.clock())
        if (switch is None or switch.state != "on"
                or on_at is None or off_at is None
                or relay.get("on_at") != on_at or not 0 <= off_at <= on_at):
            self._status(spec, "waiting_for_physical_device",
                         reason="native_supply_wake_not_verified")
            return False
        dwell = device_supply_dwell(self, spec, cfg, cap)
        if dwell is None or on_at - off_at < dwell[1]:
            self._status(spec, "minimum_off_hold",
                         reason="native_supply_wake_off_history_insufficient")
            return False
        if (not self._current_spec(spec) or record.get("pending")
                or record.get("power")):
            self._status(spec, "owned_shutdown_identity_or_dwell_hold",
                         reason="native_supply_wake_existing_output_ownership")
            return False
        _, power = model.permission(self.manager, spec, cap)
        if not power or cap.primary not in spec.source_entities:
            self._status(spec, "power_control_not_commissioned",
                         reason="native_supply_wake_requires_exact_authorization")
            return False
        from .device_activation import authorized
        if (cap.domain in ("climate", "fan", "humidifier")
                and not authorized(self.manager, spec)):
            self._status(spec, "power_control_not_commissioned",
                         reason="native_supply_wake_authorization_missing")
            return False
        current = self.hass.states.get(cap.primary)
        if (current is None or current.state in ("unknown", "unavailable")
                or any(snapshot(self.hass.states.get(e)) is None
                       for e in spec.source_entities)
                or any(foreign_owner_hold(
                    self.hass, self.manager.entry.entry_id, e
                ) for e in spec.source_entities)):
            self._status(spec, "waiting_for_physical_device",
                         reason="native_supply_wake_sources_not_verified")
            return False
        # Actual HA physical states vary by domain: climate says "heat",
        # while a heat-assigned native switch/fan/humidifier says "on" and
        # a proportional valve says "35". Capabilities describe the DEVICE
        # ROLE, not the raw ON state for those non-climate domains.
        if cap.domain == "climate":
            valid = current.state in cap.modes
        elif cap.domain in ("switch", "input_boolean", "fan", "humidifier"):
            valid = current.state in ("off", "on")
        elif cap.domain in ("number", "input_number"):
            attrs = current.attributes
            valid = (finite(current.state, 0, 100) is not None
                     and attrs.get("unit_of_measurement") == "%"
                     and attrs.get("min") == 0 and attrs.get("max") == 100)
        else:
            valid = False
        if not valid:
            self._status(spec, "paused",
                         reason="native_supply_wake_unsupported_physical_state")
            return False
        if not output_off(current):
            # Auto-restoration after our own acknowledged ON accepts only the
            # selected heat/cool/dry/fan role, or an unambiguous single-purpose
            # controller. Never infer mode ownership from a generic ON value.
            allowed = set(cap.modes) - {"off"}
            selected = cfg.get("requested_mode")
            if (selected is not None and (
                    selected not in allowed or
                    cap.domain == "climate" and current.state != selected)
                    or selected is None and (
                        (cap.domain == "climate" and allowed != {current.state})
                        or (cap.domain != "climate" and len(allowed) != 1))):
                self._status(spec, "paused",
                             reason="native_supply_wake_mode_unverified")
                return False
            min_on, _, max_on = model.timing(self.manager, spec, cap)
            # Reconnected state.last_changed can mean HA discovery, not
            # actual ON. Using the *later* of relay ON and native discovery
            # is conservative: it will not prematurely shut a compressor.
            try:
                observed_on = finite(
                    current.last_changed.timestamp(), 0, self.clock()
                )
            except (AttributeError, TypeError, ValueError, OverflowError):
                observed_on = None
            start = max(on_at, observed_on or self.clock())
            record["power"][cap.primary] = {
                "since": start, "min_on": min_on, "max_on": max_on,
            }
            wake["native_state"] = "on"
        else:
            # A trustworthy native OFF state stamp lets the running HEM
            # detect a later new OFF event. If HA supplies no timestamp,
            # do not grant an exemption from native physical protection.
            try:
                native_stamp = finite(
                    current.last_changed.timestamp(), 0, self.clock()
                )
            except (AttributeError, TypeError, ValueError, OverflowError):
                native_stamp = None
            if native_stamp is not None:
                record.setdefault("off_at", {})[cap.primary] = off_at
                wake["native_state"] = "off"
                wake["native_off_stamp"] = native_stamp
            else:
                record.setdefault("off_at", {})[cap.primary] = self.clock()
                wake["native_state"] = "off_no_credit"
        record["baseline"] = {
            entity: snapshot(self.hass.states.get(entity))
            for entity in spec.source_entities
        }
        wake["reconciled"] = True
        await self._save()
        return True

    async def _verify_restart_power(self, spec: model.ManagedDevice) -> bool:
        """Resume only a persisted, acknowledged, unchanged physical output.

        No HA service is called. Missing/unknown native sources are waited
        for; a changed source, foreign owner or ambiguous pending command
        remains paused rather than auto-adopted. Last_changed is NOT treated
        as a new ON timestamp merely because HA restored its State object.
        """
        record = self._record(spec)
        if not record.get("restart_power_verification"):
            return True
        if not self._current_spec(spec):
            self._status(spec, "source_deselected_or_moved")
            return False
        if record.get("pending"):
            # Latch the failure DURABLY before saving the pause. Do not
            # auto-clear it during the next HA restart.
            record.pop("restart_power_verification", None)
            record["restart_recovery_blocked"] = True
            await self._pause(spec, "restart_reconciliation_required")
            return False
        cfg = model.settings(self.manager, spec)
        cap = model.capabilities(self.manager, spec)
        if cap is None or not model.sources_available(self.manager, spec):
            self._status(spec, "waiting_for_physical_device")
            return False
        if cfg.get("control_mode") not in ("automatic", "pid", "manual", "off"):
            # Latch the failure DURABLY before saving the pause. Do not
            # auto-clear it during the next HA restart.
            record.pop("restart_power_verification", None)
            record["restart_recovery_blocked"] = True
            await self._pause(spec, "restart_reconciliation_required")
            return False
        _, authorized_power = model.permission(self.manager, spec, cap)
        if not authorized_power or not self._identity_ok(spec):
            # Latch the failure DURABLY before saving the pause. Do not
            # auto-clear it during the next HA restart.
            record.pop("restart_power_verification", None)
            record["restart_recovery_blocked"] = True
            await self._pause(spec, "restart_reconciliation_required")
            return False
        upstream = record.get("upstream", {})
        if isinstance(upstream, dict) and upstream.get("pending"):
            # Latch the failure DURABLY before saving the pause. Do not
            # auto-clear it during the next HA restart.
            record.pop("restart_power_verification", None)
            record["restart_recovery_blocked"] = True
            await self._pause(spec, "restart_reconciliation_required")
            return False
        supply = cfg.get("power_switch_entity")
        if supply and isinstance(upstream, dict) and upstream.get("owned"):
            from .equipment_power_switch import permitted_supply
            physical_relay = self.hass.states.get(supply)
            if physical_relay is None or physical_relay.state not in ("on", "off"):
                self._status(spec, "waiting_for_physical_device")
                return False
            if (physical_relay.state != "on"
                    or permitted_supply(
                        self.manager, spec, supply, upstream.get("identity")
                    ) is None):
                record.pop("restart_power_verification", None)
                record["restart_recovery_blocked"] = True
                await self._pause(spec, "restart_reconciliation_required")
                return False
        previous = record.get("baseline", {})
        revised = {}
        verified_off = []
        now = self.clock()
        if not record.get("power"):
            record.pop("restart_power_verification", None)
            return True
        for entity, owned in record["power"].items():
            if entity not in spec.source_entities or cap.primary != entity:
                record.pop("restart_power_verification", None)
                record["restart_recovery_blocked"] = True
                await self._pause(spec, "restart_reconciliation_required")
                return False
            actual_state = self.hass.states.get(entity)
            current = snapshot(actual_state)
            if current is None:
                self._status(spec, "waiting_for_physical_device")
                return False
            if (foreign_owner_hold(
                    self.hass, self.manager.entry.entry_id, entity
                ) is not None or finite(owned.get("since"), 0, now) is None):
                record.pop("restart_power_verification", None)
                record["restart_recovery_blocked"] = True
                await self._pause(spec, "restart_reconciliation_required")
                return False
            if output_off(actual_state):
                # A previously owned appliance genuinely reported OFF after
                # HA's stable-source cooldown. That ends the historical ON
                # interval; it is not a manual intervention. The OFF time is
                # deliberately conservative: a fresh minimum-OFF starts NOW,
                # not the potentially misleading HA restoration timestamp.
                verified_off.append(entity)
                revised[entity] = current
                continue
            if (not isinstance(previous.get(entity), dict)
                    or previous[entity].get("state") != current["state"]
                    or _manual_output_changes(previous[entity], current)):
                # Different restored ON modes do not establish the previous
                # native command's ownership. Never adopt them here.
                record.pop("restart_power_verification", None)
                record["restart_recovery_blocked"] = True
                await self._pause(spec, "restart_reconciliation_required")
                return False
            revised[entity] = current
        for entity in verified_off:
            record["power"].pop(entity, None)
            record.setdefault("off_at", {})[entity] = now
        record["baseline"].update(revised)
        record.pop("restart_power_verification", None)
        record.pop("restart_recovery_blocked", None)
        await self._save()
        self._status(
            spec, "awaiting_evaluation",
            reason="native_off_confirmed_after_restart"
                   if verified_off else "verified_owned_native_power_after_restart",
            verified_native_off=list(verified_off),
        )
        return True

    def _lock(self, key: str) -> asyncio.Lock:
        record = self.records.get(key)
        if record:
            group = (record["area"], record.get("source_device_id") or key)
        else:
            spec = next((s for s in model.specs(self.manager) if s.identifier == key), None)
            group = (spec.area_id, spec.source_device_id or key) if spec else key
        return self._locks.setdefault(group, asyncio.Lock())

    async def _pause(self, spec: Any, reason: str) -> None:
        record = self._record(spec)
        record["paused"] = reason
        # Only an observed change to the REAL native device (not the HEM
        # climate facade, the PID, a metadata refresh or HA restart) demotes
        # Automatic/PID to Manual. Preserve the algorithm for Continue.
        if reason == "physical_manual_override":
            # A genuine user intervention ends this PID continuity. Keep
            # physical ON/OFF ownership timestamps and safety dwell intact.
            getattr(self, "_memory", {}).pop(spec.identifier, None)
            record.pop("pid_checkpoint", None)
            cfg = model.settings(self.manager, spec)
            previous = cfg.get("control_mode")
            if previous in ("automatic", "pid") and self._current_spec(spec):
                record["resume_control_mode"] = previous
                await self._save()
                lock = getattr(self.manager, "_device_settings_write_lock", None)
                if lock is None:
                    lock = self.manager._device_settings_write_lock = asyncio.Lock()
                async with lock:
                    fresh = model.settings(self.manager, spec)
                    if (fresh.get("control_mode") == previous
                            and self._current_spec(spec)):
                        options = deepcopy(self.manager.entry.options)
                        profiles = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
                        profiles = profiles if isinstance(profiles, dict) else {}
                        saved = profiles.get(spec.identifier, {})
                        profiles[spec.identifier] = {
                            **(saved if isinstance(saved, dict) else {}),
                            "control_mode": "manual",
                        }
                        options[model.SETTINGS] = profiles
                        self.hass.config_entries.async_update_entry(
                            self.manager.entry, options=options
                        )
        self._status(spec, "paused", reason=reason)
        await self._save()

    def _identity_ok(self, spec: model.ManagedDevice) -> bool:
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self.hass)
        for entity in spec.source_entities:
            item = registry.async_get(entity)
            if item is None or getattr(item, "platform", None) == DOMAIN:
                return False
            if getattr(item, "device_id", None) != spec.source_device_id:
                return False
        return bool(spec.source_entities)

    def _current_spec(self, spec: model.ManagedDevice) -> bool:
        active = set(configured_sources(self.manager.settings, spec.area_id))
        return self._identity_ok(spec) and all(
            e in active and entity_area(self.hass, e) == spec.area_id
            for e in spec.source_entities)

    def _legacy_busy(self, spec: model.ManagedDevice) -> str | None:
        for key, record in self.records.items():
            if key != spec.identifier and set(record.get("sources", ())).intersection(spec.source_entities):
                if record.get("power") or record.get("pending"):
                    return "Prior device controller must reconcile this source OFF before transfer"
        for name in LEGACY_DRIVERS:
            driver = getattr(self.manager, name, None)
            task = getattr(driver, "_tasks", {}).get(spec.area_id)
            if task is not None and not task.done():
                return "Existing room controller has a write in progress"
            paused = getattr(driver, "paused", {})
            if isinstance(paused, dict) and spec.area_id in paused:
                return "Existing controller is paused; reconcile it before transferring ownership"
            for attr in ("owned", "_owned"):
                owned = getattr(driver, attr, {})
                if isinstance(owned, dict) and any(e in owned for e in spec.source_entities):
                    return "Existing power owner must reconcile this device OFF before transfer"
        return None

    def _pid_passive_auto_authorized(
        self, spec: model.ManagedDevice, changes: dict, proof: tuple,
    ) -> bool:
        """Fail closed under the per-controller update lock, with no IO."""
        try:
            context, cycle_at, previous = proof
            cfg = model.settings(self.manager, spec)
            record = self.records.get(spec.identifier, {})
            saved = record.get("pid_passive", {})
            summary = saved.get("summary", {})
            cap = model.capabilities(self.manager, spec)
            native = self.hass.states.get(cap.primary) if cap is not None else None
            if (not self._active or not self._ready
                    or not self._current_spec(spec)
                    or cfg.get("control_mode") != "pid"
                    or cfg.get("pid_adaptation_mode") != "bounded"
                    or cfg.get("pid_calibration_method", "adaptive_auto") != "adaptive_auto"
                    or cfg.get("requested_mode") not in ("heat", "cool", "dry")
                    or self.clock() - self._started < STARTUP_SECONDS
                    or cap is None or native is None or not output_off(native)
                    or native.attributes.get("hvac_action") not in (None,"off","idle")
                    or record.get("paused") or record.get("pending")
                    or record.get("power") or (record.get("upstream") or {}).get("pending")
                    or saved.get("context") != context
                    or summary.get("confidence") != "high"
                    or summary.get("status") != "validated"
                    or summary.get("last_cycle_at") != cycle_at
                    or not isinstance(saved.get("cycles"), list)
                    or len(saved["cycles"]) < 5
                    or saved["cycles"][-1].get("at") != cycle_at
                    or not isinstance(previous, dict)
                    or any(cfg.get(k) != previous.get(k) for k in ("kp","ki","kd"))
                    or self.clock() - cycle_at > 3600
                    or not all(c["at"] <= self.clock()
                               for c in saved.get("cycles", []))):
                return False
            soft, power = model.permission(self.manager, spec, cap)
            if not (soft and power):
                return False
            # Recheck live room, sleep, source, window and foreign-owner gates;
            # a stale proposal cannot act on a newly changed physical system.
            plan = model.plan_for(self.manager, spec)
            if self._gate(spec, cap, cfg, plan, cfg["requested_mode"]) is not None:
                return False
            last = cfg.get("pid_last_calibration")
            if isinstance(last, dict) and last.get("method") == "passive_imc_lambda":
                stamp = last.get("at")
                old_cycle = last.get("cycle_at")
                if (not isinstance(stamp, (int,float))
                        or self.clock() - stamp < AUTO_INTERVAL_S
                        or not isinstance(old_cycle, (int,float))
                        or sum(c["at"] > old_cycle for c in saved["cycles"]) < 2):
                    return False
            expected = passive_bounded_gains(cfg, summary["suggested_gains"])
            if (expected is None
                    or any(changes.get(k) != expected.get(k)
                           for k in ("kp", "ki", "kd"))
                    or set(changes) != {"kp", "ki", "kd", "pid_last_calibration"}):
                return False
            evidence = changes["pid_last_calibration"]
            return (isinstance(evidence, dict)
                    and evidence.get("method") == "passive_imc_lambda"
                    and evidence.get("cycle_at") == cycle_at)
        except (AttributeError, KeyError, ValueError, TypeError):
            return False

    def _pid_review_authorized(
        self, spec: model.ManagedDevice, changes: dict, token: str,
    ) -> bool:
        """Approve only the exact still-current model, gains and native OFF.

        Called TWICE under async_update's per-controller lock, before and
        after storage yields. No physical service is issued by this path.
        """
        from .equipment_power_switch import observed_output_off
        from .pid_review import is_pending
        try:
            cfg = model.settings(self.manager, spec)
            record = self.records.get(spec.identifier, {})
            review = record.get("pid_passive_review")
            saved = record.get("pid_passive", {})
            summary = saved.get("summary", {})
            cap = model.capabilities(self.manager, spec)
            now = self.clock()
            if (not self._active or not self._ready
                    or not self._current_spec(spec)
                    or cfg.get("control_mode") != "pid"
                    or cfg.get("pid_calibration_method") != "adaptive_suggest"
                    or cfg.get("requested_mode") not in ("heat","cool","dry")
                    or now-self._started < STARTUP_SECONDS
                    or not is_pending(review) or review["id"] != token
                    or not isinstance(saved, dict)
                    or saved.get("context") != review["context"]
                    or summary.get("last_cycle_at") != review["cycle_at"]
                    or summary.get("status") not in ("suggestion_only","validated")
                    or summary.get("confidence") not in ("medium","high")
                    or not isinstance(review.get("created_at"), (int,float))
                    or not 0 <= now-review["created_at"] <= 48*3600
                    or cap is None or not observed_output_off(
                        self.hass.states.get(cap.primary)
                    )
                    or record.get("paused") or record.get("pending")
                    or record.get("power")
                    or (record.get("upstream") or {}).get("pending")
                    or any(cfg.get(k) != review["current"].get(k)
                           for k in ("kp","ki","kd"))
                    or set(changes) != {"kp","ki","kd","pid_last_calibration"}
                    or any(changes.get(k) != review["apply"].get(k)
                           for k in ("kp","ki","kd"))):
                return False
            for source in spec.source_entities:
                state = self.hass.states.get(source)
                if not observed_output_off(state):
                    return False
            # Rebuild the exact physical learning context with CURRENT
            # room sensor membership, target, profile, direction and native
            # fan settings; saved evidence cannot approve a different plant.
            plan = model.plan_for(self.manager, spec)
            targets = model.targets(self.manager, spec, cap, cfg, plan)
            measured = self.measurements(spec, cap)
            direction = cfg["requested_mode"]
            metric = "humidity" if direction == "dry" else "temperature"
            goal = targets.get("humidity" if metric == "humidity" else direction)
            source_ids = measured.get(metric + "_selected_entities")
            if source_ids is not None:
                feedback = (source_ids[0] if isinstance(source_ids, list)
                            and len(source_ids) == 1 else None)
            else:
                feedback = measured.get(metric + "_entity")
            if (not isinstance(feedback, str)
                    or not feedback.startswith("sensor.")
                    or finite(goal, -40 if metric == "temperature" else 0,
                                    80 if metric == "temperature" else 100) is None
                    or finite(measured.get(metric), -40 if metric == "temperature" else 0,
                                                80 if metric == "temperature" else 100) is None):
                return False
            live_context = passive_identity(
                spec.area_id, list(spec.source_entities), cap.primary,
                direction, metric, feedback, model.profile_name(cfg, plan),
                round(float(goal), 2),
                self.hass.states.get(cap.primary).attributes.get("fan_mode"),
                self.hass.states.get(cap.primary).attributes.get("percentage"),
            )
            if live_context != review["context"]:
                return False
            soft,power = model.permission(self.manager,spec,cap)
            if not (soft and power):
                return False
            if self._gate(
                spec,cap,cfg,plan,direction,
            ) is not None:
                return False
            evidence = changes.get("pid_last_calibration")
            return (
                isinstance(evidence,dict)
                and evidence.get("method") == "passive_approved_imc_lambda"
                and evidence.get("proposal_id") == token
                and evidence.get("cycle_at") == review["cycle_at"]
                and evidence.get("previous_gains") == review["current"]
            )
        except (AttributeError, KeyError, ValueError, TypeError):
            return False

    async def async_review_pid(
        self, spec: model.ManagedDevice, decision: str, token: str | None = None,
    ) -> bool:
        """Approve or discard one pending suggestion. Stale tokens do nothing."""
        from .pid_review import is_pending, async_clear_review
        if decision not in ("approve","discard"):
            return False
        record = self._record(spec)
        review = record.get("pid_passive_review")
        if not is_pending(review) or (
            token is not None and review["id"] != token
        ):
            return False
        token = review["id"]
        if decision == "discard":
            async with self._lock(spec.identifier):
                latest = record.get("pid_passive_review")
                if (not self._active or not self._ready
                        or not self._current_spec(spec)
                        or not is_pending(latest) or latest["id"] != token):
                    return False
                latest["state"] = "discarded"
                await self._save()
            await async_clear_review(self.hass,self.manager,spec)
            self._presentation_updates.request(spec.identifier)
            return True

        changes = {
            **review["apply"],
            "pid_last_calibration": {
                "method": "passive_approved_imc_lambda",
                "proposal_id": token,
                "cycle_at": review["cycle_at"],
                "at": self.clock(),
                "confidence": review["confidence"],
                "model_target": review["recommended"],
                "previous_gains": dict(review["current"]),
                "rate_limit": "approved_10_percent_step",
            },
        }
        try:
            await self.async_update(spec,changes,passive_review=token)
        except (HomeAssistantError,ValueError,TypeError):
            # Keep it pending for a later user retry after safe physical OFF.
            _LOGGER.debug("HEM PID review approval held for %s",spec.identifier)
            return False
        async with self._lock(spec.identifier):
            latest = record.get("pid_passive_review")
            if is_pending(latest) and latest["id"] == token:
                latest["state"] = "applied"
                await self._save()
        await async_clear_review(self.hass,self.manager,spec)
        self._presentation_updates.request(spec.identifier)
        return True

    async def async_update(
        self, spec: model.ManagedDevice, changes: dict, *,
        passive_auto: tuple | None = None,
        passive_review: str | None = None,
    ) -> None:
        """Validate all requested edits atomically; no hidden hardware permission."""
        if "fan_min_percentage" in changes or "fan_max_percentage" in changes:
            # Fan bounds are independent configuration, never a fan command
            # or permission to acknowledge/adopt an outstanding output.
            if set(changes) - set(model.FAN_LIMIT_FIELDS):
                raise HomeAssistantError("Change fan speed limits separately from other controls")
            lock = getattr(self.manager, "_device_settings_write_lock", None)
            if lock is None:
                lock = self.manager._device_settings_write_lock = asyncio.Lock()
            async with lock:
                if not self._ready or not self._current_spec(spec):
                    raise HomeAssistantError("Controller storage or source identity is unavailable")
                cap = model.fan_limit_capability(self.manager, spec)
                if cap is None and model.sources_available(self.manager, spec):
                    raise HomeAssistantError("This device does not support fan percentage control")
                profiles = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
                profiles = profiles if isinstance(profiles, dict) else {}
                previous = profiles.get(spec.identifier)
                previous = previous if isinstance(previous, dict) else {}
                if cap is None and not isinstance(previous.get("fan_speed_limits"), dict):
                    from .equipment_feature_registration import registered_control
                    from homeassistant.helpers import entity_registry as er
                    registry = er.async_get(self.hass)
                    if not any(registered_control(registry, "number", spec, key)
                               for key in model.FAN_LIMIT_FIELDS):
                        raise HomeAssistantError("This controller has no previously verified percentage fan")
                low, high, _, _ = model.fan_limit_edit_bounds(self.manager, spec)
                proposed = model.device_fan_limits(self.manager, spec, cap)
                for key, raw_value in changes.items():
                    value = None if isinstance(raw_value, bool) else finite(raw_value, low, high)
                    if value is None:
                        raise HomeAssistantError("Fan speed limit is outside this device's supported range")
                    proposed[key] = value
                minimum, maximum = (proposed[key] for key in model.FAN_LIMIT_FIELDS)
                if minimum > maximum:
                    raise HomeAssistantError("Maximum fan speed must not be below minimum")
                if cap is not None and not any(
                    finite(value, minimum, maximum) is not None for value in cap.fan_modes
                ):
                    raise HomeAssistantError("Fan speed range must include a supported native speed")
                options = deepcopy(self.manager.entry.options)
                profiles[spec.identifier] = {**previous, "fan_speed_limits": proposed}
                options[model.SETTINGS] = profiles
                self.hass.config_entries.async_update_entry(self.manager.entry, options=options)
            self._presentation_updates.request(spec.identifier)
            if getattr(self.manager, "_active", False):
                self.manager._recalculate(initial=True)
            return
        if ("timed_setpoint_sequence" in changes
                or "sleep_when_everyone_asleep" in changes):
            # These are independent device preferences. A pending service,
            # ACK or recovery hold must not block editing or be acknowledged
            # by the edit. Serialize only the options write, not hardware.
            key = "sleep_when_everyone_asleep" if "sleep_when_everyone_asleep" in changes else "timed_setpoint_sequence"
            if set(changes) != {key} or type(changes[key]) is not bool:
                raise HomeAssistantError("Change this device preference separately using ON or OFF")
            lock = getattr(self.manager, "_device_settings_write_lock", None)
            if lock is None:
                lock = self.manager._device_settings_write_lock = asyncio.Lock()
            async with lock:
                if not self._ready or not self._current_spec(spec):
                    raise HomeAssistantError("Controller storage or source identity is unavailable")
                options = deepcopy(self.manager.entry.options)
                profiles = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
                profiles = profiles if isinstance(profiles, dict) else {}
                previous = profiles.get(spec.identifier)
                profiles[spec.identifier] = {
                    **(previous if isinstance(previous, dict) else {}),
                    key: changes[key],
                }
                options[model.SETTINGS] = profiles
                self.hass.config_entries.async_update_entry(self.manager.entry, options=options)
            self._presentation_updates.request(spec.identifier)
            if key == "sleep_when_everyone_asleep":
                if getattr(self.manager, "_active", False):
                    self.manager._recalculate(initial=True)
                return
            if self._active:
                # Refresh just this device. An in-flight tick may abort an
                # unsent preparation when it sees the saved preference.
                # Let its lock unwind before evaluating the new policy.
                task = self._tasks.get(spec.identifier)
                if task is not None and not task.done():
                    rerun = getattr(self, "_setpoint_rerun", None)
                    if rerun is None:
                        rerun = self._setpoint_rerun = set()
                    rerun.add(spec.identifier)
                elif self.statuses.get(spec.identifier, {}).get("status") == "native_setpoint_startup_grace":
                    self._tasks[spec.identifier] = self.hass.async_create_task(self._run(spec))
            return
        async with self._lock(spec.identifier):
            if not self._ready:
                raise HomeAssistantError("Controller state storage is unavailable")
            if not self._current_spec(spec):
                raise HomeAssistantError("Controller sources are no longer assigned to this area")
            if (passive_auto is not None and
                    not self._pid_passive_auto_authorized(spec, changes, passive_auto)):
                raise HomeAssistantError("Passive PID gain change is no longer safe or validated")
            if (passive_review is not None and
                    not self._pid_review_authorized(spec, changes, passive_review)):
                raise HomeAssistantError("PID review has changed or hardware is not safely OFF")
            changes = deepcopy(changes)
            # A supply reassignment is configuration, never authority to
            # interrupt a running compressor or discard the previous supply's
            # acknowledged ownership. Accept the user's choice now and stage
            # only that field until the old native output/supply is idle.
            deferred_supply = None
            old_supply = model.settings(self.manager, spec).get("power_switch_entity")
            if "power_switch_entity" in changes:
                requested_supply = changes["power_switch_entity"]
                if requested_supply == "none":
                    requested_supply = None
                record = self._record(spec)
                upstream = record.get("upstream", {})
                busy = bool(
                    record.get("pending") or record.get("power")
                    or isinstance(upstream, dict) and (
                        upstream.get("owned") or upstream.get("pending")
                    )
                )
                if requested_supply != old_supply and busy:
                    if requested_supply is not None:
                        from .equipment_power_switch import permitted_supply
                        if permitted_supply(self.manager, spec, requested_supply) is None:
                            raise HomeAssistantError(
                                "Select a dedicated physical power switch in the same room"
                            )
                    deferred_supply = {
                        "requested": requested_supply,
                        "original": old_supply,
                        "source_device_id": spec.source_device_id,
                        "area": spec.area_id,
                        "at": self.clock(),
                    }
                    changes.pop("power_switch_entity")
                    if not changes:
                        record["queued_power_switch"] = deferred_supply
                        await self._save()
                        self._status(
                            spec, "awaiting_evaluation",
                            reason="power_switch_change_saved_for_safe_release",
                            settings_saved=True, queued_power_switch=requested_supply,
                            recovery_detail=(
                                "Power-switch preference saved. HEM will apply "
                                "it after the old physical output and supply "
                                "are safely released."
                            ),
                        )
                        return
                elif requested_supply == old_supply and record.get(
                    "queued_power_switch"
                ):
                    record.pop("queued_power_switch", None)
                    await self._save()
            if set(changes) == {"pause_on_window_open"}:
                value = changes["pause_on_window_open"]
                if type(value) is not bool:
                    raise HomeAssistantError("Window pause must be a boolean")
                lock = getattr(self.manager, "_device_settings_write_lock", None)
                if lock is None:
                    lock = self.manager._device_settings_write_lock = asyncio.Lock()
                async with lock:
                    if not self._current_spec(spec):
                        raise HomeAssistantError("Controller sources changed during configuration")
                    options = deepcopy(self.manager.entry.options)
                    profiles = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
                    profiles = profiles if isinstance(profiles, dict) else {}
                    prior = profiles.get(spec.identifier, {})
                    profiles[spec.identifier] = {
                        **(prior if isinstance(prior, dict) else {}),
                        "pause_on_window_open": value,
                    }
                    options[model.SETTINGS] = profiles
                    self.hass.config_entries.async_update_entry(self.manager.entry, options=options)
                # Do not clear manual override or uncertain hardware latches.
                if deferred_supply is not None:
                    self._record(spec)["queued_power_switch"] = deferred_supply
                    await self._save()
                getattr(self, "_window_policy_cache", {}).pop(spec.identifier, None)
                self._status(spec, "settings_updated", settings_saved=True,
                             queued_power_switch=(
                                 deferred_supply.get("requested")
                                 if isinstance(deferred_supply, dict) else None
                             ))
                if getattr(self.manager, "_active", False):
                    self.manager._recalculate(initial=True)
                return
            cap = model.capabilities(self.manager, spec)
            if cap is None:
                # An intentionally unpowered native appliance has no live
                # capabilities. Its optional supply configuration must remain
                # editable, without granting ANY native HVAC authority.
                if not changes or set(changes) - {
                    "power_switch_entity", "power_switch_cooldown_seconds"
                }:
                    raise HomeAssistantError("Device capabilities are unavailable")
                old = model.settings(self.manager, spec)
                selected = changes.get("power_switch_entity",
                                       old.get("power_switch_entity"))
                if selected == "none":
                    selected = None
                record = self._record(spec)
                upstream = record.get("upstream", {})
                if selected != old.get("power_switch_entity"):
                    if (upstream.get("owned") or upstream.get("pending")
                            or record.get("pending")):
                        raise HomeAssistantError(
                            "Reconcile the previously controlled output before changing its power supply"
                        )
                    if selected is not None:
                        from .equipment_power_switch import permitted_supply
                        if permitted_supply(self.manager, spec, selected) is None:
                            raise HomeAssistantError(
                                "Select a dedicated physical power switch in the same room"
                            )
                    # Binding or unbinding is configuration only. An unowned
                    # switch may be ON, OFF, unavailable or absent from states.
                    # Existing controller-owned/pending power still requires
                    # explicit OFF reconciliation, checked above.
                value = changes.get("power_switch_cooldown_seconds",
                                    old["power_switch_cooldown_seconds"])
                bounds = model.NUMBER_FIELDS["power_switch_cooldown_seconds"]
                value = finite(value, bounds[0], bounds[1])
                if value is None:
                    raise HomeAssistantError("Invalid upstream idle cooldown")
                adjusted = {**old, "power_switch_entity": selected,
                            "power_switch_cooldown_seconds": value}
                lock = getattr(self.manager, "_device_settings_write_lock", None)
                if lock is None:
                    lock = self.manager._device_settings_write_lock = asyncio.Lock()
                async with lock:
                    options = deepcopy(self.manager.entry.options)
                    existing = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
                    existing = existing if isinstance(existing, dict) else {}
                    # Independent switches may have changed while we waited.
                    adjusted["timed_setpoint_sequence"] = model.settings(
                        self.manager, spec
                    ).get("timed_setpoint_sequence") is True
                    adjusted["sleep_when_everyone_asleep"] = model.settings(self.manager, spec).get("sleep_when_everyone_asleep") is True
                    latest_profile = existing.get(spec.identifier)
                    latest_fan_limits = (latest_profile.get("fan_speed_limits")
                                         if isinstance(latest_profile, dict) else None)
                    if isinstance(latest_fan_limits, dict):
                        adjusted["fan_speed_limits"] = deepcopy(latest_fan_limits)
                    else:
                        adjusted.pop("fan_speed_limits", None)
                    existing[spec.identifier] = adjusted
                    options[model.SETTINGS] = existing
                    # Revalidate physical identity, area and competing claims
                    # before saving, but never interpret switch state as consent
                    # to operate an unowned supply.
                    if selected != old.get("power_switch_entity") and selected is not None:
                        from .equipment_power_switch import permitted_supply
                        if (not self._current_spec(spec)
                                or permitted_supply(self.manager, spec, selected) is None):
                            raise HomeAssistantError(
                                "Power supply identity or ownership changed during selection"
                            )
                    self.hass.config_entries.async_update_entry(
                        self.manager.entry, options=options,
                    )
                if deferred_supply is not None:
                    self._record(spec)["queued_power_switch"] = deferred_supply
                    await self._save()
                self._status(spec, "settings_updated",
                             control_mode=adjusted["control_mode"],
                             settings_saved=True)
                # Persisting a safe, offline-only edit must refresh UI/room
                # settings. This is not permission to send physical commands.
                if getattr(self.manager, "_active", False):
                    self.manager._recalculate(initial=True)
                return
            old = model.settings(self.manager, spec)
            changes = deepcopy(changes)
            if "pid_adaptation_mode" in changes:
                # Backwards compatible API callers of the removed Beta82
                # selector still enter the SAME canonical method.
                legacy = changes.pop("pid_adaptation_mode")
                if "pid_calibration_method" in changes:
                    raise HomeAssistantError("Select one PID calibration method only")
                if legacy not in ("disabled","observe","bounded"):
                    raise HomeAssistantError("Unsupported legacy PID adaptation mode")
                changes["pid_calibration_method"] = {
                    "disabled":"manual",
                    "observe":"adaptive_suggest",
                    "bounded":"adaptive_auto",
                }[legacy]
            # Operating ON/OFF preferences belong to the native endpoint.
            # Resolve legacy effective timings before the first explicit edit,
            # retaining the other native minimum and the independent supply
            # protections. Existing pending/owned command journals stay intact.
            timing_base = (
                model.normalize_native_timing(self.manager, spec, cap, old)
                if {"min_on_seconds", "min_off_seconds"} & changes.keys()
                else old
            )
            new = {**timing_base, **changes}
            if "pid_calibration_method" in changes:
                new["pid_adaptation_mode"] = "disabled"
            if ("pause_on_window_open" in new
                    and type(new["pause_on_window_open"]) is not bool):
                raise HomeAssistantError("Window pause must be a boolean")
            allowed = set(model.DEFAULTS) | {"fan_mode", "swing_mode", "swing_horizontal_mode",
                "sensor_verified", *model.DEVICE_SELECTS}
            if set(changes) - allowed:
                raise HomeAssistantError("Unsupported controller setting")
            if new["control_mode"] not in model.control_modes(self.manager, spec):
                raise HomeAssistantError("Unsupported control method")
            if new["pid_calibration_method"] not in model.PID_CALIBRATION_METHODS:
                raise HomeAssistantError("Unsupported deterministic PID tuning method")
            # A valid existing configuration predating Beta82 has no
            # adaptation key. It remains observe-only, including in the
            # legacy controller/physical-power regression harnesses.
            if new.get("pid_adaptation_mode", "observe") not in getattr(
                    model, "PID_ADAPTATION_MODES",
                    ("disabled", "observe", "bounded")):
                raise HomeAssistantError("Unsupported passive PID learning policy")
            # Model fields are inert commissioning inputs. A zero means "not
            # measured yet"; it is never interpreted as a physical response.
            for key, limits in model.PID_MODEL_FIELDS.items():
                value = finite(new[key], 0, limits[1])
                if value is None or (value > 0 and value < limits[0]):
                    raise HomeAssistantError(f"Invalid PID response parameter: {key}")
                new[key] = value
            if new["pid_fan_capacity_mode"] not in model.PID_FAN_CAPACITY_METHODS:
                raise HomeAssistantError("Unsupported PID fan capacity strategy")
            direction = new["pid_fan_capacity_for_mode"]
            if direction not in ("choose", *model.PID_FAN_DIRECTIONS):
                raise HomeAssistantError("Unsupported calibrated HVAC direction")
            if direction != "choose" and direction not in cap.modes:
                raise HomeAssistantError("Fan capacity calibration direction is not a native HVAC mode")
            for key, limits in model.PID_FAN_CAPACITY_FIELDS.items():
                value = finite(new[key], 0, limits[1])
                if value is None:
                    raise HomeAssistantError(f"Invalid measured fan capacity input: {key}")
                new[key] = value
            maps = new.get("pid_fan_capacity_models")
            if not isinstance(maps, dict) or set(maps) - set(model.PID_FAN_DIRECTIONS):
                raise HomeAssistantError("Invalid per-mode PID capacity models")
            # The apply button is the sole writer of calibrated model maps.
            if "pid_fan_capacity_models" in changes and not isinstance(
                changes["pid_fan_capacity_models"], dict
            ):
                raise HomeAssistantError("Invalid calibrated fan model data")
            if (new["pid_fan_capacity_mode"] == "measured"
                    and new["control_mode"] == "pid"
                    and "pid_fan_capacity_mode" in changes):
                # Changing the *calibration edit direction* must not disable an
                # existing measured model for another HVAC mode. Only entering
                # Measured strategy or Apply requires an existing valid model.
                saved = maps.get(direction)
                if (not cap.fan_entity
                        or not fan_capacity_model_is_valid(
                            saved, mode=direction, physical_entity=cap.primary,
                            fan_entity=cap.fan_entity, percentage=cap.fan_percentage,
                            advertised_modes=cap.fan_modes)):
                    raise HomeAssistantError(
                        "Measured PID fan capacity requires a valid saved model for this exact HVAC direction"
                    )
            if new["preset"] not in model.PRESETS:
                raise HomeAssistantError("Unsupported comfort preset")
            if new["requested_mode"] is not None and new["requested_mode"] not in cap.modes:
                raise HomeAssistantError("The physical device does not support this HVAC mode")
            for key, bounds in model.NUMBER_FIELDS.items():
                number = finite(new[key], bounds[0], bounds[1])
                if number is None:
                    raise HomeAssistantError(f"Invalid controller value: {key}")
                new[key] = number
            for key in model.QUIET_FLAGS:
                if type(new[key]) is not bool or new[key] and not cap.fan_modes:
                    raise HomeAssistantError("Quiet control requires an adjustable native fan")
            if (any(new[k] for k in model.QUIET_FLAGS) and not cap.fan_percentage
                    and "low" not in cap.fan_modes and new.get("quiet_fan_mode") is None):
                raise HomeAssistantError("Select an advertised quiet fan mode before enabling quiet control")
            for key, choices in (("fan_mode", cap.fan_modes), ("quiet_fan_mode", cap.fan_modes),
                                 ("swing_mode", cap.swing_modes), ("swing_horizontal_mode", cap.swing_horizontal_modes)):
                if new.get(key) is not None and str(new[key]) not in choices:
                    raise HomeAssistantError(f"Unsupported native choice: {key}")
            table = new.get("profile_targets")
            if not isinstance(table, dict) or set(table) - {"manual"}:
                raise HomeAssistantError("Invalid profile target table")
            for profile, values in table.items():
                if not isinstance(values, dict) or set(values) - {"heat", "cool", "humidity"}:
                    raise HomeAssistantError("Invalid profile targets")
                for key, value in values.items():
                    low, high = (cap.min_humidity, cap.max_humidity) if key == "humidity" else (cap.min_temp, cap.max_temp)
                    if finite(value, low, high) is None:
                        raise HomeAssistantError("Target outside physical device limits")
                profile_config = {**new, "preset": "eco" if profile == "unoccupied" else profile}
                if profile == "manual":
                    profile_config.update(control_mode="manual", preset="none")
                band = model.targets(self.manager, spec, cap, profile_config, {})
                if band["cool"]-band["heat"] < 1:
                    raise HomeAssistantError("Heating and cooling targets must be at least 1°C apart")
            fan_table = new.get("profile_fans")
            if not isinstance(fan_table, dict) or set(fan_table) - {"manual", "home", "comfort", "away", "sleep", "eco"}:
                raise HomeAssistantError("Invalid fan profile table")
            if any(str(v) not in cap.fan_modes for v in fan_table.values()):
                raise HomeAssistantError("Unsupported native fan choice for profile")
            from .device_activation import authority_context
            soft, power = model.permission(self.manager, spec, cap)
            for key, choices in model.DEVICE_SELECTS.items():
                if new.get(key) not in choices:
                    raise HomeAssistantError(f"Unsupported device policy: {key}")
            # The relay is a separate physical device, never an alias for
            # this controller's own output. It grants no independent native
            # power authority and cannot be shared with other controllers.
            from .equipment_power_switch import permitted_supply
            selected_supply = new.get("power_switch_entity")
            if selected_supply == "none":
                selected_supply = None
                new["power_switch_entity"] = None
            if selected_supply is not None and not isinstance(selected_supply, str):
                raise HomeAssistantError("Select a native same-room switch or None")
            if selected_supply:
                identity = permitted_supply(self.manager, spec, selected_supply)
                if identity is None:
                    raise HomeAssistantError(
                        "Power switch must be a dedicated same-room physical switch, "
                        "not a managed output or another controller's power supply"
                    )
            if selected_supply != old.get("power_switch_entity"):
                upstream = self._record(spec).get("upstream", {})
                if (upstream.get("pending") or upstream.get("owned")
                        or self._record(spec).get("pending")):
                    raise HomeAssistantError(
                        "Reconcile previously controlled output before changing its power supply"
                    )
                # Selecting an independent supply does not grant ownership.
                # An unowned ON switch is left ON, an OFF switch left OFF,
                # and an unavailable switch is held by before_tick().
            if "sensor_verified" in changes and type(changes["sensor_verified"]) is not bool:
                raise HomeAssistantError("Sensor verification must be a boolean")
            # The selector itself authorizes only this selected native endpoint.
            # No old room-wide driver or sibling device acquires permission.
            authorizing = ("control_mode" in changes and new["control_mode"] in ("automatic", "pid", "manual")
                           and cap.domain in ("climate", "fan", "humidifier"))
            if authorizing:
                new["_native_authorization"] = authority_context(self.manager, spec)
                soft = True
                power = "off" in cap.modes
            elif "_native_authorization" in new:
                soft = new["_native_authorization"] == authority_context(self.manager, spec)
                power = soft and new.get("control_mode") in ("automatic", "pid", "manual", "off") and "off" in cap.modes
            on, off, maximum = model.timing(self.manager, spec, cap, config=new)
            if cap.domain != "fan" and maximum > 28800:
                raise HomeAssistantError("Maximum continuous runtime for this device cannot exceed 28800 seconds")
            if "requested_mode" in changes and new["requested_mode"] is not None:
                state = self.hass.states.get(cap.primary)
                requested = new["requested_mode"]
                change_power = state is not None and ((cap.domain == "climate" and state.state != requested)
                    or cap.domain != "climate" and output_off(state) != (requested == "off"))
                if change_power and not power and not (requested == "off" and self._record(spec).get("power")):
                    raise HomeAssistantError("This controller is not authorized to change the physical mode")
            # Methods remain selectable with incomplete feedback. Execution,
            # rather than this preference edit, reports the exact missing input.
            if new["control_mode"] == "pid":
                if cap.domain == "climate" and new.get("requested_mode") in ("auto", "heat_cool"):
                    raise HomeAssistantError("PID requires an explicit single thermal, drying or fan direction")
                if not (cap.temperature or cap.humidity or cap.domain == "fan"
                        or set(cap.modes) == {"off", "fan_only"}):
                    raise HomeAssistantError("No qualified feedback loop exists for this device")
                if power:
                    if new["cycle_seconds"] < on+off:
                        raise HomeAssistantError("PID cycle must include the full minimum ON and OFF intervals")
            if old["control_mode"] == "existing" and new["control_mode"] != "existing":
                if why := self._legacy_busy(spec):
                    raise HomeAssistantError(why)
                # Already-running manual equipment is not adopted here. The
                # runtime retains its OFF/reconciliation hold without rejecting
                # the requested method or resetting its ownership protection.
            record = self._record(spec)
            if selected_supply and model.sources_available(self.manager, spec):
                # Preserve only genuinely live, verified native capabilities.
                # An OFF supply may leave stale attributes in unavailable HA
                # states: never promote those into proof for automatic power ON.
                record["capabilities"] = asdict(cap)
                await self._save()
            # Preferences are NOT physical service commands. The previous
            # service may still be awaiting an HA state ACK; never force the
            # user to wait before editing, and never retry it from this editor.
            # Preserve its immutable pending intent, previous physical
            # baselines and dwell history until independently reconciled.
            upstream = record.get("upstream", {})
            hardware_unresolved = bool(
                record.get("pending") or
                isinstance(upstream, dict) and (
                    upstream.get("pending") or upstream.get("paused")
                ) or record.get("paused")
            )
            method_selected = "control_mode" in changes
            if (method_selected and old["control_mode"] in ("automatic", "pid")
                    and new["control_mode"] == "manual"):
                record["resume_control_mode"] = old["control_mode"]
            elif method_selected and new["control_mode"] in ("automatic", "pid"):
                record.pop("resume_control_mode", None)
            if method_selected or old["control_mode"] != new["control_mode"]:
                if (method_selected and not hardware_unresolved
                        and new["control_mode"] in ("automatic", "pid", "manual", "off")):
                    record.pop("paused", None)
                # Unresolved hardware history is NOT erased by a UI action.
                if not hardware_unresolved:
                    record["baseline"] = {
                        e: snapshot(self.hass.states.get(e))
                        for e in spec.source_entities
                    }
                    now = self.clock()
                    record.setdefault("off_at", {}).update({
                        e: self._observed_off_since(e, now)
                        for e in spec.source_entities
                        if output_off(self.hass.states.get(e))
                    })
                    await self._save()
            if new["control_mode"] in ("automatic", "pid") and hardware_unresolved:
                record["automatic_continue_requested"] = {
                    "at": self.clock(), "method": new["control_mode"],
                    "awaiting_physical_verification": True,
                }
                await self._save()
            elif method_selected and new["control_mode"] not in ("automatic", "pid"):
                record.pop("automatic_continue_requested", None)
                await self._save()
            # Use the shared options lock to preserve simultaneous room/mold edits.
            lock = getattr(self.manager, "_device_settings_write_lock", None)
            if lock is None:
                lock = self.manager._device_settings_write_lock = asyncio.Lock()
            async with lock:
                options = deepcopy(self.manager.entry.options)
                saved = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
                saved = saved if isinstance(saved, dict) else {}
                new["timed_setpoint_sequence"] = model.settings(
                    self.manager, spec
                ).get("timed_setpoint_sequence") is True
                new["sleep_when_everyone_asleep"] = model.settings(self.manager, spec).get("sleep_when_everyone_asleep") is True
                latest_profile = saved.get(spec.identifier)
                latest_fan_limits = (latest_profile.get("fan_speed_limits")
                                     if isinstance(latest_profile, dict) else None)
                if isinstance(latest_fan_limits, dict):
                    new["fan_speed_limits"] = deepcopy(latest_fan_limits)
                else:
                    new.pop("fan_speed_limits", None)
                saved[spec.identifier] = new
                options[model.SETTINGS] = saved
                # Storage awaited above: refuse a stale approval if the source
                # selection or identity changed while the preference was saved.
                if authorizing and (not self._current_spec(spec) or
                        new["_native_authorization"] != authority_context(self.manager, spec)):
                    raise HomeAssistantError("Device sources changed; select the control method again")
                if selected_supply != old.get("power_switch_entity") and selected_supply:
                    # Never save a reassigned or already-claimed supply after
                    # awaiting storage. Live ON/OFF/unavailable transitions do
                    # not block configuration, and never confer power ownership.
                    if (not self._current_spec(spec)
                            or permitted_supply(self.manager, spec, selected_supply) is None):
                        raise HomeAssistantError(
                            "Power supply identity or ownership changed during selection"
                        )
                if (passive_auto is not None and
                        not self._pid_passive_auto_authorized(spec, changes, passive_auto)):
                    raise HomeAssistantError("Passive PID context changed before saving new gains")
                if (passive_review is not None and
                        not self._pid_review_authorized(spec, changes, passive_review)):
                    raise HomeAssistantError("PID review changed before saving gains")
                self.hass.config_entries.async_update_entry(self.manager.entry, options=options)
            self._memory.pop(spec.identifier, None)
            self._fan_allocations.pop(spec.identifier, None)
            self._pid_offline_previews.pop(spec.identifier, None)
            if record.pop("pid_checkpoint", None) is not None:
                # An explicit settings/algorithm edit invalidates the
                # previous controller math, never the physical dwell.
                await self._save()
            if passive_auto is None and passive_review is None and (
                    old["control_mode"] != new["control_mode"]
                    or any(k in changes and old.get(k) != new.get(k)
                           for k in ("kp", "ki", "kd", "pid_calibration_method"))):
                # Manual or classical tuning supersedes old passive proposals.
                self._pid_passive_observers.pop(spec.identifier, None)
                record.pop("pid_passive", None)
                if record.pop("pid_passive_review", None) is not None:
                    from .pid_review import async_clear_review
                    self.hass.async_create_task(
                        async_clear_review(self.hass,self.manager,spec)
                    )
                await self._save()
            if deferred_supply is not None:
                record["queued_power_switch"] = deferred_supply
                await self._save()
            self._status(
                spec,
                "awaiting_physical_acknowledgement" if hardware_unresolved
                else "settings_updated",
                control_mode=new["control_mode"],
                settings_saved=True,
                queued_power_switch=(
                    deferred_supply.get("requested")
                    if isinstance(deferred_supply, dict) else None
                ),
                automatic_selected=new["control_mode"] in ("automatic", "pid"),
                recovery_detail=(
                    "Your settings are saved. HEM will verify the previous "
                    "physical command before applying any new output."
                    if hardware_unresolved else None
                ),
            )
        if getattr(self.manager, "_active", False):
            self.manager._recalculate(initial=True)

    async def _pid_passive_observe(
        self, spec: model.ManagedDevice, cfg: dict, cap: model.Capabilities,
        plan: dict, target: dict, measured: dict, record: dict,
        state: Any, mode: str, metric: str, goal: float,
        soft: bool, power: bool,
    ) -> None:
        """Record only naturally occurring, safely verified ON/OFF responses.

        The controller's existing authority, occupancy, sleep, window,
        compressor and power guards have already passed. This observer never
        calls a hardware service, changes the controller's output decision or
        triggers test cycles. A thermostat MODE alone is not evidence of heat
        delivery: its actual hvac_action must confirm the physical activity.
        """
        key = spec.identifier
        if cfg.get("pid_calibration_method", "adaptive_suggest") not in (
            "adaptive_suggest", "adaptive_auto"
        ):
            self._pid_passive_observers.pop(key, None)
            return
        if (cfg.get("control_mode") != "pid"
                or cfg.get("requested_mode") not in ("heat", "cool", "dry")
                or mode != cfg["requested_mode"]
                or metric not in ("temperature", "humidity")
                or cap.domain not in ("climate", "humidifier", "switch", "input_boolean")
                or not (soft and power)):
            observer = self._pid_passive_observers.get(key)
            if observer is not None:
                observer.interrupt()
            return
        # Never mix sensor means whose membership changes when a sensor drops
        # out; use exactly one verified physical feedback entity.
        source_ids = measured.get(metric + "_selected_entities")
        if source_ids is not None:
            feedback = source_ids[0] if isinstance(source_ids, list) and len(source_ids) == 1 else None
        else:
            feedback = measured.get(metric + "_entity")
        if not isinstance(feedback, str) or not feedback.startswith("sensor."):
            observer = self._pid_passive_observers.get(key)
            if observer is not None:
                observer.interrupt()
            return
        valid = (
            not record.get("pending") and not record.get("paused")
            and not (record.get("upstream") or {}).get("pending")
            and cfg.get("requested_mode") == mode
            and self._active and self._ready
        )
        action = state.attributes.get("hvac_action")
        is_on = not output_off(state)
        if cap.domain == "climate" and is_on:
            expected = {"heat": "heating", "cool": "cooling", "dry": "drying"}[mode]
            valid = valid and action == expected
        if cap.domain == "humidifier" and mode != "dry":
            valid = False
        # Source identity, operating direction, target, preset and fan
        # settings are tied to a model. All context changes revoke the
        # old response evidence; no cross-room or cross-mode learning.
        context = passive_identity(
            spec.area_id, list(spec.source_entities), cap.primary,
            mode, metric, feedback, model.profile_name(cfg, plan),
            round(float(goal), 2),
            state.attributes.get("fan_mode"), state.attributes.get("percentage"),
        )
        saved = record.get("pid_passive")
        if isinstance(saved, dict) and saved.get("context") != context:
            record.pop("pid_passive", None)
            self._pid_passive_observers.pop(key, None)
            await self._save()
            saved = None
        observer = self._pid_passive_observers.get(key)
        if observer is None:
            observer = self._pid_passive_observers[key] = PassiveObserver(saved)
        complete = observer.observe(
            context=context, at=self.clock(), value=measured.get(metric),
            on=is_on, owned=bool(record.get("power", {}).get(cap.primary)),
            metric=metric, direction=1 if mode == "heat" else -1,
            sample_seconds=cfg["sample_seconds"], safe=bool(valid),
        )
        if not complete:
            return
        summary = observer.summary(metric=metric, sample_seconds=cfg["sample_seconds"])
        # The persisted record has only six short numerical summaries, not the
        # raw temperature/humidity history. Write at most once per cycle.
        record["pid_passive"] = {**observer.ledger(), "summary": summary}
        await self._save()
        self._presentation_updates.request(key)
        if cfg["pid_calibration_method"] == "adaptive_suggest":
            from .pid_review import proposal_for, async_publish_review, async_clear_review
            latest = record.get("pid_passive_review")
            if (isinstance(latest, dict)
                    and latest.get("cycle_at") != summary.get("last_cycle_at")
                    and summary.get("status") not in ("suggestion_only", "validated")):
                record.pop("pid_passive_review", None)
                await self._save()
                self.hass.async_create_task(
                    async_clear_review(self.hass,self.manager,spec)
                )
                latest = None
            if (not isinstance(latest, dict)
                    or latest.get("cycle_at") != summary.get("last_cycle_at")):
                review = proposal_for(cfg,summary,context,self.clock())
                if review is not None:
                    record["pid_passive_review"] = review
                    await self._save()
                    # Notification delivery is an independent task, never a
                    # prerequisite for native PID control or physical power.
                    self.hass.async_create_task(
                        async_publish_review(
                            self.hass,self.manager,spec,dict(review)
                        )
                    )
                    self._presentation_updates.request(key)
        if (cfg["pid_calibration_method"] == "adaptive_auto"
                and summary.get("confidence") == "high"
                and summary.get("status") == "validated"
                and output_off(state) and not record.get("power")
                and not record.get("pending")
                and key not in self._pid_passive_tasks):
            # A separate task waits for the controller's existing per-device
            # lock. No nested lock/deadlock, no service or forced OFF cycle.
            task = self.hass.async_create_task(
                self._pid_passive_apply(spec, context, summary["last_cycle_at"])
            )
            self._pid_passive_tasks[key] = task
            task.add_done_callback(
                lambda finished, identifier=key:
                    self._pid_passive_tasks.pop(identifier, None)
            )

    async def _pid_passive_apply(
        self, spec: model.ManagedDevice, context: str, cycle_at: float,
    ) -> None:
        """Optionally apply ≤10% PI gain changes after independent validation.

        async_update rechecks the complete authorization and physical OFF
        evidence *inside* the existing controller lock before saving.
        """
        try:
            cfg = model.settings(self.manager, spec)
            record = self.records.get(spec.identifier, {})
            evidence = record.get("pid_passive", {})
            summary = evidence.get("summary", {}) if isinstance(evidence, dict) else {}
            proposal = summary.get("suggested_gains")
            if not isinstance(proposal, dict):
                return
            new = passive_bounded_gains(cfg, proposal)
            if new is None:
                return
            await self.async_update(spec, {
                **new,
                "pid_last_calibration": {
                    "method": "passive_imc_lambda",
                    "source": "natural_owned_cycles",
                    "at": self.clock(),
                    "cycle_at": cycle_at,
                    "cycles": summary["valid_cycles"],
                    "model": summary["identified_model"],
                    "previous_gains": {k: cfg[k] for k in ("kp", "ki", "kd")},
                    "rate_limit": "10_percent_per_24h",
                },
            }, passive_auto=(context, cycle_at, {k: cfg[k] for k in ("kp","ki","kd")}))
        except asyncio.CancelledError:
            raise
        except (HomeAssistantError, ValueError, KeyError, TypeError):
            # An interrupted/changed/offline physical system is NORMAL:
            # preserve the observed proposal without applying any gains.
            _LOGGER.debug("Passive PID gain update safely held for %s", spec.identifier)

    async def async_apply_pid_calibration(self, spec: model.ManagedDevice) -> None:
        """Apply a deterministic measured-model tune, never perform a step test.

        This is an explicit user action on the selected physical controller.
        No physical service is called; refuse recalibration while power is
        being cycled or its acknowledgement is pending. Saved manual gains
        remain untouched on every failed/incomplete model.
        """
        cfg = model.settings(self.manager, spec)
        if cfg["control_mode"] != "pid":
            raise HomeAssistantError("Select PID before applying calibration")
        method = cfg["pid_calibration_method"]
        if method not in ("imc_lambda", "cohen_coon"):
            raise HomeAssistantError(
                "Select IMC/Lambda or Cohen-Coon before using Apply calibration"
            )
        cap = model.capabilities(self.manager, spec)
        if cap is None or not self._current_spec(spec):
            raise HomeAssistantError("Native controller unavailable for calibration")
        record = self._record(spec)
        if record.get("pending") or record.get("power"):
            raise HomeAssistantError("Stop and reconcile physical output before changing PID gains")
        state = self.hass.states.get(cap.primary)
        if state is None or not output_off(state):
            raise HomeAssistantError("Physical device must be OFF when applying new PID gains")
        try:
            result = tune_pid(method, cfg, sample_seconds=cfg["sample_seconds"],
                              constraints=model.NUMBER_FIELDS)
        except ValueError as error:
            raise HomeAssistantError(f"PID calibration requires valid measured model: {error}") from error
        model_evidence = {
            "method": method,
            "process_gain": result.process_gain,
            "time_constant_minutes": result.time_constant_minutes,
            "dead_time_minutes": result.dead_time_minutes,
            "lambda_minutes": result.lambda_minutes,
            "observed_sources": list(spec.source_entities),
        }
        await self.async_update(spec, {
            "kp": result.kp, "ki": result.ki, "kd": result.kd,
            "pid_last_calibration": model_evidence,
        })

    async def async_apply_fan_capacity(self, spec: model.ManagedDevice) -> None:
        """Apply a measured fan/output capacity curve while safely OFF.

        This does not measure capacity, switch the fan, run a relay step test,
        reset existing PID gains, or issue a physical Home Assistant service.
        """
        cfg = model.settings(self.manager, spec)
        if cfg["control_mode"] != "pid":
            raise HomeAssistantError("Select PID before applying measured fan capacity")
        cap = model.capabilities(self.manager, spec)
        if cap is None or not self._current_spec(spec) or not cap.fan_entity:
            raise HomeAssistantError("Native fan capabilities unavailable")
        if cap.domain not in ("climate", "humidifier"):
            raise HomeAssistantError("Capacity compensation is for ON/OFF equipment with a fan")
        direction = cfg["pid_fan_capacity_for_mode"]
        if direction not in model.PID_FAN_DIRECTIONS or direction not in cap.modes:
            raise HomeAssistantError("Select the specific native heating/cooling/drying direction")
        record = self._record(spec)
        source = self.hass.states.get(cap.primary)
        if (source is None or not output_off(source) or record.get("pending")
                or record.get("power") or record.get("paused")):
            raise HomeAssistantError("Physical device must be safely OFF, idle and reconciled")
        fan_min = model.device_limits(self.manager, spec, cap)["fan_min_percentage"]
        try:
            curve = build_fan_capacity_model(
                percentage=cap.fan_percentage,
                advertised_modes=cap.fan_modes, measured=cfg,
                min_speed=fan_min,
            )
        except ValueError as error:
            raise HomeAssistantError(f"Invalid measured fan capacities: {error}") from error
        saved = {
            **curve, "direction": direction,
            "physical_entity": cap.primary, "fan_entity": cap.fan_entity,
            "sources": list(spec.source_entities),
        }
        maps = deepcopy(cfg["pid_fan_capacity_models"])
        maps[direction] = saved
        await self.async_update(spec, {
            "pid_fan_capacity_models": maps,
            "pid_fan_capacity_mode": "measured",
        })

    async def async_set_targets(self, spec: model.ManagedDevice, values: dict,
                                *, mode: str | None = None) -> None:
        cap = model.capabilities(self.manager, spec)
        if cap is None:
            raise HomeAssistantError("Native capabilities unavailable")
        cfg = model.settings(self.manager, spec)
        changes = {}
        if cfg["control_mode"] == "existing" or mode is not None:
            changes["control_mode"] = "off" if mode == "off" else "manual"
        effective={**cfg,**changes}
        profile=model.profile_name(effective,model.plan_for(self.manager,spec))

        if effective["control_mode"]=="manual" and effective.get("preset","none")=="none":
            table=deepcopy(cfg["profile_targets"])
            table["manual"]={**table.get("manual",{}),**values}
            changes["profile_targets"]=table
            if mode is not None:
                changes["requested_mode"]=mode
            await self.async_update(spec,changes)
            return

        if set(values)-{"heat","cool","humidity"}:
            raise HomeAssistantError("Unsupported room target")
        if not values:
            raise HomeAssistantError("No supported room target supplied")

        limits=model.device_limits(self.manager,spec,cap)
        lock=getattr(self.manager,"_device_settings_write_lock",None)
        if lock is None:
            lock=self.manager._device_settings_write_lock=asyncio.Lock()
        async with lock:
            options=deepcopy(self.manager.entry.options)
            rooms=deepcopy(self.manager.settings.get("climate_rooms",{}))
            room=deepcopy(rooms.get(spec.area_id,{}))

            if profile not in ("comfort","home","away","sleep","eco"):
                raise HomeAssistantError("Select a Room Environment profile before editing its target")

            from .climate_strategy import DEFAULT_PROFILE_TARGETS, profile_humidity_target
            raw_profiles=deepcopy(room.get("profiles",{}))
            raw_profiles=raw_profiles if isinstance(raw_profiles,dict) else {}
            fallback=DEFAULT_PROFILE_TARGETS[profile]
            existing=raw_profiles.get(profile,{})
            band={**fallback, "humidity": profile_humidity_target(room, profile),
                  **(existing if isinstance(existing,dict) else {})}

            if "humidity" in values:
                humidity=finite(
                    values["humidity"],
                    limits["humidity_min_limit"],
                    limits["humidity_max_limit"],
                )
                if humidity is None:
                    raise HomeAssistantError("Humidity target outside Room Environment limits")
                band["humidity"]=humidity

            for key,value in values.items():
                if key not in ("heat","cool"):
                    continue
                number=finite(
                    value,
                    limits["temperature_min_limit"],
                    limits["temperature_max_limit"],
                )
                if number is None:
                    raise HomeAssistantError("Target outside Room Environment limits")
                band["heat_c" if key=="heat" else "cool_c"]=number

            heat=float(band["heat_c"])
            cool=float(band["cool_c"])
            if cool-heat<1.0:
                raise HomeAssistantError("Heating and cooling targets must be at least 1°C apart")
            raw_profiles[profile]=band
            room["profiles"]=raw_profiles

            rooms[spec.area_id]=room
            options["climate_rooms"]=rooms
            self.hass.config_entries.async_update_entry(self.manager.entry,options=options)
        if getattr(self.manager,"_active",False):
            self.manager._recalculate(initial=True)


    async def async_set_fan(self, spec: model.ManagedDevice, value: str) -> None:
        cfg = model.settings(self.manager, spec)
        changes = {"control_mode": "manual"} if cfg["control_mode"] == "existing" else {}
        profile = model.profile_name({**cfg, **changes}, model.plan_for(self.manager, spec))
        table = deepcopy(cfg["profile_fans"])
        table[profile] = str(value)
        await self.async_update(spec, {**changes, "profile_fans": table})

    def resume_information(self, spec: model.ManagedDevice) -> dict | None:
        """Read-only explanation of an unresolved native command and next step.

        This is safe for the controller status sensor and Check/Continue
        entity. Never scans the registry, polls hardware or issues a service.
        """
        record = self.records.get(spec.identifier, {})
        pending = record.get("pending") if isinstance(record, dict) else None
        unconfirmed_target = (record.get("unconfirmed_native_target")
                              if isinstance(record, dict) else None)
        retained_target = not pending and isinstance(unconfirmed_target, dict)
        if retained_target:
            pending = unconfirmed_target
        if not pending:
            return None
        from .equipment_resume import check_pending, instructions
        entity = pending.get("entity") if isinstance(pending, dict) else None
        state = self.hass.states.get(entity) if isinstance(entity, str) else None
        expected = pending.get("expected") if isinstance(pending, dict) else None
        ha_config = getattr(self.hass, "config", None)
        language = str(getattr(ha_config, "language", "en"))
        checked = check_pending(
            pending, state, self.clock(),
            record.get("pending_resume_probe"),
            matches_expected=matches(state, expected) if isinstance(expected, dict) else False,
            language=language,
            temperature_unit=getattr(getattr(ha_config, "units", None),
                                     "temperature_unit", None),
        )
        checked = {
            key: checked.get(key)
            for key in ("decision", "entity", "requested", "observed",
                        "remaining_seconds", "phase", "needs_physical_check")
        }
        if retained_target:
            from .equipment_resume import exhausted_target_message, pending_feedback_message
            checked["command_attempts"] = pending.get("attempts")
            checked["retry_limit_reached"] = (
                type(pending.get("attempts")) is int
                and pending["attempts"] >= NATIVE_COMMAND_MAX_ATTEMPTS
            )
            checked["requires_user_repeated_check"] = False
            message = (pending_feedback_message
                       if not checked["retry_limit_reached"]
                       and pending.get("retry_state_verified_at") is not None
                       else exhausted_target_message)
            checked["instructions"] = message(
                checked, language=language,
            )
        elif isinstance(record.get("automatic_continue_requested"), dict):
            # A saved user choice is handled by HEM itself. The user does
            # not need to keep pressing a button, and being online is not
            # proof the previously requested physical command succeeded.
            from .equipment_resume import automatic_recovery_message
            checked["instructions"] = automatic_recovery_message(
                checked, language=language,
            )
            checked["settings_saved"] = True
            checked["requires_user_repeated_check"] = False
        elif not record.get("paused"):
            # This read is not a manual Resume attempt. An ordinary pending
            # command is already checked/retried by _reconcile; presenting
            # the manual verifier's two-click instructions here falsely
            # implies a pause and that no command was sent.
            from .equipment_resume import pending_feedback_message
            checked["instructions"] = pending_feedback_message(
                checked, language=language,
            )
            checked["requires_user_repeated_check"] = False
        else:
            checked["instructions"] = instructions(
                checked, language=language,
            )
        return checked

    async def async_continue_automatic(self, spec: model.ManagedDevice) -> bool:
        """Select the prior PID/Automatic algorithm, without bypassing hardware.

        An explicit click always restores the *requested controller method*
        when the exact source identity and settings Store remain writable.
        Actual native service dispatch remains blocked until the usual
        physical ACK, ownership, dwell, and window/sleep guards permit it.
        """
        if not self._ready or not self._current_spec(spec):
            raise HomeAssistantError("Controller identity or storage is unavailable")
        cfg = model.settings(self.manager, spec)
        record = self._record(spec)
        upstream = record.get("upstream", {})
        if (cfg["control_mode"] in ("automatic", "pid")
                and not record.get("paused") and not record.get("pending")
                and not record.get("unconfirmed_native_target")
                and not record.get("native_setpoint_stop")
                and not (isinstance(upstream, dict) and (
                    upstream.get("paused") or upstream.get("pending")))):
            return True  # Already automatic; no mode or physical write.
        try:
            await self.async_resume(spec)
            return True
        except HomeAssistantError as problem:
            # An unavailable device or ambiguous in-flight native command is
            # NOT authority to discard protected state. Nonetheless, the user
            # explicitly chose the automatic algorithm. Persist that policy
            # without sending or assuming a physical command.
            async with self._lock(spec.identifier):
                if not self._ready or not self._current_spec(spec):
                    raise
                latest = model.settings(self.manager, spec)
                current = self._record(spec)
                original = current.get("resume_control_mode")
                desired = (original if original in ("automatic", "pid")
                           else latest["control_mode"] if latest["control_mode"]
                           in ("automatic", "pid") else "automatic")
                cap = model.capabilities(self.manager, spec)
                if (cap is not None and desired == "pid"
                        and "pid" not in model.control_modes(self.manager, spec)):
                    desired = "automatic"
                if latest["control_mode"] != desired:
                    lock = getattr(self.manager, "_device_settings_write_lock", None)
                    if lock is None:
                        lock = self.manager._device_settings_write_lock = asyncio.Lock()
                    async with lock:
                        latest = model.settings(self.manager, spec)
                        if not self._current_spec(spec):
                            raise HomeAssistantError("Native device identity changed")
                        options = deepcopy(self.manager.entry.options)
                        profiles = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
                        profiles = profiles if isinstance(profiles, dict) else {}
                        saved = profiles.get(spec.identifier, {})
                        saved = saved if isinstance(saved, dict) else {}
                        from .device_activation import authority_context
                        profile = {**saved, "control_mode": desired}
                        # This actual button click is a user authorization for
                        # exactly the still-configured physical sources, not
                        # a grant to another device or a physical service.
                        if cap is not None and cap.domain in (
                            "climate", "fan", "humidifier"
                        ):
                            profile["_native_authorization"] = authority_context(
                                self.manager, spec
                            )
                        profiles[spec.identifier] = profile
                        options[model.SETTINGS] = profiles
                        self.hass.config_entries.async_update_entry(
                            self.manager.entry, options=options
                        )
                current.pop("resume_control_mode", None)
                # Keep a genuine uncertain-command/manual source latch until
                # it can be physically reconciled. Choosing Automatic does
                # not mean that the compressor is already running.
                current["paused"] = current.get("paused") or (
                    "continue_automatic_waiting_for_physical_verification"
                )
                current["automatic_continue_requested"] = {
                    "at": self.clock(), "method": desired,
                    "awaiting_physical_verification": True,
                }
                await self._save()
                self._status(
                    spec, "awaiting_physical_acknowledgement"
                    if current.get("pending")
                    or (current.get("upstream") or {}).get("pending")
                    else "awaiting_evaluation",
                    reason="automatic_recovery_requested",
                    requested_control_mode=desired, settings_saved=True,
                    automatic_selected=True, physical_output_confirmed=False,
                    recovery_detail=(
                        "Automatic/PID is saved. HEM will verify the earlier "
                        "physical command and resume control when safe."
                    ),
                    last_verification_issue=str(problem)[:180],
                )
            # The caller is finished; HEM (not the user) now owns the
            # recovery/re-evaluation lifecycle on every normal scheduler tick.
            if getattr(self, "_active", False):
                self.schedule()
            return False

    async def async_resume(
        self, spec: model.ManagedDevice, *, automatic: bool = False,
    ) -> None:
        """Re-arm a verified live device without forcing an OFF/ON cycle.

        Explicit Resume grants another attempt after current-state verification.
        Background reconciliation preserves exhausted target budgets: stable
        observations establish current native state, not a successful command.
        Neither path issues a physical service or bypasses identity, authority,
        ownership or physical dwell verification.
        """
        async with self._lock(spec.identifier):
            if not self._ready or not self._current_spec(spec):
                raise HomeAssistantError("Controller or its source identity is unavailable")
            cfg = model.settings(self.manager, spec)
            cap = model.capabilities(self.manager, spec)
            record = self._record(spec)
            if (record.get("area") != spec.area_id
                    or tuple(record.get("sources", ())) != tuple(spec.source_entities)
                    or record.get("source_device_id") != spec.source_device_id):
                raise HomeAssistantError(
                    "Stored physical controller identity changed; Resume is not authorized"
                )
            if automatic and record.get("native_setpoint_stop"):
                # A committed shutdown has its own read/dispatch verifier.
                # Background Resume must not adopt a new episode or retire
                # its bounded OFF journal as generic stable-state recovery.
                return
            now = self.clock()
            supply = cfg.get("power_switch_entity")
            upstream = record.setdefault("upstream", {})
            if not isinstance(upstream, dict):
                raise HomeAssistantError("Invalid upstream supply history")
            from .equipment_power_switch import permitted_supply
            identity = None
            outlet = None
            if supply:
                # A relay ON is not inherently unsafe: preserve its previous
                # ownership, if any, without ever adopting an unowned ON relay.
                # All subsequent physical commands still have exact-ID checks.
                identity = permitted_supply(
                    self.manager, spec, supply, upstream.get("identity")
                )
                outlet = self.hass.states.get(supply)
                if (identity is None or outlet is None
                        or outlet.state not in ("on", "off")
                        or upstream.get("entity") not in (None, supply)):
                    raise HomeAssistantError(
                        "The selected supply identity or physical state cannot be verified"
                    )
                previous_switch_intent = upstream.get("pending")
                if ((upstream.get("owned") or previous_switch_intent)
                        and upstream.get("identity") != identity):
                    raise HomeAssistantError(
                        "Stored power-switch ownership identity cannot be verified"
                    )
                if previous_switch_intent:
                    if (not isinstance(previous_switch_intent, dict)
                            or previous_switch_intent.get("phase") != "commanded"
                            or previous_switch_intent.get("identity") != identity
                            or previous_switch_intent.get("desired") != outlet.state):
                        raise HomeAssistantError(
                            "A prior upstream power command needs acknowledgement before Resume"
                        )
            elif (upstream.get("owned") or upstream.get("pending")):
                raise HomeAssistantError("An old managed power switch still needs reconciliation")

            physical = {e: self.hass.states.get(e) for e in spec.source_entities}
            observed = {e: snapshot(value) for e, value in physical.items()}
            # With an intentionally OFF supply, no native state is expected.
            # Otherwise an unavailable native endpoint is NOT verified idle.
            offline = bool(supply and outlet.state == "off")
            if any(value is None for value in observed.values()) and not offline:
                raise HomeAssistantError(
                    "Physical equipment is unavailable; Resume cannot verify its output"
                )
            if offline:
                # An OFF physical supply cannot authenticate a live downstream
                # output. ESPHome/native climate may keep its last DRY/HEAT
                # mode while the relay is disconnected; never count that mode
                # as running, claim ownership, or send a service during Resume.
                # Conversely, a previously owned/pending native command (or
                # controller-owned supply that unexpectedly went OFF) remains
                # a real safety conflict, not a stale-state recovery.
                if (record.get("power") or record.get("pending")
                        or upstream.get("owned")):
                    raise HomeAssistantError(
                        "The upstream supply is OFF with unresolved controller "
                        "power ownership or a pending native command"
                    )

            pending = record.get("pending")
            pending_recovery = None
            if pending:
                from .equipment_resume import check_pending, instructions
                # A valid source/identity is mandatory. Never use a stale
                # stored entity or a disconnected endpoint as native feedback.
                if (not isinstance(pending, dict)
                        or pending.get("entity") not in physical):
                    raise HomeAssistantError(
                        "An interrupted native command refers to a missing physical "
                        "device. Check the original device in Home Assistant; "
                        "HEM cannot safely clear or replay the command."
                    )
                reported = physical[pending["entity"]]
                ha_config = getattr(self.hass, "config", None)
                language = str(getattr(ha_config, "language", "en"))
                confirmation = check_pending(
                    pending, reported, now,
                    record.get("pending_resume_probe"),
                    matches_expected=matches(
                        reported, pending.get("expected", {}),
                    ) if isinstance(pending.get("expected"), dict) else False,
                    language=language,
                    temperature_unit=getattr(getattr(ha_config, "units", None),
                                             "temperature_unit", None),
                )
                decision = confirmation["decision"]
                if decision == "first_check":
                    record["pending_resume_probe"] = {
                        "command": confirmation["command"],
                        "observed": confirmation["observation"],
                        "at": now,
                    }
                    await self._save()
                if decision not in ("confirmed", "verified"):
                    raise HomeAssistantError(
                        instructions(confirmation, language=language)
                    )
                # When HA acknowledged a command but failed to record the
                # durable completion, a fresh matching native observation
                # can re-arm it. A differing/old observation requires two
                # deliberate, unchanged user checks >=60s apart after a
                # >=120s native-command settling period.
                pending_recovery = decision
            for e in record.get("power", {}):
                if e not in physical or observed[e] is None:
                    raise HomeAssistantError(
                        "Previously owned native output is missing or unavailable"
                    )
            if any(
                foreign_owner_hold(self.hass, self.manager.entry.entry_id, e)
                for e, value in physical.items() if value is not None
            ):
                raise HomeAssistantError(
                    "A different controller still owns the physical equipment"
                )

            live_primary = physical.get(cap.primary) if cap is not None else None
            active = (not offline and cap is not None and live_primary is not None
                      and not output_off(live_primary))
            if active:
                if (cap.primary not in spec.source_entities or "off" not in cap.modes
                        or (cap.domain == "climate" and live_primary.state not in cap.modes)
                        or (cap.domain in ("number", "input_number")
                            and (finite(live_primary.state, 0, 100) is None
                                 or live_primary.attributes.get("unit_of_measurement") != "%"
                                 or live_primary.attributes.get("min") != 0
                                 or live_primary.attributes.get("max") != 100))):
                    raise HomeAssistantError("Unsupported or unverified running physical output")
                # Only a user-selected native controller method, with its
                # original exact-device power authorization, can explicitly
                # take over an already-running appliance.
                if cfg["control_mode"] not in ("pid", "automatic", "manual"):
                    raise HomeAssistantError(
                        "Running physical equipment needs an authorized controller "
                        "method before Continue Automatic"
                    )
                from .device_activation import authorized
                _, power_granted = model.permission(self.manager, spec, cap)
                if not power_granted or not authorized(self.manager, spec):
                    raise HomeAssistantError(
                        "Physical power control is not authorized for this device"
                    )
            elif (cap is None and not offline):
                raise HomeAssistantError("Native physical capabilities are unavailable")

            prior = deepcopy(record)
            # Continue Automatic is an explicit user choice. Restore the
            # previously configured PID when available; otherwise choose the
            # regular Automatic algorithm, never leave a successful Resume
            # stranded in Manual/Off. A selected already-running Automatic
            # or PID method needs reconciliation only, not a mode change.
            chosen = record.get("resume_control_mode")
            if chosen not in ("automatic", "pid"):
                chosen = cfg["control_mode"] if cfg["control_mode"] in (
                    "automatic", "pid"
                ) else "automatic"
            restore_mode = chosen if chosen != cfg["control_mode"] else None
            if restore_mode and cap is not None and (
                restore_mode not in model.control_modes(self.manager, spec)
            ):
                raise HomeAssistantError(
                    "Selected automatic control method is no longer supported"
                )

            # Preserve the physical start for already-owned outputs. A
            # previously unowned active appliance is accepted ONLY because
            # the user pressed Resume; start a conservative new supervision
            # interval without pretending the controller switched it on.
            next_power = {}
            for entity, owned in record.get("power", {}).items():
                if not output_off(physical[entity]):
                    # A manual OFF -> ON between controller evaluations may
                    # restart the real physical ON interval. Use the LATER
                    # of recorded ownership and current observed ON start,
                    # so Resume cannot prematurely end a newly started cycle.
                    owned_since = finite(owned.get("since"), 0, now)
                    if owned_since is None:
                        raise HomeAssistantError("Stored native power runtime is not verified")
                    # Unlike a real OFF->ON transition recorded while running,
                    # HA startup can reset last_changed when it re-creates an
                    # already-ON thermostat. NEVER turn that timestamp into a
                    # fabricated new minimum-ON period.
                    observation = record.get("native_power_observations", {})
                    observation = observation.get(entity) if isinstance(
                        observation, dict) else None
                    if (isinstance(observation, dict)
                            and observation.get("state") == "on"):
                        known_since = finite(observation.get("since"), 0, now)
                    else:
                        known_since = None
                    next_power[entity] = {
                        **owned, "since": max(owned_since, known_since or owned_since),
                    }
            if active and cap.primary not in next_power:
                on_min, _, max_on = model.timing(self.manager, spec, cap)
                observation = record.get("native_power_observations", {})
                observation = observation.get(cap.primary) if isinstance(
                    observation, dict) else None
                trusted_since = (
                    finite(observation.get("since"), 0, now)
                    if isinstance(observation, dict)
                    and observation.get("state") == "on" else None
                )
                if trusted_since is None:
                    changed = getattr(live_primary, "last_changed", None)
                    try:
                        trusted_since = finite(changed.timestamp(), 0, now) if changed else None
                    except (AttributeError, TypeError, ValueError, OverflowError):
                        trusted_since = None
                next_power[cap.primary] = {
                    "since": trusted_since if trusted_since is not None else now,
                    "min_on": on_min, "max_on": max_on,
                }
            # A physically uncertain ON/OFF request is not evidence of the
            # actual moment a compressor or heater changed state. If the
            # user explicitly accepted current native feedback, restart
            # only this uncertain output's minimum physical dwell, never
            # infer the old power timestamp or issue an actuator command.
            if (pending_recovery is not None and pending
                    and pending.get("power") is True
                    and (pending_recovery == "verified"
                         or pending.get("phase") in ("intent", "retry_intent"))
                    and pending["entity"] in next_power):
                owned_since = next_power[pending["entity"]]
                next_power[pending["entity"]] = {
                    **owned_since, "since": now,
                }
            next_off_at = dict(record.get("off_at", {}))
            for entity, value in physical.items():
                if output_off(value):
                    observed_off = self._observed_off_since(entity, now)
                    historical = finite(next_off_at.get(entity), 0, now)
                    next_off_at[entity] = max(observed_off, historical or 0)

            if (pending_recovery is not None and pending
                    and pending.get("power") is True
                    and (pending_recovery == "verified"
                         or pending.get("phase") in ("intent", "retry_intent"))
                    and output_off(physical[pending["entity"]])):
                next_off_at[pending["entity"]] = now
            record.update(
                paused=None, pending=None, power=next_power,
                baseline=observed, off_at=next_off_at,
            )
            sequence = record.get("native_setpoint_stop")
            if isinstance(sequence, dict) and (
                sequence.get("entity") != cap.primary
                or live_primary.state != sequence.get("mode")
                or sequence.get("entity") not in next_power
            ):
                # Only this successful explicit physical reconciliation can
                # retire a stop belonging to a now-obsolete native episode.
                # Keep its evidence; no actuator call is made by Resume.
                sequence.update(reconciled_at=now,
                                observed_mode=live_primary.state,
                                superseded_by="explicit_native_reconciliation")
                record["last_native_setpoint_stop"] = deepcopy(sequence)
                record.pop("native_setpoint_stop", None)
            elif isinstance(sequence, dict):
                # Explicit native reconciliation may conservatively restart
                # the physical dwell. Keep the same committed OFF tied to
                # that verified episode; never reopen its active target leg.
                sequence["owned"] = True
                sequence["owned_since"] = next_power[sequence["entity"]]["since"]
                sequence.pop("invalidated_on_epoch", None)
                if pending and pending.get("stop_sequence_at") == sequence.get("requested_at"):
                    sequence["resume_journal"] = deepcopy(pending)
                    if pending.get("stop_finish"):
                        sequence["phase"] = "off_ready"
                        sequence.pop("off_retry_budget", None)
                        sequence["explicit_retry_at"] = now
                    elif sequence.get("phase") == "preparing":
                        sequence.update(phase="uncertain", recovered_at=now,
                                        off_not_before=now + 30.0)
            target_budget = record.get("unconfirmed_native_target")
            if not automatic:
                # A successful explicit Check/Continue is fresh user consent
                # to try again. Background polls cannot provide this consent.
                record.pop("unconfirmed_native_target", None)
            elif (
                pending_recovery == "verified"
                and isinstance(pending, dict)
                and pending.get("service") == "set_temperature"
                and pending.get("power") is not True
                and type(pending.get("attempts")) is int
                and pending["attempts"] >= 2
                and (
                    pending.get("phase") == "retry_intent"
                    or pending["attempts"] >= NATIVE_COMMAND_MAX_ATTEMPTS
                    and (
                        pending.get("phase") == "commanded"
                        or isinstance(target_budget, dict)
                        and pending.get("phase") == "intent"
                        and all(pending.get(key) == target_budget.get(key)
                                for key in ("entity", "service", "data", "expected"))
                    )
                )
                and not output_off(physical[pending["entity"]])
            ):
                # Retire the blocking command journal so normal OFF policies
                # remain reachable, but retain its full failed target budget.
                # Two stable observations must never make this a new attempt 1.
                record["unconfirmed_native_target"] = deepcopy(pending)
                if pending.get("phase") == "retry_intent":
                    # Verified current state is not an ACK. Retain the exact
                    # retry budget and allow only its remaining attempts,
                    # through the ordinary fresh policy/dispatch gates.
                    record["unconfirmed_native_target"]["retry_state_verified_at"] = now
            target_budget = record.get("unconfirmed_native_target")
            if isinstance(target_budget, dict):
                native = physical.get(target_budget.get("entity"))
                expected_target = target_budget.get("expected")
                if (native is not None and observed.get(target_budget.get("entity")) is not None
                        and (output_off(native)
                             or isinstance(expected_target, dict) and expected_target
                             and matches(native, expected_target))):
                    # The target is now reported, or a real OFF ended its ON
                    # episode. Neither a timeout nor availability earns this.
                    record.pop("unconfirmed_native_target", None)
            record.pop("pending_resume_probe", None)
            if pending_recovery is not None and pending:
                record["last_resume_reconciliation"] = {
                    "at": now,
                    "entity": pending["entity"],
                    "method": "fresh_native_ack" if pending_recovery == "confirmed"
                              else "stable_native_state" if automatic
                              else "two_physical_checks",
                    "observed": physical[pending["entity"]].state,
                }
            record.pop("restart_power_verification", None)
            record.pop("restart_recovery_blocked", None)
            native_history = record.setdefault("native_power_observations", {})
            if not isinstance(native_history, dict):
                raise HomeAssistantError("Stored native power observations are invalid")
            if active:
                native_history[cap.primary] = {
                    "state": "on",
                    "since": next_power[cap.primary]["since"],
                }
            if supply:
                # Never claim an already-ON, previously unowned smart plug.
                # Its own history is independent of the native actuator.
                old_switch_intent = upstream.get("pending")
                owned_supply = bool(upstream.get("owned"))
                if old_switch_intent:
                    owned_supply = old_switch_intent["desired"] == "on"
                if outlet.state == "off":
                    owned_supply = False
                upstream.update(
                    entity=supply, identity=identity, paused=None, pending=None,
                    owned=owned_supply, idle_since=None,
                )
                if outlet.state == "off":
                    old_off = finite(upstream.get("off_at"), 0, now)
                    upstream["off_at"] = max(
                        old_off or 0, self._observed_off_since(supply, now)
                    )
            self._memory.pop(spec.identifier, None)
            self._profile_wake.pop(spec.identifier, None)
            self._fan_allocations.pop(spec.identifier, None)
            self._pid_offline_previews.pop(spec.identifier, None)

            # Restoring a previously chosen automatic method is a policy
            # update, not a device write. Preserve all unrelated options.
            if restore_mode:
                lock = getattr(self.manager, "_device_settings_write_lock", None)
                if lock is None:
                    lock = self.manager._device_settings_write_lock = asyncio.Lock()
                async with lock:
                    options = deepcopy(self.manager.entry.options)
                    profiles = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
                    profiles = profiles if isinstance(profiles, dict) else {}
                    saved = profiles.get(spec.identifier, {})
                    if (not isinstance(saved, dict)
                            or saved.get("control_mode") != cfg["control_mode"]
                            or not self._current_spec(spec)):
                        record.clear()
                        record.update(prior)
                        raise HomeAssistantError(
                            "Controller settings changed during manual reconciliation"
                        )
                    profiles[spec.identifier] = {
                        **saved, "control_mode": restore_mode,
                    }
                    options[model.SETTINGS] = profiles
                    self.hass.config_entries.async_update_entry(
                        self.manager.entry, options=options,
                    )
                record.pop("resume_control_mode", None)
            await self._save()

            # A durable save may yield to a native state change. The command
            # loop cannot start under this controller lock until we return,
            # so reject the re-arm rather than claim a stale hardware state.
            if (not self._current_spec(spec)
                    or any(snapshot(self.hass.states.get(e)) != before
                           for e, before in observed.items())
                    or (supply and (
                        self.hass.states.get(supply) is None
                        or self.hass.states.get(supply).state != outlet.state
                        or permitted_supply(self.manager, spec, supply, identity) is None
                    ))):
                # A changed observation invalidates the completed two-check
                # proof. Preserve the original unresolved command so another
                # user check is required; do not erase its safety evidence.
                if (pending_recovery == "verified"
                        or pending_recovery == "confirmed" and pending
                        and pending.get("phase") in ("intent", "retry_intent")
                        or prior.get("unconfirmed_native_target")
                            != record.get("unconfirmed_native_target")):
                    record.clear()
                    record.update(prior)
                    record.pop("pending_resume_probe", None)
                record["paused"] = "physical_state_changed_during_resume"
                await self._save()
                raise HomeAssistantError(
                    "Physical state or identity changed during Resume; retry after verification"
                )
            effective_method = restore_mode or cfg["control_mode"]
            # Prefer existing localized statuses rather than creating an
            # untranslated diagnostic enum and another recorder schema.
            self._status(
                spec, "awaiting_physical_acknowledgement"
                if record.get("unconfirmed_native_target")
                else "manual" if active and effective_method == "manual"
                else "controlling" if active else "awaiting_evaluation",
                reason="previous_command_not_yet_confirmed"
                if record.get("unconfirmed_native_target")
                else "explicit_resume_verified_running" if active
                else "explicit_resume_awaiting_evaluation",
                physical_mode=live_primary.state if active else "off",
                controller_method=effective_method,
            )
        # No new hardware command or artificial five-minute startup hold.
        # Trigger one eligible controller evaluation on the next event loop
        # turn; the existing service-ACK and dwell gates remain authoritative.
        if self._active:
            self.schedule()

    def schedule(self) -> None:
        if not self._active or not self._ready:
            return
        known = {spec.identifier: spec for spec in model.specs(self.manager)}
        for key, spec in known.items():
            cfg = model.settings(self.manager, spec)
            if cfg["control_mode"] == "existing" and not (
                self.records.get(key, {}).get("power")
                or self.records.get(key, {}).get("pending")
                or self.records.get(key, {}).get("native_setpoint_stop")
            ):
                continue
            task = self._tasks.get(key)
            if task is not None and not task.done():
                continue
            self._tasks[key] = self.hass.async_create_task(self._run(spec))
        for key, record in tuple(self.records.items()):
            if key not in known and (
                record.get("power") or record.get("pending")
                or record.get("native_setpoint_stop")
            ):
                task = self._tasks.get(key)
                if task is None or task.done():
                    spec = model.ManagedDevice(key, record["area"], "Retired controller",
                        record.get("source_device_id"), tuple(record["sources"]))
                    self._tasks[key] = self.hass.async_create_task(self._run(spec))

    async def _run(self, spec: model.ManagedDevice) -> None:
        try:
            async with self._lock(spec.identifier):
                await self.tick(spec)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Managed controller failed for %s", spec.identifier)
            if self._ready:
                await self._pause(spec, "controller_exception")
        finally:
            if self._tasks.get(spec.identifier) is asyncio.current_task():
                self._tasks.pop(spec.identifier, None)
                rerun = getattr(self, "_setpoint_rerun", set())
                if spec.identifier in rerun:
                    rerun.discard(spec.identifier)
                    if self._active and self._ready:
                        self.schedule()

    def measurements(self, spec: model.ManagedDevice, cap: model.Capabilities) -> dict:
        room, dev = model.room_config(self.manager, spec), model.device_config(self.manager, spec, cap.primary)
        values = {}
        for metric, key in (("temperature", "temperature_entity"), ("humidity", "humidity_entity"),
                            ("co2", "co2_entity"), ("pm25", "pm25_entity")):
            from .room_sources import selected, aggregate
            group = metric if metric in ("temperature", "humidity") else "air_quality"
            chosen = selected(self.manager.settings, spec.area_id, group)
            if chosen is not None:
                if group == "air_quality":
                    from .discovery import supported_metric
                    chosen = tuple(
                        entity for entity in chosen
                        if (state := self.hass.states.get(entity)) is not None
                        and supported_metric(self.hass, state, outdoor=False) == metric
                    )
                value, _ = aggregate(self.hass, chosen, spec.area_id, group, 10)
                values[metric] = value
                values[key] = None
                values[metric + "_selected_entities"] = list(chosen)
                values[metric + "_source"] = "room_selected_mean"
                continue

            # Legacy fallback only when this room has never been given an
            # explicit source selection for this metric.
            source = dev.get(key) or room.get(key)
            if metric == "temperature" and not source:
                source = self.manager.settings.get("pid_rooms", {}).get(spec.area_id, {}).get("temperature_entity")
            excluded = self.manager.settings.get(CONF_EXCLUDED_INDOOR, {}).get(spec.area_id, [])
            legacy_mean = None
            if not source and metric in ("temperature", "humidity"):
                candidates = []
                for observed in self.hass.states.async_all("sensor"):
                    if (observed.entity_id in excluded
                            or entity_area(self.hass, observed.entity_id) != spec.area_id):
                        continue
                    if metric == "temperature":
                        if observed.attributes.get("device_class") != "temperature":
                            continue
                        valid = temperature_sensor_c(self.hass, observed.entity_id, 10)
                        if valid is not None and not -60 <= valid <= 85:
                            valid = None
                    else:
                        sample = reading(self.hass, observed.entity_id, 10, outdoor=False)
                        valid = sample.value if sample.metric == metric else None
                    if valid is not None:
                        candidates.append((observed.entity_id, valid))
                if candidates:
                    legacy_mean = sum(sample for _, sample in candidates) / len(candidates)
                    source = candidates[0][0] if len(candidates) == 1 else None
            value = None
            if isinstance(source, str) and source not in excluded and entity_area(self.hass, source) == spec.area_id:
                if metric == "temperature":
                    value = temperature_sensor_c(self.hass, source, 10)
                else:
                    observed = reading(self.hass, source, 10, outdoor=False)
                    value = observed.value if observed.metric == metric else None
            if source is None:
                value = legacy_mean
            values[metric] = value
            values[key] = source
            values[metric + "_source"] = (
                "legacy_fallback" if source else
                "legacy_room_mean" if legacy_mean is not None else "unavailable"
            )
        return values

    def _quiet_context(self, spec: model.ManagedDevice, cfg: dict, plan: dict) -> bool:
        """Do not raise fan speed on missing sleep/presence evidence."""
        if not (cfg.get("quiet_sleep") or cfg.get("quiet_occupied")):
            return False
        room = model.room_config(self.manager, spec)
        shared = plan.get("global_presence", {})
        shared = shared if isinstance(shared, dict) else {}
        known = set(plan.get("known_presence_areas", [spec.area_id]))
        occupied = plan.get("occupancy", "unknown")
        sleeping = plan.get("sleeping")
        from .occupancy_policy import controlled_sleep_presence, home_presence
        # Home trackers come from configuration, never the plan's combined
        # evidence list, which can also contain room-presence sources.
        home, _, _ = home_presence(
            self.hass, shared, room.get("away_entities", []))
        # A previous Away plan has no room readings. Re-resolve from the
        # configured room on return, even without shared presence settings.
        occupied, _, _ = room_presence(self.hass, spec.area_id, room, shared,
                                        known_areas=known or {spec.area_id},
                                        home_status=home)
        if shared:
            # Fan quiet behavior and the heating gate must evaluate the same
            # refreshed sleep facts. A failed optional sleep source while
            # everyone is verified away is not proof of a sleeping occupant.
            from .climate_schedule import scheduled_sleep
            zone = getattr(getattr(self.hass, "config", None), "time_zone", None) or "UTC"
            local_sleep, local_reason = scheduled_sleep(room, self.clock(), zone)
            sleeping, _ = controlled_sleep_presence(
                self.hass, spec.area_id, shared, known or {spec.area_id},
                home_status=home, room_status=occupied, local_sleeping=local_sleep,
                local_reason=local_reason, now=self.clock(),
                inherit_household=(cfg.get("sleep_when_everyone_asleep") is True
                                   and cfg.get("control_mode") in ("automatic", "pid")),
            )
        # Unavailable optional presence/sleep sensors must never prevent a
        # humidity or thermal output from operating. When they cannot prove
        # whether quieting is needed, conservatively use the quiet fan limit.
        # This does not override explicit occupied/absent actuator policies.
        uncertain = False
        if cfg["quiet_sleep"]:
            if sleeping is True:
                return True
            if sleeping is None:
                uncertain = True
        if cfg["quiet_occupied"]:
            if occupied == "occupied":
                return True
            if occupied not in ("occupied", "unoccupied"):
                uncertain = True
        return True if uncertain else False

    def _window_policy(self, spec, cfg=None):
        from .equipment_window import evaluate
        return evaluate(self, spec, cfg)

    def _stop_policy_verified(
        self, spec: model.ManagedDevice, cap: model.Capabilities, kind: str,
    ) -> bool:
        """Recheck shutdown consent and live sleep/demand before native OFF.

        Stop commands are a separate, narrowly scoped write path. A verified
        sleep pause must turn an authorized native output OFF, not merely stop
        PID adjustments. An IDLE stop needs independent qualified measurements;
        an unknown reading never proves idle. Neither policy can power ON.
        """
        cfg = model.settings(self.manager, spec)
        if "off" not in cap.modes or cfg.get("control_mode") not in (
            "automatic", "pid", "manual"
        ):
            return False
        room = model.room_config(self.manager, spec)
        plan = model.plan_for(self.manager, spec)
        if kind == "window":
            return (cfg.get("pause_on_window_open", False) is True
                    and self._window_policy(spec, cfg).get("stop_requested") is True)
        if kind == "sleep":
            from .device_activation import effective_device
            dev = effective_device(self.manager, spec, cap.primary)
            if dev.get("sleep_behavior") != "pause":
                return False
            _decision, reason = live_device_permission(
                self.hass, spec.area_id, room, plan, dev,
            )
            return reason == "sleep_room_control_paused"
        if kind == "idle" and cfg["control_mode"] in ("automatic", "pid"):
            from .equipment_power_switch import approved_demand
            return approved_demand(self, spec, cfg, cap) is False
        if kind == "target" and cfg["control_mode"] == "pid":
            from .equipment_pid_safety import condition
            current = condition(self, spec, cap)
            return current is not None and current["needed"] is False
        return False

    def _shutdown_allowed(self, spec: model.ManagedDevice, entity: str, expected: dict) -> bool:
        """Only an already-owned OFF can survive deselection or removed rooms."""
        from homeassistant.helpers import entity_registry as er
        record = self._record(spec)
        item = er.async_get(self.hass).async_get(entity)
        state = self.hass.states.get(entity)
        is_off = expected.get("state") == "off" or entity.startswith(("number.", "input_number.")) and finite(expected.get("state"), 0, 100) == 0
        owned = record.get("power", {}).get(entity)
        return bool(is_off and owned and entity in record["sources"] and item is not None
                    and getattr(item, "platform", None) != DOMAIN
                    and getattr(item, "device_id", None) == record.get("source_device_id")
                    and entity_area(self.hass, entity) == record["area"]
                    and not foreign_owner_hold(self.hass, self.manager.entry.entry_id, entity)
                    and state is not None and state.state not in ("unknown", "unavailable")
                    and state.attributes.get("hvac_action") != "defrosting"
                    and self.clock()-owned["since"] >= owned["min_on"])

    async def _retired(self, spec: model.ManagedDevice) -> None:
        """Drain acknowledged owned outputs using their original physical limits.

        Deleted/reassigned physical identities and interrupted restart ownership
        remain latched for manual reconciliation. No permission for a new ON is
        inferred from an old record.
        """
        record = self._record(spec)
        if record.get("paused"):
            self._status(spec, "retired_requires_manual_reconciliation", reason=record["paused"])
            return
        raw = record.get("capabilities")
        if not isinstance(raw, dict):
            self._status(spec, "retired_requires_manual_reconciliation")
            return
        try:
            cap = model.Capabilities(**raw)
        except (TypeError, ValueError):
            self._status(spec, "retired_requires_manual_reconciliation")
            return
        if not await self._reconcile(spec):
            return
        for entity in tuple(record["power"]):
            if entity != cap.primary:
                self._status(spec, "retired_identity_requires_manual_reconciliation")
                continue
            if await self._power(spec, cap, "off", automatic=False, shutdown=True):
                return
        if not record["power"] and not record.get("pending"):
            self._status(spec, "retired_outputs_reconciled")

    def _gate(self, spec: model.ManagedDevice, cap: model.Capabilities, cfg: dict, plan: dict,
              mode: str, *, automatic: bool = True, window_stop: bool = False) -> str | None:
        if not self._active or not self._ready:
            return "controller_inactive"
        if not self._current_spec(spec):
            return "source_deselected_or_moved"
        for entity in spec.source_entities:
            if snapshot(self.hass.states.get(entity)) is None:
                return "physical_device_unavailable"
            if other := foreign_owner_hold(self.hass, self.manager.entry.entry_id, entity):
                return other
        for key, record in self.records.items():
            if (key != spec.identifier and record.get("source_device_id") is not None
                    and record.get("source_device_id") == spec.source_device_id
                    and record.get("area") == spec.area_id and record.get("pending")):
                return "other_endpoint_acknowledgement_pending"
        if self._record(spec).get("paused"):
            return "controller_paused"
        if cfg["control_mode"] == "existing":
            return "existing_controller_selected"
        room = model.room_config(self.manager, spec)
        native = self.hass.states.get(cap.primary)
        if native is not None and native.attributes.get("hvac_action") == "defrosting":
            return "native_defrost_protection"
        if cfg.get("pause_on_window_open", False):
            window = self._window_policy(spec, cfg)
            if window["blocked"] and not window_stop:
                return window["status"]
        # The per-controller live window policy above is authoritative.
        # Do not additionally reject an otherwise safe local controller due
        # to old climate-plan contacts from another room, or an outdated
        # window_safe field that has not yet been recalculated.
        if mode in ("heat", "cool", "heat_cool"):
            if conflict := _physical_climate_conflict(self.hass, spec.area_id, room, cap.primary, mode):
                return conflict
        if automatic:
            soft, _ = model.permission(self.manager, spec, cap)
            if not soft:
                return "select_control_method_to_authorize_current_device_sources"
            if self.clock()-self._started < STARTUP_SECONDS:
                return "startup_warmup"
            from .device_activation import effective_device
            device = effective_device(self.manager, spec, cap.primary, cap=cap)
            if device:
                allowed, reason = live_device_permission(self.hass, spec.area_id, room, plan, device)
                if allowed != "eligible":
                    return reason
            if cap.domain == "fan" or set(cap.modes) == {"off", "fan_only"}:
                dev = effective_device(self.manager, spec, cap.primary)
                purpose = dev.get("fan_purpose") or ("extraction" if room.get("extraction_fan_entity") == cap.primary else None)
                if purpose not in ("extraction", "filtration"):
                    return "select_fan_purpose_on_controller_device"
                stamp = finite(plan.get("air_evidence_at"), 0, 1e13)
                if stamp is None or not 0 <= self.clock()-stamp <= 120:
                    return "air_quality_decision_expired"
                if purpose == "extraction":
                    if plan.get("air_actions", {}).get("outdoor_air_verified") is not True:
                        return "outside_air_not_verified"
                    # An extraction fan uses the same exact-room source
                    # policy, already evaluated at the top of this gate.
                elif not (dev.get("sensor_verified") is True or room.get("pm25_sensor_verified") is True):
                    return "particle_sensor_not_verified"
            if cap.domain == "humidifier" or mode == "dry":
                opposite = room.get("dehumidifier_entity" if cap.humidifying else "humidifier_entity")
                if opposite:
                    other = self.hass.states.get(opposite)
                    if other is None or other.state != "off":
                        return "opposing_humidity_device_active_or_unknown"
                for role in ("climate_entity", "heat_climate_entity", "cool_climate_entity", "dry_climate_entity"):
                    other_id = room.get(role)
                    if not other_id or other_id == cap.primary:
                        continue
                    other = self.hass.states.get(other_id)
                    if other is None or other.state in ("unknown", "unavailable"):
                        return "other_climate_unavailable"
                    if cap.humidifying and other.state in ("cool", "dry", "heat_cool", "auto"):
                        return "opposing_humidity_climate_active"
                    if mode == "dry" and cap.domain == "climate" and other.state not in ("off", "fan_only"):
                        return "thermal_priority_defer_dry"
                    if not cap.humidifying and other.state in ("cool", "heat_cool", "auto"):
                        humidity = self.measurements(spec, cap)["humidity"]
                        target = model.targets(self.manager, spec, cap, cfg, plan)["humidity"]
                        if humidity is None or humidity < target + float(room.get("cooling_dry_deferral_rh_points", 10)):
                            return "cooling_priority_defer_dehumidifier"
        return None

    async def _reconcile(self, spec: model.ManagedDevice) -> bool:
        record, now = self._record(spec), self.clock()
        # The supply can change between the earlier relay check and native
        # reconciliation. Never mistake an offline appliance's restored mode
        # for a physical manual override, or accept its stale ACK as live.
        supply = model.settings(self.manager, spec).get("power_switch_entity")
        if supply and (relay := self.hass.states.get(supply)) is not None and relay.state == "off":
            self._status(spec, "waiting_for_physical_device",
                         reason="upstream_switch_off_native_state_unverified")
            return False
        target_budget = record.get("unconfirmed_native_target")
        if (isinstance(target_budget, dict)
                and target_budget.get("entity") in spec.source_entities
                and self._identity_ok(spec)):
            entity = target_budget["entity"]
            native = self.hass.states.get(entity)
            expected_target = target_budget.get("expected")
            live = native is not None and native.state not in ("unknown", "unavailable")
            target_reported = bool(
                live and isinstance(expected_target, dict) and expected_target
                and matches(native, expected_target)
            )
            episode_ended = live and output_off(native)
            if target_reported or episode_ended:
                record.pop("unconfirmed_native_target", None)
                if target_reported and not episode_ended and not record.get("pending"):
                    # A late matching target is our expected feedback, not a
                    # human override or a new native ON/dwell transition.
                    # Rebase only the acknowledged attributes: a simultaneous
                    # user mode/fan change must still reach the override gate.
                    baseline = record.get("baseline", {}).get(entity)
                    fields = expected_target.get("attributes")
                    if (isinstance(baseline, dict)
                            and isinstance(baseline.get("attributes"), dict)
                            and isinstance(fields, dict)):
                        baseline["attributes"].update({
                            key: deepcopy(native.attributes[key])
                            for key in fields if key in native.attributes
                        })
                # Preserve the ordinary OFF observation/ownership handling
                # below; accepting an OFF must not skip its minimum dwell.
                await self._save()
        pending = record.get("pending")
        if pending:
            if not self._identity_ok(spec):
                await self._pause(spec, "physical_source_identity_changed")
                return False
            state = self.hass.states.get(pending["entity"])
            # ACK matching remains allowed immediately. Sending another
            # command, however, must respect full reconnect settling.
            if matches(state, pending["expected"]):
                record["baseline"][pending["entity"]] = snapshot(state)
                record["pending"] = None
                previous_target = record.get("unconfirmed_native_target")
                if (isinstance(previous_target, dict)
                        and previous_target.get("pid_target_satisfied") is True
                        and previous_target.get("entity") == pending["entity"]
                        and previous_target.get("service") == pending.get("service")
                        and not pending.get("power")):
                    # A later corrective target has now actually ACKed.
                    # The superseded target is not a fresh retry permission.
                    record.pop("unconfirmed_native_target", None)
                if pending.get("power"):
                    entity = pending["entity"]
                    if pending.get("output_on") is False or pending["expected"].get("state") == "off":
                        record["power"].pop(entity, None)
                        record["off_at"][entity] = now
                    else:
                        record["power"].setdefault(entity, {"since": now,
                            "min_on": pending["min_on"], "max_on": pending["max_on"]})
                await self._save()
            elif pending.get("retry_context") is not None:
                from .equipment_pid_safety import suppress_obsolete_pending
                if await suppress_obsolete_pending(self, spec, pending):
                    if record.get("pending") is not None:
                        return False
                    # A preserved, superseded setpoint must not block the
                    # independently authorized OFF of an already-owned ON.
                    # A late target ACK can arrive during its journal save;
                    # consume that ledger before classifying ordinary diffs.
                    return await self._reconcile(spec)
                else:
                    await self._retry_pending(spec, pending, now)
                    return False
            elif now < pending["when"] or now-pending["when"] > ACK_SECONDS:
                await self._pause(spec, "physical_acknowledgement_missing")
                return False
            else:
                self._status(spec, "awaiting_physical_acknowledgement")
                return False
        # The HA source has reappeared. Its initial mode/target reports can
        # still change as the physical device initializes or runs firmware
        # automations. Do not classify those changes as human intervention.
        settle_fn = getattr(self, "_native_settle_remaining", None)
        settle = settle_fn(spec) if callable(settle_fn) else 0
        if settle is None:
            self._status(spec, "waiting_for_physical_device",
                         reason="native_source_unavailable")
            return False
        if settle > 0:
            self._status(spec, "waiting_for_physical_device",
                         reason="native_restore_settling",
                         reconnect_settle_remaining_seconds=round(settle))
            return False
        fresh = {}
        settled = getattr(self, "_native_settled_for", {})
        for entity in spec.source_entities:
            epoch = getattr(self, "_native_ready_since", {}).get(entity)
            if epoch is not None and settled.get((spec.identifier, entity)) != epoch:
                native = snapshot(self.hass.states.get(entity))
                if native is not None:
                    fresh[entity] = native
                    settled[(spec.identifier, entity)] = epoch
        if fresh and not record.get("pending"):
            # Rebase only after the stable 30s. This is a source baseline
            # update, NOT permission to adopt an unowned running appliance or
            # bypass compressor ON/OFF dwell. The ordinary physical guards
            # below still handle all output authority.
            record.setdefault("baseline", {}).update(fresh)
            await self._save()
            self._status(spec, "awaiting_evaluation",
                         reason="native_restore_baseline_rechecked")
        restarted = getattr(self, "_restart_baseline_pending", set())
        if (spec.identifier in restarted and record.get("pending") is None
                and record.get("paused") != "physical_manual_override"):
            fresh_sources = {
                entity: snapshot(self.hass.states.get(entity))
                for entity in spec.source_entities
            }
            if all(value is not None for value in fresh_sources.values()):
                # Initial HA state restoration is NOT an external manual
                # change. The usual foreign-owner, permission and physical
                # dwell checks still govern all subsequent writes.
                record["baseline"] = fresh_sources
                restarted.discard(spec.identifier)
                await self._save()
        # Some native integrations recreate their climate entity after a
        # short loss of connectivity while an already HEM-owned external
        # power switch remains ON. The restored DRY/OFF state and defaults
        # are NOT evidence of a person touching the device. Rebase the
        # comparison only after observing that actual temporary loss.
        offline = getattr(self, "_native_offline_under_owned_supply", set())
        recovered = spec.identifier in offline
        cfg = model.settings(self.manager, spec)
        supply_entity = cfg.get("power_switch_entity")
        upstream = record.get("upstream", {})
        power_supply = self.hass.states.get(supply_entity) if supply_entity else None
        supply_owned_on = bool(
            supply_entity and isinstance(upstream, dict)
            and upstream.get("owned") is True and not upstream.get("pending")
            and not upstream.get("paused") and power_supply is not None
            and power_supply.state == "on"
        )
        if recovered and supply_owned_on and not record.get("pending"):
            fresh = {source: snapshot(self.hass.states.get(source))
                     for source in spec.source_entities}
            if fresh and all(current is not None for current in fresh.values()):
                # Reconnection cannot grant a new ON permission, a minimum
                # OFF exemption or a fictitious physical acknowledgement.
                # Previously owned ON outputs restart their minimum-ON clock
                # conservatively from now; known OFF resets minimum-OFF.
                for source, current in fresh.items():
                    if current["state"] == "off" and source in record["power"]:
                        record["power"].pop(source, None)
                        record.setdefault("off_at", {})[source] = now
                    elif current["state"] != "off" and source in record["power"]:
                        record["power"][source]["since"] = now
                record["baseline"].update(fresh)
                offline.discard(spec.identifier)
                await self._save()
                self._status(spec, "awaiting_evaluation",
                             reason="native_entity_reconnected_under_owned_supply")
        for entity, baseline in record.get("baseline", {}).items():
            if baseline is None:
                continue
            native_state = self.hass.states.get(entity)
            observed = snapshot(native_state)
            if observed is not None and observed != baseline:
                changed = _manual_output_changes(baseline, observed)
                if changed:
                    user_context = getattr(getattr(native_state, "context", None),
                                           "user_id", None)
                    # DRY-only compressors can report their own internal OFF
                    # while the dedicated, HEM-owned supply remains ON.
                    # It does not prove that a user changed the HVAC mode.
                    # A real HA user_id or a changed physical setpoint remains
                    # a manual intervention and is never swallowed here.
                    cap = model.capabilities(self.manager, spec)
                    native_self_stop = (
                        supply_owned_on and not user_context
                        and str(
                            native_state.attributes.get("change_origin")
                            or native_state.attributes.get("operation_source")
                            or ""
                        ).lower() not in (
                            "physical_button", "manual_button", "local_user"
                        )
                        and changed == ("state",)
                        and cap is not None and cap.primary == entity
                        and cap.domain == "climate"
                        and set(cap.modes) == {"off", "dry"}
                        and baseline.get("state") == "dry"
                        and observed.get("state") == "off"
                    )
                    if native_self_stop:
                        record["baseline"][entity] = observed
                        if entity in record["power"]:
                            record["power"].pop(entity, None)
                            record.setdefault("off_at", {})[entity] = now
                        await self._save()
                        self._status(spec, "minimum_off_hold",
                                     reason="native_dry_automatic_stop_not_user_override")
                        continue
                    # HA integrations also change mode, fan percentages and
                    # targets under their own firmware/native automations.
                    # A state diff by itself is NOT evidence of a person,
                    # especially when a fan is OFF (some report invalid or
                    # sentinel percentages). Only direct user context or
                    # explicit native human-origin evidence may demote PID.
                    context = getattr(native_state, "context", None)
                    direct_ha_user = bool(
                        user_context and not getattr(context, "parent_id", None)
                    )
                    native_origin = str(
                        native_state.attributes.get("change_origin")
                        or native_state.attributes.get("operation_source")
                        or ""
                    ).lower()
                    physical_button = native_origin in (
                        "physical_button", "manual_button", "local_user",
                    )
                    if direct_ha_user or physical_button:
                        record["manual_override_evidence"] = {
                            "kind": "ha_user" if direct_ha_user
                                    else "native_explicit_button",
                            "changed_controls": list(changed),
                            "at": now,
                        }
                        await self._pause(spec, "physical_manual_override")
                        self._status(
                            spec, "paused", reason="physical_manual_override",
                            changed_controls=list(changed),
                            verified_user_intervention=True,
                        )
                        return False
                    # Unattributed native transitions are *observations*.
                    # Preserve safety: an observed OFF ends old ownership and
                    # conservatively begins a NEW minimum-OFF interval; an
                    # ON under prior ownership restarts minimum-ON dwell.
                    # Never adopt a previously unowned ON output here.
                    if observed["state"] == "off":
                        if entity in record["power"]:
                            record["power"].pop(entity, None)
                            record.setdefault("off_at", {})[entity] = now
                    elif (entity in record["power"]
                          and observed["state"] != baseline.get("state")
                          and not (entity.startswith(("number.", "input_number."))
                              and finite(observed["state"], .000001, 100) is not None
                              and finite(baseline.get("state"), .000001, 100) is not None)):
                        # A target/fan attribute update is not a new native
                        # power episode. Genuine OFF->ON event epochs are
                        # independently handled by _observe_native_running.
                        record["power"][entity]["since"] = now
                    record["baseline"][entity] = observed
                    await self._save()
                    self._status(
                        spec, "awaiting_evaluation",
                        reason="unattributed_native_change_not_manual",
                        changed_controls=list(changed),
                        verified_user_intervention=False,
                    )
                    continue
                # ESPHome and HA can refresh capability metadata without the
                # user touching a physical control. Keep that metadata current
                # instead of permanently latching a false manual override.
                record["baseline"][entity] = observed
                await self._save()
        return True

    async def _retry_pending(
        self, spec: model.ManagedDevice, pending: dict, now: float,
    ) -> None:
        """Retry only the persisted identical command, never a new inferred intent.

        Physical ACK is checked first by _reconcile. A fresh policy/ownership
        check is mandatory before each additional native HA service call.
        Uncertain exceptions, changed consent and HA restarts still require
        reconciliation; they must never be counted as device nonresponse.
        """
        attempts = pending.get("attempts", 0)
        entity = pending.get("entity")
        state = self.hass.states.get(entity) if isinstance(entity, str) else None
        decision = native_retry_decision(pending, now, state)
        if state is None or state.state in ("unavailable", "unknown"):
            # Offline waiting never consumes attempts or permanently pauses
            # a valid previous command simply because the device vanished.
            self._status(spec, "waiting_for_physical_device",
                         reason="native_source_unavailable",
                         command_attempts=attempts,
                         command_retries_completed=max(0, attempts - 1))
            return
        settle_fn = getattr(self, "_native_settle_remaining", None)
        settle = settle_fn(spec) if callable(settle_fn) else 0
        if settle is None or settle > 0:
            self._status(spec, "waiting_for_physical_device",
                         reason="native_restore_settling",
                         reconnect_settle_remaining_seconds=(
                             round(settle) if settle is not None else None
                         ), command_attempts=attempts)
            return
        from .equipment_pid_safety import (
            command_allowed, command_profile_reason, condition, reducing_command,
            stopping_command, suppress_obsolete_pending,
        )
        context = pending.get("retry_context")
        cap = model.capabilities(self.manager, spec)
        if isinstance(context, dict) and cap is not None:
            why = command_profile_reason(
                self, spec, cap, pending.get("service"), pending.get("data", {}),
                mode=context.get("mode"), automatic=context.get("automatic") is True,
                stop_target=pending.get("stop_target") is True,
            )
            if why:
                # A restored/missing tracker is a temporary evidence hold,
                # not a new retry attempt or a permanent manual pause.
                self._status(spec, why, command_attempts=attempts)
                return
        if await suppress_obsolete_pending(self, spec, pending):
            return
        from .equipment_setpoint_sequence import enabled, retry_settings_match, startup_ready
        setpoint = pending.get("service") in ("set_temperature", "set_humidity")
        if setpoint and enabled(model.settings(self.manager, spec)):
            cap = model.capabilities(self.manager, spec)
            if cap is None or not await startup_ready(self, spec, cap, state):
                return
        if decision == "exhausted":
            epoch = getattr(self, "_native_reconnect_epoch", {}).get(entity)
            previous = pending.get("reconnect_retry_epoch_used")
            used = pending.get("reconnect_retry_uses", 0)
            last = pending.get("last_attempt_at")
            if (type(used) is int and used < NATIVE_RECONNECT_EXTRA_ATTEMPTS
                    and isinstance(epoch, (int,float))
                    and isinstance(last, (int,float))
                    and epoch > last
                    and epoch != previous
                    and now - epoch >= NATIVE_RECONNECT_SETTLE_SECONDS
                    and now - last >= NATIVE_COMMAND_RETRY_SECONDS
                    and pending.get("phase") == "commanded"
                    and isinstance(pending.get("retry_context"), dict)
                    and retry_settings_match(pending["retry_context"].get("settings"),
                                             model.settings(self.manager, spec))):
                pending["reconnect_retry_grant"] = True
                decision = "retry"
                # The actual grant will be consumed durably in retry_intent
                # before any physical service. Never manufacture a reconnect
                # grant from the mere fact that HA is currently online.
        if decision == "uncertain":
            await self._pause(spec, "native_retry_intent_uncertain")
            return
        if decision == "waiting":
            self._status(spec, "awaiting_physical_acknowledgement",
                         command_attempts=attempts,
                         command_retries_completed=max(0, attempts - 1),
                         native_output_confirmed=False)
            return
        if decision == "exhausted":
            await self._pause(spec, "physical_acknowledgement_missing")
            self._status(spec, "paused", reason="physical_acknowledgement_missing",
                         command_attempts=attempts,
                         command_retries_completed=NATIVE_COMMAND_MAX_ATTEMPTS - 1)
            return

        record = self._record(spec)
        entity = pending["entity"]
        context = pending.get("retry_context")
        cfg = model.settings(self.manager, spec)
        cap = model.capabilities(self.manager, spec)
        if cap is None or not model.sources_available(self.manager, spec):
            self._status(spec, "waiting_for_physical_device")
            return
        plan = model.plan_for(self.manager, spec)
        supply = cfg.get("power_switch_entity")
        relay = record.get("upstream", {})
        supply_state = self.hass.states.get(supply) if supply else None
        before = record.get("baseline", {}).get(entity)
        observed = snapshot(state)
        if (
            not isinstance(context, dict)
            or record.get("pending") is not pending
            or not self._current_spec(spec)
            or not self._identity_ok(spec)
            or asdict(cap) != record.get("capabilities")
            or not retry_settings_match(context.get("settings"), cfg)
            or before is None or observed is None
            or _manual_output_changes(before, observed)
            or (supply and (
                supply_state is None or supply_state.state != "on"
                or relay.get("paused") or relay.get("pending")
                or relay.get("owned") is not context.get("upstream_owned")
            ))
            or entity not in spec.source_entities
            or entity_area(self.hass, entity) != spec.area_id
            or foreign_owner_hold(
                self.hass, self.manager.entry.entry_id, entity
            )
        ):
            await self._pause(spec, "native_retry_authority_or_state_changed")
            return
        automatic = context.get("automatic") is True
        def changed_automatic_policy(current_cfg, current_plan):
            if (current_cfg.get("control_mode") not in ("automatic", "pid")
                    or record.get("native_setpoint_stop")):
                return False
            previous_profile = context.get("profile")
            current_profile = model.profile_name(current_cfg, current_plan)
            changed_profile = (
                automatic and previous_profile != current_profile
                and not pending.get("stop_target") and not pending.get("stop_finish")
                and not stopping_command(pending.get("service"), pending.get("data", {}))
                and not reducing_command(self, cap, pending.get("service"),
                                         pending.get("data", {}), context.get("mode"))
            )
            return (changed_profile or
                    (automatic and context.get("mode") != "off" and
                     current_plan.get("sleeping") is True and
                     self._stop_policy_verified(spec, cap, "sleep")) or
                    (context.get("policy_stop") == "sleep" and
                     not self._stop_policy_verified(spec, cap, "sleep")))

        if changed_automatic_policy(cfg, plan):
            # A Home/Away, alarm or household change is not a manual intervention. The
            # old dispatch remains uncertain: observe it through the normal
            # automatic verifier without replaying a now-obsolete profile command.
            record["automatic_continue_requested"] = {
                "at": now, "method": cfg["control_mode"],
                "awaiting_physical_verification": True,
            }
            self._status(spec, "awaiting_physical_acknowledgement",
                         reason="automatic_recovery_requested")
            await self._save()
            return
        before_on_epoch = getattr(self, "_native_on_epoch", {}).get(entity)
        mode = context.get("mode")
        shutdown = context.get("shutdown") is True
        policy_stop = context.get("policy_stop")
        active_command = automatic and not (
            pending.get("stop_target") or pending.get("stop_finish")
            or stopping_command(pending.get("service"), pending.get("data", {}))
        )
        if (not isinstance(mode, str)
                or (policy_stop is not None
                    and not self._stop_policy_verified(spec, cap, policy_stop))
                or (shutdown and not self._shutdown_allowed(
                    spec, entity, pending["expected"]))
                or (not shutdown and self._gate(
                    spec, cap, cfg, plan, mode, automatic=automatic,
                    window_stop=pending.get("power") and mode == "off"))
                or (pending.get("power") and not shutdown
                    and not model.permission(self.manager, spec, cap)[1])):
            await self._pause(spec, "native_retry_policy_changed")
            return
        if active_command:
            from .equipment_power_switch import approved_demand
            current_target = condition(self, spec, cap, mode, include_automatic=True)
            qualified = command_allowed(
                self, spec, cap, pending.get("service"), pending.get("data", {}),
                mode=mode, automatic=True, power=pending.get("power") is True,
            ) and (current_target is not None
                   or reducing_command(self, cap, pending.get("service"),
                                       pending.get("data", {}), mode)
                   or approved_demand(self, spec, cfg, cap) is True)
            if not qualified:
                if current_target is not None:
                    self._status(spec, "within_target_band" if current_target["needed"] is False
                                 else "control_measurement_missing_or_stale")
                    return
                await self._pause(spec, "native_retry_demand_changed")
                return
        domain = entity.partition(".")[0]
        service = pending.get("service")
        if (not isinstance(service, str)
                or not self.hass.services.has_service(domain, service)):
            self._status(spec, "native_service_unavailable",
                         service=f"{domain}.{service}")
            return

        # Reserve the next attempt durably BEFORE dispatch. An interrupted
        # retry stays uncertain; it cannot silently replay across restart.
        previous_last = pending["last_attempt_at"]
        previous_attempt = dict(pending)
        reconnect_grant = pending.get("reconnect_retry_grant") is True
        pending["attempts"] += 1
        pending["last_attempt_at"] = now
        pending["phase"] = "retry_intent"
        pending.pop("retry_state_verified_at", None)
        if reconnect_grant:
            pending["reconnect_retry_grant"] = False
            pending["reconnect_retry_uses"] = (
                pending.get("reconnect_retry_uses", 0) + 1
            )
            pending["reconnect_retry_epoch_used"] = (
                getattr(self, "_native_reconnect_epoch", {}).get(entity)
            )
        await self._save()

        def still_safe() -> bool:
            current = self.hass.states.get(entity)
            if current is None or current.state in ("unknown", "unavailable"):
                return False
            if matches(current, pending["expected"]):
                return False  # Already ACKed while we yielded.
            if (pending.get("service") in ("set_temperature", "set_humidity")
                    and getattr(self, "_native_on_epoch", {}).get(entity) != before_on_epoch):
                return False
            latest = model.settings(self.manager, spec)
            refreshed = model.capabilities(self.manager, spec)
            if (record.get("pending") is not pending
                    or not self._active or not self._ready
                    or record.get("paused") or not self._current_spec(spec)
                    or not retry_settings_match(context["settings"], latest)
                    or refreshed is None
                    or asdict(refreshed) != record.get("capabilities")
                    or _manual_output_changes(before, snapshot(current))
                    or foreign_owner_hold(
                        self.hass, self.manager.entry.entry_id, entity)):
                return False
            if supply:
                relay_now = record.get("upstream", {})
                physical_supply = self.hass.states.get(supply)
                if (physical_supply is None or physical_supply.state != "on"
                        or relay_now.get("pending") or relay_now.get("paused")
                        or relay_now.get("owned") is not context.get("upstream_owned")):
                    return False
            latest_plan = model.plan_for(self.manager, spec)
            if (active_command
                    and not reducing_command(self, refreshed, pending["service"], pending["data"], mode)
                    and model.profile_name(latest, latest_plan) != context["profile"]):
                return False
            if policy_stop is not None and not self._stop_policy_verified(
                spec, refreshed, policy_stop
            ):
                return False
            if shutdown:
                return self._shutdown_allowed(spec, entity, pending["expected"])
            if self._gate(spec, refreshed, latest, latest_plan, mode,
                          automatic=automatic,
                          window_stop=pending.get("power") and mode == "off"):
                return False
            if pending.get("power") and not model.permission(
                self.manager, spec, refreshed
            )[1]:
                return False
            if active_command:
                from .equipment_power_switch import approved_demand
                return command_allowed(
                    self, spec, refreshed, pending["service"], pending["data"],
                    mode=mode, automatic=True, power=pending.get("power") is True,
                ) and (condition(self, spec, refreshed, mode, include_automatic=True) is not None
                       or reducing_command(self, refreshed, pending["service"], pending["data"], mode)
                       or approved_demand(self, spec, latest, refreshed) is True)
            return True

        try:
            async with self._commands:
                if (setpoint and enabled(model.settings(self.manager, spec))
                        and not await startup_ready(self, spec, cap, self.hass.states.get(entity))):
                    # Timing can be enabled during persistence or while the
                    # command semaphore is busy. No retry has run: preserve
                    # even an unused reconnect credit and wait for eligibility.
                    pending.clear()
                    pending.update(previous_attempt)
                    await self._save()
                    return
                if not still_safe():
                    # No second call occurred; leave the original command
                    # pending for a future ACK, but never retry stale intent.
                    pending.clear()
                    pending.update(previous_attempt)
                    await self._save()
                    if await suppress_obsolete_pending(self, spec, pending):
                        return
                    latest = model.settings(self.manager, spec)
                    if changed_automatic_policy(latest, model.plan_for(self.manager, spec)):
                        # The original journal was restored above. Re-evaluate
                        # its authority and reconcile the old feedback next tick.
                        return
                    why = command_profile_reason(
                        self, spec, cap, service, pending["data"], mode=mode,
                        automatic=automatic,
                        stop_target=pending.get("stop_target") is True,
                    )
                    if why:
                        self._status(spec, why, command_attempts=pending["attempts"])
                        return
                    if (condition(self, spec, cap, mode, include_automatic=True) is not None
                            and not command_allowed(
                                self, spec, cap, service, pending["data"],
                                mode=mode, automatic=automatic,
                                power=pending.get("power") is True,
                            )):
                        self._status(spec, "control_measurement_missing_or_stale")
                        return
                    if not matches(self.hass.states.get(entity), pending["expected"]):
                        await self._pause(spec, "native_retry_authority_or_state_changed")
                    return
                await asyncio.wait_for(
                    self.hass.services.async_call(
                        domain, service, pending["data"],
                        target={"entity_id": entity}, blocking=True,
                    ), timeout=20,
                )
            pending["phase"] = "commanded"
            await self._save()
            self._status(spec, "awaiting_physical_acknowledgement",
                         command_attempts=pending["attempts"],
                         command_retries_completed=pending["attempts"] - 1,
                         native_output_confirmed=False)
        except asyncio.CancelledError:
            raise
        except Exception:
            if self._ready:
                await self._pause(spec, "native_command_failed_or_uncertain")

    async def _send(self, spec: model.ManagedDevice, cap: model.Capabilities, entity: str,
                    service: str, data: dict, expected: dict, *, power: bool = False,
                    mode: str | None = None, automatic: bool = True,
                    shutdown: bool = False, policy_stop: str | None = None,
                    stop_target: bool = False, stop_finish: bool = False) -> bool:
        """Durable intent, exact target, live rechecks after *every* yield."""
        record = self._record(spec)
        if record.get("pending") or record.get("paused"):
            return False
        if record.get("native_setpoint_stop") and not (stop_target or stop_finish):
            self._status(spec, "native_setpoint_shutdown_blocked",
                         reason="shutdown_sequence_in_progress")
            return False
        primary = self.hass.states.get(cap.primary)
        if primary is None:
            return False
        cfg = model.settings(self.manager, spec)
        plan = model.plan_for(self.manager, spec)
        action_mode = mode or primary.state
        from .equipment_setpoint_sequence import (
            enabled, finish_authorized, mark_target_sent, retry_settings_match,
            startup_ready, supports_stop, target_authorized,
        )
        plain_binary_off = (power and not stop_finish and action_mode == "off"
                            and supports_stop(cap, primary))
        if plain_binary_off and enabled(cfg):
            # Re-evaluate through _power to start the newly opted-in stop.
            self._status(spec, "authority_or_evidence_changed_before_dispatch")
            return False
        if service in ("set_temperature", "set_humidity"):
            if not await startup_ready(self, spec, cap, primary):
                return False
        if stop_target and (
            service != "set_temperature" or power or action_mode != "off"
            or not target_authorized(self, spec, cap, entity, data, expected)
        ):
            self._status(spec, "native_setpoint_shutdown_blocked",
                         reason="shutdown_target_authority_changed")
            return False
        if stop_finish and (
            service != "set_hvac_mode" or not power or action_mode != "off"
            or data != {"hvac_mode": "off"} or expected != {"state": "off"}
            or not finish_authorized(self, spec, cap, entity)
        ):
            self._status(spec, "native_setpoint_shutdown_blocked",
                         reason="shutdown_finish_authority_changed")
            return False
        if policy_stop is not None:
            if (policy_stop not in ("sleep", "idle", "window", "target")
                    or not (power or stop_target) or action_mode != "off"
                    or not self._stop_policy_verified(spec, cap, policy_stop)):
                self._status(spec, "authority_or_evidence_changed_before_dispatch")
                return False
        if shutdown:
            if not self._shutdown_allowed(
                spec, entity, {"state": "off"} if stop_target else expected
            ):
                self._status(spec, "owned_shutdown_identity_or_dwell_hold")
                return False
        elif why := self._gate(spec, cap, cfg, plan, action_mode, automatic=automatic,
                              window_stop=(power or stop_target) and action_mode == "off"):
            self._status(spec, why)
            return False
        from .equipment_pid_safety import (
            command_allowed, command_profile_reason, condition, remember_cutoff,
        )
        if not command_allowed(
            self, spec, cap, service, data, mode=action_mode,
            automatic=automatic, power=power, stop_target=stop_target,
        ):
            current_target = condition(self, spec, cap, action_mode, include_automatic=True)
            await remember_cutoff(self, spec, condition(self, spec, cap, action_mode))
            why = command_profile_reason(
                self, spec, cap, service, data, mode=action_mode, automatic=automatic,
                stop_target=stop_target,
            )
            self._status(spec, why or ("within_target_band" if current_target
                         and current_target["needed"] is False
                         else "control_measurement_missing_or_stale"))
            return False
        if entity not in spec.source_entities or entity_area(self.hass, entity) != spec.area_id:
            return False
        domain = entity.partition(".")[0]
        if not self.hass.services.has_service(domain, service):
            self._status(spec, "native_service_unavailable", service=f"{domain}.{service}")
            return False
        target_budget = record.get("unconfirmed_native_target")
        budget_retry = False
        previous_budget = None
        reserved_budget = None
        reconnect_epoch = None
        same_target = (
            not stop_target
            and isinstance(target_budget, dict)
            and (not power or target_budget.get("pid_target_satisfied") is True)
            and (service == "set_temperature"
                 or target_budget.get("pid_target_satisfied") is True)
            and all(target_budget.get(key) == value for key, value in (
                ("entity", entity), ("service", service),
                ("data", data), ("expected", expected),
            ))
        )
        invalid_budget = (service == "set_temperature" and not power and not stop_target
                          and target_budget is not None
                          and not isinstance(target_budget, dict))
        verified_retry = bool(
            same_target and target_budget.get("phase") == "retry_intent"
            and type(target_budget.get("retry_state_verified_at")) in (int, float)
            and (last := finite(target_budget.get("last_attempt_at"), 0, self.clock())) is not None
            and finite(target_budget["retry_state_verified_at"], last, self.clock()) is not None
        )
        if (same_target and (
                target_budget.get("pid_target_satisfied") is True
                and target_budget.get("phase") == "commanded" or verified_retry)
                and type(target_budget.get("attempts")) is int
                and 1 <= target_budget["attempts"] < NATIVE_COMMAND_MAX_ATTEMPTS
                and isinstance(target_budget.get("retry_context"), dict)
                and retry_settings_match(target_budget["retry_context"].get("settings"), cfg)):
            # Demand returned before physical OFF, or an interrupted retry
            # was reconciled against stable current state. Continue the SAME
            # command's remaining budget; neither event grants attempt one.
            resumed = deepcopy(target_budget)
            resumed.pop("pid_target_satisfied", None)
            record["pending"] = resumed
            record.pop("unconfirmed_native_target", None)
            await self._save()
            await self._retry_pending(spec, resumed, self.clock())
            return True
        if same_target or invalid_budget:
            # This is still the SAME exhausted target after read-only
            # reconciliation. OFF and genuinely different requests bypass
            # this budget; a timer or stable native mismatch cannot reset it.
            now = self.clock()
            attempts = target_budget.get("attempts") if same_target else None
            used = target_budget.get("reconnect_retry_uses", 0) if same_target else None
            first = finite(target_budget.get("when"), 0, now) if same_target else None
            last = finite(target_budget.get("last_attempt_at"), 0, now) if same_target else None
            reconnect_epoch = finite(
                getattr(self, "_native_reconnect_epoch", {}).get(entity), 0, now
            )
            context = target_budget.get("retry_context") if same_target else None
            settle_fn = getattr(self, "_native_settle_remaining", None)
            budget_retry = bool(
                same_target and type(attempts) is int
                and NATIVE_COMMAND_MAX_ATTEMPTS <= attempts < (
                    NATIVE_COMMAND_MAX_ATTEMPTS + NATIVE_RECONNECT_EXTRA_ATTEMPTS
                )
                and type(used) is int and 0 <= used < NATIVE_RECONNECT_EXTRA_ATTEMPTS
                and first is not None and last is not None and first <= last
                and reconnect_epoch is not None and reconnect_epoch > last
                and reconnect_epoch != target_budget.get("reconnect_retry_epoch_used")
                and now - reconnect_epoch >= NATIVE_RECONNECT_SETTLE_SECONDS
                and now - last >= NATIVE_COMMAND_RETRY_SECONDS
                and isinstance(context, dict) and retry_settings_match(context.get("settings"), cfg)
                and callable(settle_fn) and settle_fn(spec) == 0
                and self._identity_ok(spec)
            )
            if not budget_retry:
                self._status(
                    spec, "awaiting_physical_acknowledgement",
                    reason="previous_command_not_yet_confirmed",
                    command_attempts=attempts,
                    command_retries_completed=(max(0, attempts - 1)
                                               if type(attempts) is int else None),
                    native_output_confirmed=False,
                )
                return False
            previous_budget = deepcopy(target_budget)
        before_settings = deepcopy(self.manager.settings)
        before_plan = deepcopy(plan)
        before_sources = {e: snapshot(self.hass.states.get(e)) for e in spec.source_entities}
        before_on_epoch = getattr(self, "_native_on_epoch", {}).get(entity)
        before_feedback = self.measurements(spec, cap) if automatic else None
        before_quiet = self._quiet_context(spec, cfg, plan)
        if shutdown:
            owned = record["power"][entity]
            min_on, max_on = owned["min_on"], owned["max_on"]
        else:
            min_on, _, max_on = model.timing(self.manager, spec, cap)
        record["baseline"].setdefault(entity, before_sources[entity])
        record["capabilities"] = asdict(cap)
        pending = {"entity": entity, "service": service, "data": data,
                   "expected": expected, "power": power, "output_on": not (
                       expected.get("state") == "off" or service == "set_value" and data.get("value") == 0),
                   "phase": "intent", "when": self.clock(), "min_on": min_on, "max_on": max_on,
                   "attempts": 1, "retry_context": {
                       "settings": deepcopy(cfg),
                       "profile": (model.profile_name(cfg, plan)
                                   if automatic and hasattr(model, "profile_name")
                                   else None),
                       "automatic": automatic, "mode": action_mode,
                       "shutdown": shutdown, "policy_stop": policy_stop,
                       "upstream_owned": record.get("upstream", {}).get("owned"),
                   }}
        if stop_target or stop_finish:
            pending.update(
                stop_target=stop_target, stop_finish=stop_finish,
                stop_sequence_at=record["native_setpoint_stop"]["requested_at"],
            )
            retry = record["native_setpoint_stop"].get("off_retry_budget")
            if stop_finish and isinstance(retry, dict):
                pending.update(
                    attempts=retry["attempts"] + 1, when=retry["when"],
                    reconnect_retry_uses=retry.get("reconnect_retry_uses", 0),
                    reconnect_retry_epoch_used=retry.get("reconnect_retry_epoch_used"),
                )
        if budget_retry:
            pending.update(
                when=previous_budget["when"],
                attempts=previous_budget["attempts"] + 1,
                last_attempt_at=self.clock(),
                reconnect_retry_uses=previous_budget.get("reconnect_retry_uses", 0) + 1,
                reconnect_retry_epoch_used=reconnect_epoch,
            )
            # Reserve the old budget durably before dispatch, including an
            # uncertain interrupted intent. A restart cannot turn attempt 5
            # into a new four-attempt command. A proven pre-send abort below
            # restores the old budget because no actuator command occurred.
            reserved_budget = deepcopy(pending)
            record["unconfirmed_native_target"] = reserved_budget
        record["pending"] = pending
        await self._save()

        def current() -> bool:
            if (not self._active or not self._ready or record.get("paused")
                    or record.get("pending") is not pending):
                return False
            if budget_retry and (
                record.get("unconfirmed_native_target") is not reserved_budget
                or self._native_settle_remaining(spec) != 0
                or getattr(self, "_native_reconnect_epoch", {}).get(entity) != reconnect_epoch
            ):
                return False
            if any(snapshot(self.hass.states.get(e)) != previous for e, previous in before_sources.items()):
                return False
            if getattr(self, "_native_on_epoch", {}).get(entity) != before_on_epoch:
                return False
            if (policy_stop is not None
                    and not self._stop_policy_verified(spec, cap, policy_stop)):
                return False
            if plain_binary_off and enabled(model.settings(self.manager, spec)):
                # Owned shutdown normally survives settings changes, but an
                # undispatched direct OFF must now use the selected sequence.
                return False
            if stop_target and not target_authorized(
                self, spec, cap, entity, data, expected
            ):
                return False
            if stop_finish and not finish_authorized(self, spec, cap, entity):
                return False
            if shutdown:
                return self._shutdown_allowed(
                    spec, entity, {"state": "off"} if stop_target else expected
                )
            if not command_allowed(
                self, spec, cap, service, data, mode=action_mode,
                automatic=automatic, power=power, stop_target=stop_target,
            ):
                return False
            latest = model.settings(self.manager, spec)
            latest_plan = model.plan_for(self.manager, spec)
            return bool(self._current_spec(spec) and self.manager.settings == before_settings
                and model.capabilities(self.manager, spec) == cap and latest_plan == before_plan
                and (not automatic or self.measurements(spec, cap) == before_feedback)
                and self._quiet_context(spec, latest, latest_plan) == before_quiet
                and not self._gate(spec, cap, latest, latest_plan, action_mode, automatic=automatic,
                                   window_stop=(power or stop_target) and action_mode == "off"))

        async def abort() -> bool:
            self._invalidated.add(spec.identifier)
            if record.get("pending") is pending:
                record["pending"] = None  # Dispatch has NOT happened; no uncertainty.
            if budget_retry and record.get("unconfirmed_native_target") is reserved_budget:
                record["unconfirmed_native_target"] = previous_budget
            await self._save()
            if automatic and action_mode != "off":
                await remember_cutoff(self, spec, condition(self, spec, cap, action_mode))
            why = command_profile_reason(
                self, spec, cap, service, data, mode=action_mode, automatic=automatic,
                stop_target=stop_target,
            )
            self._status(spec, why or "authority_or_evidence_changed_before_dispatch")
            return False

        if not current():
            return await abort()
        try:
            async with self._commands:
                if not current():
                    return await abort()
                await asyncio.wait_for(self.hass.services.async_call(domain, service, data,
                    target={"entity_id": entity}, blocking=True), timeout=20)
            pending["phase"] = "commanded"
            pending["last_attempt_at"] = self.clock()
            if stop_target:
                mark_target_sent(self, spec, pending["last_attempt_at"])
            if budget_retry and record.get("unconfirmed_native_target") is reserved_budget:
                reserved_budget.update(deepcopy(pending))
            await self._save()
            self._status(spec, "command_sent", entity_id=entity, service=service,
                         command_attempts=pending["attempts"])
            return True
        except asyncio.CancelledError:
            raise  # Persisted intent is deliberately retained.
        except Exception:
            if self._ready:
                await self._pause(spec, "native_command_failed_or_uncertain")
            return False

    async def _power(self, spec: model.ManagedDevice, cap: model.Capabilities,
                     desired: str, *, automatic: bool, shutdown: bool = False,
                     policy_stop: str | None = None) -> bool:
        state = self.hass.states.get(cap.primary)
        if state is None or state.state in ("unknown", "unavailable"):
            return False
        if desired not in cap.modes or "off" not in cap.modes:
            self._status(spec, "native_power_mode_unsupported")
            return False
        _, granted = model.permission(self.manager, spec, cap)
        record, now = self._record(spec), self.clock()
        owned = record.get("power", {}).get(cap.primary)
        if not granted and not (shutdown and owned):
            self._status(spec, "power_control_not_commissioned")
            return False
        proportional = cap.domain in ("number", "input_number")
        target_state = ("0.0" if desired == "off" else "100.0") if proportional else (
            desired if cap.domain == "climate" else "off" if desired == "off" else "on")
        if matches(state, {"state": target_state}):
            return False
        if state.attributes.get("hvac_action") == "defrosting":
            self._status(spec, "native_defrost_protection")
            return False
        if shutdown and owned:
            on_min, off_min, maximum = owned["min_on"], 600, owned["max_on"]
        else:
            on_min, off_min, maximum = model.timing(self.manager, spec, cap)
            if owned:
                on_min = max(on_min, owned["min_on"])
        if not output_off(state):
            if desired != "off":
                # Heat->cool is ALWAYS OFF, full dwell, then new mode.
                desired, target_state = "off", "0.0" if proportional else "off"
            stamp = owned.get("since") if owned else None
            if stamp is None:
                changed = getattr(state, "last_changed", None)
                stamp = changed.timestamp() if changed is not None else record.setdefault("on_seen", {}).setdefault(cap.primary, now)
            if not 0 <= now-stamp or now-stamp < on_min:
                self._status(
                    spec, "minimum_on_hold",
                    minimum_on_remaining_seconds=(
                        round(max(0, on_min - (now - stamp)))
                        if 0 <= now-stamp else None
                    ),
                    minimum_on_until=(
                        stamp + on_min if 0 <= now-stamp else None
                    ),
                    native_state=state.state,
                )
                return False
        else:
            relay = record.get("upstream", {})
            wake = relay.get("native_wake") if isinstance(relay, dict) else None
            try:
                live_native_stamp = finite(
                    state.last_changed.timestamp(), 0, now
                )
            except (AttributeError, TypeError, ValueError, OverflowError):
                live_native_stamp = None
            certified = (
                isinstance(wake, dict) and wake.get("reconciled") is True
                and wake.get("native_state") == "off"
                and live_native_stamp is not None
                and live_native_stamp == wake.get("native_off_stamp")
                and relay.get("owned") is True
                and relay.get("on_at") == wake.get("on_at")
                and model.settings(self.manager, spec).get("power_switch_entity")
                    == relay.get("entity")
                and finite(wake.get("off_at"), 0, now) is not None
            )
            if certified:
                # This OFF existed continuously while the dedicated HEM-owned
                # supply itself was disconnected. HA rediscovery cannot
                # invalidate a *completed* physical OFF interval.
                stamp = max(
                    finite(record["off_at"].get(cap.primary), 0, now) or 0,
                    float(wake["off_at"]),
                )
            else:
                changed = getattr(state, "last_changed", None)
                try:
                    observed = changed.timestamp() if changed is not None else None
                except (AttributeError, TypeError, ValueError, OverflowError):
                    observed = None
                observed = finite(observed, 0, 1e13)
                stamp = record["off_at"].get(cap.primary)
                if stamp is None:
                    stamp = observed if observed is not None and observed <= now else now
                elif observed is not None and stamp < observed <= now:
                    # A true later native OFF still creates a new dwell.
                    stamp = observed
            record["off_at"][cap.primary] = stamp
            if not 0 <= now-stamp or now-stamp < off_min:
                self._status(
                    spec, "minimum_off_hold",
                    minimum_off_remaining_seconds=(
                        round(max(0, off_min - (now - stamp)))
                        if 0 <= now-stamp else None
                    ),
                    minimum_off_until=(
                        stamp + off_min if 0 <= now-stamp else None
                    ),
                    native_state=state.state,
                )
                return False
        if desired == "off":
            from .equipment_setpoint_sequence import begin_stop, enabled, supports_stop
            if enabled(model.settings(self.manager, spec)) and supports_stop(cap, state):
                return await begin_stop(
                    self, spec, cap, automatic=automatic, shutdown=shutdown,
                    policy_stop=policy_stop,
                )
        if proportional:
            attrs = state.attributes
            if attrs.get("unit_of_measurement") != "%" or attrs.get("min") != 0 or attrs.get("max") != 100:
                self._status(spec, "proportional_output_not_verified")
                return False
            service, data = "set_value", {"value": float(target_state)}
        else:
            service = "set_hvac_mode" if cap.domain == "climate" else "turn_off" if desired == "off" else "turn_on"
            data = {"hvac_mode": desired} if cap.domain == "climate" else {}
        return await self._send(spec, cap, cap.primary, service, data, {"state": target_state},
                                power=True, mode=desired, automatic=automatic,
                                shutdown=shutdown, policy_stop=policy_stop)

    async def _native_target(self, spec: model.ManagedDevice, cap: model.Capabilities,
                             mode: str, targets: dict, demand: float | None, automatic: bool) -> bool | None:
        """Return True if sent, False if skipped, None for a blocked binary target."""
        state = self.hass.states.get(cap.primary)
        if state is None or state.state == "off":
            return False
        if cap.domain in ("climate", "humidifier"):
            from .equipment_setpoint_sequence import startup_ready
            if not await startup_ready(self, spec, cap, state):
                return None
        config = model.settings(self.manager, spec)
        limits = model.device_limits(self.manager, spec, cap)
        plan = model.plan_for(self.manager, spec)
        profile = model.profile_name(config, plan)
        if automatic:
            # An alarm/profile can change while tick persists PID evidence or
            # waits for native startup. Do not attach the old Sleep target
            # to a newly refreshed wake plan at the dispatch boundary.
            targets = model.targets(self.manager, spec, cap, config, plan)
        manual_humidity = not automatic and "humidity" in config.get("profile_targets", {}).get(profile, {})
        # For genuinely binary climate regulation, the physical HVAC mode is
        # HEM's actuator. A native thermostat setpoint close to the room goal
        # would fight the ON period. Drive the verified full heating/cooling
        # limit while commanded ON, including devices with a manual preset.
        # Offering such a preset does not mean it is selected or that the
        # appliance's own thermostat has stopped limiting its output.
        binary_full_output = (
            automatic and cap.domain == "climate"
            and config["control_mode"] in ("automatic", "pid")
            and mode in ("heat", "cool")
            and cap.temperature and model.permission(self.manager, spec, cap)[1]
        )
        if binary_full_output:
            # The binary controller owns output timing. While the native mode is
            # positively observed ON, force the device's *reported* extremum,
            # not a room comfort/setpoint limit. Treat the physical entity's
            # native target range as authoritative for this actuator.
            # A set_temperature while OFF can implicitly activate hardware.
            if state.state != mode or not model.features(state) & model.TEMP:
                return False
            attrs = state.attributes
            native_low = finite(attrs.get("min_temp"), -30, 140)
            native_high = finite(attrs.get("max_temp"), -29, 150)
            if (native_low is None or native_high is None
                    or native_low >= native_high):
                self._status(spec, "physical_capabilities_unavailable")
                return None
            # HA exposes these bounds in the same unit accepted by its
            # set_temperature service. Copy the exact reported endpoint:
            # older HA states omit temperature_unit, and target_temp_step is
            # optional. Neither metadata field is needed for this operation.
            # Rounding a bound to a step can also move it away from the
            # device's actual maximum/minimum (or outside its valid range).
            value = native_high if mode == "heat" else native_low
            actual = finite(attrs.get("temperature"), -30, 150)
            if actual is None:
                self._status(spec, "native_setpoint_unavailable")
                return None
            if abs(value - actual) < .05:
                return False
            # Durable single-command, native ACK, consent and room safety
            # gates are enforced by the existing _send implementation.
            sent = await self._send(
                spec, cap, cap.primary, "set_temperature",
                {"temperature": value}, {"attributes": {"temperature": value}},
                automatic=automatic,
            )
            if sent:
                self._record(spec)["target_at"] = self.clock()
            # Preserve a dispatch blocker instead of falling through to a
            # misleading "controlling" status when the target was not sent.
            return True if sent else None
        if cap.domain == "humidifier" or cap.humidity and (mode == "dry" or manual_humidity):
            if cap.domain == "climate" and not (model.features(state) & model.HUMIDITY):
                return False
            value = round(max(limits["humidity_min_limit"],
                              min(limits["humidity_max_limit"], targets["humidity"])))
            if automatic:
                actual = finite(state.attributes.get("humidity"), 0, 100)
                if actual is None:
                    return False
                outside_soft_limit = not limits["humidity_min_limit"] <= actual <= limits["humidity_max_limit"]
                if not outside_soft_limit:
                    value = round(max(actual-5, min(actual+5, value)))
                value = round(max(limits["humidity_min_limit"],
                                  min(limits["humidity_max_limit"], value)))
                if self.clock()-self._record(spec).get("target_at", 0) < model.settings(self.manager, spec)["sample_seconds"]:
                    return False
            if not cap.min_humidity <= value <= cap.max_humidity:
                self._status(spec, "target_outside_native_limits")
                return False
            if finite(state.attributes.get("humidity"), 0, 100) == value:
                return False
            sent = await self._send(spec, cap, cap.primary, "set_humidity", {"humidity": value},
                {"attributes": {"humidity": value}}, automatic=automatic)
            if sent:
                self._record(spec)["target_at"] = self.clock()
            return sent
        if cap.domain != "climate" or mode not in ("heat", "cool", "heat_cool", "auto"):
            return False
        unit = state.attributes.get("temperature_unit")
        if mode == "heat_cool" and cap.temperature_range:
            data = {"target_temp_low": target_to_unit(targets["heat"], unit),
                    "target_temp_high": target_to_unit(targets["cool"], unit)}
        elif cap.temperature and model.features(state) & model.TEMP:
            target = (
                limits["temperature_max_limit"] if mode == "heat"
                else limits["temperature_min_limit"]
            ) if binary_full_output else targets["cool" if mode == "cool" else "heat"]
            if demand is not None and not binary_full_output:
                # Setpoint-only PID never gains compressor-cycle permissions.
                target += (1 if mode == "heat" else -1) * 1.5 * demand / 100
            target = max(limits["temperature_min_limit"],
                         min(limits["temperature_max_limit"], target))
            data = {"temperature": target_to_unit(target, unit)}
        else:
            return False
        for key, value in data.items():
            if value is None:
                self._status(spec, "unsupported_temperature_unit")
                return False
            actual = finite(state.attributes.get(key), -50, 150)
            if actual is None:
                self._status(spec, "native_setpoint_unavailable")
                return False
            desired_c = target_from_unit(value, unit)
            actual_c = target_from_unit(actual, unit)
            if desired_c is None or actual_c is None:
                self._status(spec, "unsupported_temperature_unit")
                return False
            soft_min, soft_max = limits["temperature_min_limit"], limits["temperature_max_limit"]
            desired_c = max(soft_min, min(soft_max, desired_c))
            value = target_to_unit(desired_c, unit)
            outside_soft_limit = not soft_min <= actual_c <= soft_max
            if automatic and not outside_soft_limit and not binary_full_output:
                delta = .5 if unit in ("°C", "C") else .9
                value = max(actual-delta, min(actual+delta, value))
            native_min = target_to_unit(soft_min, unit)
            native_max = target_to_unit(soft_max, unit)
            if native_min is None or native_max is None:
                return False
            try:
                physical_min = float(state.attributes.get("min_temp", native_min))
                physical_max = float(state.attributes.get("max_temp", native_max))
            except (TypeError, ValueError):
                physical_min, physical_max = native_min, native_max
            value = quantize_target(
                value, state.attributes.get("target_temp_step", .5),
                max(physical_min, native_min), min(physical_max, native_max))
            if value is None:
                return False
            final_c = target_from_unit(value, unit)
            if final_c is None or not soft_min-1e-6 <= final_c <= soft_max+1e-6:
                self._status(spec, "target_outside_device_limits")
                return False
            if automatic and not binary_full_output and not outside_soft_limit and abs(final_c-actual_c) > .500001:
                self._status(spec, "native_step_exceeds_setpoint_rate_limit")
                return False
            data[key] = value
        if all(abs(float(state.attributes.get(k))-v) < .05 for k, v in data.items()):
            return False
        record = self._record(spec)
        # Sampling applies to trim/setpoint writes too, not merely PID math.
        if automatic and self.clock()-record.get("target_at", 0) < model.settings(self.manager, spec)["sample_seconds"]:
            return False
        sent = await self._send(spec, cap, cap.primary, "set_temperature", data,
                                {"attributes": data}, automatic=automatic)
        if sent:
            record["target_at"] = self.clock()
        return sent

    async def _fan(self, spec: model.ManagedDevice, cap: model.Capabilities,
                   cfg: dict, plan: dict, demand: float | None, automatic: bool,
                   measured_capacity_speed: str | int | None = None) -> bool:
        if not cap.fan_entity or not cap.fan_modes:
            return False
        state = self.hass.states.get(cap.fan_entity)
        if state is None or state.state == "off":
            return False  # Quiet mode never powers an appliance on.
        record = self._record(spec)
        attribute = "percentage" if cap.fan_percentage else "fan_mode" if cap.fan_entity.startswith("climate.") else "preset_mode"
        observed = state.attributes.get(attribute)
        if observed is None:
            return False
        record.setdefault("normal_fan", observed)
        selected_fan = cfg.get("profile_fans", {}).get(model.profile_name(cfg, plan)) or cfg.get("fan_mode")
        normal = selected_fan or str(record["normal_fan"])
        if cap.fan_percentage:
            dev = model.device_config(self.manager, spec, cap.primary)
            normal = selected_fan or dev.get("fan_speed_percent") or normal
            if measured_capacity_speed is not None:
                normal = measured_capacity_speed
            elif demand is not None and automatic and cfg["control_mode"] == "pid":
                planned = fan_speed_for_pid(
                    demand, modes=cap.fan_modes, percentage=True,
                    min_percentage=model.device_limits(self.manager, spec, cap)["fan_min_percentage"],
                    max_percentage=model.device_limits(self.manager, spec, cap)["fan_max_percentage"],
                )
                if planned is not None:
                    normal = planned
            quiet_state = self._quiet_context(spec, cfg, plan) if automatic else False
            if quiet_state is None:
                self._status(spec, "quiet_context_unknown")
                return True  # handled hold: do not overwrite status or change speed
            quiet = quiet_state is True
            limits = model.device_limits(self.manager, spec, cap)
            value = max(limits["fan_min_percentage"],
                        min(limits["fan_max_percentage"], float(normal)))
            if quiet:
                quiet_value = max(limits["fan_min_percentage"],
                                  min(limits["fan_max_percentage"], cfg["quiet_percentage"]))
                value = min(value, quiet_value)
            valid = [int(v) for v in cap.fan_modes
                     if limits["fan_min_percentage"] <= int(v) <= limits["fan_max_percentage"]]
            if not valid:
                self._status(spec, "fan_limits_have_no_supported_step")
                return False
            if quiet:
                lower = [v for v in valid if v <= value]
                value = max(lower) if lower else min(valid)
            else:
                value = min(valid, key=lambda v: abs(v-value))
            service, data, expected = "set_percentage", {"percentage": value}, {"attributes": {attribute: value}}
        else:
            quiet_state = self._quiet_context(spec, cfg, plan) if automatic else False
            if quiet_state is None:
                self._status(spec, "quiet_context_unknown")
                return True  # handled hold: do not overwrite status or change speed
            quiet = quiet_state is True
            low = cfg.get("quiet_fan_mode") or ("low" if "low" in cap.fan_modes else None)
            value = low if quiet and low is not None else normal
            if measured_capacity_speed is not None and measured_capacity_speed in cap.fan_modes:
                value = measured_capacity_speed
            # Map the same PID demand to Low/Medium/High ONLY where the
            # physical source advertises an unambiguous ordered speed set.
            # Arbitrary native presets keep their saved profile/normal speed.
            if (measured_capacity_speed is None and automatic and cfg["control_mode"] == "pid"
                    and demand is not None and demand > 0):
                chosen = fan_speed_for_pid(
                    demand, modes=cap.fan_modes, percentage=False,
                    quiet=quiet, quiet_mode=low,
                )
                if chosen is not None:
                    value = chosen
            if value not in cap.fan_modes:
                return False
            service = "set_fan_mode" if cap.fan_entity.startswith("climate.") else "set_preset_mode"
            key = "fan_mode" if service == "set_fan_mode" else "preset_mode"
            data, expected = {key: value}, {"attributes": {attribute: value}}
        if observed == value:
            return False
        return await self._send(spec, cap, cap.fan_entity, service, data, expected, automatic=automatic)

    async def _apply_queued_power_switch(self, spec: model.ManagedDevice) -> bool:
        """Commit a user's saved supply preference only after safe release.

        Returns True when a preference was committed. Existing native output
        and upstream relay ownership are never cleared here and no physical
        service is called. The old supply remains authoritative until HEM
        has independently completed its safe OFF/ACK/dwell process.
        """
        record = self._record(spec)
        queued = record.get("queued_power_switch")
        if not isinstance(queued, dict):
            return False
        if not self._current_spec(spec) or not self._ready:
            return False
        upstream = record.get("upstream", {})
        if (record.get("pending") or record.get("power")
                or isinstance(upstream, dict) and (
                    upstream.get("pending") or upstream.get("owned")
                )):
            return False
        if (queued.get("area") != spec.area_id
                or queued.get("source_device_id") != spec.source_device_id):
            self._status(spec, "awaiting_evaluation",
                         reason="queued_supply_source_identity_changed")
            return False
        old = model.settings(self.manager, spec).get("power_switch_entity")
        selected = queued.get("requested")
        if old != queued.get("original"):
            self._status(spec, "awaiting_evaluation",
                         reason="queued_supply_configuration_changed")
            return False
        from .equipment_power_switch import permitted_supply
        if selected is not None and permitted_supply(
            self.manager, spec, selected
        ) is None:
            self._status(spec, "awaiting_evaluation",
                         reason="queued_supply_no_longer_available")
            return False
        lock = getattr(self.manager, "_device_settings_write_lock", None)
        if lock is None:
            lock = self.manager._device_settings_write_lock = asyncio.Lock()
        async with lock:
            current = model.settings(self.manager, spec)
            if (not self._current_spec(spec)
                    or current.get("power_switch_entity") != old
                    or record.get("pending") or record.get("power")
                    or (record.get("upstream") or {}).get("pending")
                    or (record.get("upstream") or {}).get("owned")
                    or (selected is not None and permitted_supply(
                        self.manager, spec, selected
                    ) is None)):
                return False
            options = deepcopy(self.manager.entry.options)
            profiles = deepcopy(self.manager.settings.get(model.SETTINGS, {}))
            profiles = profiles if isinstance(profiles, dict) else {}
            saved = profiles.get(spec.identifier, {})
            saved = saved if isinstance(saved, dict) else {}
            profiles[spec.identifier] = {
                **saved, "power_switch_entity": selected,
            }
            options[model.SETTINGS] = profiles
            self.hass.config_entries.async_update_entry(
                self.manager.entry, options=options,
            )
        record.pop("queued_power_switch", None)
        await self._save()
        self._status(spec, "settings_updated",
                     reason="queued_supply_applied_after_safe_release",
                     settings_saved=True)
        return True

    def observe_native_availability(
        self, entity_id: str, old: Any, new: Any,
    ) -> None:
        """Observe exact native HA offline→online; never infer physical ACK.

        No service calls, database queries or controller reconfiguration.
        The HA event timestamp begins the settle window, avoiding an extra
        full polling interval after a genuine reconnection.
        """
        if not isinstance(entity_id, str):
            return
        live = lambda item: (
            item is not None
            and getattr(item, "state", None) not in (
                None, "unavailable", "unknown"
            )
        )
        if (entity_id.startswith(("climate.", "humidifier."))
                and live(old) and live(new)
                and old.state == "off" and new.state != "off"):
            # Capture an actual OFF->ON before manager refreshes coalesce.
            # A hidden OFF/ON during a Store save must invalidate that write,
            # even when its final snapshot equals the old running state.
            epochs = getattr(self, "_native_on_epoch", None)
            if epochs is None:
                epochs = self._native_on_epoch = {}
            epochs[entity_id] = self.clock()
        if not live(new):
            self._native_ready_since.pop(entity_id, None)
            return
        if not live(old):
            stamp = self.clock()
            self._native_ready_since[entity_id] = stamp
            # Only a genuine known OFFLINE→ONLINE edge (not the first HA
            # registration or the integration starting) grants one bounded
            # recovery opportunity to a previously exhausted command.
            if old is not None:
                self._native_reconnect_epoch[entity_id] = stamp

    def _native_settle_remaining(
        self, spec: model.ManagedDevice,
    ) -> float | None:
        """None = absent/unknown; positive = startup settling; zero = ready.

        Native output is still checked against live identity, capability,
        physical safety and the old command ACK before any new write.
        """
        now = self.clock()
        remaining = 0.0
        for entity in spec.source_entities:
            state = self.hass.states.get(entity)
            if state is None or state.state in ("unavailable", "unknown"):
                self._native_ready_since.pop(entity, None)
                return None
            since = self._native_ready_since.get(entity)
            if since is None or not 0 <= now - since:
                since = now
                self._native_ready_since[entity] = now
            remaining = max(
                remaining,
                NATIVE_RECONNECT_SETTLE_SECONDS - (now - since)
            )
        return max(0.0, remaining)

    def _automatic_recovery_gate(self, spec: model.ManagedDevice) -> dict:
        """Read-only: verify current state before resuming ordinary control.

        An online entity or two stable observations are not a command ACK.
        Automatic Resume preserves an unconfirmed exhausted target budget
        separately, so normal shutdown policies remain reachable afterwards.
        """
        if not self._current_spec(spec):
            return {"ready": False, "reason": "source_deselected_or_moved"}
        settle = self._native_settle_remaining(spec)
        if settle is None:
            return {"ready": False, "reason": "native_source_unavailable"}
        if settle > 0:
            return {
                "ready": False,
                "reason": "native_reconnected_settling",
                "remaining_seconds": round(settle),
            }
        record = self._record(spec)
        pending = record.get("pending")
        if pending:
            evidence = self.resume_information(spec) or {}
            decision = evidence.get("decision")
            # On restart, an interrupted intent may never have been sent.
            # It cannot spontaneously become a native ACK. But the EXISTING
            # read-only Resume verifier can take two stable independent
            # observations (>=60s, after >=120s from original command) and
            # reconcile the *reported current state* without inventing a
            # completed actuator command. Start that verifier automatically:
            # the previously selected PID/Automatic is already user consent.
            if decision not in (
                "confirmed", "verified", "first_check",
                "second_check_wait", "settling",
            ):
                return {
                    "ready": False,
                    "reason": "previous_command_evidence_invalid",
                    "requested_native_state": evidence.get("requested"),
                    "observed_native_state": evidence.get("observed"),
                }
        relay = record.get("upstream", {})
        supply_pending = (
            relay.get("pending") if isinstance(relay, dict) else None
        )
        if supply_pending:
            supply = self.hass.states.get(relay.get("entity"))
            if (not isinstance(supply_pending, dict)
                    or supply_pending.get("phase") != "commanded"
                    or supply is None
                    or supply.state != supply_pending.get("desired")):
                return {
                    "ready": False,
                    "reason": "upstream_switch_command_not_yet_confirmed",
                }
        return {"ready": True}

    def _schedule_automatic_reconciliation(self, spec: model.ManagedDevice) -> None:
        """Run the existing no-command Resume verifier outside the tick lock.

        User settings stay persisted even if physical feedback arrives late.
        This task NEVER clears a pending command on a timer or assumes that
        an online entity proves a native command completed.
        """
        tasks = getattr(self, "_automatic_recovery_tasks", None)
        if tasks is None:
            tasks = self._automatic_recovery_tasks = {}
        current = tasks.get(spec.identifier)
        if current is not None and not current.done():
            return
        task = self.hass.async_create_task(
            self._apply_automatic_reconciliation(spec)
        )
        tasks[spec.identifier] = task
        task.add_done_callback(
            lambda finished, key=spec.identifier, active=tasks: (
                active.pop(key, None)
                if active.get(key) is finished else None
            )
        )

    async def _retry_after_verified_reconnect(
        self, spec: model.ManagedDevice,
    ) -> bool:
        """Resume a bounded native retry, only for a genuine new HA reconnect.

        Never replay an obsolete command after the user changed settings, nor
        clear uncertain intents, force an OFF/ON cycle, or adopt an unowned
        output. The original _retry_pending still validates all safety gates.
        """
        record = self._record(spec)
        pending = record.get("pending")
        if (not isinstance(pending, dict)
                or pending.get("phase") != "commanded"
                or record.get("paused") not in (
                    None, "physical_acknowledgement_missing",
                    "restart_reconciliation_required",
                )
                or not isinstance(pending.get("retry_context"), dict)):
            return False
        entity = pending.get("entity")
        if entity not in spec.source_entities:
            return False
        now = self.clock()
        stamp = self._native_reconnect_epoch.get(entity)
        last = pending.get("last_attempt_at")
        attempts = pending.get("attempts", 0)
        used = pending.get("reconnect_retry_uses", 0)
        from .equipment_setpoint_sequence import retry_settings_match
        if (not isinstance(stamp, (int, float))
                or not isinstance(last, (int, float))
                or not isinstance(attempts, int) or not 1 <= attempts <= (
                    NATIVE_COMMAND_MAX_ATTEMPTS + NATIVE_RECONNECT_EXTRA_ATTEMPTS
                )
                or not isinstance(used, int)
                or used > NATIVE_RECONNECT_EXTRA_ATTEMPTS
                or stamp <= last
                or stamp == pending.get("reconnect_retry_epoch_used")
                or now - stamp < NATIVE_RECONNECT_SETTLE_SECONDS
                or now - last < NATIVE_COMMAND_RETRY_SECONDS
                or (attempts >= NATIVE_COMMAND_MAX_ATTEMPTS
                    and used >= NATIVE_RECONNECT_EXTRA_ATTEMPTS)
                or not retry_settings_match(pending["retry_context"].get("settings"),
                                            model.settings(self.manager, spec))
                or self._native_settle_remaining(spec) != 0
                or not self._current_spec(spec)
                or not self._identity_ok(spec)
                or not model.sources_available(self.manager, spec)):
            return False
        # Clearing only an ACK-exhausted *software pause* allows the exact
        # existing retry path to enforce every fresh native/demand/supply
        # safety check. Any other manual/physical safety hold stays latched.
        if record.get("paused") == "physical_acknowledgement_missing":
            record["paused"] = None
            await self._save()
        await self._retry_pending(spec, pending, now)
        return True

    async def _apply_automatic_reconciliation(
        self, spec: model.ManagedDevice,
    ) -> None:
        """Apply a saved Automatic/PID preference once real ACK is verified."""
        if not (self._ready and self._current_spec(spec)):
            return
        request = self._record(spec).get("automatic_continue_requested")
        if not isinstance(request, dict):
            return
        if model.settings(self.manager, spec).get("control_mode") not in (
            "automatic", "pid"
        ):
            return
        try:
            # async_resume is the original comprehensive native/source/relay
            # verifier. No new physical service is sent by this helper.
            await self.async_resume(spec, automatic=True)
        except HomeAssistantError as error:
            # An observation interval or missing ACK is not a user-facing
            # Manual pause. HEM continues checking during its next normal
            # scheduler tick; no new physical command is sent by this path.
            self._status(
                spec, "awaiting_physical_acknowledgement",
                reason="automatic_reconciliation_observing_native_state",
                automatic_selected=True, settings_saved=True,
                recovery_detail=(
                    "Automatic/PID stays selected. HEM is checking the "
                    "original device state automatically; no action needed."
                ),
                last_verification_issue=str(error)[:180],
            )
            return
        async with self._lock(spec.identifier):
            record = self._record(spec)
            requested = record.get("automatic_continue_requested")
            if isinstance(requested, dict) and (
                model.settings(self.manager, spec).get("control_mode")
                in ("automatic", "pid")
            ):
                record.pop("automatic_continue_requested", None)
                await self._save()
                target_budget = record.get("unconfirmed_native_target")
                self._status(
                    spec, "awaiting_physical_acknowledgement"
                    if target_budget else "awaiting_evaluation",
                    reason="previous_command_not_yet_confirmed"
                    if target_budget else "automatic_recovery_verified",
                    automatic_selected=True,
                    physical_output_confirmed=not bool(target_budget),
                    command_attempts=(target_budget.get("attempts")
                                      if isinstance(target_budget, dict) else None),
                )

    def _startup_readiness(self, spec: model.ManagedDevice) -> dict:
        """Wait for HA ready and a stable, source-bound native startup.

        A device which deliberately has a verified external supply OFF may
        remain unavailable indefinitely. Its original supply controller
        can continue after the HA-ready cooldown; native commands still
        require subsequent source stabilization.
        """
        now = self.clock()
        # Home Assistant's hass.is_running ALSO includes CoreState.starting.
        # That is too early for actuator reconciliation. Require the actual
        # CoreState.running after ALL HA startup integrations have finished;
        # the fallback supports minimal HA-like test harnesses only.
        core_state = getattr(self.hass, "state", None)
        core_ready = (
            getattr(core_state, "value", str(core_state)).lower() == "running"
            if core_state is not None
            else getattr(self.hass, "is_running", True) is True
        )
        if not core_ready:
            self._ha_running_since = None
            return {"ready": False, "reason": "home_assistant_still_starting"}
        if self._ha_running_since is None or not 0 <= now - self._ha_running_since:
            self._ha_running_since = now
        remaining = HA_READY_COOLDOWN_SECONDS - (now - self._ha_running_since)
        if remaining > 0:
            return {
                "ready": False, "reason": "home_assistant_ready_cooldown",
                "remaining_seconds": round(remaining),
            }
        record = self._record(spec)
        cfg = model.settings(self.manager, spec)
        disconnected = []
        for entity in spec.source_entities:
            current = snapshot(self.hass.states.get(entity))
            if current is None:
                disconnected.append(entity)
                self._startup_source_observed.pop((spec.identifier, entity), None)
                self._startup_source_since.pop((spec.identifier, entity), None)
                self._startup_source_done.discard((spec.identifier, entity))
                continue
            key = (spec.identifier, entity)
            if key in self._startup_source_done:
                continue
            previous = self._startup_source_observed.get(key)
            started = self._startup_source_since.get(key)
            # Only native mode and user-settable attributes reset startup
            # readiness. Passive current humidity, temperature and battery
            # reports must not keep an occupied room blocked indefinitely.
            if (previous is None or started is None or now < started
                    or _manual_output_changes(previous, current)):
                self._startup_source_observed[key] = current
                self._startup_source_since[key] = now
                started = now
            wait = NATIVE_STARTUP_STABLE_SECONDS - (now - started)
            if wait > 0:
                remaining = max(remaining, wait)
            else:
                self._startup_source_done.add(key)
        if disconnected:
            # An OFF supply intentionally disconnects its downstream
            # device. Allow the existing guarded upstream controller to
            # evaluate it, but never bypass a persisted native command,
            # power ownership, or restart output verification.
            supply = cfg.get("power_switch_entity")
            state = self.hass.states.get(supply) if supply else None
            upstream = record.get("upstream", {})
            if (state is not None and state.state == "off"
                    and not record.get("pending")
                    and not record.get("power")
                    and not record.get("restart_power_verification")
                    and not (isinstance(upstream, dict)
                             and (upstream.get("pending") or upstream.get("owned")))):
                return {"ready": True, "native_offline_supply_only": True}
            return {
                "ready": False, "reason": "native_source_unavailable",
                "remaining_seconds": None,
            }
        if remaining > 0:
            return {
                "ready": False, "reason": "native_startup_stabilizing",
                "remaining_seconds": round(remaining),
            }
        return {"ready": True}

    async def tick(self, spec: model.ManagedDevice) -> None:
        if not self._active or not self._ready:
            return
        self._invalidated.discard(spec.identifier)
        record = self._record(spec)
        # The production runtime always defines _startup_readiness. Older
        # source-extracted PID test harnesses intentionally bind only tick()
        # and simulate their own ready native device.
        readiness_fn = getattr(self, "_startup_readiness", None)
        readiness = readiness_fn(spec) if callable(readiness_fn) else {"ready": True}
        if not readiness["ready"]:
            self._status(
                spec, "waiting_for_physical_device",
                reason=readiness["reason"],
                startup_settle_remaining_seconds=readiness.get("remaining_seconds"),
                configured_control_method=model.settings(
                    self.manager, spec
                ).get("control_mode"),
                automatic_selected=model.settings(
                    self.manager, spec
                ).get("control_mode") in ("automatic", "pid"),
            )
            return
        from .equipment_setpoint_sequence import progress_stop
        if await progress_stop(self, spec):
            return
        if record.get("queued_power_switch"):
            if await self._apply_queued_power_switch(spec):
                return
        if record.get("restart_power_verification"):
            if not await self._verify_restart_power(spec):
                return
        requested = record.get("automatic_continue_requested")
        if (not isinstance(requested, dict)
                and record.get("paused") == "physical_acknowledgement_missing"
                and model.settings(self.manager, spec).get("control_mode")
                    in ("automatic", "pid")):
            # Recover a Beta97-era stale ACK pause even before a user opens
            # the card. Selecting Auto remains an independent preference;
            # output is still gated on the exact original native evidence.
            method = model.settings(self.manager, spec)["control_mode"]
            record["automatic_continue_requested"] = {
                "at": self.clock(), "method": method,
                "awaiting_physical_verification": True,
            }
            await self._save()
            requested = record["automatic_continue_requested"]
        if isinstance(requested, dict):
            # A newly restored HA entity is observed but never spammed.
            # A real offline→online transition earns at most one bounded
            # reconnect retry per episode, with the unchanged safety gate.
            gate = self._automatic_recovery_gate(spec)
            if (not gate["ready"]
                    and gate.get("reason")
                        == "previous_command_not_yet_confirmed"):
                if await self._retry_after_verified_reconnect(spec):
                    return
            if not gate["ready"]:
                self._status(
                    spec, "awaiting_physical_acknowledgement",
                    reason=gate["reason"],
                    automatic_selected=True, settings_saved=True,
                    requested_native_state=gate.get("requested_native_state"),
                    observed_native_state=gate.get("observed_native_state"),
                    recovery_detail=(
                        "Settings saved. HEM will apply them after verifying "
                        "the earlier physical command. No repeated clicks."
                    ),
                )
                return
            self._schedule_automatic_reconciliation(spec)
            self._status(
                spec, "awaiting_evaluation",
                reason="automatic_reconciliation_scheduled",
                automatic_selected=True, settings_saved=True,
            )
            return
        if record.get("paused"):
            self._status(spec, "paused", reason=record["paused"])
            return
        if not self._current_spec(spec):
            await self._retired(spec)
            return
        # A smart supply may make the downstream device unavailable when it
        # is intentionally OFF. Its own source-bound, durable controller
        # therefore runs BEFORE the native-device availability gate.
        from .equipment_power_switch import before_tick as power_switch_before_tick
        if await power_switch_before_tick(self, spec):
            return
        # The physical device must be available before ANY capability,
        # occupancy, target, measurement or PID calculation is performed.
        if not model.sources_available(self.manager, spec):
            self._status(spec, "waiting_for_physical_device")
            return
        cfg = model.settings(self.manager, spec)
        if cfg["control_mode"] != "pid":
            self._profile_wake.pop(spec.identifier, None)
        cap = model.capabilities(self.manager, spec)
        if cap is None:
            self._status(spec, "physical_capabilities_unavailable")
            return
        # Cache only observed real native capabilities, permitting future
        # switch power-up from still-verified room sensors after outlet OFF.
        # This cache NEVER authorizes native calls while that source is down.
        actual_capabilities = asdict(cap)
        if record.get("capabilities") != actual_capabilities:
            record["capabilities"] = actual_capabilities
            await self._save()
        # The device may have just returned to HA and still be applying its
        # own startup presets. Do not classify manual operation, adopt native
        # output ownership or issue HVAC services until 30 seconds after the
        # verified native source is back. The upstream supply safety stage
        # above continues to run independently.
        settle_fn = getattr(self, "_native_settle_remaining", None)
        settle = settle_fn(spec) if callable(settle_fn) else 0.0
        if settle is None or settle > 0:
            self._status(spec, "waiting_for_physical_device",
                         reason="native_restore_settling"
                         if settle is not None else "native_source_unavailable",
                         reconnect_settle_remaining_seconds=(
                             round(settle) if settle is not None else None
                         ))
            return
        # Native discovery after a HEM-owned supply ON must not fabricate
        # another OFF period or indefinitely reject the same just-powered
        # device as an unrelated unowned manual source.
        if not await self._reconcile_native_after_supply_wake(spec, cap):
            return
        if not await self._reconcile(spec):
            return
        state = self.hass.states.get(cap.primary)
        if state is None or state.state in ("unknown", "unavailable"):
            self._status(spec, "waiting_for_physical_device")
            return
        record["baseline"].setdefault(cap.primary, snapshot(state))
        await self._observe_native_running(spec, cap, state)
        plan = model.plan_for(self.manager, spec)
        presentation = getattr(self, "_presentation_context", None)
        if isinstance(presentation, dict):
            context = (model.profile_name(cfg, plan), plan.get("sleeping"),
                       plan.get("sleep_schedule_evidence"), plan.get("occupancy"),
                       plan.get("away"))
            if presentation.get(spec.identifier) != context:
                presentation[spec.identifier] = context
                # Sleep -> Home can leave demand/status unchanged (e.g. the
                # same RH target). Still refresh this device's effective
                # preset and sleep evidence without waking every room's UI.
                self._presentation_updates.request(spec.identifier)
        target = model.targets(self.manager, spec, cap, cfg, plan)
        mode = cfg.get("requested_mode")
        auto = cfg["control_mode"] in ("automatic", "pid")
        measured = self.measurements(spec, cap)
        soft, power = model.permission(self.manager, spec, cap)
        owned = record["power"].get(cap.primary)
        from .equipment_pid_safety import condition, remember_cutoff, status_details
        current_target = condition(self, spec, cap)
        await remember_cutoff(self, spec, current_target)
        if self._stop_policy_verified(spec, cap, "sleep"):
            # A sleeping room with Pause selected is OFF, not just deprived
            # of PID/setpoint updates. Never re-tune its fan or targets while
            # sleeping. Respect the native minimum ON/defrost interlocks,
            # then let a controller-owned upstream relay idle out separately.
            self._memory.pop(spec.identifier, None)
            self._fan_allocations.pop(spec.identifier, None)
            if record.pop("pid_checkpoint", None) is not None:
                await self._save()
            if output_off(state):
                self._status(spec, "sleep_room_control_paused",
                             reason="native_output_off_during_sleep")
                return
            if not power and not owned:
                self._status(spec, "power_control_not_commissioned",
                             reason="sleep_shutdown_needs_native_power_grant")
                return
            await self._power(
                spec, cap, "off", automatic=False, shutdown=bool(owned),
                policy_stop="sleep",
            )
            return
        if cfg.get("pause_on_window_open", False) and cfg["control_mode"] not in ("existing", "off"):
            window = self._window_policy(spec, cfg)
            if window["blocked"]:
                self._memory.pop(spec.identifier, None)
                self._fan_allocations.pop(spec.identifier, None)
                if record.pop("pid_checkpoint", None) is not None:
                    await self._save()
                if (window["stop_requested"] and not output_off(state)
                        and (power or owned)):
                    await self._power(
                        spec, cap, "off", automatic=False, shutdown=bool(owned),
                        policy_stop="window",
                    )
                else:
                    self._status(spec, window["status"],
                                 window_resume_remaining_seconds=window["remaining_seconds"])
                return  # No targets, fan, swing or mode control during hold.
        if current_target is not None and current_target["needed"] is False and (power or owned):
            # Reaching the target ends this logical PID pulse immediately.
            # Physical OFF retains native minimum-ON, defrost and the user's
            # optional reverse-setpoint grace; never cut the supply directly.
            if not output_off(state):
                await self._power(
                    spec, cap, "off", automatic=False, shutdown=bool(owned),
                    policy_stop="target",
                )
            else:
                self._status(spec, "within_target_band", **status_details(record))
            return
        if (auto and power and not output_off(state)
                and self._stop_policy_verified(spec, cap, "idle")):
            # PID integral or PWM phase cannot keep an appliance energized
            # once independent fresh measured demand is decisively FALSE.
            # Native OFF still enforces the minimum runtime. The optional
            # external supply remains on until a *separate* idle cooldown.
            await self._power(
                spec, cap, "off", automatic=False, shutdown=bool(owned),
                policy_stop="idle",
            )
            return
        if auto and power and not owned and not output_off(state):
            self._status(spec, "running_device_requires_off_before_automatic_power_ownership")
            return
        if owned and not power:
            await self._power(spec, cap, "off", automatic=auto, shutdown=True)
            return
        from .equipment_setpoint_sequence import SETPOINT_GRACE_SECONDS, enabled, supports_stop
        shutdown_lead = (SETPOINT_GRACE_SECONDS if owned
                         and enabled(model.settings(self.manager, spec))
                         and supports_stop(cap, state) else 0)
        if owned and self.clock()-owned["since"] >= max(
            owned["min_on"], owned["max_on"] - shutdown_lead
        ):
            await self._power(spec, cap, "off", automatic=auto, shutdown=True)
            return
        if cfg["control_mode"] == "off":
            if not output_off(state):
                await self._power(spec, cap, "off", automatic=False, shutdown=bool(owned))
            else:
                self._status(spec, "off")
            return
        if cfg["control_mode"] == "existing":
            return
        if cfg["control_mode"] == "manual" and not (
            cfg.get("requested_mode") or cfg.get("profile_targets") or cfg.get("profile_fans")
            or cfg["preset"] != "none" or cfg.get("fan_mode")
            or cfg.get("swing_mode") or cfg.get("swing_horizontal_mode")
        ):
            self._status(spec, "manual_no_request")
            return
        if auto and not (cfg["control_mode"] == "pid" and mode in cap.modes and mode != "off"):
            from .dry_mode import automatic_mode
            room = model.room_config(self.manager, spec)
            mode = automatic_mode(
                cap, state, measured, target,
                dedicated_dry=room.get("dry_climate_entity") == cap.primary,
                pid=cfg["control_mode"] == "pid",
            )
        if mode is None:
            mode = state.state if cap.domain == "climate" else next((v for v in cap.modes if v != "off"), "off")
        if why := self._gate(spec, cap, cfg, plan, mode, automatic=auto):
            self._status(spec, why)
            if owned and state.state != "off":
                await self._power(spec, cap, "off", automatic=auto, shutdown=True)
            return
        demand, metric, increasing, goal, wanted = None, None, False, None, None
        pwm_info = None
        measured_fan_allocation = None
        self._fan_allocations.pop(spec.identifier, None)
        if cap.domain == "fan" or set(cap.modes) == {"off", "fan_only"}:
            from .device_activation import effective_device
            dev = effective_device(self.manager, spec, cap.primary)
            room = model.room_config(self.manager, spec)
            extraction = dev.get("fan_purpose") == "extraction" or room.get("extraction_fan_entity") == cap.primary
            metric = "co2" if extraction else "pm25"
            goal = plan.get("air_actions", {}).get("thresholds", {}).get(
                "co2_operational_ppm" if extraction else "pm25_short_term_action_ug_m3")
        elif cap.domain == "humidifier" or mode == "dry":
            metric, goal, increasing = "humidity", target["humidity"], cap.humidifying
        elif mode in ("heat", "cool"):
            metric, goal, increasing = "temperature", target[mode], mode == "heat"
        elif mode in ("heat_cool", "auto") and (cap.temperature or cap.temperature_range):
            # Native range/AUTO owns its thermal direction. We only qualify
            # an outside-band ON; never implement simultaneous heating/cooling.
            value = measured["temperature"]
            metric, increasing = "temperature", value is not None and value < target["heat"]
            goal = target["heat"] if increasing else target["cool"]
        if auto and metric:
            value = measured[metric]
            if value is None or finite(goal, 0, 20000) is None:
                self._status(spec, "control_measurement_missing_or_stale")
                if owned:
                    await self._power(spec, cap, "off", automatic=True, shutdown=True)
                return
            error = (goal-value) if increasing else (value-goal)
            if cfg["control_mode"] == "pid" and mode in ("heat_cool", "auto") and cap.domain == "climate":
                self._status(spec, "select_single_direction_for_pid")
                return
            if cfg["control_mode"] == "pid":
                # Older standalone production-tick regression harnesses
                # compile only tick() without the new observer methods.
                # The real runtime always has the passive observer; treating
                # it as an optional diagnostic keeps the actuator path pure.
                passive = getattr(self, "_pid_passive_observe", None)
                if passive is not None:
                    await passive(
                        spec, cfg, cap, plan, target, measured, record, state,
                        mode, metric, goal, soft, power,
                    )
                from .pid_phase import phase_decision, binary_pwm_off_phase
                previous, memory, anchor = self._memory.get(
                    spec.identifier, (None, None, self.clock())
                )
                if previous is None:
                    restore = getattr(self, "_resume_pid_checkpoint", None)
                    if callable(restore):
                        recovered = restore(
                            spec, record, cfg, value, goal, increasing
                        )
                        if recovered is not None:
                            previous, memory, anchor = recovered
                profile = model.profile_name(cfg, plan)
                on_min, off_min, _ = model.timing(self.manager, spec, cap)
                signature, rebased, priority_wake = phase_decision(
                    previous, metric=metric, target=goal, increasing=increasing,
                    profile=profile, mode=mode, preset=cfg["preset"],
                    kp=cfg["kp"], ki=cfg["ki"], kd=cfg["kd"],
                    cycle_s=cfg["cycle_seconds"],
                    min_on_s=on_min, min_off_s=off_min, measured=value,
                )
                if rebased:
                    memory, anchor = None, self.clock()
                    # A new comfort demand starts a fresh logical phase.
                    # Keep the one-time wake request until the physical output
                    # is seen ON or its bounded validity window expires. This
                    # survives a minimum-OFF hold without resetting that hold.
                    self._profile_wake.pop(spec.identifier, None)
                    if (priority_wake and power and output_off(state)
                            and cap.domain in ("climate", "switch", "input_boolean")):
                        self._profile_wake[spec.identifier] = {
                            "profile": profile, "mode": mode,
                            "until": self.clock() + max(
                                off_min + cfg["sample_seconds"],
                                cfg["cycle_seconds"],
                            ),
                        }
                memory = model.pid_step(
                    value, goal, self.clock(), increasing=increasing,
                    kp=cfg["kp"], ki=cfg["ki"], kd=cfg["kd"],
                    sample=cfg["sample_seconds"], memory=memory,
                )
                self._memory[spec.identifier] = (signature, memory, anchor)
                persist = getattr(self, "_checkpoint_pid", None)
                if callable(persist):
                    await persist(spec, record, cfg, signature, memory, anchor)
                demand = memory.demand
                if (cfg.get("pid_fan_capacity_mode") == "measured"
                        and cap.domain in ("climate", "humidifier")
                        and cap.fan_entity and cap.fan_modes and demand > 0):
                    # Only the calibrated HVAC direction and the *exact*
                    # same physical endpoint and fan may use the model.
                    # A separate accessory fan that is currently OFF cannot
                    # be assumed to produce the measured capacity.
                    saved_models = cfg.get("pid_fan_capacity_models") or {}
                    saved_curve = saved_models.get(mode) if isinstance(saved_models, dict) else None
                    fan_state = self.hass.states.get(cap.fan_entity)
                    native_ready = (cap.fan_entity == cap.primary or
                                    fan_state is not None and
                                    fan_state.state not in ("off", "unknown", "unavailable"))
                    valid = (native_ready and isinstance(saved_curve, dict)
                             and saved_curve.get("sources") == list(spec.source_entities)
                             and fan_capacity_model_is_valid(
                                 saved_curve, mode=mode,
                                 physical_entity=cap.primary,
                                 fan_entity=cap.fan_entity,
                                 percentage=cap.fan_percentage,
                                 advertised_modes=cap.fan_modes))
                    if valid:
                        quiet_context = self._quiet_context(spec, cfg, plan)
                        if quiet_context is not None:
                            limits = model.device_limits(self.manager, spec, cap)
                            measured_fan_allocation = allocate_fan_capacity(
                                demand, saved_curve, quiet=quiet_context,
                                quiet_mode=cfg.get("quiet_fan_mode"),
                                quiet_percentage=cfg["quiet_percentage"],
                                fan_min_percentage=limits["fan_min_percentage"],
                                fan_max_percentage=limits["fan_max_percentage"],
                            )
                            if measured_fan_allocation:
                                self._fan_allocations[spec.identifier] = {
                                    "status": "capacity_limited" if
                                        measured_fan_allocation.unmet_demand_percent > 0
                                        else "capacity_compensated",
                                    **measured_fan_allocation.snapshot(),
                                    "direction": mode,
                                }
                        else:
                            self._fan_allocations[spec.identifier] = {
                                "status": "quiet_context_unknown",
                                "direction": mode,
                            }
                    else:
                        self._fan_allocations[spec.identifier] = {
                            "status": "model_source_or_mode_not_ready",
                            "direction": mode,
                        }
                # Use ONE modulation dimension for continuously adjustable
                # standalone fans. Never multiply a PID percentage by a
                # second PWM duty. Binary valves/heaters retain safe slow PWM.
                if cap.domain == "fan" and cap.fan_percentage:
                    min_speed = model.device_limits(self.manager, spec, cap)["fan_min_percentage"]
                    wanted = percentage_output_requested(demand, min_percentage=min_speed)
                elif cap.domain == "fan" and ordered_fan_stages(cap.fan_modes):
                    wanted = demand > 0
                else:
                    duty_demand = (
                        measured_fan_allocation.compensated_duty_percent
                        if measured_fan_allocation else demand
                    )
                    elapsed = self.clock() - anchor
                    pwm_info = binary_pwm_off_phase(
                        duty_demand, elapsed, cfg["cycle_seconds"],
                        on_min, off_min, starting=output_off(state),
                    )
                    # A short duty must produce a full physically safe
                    # native ON interval rather than being skipped FOREVER.
                    # The longer mathematical cycle never bypasses the
                    # separately persisted real compressor ON/OFF dwell.
                    effective_cycle = pwm_info["effective_cycle_seconds"]
                    wanted = bool(effective_cycle is not None and model.duty_on(
                        duty_demand, elapsed, effective_cycle,
                        on_min, off_min, starting=output_off(state),
                    ))
                    recovery = self._profile_wake.get(spec.identifier)
                    if recovery:
                        still_qualified = (
                            self.clock() <= recovery["until"]
                            and recovery["profile"] == profile
                            and recovery["mode"] == mode
                            and metric == "temperature"
                            and error >= 0.5
                            and demand > 0
                            and power
                            and output_off(state)
                        )
                        if still_qualified:
                            # A brief priority pulse is permissible after a
                            # MORE demanding comfort profile, even when its
                            # proportional PWM duty is below minimum ON time.
                            # _power() separately checks actual off-min dwell,
                            # grants, ACK, opposite-mode and live room policy.
                            wanted = True
                        else:
                            self._profile_wake.pop(spec.identifier, None)
            else:
                # Hysteresis preserves current output until the opposite boundary.
                band = .3 if metric == "temperature" else 2 if metric == "humidity" else 50 if metric == "co2" else 2
                wanted = error > band or not output_off(state) and error > -band
            # HEM_B102_NATIVE_PID_FOLLOWTHROUGH
            # A climate can ACK HEAT/COOL with its previous antifrost setpoint
            # (e.g. 4/5°C). For a commissioned, already HEM-owned physical ON,
            # correct the native setpoint BEFORE an unrelated PWM OFF-phase
            # minimum-ON hold returns early. The real PID demand must remain
            # positive; never energize an OFF device or delay a permitted OFF.
            # All startup, sleep, window, quiet, manual, availability, identity
            # and foreign-owner gates above have already passed. _native_target
            # dispatches only through the existing durable _send/ACK path.
            if (
                cfg["control_mode"] == "pid"
                and power and cap.domain == "climate" and cap.temperature
                and mode in ("heat", "cool") and state.state == mode
                and isinstance(owned, dict)
                and demand is not None and demand > 0 and error > 0
                and (
                    wanted is True or (
                        wanted is False
                        and isinstance(owned.get("since"), (int, float))
                        and isinstance(owned.get("min_on"), (int, float))
                        and 0 <= self.clock() - owned["since"] < owned["min_on"]
                    )
                )
            ):
                if (await self._native_target(
                    spec, cap, mode, target, None, True
                )) is not False:
                    return
                if spec.identifier in self._invalidated:
                    return
            if power and (cap.domain != "number" and cap.domain != "input_number"):
                desired = mode if wanted else "off"
                if wanted and output_off(state) and cap.fan_modes and (
                    cfg.get("quiet_sleep") or cfg.get("quiet_occupied")
                ) and self._quiet_context(spec, cfg, plan) is None:
                    self._status(spec, "quiet_context_unknown")
                    return  # Never power on into an unknown quiet context.
                if (state.state == "off") != (desired == "off") or cap.domain == "climate" and state.state != desired:
                    await self._power(spec, cap, desired, automatic=True)
                    return
        elif not auto and mode != state.state and (cap.domain == "climate" or (mode == "off") != (state.state == "off")):
            await self._power(spec, cap, mode, automatic=False)
            return
        if cap.domain in ("number", "input_number") and auto:
            if not power or metric is None:
                self._status(spec, "proportional_output_not_commissioned")
                return
            value = 100. if demand is None and wanted else demand or 0.
            attrs = state.attributes
            current = finite(state.state, 0, 100)
            if attrs.get("unit_of_measurement") != "%" or attrs.get("min") != 0 or attrs.get("max") != 100 or current is None:
                self._status(spec, "proportional_output_not_verified")
                return
            on_min, off_min, _ = model.timing(self.manager, spec, cap)
            if current == 0 and value > 0:
                stamp = record["off_at"].setdefault(cap.primary, self.clock())
                if self.clock()-stamp < off_min:
                    self._status(spec, "minimum_off_hold")
                    return
            if value == 0 and current > 0:
                await self._power(spec, cap, "off", automatic=True, shutdown=bool(owned))
                return
            if self.clock()-record.get("output_at", 0) < cfg["sample_seconds"]:
                return
            value = round(max(current-10, min(current+10, value)), 1)
            step = finite(attrs.get("step", 1), .01, 10)
            if step is None:
                return
            value = max(0., min(100., round(value/step)*step))
            if abs(value-current) >= step:
                if await self._send(spec, cap, cap.primary, "set_value", {"value": value},
                                    {"state": str(value)}, power=True, mode=mode, automatic=True):
                    record["output_at"] = self.clock()
                return
        if auto and output_off(state) and not power:
            self._status(spec, "native_off_no_power_permission")
            return
        if auto or cfg.get("profile_targets", {}).get(model.profile_name(cfg, plan)) or cfg["preset"] != "none":
            if (await self._native_target(spec, cap, mode, target, demand if not power else None, auto)) is not False:
                return
            if spec.identifier in self._invalidated:
                return
        if await self._fan(spec, cap, cfg, plan,
                           demand if auto and cfg["control_mode"] == "pid" else None,
                           auto, measured_fan_allocation.speed
                           if measured_fan_allocation else None):
            return
        if spec.identifier in self._invalidated:
            return
        for key, service in (("swing_mode", "set_swing_mode"), ("swing_horizontal_mode", "set_swing_horizontal_mode")):
            if cfg.get(key) is not None and state.attributes.get(key) != cfg[key]:
                if await self._send(spec, cap, cap.primary, service, {key: cfg[key]}, {"attributes": {key: cfg[key]}}, automatic=auto):
                    return
        status = "controlling" if auto else "manual"
        if auto and wanted is False and output_off(state):
            # A selected PID method is not necessarily energizing the device:
            # expose duty-cycle idle vs ordinary deadband, without changing a
            # single actuator command, timer, protection, or ownership decision.
            status = ("pid_output_inactive" if cfg["control_mode"] == "pid"
                      and demand is not None and demand > 0
                      else "within_target_band")
        self._status(
            spec, status, demand_percent=demand,
            profile=model.profile_name(cfg, plan),
            mode=mode, temperature=measured["temperature"],
            humidity=measured["humidity"],
            # Neutral PID scheduling diagnostics, NOT an actuator failure.
            pid_control_metric=metric if cfg["control_mode"] == "pid" else None,
            pid_pwm_state=pwm_info["state"] if pwm_info else None,
            pid_pwm_effective_cycle_seconds=(
                pwm_info["effective_cycle_seconds"] if pwm_info else None
            ),
            pid_pwm_next_window_seconds=(
                pwm_info["next_window_seconds"] if pwm_info else None
            ),
        )
