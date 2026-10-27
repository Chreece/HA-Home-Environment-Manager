"""Beta62 regression tests using the real PID method bodies, isolated from HA."""
from __future__ import annotations

import ast
import asyncio
import math
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS
import sys

ROOT = Path(__file__).resolve().parents[2]


def extract(*method_names, env):
    path = ROOT / "climate_pid.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    methods = [
        method for node in tree.body if isinstance(node, ast.ClassDef)
        for method in node.body
        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
        and method.name in method_names
    ]
    assert {m.name for m in methods} == set(method_names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), "exec"), env)
    return [env[method] for method in method_names]


def finite(value, low, high):
    try:
        number = float(value)
        return number if low <= number <= high and math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def physical(target=20, mode="heat"):
    return NS(
        state=mode, attributes={
            "supported_features": 1, "preset_mode": "none",
            "temperature": target, "temperature_unit": "°C",
            "min_temp": 5, "max_temp": 35, "target_temp_step": 0.5,
        },
    )


@dataclass
class Memory:
    steps: int = 0


@dataclass
class Control:
    memory: Memory = field(default_factory=Memory)
    last_checked: float | None = None
    last_sent: float | None = None


class Controller:
    def __init__(self, *, two_devices=False):
        self.entry_id = "pid-test-entry"
        self._active = True
        self._store_ready = True
        self._tasks = {}
        self._paused = {}
        self._rooms = {}
        self._expected = {}
        self.statuses = {}
        self.saved = []
        self._started_at = 1000
        self._clock = lambda: 5000
        self.states = {
            "climate.one": physical(20),
            "climate.two": physical(21),
        }
        self.sensor_value = 20.
        self.commands = []
        self.first_entered = asyncio.Event()
        self.release_first = asyncio.Event()
        self.block_first = False
        self.change_second = None
        self.hass = NS(states=NS(get=self.states.get), services=NS())
        self.hass.services.has_service = lambda domain, service: (
            domain, service) == ("climate", "set_temperature")

        async def send(domain, service, data, target, blocking):
            entity = target["entity_id"]
            self.commands.append((entity, data["temperature"]))
            if entity == "climate.one":
                self.first_entered.set()
                if self.change_second == "native":
                    self.states["climate.two"] = physical(25)
                elif self.change_second == "sensor":
                    self.sensor_value = 22.
                if self.block_first:
                    await self.release_first.wait()
        self.hass.services.async_call = send

    def _set_status(self, area, status, **data):
        self.statuses[area] = {"status": status, **data}

    def _save(self):
        self.saved.append((
            dict(self._paused), {area: dict(values)
                                 for area, values in self._expected.items()}
        ))

    def _targets(self, cfg):
        return ("climate.one", "climate.two") if cfg.get("two_devices") else ("climate.one",)

    async def _pause(self, area, reason):
        self._paused[area] = reason
        self._save()
        self._set_status(area, "paused", reason=reason)


settings = {
    "enabled": True,
    "mode": "heat",
    "target_c": 23.,
    "temperature_entity": "sensor.thermometer",
    "sample_seconds": 300,
    "pause_on_window_open": True,
    "kp": 1, "ki": 0, "kd": 0,
    "offset_c": 3,
    "min_setpoint_c": 17, "max_setpoint_c": 28,
    "max_change_c": 2, "min_change_c": 0.1,
}


def env_for(controller):
    return {
        "asyncio": asyncio, "math": math, "finite": finite,
        "RoomControl": Control, "TARGET_TEMPERATURE_FEATURE": 1,
        "MANUAL_GRACE_SECONDS": 120, "SENSOR_MAX_AGE_MINUTES": 10,
        "entity_area": lambda hass, entity: "living",
        "temperature_sensor_c": lambda hass, entity, age: controller.sensor_value,
        "validate_settings": lambda config: (True, "ready"),
        "target_from_unit": lambda temp, unit: temp,
        "target_to_unit": lambda temp, unit: temp,
        "setpoint_c": lambda *args: 23.,
        "step": lambda *args: NS(status="ready", memory=Memory(1),
                                 demand_percent=50, proportional=1,
                                 integral=0, derivative=0),
        "bounded_command": lambda *args, **kwargs: ("command", 23.),
        "foreign_owner_hold": lambda *args: None,
    }


pkg = ModuleType("pid_bug_test")
pkg.__path__ = []
equip = ModuleType("pid_bug_test.equipment_model")
equip.legacy_hold = lambda *args: None
sys.modules[pkg.__name__] = pkg
sys.modules[equip.__name__] = equip


async def run():
    # The per-room action UI must not cancel a potentially already-dispatched
    # physical command and lose the asynchronous service acknowledgment.
    ctrl = Controller()
    env = env_for(ctrl)
    env["__package__"] = "pid_bug_test"
    async_action, async_stop, tick = extract(
        "async_action", "async_stop", "_tick", env=env
    )
    room = NS(windows=())
    cfg = {**settings, "two_devices": True}

    ctrl.block_first = True
    command = asyncio.create_task(tick(ctrl, "living", room, cfg, 5000))
    ctrl._tasks["living"] = command
    await asyncio.wait_for(ctrl.first_entered.wait(), timeout=3)
    initial_commands = list(ctrl.commands)
    assert initial_commands == [("climate.one", 23.)], initial_commands

    paused = await async_action(
        ctrl, "living", "pause", {"living": {"enabled": True}}
    )
    assert paused["accepted"] and not command.cancelled()
    assert ctrl._paused["living"] == "user_pause"
    # Reset and resume cannot erase an in-flight command's intended target.
    for action in ("reset", "resume"):
        rejected = await async_action(
            ctrl, "living", action, {"living": {"enabled": True}}
        )
        assert not rejected["accepted"] and rejected["reason"] == "command_in_progress"
    ctrl.release_first.set()
    await asyncio.wait_for(command, timeout=3)
    assert not command.cancelled()
    assert ctrl.commands == initial_commands, ctrl.commands
    assert ctrl._expected["living"]["climate.one"]["value"] == 23.
    assert ctrl.statuses["living"]["status"] == "paused", ctrl.statuses

    # Once the task finishes, Resume can explicitly acknowledge its
    # expected-state history without a cancellation race.
    resumed = await async_action(
        ctrl, "living", "resume", {"living": {"enabled": True}}
    )
    assert resumed["accepted"]
    assert ctrl._paused == {} and ctrl._expected == {}

    # Legacy PID should not be stuck forever simply because this room has
    # no configured windows. Unknown or open SELECTED contacts still hold.
    for windows, expected in (
        ((), "temperature_unavailable_or_stale"),
        ((NS(opened=None),), "window_open_or_unknown"),
        ((NS(opened=True),), "window_open_or_unknown"),
        ((NS(opened=False),), "temperature_unavailable_or_stale"),
    ):
        c = Controller()
        e = env_for(c)
        e["temperature_sensor_c"] = lambda *args: None
        e["__package__"] = "pid_bug_test"
        (tick_method,) = extract("_tick", env=e)
        await tick_method(c, "living", NS(windows=windows), cfg, 5000)
        assert c.statuses["living"]["status"] == expected, (windows, c.statuses)

    # Prevent stale second-device writes when the first awaited HA service
    # returns after another user changed the second device's target.
    for changed, expected in (
        ("native", "physical_state_changed_before_pid_write"),
        ("sensor", "temperature_changed_before_pid_write"),
    ):
        c = Controller()
        c.change_second = changed
        e = env_for(c)
        e["__package__"] = "pid_bug_test"
        (t,) = extract("_tick", env=e)
        await t(c, "living", room, cfg, 5000)
        assert c.commands == [("climate.one", 23.)], (changed, c.commands)
        assert c.statuses["living"]["status"] in (
            "paused", "temperature_changed_before_pid_write"
        )
        if changed == "native":
            assert c._paused["living"] == expected
        else:
            assert c.statuses["living"]["status"] == expected

    # HA unload while set_temperature is in flight must latch a durable
    # hold *before* cancellation, so restart cannot replay ambiguous I/O.
    c = Controller()
    blocker = asyncio.Event()
    task = asyncio.create_task(blocker.wait())
    c._tasks["living"] = task
    class DurableStore:
        def __init__(self):
            self.snapshots = []
        async def async_save(self, snapshot):
            self.snapshots.append(snapshot)

    c._store = DurableStore()
    c._snapshot = lambda: {"paused": dict(c._paused), "expected": dict(c._expected)}
    c._store_ready = True
    await async_stop(c)
    assert task.cancelled()
    assert c._store.snapshots
    assert c._store.snapshots[-1]["paused"]["living"] == (
        "shutdown_during_inflight_pid_cycle"
    )

    print("PASS: paused service ACK retained; resume/reset do not cancel; windowless PID; unknown contacts block; native and sensor races; unload hold")


asyncio.run(run())
