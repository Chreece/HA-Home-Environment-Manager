"""Observed target/output history: honest intervals, bounds and WS ownership."""
from __future__ import annotations

import importlib
import json
import math
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "hem075controlhistorytest"
package = ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components/environment_manager")]
sys.modules[PACKAGE] = package
control = importlib.import_module(PACKAGE + ".control_history")
environment = importlib.import_module(PACKAGE + ".environment_history")
History = control.ControlHistory
BASE = 1_790_000_000.0
SOURCES = ["sensor.room_temperature"]


def observation(controller="controller", *, metric="temperature", sources=None,
                context=None, target=21., measured=20., profile="home", mode="heat",
                method="pid", demand=10., output=None, output_kind=None,
                target_kind="control", **point):
    basis, unit, _low, _high = control._QUANTITIES[metric]
    return {
        "controller_id": controller, "area_id": "room", "name": "Room device " + controller,
        "source_entity_ids": ["climate.heater"], "metric": metric, "basis": basis, "unit": unit,
        "feedback_source_ids": SOURCES if sources is None else sources,
        "context_id": context, "target_kind": target_kind,
        "point": {"target": target, "measured": measured, "profile": profile, "mode": mode,
                  "control_mode": method, "demand_percent": demand, "output_percent": output,
                  "output_kind": output_kind, **point},
    }


def stored(history):
    return json.loads(json.dumps(history.snapshot(), allow_nan=False))


def points(history, *, metric="temperature", sources=None, now=BASE + 3600, controller=0, series=0):
    result = history.view("room", metric, SOURCES if sources is None else sources, now=now)
    return result[controller]["series"][series]["points"] if result else []


class ControlHistoryTests(unittest.TestCase):
    def test_targets_and_modes_change_at_observed_time_without_backfill(self):
        history = History()
        history.observe(observation(), now=BASE)
        history.observe(observation(measured=20.1), now=BASE + 30)
        # Feedback sampling does not turn every sensor report into an event.
        self.assertEqual(len(points(history)), 1)
        self.assertEqual(points(history)[0]["until"], BASE + 30)
        history.observe(observation(target=19., profile="eco", demand=0.), now=BASE + 45)
        values = points(history)
        self.assertEqual([(p["t"], p["until"], p["target"], p["profile"]) for p in values],
                         [(BASE, BASE + 45, 21., "home"),
                          (BASE + 45, BASE + 45, 19., "eco")])
        before = stored(history)
        later = points(history, now=BASE + 8000)
        self.assertEqual(later, values)
        self.assertEqual(stored(history), before)
        self.assertFalse(history.observe(observation(target=22.), now=BASE + 20))
        self.assertEqual(stored(history), before)

    def test_pid_demand_reported_activity_and_missing_output_remain_distinct(self):
        history = History()
        history.observe(observation(demand=34.26, output=100, output_kind="activity",
                                    output_entity_id="climate.heater", output_reported_at=BASE,
                                    demand_reported_at=BASE), now=BASE)
        history.observe(observation(demand=34.26, output=0, output_kind="activity",
                                    output_entity_id="climate.heater", output_reported_at=BASE + 12), now=BASE + 12)
        history.observe(observation(demand=34.26, output=None, output_kind="activity"), now=BASE + 20)
        values = points(history)
        self.assertEqual([p["demand_percent"] for p in values], [34.3, 34.3, 34.3])
        self.assertEqual([p["output_percent"] for p in values], [100., 0., None])
        self.assertTrue(all(p["output_kind"] == "activity" for p in values))
        # A service request or missing physical source is not a report of ON.
        history.observe(observation(demand=None, output=100, output_kind="binary",
                                    output_entity_id="climate.some_other_device",
                                    demand_reported_at=BASE), now=BASE + 25)
        self.assertIsNone(points(history)[-1]["output_percent"])
        self.assertNotIn("demand_reported_at", points(history)[-1])
        self.assertEqual(points(history)[0]["demand_reported_at"], BASE)

    def test_range_off_and_manual_native_targets_preserve_their_meaning(self):
        history = History()
        history.observe(observation(target=None, target_low=20., target_high=24.,
                                    mode="heat_cool", method="automatic"), now=BASE)
        history.observe(observation(target=None, mode="off", method="off", demand=None), now=BASE + 10)
        values = points(history)
        self.assertEqual((values[0]["target"], values[0]["target_low"], values[0]["target_high"]),
                         (None, 20., 24.))
        self.assertTrue(all(values[1][key] is None for key in ("target", "target_low", "target_high")))
        history.observe(observation(target=5., target_kind="physical_device", method="manual"),
                        now=BASE + 20)
        series = history.view("room", "temperature", SOURCES, now=BASE + 20)[0]["series"]
        self.assertEqual([row["target_kind"] for row in series], ["control", "physical_device"])
        self.assertEqual(series[1]["points"][0]["target"], 5.)

    def test_restart_and_missing_inventory_do_not_extend_the_previous_target(self):
        history = environment.EnvironmentHistory()
        history.control.observe(observation(), now=BASE)
        history.control.observe(observation(), now=BASE + 30)
        restored = environment.EnvironmentHistory.restore(stored(history), now=BASE + 120)
        restored.control.observe(observation(target=23.), now=BASE + 150)
        values = points(restored.control)
        self.assertEqual(values[0]["until"], BASE + 30)
        self.assertTrue(values[1]["break_before"])
        restored.control.reconcile([], now=BASE + 170)
        restored.control.observe(observation(target=22.), now=BASE + 180)
        values = points(restored.control)
        self.assertEqual(values[1]["until"], BASE + 150)
        self.assertTrue(values[2]["break_before"])
        self.assertTrue(all(point["target_break_before"] for point in values[1:]))
        reloaded = environment.EnvironmentHistory.restore(stored(restored), now=BASE + 185)
        self.assertEqual(points(reloaded.control), values)
        self.assertEqual(stored(restored)["version"], 1)
        legacy = environment.EnvironmentHistory.restore(
            {"version": 1, "areas": {}, "averages": {}, "daily": {}}, now=BASE)
        self.assertEqual(legacy.control.view("room", "temperature", SOURCES, now=BASE), [])

    def test_sources_contexts_and_peer_controllers_are_never_combined(self):
        history = History()
        history.reconcile([observation("first"), observation("second", target=22.)], now=BASE)
        alternate = observation("first", sources=["sensor.alternate"], target=23.)
        history.reconcile_controller("first", [alternate], now=BASE + 30)
        history.reconcile_controller("first", [observation("first")], now=BASE + 60)
        original = points(history, now=BASE + 60)
        self.assertEqual(original[0]["until"], BASE)
        self.assertTrue(original[-1]["break_before"])
        peer = points(history, now=BASE + 60, controller=1)
        self.assertEqual(len(peer), 1)
        # Updating one controller cannot pause or extend the other one.
        history.observe(observation("second", target=22.), now=BASE + 90)
        self.assertEqual(points(history, now=BASE + 90, controller=1)[0]["until"], BASE + 90)
        self.assertEqual(points(history, sources=["sensor.alternate"], now=BASE + 90)[0]["target"], 23.)
        self.assertEqual(points(history, sources=["sensor.unrelated"], now=BASE + 90), [])

    def test_mold_and_derived_room_humidity_use_separate_quantities(self):
        history = History()
        humidity_sources = ["sensor.rh"]
        mold_sources = ["sensor.rh", "sensor.room_temperature", "weather.home"]
        mold = observation(metric="mold", sources=mold_sources, context="calibration_one",
                           target=60., measured=64.4, mode="dry")
        rh = observation(metric="humidity", sources=humidity_sources, context="calibration_one",
                         target=44.2, measured=49., mode="dry", target_kind="derived_room_rh")
        history.reconcile([mold, rh], now=BASE)
        self.assertEqual(points(history, metric="mold", sources=[])[0]["target"], 60.)
        self.assertEqual(points(history, metric="humidity", sources=humidity_sources)[0]["target"], 44.2)
        self.assertEqual(points(history, metric="humidity", sources=mold_sources), [])
        mold["context_id"] = "calibration_two"
        history.reconcile([mold, rh], now=BASE + 30)
        series = history.view("room", "mold", [], now=BASE + 30)[0]["series"]
        self.assertEqual([row["context_id"] for row in series], ["calibration_one", "calibration_two"])
        self.assertEqual(series[0]["points"][0]["until"], BASE)

    def test_long_gap_stays_a_gap_and_heartbeat_keeps_actual_observations(self):
        history = History()
        history.observe(observation(), now=BASE)
        history.observe(observation(measured=20.5), now=BASE + 300)
        history.observe(observation(measured=20.6), now=BASE + 1501)
        values = points(history)
        self.assertEqual([p["measured"] for p in values], [20., 20.5, 20.6])
        self.assertEqual([p["until"] for p in values], [BASE + 300, BASE + 300, BASE + 1501])
        self.assertTrue(values[-1]["break_before"])
        self.assertFalse(values[-1].get("target_break_before"))

    def test_recently_confirmed_interval_survives_delayed_next_heartbeat(self):
        history = History()
        history.observe(observation(), now=BASE)
        history.observe(observation(), now=BASE + 290)
        history.observe(observation(), now=BASE + 1180)
        self.assertEqual(points(history)[0]["until"], BASE + 1180)
        restored = History.restore(stored(history), now=BASE + 1180)
        self.assertEqual(points(restored, now=BASE + 1180), points(history, now=BASE + 1180))

    def test_restore_rejects_corrupt_metadata_and_sanitizes_values_and_intervals(self):
        history = History()
        history.observe(observation(), now=BASE)
        history.observe(observation(target=22.), now=BASE + 30)
        raw = stored(history)
        rows = raw["controllers"][0]["series"][0]["points"]
        rows[0].update(target=math.nan, measured=True, demand_percent=math.inf,
                       output_percent=75, output_kind="binary", until=BASE + 40)
        rows.append({**rows[1], "t": BASE + 40, "until": BASE + 2000})
        restored = History.restore(raw, now=BASE + 50)
        values = points(restored, now=BASE + 50)
        self.assertEqual(len(values), 2)
        self.assertIsNone(values[0]["target"])
        self.assertIsNone(values[0]["measured"])
        self.assertIsNone(values[0]["demand_percent"])
        self.assertIsNone(values[0]["output_percent"])
        self.assertEqual(values[0]["until"], BASE + 30)
        json.dumps(restored.snapshot(), allow_nan=False)
        raw["controllers"][0]["series"][0]["unit"] = "%"
        self.assertEqual(History.restore(raw, now=BASE + 50).snapshot()["controllers"], [])
        for update in ({"metric": {}}, {"feedback_source_ids": [None]}, {"target_kind": []},
                       {"controller_id": "x" * 256}, {"context_id": "x" * 129}):
            self.assertFalse(history.observe({**observation(), **update}, now=BASE + 60))

    def test_restored_series_cannot_change_the_containing_owner_or_room(self):
        history = History()
        history.observe(observation(), now=BASE)
        raw = stored(history)
        raw["controllers"][0]["series"][0].update(controller_id="other", area_id="other_room")
        restored = History.restore(raw, now=BASE + 60)
        self.assertEqual(restored.snapshot()["controllers"][0]["controller_id"], "controller")
        self.assertEqual(restored.view("other_room", "temperature", SOURCES, now=BASE + 60), [])

    def test_global_budget_spans_many_controllers_and_retains_latest_events(self):
        history = History()
        # Exercise the actual production global bound with 20 distinct devices;
        # a separate series cap alone cannot contain a whole home's payload.
        count = control.CONTROL_MAX_TOTAL_POINTS // 20 + 10
        for index in range(count):
            for controller in range(20):
                history.observe(observation(str(controller), target=20. + index % 2), now=BASE + index)
        snapshot = history.snapshot()
        retained = [point for device in snapshot["controllers"]
                    for series in device["series"] for point in series["points"]]
        self.assertEqual(len(retained), control.CONTROL_MAX_TOTAL_POINTS)
        self.assertEqual(len(snapshot["controllers"]), 20)
        self.assertEqual(max(point["t"] for point in retained), BASE + count - 1)
        self.assertLess(len(json.dumps(snapshot, allow_nan=False).encode()), 16_000_000)
        self.assertLessEqual(len(history._oldest), 2 * 20 + 1024)
        restored = History.restore(snapshot, now=BASE + count)
        self.assertEqual(sum(len(s["points"]) for c in restored.snapshot()["controllers"]
                             for s in c["series"]), control.CONTROL_MAX_TOTAL_POINTS)
        before = stored(history)
        self.assertEqual(history.view("room", "temperature", SOURCES,
                                      now=BASE + count + control.CONTROL_MAX_AGE + 1), [])
        self.assertEqual(stored(history), before)

    def test_context_controller_and_per_series_limits_apply_independently(self):
        history = History()
        # Small patched budgets exercise each eviction boundary without making
        # another large synthetic workload duplicate the global-budget test.
        with patch.object(control, "CONTROL_MAX_CONTROLLERS", 3), \
                patch.object(control, "CONTROL_MAX_SERIES", 2), \
                patch.object(control, "CONTROL_MAX_POINTS", 4):
            for index in range(10):
                history.observe(observation(target=20. + index % 2), now=BASE + index)
            self.assertEqual(len(points(history)), 4)
            for index in range(4):
                history.observe(observation(context=str(index)), now=BASE + 20 + index)
            self.assertEqual(len(history.snapshot()["controllers"][0]["series"]), 2)
            for index in range(4):
                history.observe(observation(str(index)), now=BASE + 40 + index)
            self.assertEqual(len(history.snapshot()["controllers"]), 3)
            self.assertEqual([c["controller_id"] for c in history.snapshot()["controllers"]],
                             ["1", "2", "3"])


def module(name, **attributes):
    result = ModuleType(name)
    result.__dict__.update(attributes)
    sys.modules[name] = result
    return result


module("probatio", Required=lambda key: key, In=lambda values: lambda value: value)
module("homeassistant")
module("homeassistant.auth")
module("homeassistant.auth.permissions")
module("homeassistant.auth.permissions.const", POLICY_READ="read")
module("homeassistant.components")
registered = []
module("homeassistant.components.websocket_api", ActiveConnection=object,
       websocket_command=lambda schema: lambda function: function,
       ERR_NOT_FOUND="not_found", ERR_UNAUTHORIZED="unauthorized",
       async_register_command=lambda hass, command: registered.append(command))
module("homeassistant.core", HomeAssistant=object, callback=lambda function: function)
module("homeassistant.helpers")
module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry)
module(PACKAGE + ".controller_inventory", controller_inventory=lambda manager: [])
api = importlib.import_module(PACKAGE + ".dashboard_api")


class ControlTrendWebSocketTests(unittest.TestCase):
    def setUp(self):
        self.history = environment.EnvironmentHistory()
        self.history.control.observe(observation(), now=BASE)
        self.report = {"measurement_evidence": {
            "temperature": {"source_ids": SOURCES, "source_count": 1, "value": 20.}},
            "mold_trend": {"source_ids": [], "source_count": 0, "value": 64.4}}
        self.manager = N(entry=N(entry_id="owner"), _stopping=False, _environment_history=self.history,
                         plan=N(rooms=(N(area_id="room"),), climate_rooms=(),
                                environment={"room": self.report}))
        self.record = N(platform="environment_manager", config_entry_id="owner",
                        unique_id="owner_recommendation")
        self.records = {"sensor.hem": self.record}
        self.hass = N(data={"environment_manager": {"owner": self.manager}},
                      registry=N(async_get=self.records.get))
        self.results, self.errors, self.permissions = [], [], []
        self.allowed = True

        def permitted(entity, policy):
            self.permissions.append((entity, policy))
            return self.allowed

        self.connection = N(user=N(is_admin=False, permissions=N(check_entity=permitted)),
                            send_result=lambda request, result: self.results.append(result),
                            send_error=lambda request, code, message: self.errors.append(code))

    def request(self, **changes):
        message = {"id": 1, "type": api.CONTROL_TREND_COMMAND, "entity_id": "sensor.hem",
                   "area_id": "room", "metric": "temperature", "source_ids": SOURCES, **changes}
        with patch.object(api.time, "time", return_value=BASE + 60):
            api.websocket_control_trend(self.hass, self.connection, message)

    def test_single_sensor_and_exact_mean_sources_authorize_without_writes(self):
        before = stored(self.history)
        self.request()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.permissions, [("sensor.hem", "read")])
        self.assertEqual(self.results[-1]["source_ids"], SOURCES)
        self.assertEqual(self.results[-1]["controllers"][0]["series"][0]["points"][0]["until"], BASE)
        self.assertEqual(stored(self.history), before)
        mean = SOURCES + ["sensor.other_temperature"]
        self.report["measurement_evidence"]["temperature"].update(source_ids=mean, source_count=2)
        self.history.control.observe(observation(sources=mean), now=BASE + 30)
        self.request(source_ids=list(reversed(mean)))
        self.assertEqual(self.results[-1]["source_ids"], sorted(mean))
        self.assertEqual(len(self.results[-1]["controllers"][0]["series"]), 1)
        self.assertEqual(self.results[-1]["controllers"][0]["series"][0]["feedback_source_ids"], sorted(mean))

    def test_source_mismatch_unmonitored_room_wrong_owner_and_permission_are_denied(self):
        for changes in ({"source_ids": ["sensor.foreign"]}, {"source_ids": []},
                        {"source_ids": SOURCES * 2}, {"source_ids": [None]},
                        {"source_ids": ["climate.heater"]}, {"area_id": "outside"},
                        {"metric": "noise"}, {"entity_id": "sensor.foreign"}):
            with self.subTest(changes=changes):
                self.request(**changes)
                self.assertEqual(self.results, [])
                self.assertEqual(self.errors[-1], "not_found")
        self.allowed = False
        self.request()
        self.assertEqual(self.errors[-1], "unauthorized")
        self.allowed = True
        self.record.unique_id = "other_recommendation"
        self.request()
        self.assertEqual(self.results, [])
        self.assertEqual(self.errors[-1], "not_found")

    def test_native_contributor_chart_never_borrows_the_whole_mean_controller(self):
        mean = SOURCES + ["sensor.other_temperature"]
        self.report["measurement_evidence"]["temperature"].update(source_ids=mean, source_count=2)
        # Replace the original single-sensor history with a mean-only owner.
        self.history.control = History()
        self.history.control.observe(observation(sources=mean), now=BASE)
        self.request(source_ids=SOURCES)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.results[-1]["controllers"], [])
        self.history.control.observe(observation("single", sources=SOURCES, target=19.), now=BASE + 10)
        self.request(source_ids=SOURCES)
        self.assertEqual([row["controller_id"] for row in self.results[-1]["controllers"]], ["single"])
        self.assertEqual(self.results[-1]["controllers"][0]["series"][0]["points"][0]["target"], 19.)
        # A missing current reading remains an authorized configured sensor;
        # removing its actual room membership removes that permission.
        self.report["measurement_evidence"].clear()
        self.manager.plan.rooms[0].readings = (N(entity_id=SOURCES[0], metric="temperature", value=None),)
        self.request(source_ids=SOURCES)
        self.assertEqual(self.errors, [])
        self.manager.plan.rooms[0].readings = ()
        before = len(self.results)
        self.request(source_ids=SOURCES)
        self.assertEqual(len(self.results), before)
        self.assertEqual(self.errors[-1], "not_found")

    def test_removed_controller_retains_only_its_closed_historical_intervals(self):
        self.history.control.observe(observation(), now=BASE + 20)
        self.history.control.reconcile([], now=BASE + 30)
        self.request()
        values = self.results[-1]["controllers"][0]["series"][0]["points"]
        self.assertEqual(values[-1]["until"], BASE + 20)
        self.assertEqual(values[-1]["target"], 21.)

    def test_production_collector_payload_survives_storage_and_authorized_transport(self):
        actual = runpy.run_path(str(ROOT / ".github/tests/test_075_control_trend_capture.py"))
        payload = actual["fixture_payload"]()
        for metric in ("temperature", "humidity", "mold"):
            with self.subTest(metric=metric):
                envelope = payload[metric]
                self.history.control = History.restore(
                    {"version": 1, "controllers": envelope["controllers"]}, now=payload["now"])
                if metric != "mold":
                    self.report["measurement_evidence"][metric] = {
                        "source_ids": envelope["source_ids"],
                        "source_count": len(envelope["source_ids"]), "value": None,
                    }
                before = stored(self.history)
                with patch.object(api.time, "time", return_value=payload["now"]):
                    api.websocket_control_trend(self.hass, self.connection, {
                        "id": 1, "type": api.CONTROL_TREND_COMMAND, "entity_id": "sensor.hem",
                        "area_id": "room", "metric": metric, "source_ids": envelope["source_ids"],
                    })
                self.assertEqual(self.errors, [])
                self.assertEqual(self.results[-1]["controllers"], envelope["controllers"])
                self.assertEqual(stored(self.history), before)
                json.dumps(self.results[-1], allow_nan=False)

    def test_mold_has_own_calibrated_provenance_and_missing_history_is_empty(self):
        self.request(metric="mold", source_ids=[])
        self.assertEqual(self.results[-1]["controllers"], [])
        self.history.control.observe(observation(metric="mold", sources=["sensor.rh", "weather.home"],
                                                 context="calibrated", target=60., measured=64.4), now=BASE)
        self.request(metric="mold", source_ids=[])
        result = self.results[-1]
        self.assertEqual(result["source_ids"], [])
        self.assertEqual(result["controllers"][0]["series"][0]["basis"], "mold_surface_rh")
        self.assertEqual(result["controllers"][0]["series"][0]["points"][0]["target"], 60.)
        self.request(metric="mold", source_ids=["sensor.rh"])
        self.assertEqual(self.errors[-1], "not_found")

    def test_stopped_manager_and_bad_evidence_never_grant_history_access(self):
        self.manager._stopping = True
        self.request()
        self.assertEqual(self.results, [])
        self.manager._stopping = False
        self.report["measurement_evidence"]["temperature"]["source_count"] = True
        self.request()
        self.assertEqual(self.results, [])
        self.assertEqual(self.errors[-1], "not_found")

    def test_dashboard_advertises_supported_transport_and_registers_it(self):
        with patch.object(api, "manager_dashboard_snapshot", return_value={"rooms": []}):
            api.websocket_dashboard(self.hass, self.connection,
                                    {"id": 1, "type": api.COMMAND, "entity_id": "sensor.hem"})
        self.assertEqual(self.results[-1]["control_trend_version"], 1)
        registered.clear()
        api.async_register_dashboard_api(self.hass)
        self.assertIn(api.websocket_control_trend, registered)


if __name__ == "__main__":
    unittest.main()
