"""Missing foreign contacts cannot hold a different room's controller.

Exercise the production window policy and room-source selection. Registry
lookups use the actual discovery helpers; only Home Assistant state/registry
access and the runtime clock are simulated. No physical devices or services.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "hem119_window_regression"
AREA = "living"
LOCAL = "binary_sensor.living_window"
FOREIGN = "binary_sensor.bath_window"
BASE = 1700000000.0


def module(name, **members):
    result = ModuleType(name)
    result.__dict__.update(members)
    sys.modules[name] = result
    return result


module(PACKAGE, __path__=[str(ROOT)])
module(PACKAGE + ".const", DOMAIN="environment_manager")
module(PACKAGE + ".equipment_model")  # Policy settings are passed explicitly.
discovery = module(
    PACKAGE + ".discovery",
    er=N(async_get=lambda hass: N(async_get=hass.entities.get)),
    dr=N(async_get=lambda hass: N(async_get=hass.devices.get)),
)
tree = ast.parse((ROOT / "discovery.py").read_text(encoding="utf-8"))
names = {"entity_area", "_device_class", "is_window"}
functions = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in names]
assert {node.name for node in functions} == names
exec(compile(ast.Module(
    body=[ast.parse("from __future__ import annotations").body[0], *functions],
    type_ignores=[],
), str(ROOT / "discovery.py"), "exec"), discovery.__dict__)
window = importlib.import_module(PACKAGE + ".equipment_window")


class Fixture:
    def __init__(self, contacts=None):
        self.now = BASE
        self.states = {}
        self.entities = {}
        self.devices = {}
        self.hass = N(states=N(get=self.states.get), entities=self.entities,
                      devices=self.devices)
        self.manager = N(settings={"room_sources": {
            AREA: {"windows": list(contacts if contacts is not None else (LOCAL, FOREIGN))},
        }})
        self.spec = N(identifier="living-controller", area_id=AREA)
        self.register(LOCAL, AREA)
        self.register(FOREIGN, "bath")
        self.put(LOCAL, "off", changed=BASE - 120)

    def clock(self):
        return self.now

    def register(self, entity, area, *, device_area=None):
        device_id = entity + "-device" if device_area is not None else None
        if device_id is not None:
            self.devices[device_id] = N(area_id=device_area)
        self.entities[entity] = N(area_id=area, device_id=device_id,
                                  original_device_class="window", device_class=None)

    def put(self, entity, value, *, changed=None):
        self.states[entity] = N(
            entity_id=entity, domain=entity.split(".", 1)[0], state=value,
            attributes={},
            last_changed=datetime.fromtimestamp(
                self.now if changed is None else changed, timezone.utc),
        )

    def evaluate(self):
        return window.evaluate(self, self.spec, {"pause_on_window_open": True})


class RoomWindowTests(unittest.TestCase):
    def test_missing_foreign_contact_uses_registry_area_without_live_state(self):
        for entity_area, device_area in (("bath", None), (None, "bath")):
            with self.subTest(entity_area=entity_area, device_area=device_area):
                fixture = Fixture()
                fixture.register(FOREIGN, entity_area, device_area=device_area)
                result = fixture.evaluate()
                self.assertEqual(result["contacts"], [LOCAL])
                self.assertEqual(result["ignored_other_room_contacts"], [FOREIGN])
                self.assertEqual(result["status"], "window_closed_ready")
                self.assertFalse(result["blocked"])
                self.assertFalse(result["stop_requested"])

    def test_missing_foreign_contact_cannot_invent_windows_for_windowless_room(self):
        fixture = Fixture([FOREIGN])
        result = fixture.evaluate()
        self.assertEqual(result["contacts"], [])
        self.assertEqual(result["status"], "window_contacts_not_configured")
        self.assertFalse(result["blocked"])

    def test_foreign_state_disappearing_cannot_restart_local_recovery(self):
        fixture = Fixture()
        fixture.put(FOREIGN, "on")
        self.assertFalse(fixture.evaluate()["blocked"])
        fixture.put(LOCAL, "on")
        self.assertTrue(fixture.evaluate()["stop_requested"])
        fixture.put(LOCAL, "off")
        self.assertEqual(fixture.evaluate()["remaining_seconds"], 60)

        fixture.now += 20
        fixture.states.pop(FOREIGN)
        result = fixture.evaluate()
        self.assertEqual(result["status"], "window_close_warmup")
        self.assertEqual(result["remaining_seconds"], 40)
        self.assertTrue(result["stop_requested"])

        fixture.now += 39
        fixture.put(FOREIGN, "unavailable")
        self.assertEqual(fixture.evaluate()["remaining_seconds"], 1)
        fixture.now += 1
        fixture.states.pop(FOREIGN)
        result = fixture.evaluate()
        self.assertEqual(result["status"], "window_closed_ready")
        self.assertFalse(result["blocked"])
        self.assertFalse(result["stop_requested"])

    def test_missing_local_contact_still_holds_and_requires_recovery_delay(self):
        fixture = Fixture([LOCAL])
        # Entity-area override is authoritative even when its device has
        # been assigned elsewhere. Missing local evidence must not be ignored.
        fixture.register(LOCAL, AREA, device_area="bath")
        fixture.states.pop(LOCAL)
        result = fixture.evaluate()
        self.assertEqual(result["status"], "window_state_unknown")
        self.assertEqual(result["unknown_contacts"], [LOCAL])
        self.assertTrue(result["blocked"])
        self.assertFalse(result["stop_requested"])

        fixture.put(LOCAL, "off", changed=BASE - 120)
        self.assertEqual(fixture.evaluate()["remaining_seconds"], 60)
        fixture.now += 59
        self.assertTrue(fixture.evaluate()["blocked"])
        fixture.now += 1
        self.assertFalse(fixture.evaluate()["blocked"])

    def test_missing_contact_without_registry_area_remains_unknown(self):
        fixture = Fixture([FOREIGN])
        fixture.entities.pop(FOREIGN)
        result = fixture.evaluate()
        self.assertEqual(result["contacts"], [FOREIGN])
        self.assertEqual(result["status"], "window_state_unknown")
        self.assertEqual(result["unknown_contacts"], [FOREIGN])
        self.assertTrue(result["blocked"])
        self.assertFalse(result["stop_requested"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
