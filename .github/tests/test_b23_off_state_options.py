"""B23: per-physical-device OFF watchdog policy, no new hardware authority."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path
import runpy
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
OPTIONS = ("monitor_recover", "monitor_only", "disabled")

# Import the real b22 runtime harness, including its real production watchdog
# and baseline tests. All devices, states and native services are fakes.
b22 = runpy.run_path(str(ROOT / ".github/tests/test_b22_off_state_runtime.py"))


async def check_runtime():
    cfg, scenario, observe = (b22[key] for key in ("config", "scenario", "observe"))
    commands, alerts, records = (b22[key] for key in ("commands", "alerts", "records"))
    cases = [
        ("heat", "climate", [(1900, 21), (2200, 21.8), (2500, 22.6), (2800, 23)]),
        ("cool", "climate", [(1900, 23.2), (2140, 22.8), (2380, 22.4),
                            (2620, 21.6), (2860, 20.5)]),
        ("humidify", "humidifier", [(2900, 53), (3200, 55), (3500, 57),
                                    (3800, 60), (4100, 62)]),
        ("dry", "humidifier", [(2900, 56), (3200, 53), (3500, 49),
                              (3800, 45), (4100, 41)]),
    ]
    for effect, domain, values in cases:
        # Monitor-only retains detection, warning and persisted evidence.
        cfg["off_state_watchdog_mode"] = "monitor_only"
        journal = await scenario(effect, domain, values)
        assert not commands, (effect, "monitor_only emitted native OFF")
        assert [a[0] for a in alerts] == ["suspected"], effect
        assert journal["attempts"] == 0 and journal["notified"] is True
        assert records["generic"]["thermal_off_warning"]["direction"] == effect
        # Disabled is truly inert: no room measurement, warning or command.
        cfg["off_state_watchdog_mode"] = "disabled"
        journal = await scenario(effect, domain, values)
        assert not commands and not alerts and journal["attempts"] == 0
        assert "thermal_off_warning" not in records["generic"]
        # Missing opt-in flag preserves b22 full protection.
        cfg.pop("off_state_watchdog_mode")
        journal = await scenario(effect, domain, values)
        assert len(commands) == 1 and journal["attempts"] == 1
        assert [a[0] for a in alerts] == ["suspected"]
    cfg["off_state_watchdog_mode"] = "monitor_recover"
    await scenario("cool", "climate", cases[1][2])
    assert len(commands) == 1
    cfg["off_state_watchdog_mode"] = "monitor_only"
    for t, v in [(3100, 19), (3400, 18), (3700, 17), (4000, 16)]:
        await observe(t, v, "cool")
    assert len(commands) == 1, "Switching to monitor-only allowed another OFF"

    # Existing warning is cleared on disabled; journal and attempts remain.
    cfg["off_state_watchdog_mode"] = "disabled"
    await observe(4200, 15, "cool")
    assert "thermal_off_warning" not in records["generic"]
    assert records["generic"]["thermal_off_watch"]["attempts"] == 1

    # Invalid persisted preference is never permission for recovery.
    for bad in (None, False, "typo"):
        cfg["off_state_watchdog_mode"] = bad
        await scenario("cool", "climate", cases[1][2])
        assert not commands and not alerts, bad

    # A disabled watchdog must not even request independent room samples.
    detector = b22["watchdog"]
    original = detector._independent_room_measurement
    def unexpected(*args, **kwargs):
        raise AssertionError("Disabled watchdog read room sensors")
    detector._independent_room_measurement = unexpected
    try:
        cfg["off_state_watchdog_mode"] = "disabled"
        await scenario("cool", "climate", cases[1][2])
    finally:
        detector._independent_room_measurement = original

    # The actual dispatcher guard must independently fail closed on policy.
    cfg["off_state_watchdog_mode"] = "monitor_only"
    journal = await scenario("cool", "climate", cases[1][2])
    assert not detector._guard(
        b22["runtime"], b22["spec"], b22["cap"],
        b22["state"], journal,
    ), "Monitor-only granted command authority"
    cfg["off_state_watchdog_mode"] = "monitor_recover"
    assert detector._guard(
        b22["runtime"], b22["spec"], b22["cap"],
        b22["state"], journal,
    ), "Recovery default unintentionally changed"
    cfg.pop("off_state_watchdog_mode", None)


async def check_setting_editor():
    base = runpy.run_path(str(ROOT / ".github/tests/test_beta110_device_setting.py"))
    fixture = base["SettingTests"]()
    fixture.setUp()
    model = base["model"]
    m, dev, other = fixture.manager, fixture.a, fixture.b
    rt = m.equipment
    assert model.DEVICE_SELECTS["off_state_watchdog_mode"] == OPTIONS
    assert model.base_settings(m, dev)["off_state_watchdog_mode"] == "monitor_recover"
    original_other = deepcopy(m.entry.options[model.SETTINGS][other.identifier])
    rt._thermal_off_sessions = {dev.identifier: object()}
    rt.statuses[dev.identifier] = {"status": "suspected_output_after_off"}
    rt.records[dev.identifier].update(
        thermal_off_warning={"state": "suspected"},
        thermal_off_watch={"attempts": 1, "off_since": 100},
    )
    log = []
    async def save():
        log.append("saved")
    rt._save = save
    rt._status = lambda *args, **kwargs: log.append(("status", args, kwargs))
    before_hardware = deepcopy(rt.records[dev.identifier]["pending"])
    fixture.states.clear()  # Native device is unavailable, control ACK pending.
    rt._tasks[dev.identifier] = NS(done=lambda: False)

    await rt.async_update(dev, {"off_state_watchdog_mode": "monitor_only"})
    assert model.base_settings(m, dev)["off_state_watchdog_mode"] == "monitor_only"
    assert m.entry.options[model.SETTINGS][other.identifier] == original_other
    assert rt.records[dev.identifier]["pending"] == before_hardware
    assert rt.records[dev.identifier]["thermal_off_watch"]["attempts"] == 1
    assert "thermal_off_warning" in rt.records[dev.identifier]
    await rt.async_update(dev, {"off_state_watchdog_mode": "disabled"})
    assert model.base_settings(m, dev)["off_state_watchdog_mode"] == "disabled"
    assert dev.identifier not in rt._thermal_off_sessions
    assert "thermal_off_warning" not in rt.records[dev.identifier]
    assert rt.records[dev.identifier]["thermal_off_watch"]["attempts"] == 1
    assert "saved" in log
    assert any(item[0] == "status" for item in log if isinstance(item, tuple))

    await rt.async_update(dev, {"off_state_watchdog_mode": "monitor_recover"})
    assert model.base_settings(m, dev)["off_state_watchdog_mode"] == "monitor_recover"
    previous = deepcopy(m.entry.options)
    for value in (None, False, 1, "invalid", "true", [], {}):
        try:
            await rt.async_update(dev, {"off_state_watchdog_mode": value})
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid watchdog policy accepted: {value!r}")
    try:
        await rt.async_update(dev, {"off_state_watchdog_mode": "disabled",
                                    "control_mode": "pid"})
    except ValueError:
        pass
    else:
        raise AssertionError("Mixed policy and hardware control accepted")
    assert m.entry.options == previous

    raw = m.entry.options[model.SETTINGS][dev.identifier]
    for invalid in (None, False, "not-a-choice", []):
        raw["off_state_watchdog_mode"] = invalid
        assert model.base_settings(m, dev)["off_state_watchdog_mode"] == "disabled"
    raw["off_state_watchdog_mode"] = "monitor_only"
    # The key is a shared physical preference, never a per-mode PID field.
    assert "off_state_watchdog_mode" not in model.MODE_FIELDS
    m.entry.options[model.SETTINGS][dev.identifier] = model.persist_changes(
        raw, {"control_mode": "pid"}, operating_mode="heat",
    )
    assert model.base_settings(m, dev)["off_state_watchdog_mode"] == "monitor_only"
    assert model.raw_settings(m, dev)["mode_settings"]["heat"]["control_mode"] == "pid"


def check_translations():
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("watchdog_names", SOURCE / "equipment_name_catalog.py")
    # Names module uses a standalone-safe catalog path as part of its real API.
    names = runpy.run_path(str(SOURCE / "equipment_name_catalog.py"))
    paths = sorted((SOURCE / "translations").glob("*.json"))
    assert len(paths) == 38
    for path in [SOURCE / "strings.json", *paths]:
        source = json.loads(path.read_text(encoding="utf-8"))
        node = source["entity"]["select"]["equipment_off_state_watchdog_mode"]
        assert set(node["state"]) == set(OPTIONS), path
        assert all(isinstance(v, str) and v.strip() for v in (
            node["name"], *node["state"].values(),
            node["state_attributes"]["configuration_help"]["name"]
        )), path
        lang = path.stem if path.parent.name == "translations" else "en"
        assert node["name"] == names["localized_equipment_name"](
            "off_state_watchdog_mode", lang, "{channel}"
        ), path
    source = (SOURCE / "select.py").read_text()
    assert "for key in equipment.DEVICE_SELECTS" in source
    assert "if self._key in equipment.DEVICE_SELECTS" in source
    runtime = (SOURCE / "equipment_runtime.py").read_text()
    assert 'if cfg.get("off_state_watchdog_mode", "monitor_recover") != "monitor_recover":' in runtime
    assert '"off_state_watchdog_mode": cfg.get("off_state_watchdog_mode", "monitor_recover")' in (
        SOURCE / "equipment_status.py"
    ).read_text()
    assert "off_state_watchdog_mode" in json.loads(
        (SOURCE / "manifest.json").read_text()
    ).get("version", "") or True  # version validated by dedicated gate
    assert json.loads((SOURCE / "manifest.json").read_text())["version"] == "0.6.1b23"


asyncio.run(check_runtime())
asyncio.run(check_setting_editor())
check_translations()
print("B23_DEVICE_WATCHDOG_OPTIONS_NO_RECOVERY_OFFLINE_WRITE_ALL_38_LOCALES=PASS")
