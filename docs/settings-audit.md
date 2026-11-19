# HEM card setting levels

Baseline: `cbdf94b1db46d477d7ba24dc575cd37b70363554` (v0.7.4b2).

The Home, room and device settings menus use three cumulative levels.
`frontend/settings-audit-policy.json` assigns levels to exact setting
identities, with Basic as the fallback for an unrecognized new setting.

## Classification

| Minimum level | Settings available |
|---|---|
| Basic | Source and device setup; operating methods, modes and targets; presence, sleep and quiet preferences; announcements; window and door protection; device ON/OFF minimums, maximum runtime, supply cooldown, target/fan bounds, watchdog and recovery; calibration choice and Approve/Discard actions. |
| Advanced | All Basic settings, plus device Kp/Ki/Kd, PID sampling and PWM cycles, pollutant threshold customization, strategy hysteresis, room volume and rated purifier CADR, optional lux shading refinements, announcement repetition/AI wording and door start coordination. |
| Expert | All lower levels, plus process-model constants, IMC lambda, fan-capacity curves and their direct calibration actions, PMV inputs and method selection, specialist radon/pollen references, legacy room tuning and door-energy diagnostics. |

A field's minimum level does not depend on its translated name, entity ID or
current value. Per-mode fields use their published setting key, so Heat, Cool,
Dry and other supported modes follow the same classification. Target profiles
remain Basic in every mode.

### Dependencies that stay together

- Source attribute names stay beside the occupied-room and sleeping-room
  source selectors at Basic.
- A custom freshness policy and its custom age field stay Basic for Home,
  room and outdoor measurements. The age editor still appears only when the
  corresponding validity policy is Custom.
- AQI scale and a custom scale's limit stay Basic.
- Model constants and the direct **Apply Calibration** action are Expert.
  Adaptive **Approve suggestion** and **Discard suggestion** remain Basic.
- Door type and connected room stay Basic. They identify physical boundaries
  and exclusions; optional start coordination is Advanced and measured energy
  comparisons are Expert.
- The small Floor form remains fully available for name, level, icon and room
  membership.

## Selection, search and editing

The level is a presentation preference shared by the Home, room and device
menus for the current Home Assistant user in this browser. Higher levels
include every setting from lower levels. Choosing a level does not edit
integration configuration or control a device.

Search respects the selected level. Matching settings at a higher level are
counted so the user can choose a broader view. Unsaved, saving and failed edits
remain visible until they are resolved; filtering does not discard drafts or
replace their inputs. Empty categories are hidden, and clearing search restores
the user's normal accordion state.

The previous checkbox had no durable preference. An already-open legacy
dialog with its Advanced checkbox selected maps to Expert so its previously
visible controls are retained. New dialogs start at Basic unless the browser
has a saved level for that Home Assistant user.

## Existing duplicate handling

The existing Home aliases remain exact identity mappings. For example:

| Native metadata key | Existing Home Options field | Stored property |
|---|---|---|
| `global_occupancy_source_stale_minutes` | `general_source_stale_minutes` | `occupancy_global.source_stale_minutes` |
| `global_occupancy_away_cooldown_minutes` | `general_away_cooldown_minutes` | `occupancy_global.away_cooldown_minutes` |
| `home_global_policy_home_policy` | `general_home_policy` | `occupancy_global.home_policy` |

The card keeps the native fallback when the matching adapted Options field is
unavailable. Source freshness aliases added after the original audit remain in
the same policy. Home occupancy, room presence, global ventilation limits,
room targets and device overrides continue to represent their own properties.

## Inventory and verification

The explicit policy classifies:

| Scope | Basic | Advanced | Expert |
|---|---:|---:|---:|
| Native setting identities, including dynamic families | 125 | 36 | 46 |
| Home Options field keys | 33 | 18 | 2 |
| Room source groups | 8 | 0 | 0 |

The 207 native identities comprise 178 static catalog entries, seven additional
device identities, four door identities and 18 per-mode target identities.
The inventory also lists 722 config/Options label occurrences for source
navigation, including duplicated and historical forms. These are **catalog
counts, not counts of controls displayed on one device or in one menu**.

Only the card's adapted General and room Options forms receive these filters.
Initial setup and native Home Assistant Options pages remain unchanged.
Their inventory entries are marked `native_flow_unchanged`; a label alone
does not prove that a historical flow is reachable.

Run `python .github/scripts/audit_settings.py` to regenerate
`docs/settings-inventory.json`, then use `--check` to verify it. The audit
requires the embedded card policy to match the JSON source, every known key
to have a level, required setup/safety identities to remain Basic, device
manual gains to remain Advanced, and model inputs/actions to remain Expert.

Setting levels change visibility. Saved values, native entities, authorization,
validation, calibration and physical protection rules keep their existing
behavior.
