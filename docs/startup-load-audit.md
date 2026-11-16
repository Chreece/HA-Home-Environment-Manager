# v0.7.0 Home Assistant startup/load audit

## Work still performed during startup (intentional)

- Read independent HA Store records for environmental history, absence
  continuity, arrival preparation, PID/native/direct HVAC, humidity, fans,
  equipment and shade ownership before enabling normal control.
- Observe native availability and fault changes at event time. Preserve
  expected-state evidence, minimum run/off times, recoverable outage holds,
  post-HA-running native stability windows and all fail-closed rules.
- Run exactly one initial full-home environment computation after managers
  have restored their state. This supplies dashboard and controller plans.
- Keep the 30-second fast control timer where equipment or mixed legacy
  controllers require fresh occupancy/outdoor authority; keep the 5-minute
  environmental timer and wake/alarm deadlines.

## Changes and expected effect

- Before HA reaches RUNNING, bursty state/registry updates no longer cause
  an expensive rebuild on every event-loop turn. Coalescing is bounded to
  750 ms, not a periodic poll; native availability/fault observers are
  synchronous and cannot be delayed by this dashboard debounce.
- At RUNNING, tracked state changes continue to schedule one same-turn
  coalesced refresh; a pending STARTING timer is immediately superseded.
- Shade-only homes now run the direct 30-second shade tick using live HA
  evidence, without repeating all home-environment physics per clock tick.
  Full rebuilds still happen for source changes and five-minute freshness.

## Deliberately not optimized without physical traces

- Stored command/restart safety history is NOT skipped, lazily loaded or
  loaded concurrently just to improve benchmark numbers.
- Managed-device 30-second safety recalculation is NOT reduced.
- No changes to actuator grace periods, timers, power/target commands,
  watchdogs, native entity identity or room/device policy.
- Remaining opportunities need measured HA profiler/CPU traces and a
  live-device validation window; no percentage speedup is claimed.

## Test invariants

`.github/tests/test_070_startup_load.py` verifies isolated callbacks from
the production manager, including the safety-sensitive immediate observer
calls, zero full rebuilds during STARTING burst, one bounded catch-up,
RUNNING urgency, fast shading and managed controller parity. The full
repository validation suite is the release gate.
