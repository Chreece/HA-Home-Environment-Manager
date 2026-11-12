# Settings simplification: source-verified implementation

Baseline: `365f81082111b6bcd0fb2b1976eee60805ddc8b7` (v0.6.2b7).

The external Deep Research report was not retrievable during implementation.
This is an independently verified, non-destructive presentation pass, not a
claim that all recommendations in that report have been implemented.

## Decisions implemented

| Decision | Implementation | Evidence and compatibility |
|---|---|---|
| Keep everyday control and safety settings visible | Methods, targets/profiles, presence, sleep, source selectors, window protection, minimum ON/OFF, maximum runtime, watchdog and recovery actions remain in the normal view | Explicit policy allowlist; unknown new keys remain visible. No runtime changes. |
| Fold specialist tuning, not its behaviour | Advanced view contains PID numeric/plant/capacity tuning, PMV model inputs, specialist reference values, legacy tuning defaults and optional door diagnostics | `frontend/settings-audit-policy.json` records 51 exact native/dynamic identities. Saved values remain active, with no changes to registry availability. |
| Fold source-format details | Four Home form fields are Advanced: pollen scale/high threshold and occupied/sleep room attribute names | Their source selectors remain visible. These fields are still searchable/editable; no automatic inference. |
| Remove duplicate Home editors | Use the existing Home Options editor for source age, away cooldown and household presence policy | Native and Options setters address the same `occupancy_global` key. Hidden native entities remain intact for automations. A missing/unsupported form preserves the native fallback. |
| Make every setting discoverable | Search matches meaningful label, help and entity ID, including Advanced fields. Per-dialog Advanced checkbox reveals all classified settings | UI-only controls send no HA service or registry/configuration write. No new persisted preference. |
| Preserve editing and errors | Pending/failed edits remain visible through filters. Search preserves accordion state and does not recreate source editors | b7 queue, validation, target identity and confirmation behaviour are retained. |
| Leave Floor settings simple | Name, level, icon and room assignment are all useful; no extra tier is added to the small Floor form | Existing b7 autosave is unchanged. |

## Verified duplicate properties

| Native metadata key | Existing Home Options field | Stored property |
|---|---|---|
| `global_occupancy_source_stale_minutes` | `general_source_stale_minutes` | `occupancy_global.source_stale_minutes` |
| `global_occupancy_away_cooldown_minutes` | `general_away_cooldown_minutes` | `occupancy_global.away_cooldown_minutes` |
| `home_global_policy_home_policy` | `general_home_policy` | `occupancy_global.home_policy` |

Definitions/consumers: `number.py:ConfigNumber`, `select.py:ConfigSelect`,
`device_controls.py:update_device_setting`, and `room_setup.py:async_step_setup_general`.
The new aliases use exact registry/setting identities, not translated labels.

## Similar names that are NOT treated as duplicates

- Home occupancy and local room presence have different authorities.
- Global ventilation thresholds, room operating targets and device/profile
  overrides feed different decisions. They are not merged.
- Door closed/open evidence does not establish occupancy or airtight isolation.
- Minimum ON/OFF, maximum ON and supply cooldown protect different transitions.
- Manual PID gains, learned-model inputs, per-mode values and legacy fallback
  values are not interchangeable. They remain available in Advanced.
- A legacy translation or a missing literal search result does not prove dead
  code. Dynamic generation and historical option flows require separate tracing.

## Inventory and remaining audit work

`settings-inventory.json` contains 175 static native setting catalog entries,
718 config/options form-label occurrences (including duplicates and legacy
steps), five per-door identities and 18 dynamic target identities. These are
**catalog counts, not a count of controls displayed to one user or device**.
The file records classification, source navigation references and explicit
verification limitations. The full dynamic consumer graph and legacy step
reachability have not been exhaustively proved. No field is deleted as dead
on the basis of this catalog scan.

Regenerate with `python .github/scripts/audit_settings.py`; CI verifies that
both this inventory and the embedded frontend policy match the source.

## Compatibility and scope

No stored value, default, unique/entity ID, actuator permission, native entity,
backend validation, PID, physical dwell, controller recovery, registry
assignment or Announcement Hub routing is changed. No configuration migration
or automatic user-server installation is performed. Advanced hides editors,
not active behaviour. No performance or energy-savings claims are made.
