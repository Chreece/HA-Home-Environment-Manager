"""Retained trend detail, genuine outage boundaries and read-only WS ownership.

Exercise the actual history and WebSocket handlers. Home Assistant transport
and permissions are simulated; no Recorder, live devices or files are touched.
"""
from __future__ import annotations

import importlib
import json
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "hem074trendtest"
package = ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components/environment_manager")]
sys.modules[PACKAGE] = package
history_module = importlib.import_module(PACKAGE + ".environment_history")
History = history_module.EnvironmentHistory
BASE = 1_790_000_000.0
SOURCES = ["sensor.temperature_a", "sensor.temperature_b"]


def snapshot(history):
    return json.loads(json.dumps(history.snapshot(), allow_nan=False))


class RetainedTrendTests(unittest.TestCase):
    def week(self, *, missing_index=None):
        history = History()
        for index in range(672):
            if index == missing_index:
                history.pause_average("room", "temperature", now=BASE + (index - 1) * 900 + 60)
            history.add_average("room", "temperature", SOURCES,
                                20 + (index % 9) / 10, now=BASE + index * 900)
        return history, BASE + 671 * 900

    def test_daily_view_receives_every_retained_average_without_overview_growth(self):
        history, now = self.week()
        before = snapshot(history)
        overview = history.average_trend("room", "temperature", SOURCES)
        detailed = history.average_points("room", "temperature", SOURCES, now=now)
        self.assertLessEqual(len(overview), 73)
        self.assertLessEqual(sum(point["t"] >= now - 86400 for point in overview), 12)
        self.assertEqual(len(detailed), 672)
        self.assertEqual(sum(point["t"] >= now - 86400 for point in detailed), 97)
        self.assertEqual(detailed, before["averages"]["room"]["temperature"]["points"])
        self.assertFalse(any(point.get("break_before") for point in detailed))
        self.assertEqual(snapshot(history), before)
        # No current-value anchor may masquerade as a newly recorded sample.
        later = history.average_points("room", "temperature", SOURCES, now=now + 60)
        self.assertEqual(later[-1]["t"], now)

    def test_short_average_outage_keeps_adjacent_actual_boundaries(self):
        history, now = self.week(missing_index=600)
        detailed = history.average_points("room", "temperature", SOURCES, now=now)
        self.assertEqual([index for index, point in enumerate(detailed)
                          if point.get("break_before")], [600])
        self.assertEqual(detailed[600]["t"] - detailed[599]["t"], 900)
        overview = history.average_trend("room", "temperature", SOURCES)
        interrupted = next(index for index, point in enumerate(overview)
                           if point.get("break_before"))
        self.assertGreater(overview[interrupted]["t"] - overview[interrupted - 1]["t"], 900)

    def test_source_sets_and_retention_are_never_combined(self):
        history, now = self.week()
        alternate = [SOURCES[0], "sensor.temperature_other"]
        history.add_average("room", "temperature", alternate, 99., now=now + 60)
        self.assertEqual(history.average_points("room", "temperature", alternate, now=now + 60),
                         [{"t": now + 60, "v": 99.}])
        original = history.average_points("room", "temperature", SOURCES, now=now + 60)
        self.assertTrue(all(point["v"] < 30 for point in original))
        self.assertLessEqual(len(original), 672)
        self.assertEqual(history.average_points("room", "temperature", SOURCES,
                                               now=now + 604801), [])
        for invalid in (SOURCES[:1], [SOURCES[0], SOURCES[0]], [None, SOURCES[0]]):
            self.assertEqual(history.average_points("room", "temperature", invalid, now=now), [])

    def test_daily_mold_view_retains_raw_density_and_actual_missing_snapshots(self):
        rows = [{"t": BASE + index * 300, "surface_rh": 65 + index % 5}
                for index in range(2017)]
        rows[1900].pop("surface_rh")
        history = History(areas={"room": rows})
        now = rows[-1]["t"]
        before = snapshot(history)
        detailed = history.mold_points("room", now=now)
        self.assertEqual(len(detailed), 2017)
        self.assertEqual(sum(point["t"] >= now - 86400 for point in detailed), 289)
        self.assertEqual(detailed[1900], {"t": rows[1900]["t"], "v": None})
        self.assertEqual(detailed[1901], {"t": rows[1901]["t"], "v": 66.})
        self.assertLessEqual(len(history.mold_trend("room", now=now)), 96)
        self.assertEqual(snapshot(history), before)
        self.assertEqual(history.mold_points("room", now=now + 60)[-1]["t"], now)

    def test_mold_detail_filters_bad_times_and_marks_bad_values_as_missing(self):
        rows = [
            {"t": BASE - 604801, "surface_rh": 40},
            {"t": BASE - 1200, "surface_rh": 50},
            {"t": BASE - 900, "surface_rh": math.nan},
            {"t": BASE - 600, "surface_rh": 101},
            {"t": BASE - 300, "surface_rh": True},
            {"t": BASE, "surface_rh": 60},
            {"t": BASE + 61, "surface_rh": 70},
        ]
        history = History(areas={"room": rows})
        detailed = history.mold_points("room", now=BASE)
        self.assertEqual([point["v"] for point in detailed], [50., None, None, None, 60.])
        self.assertTrue(history.mold_trend("room", now=BASE)[-1]["break_before"])
        self.assertEqual(history.mold_points("other_room", now=BASE), [])
        self.assertEqual(history.mold_points("room", now=math.nan), [])

    def test_five_minute_precision_does_not_drop_a_regular_snapshot(self):
        history = History()
        start = BASE + 0.0006
        self.assertTrue(history.add("room", {"surface_rh": 60}, now=start))
        self.assertTrue(history.add("room", {"surface_rh": 61}, now=start + 300))
        self.assertEqual(len(history.samples("room")), 2)

    def test_short_mold_unavailability_survives_sampling_throttle_and_restart(self):
        history = History()
        history.add("room", {"surface_rh": 60}, now=BASE)
        self.assertFalse(history.add("room", {"surface_rh": 61}, now=BASE + 20))
        self.assertTrue(history.add("room", {}, now=BASE + 30))
        self.assertFalse(history.add("room", {}, now=BASE + 40))
        self.assertTrue(history.add("room", {"surface_rh": 62}, now=BASE + 60))
        restored = History.restore(snapshot(history), now=BASE + 90)
        self.assertTrue(restored.add("room", {"surface_rh": 63}, now=BASE + 120))
        detailed = restored.mold_points("room", now=BASE + 120)
        self.assertEqual([point["v"] for point in detailed], [60., None, 62., 63.])
        self.assertTrue(detailed[-1]["break_before"])
        self.assertEqual(restored.snapshot()["version"], 1)
        again = History.restore(snapshot(restored), now=BASE + 120)
        self.assertEqual(again.mold_points("room", now=BASE + 120), detailed)
        self.assertTrue(again.mold_trend("room", now=BASE + 120)[-1]["break_before"])


# Import the actual WS handlers with just their external HA boundary simulated.
def module(name, **attributes):
    value = ModuleType(name)
    value.__dict__.update(attributes)
    sys.modules[name] = value
    return value


module("probatio", Required=lambda key: key, In=lambda values: lambda value: value)
module("homeassistant")
module("homeassistant.auth")
module("homeassistant.auth.permissions")
module("homeassistant.auth.permissions.const", POLICY_READ="read")
module("homeassistant.components")
registered = []
websocket = module(
    "homeassistant.components.websocket_api", ActiveConnection=object,
    websocket_command=lambda schema: lambda function: function,
    ERR_NOT_FOUND="not_found", ERR_UNAUTHORIZED="unauthorized",
    async_register_command=lambda hass, command: registered.append(command),
)
module("homeassistant.core", HomeAssistant=object, callback=lambda function: function)
module("homeassistant.helpers")
module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry)
module(PACKAGE + ".controller_inventory", controller_inventory=lambda manager: [])
api = importlib.import_module(PACKAGE + ".dashboard_api")


class TrendWebSocketTests(unittest.TestCase):
    def setUp(self):
        self.history = History()
        self.history.add_average("room", "temperature", SOURCES, 21., now=BASE)
        self.history.add("room", {"surface_rh": 65.}, now=BASE)
        self.report = {
            "measurement_evidence": {"temperature": {
                "value": 21., "source_ids": SOURCES, "source_count": 2,
            }},
            "mold_trend": {"value": 65., "source_ids": [], "source_count": 0},
        }
        self.manager = N(
            entry=N(entry_id="one"), _stopping=False, _environment_history=self.history,
            plan=N(rooms=(N(area_id="room"),), climate_rooms=(), environment={"room": self.report}),
        )
        self.record = N(config_entry_id="one", platform="environment_manager",
                        unique_id="one_recommendation")
        self.entities = {"sensor.hem_one": self.record}
        self.hass = N(data={"environment_manager": {"one": self.manager}},
                      registry=N(async_get=self.entities.get))
        self.results, self.errors, self.permission_checks = [], [], []
        self.allowed = True

        def check(entity, policy):
            self.permission_checks.append((entity, policy))
            return self.allowed

        self.connection = N(
            user=N(is_admin=False, permissions=N(check_entity=check)),
            send_result=lambda request, result: self.results.append((request, result)),
            send_error=lambda request, code, message: self.errors.append((request, code, message)),
        )

    def request(self, **changes):
        message = {"id": 7, "type": api.TREND_COMMAND,
                   "entity_id": "sensor.hem_one", "area_id": "room", "metric": "temperature",
                   **changes}
        with patch.object(api.time, "time", return_value=BASE + 60):
            api.websocket_trend(self.hass, self.connection, message)

    def test_authorized_user_gets_exact_detail_without_writing_or_querying_recorder(self):
        before = snapshot(self.history)
        self.request()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.permission_checks, [("sensor.hem_one", "read")])
        self.assertEqual(self.results, [(7, {
            "area_id": "room", "metric": "temperature", "source_ids": SOURCES,
            "source_count": 2, "trend": [{"t": BASE, "v": 21.}],
            "retention_seconds": 604800, "sample_interval_seconds": 900,
        })])
        self.assertEqual(snapshot(self.history), before)
        self.request(metric="mold")
        result = self.results[-1][1]
        self.assertEqual(result["trend"], [{"t": BASE, "v": 65.}])
        self.assertEqual(result["source_ids"], [])
        self.assertEqual(result["sample_interval_seconds"], 300)

    def test_unauthorized_user_never_receives_any_history(self):
        self.allowed = False
        self.request()
        self.assertEqual(self.results, [])
        self.assertEqual(self.errors[-1][1], "unauthorized")

    def test_wrong_entity_owner_room_metric_and_stopped_manager_are_rejected(self):
        for changes in ({"entity_id": "sensor.external"}, {"entity_id": "climate.hem_one"},
                        {"area_id": "other"}, {"area_id": "__outside__"},
                        {"metric": "unconfigured"}):
            with self.subTest(changes=changes):
                self.request(**changes)
                self.assertEqual(self.results, [])
                self.assertEqual(self.errors[-1][1], "not_found")
        self.record.unique_id = "other_recommendation"
        self.request()
        self.assertEqual(self.results, [])
        self.record.unique_id = "one_recommendation"
        self.manager._stopping = True
        self.request()
        self.assertEqual(self.results, [])
        self.manager._stopping = False
        self.manager.entry.entry_id = "another"
        self.request()
        self.assertEqual(self.results, [])

    def test_current_source_set_is_required(self):
        aggregate = self.report["measurement_evidence"]["temperature"]
        aggregate["source_ids"] = [SOURCES[0], "sensor.other"]
        self.request()
        self.assertEqual(self.results[-1][1]["trend"], [])
        self.assertEqual(self.results[-1][1]["source_ids"], aggregate["source_ids"])
        for updates in ({"source_count": 1}, {"source_count": True},
                        {"source_ids": [SOURCES[0], SOURCES[0]], "source_count": 2},
                        {"source_ids": [SOURCES[0], None]}):
            with self.subTest(updates=updates):
                aggregate.update(updates)
                prior = len(self.results)
                self.request()
                self.assertEqual(len(self.results), prior)
                self.assertEqual(self.errors[-1][1], "not_found")

    def test_missing_current_value_does_not_erase_recorded_history(self):
        self.report["measurement_evidence"]["temperature"]["value"] = None
        self.report["mold_trend"]["value"] = None
        self.request()
        self.assertEqual(self.results[-1][1]["trend"], [{"t": BASE, "v": 21.}])
        self.request(metric="mold")
        self.assertEqual(self.results[-1][1]["trend"], [{"t": BASE, "v": 65.}])
        self.assertEqual(self.errors, [])

    def test_climate_only_rooms_have_the_same_ownership_checks(self):
        self.manager.plan.climate_rooms = self.manager.plan.rooms
        self.manager.plan.rooms = ()
        self.request()
        self.assertEqual(self.errors, [])
        self.assertEqual(len(self.results), 1)
        self.manager.plan.climate_rooms = ()
        self.request()
        self.assertEqual(len(self.results), 1)
        self.assertEqual(self.errors[-1][1], "not_found")

    def test_dashboard_setup_registers_the_read_only_detail_command(self):
        registered.clear()
        api.async_register_dashboard_api(self.hass)
        self.assertEqual(registered, [api.websocket_dashboard, api.websocket_trend])


if __name__ == "__main__":
    unittest.main()
