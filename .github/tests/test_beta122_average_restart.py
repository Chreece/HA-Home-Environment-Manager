"""Beta122: retain measured average history across restarts and source outages.

Exercises actual discovery, environmental aggregation, Store snapshot/restore,
and dashboard consumers with the existing lightweight Home Assistant registry.
No device services or external history databases are used.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]
with redirect_stdout(StringIO()):
    fixture = runpy.run_path(str(ROOT / ".github/tests/test_beta65_data.py"))

env, mod, discovery, logic, dashboard = (
    fixture[key] for key in ("env", "history_mod", "dis", "logic", "dash")
)
History = mod.EnvironmentHistory
BASE = round(fixture["now"].timestamp(), 3)
SOURCES = ["sensor.average_a", "sensor.average_b", "sensor.average_c"]


def persisted(history):
    """Match the JSON data boundary used by Home Assistant Store."""
    return json.loads(json.dumps(history.snapshot(), allow_nan=False))


def series_rows(history, metric="humidity"):
    series = history.averages["room"][metric]
    return [series, *series.get("previous", [])]


class AverageRestartTests(unittest.TestCase):
    def setUp(self):
        self.states, self.entities = fixture["states"], fixture["entities"]
        self.states.clear()
        self.entities.clear()
        self.clock = BASE
        self.metric = "humidity"
        self.sources = SOURCES[:2]
        previous_clock = fixture["util"].dt.utcnow
        fixture["util"].dt.utcnow = lambda: datetime.fromtimestamp(self.clock, timezone.utc)
        self.addCleanup(setattr, fixture["util"].dt, "utcnow", previous_clock)

    def value(self, entity, value, *, restored=False, stale=False):
        metric = self.metric
        state = fixture["state"](entity, value, "°C" if metric == "temperature" else "%", metric)
        observed = datetime.fromtimestamp(self.clock, timezone.utc)
        state.last_updated = state.last_reported = observed - timedelta(hours=2 if stale else 0)
        if restored:
            state.attributes["restored"] = True
        self.states[entity] = state
        self.entities[entity] = fixture["N"](
            entity_id=entity, area_id="room", device_id=None, platform="test",
            device_class=None, original_device_class=metric,
        )

    def capture(self, history, offset, *, room_present=True):
        self.clock = BASE + offset
        selected = {"room": {
            "humidity": self.sources if self.metric == "humidity" else [],
            "temperature": self.sources if self.metric == "temperature" else [],
            "air_quality": [], "windows": [],
        }}
        rooms = discovery.rooms(
            fixture["hass"], ["room"] if room_present else [], 90,
            source_selections=selected,
        )
        report, changed = env.build_environment(
            fixture["hass"], rooms, rooms, (), (), history=history,
            max_age_minutes=90, source_selections=selected, now=self.clock,
        )
        if not room_present:
            return {}, changed
        return report["room"]["measurement_evidence"], changed

    def seed(self):
        history = History()
        for index, entity in enumerate(self.sources):
            self.value(entity, 40 + 10 * index)
        self.capture(history, 0)
        self.capture(history, 900)
        return history

    def test_restart_three_to_two_to_three_keeps_each_actual_source_set(self):
        for metric in ("humidity", "temperature"):
            with self.subTest(metric=metric):
                self.metric, self.sources = metric, SOURCES[:]
                self.clock = BASE
                history = self.seed()
                original = history.average_trend("room", metric, SOURCES)
                self.assertEqual([p["v"] for p in original], [50., 50.])
                history = History.restore(persisted(history), now=BASE + 960)
                # A restored HA state with a new startup timestamp is not a
                # live contributor. The two reported sources form their own mean.
                self.value(SOURCES[2], 60, restored=True)
                evidence, _ = self.capture(history, 960)
                partial = evidence[metric]
                self.assertEqual(partial["source_ids"], SOURCES[:2])
                self.assertEqual([p["v"] for p in partial["trend"]], [45.])
                self.assertEqual(history.average_trend("room", metric, SOURCES), original)
                # Save and restart once more while only the subset is live.
                history = History.restore(persisted(history), now=BASE + 990)
                self.value(SOURCES[2], 66)
                evidence, _ = self.capture(history, 990)
                resumed = evidence[metric]
                self.assertEqual(resumed["source_ids"], SOURCES)
                self.assertEqual(resumed["source_count"], 3)
                self.assertEqual([p["v"] for p in resumed["trend"]], [50., 50., 52.])
                self.assertTrue(resumed["trend"][-1]["break_before"])
                self.assertEqual(resumed["trend"][:2], original)
                self.assertEqual(history.average_trend("room", metric, SOURCES[:2]), partial["trend"])
                again = History.restore(persisted(history), now=BASE + 990)
                self.assertEqual(again.average_trend("room", metric, SOURCES), resumed["trend"])

    def test_short_observed_outages_persist_gaps_without_any_fake_average(self):
        for outage in ("unavailable", "restored", "stale", "missing", "zero", "room"):
            with self.subTest(outage=outage):
                self.clock = BASE
                self.states.clear()
                history = self.seed()
                original = history.average_trend("room", "humidity", self.sources)
                if outage == "missing":
                    del self.states[SOURCES[1]]
                elif outage == "zero":
                    for entity in self.sources:
                        self.value(entity, "unavailable")
                elif outage != "room":
                    self.value(SOURCES[1], "unavailable" if outage == "unavailable" else 50,
                               restored=outage == "restored", stale=outage == "stale")
                evidence, changed = self.capture(history, 930, room_present=outage != "room")
                self.assertTrue(changed, "the persisted gap itself must dirty the Store")
                self.assertTrue(history.averages["room"]["humidity"]["gap"])
                self.assertLess(evidence.get("humidity", {}).get("source_count", 0), 2)
                self.assertNotIn("trend", evidence.get("humidity", {}))
                self.assertEqual(history.average_trend("room", "humidity", self.sources), original)
                _, changed = self.capture(history, 940, room_present=outage != "room")
                self.assertFalse(changed, "repeated identical outage must not continually dirty storage")
                history = History.restore(persisted(history), now=BASE + 940)
                for index, entity in enumerate(self.sources):
                    self.value(entity, 42 + 10 * index)
                evidence, changed = self.capture(history, 960)
                self.assertTrue(changed)
                resumed = evidence["humidity"]["trend"]
                self.assertEqual([p["v"] for p in resumed], [45., 45., 47.])
                self.assertTrue(resumed[-1]["break_before"])
                self.assertEqual(resumed[-1]["t"], BASE + 960)

    def test_uninterrupted_samples_keep_the_fifteen_minute_cadence(self):
        history = self.seed()
        before = persisted(history)
        self.assertFalse(history.add_average("room", "humidity", self.sources, 47., now=BASE + 960))
        self.assertEqual(persisted(history), before)
        self.assertTrue(history.add_average("room", "humidity", self.sources, 47., now=BASE + 1800))
        trend = history.average_trend("room", "humidity", self.sources)
        self.assertEqual([p["v"] for p in trend], [45., 45., 47.])
        self.assertFalse(any(p.get("break_before") for p in trend))

    def test_restart_with_all_sources_ready_still_marks_unobserved_downtime(self):
        history = History.restore(persisted(self.seed()), now=BASE + 930)
        evidence, _ = self.capture(history, 960)
        trend = evidence["humidity"]["trend"]
        self.assertEqual([p["v"] for p in trend], [45., 45., 45.])
        self.assertTrue(trend[-1]["break_before"])

    def test_retention_bounds_are_shared_by_all_source_sets(self):
        history = History()
        for index in range(900):
            sources = ["sensor.fixed", f"sensor.member_{index % mod.AVG_MAX_SOURCE_SETS}"]
            history.add_average("room", "humidity", sources, float(index), now=BASE + index * 60)
        rows = series_rows(history)
        self.assertEqual(len(rows), mod.AVG_MAX_SOURCE_SETS)
        self.assertEqual(sum(len(row["points"]) for row in rows), mod.AVG_MAX_POINTS)
        history.add_average("room", "humidity", ["sensor.fixed", "sensor.new"], 900., now=BASE + 900 * 60)
        rows = series_rows(history)
        self.assertEqual(len(rows), mod.AVG_MAX_SOURCE_SETS)
        self.assertLessEqual(sum(len(row["points"]) for row in rows), mod.AVG_MAX_POINTS)
        restored = History.restore(persisted(history), now=BASE + 900 * 60)
        self.assertEqual([(row["sources"], row["points"]) for row in series_rows(restored)],
                         [(row["sources"], row["points"]) for row in rows])
        self.assertTrue(restored.pause_average("room", "humidity", now=BASE + 900 * 60 + mod.AVG_MAX_AGE + 1))
        self.assertEqual(restored.averages, {})

    def test_invalid_or_duplicate_sources_never_change_retained_history(self):
        history = self.seed()
        before = persisted(history)
        for sources, value in (([SOURCES[0]], 40.), ([SOURCES[0], SOURCES[0]], 40.),
                               ([SOURCES[0], "climate.fake"], 40.), (self.sources, float("nan"))):
            self.assertFalse(history.add_average("room", "humidity", sources, value, now=BASE + 1800))
            self.assertEqual(persisted(history), before)
        self.assertEqual(history.average_trend("room", "humidity", [SOURCES[0], SOURCES[2]]), [])

    def test_downsampling_propagates_skipped_gap_without_editing_actual_samples(self):
        history = History()
        for index in range(10):
            if index == 2:
                history.pause_average("room", "humidity", now=BASE + 1350)
            history.add_average("room", "humidity", self.sources, float(index), now=BASE + index * 900)
        before = persisted(history)
        view = history.average_trend("room", "humidity", self.sources, limit=3)
        self.assertEqual([(p["t"], p["v"]) for p in view],
                         [(BASE, 0.), (BASE + 4500, 5.), (BASE + 8100, 9.)])
        self.assertTrue(view[1]["break_before"])
        self.assertNotIn("break_before", view[2])
        self.assertNotIn("break_before", history.averages["room"]["humidity"]["points"][5])
        self.assertEqual(persisted(history), before)

    def test_legacy_store_migration_preserves_real_gaps_and_rejects_bad_archives(self):
        points = [{"t": BASE + i * 900 + (4500 if i >= 3 else 0), "v": float(i)}
                  for i in range(10)]
        legacy = {"version": 1, "areas": {}, "daily": {}, "averages": {"room": {
            "humidity": {"sources": self.sources, "points": points},
        }}}
        history = History.restore(legacy, now=points[-1]["t"])
        self.assertEqual(history.averages["room"]["humidity"]["points"], points)
        view = history.average_trend("room", "humidity", self.sources, limit=3)
        self.assertTrue(view[1]["break_before"])
        stored = persisted(history)
        stored["averages"]["room"]["humidity"]["previous"] = [
            None, {"sources": ["sensor.bad", {}], "points": points},
            {"sources": self.sources, "points": [{"t": points[-1]["t"], "v": 999.}]},
        ]
        restored = History.restore(stored, now=points[-1]["t"])
        self.assertEqual(len(series_rows(restored)), 1)
        self.assertEqual(restored.average_trend("room", "humidity", self.sources, limit=3), view)

    def test_dashboard_fallback_passes_exact_resumed_points_and_gap(self):
        history = self.seed()
        self.value(SOURCES[1], "unavailable")
        self.capture(history, 930)
        self.value(SOURCES[1], 52.)
        evidence, _ = self.capture(history, 960)
        aggregate = evidence["humidity"]
        fallback = logic.Reading("sensor.derived", "RH mean", "humidity", aggregate["value"],
                                 {"fallback_for_mold": True, "humidity_sensor_count": 2})
        room = logic.Room("room", "Room", (), (fallback,))
        plan = logic.evaluate((), (), (), (room,), fixture["constants"].DEFAULT_THRESHOLDS)
        plan = replace(plan, environment={"room": {"measurement_evidence": evidence}})
        payload = dashboard.dashboard_snapshot(plan, fixture["constants"].DEFAULT_THRESHOLDS)
        consumer = payload["rooms"][0]["readings"][0]["average_evidence"]
        self.assertEqual(consumer["trend"], aggregate["trend"])
        self.assertEqual(consumer["source_ids"], self.sources)
        self.assertTrue(consumer["trend"][-1]["break_before"])


if __name__ == "__main__":
    unittest.main()
