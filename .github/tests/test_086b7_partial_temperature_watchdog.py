"""A stale optional thermometer must not hide fresh independent OFF evidence.

Execute the real room-source mean and full OFF watchdog. Only native HA state,
registry, temperature freshness conversion and service transport are simulated.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import runpy
from types import SimpleNamespace as NS


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_b21_off_state_runtime.py"))
runtime, production, manager, spec, cap, state, env, record, cfg = (
    fixture[key] for key in (
        "runtime", "runtime_module", "manager", "spec", "cap", "state", "env", "record", "cfg"
    )
)
commands, messages = fixture["commands"], fixture["messages"]
room = fixture["module"]("room_sources", "room_sources.py")
production.room_temperature_evidence = room.room_temperature_evidence
discovery, registry = fixture["discovery"], fixture["entity_registry"]
FRESH = ("sensor.room_first", "sensor.room_second")
SLOW = "sensor.slow_temperature"
OWN = "sensor.appliance_temperature"
sensors = {}
readings = []
saved = []


async def save():
    saved.append(deepcopy(record["thermal_off_watch"]))


runtime._save = save


def sensor(value, at, *, device="independent-device"):
    return NS(state=str(value), attributes={}, device_id=device,
              last_reported=datetime.fromtimestamp(at, timezone.utc))


def temperature_sensor_c(_hass, entity, age_minutes):
    readings.append(entity)
    value = sensors.get(entity)
    if value is None or env["time"] - value.last_reported.timestamp() > age_minutes * 60:
        return None
    return float(value.state)


discovery.temperature_sensor_c = temperature_sensor_c
discovery.entity_area = lambda *_: spec.area_id
registry.async_get = lambda _: NS(async_get=lambda entity: NS(
    device_id=spec.source_device_id if entity in (OWN, cap.primary) else "independent-device",
    platform="zha",
))
runtime.hass.states.get = lambda entity: state if entity == cap.primary else sensors.get(entity)
runtime.hass.states.async_all = lambda _domain: []


def reset(*, pending=False):
    manager.settings.clear()
    manager.settings.update(
        room_sources={spec.area_id: {"temperature": [*FRESH, SLOW]}},
        weather_entities=["weather.home"],
    )
    cfg.clear()
    cfg.update(control_mode="pid", announce_device_errors=True)
    env.update(time=1900., permission=True, source_available=True,
               weather="clear-night", outdoor=2., peer=18., other_heater=False)
    state.state, state.attributes = "off", {}
    record.clear()
    record.update(area=spec.area_id, sources=list(spec.source_entities),
                  source_device_id=spec.source_device_id, baseline={}, power={}, off_at={},
                  thermal_off_watch={
                      "entity": cap.primary, "area": spec.area_id,
                      "source_device_id": spec.source_device_id, "off_since": 100.,
                      "attempts": 0, "last_attempt_at": None, "notified": False,
                  })
    if pending:
        record["thermal_off_watch"]["external_heat_pending"] = True
    runtime._thermal_off_sessions.clear()
    sensors.clear()
    sensors[SLOW] = sensor(50., 100.)
    readings.clear()
    commands.clear()
    messages.clear()
    saved.clear()


async def observe(at, value, *, slow=None):
    env["time"] = float(at)
    for entity in FRESH:
        sensors[entity] = sensor(value, at)
    if slow is not None:
        sensors[SLOW] = sensor(slow, at)
    return await production.watchdog_tick(runtime, spec, cap, state)


async def main():
    reset()
    await observe(1900, 21.)
    value, ids = production._independent_room_temperature(runtime, spec, cap.primary)
    assert value == 21. and ids == FRESH, (value, ids)
    assert sensors[SLOW].state == "50.0", "The stale source must not enter the mean"

    # Exclude both the appliance endpoint and another sensor on that physical
    # device before averaging; merely removing their IDs afterward is unsafe.
    manager.settings["room_sources"][spec.area_id]["temperature"] = [*FRESH, OWN, cap.primary]
    sensors[OWN] = sensor(80., 1900., device=spec.source_device_id)
    readings.clear()
    value, ids = production._independent_room_temperature(runtime, spec, cap.primary)
    assert value == 21. and ids == FRESH
    assert OWN not in readings and cap.primary not in readings

    # Reject inconsistent adapter metadata rather than claiming an arbitrary
    # subset corresponds to the supplied mean.
    real_adapter = production.room_temperature_evidence
    good = {"status": "ready", "partial": True, "entity_ids": [*FRESH, SLOW],
            "valid_count": 2, "ignored_count": 1,
            "invalid_sources": [{"entity_id": SLOW, "reason": "invalid_or_stale_temperature"}]}
    malformed = (
        {**good, "invalid_sources": []},
        {**good, "invalid_sources": [{"entity_id": "sensor.foreign", "reason": "stale"}]},
        {**good, "invalid_sources": [{"entity_id": SLOW}]},
        {**good, "invalid_sources": [None]},
        {**good, "invalid_sources": "not-a-list"},
        {**good, "invalid_sources": good["invalid_sources"] * 2},
        {**good, "partial": False},
        {**good, "partial": "true"},
        {**good, "valid_count": 3},
        {**good, "ignored_count": 0},
        {**good, "entity_ids": [*FRESH, SLOW, SLOW]},
        {**good, "entity_ids": "sensor.room_first"},
        {**good, "entity_ids": [*FRESH, None]},
        {**good, "status": "selected_temperature_invalid", "valid_count": 0},
    )
    try:
        for evidence in malformed:
            production.room_temperature_evidence = lambda *_a, **_k: (21., evidence)
            assert production._independent_room_temperature(runtime, spec, cap.primary) == (None, ()), evidence
    finally:
        production.room_temperature_evidence = real_adapter

    # A contributor returning with a different temperature must start a new
    # trend. Its later expiry also starts a new trend; neither jump is warming.
    reset()
    for at, value in ((1900, 21.), (2200, 21.1), (2500, 21.2)):
        assert not await observe(at, value)
    first = runtime._thermal_off_sessions[spec.identifier]
    assert first.source_ids == FRESH and len(first.samples) == 3
    assert not await observe(2800, 21.3, slow=35.)
    second = runtime._thermal_off_sessions[spec.identifier]
    assert second is not first and second.source_ids == (*FRESH, SLOW)
    assert len(second.samples) == 1 and second.samples[0][0] == 2800
    assert not await observe(3100, 21.4)
    assert not await observe(3401, 21.5)
    third = runtime._thermal_off_sessions[spec.identifier]
    assert third is not second and third.source_ids == FRESH
    assert len(third.samples) == 1 and third.samples[0] == (3401., 21.5)
    assert not commands and not messages
    for at, value in ((3701, 21.8), (4001, 22.1)):
        assert not await observe(at, value)
    assert await observe(4301, 22.4)
    assert len(commands) == 1 and len(messages) == 1
    assert record["thermal_off_watch"]["attempts"] == 1
    assert record["thermal_off_warning"]["source_ids"] == list(FRESH)
    assert not await observe(4601, 22.7)
    assert await observe(4901, 23.)
    assert not await observe(5501, 23.6)
    assert len(commands) == 2 and record["thermal_off_watch"]["attempts"] == 2
    assert [kind for _, kind, _ in messages] == ["suspected", "exhausted"]
    assert {row["attempts"] for row in saved} >= {1, 2}
    assert max(row["attempts"] for row in saved) == 2

    # No valid thermometer means no independent evidence and no retained trend.
    before = len(commands)
    env["time"] = 6102.
    assert production._independent_room_temperature(runtime, spec, cap.primary) == (None, ())
    assert not await production.watchdog_tick(runtime, spec, cap, state)
    assert spec.identifier not in runtime._thermal_off_sessions
    assert len(commands) == before

    # Recovering observation capability does not relax heat-source attribution.
    # An unresolved previous external gain can expose an unattributed rise,
    # but cannot gain OFF authority, send an alert, or spend either retry.
    reset(pending=True)
    for at, value in ((1900, 21.), (2200, 21.3), (2500, 21.8), (2800, 22.4)):
        assert not await observe(at, value)
    assert record["thermal_off_unattributed"]["heat_sources"]["reason"] == "residual_external_heat_possible"
    ledger = record["thermal_off_watch"]
    assert ledger["external_heat_pending"] is True
    assert ledger["attempts"] == 0 and ledger["last_attempt_at"] is None
    assert ledger["notified"] is False and not commands and not messages
    assert "thermal_off_warning" not in record
    assert saved and all(row["attempts"] == 0 for row in saved)
    print("B7_PARTIAL_FRESH_OFF_TREND_SOURCE_RESETS_AND_EXTERNAL_HEAT_GUARDS=PASS")


if __name__ == "__main__":
    asyncio.run(main())
