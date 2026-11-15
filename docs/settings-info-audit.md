# HEM — Setting information and explanation audit (v0.6.2b22)

## Goal and source of truth

People should be able to open **Info** next to an actual Home, Room, Door, Device or Floor setting and answer:

1. **What does it do?** What physical or logical result should I expect?
2. **When does it matter?** Which room/device, preconditions and limits apply?
3. **What does each option mean?** What changes if I choose it?
4. **What does it *not* do?** Important exclusions and safety priorities.

The behavioral source of truth is the existing HEM implementation (including
`door_coordination.py`, `equipment_door_policy.py`, `equipment_model.py`,
`occupancy_policy.py` and the actual native fields). Help must describe those
rules, **not add permissions or claim physical behavior that has not been verified**.

## Inventory audit

At this revision the English native `strings.json` entity catalog defines
**183 entity keys**, of which **178** are configuration/action platforms:
118 Number, 24 Switch, 26 Select, 2 Time and 8 Button. Four Sensor keys and
one Climate key are not editable setting controls. Some catalog entries are
legacy or conditional and are *not* necessarily instantiated for every home.

- **18 currently exposed fixed-choice native Select types, 57 distinct
  option entries:** all have specific EN/EL/DE option-by-option explanations.
  `area_climate_policy_away_policy` intentionally shares the current
  `home_global_policy_home_policy` semantics; these are not two independently
  implemented home policies.
- **Additional dynamic door selectors:** the device-wide coordination
  `inherit/observe/conflicts/shared` values, room door classification
  `interior/fire/exterior`, and legacy per-door coordination have dedicated
  explanations. Existing saved IDs and service values are unchanged.
- **Seven source/provider-dependent Select types:** their choices represent
  real sensor IDs, device speed modes, source assignments or similar native
  values. HEM describes **why to select a source or mode** but does not invent
  the consequences of an arbitrary vendor-provided option.
- The old `equipment_pid_adaptation_mode` appears in historical translations
  but is intentionally retired from the current UI; the unified PID method
  selector is authoritative. Do not reintroduce it merely to count a catalog key.
- The Options wizard contains **361 field entries** in the English catalog.
  All now have descriptions in the EN/EL/DE canonical catalogs, including the
  two historical room-navigation fields (`room_occupancy_area` and
  `edit_room_area`), which previously had no individual help.

## What changed in the actual card

- Native setting info now renders **readable paragraphs**, preserves the
  expanded disclosure on refresh and shows a section **“What each option
  does / Τι κάνει κάθε επιλογή / Was jede Auswahl bewirkt”** for fixed
  dropdown choices. The current value is marked *Current choice*.
- Native numbers show their actual allowed min/max, units and step, alongside
  their purpose description; this is **input validation**, not a fabricated
  recommendation about the best target.
- Room/Home Options and Floor help keep an explicit Info control independent
  from the edit action. The two former legacy navigation gaps have
  purpose-specific localized text.
- The fast native element reconciliation updates the entire help content
  without discarding focus, an open disclosure, pending input or its saved draft.
  Every rendered string, including selected option descriptions and labels,
  is escaped as text; help never submits a service call.
- The default unknown-future equipment help no longer borrows the Climate
  entity's text (which could describe the wrong setting).
- Native help is authored in Greek, English and German. For other UI locales,
  the detailed Info text may fall back to English, rather than showing an
  unreviewed machine translation. Existing 38 localized setting *names* are
  not renamed or removed.

## Concrete example: cross-room door coordination

The per-device selector now answers all of these explicitly:

- **What:** optionally delay only a NEW Automatic start of this device when
  another suitable unit already runs across a connected, verified open
  interior door. HEM does **not** switch or stop the peer device.
- **When:** door open for at least 30 seconds, moderate local demand,
  verified relevant measurements, supported modes, no higher-priority
  sleep/away/arrival/manual/PID/urgent conditions. Delay is at most 3 minutes.
- **Inherit:** follow saved per-door policies, if any; this is not a command
  to synchronize the machines and does not create a policy where none exists.
- **Observe:** do not delay this device for inter-room reasons.
- **Opposing starts:** may briefly defer starting heating versus cooling,
  humidifying versus drying, where an eligible peer is already operating.
- **Shared starts:** can additionally defer starting for the same purpose
  when a favorable gradient suggests a peer might help; after 60 seconds the
  measured improvement is rechecked. Missing improvement releases the wait.
- **Closed/missing door:** no cross-room coordination. The feature never
  guarantees actual airflow through an open doorway.

## Verification gates

`.github/tests/test_062b22_setting_info_catalog.py` checks fixed Select
coverage against the **real shipped option IDs**, active form help in EN/EL/DE,
the room-door labels, and metadata integration.

`.github/tests/test_062b22_setting_info_browser.py` exercises the **real
Lovelace card** in Chromium at mobile/desktop widths, testing each option
explanation, selected value, readable paragraphs, numeric range, dynamic
vendor fallback, malicious-looking strings, and zero native service calls.

All existing HEM tests must still pass, including saved options, native
controllers, safety, door coordination, translations and responsive layout.

## Known limits and follow-up review

- The catalog audit counts documented **definitions**, not the set of
  controls actually displayed for a particular home/device.
- External hardware reports, sensor availability and the installed HA version
  determine which conditional settings can be edited. An Info disclosure is
  not an authorization to control anything.
- Detailed Info in the remaining languages is not yet professionally reviewed;
  retaining clear English fallback is safer than claiming native coverage.
- Physical changes, energy savings and whole-room airflow must never be
  inferred merely from the explanatory text. These still require independent
  measurement and the integration's existing safety evidence.
