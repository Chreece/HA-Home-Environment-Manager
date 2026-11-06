"""Room list, sensor vacancy and household Sleep against production code."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib
from pathlib import Path
import runpy
import unittest

fixture = runpy.run_path(str(Path(__file__).with_name("test_home_presence_authority.py")))
Hass, policy = fixture["Hass"], fixture["occupancy"]
AREA, OTHER = fixture["AREA"], "bath"
ROOMS, SENSOR, HOME = fixture["ROOMS"], fixture["MOTION"], fixture["PERSON"]
SLEEP = "sensor.sleep_rooms"
EXTRA = "binary_sensor.bath_presence"
alarm = importlib.import_module(policy.__package__ + ".wake_alarm")


class OvernightPresenceTests(unittest.TestCase):
    def setUp(self):
        self.hass = Hass()
        self.conf = {"occupied_rooms_entity": ROOMS, "sleep_rooms_entity": SLEEP}
        self.hass.put(ROOMS, "Wohnzimmer", age=550)
        self.hass.put(SLEEP, "Living room", age=550)

    def room(self, area=AREA, settings=None):
        return policy.room_presence(self.hass, area, settings or {}, self.conf,
                                    known_areas={AREA}, home_status="home")[0]

    def household(self, home="home"):
        return policy.household_sleep_presence(self.hass, self.conf, {AREA}, home_status=home)[0]

    def own(self, area=AREA, inherit=False, local=False, home="home"):
        return policy.controlled_sleep_presence(
            self.hass, area, self.conf, {AREA}, home_status=home,
            room_status=self.room(area), local_sleeping=local, inherit_household=inherit,
        )[0]

    def test_unchanged_state_and_attribute_lists_remain_authoritative_overnight(self):
        self.hass.put(SENSOR, "off", age=600)
        self.hass.put(EXTRA, "on", area=OTHER, attributes={"device_class":"presence"})
        for src, attribute, value, attrs in (
            (ROOMS, "__state__", "Wohnzimmer", {}),
            ("sensor.multiple_presence", "used_rooms", "1", {"used_rooms":[AREA]}),
        ):
            with self.subTest(src=src, attribute=attribute):
                self.conf.update(occupied_rooms_entity=src, occupied_rooms_attribute=attribute)
                self.hass.put(src, value, attributes=attrs, age=550)
                self.assertEqual((self.room(), self.room(OTHER)), ("occupied", "unoccupied"))
                self.assertIs(self.own(), True)
                self.assertIs(self.own(OTHER), False)
                self.assertIs(self.household(), True)

    def test_sleep_list_membership_alone_does_not_mean_occupied(self):
        self.hass.put(SLEEP, '["living", "bath"]', age=525)
        self.assertFalse(self.own(OTHER))
        self.assertTrue(self.own(OTHER, inherit=True))
        self.hass.put(ROOMS, "", age=525)
        self.assertFalse(self.household())
        self.assertFalse(self.own(inherit=True))
        # Deliberately selecting Sleeping now/schedule remains a local control.
        self.assertTrue(self.own(local=True))
        self.assertFalse(self.own(local=True, home="away"))

    def test_household_checks_unmonitored_list_members(self):
        self.hass.put(ROOMS, '["Wohnzimmer","Bathroom"]')
        self.assertFalse(self.household())
        self.hass.put(SLEEP, "2", attributes={"sleeping":["living","bath"]}, age=600)
        self.conf["sleep_rooms_attribute"] = "sleeping"
        self.assertTrue(self.household())
        self.hass.put(SLEEP, "2", attributes={"sleeping":["not_a_registered_room"]})
        self.assertIsNone(self.household())

    def test_change_only_binary_sensors_and_no_configured_room_sensor(self):
        self.conf.pop("occupied_rooms_entity")
        self.assertEqual(self.room(), "unoccupied")
        self.assertFalse(self.household())
        self.hass.put(SENSOR, "on", age=500)
        self.assertEqual(self.room(), "occupied")
        self.assertTrue(self.household())
        self.hass.put(SENSOR, "off", age=500)
        self.assertEqual(self.room(), "unoccupied")
        self.assertFalse(self.household())
        # A room without any configured inputs cannot establish an empty house.
        self.assertEqual(policy.home_presence(self.hass, {})[0], "home")

    def test_sensor_fallback_respects_other_ha_areas_and_saved_empty_selections(self):
        self.conf.pop("occupied_rooms_entity")
        self.hass.put(SENSOR, "on", age=500)
        self.hass.put(EXTRA, "on", area=OTHER, attributes={"device_class":"occupancy"}, age=600)
        self.assertFalse(self.household())
        self.conf["_room_occupancy_selections"] = {OTHER: []}
        self.assertTrue(self.household())
        self.conf["_room_occupancy_selections"] = {OTHER: [EXTRA]}
        self.hass.put(EXTRA, "unavailable", area=OTHER)
        self.assertIsNone(self.household())
        self.hass.put(EXTRA, "off", area=OTHER, attributes={"device_class":"occupancy"})
        self.assertTrue(self.household())

    def test_missing_invalid_and_restored_inputs_remain_unverified(self):
        for state, attrs in (("unavailable", {}), ("unknown", {}), ("[broken", {}),
                             ("not_a_registered_room", {}), ("Wohnzimmer", {"restored":True})):
            with self.subTest(state=state, attrs=attrs):
                self.hass.put(ROOMS, state, attributes=attrs)
                self.assertEqual(self.room(), "unknown")
                self.assertIsNone(self.household())
        self.conf.pop("occupied_rooms_entity")
        for value in ("unavailable","unknown"):
            self.hass.put(EXTRA, value, area=OTHER)
            self.assertEqual(self.room(OTHER, {"occupancy_sensors":[EXTRA]}), "unknown")

    def test_no_room_or_sleep_source_reads_after_whole_home_away(self):
        self.hass.states.blocked.update({ROOMS,SENSOR,EXTRA,SLEEP})
        self.hass.states.forbid_discovery = True
        self.assertIs(self.household("away"),False)
        self.assertFalse(policy.controlled_sleep_presence(
            self.hass, AREA, self.conf, {AREA}, home_status="away",
            room_status="unoccupied", local_sleeping=True, inherit_household=True)[0])

    def test_sampled_counts_and_direct_home_trackers_keep_age_limits(self):
        num = "sensor.people_in_bathroom"
        self.conf.pop("occupied_rooms_entity")
        self.conf["room_occupancy_sensors"] = [num]
        self.hass.put(num, "1", age=15, area=OTHER)
        self.assertEqual(self.room(OTHER, {"occupancy_stale_minutes":10}), "unknown")
        self.assertEqual(self.room(OTHER, {"occupancy_stale_minutes":20}), "occupied")
        self.hass.put(HOME, "not_home", age=400)
        self.assertEqual(policy.home_presence(self.hass, {"home_trackers":[HOME]})[0], "unknown")

    def test_household_and_inferred_room_sleep_keep_per_room_count_age_limit(self):
        num = "sensor.people_in_bathroom"
        self.conf.pop("occupied_rooms_entity")
        self.hass.put(SLEEP, '["living", "bath"]', age=550)
        self.hass.put(SENSOR, "on", age=550)
        self.hass.put(num, "1", age=15, area=OTHER)
        self.conf["_room_occupancy_selections"] = {OTHER: [num]}
        self.conf["_room_occupancy_stale_minutes"] = {AREA: 10, OTHER: 10}
        self.assertIsNone(self.household())
        self.assertIsNone(policy.controlled_sleep_presence(
            self.hass, OTHER, self.conf, {AREA}, home_status="home")[0])
        self.conf["_room_occupancy_stale_minutes"][OTHER] = 20
        self.assertTrue(self.household())
        self.assertTrue(policy.controlled_sleep_presence(
            self.hass, OTHER, self.conf, {AREA}, home_status="home")[0])


class WakeObservationTests(unittest.TestCase):
    """Production capture observer, with no device consumer or HA Store."""
    def setUp(self):
        self.hass = Hass()
        self.tracker = alarm.WakeAlarm()
        self.hass.data = {alarm._TRACKERS: {"entry": self.tracker}}
        self.conf = {"occupied_rooms_entity": ROOMS, "sleep_rooms_entity": SLEEP,
                     "wake_alarm_entity": "sensor.next_alarm",
                     "wake_lead_minutes_entity": "input_number.wake_lead",
                     "_wake_entry_id": "entry"}
        self.ring = fixture["NOW"].timestamp() + 3600
        self.set_alarm(self.ring)
        self.hass.put("input_number.wake_lead", "30")
        self.hass.put(ROOMS, AREA)
        self.hass.put(SLEEP, AREA)

    def set_alarm(self, ring):
        self.hass.put("sensor.next_alarm", datetime.fromtimestamp(ring, timezone.utc).isoformat())

    def observe(self, when, *, known=None, rooms=None, settings=None):
        alarm.observe_wake_episodes(
            self.hass, "entry", self.conf if settings is None else settings,
            {AREA} if known is None else known, home_status="home",
            room_settings=rooms or {}, now=when,
        )

    def test_daytime_clear_without_opt_in_consumers_allows_next_sleep_episode(self):
        self.observe(self.ring-20)
        self.assertEqual(set(self.tracker.active), {"household", "room:"+AREA})
        self.set_alarm(self.ring+86400)
        self.observe(self.ring+60)
        self.assertEqual(self.tracker.active["household"], self.ring)
        # No per-device sleep call is made during the day. Capture alone
        # sees the list clear while every device may be Manual or opted out.
        self.hass.put(SLEEP, "")
        self.observe(self.ring+3600)
        self.assertFalse(self.tracker.active)
        self.hass.put(SLEEP, AREA)
        self.observe(self.ring+20*3600)
        sleeping, _ = policy.controlled_sleep_presence(
            self.hass, OTHER, self.conf, {AREA, OTHER}, home_status="home",
            room_status="unoccupied", inherit_household=True, now=self.ring+20*3600)
        self.assertTrue(sleeping)
        self.assertFalse(self.tracker.active)
        self.observe(self.ring+86400-1800)
        self.assertEqual(self.tracker.active["household"], self.ring+86400)

    def test_room_wake_survives_household_sleep_start_after_alarm(self):
        # One room is asleep while another occupied room is still awake.
        # Only the first room has a wake episode when the alarm rings.
        self.hass.put(ROOMS, '["living", "bath"]')
        self.observe(self.ring-10, known={AREA, OTHER})
        self.assertEqual(self.tracker.active, {"room:"+AREA: self.ring})
        self.set_alarm(self.ring+86400)
        self.observe(self.ring+1, known={AREA, OTHER})
        self.hass.put(ROOMS, AREA)
        self.observe(self.ring+60, known={AREA, OTHER})
        self.assertTrue(policy.household_sleep_presence(
            self.hass, self.conf, {AREA, OTHER}, home_status="home")[0])
        self.assertEqual(policy.controlled_sleep_presence(
            self.hass, AREA, self.conf, {AREA, OTHER}, home_status="home",
            room_status="occupied", inherit_household=True, now=self.ring+60),
            (False, "wake_before_alarm"))
        self.assertEqual(self.tracker.active, {"room:"+AREA: self.ring})

        # Once the real sleeping condition clears, next night's new episode
        # must still sleep normally and then wake at its own deadline.
        self.hass.put(SLEEP, "")
        self.observe(self.ring+3600, known={AREA, OTHER})
        self.assertFalse(self.tracker.active)
        self.hass.put(SLEEP, AREA)
        self.observe(self.ring+20*3600, known={AREA, OTHER})
        self.assertTrue(policy.controlled_sleep_presence(
            self.hass, AREA, self.conf, {AREA, OTHER}, home_status="home",
            room_status="occupied", inherit_household=True, now=self.ring+20*3600)[0])
        self.observe(self.ring+86400-1800, known={AREA, OTHER})
        self.assertEqual(policy.controlled_sleep_presence(
            self.hass, AREA, self.conf, {AREA, OTHER}, home_status="home",
            room_status="occupied", inherit_household=True, now=self.ring+86400-1800),
            (False, "wake_before_alarm"))

    def test_household_wake_survives_room_sleep_start_after_alarm(self):
        # An empty room's opted-in device already woke with the household.
        # Entering that sleeping room after the alarm must not undo its wake.
        self.hass.put(SLEEP, '["living", "bath"]')
        self.observe(self.ring-10, known={AREA, OTHER})
        self.assertEqual(self.tracker.active["household"], self.ring)
        self.assertNotIn("room:"+OTHER, self.tracker.active)
        self.set_alarm(self.ring+86400)
        self.observe(self.ring+1, known={AREA, OTHER})
        self.hass.put(ROOMS, '["living", "bath"]')
        self.observe(self.ring+60, known={AREA, OTHER})
        self.assertEqual(policy.controlled_sleep_presence(
            self.hass, OTHER, self.conf, {AREA, OTHER}, home_status="home",
            room_status="occupied", inherit_household=True, now=self.ring+60),
            (False, "wake_before_alarm"))
        # A peer that did not opt into household Sleep has no earlier wake
        # episode; its newly occupied sleeping room still uses normal Sleep.
        self.assertTrue(policy.controlled_sleep_presence(
            self.hass, OTHER, self.conf, {AREA, OTHER}, home_status="home",
            room_status="occupied", inherit_household=False, now=self.ring+60)[0])
        self.assertNotIn("room:"+OTHER, self.tracker.active)

    def test_removing_and_reselecting_same_alarm_pair_cannot_reuse_old_wake(self):
        self.observe(self.ring-20)
        disabled = {key: value for key, value in self.conf.items()
                    if key not in ("wake_alarm_entity", "wake_lead_minutes_entity", "_wake_entry_id")}
        self.observe(self.ring+60, settings=disabled)
        self.assertIsNone(self.tracker.pair)
        self.assertFalse(self.tracker.active)
        self.assertFalse(self.tracker.armed)
        self.set_alarm(self.ring+86400)
        self.observe(self.ring+120)
        self.assertFalse(self.tracker.active)
        self.assertTrue(policy.controlled_sleep_presence(
            self.hass, AREA, self.conf, {AREA}, home_status="home",
            room_status="occupied", now=self.ring+120)[0])

    def test_removed_room_is_observed_without_expiring_continuous_household_sleep(self):
        self.observe(self.ring-20, known={AREA, OTHER}, rooms={OTHER:{"sleep_active":True}})
        self.assertEqual(self.tracker.active["room:"+OTHER], self.ring)
        self.set_alarm(self.ring+86400)
        # The remembered bathroom scope is no longer among current consumers.
        # Its local Sleeping now control was removed and it is not on the list.
        self.observe(self.ring+120, known={AREA})
        self.assertNotIn("room:"+OTHER, self.tracker.active)
        self.assertEqual(self.tracker.active["household"], self.ring)
        self.observe(self.ring+20*3600, known={AREA, OTHER}, rooms={OTHER:{"sleep_active":True}})
        self.assertNotIn("room:"+OTHER, self.tracker.active)
        self.assertTrue(policy.controlled_sleep_presence(
            self.hass, OTHER, self.conf, {AREA, OTHER}, home_status="home",
            room_status="unoccupied", local_sleeping=True, now=self.ring+20*3600)[0])
        # Continuous live sleep, even a long episode, does not end by age alone.
        self.set_alarm(self.ring+4*86400)
        self.observe(self.ring+3*86400)
        self.assertEqual(self.tracker.active["household"], self.ring)
        self.assertEqual(self.tracker.active["room:"+AREA], self.ring)


if __name__ == "__main__":
    unittest.main(verbosity=2)
