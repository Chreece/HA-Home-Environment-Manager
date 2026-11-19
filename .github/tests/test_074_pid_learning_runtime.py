"""Normal target completion reaches the real passive observer, without actuation.

Reuse the complete production-tick/native-ACK fixture. All HA state, transport,
storage and time are synthetic; the observer and controller are production code.
"""
from __future__ import annotations

import ast
import math
from pathlib import Path
import runpy
from types import MethodType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_beta111_pid_target_cutoff.py"))
production, model = fixture["production"], fixture["model"]
load_pure = fixture["fixture"]["load_pure"]
passive = load_pure("pid_passive", "pid_passive.py")
production.PassiveObserver = passive.PassiveObserver
production.passive_identity = passive.identity
tree = ast.parse((ROOT / "equipment_runtime.py").read_text())
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EquipmentRuntime")
observer_method = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef)
                       and n.name == "_pid_passive_observe")
exec(compile(ast.Module(body=[observer_method], type_ignores=[]),
             "production passive observation", "exec"), production.__dict__)


def attach(runtime):
    runtime.manager.settings.update(pid_calibration_method="adaptive_suggest",
                                    requested_mode="heat", sample_seconds=300)
    runtime._pid_passive_observers = {}
    runtime._pid_passive_tasks = {}
    runtime._pid_learning_holds = {}
    runtime._presentation_updates = N(request=lambda *_: None)
    runtime._pid_passive_observe = MethodType(production._pid_passive_observe, runtime)
    original_measurements = runtime.measurements

    def measurements(spec, cap):
        return {**original_measurements(spec, cap),
                "temperature_selected_entities": ["sensor.room_temperature"]}

    runtime.measurements = measurements
    runtime.hass.async_create_task = lambda coro: runtime.queued_tasks.append(coro)
    cap = model.capabilities(runtime.manager, runtime.spec)
    cfg = model.settings(runtime.manager, runtime.spec)
    context = passive.identity(
        runtime.spec.area_id, list(runtime.spec.source_entities), cap.primary,
        "heat", "temperature", "sensor.room_temperature",
        model.profile_name(cfg, runtime.manager.plan), round(float(runtime.goal), 2),
        runtime.state.attributes.get("fan_mode"), runtime.state.attributes.get("percentage"),
    )
    return cap, cfg, context


def seed_normal_response(runtime, context):
    observer = passive.PassiveObserver()
    start = runtime.now - 42 * 300
    options = dict(context=context, metric="temperature", direction=1,
                   sample_seconds=300, safe=True)
    for index in range(6):
        observer.observe(at=start - (6 - index) * 300, value=17.,
                         on=False, owned=False, **options)
    for index in range(42):
        value = 17. + 4. * (1. - math.exp(-max(0., index * 5. - 10.) / 28.))
        observer.observe(at=start + index * 300, value=value,
                         on=True, owned=True, **options)
    assert observer.on and not observer.cycles
    runtime._pid_passive_observers[runtime.spec.identifier] = observer
    return observer


class LearningRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_target_satisfied_off_completes_real_cycle_without_service(self):
        with fixture["endpoint"]("heat") as runtime:
            _, _, context = attach(runtime)
            observer = seed_normal_response(runtime, context)
            runtime.state.state = "off"
            runtime.state.attributes["hvac_action"] = "off"
            runtime.measurement = runtime.goal
            await runtime.evaluate()
            self.assertEqual(len(observer.cycles), 1)
            self.assertFalse(observer.on)
            self.assertEqual(runtime.record["pid_passive"]["summary"]["valid_cycles"], 1)
            self.assertEqual(runtime.calls, [])
            # The normal idle interval also builds the next stable baseline.
            for _ in range(3):
                await runtime.evaluate(advance=300)
            self.assertGreaterEqual(observer.off[-1][0] - observer.off[0][0], passive.MIN_OFF_S)
            self.assertEqual(runtime.calls, [])

    async def test_target_reached_does_not_invent_off_before_native_ack(self):
        with fixture["endpoint"]("heat") as runtime:
            _, _, context = attach(runtime)
            observer = seed_normal_response(runtime, context)
            runtime.own()
            runtime.state.attributes["hvac_action"] = "heating"
            runtime.measurement = runtime.goal
            await runtime.evaluate()
            self.assertEqual(len(observer.cycles), 0)
            self.assertTrue(observer.last_on)
            # The controller may request native OFF, but a service return is
            # never a completed passive cycle until a later real observation.
            self.assertTrue(all(c["service"] != "set_hvac_mode" or
                                c["data"].get("hvac_mode") == "off"
                                for c in runtime.calls))

    async def test_safety_hold_interrupts_instead_of_accepting_target_stop(self):
        with fixture["endpoint"]("heat") as runtime:
            _, _, context = attach(runtime)
            observer = seed_normal_response(runtime, context)
            runtime.state.state = "off"
            runtime.state.attributes["hvac_action"] = "off"
            runtime.measurement = runtime.goal
            runtime._gate = lambda *args, **kwargs: "source_deselected_or_moved"
            await runtime.evaluate()
            self.assertEqual(observer.cycles, [])
            self.assertFalse(observer.on)
            self.assertEqual(runtime.calls, [])

    async def test_contradictory_native_off_is_not_baseline_or_completion(self):
        with fixture["endpoint"]("heat") as runtime:
            cap, cfg, context = attach(runtime)
            observer = seed_normal_response(runtime, context)
            runtime.state.state = "off"
            runtime.state.attributes["hvac_action"] = "heating"
            await runtime._pid_passive_observe(
                runtime.spec, cfg, cap, runtime.manager.plan, {},
                runtime.measurements(runtime.spec, cap), runtime.record, runtime.state,
                "heat", "temperature", runtime.goal, True, True,
            )
            self.assertEqual(observer.cycles, [])
            self.assertFalse(observer.off)
            self.assertFalse(observer.on)
            self.assertEqual(runtime._pid_learning_holds[runtime.spec.identifier]["reason"],
                             "verified_activity_required")
            self.assertEqual(runtime.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
