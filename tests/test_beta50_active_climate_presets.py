"""Beta50: real Away/Comfort/Sleep/Home preset on every managed climate class.

Regression contract: saved 'none' means automatic evidence-based profile, not
HA's currently active preset. Reading the facade must never actuate hardware,
override native HVAC modes, or forget the user's explicit preset selection.
"""
from __future__ import annotations

import asyncio
import pytest

from test_equipment_entities import platforms
from test_equipment_control import home
from custom_components.environment_manager import equipment_model as model


@pytest.mark.parametrize("domain", ["climate", "humidifier", "fan", "switch", "number"])
@pytest.mark.parametrize("method", ["automatic", "pid"])
def test_all_managed_climate_types_display_live_away_profile(
    platforms, domain, method,
):
    h = home(platforms.runtime, domain=domain, mode=method, state="off")
    if domain == "climate":
        h.state.attributes.update(hvac_modes=["off", "dry"], supported_features=0)
    h.plan.update(away="away", occupancy="unoccupied", sleeping=False)
    h.room["profiles"] = {
        "home": {"heat_c": 18, "cool_c": 28, "humidity": 55},
        "away": {"heat_c": 16, "cool_c": 30, "humidity": 43},
    }
    facade = platforms.climate.ManagedClimate(h.manager, h.spec)
    assert facade.preset_mode == "away"
    assert facade.preset_mode in facade.preset_modes
    assert facade.extra_state_attributes["active_profile"] == "away"
    assert facade.extra_state_attributes["preset_source"] == "automatic_presence"
    assert facade.extra_state_attributes["preset_override"] == "none"
    assert facade.extra_state_attributes["effective_preset"] == "away"
    assert facade.target_humidity == 43 if facade._caps.humidity else facade.target_humidity is None
    # A virtual climate's state is derived evidence, not a physical command.
    assert h.hass.services.calls == []


@pytest.mark.parametrize("mode", ["automatic", "pid"])
def test_dry_only_climate_pid_stays_dry_while_away_preset_and_physical_off(
    platforms, mode,
):
    h = home(platforms.runtime, domain="climate", mode=mode, state="off")
    h.state.attributes.update(hvac_modes=["off", "dry"], supported_features=0)
    h.room["profiles"] = {
        "away": {"heat_c": 16, "cool_c": 30, "humidity": 45},
        "sleep": {"heat_c": 18, "cool_c": 26, "humidity": 48},
    }
    h.plan.update(away="away", occupancy="unoccupied", sleeping=False,
                  away_evidence="verified_number_zero")
    # A real controller can legitimately hold the compressor on minimum OFF.
    h.runtime.statuses[h.spec.identifier] = {
        "status": "minimum_off_hold", "reason": "min_off"
    }
    facade = platforms.climate.ManagedClimate(h.manager, h.spec)
    assert facade.available
    assert facade.hvac_modes == ["off", "dry"]
    assert facade.hvac_mode == "dry"
    assert facade.hvac_action == "idle"
    assert facade.preset_mode == "away"
    assert facade.current_humidity == 70
    assert facade.target_humidity == 45
    attrs = facade.extra_state_attributes
    assert attrs["profile_home_status"] == "away"
    assert attrs["profile_home_evidence"] == "verified_number_zero"
    assert attrs["physical_source_state"] == "off"
    assert attrs["controller_status"]["status"] == "minimum_off_hold"
    assert h.hass.services.calls == []


def test_same_climate_switches_dynamic_preset_as_live_presence_changes(platforms):
    h = home(platforms.runtime, domain="climate", mode="pid", state="off")
    h.state.attributes.update(hvac_modes=["off", "dry"], supported_features=0)
    h.room["profiles"] = {
        "home": {"heat_c": 18, "cool_c": 28, "humidity": 52},
        "comfort": {"heat_c": 20, "cool_c": 26, "humidity": 54},
        "sleep": {"heat_c": 18, "cool_c": 25, "humidity": 49},
        "away": {"heat_c": 16, "cool_c": 30, "humidity": 40},
    }
    facade = platforms.climate.ManagedClimate(h.manager, h.spec)
    cases = (
        ("home", "unoccupied", False, "home", 52),
        ("home", "occupied", False, "comfort", 54),
        ("home", "occupied", True, "sleep", 49),
        ("away", "unoccupied", True, "away", 40),
        ("unknown", "unoccupied", False, "home", 52),
    )
    for home_state, occupancy, sleeping, expected, rh in cases:
        h.plan.update(away=home_state, occupancy=occupancy, sleeping=sleeping)
        assert facade.preset_mode == expected
        assert facade.target_humidity == rh
        assert facade.extra_state_attributes["active_profile"] == expected
        assert facade.hvac_mode == "dry"
    assert h.hass.services.calls == []


@pytest.mark.parametrize("domain", ["climate", "humidifier", "fan", "number"])
def test_explicit_preset_override_does_not_silently_turn_into_away(
    platforms, domain,
):
    h = home(platforms.runtime, domain=domain, mode="pid", state="off",
             controls={"preset": "comfort"})
    h.plan.update(away="away", occupancy="unoccupied", sleeping=False)
    facade = platforms.climate.ManagedClimate(h.manager, h.spec)
    assert facade.preset_mode == "comfort"
    assert facade.extra_state_attributes["preset_override"] == "comfort"
    assert facade.extra_state_attributes["preset_source"] == "explicit_override"
    assert model.profile_name(facade.controller_settings, h.plan) == "comfort"
    assert h.hass.services.calls == []


@pytest.mark.parametrize("mode", ["existing", "manual", "off"])
def test_not_automatic_modes_do_not_claim_away_without_an_override(platforms, mode):
    h = home(platforms.runtime, domain="climate", mode=mode, state="off")
    h.plan.update(away="away", occupancy="unoccupied", sleeping=False)
    facade = platforms.climate.ManagedClimate(h.manager, h.spec)
    assert facade.preset_mode == "none"
    assert facade.extra_state_attributes["preset_source"] == "not_automatically_managed"
    assert h.hass.services.calls == []


def test_explicit_preset_cleared_returns_to_dynamic_away_without_actuation(platforms):
    async def run():
        h = home(platforms.runtime, domain="climate", mode="pid", state="off",
                 controls={"preset": "comfort"})
        h.plan.update(away="away", occupancy="unoccupied", sleeping=False)
        facade = platforms.climate.ManagedClimate(h.manager, h.spec)
        assert facade.preset_mode == "comfort"
        await facade.async_set_preset_mode("none")
        assert h.manager.settings[model.SETTINGS][h.spec.identifier]["preset"] == "none"
        assert h.manager.settings[model.SETTINGS][h.spec.identifier]["control_mode"] == "pid"
        assert facade.preset_mode == "away"
        assert facade.extra_state_attributes["preset_source"] == "automatic_presence"
        assert h.hass.services.calls == []
    asyncio.run(run())


def test_same_effective_profile_reported_for_dry_held_manual_and_native_capabilities(platforms):
    for domain in ("climate", "humidifier", "fan", "switch"):
        h = home(platforms.runtime, domain=domain, mode="automatic", state="off")
        h.plan.update(away="away", occupancy="unknown", sleeping=None)
        facade = platforms.climate.ManagedClimate(h.manager, h.spec)
        h.runtime.statuses[h.spec.identifier] = {"status": "startup_warmup"}
        assert facade.preset_mode == facade.extra_state_attributes["active_profile"] == "away"
        assert facade.hvac_mode in facade.hvac_modes
        assert h.hass.services.calls == []
