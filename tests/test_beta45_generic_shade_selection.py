"""Native classless roller shutters must appear without granting motor movement."""
from __future__ import annotations

import asyncio
import pytest

from test_discovery import FakeHass, MockState, adapter
from custom_components.environment_manager import room_sources
from custom_components.environment_manager.shade_cooling import eligible_shade


# These mirror reported HA TemplateStates: no device_class, but native CLOSE.
USER_COVERS = {
    "cover.ksenonas_rolo_aristera": ("gastezimmer", "Ξενώνας Ρολό Δεξιά", "open"),
    "cover.wohnzimmer_rollo_links_rolo_3": ("wohnzimmer", "Καθιστικό Ρολό Αριστερά", "open"),
    "cover.wohnzimmer_rollo_rechts": ("wohnzimmer", "Καθιστικό Ρολό Δεξιά", "open"),
    "cover.gastezimmer_rollo_rechts_rolo_5": ("gastezimmer", "Ξενώνας Ρολό Αριστερά", "open"),
    "cover.schlafzimmer_rollo_rolo": ("schlafzimmer", "Υπνοδωμάτιο Ρολό", "open"),
    "cover.kuche_rollo": ("kuche", "Κουζίνα Ρολό", "unknown"),
}


def _setup_user_covers():
    states=[]
    for entity,(room,name,value) in USER_COVERS.items():
        state=MockState(entity,value,name=name)
        state.attributes.update(supported_features=15)
        if value == "open":
            state.attributes.update(is_closed=False,current_position=100)
        else:
            state.attributes.update(is_closed=None)
        states.append(state)
    hass=FakeHass(states)
    for i, (entity,(room,_,_)) in enumerate(USER_COVERS.items()):
        physical=f"physical-{i}"
        hass._entity_devices[entity]=physical
        hass._device_areas[physical]=room
    return hass


def test_all_six_real_classless_rollers_are_selectable_in_their_rooms(adapter):
    hass=_setup_user_covers()
    expected={}
    for entity,(area,_,_) in USER_COVERS.items():
        expected.setdefault(area,set()).add(entity)
    for area,entities in expected.items():
        available={item["value"]:item["label"] for item in room_sources.choices(hass,area)["shades"]}
        assert set(available)==entities
        assert all("Ρολό" in label for label in available.values())
        assert all(room_sources.category(hass,hass.states.get(e))=="shades" for e in entities)

    # The unavailable / unknown kitchen shutter remains selectable but cannot
    # be operated until its live state becomes known and passes later checks.
    kitchen="cover.kuche_rollo"
    assert kitchen in {v["value"] for v in room_sources.choices(hass,"kuche")["shades"]}
    assert eligible_shade(hass,"kuche",kitchen,(kitchen,))==(False,"cover_unavailable")


def test_entity_area_override_precedes_device_area_and_other_rooms_excluded(adapter):
    hass=_setup_user_covers()
    entity="cover.ksenonas_rolo_aristera"
    hass._device_areas[hass._entity_devices[entity]]="wohnzimmer"
    hass._entity_areas[entity]="gastezimmer"
    assert {o["value"] for o in room_sources.choices(hass,"gastezimmer")["shades"]}=={
        entity,"cover.gastezimmer_rollo_rechts_rolo_5",
    }
    assert entity not in {o["value"] for o in room_sources.choices(hass,"wohnzimmer")["shades"]}
    assert eligible_shade(hass,"gastezimmer",entity,(entity,))==(True,"verified_shade")
    assert eligible_shade(hass,"wohnzimmer",entity,(entity,))==(False,"cover_wrong_room")


@pytest.mark.parametrize("klass",[
    "garage","gate","door","window","awning","damper","valve","unknown-specialized"
])
def test_explicit_non_shading_classes_still_rejected(adapter, klass):
    entity="cover.not_a_shade"
    state=MockState(entity,"open",device_class=klass)
    state.attributes["supported_features"]=15
    hass=FakeHass([state],{entity:"room"})
    assert room_sources.category(hass,state) is None
    assert room_sources.choices(hass,"room")["shades"]==[]
    assert not eligible_shade(hass,"room",entity,(entity,))[0]


@pytest.mark.parametrize("klass",["blind","shade","shutter","curtain",None])
def test_native_shade_classes_and_unclassified_close_capability(adapter,klass):
    state=MockState("cover.blind","open",device_class=klass)
    state.attributes["supported_features"]=2
    hass=FakeHass([state],{state.entity_id:"room"})
    assert room_sources.category(hass,state)=="shades"
    assert eligible_shade(hass,"room",state.entity_id,(state.entity_id,))[0]


@pytest.mark.parametrize("features",[0,1,4,8,"not_a_bitmask",-1,None])
def test_no_close_feature_never_listed(adapter,features):
    state=MockState("cover.missing_close","open")
    state.attributes["supported_features"]=features
    hass=FakeHass([state],{state.entity_id:"room"})
    assert room_sources.category(hass,state) is None


def test_manager_generated_and_hidden_covers_are_not_listed(adapter):
    states=[MockState("cover.native_hidden","open"),MockState("cover.native_disabled","open"),
            MockState("cover.manager_created","open")]
    for state in states:
        state.attributes["supported_features"]=15
    hass=FakeHass(states,{s.entity_id:"room" for s in states})
    hass._entity_details["cover.native_hidden"]={"hidden_by":"user"}
    hass._entity_details["cover.native_disabled"]={"disabled_by":"user"}
    hass._entity_details["cover.manager_created"]={"platform":"environment_manager"}
    assert room_sources.choices(hass,"room")["shades"]==[]


def test_classless_cover_is_inventory_only_and_cannot_auto_close_from_selection(adapter):
    from test_beta43_shade_cooling import make_room
    h=make_room(enabled=False,cover_class=None,supported_features=15)
    available={v["value"] for v in room_sources.choices(h.hass,"room")["shades"]}
    assert h.cover.entity_id in available
    asyncio.run(h.control._tick("room"))
    assert not h.hass.services.calls
    assert h.control.statuses["room"]["status"]=="disabled"
