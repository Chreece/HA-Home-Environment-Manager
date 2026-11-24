# Detailed configuration and behavior

[← Back to the HEM overview](../README.md)

This guide documents HEM's more detailed setup choices, prerequisites, safety checks, and runtime behavior. The [README](../README.md) is the easier starting point, with screenshots and real-life examples. **Monitoring and recommendations do not require authorizing any equipment.** Use automatic control only for the devices and modes you explicitly select.

---

## Home Assistant startup, restart and shutdown

HEM restores saved controller state before enabling control. Up to four
independent stores load concurrently; presence continuity finishes before
arrival preparation reads household status. Environment-history sanitization
runs in the executor. Saved review notices and automatic announcements wait
until Home Assistant is running, and optional deliveries run as owned
background tasks. Direct notification and TTS calls have a 10-second deadline;
Announcement Hub retains its existing acknowledgment deadline.

When Home Assistant starts stopping, HEM immediately disables new scheduling
and cancels its timers and optional work. Controller cleanup and state flushes
share a 10-second budget, followed by a brief cancellation drain. A full Home
Assistant stop does not begin the legacy controller's reload-only safe-OFF
sequence. An ordinary integration reload retains that sequence, but refuses
to start a replacement manager if teardown fails or exceeds its budget.

These limits cover HEM's cleanup, not the entire Home Assistant or host shutdown.
Home Assistant can perform its final storage writes afterward. Physical devices
may keep their last native state while Home Assistant is offline; HEM's device
ownership, saved gains, minimum operating times and restart journals remain
part of recovery when it starts again.

## Choose how many settings to show

The HEM card's Home, room and device settings menus have a **Settings level**
selector. Each level includes the settings below it:

| Level | What it adds |
|---|---|
| **Basic** | Everyday controls, source setup, modes and targets, presence/sleep preferences, safety limits, watchdog/recovery and calibration approval actions. |
| **Advanced** | Manual device Kp/Ki/Kd, PID sampling/cycle adjustments, detailed thresholds, optional strategy and announcement refinements. |
| **Expert** | Process-model constants, custom fan-capacity curves, their calibration actions and specialist comfort/reference inputs. |

The selected level is remembered for your Home Assistant user in this browser
and follows you between the three menus. It changes which editors you see;
your saved settings keep their values and remain active. Search follows the
selected level and reports matches hidden at higher levels. A pending or
failed edit remains visible so you can finish it or correct its error.

Use **Advanced** to edit a device's PID gains. Calibration status and adaptive
Approve/Discard actions are available at Basic. Choose **Expert** for manual
plant-model calibration or custom fan-capacity inputs. Initial setup and the
native Home Assistant Options flow retain their existing controls.

For the exact classification and its source audit, see
[HEM card setting levels](settings-audit.md).

## First setup

### 1. Prepare your Home Assistant areas

Create an area for each room you want to monitor and assign its sensors and
devices to that area. An entity's own area assignment takes precedence over its
device's area. HEM uses these assignments to suggest sources.

For ventilation advice, also have a weather entity and outdoor air-quality
sources available. Additional features need their corresponding inputs: window
contacts for window state, occupancy sources for presence, and controllable
appliances for climate control.

### 2. Choose rooms and review their sources

The setup wizard starts with **Choose rooms**, then shows one source page for
each selected room. Review the suggestions and select the entities that actually
describe that room.

| Source group | What to select |
| --- | --- |
| **Windows** | Genuine `window`-class contact sensors are preselected. `door` and generic `opening`-class binary sensors are also available but **unchecked by default**; select only balcony/patio doors or other real exterior openings that should count as windows. |
| **Air quality and environmental sensors** | Supported pollutant sensors and optional environmental readings, such as illuminance |
| **Temperature** | Room temperature measurements |
| **Humidity** | Room relative-humidity measurements |
| **Devices** | Native `climate.*`, `humidifier.*` and `fan.*` appliances |
| **Window blinds, shades and shutters** | Supported `cover.*` shading devices |

Leave unused groups empty. Saved empty selections stay empty. A blind or shutter
belongs in the shading group; window-state inputs come from contact sensors.
**Home Assistant has no dedicated balcony-door device class:** a balcony door
may be classified as `door`, `window` or `opening`. HEM does not infer
this from its name. Door/Opening contacts are suggested for manual selection
only; they are never automatically included in the Windows group. A chosen
contact can also remain in the separate Door settings for room-boundary or
Eco policies. The room shows **Needs attention** and names any contact with
a missing, unavailable, unknown or restored reading. Equipment uses the remaining
live contacts. A confirmed open window still pauses opted-in equipment, and its
confirmed closure starts the normal 60-second delay. A sensor returning from
an outage with a closed reading can participate immediately.
Do not use garage-door, motion or powered-cover entities for window evidence.

### 3. Complete General settings

Choose the shared inputs and optional features you use:

- **Weather and outdoor air quality:** the sources used to judge ventilation
  conditions. Optional warning and pollen sensors add further context.
- **Home occupancy:** people, trackers, presence sensors or explicitly selected
  people counters. You can also choose shared occupied-room and sleeping-room lists.
- **Announcements:** direct notification destinations, media players and TTS, or
  your configured Announcement Hub. **Announcement language** defaults to
  **Home Assistant language** and also offers all 38 languages supported by HEM.
  Choose an optional AI agent here too.
- **Mold indication and ventilation limits:** enable mold indication if you will
  calibrate it, and review the outdoor temperature, humidity, wind and pollution limits.

After saving, review **Ventilation · AQI scale** on the HEM Home device for each
AQI source **if you want to use its index for decisions**. Select the
provider's actual scale, or configure a custom scale and limit. A numeric
index without a verified scale cannot be compared meaningfully.

**AQI is optional.** An index whose scale has not been configured remains
visible as *incomplete information*; it never blocks ventilation, forces
window closure, or invalidates otherwise verified outdoor pollution readings.
You do not need an AQI sensor at all. Actual PM2.5, CO₂ and other supported
physical measurements keep their own limits and safety rules; a **verified
unsafe AQI** still correctly blocks unsuitable outdoor air. The dashboard
labels outdoor data **partial** when optional AQI readings are unverified.
Automatic outside-air intake still requires separate valid, supported
pollutant evidence; unknown AQI readings do not count as proof of clean air.

Ventilation limits identify outside conditions that need caution and continue
to protect automatic use of outside air. A measured indoor need can still
produce a conditional request to air the room briefly, naming the detected
cold, heat, humidity, wind, weather alerts or pollution. Missing outside data
is described as uncertain. HEM does not describe these conditions as suitable.
These limits are separate from a room's heating or cooling targets.

You can also change the announcement language on the HEM **Home Environment**
device under **Announcement · Language**. The default follows Home Assistant's
configured language when each announcement is sent. An explicit choice applies
to announcement text, AI rewriting and the language sent to Announcement Hub or
direct TTS. The full menu is available even without a TTS provider; spoken output
requires the selected provider to support that language.

### Give window airing a chance before automatic devices start

Each eligible device controller has **Ask to open windows**, which defaults to
**off**, and its own **Window opening wait (min)**, which defaults to **5 minutes**
and accepts **0-30 minutes**. These appear beside the device's control settings
in the card and as native Home Assistant entities. Turn the option on only for
devices where you want an airing request before automatic operation. With the
option off, the device follows normal demand without this added delay. A wait
of **0** also removes the added delay. The shared **Window opening timeout** in
General remains available for existing room-controller paths.

The general mold, humidity and particle announcements respect this preference
too. When an authorized, available automatic device can handle that problem
with its airing option off, HEM does not ask you to open a window for the same
problem and adds no window-response wait. Other reasons still appear: a
particle purifier does not remove CO₂. An unavailable, unauthorized or paused
device, or one with an invalid configured supply, does not silence advice or
create a promise that it will start.
If another device in the same room has airing enabled, it does not add a
redundant request or wait for a problem already covered by that ready device.

When opening a real, closed room window could help, HEM requests it through the
enabled automatic announcement channels. Opening requests name the room and
explain the reason; they do not list the contact sensors. Closing requests name
the room and the friendly names of the windows that are actually open, together
with the reason for closing them. When an opted-in Automatic/PID device would
otherwise start for a problem that airing can also reduce, the request names
that device and its response time. HEM briefly defers that new start while submitting the
request. Submission is bounded to 130 seconds; a rejected or failed delivery
releases it immediately. Once a direct output succeeds or Announcement Hub
accepts the job, the configured response timer starts. Hub acceptance confirms
queueing, not that someone has heard the message.

If the window stays closed until the timer expires, normal device control
resumes if demand still exists. Repeated announcements and changing sensor
numbers do not extend the deadline. Each device has its own deadline, and an
unanswered request is consumed for that demand episode instead of restarting
the wait at every reminder. Opening the window hands control to the
device's existing window policy; closing it retains the normal stabilization
and minimum operating-time checks. This option is independent of the device's
**Window protection** setting. Running equipment, manual commands and OFF
commands retain their own behavior. Humidifiers, dehumidifiers, thermal devices
and particle-filtering air purifiers can participate when measurements support
the same benefit from airing; an extraction fan is not an indoor alternative.

The bounded response wait requires someone home and an awake room, verified contacts in that
room and an enabled announcement channel. Outdoor warnings remain in the
message; airing that would demonstrably worsen the relevant humidity or
pollutant measurement is not suggested for that purpose. Actionable opening
requests use Announcement Hub's **warning** level, so a warning-level TTS
threshold can include them. Optional wake/return timing reminders remain
informational. HEM sends the complete reasons, cautions and response times to
the delivery destination. When AI announcements and Announcement Hub are both
enabled, HEM requests the Hub's AI rewrite and lets the Hub own that delivery.
Direct HEM delivery retains complete caution and timeout wording.

## Add the dashboard card

HEM includes and automatically registers its dashboard card. In dashboard edit
mode, add the **Home Environment Manager** card. You can also use a manual card:

```yaml
type: custom:home-environment-manager-card
```

The card detects the recommendation sensor when there is exactly one candidate.
If you need to select it explicitly, choose HEM's **Window recommendations**
sensor in the card editor. For YAML, replace the sample entity below with your
actual entity ID:

```yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
show_outside: true
show_metrics: true
show_science: true
```

Entity IDs can differ with your language, naming and renames. The older
`custom:home-environment-manager-card` type remains supported.

### Using the card

Each room tab starts with the settings cog, the room name and its condition faces.
Hover the faces, or expand the room on a phone, to read their localized meanings.
Activity and alert icons on the right retain their own tooltips or actions.
Readings underneath open their usual details and trends.

The faces show simultaneous measured conditions. Temperature uses the current
PMV estimate (neutral from −0.5 to +0.5), then the adaptive comfort band when
applicable, then a simple 20 to 26 °C display range. Indoor relative humidity
below 30% is dry. The configured indoor humidity warning threshold marks humid
conditions (default 65%). A measured indoor pollutant exceedance can show poor
air even when temperature and humidity are missing. A smile requires both
thermal and humidity data and no outstanding issue in the monitored air readings.
Missing evidence has a neutral face. These descriptions do not operate equipment.

When Home Assistant has configured floors, HEM groups each monitored room under
its real HA floor. Floor groups can be expanded or collapsed independently and
show room counts and whether any of their rooms need attention. Rooms not
assigned to a floor appear under **Rooms without a floor**. The floor gear lets
an HA administrator change that floor's name, level, icon and the room
assignments, or open the existing settings of an individual HEM room. These
floor settings use the native Home Assistant floor and area registries and
never control a heater, fan or dehumidifier themselves.

If you have **no Home Assistant floors**, HEM displays the original flat room
list, with no floor heading or floor settings. Create or assign floors in
**Settings → Areas, labels & zones**. Renaming or moving areas in Home Assistant
updates their HEM groups without duplicating area configuration. Room targets,
sleep, PID and other environmental controls remain independently configured
per room; floor-wide environmental overrides are not implied.

- Read the outdoor summary and room status, then expand a room for its advice,
  additional measurements and device controllers. Expanded tiles show data
  that is not already in the room overview; warning and calibration details
  remain available without repeating the same current value.
- Open information and warning details to understand missing inputs or the
  reason for a recommendation.
- Use a room's settings gear to edit its selected sources. **Room controls**
  opens the room's Home Assistant device page.
- Open an averaged room reading (**≈**, with multiple contributing sensors) for
  HEM's trend view and choose **6 h**, **24 h**, **7 d** or **All**. Inspect points
  with the pointer, touch/drag or keyboard; gaps represent missing readings.
  Single-sensor readings and contributing sensors open the same trend window
  using their recorded Home Assistant history. **Open entity** opens that
  sensor's native Home Assistant details. History remains useful when a current
  value is unavailable; sources excluded from recording may have no history.
- Matching controllers add their recorded targets to the trend. Stepped lines
  show when a target or profile changed, and each controller keeps its own
  identity. Measurement, target, HEM's requested demand and the device's
  reported activity or output setting share one graph and one time axis.
  Measurements and targets use the left scale in the reading's unit; demand
  and output use the right percentage or On/Off scale. The legend identifies
  each controller and line, and one cursor inspects their values at the same
  time. A fan percentage or valve position is a reported setting, not measured
  airflow or power.
- Targets use the exact feedback sources and quantity represented by the
  chart. For mold control, the mold chart shows the surface-humidity target;
  the corresponding room-humidity chart shows the effective room-air target.
  Temperature targets follow the chart's temperature unit. Off, missing target
  evidence and Manual without an explicit HEM target leave the target line
  empty.
- Average history keeps separate records for each exact group of contributing
  sensors. Temporary startup outages do not replace the original group's
  samples. A returning group resumes its history with a visible gap.
- The room-average and mold popups fetch detailed retained observations only
  when opened. The small preview in the normal dashboard is not used as the
  complete history of a 6-hour or 24-hour chart. Unavailable intervals and
  restart boundaries remain visible; HEM does not fill them with invented
  measurements.
- The icon before a physical entity's name opens its device page; the icon
  before a HEM controller's name opens its HEM device page. Clicking either
  name opens the corresponding entity. Announcement controls show the bell
  icon and current On/Off state.
- For a waiting controller, read its **Reason** and **Diagnostics** before
  changing settings.

Opening advice compares indoor needs with the available outdoor evidence.
Useful manual airing can still be suggested with detected weather or pollution
cautions and explicit uncertainty about missing or stale outside readings.
HEM does not claim a moisture or pollutant benefit contradicted by comparable
outside measurements. Read the room's reasons and diagnostics for the basis
of the recommendation.

## Where to change settings

Use **Settings → Devices & services → Home Environment Manager → Configure**
to choose rooms, open **Settings · {room name}**, or edit **General settings**.
The room page also lets you select that room's occupancy/presence sensors.

Everyday operating settings are grouped on the integration's devices:

| Device | Settings you will find there |
| --- | --- |
| **Home** | Shared ventilation limits, announcements, occupancy and source-specific AQI settings |
| **{Room} Environment** | Room targets, sleep, mold and other room policies |
| **Individual device controller** | That appliance's control method, targets, supported limits, behavior and PID options |

Setting names use prefixes such as **Announcement**, **Ventilation**, **Sleep**
and **PID** so related controls stay together. Help explains what each setting
changes. Removing a monitored room revokes its automatic controls; replacing or
moving a physical device can require choosing its control method again.

Each controller's shared quick options appear in one compact row. Select an
option's **icon** to read its explanation, or its adjacent **state** to change
that exact option. Window protection, device-error announcements, opening
requests and supported optional behaviors share this row. Mode methods and
their parameters stay inside their individual mode panels.

The help explains the effect of both On and Off and which conditions apply to
that device. **Announce device errors** controls error delivery; fault detection
and device protection remain active when announcements are disabled.
**Maximum target by mode** lists only the device's supported native target
modes, such as **(Heating, Cooling)** or **(Dehumidifying)**, using translated
mode names. **Keep device off when all asleep** explicitly pauses an opted-in
automatic device while the household sleep condition is confirmed.

### Detect possible heating while a heater reports Off

HEM monitors independent, fresh room temperature sensors after a supervised heater
acknowledges an OFF command. It also starts a fresh observation when a supervised
heating-only valve already reports OFF, including at startup. HEM excludes the
heater’s own temperature probe before averaging the room thermometers. Older
setups can use their assigned device or PID-room thermometer. After a 30-minute
thermal settling period, if
the room continues warming for at least 15 minutes (≥0.7°C increase and
≥1.5°C above the heating target), HEM records a **suspected** thermal fault.
The device can still report OFF while physically heating; room temperature
alone never proves that a valve/relay is active.

Before attributing a rise to a heater, HEM compares fresh outdoor temperatures
and sky conditions with independent readings from neighboring rooms. It uses
configured room connections in either direction. Without mapped connections it
checks the other monitored rooms. A warm neighboring room can transfer heat
even with its door closed. Outdoor or neighboring readings within 0.5°C of the
watched room are treated conservatively. If configured, room illuminance from
the shade settings can identify possible local solar gain even on an overcast day.
Sunny daytime conditions, missing
weather, or missing readings from a relevant neighbor can also explain or
obscure the warming. The controller exposes unattributed warming in its watchdog
diagnostics and withholds heater-specific warnings and OFF retries in those cases.
After a competing source clears, one continuous temperature rise can still
include stored heat. HEM keeps that rise unattributed until the independent
room thermometers show at least 15 minutes of stable or falling temperature.
Readings must finish at or below the start of that interval. A rebound of more
than 0.1°C from the observed minimum restarts the interval. Only a subsequent
fresh rise can qualify for a temperature-based heater warning. Restarting Home
Assistant preserves the unresolved heat and retry count, and starts fresh
observations. PID calibration excludes the affected OFF baseline.

A fresh positive actual valve-position report while disabled is separate evidence
for an OFF retry even when other heat sources are present. It establishes valve
travel, while the cause of the room temperature rise can still be mixed.

For HEM-commissioned heating endpoints with unchanged identity, available
native sources, no conflicting heater and authorization to control the device,
HEM may send **at most two** additional OFF commands, 10 minutes apart. HEM
never infers permission to turn anything ON. The original OFF time and retry
budget persist across restarts. If the anomaly remains, HEM escalates via the
same device-error notification channels, including Announcement Hub. The
controller diagnostics show the room temperature evidence and recovery count.

This uses Home Assistant's generic heating capabilities; there are no
brand-specific Zigbee profiles or entity-ID lists. HEM excludes its own virtual controllers from the competing-heater check.
A native thermostat reporting idle can coexist with the watch. Active or uncertain
competing heaters prevent attribution. Long OFF periods renew the temperature
observation window while retaining the original retry count.
Solar gain, residual radiator heat and unknown heat sources are still possible.
A native reported OFF is **not proof of physical shutdown**.

## Enable device control

1. Select the appliance in the room's **Devices** group and save.
2. Open its HEM controller through **Device controllers** in the card or the
   integration's device list.
3. Review its feedback sensors, targets, presence/sleep behavior and supported
   limits. For fans, check the intended purpose and minimum/maximum speed.
4. Choose the method in each supported operating-mode panel, such as
   **Heating**, **Cooling**, **Drying**, **Humidifying** or **Fan**.

| Method | What it does |
| --- | --- |
| **Existing room controller** | Keeps the existing controller path without handing operation to the new per-device method |
| **Automatic** | Follows HEM's automatic demand and profile decisions |
| **Manual** | Uses explicit requests and targets through the HEM controller |
| **Off** | Requests the controller/device off, subject to its operating protections |
| **PID** | Uses feedback-based PID demand control where supported |

Choosing **Automatic**, **Manual** or **PID** authorizes operation of that exact
native appliance through its supported controls. If HEM asks you to turn an
already running appliance off first, do so and wait for its reported state
before taking control.

The authorization is bound to the physical device and its registered control
endpoints in that room. Changing room feedback sensors or reordering the same
sources does not invalidate a selected method. Existing grants are recognized
only when those physical identities still match.

An unacknowledged command does not change **Automatic** or **PID** to Manual.
While demand and authority remain valid, HEM retries unconfirmed native power
and mode commands every **60 seconds**. After **three unsuccessful dispatch
attempts** it announces that the device is not responding to HEM, while
continuing to retry.
Unavailable checks do not count as dispatch attempts. Device availability,
window policy and minimum operating times still constrain each attempt.

Full-demand native setpoints for **PID ON/OFF control** are best effort. HEM
makes at most **three actual dispatch attempts** for the same request. If the
device still reports a different target, HEM records the unconfirmed result,
stops retrying that target and continues its automatic ON/OFF control. This
allows devices whose continuous mode ignores a temperature or humidity
setpoint to remain under PID control. The displayed native target remains
the device's reported value; native ON/OFF commands still require feedback.

A confirmed manual change on the appliance after HEM has successfully
controlled it can pause automatic control. Use
**Control · Continue Automatic** when you want HEM to resume. Window state,
availability, presence policies and minimum ON/OFF times still apply; the reason
display explains ordinary waiting periods.

### Independent operating modes

Each supported mode has its own method dropdown and **Parameters** section.
Heating can use PID while Cooling uses Automatic and Drying uses a separately
tuned PID. Gains, measurement/cycle timing, calibration, profile targets and
supported fan/swing/quiet settings belong to their mode. Editing an inactive
mode does not restart the active mode's cycle or change its pending command.
The device keeps one physical controller; window, presence, power supply and
minimum ON/OFF protections remain shared.

The native **Auto** and **Heat/Cool** modes retain their supported automatic
and manual choices. PID belongs to an explicit direction: use the separate
Heat and Cool panels when the appliance advertises those modes. Fan PID needs
qualified feedback for its configured extraction or filtration purpose.

Resume, a change to the active control settings, a real policy pause or loss
of valid feedback invalidates the old PID integral and cycle checkpoint. When
operation becomes eligible again, HEM calculates a fresh cycle. HEM remembers a
disconnect and reconnect even if both occur between evaluations. A change to a
fixed target starts a fresh cycle even below 0.25 degrees. Small fluctuations in
calculated comfort or mold targets keep the existing phase. Normal PWM
OFF periods and minimum-OFF waits keep their current phase. These resets never
erase physical run/rest history, an unconfirmed native command or a genuine
manual override.

Low PID demand can need a longer ON/OFF cycle to fit the appliance's minimum
operating times. If a controller check misses the scheduled start, HEM keeps
at most one overdue pulse and starts it when the existing physical protections
permit. Its timing follows the confirmed device start, including the full
following OFF period. Missed cycles do not accumulate into a burst of heating
or cooling. Controller status exposes the effective PID target, selected
measurement, demand and next scheduled window for diagnosis.
These timings use confirmed native state; delayed appliance feedback can
affect the duty actually delivered.

Device status distinguishes a missing physical source from Home Assistant
startup and an available device's stability checks. Diagnostics include the
selected source, readiness deadline, effective cycle and operating minimums,
last confirmed ON/OFF times, and the **next eligible window**. Eligibility is
followed by fresh demand, feedback and operating-protection checks; it is not
a promise that the physical device will start at that instant.

For a supported appliance with Automatic/PID permission to control native
ON/OFF operation, its **Maximum target by mode** option determines whether HEM
writes a native target during the ON period. Enabled by default, it requests
the appliance's reported maximum during heating or humidifying and its
reported minimum during cooling or drying. This keeps the appliance's internal
thermostat or humidistat from ending HEM's requested ON period early when its
local sensor differs from the selected room sensor. Turn the option off to
leave the native setpoint unchanged, including devices whose continuous mode
ignores target changes. HEM's room target still determines demand and when to
request OFF, with the configured operating minimums and confirmed feedback.
Devices authorized only for setpoint changes keep their bounded target
adjustments; Dry modes without a native humidity setter use their supported
mode control.

Appliances advertising fan modes such as **low**, **medium** and **high** also
have staged fan control. HEM selects from their available stages and applies
the active occupied/sleep quiet limit to the final speed command. A pending
optional native target does not prevent a required quiet fan reduction.
Fan-stage control and compressor ON/OFF timing remain separate; advertised fan
speeds alone do not establish proportional compressor control.

### Room-presence choices

The controller's **Presence · Requirement** setting decides when **Automatic**
and **PID** may operate this particular device:

| Choice | Meaning |
| --- | --- |
| **No room-presence restriction** | Meet demand whether this room is occupied or empty, using the active target profile. This does not mean continuously ON. |
| **Only while room is occupied** | Allow operation only when HEM confirms someone is in this room. |
| **Only while room is empty** | Allow operation only when HEM confirms this room is empty. Someone may still be elsewhere at home. |

If room presence is unknown, the two restricted choices pause operation.
Confirmed whole-home **Away** takes priority over room sensors and counts every
room as empty. A valid shared occupied-room list is authoritative: a room
included in it is occupied and a room omitted from it is empty. With neither a
configured room list nor any room-presence sensors, HEM treats the room as empty.

When a presence condition stops matching, HEM requests OFF for an output it
already controls, respecting its current minimum ON time and native protections.
Presence permission does not create demand or override sleep, window or other
control rules. The stored choices and existing selections remain unchanged;
the labels now state their meaning directly.

The optional **Prepare for arrival** action temporarily allows eligible automatic
controllers restricted to occupied rooms to prepare those rooms while everyone
is still away, using their existing permission for native ON/OFF control. It
preserves the actual presence readings and the stored choices.
See [Prepare for arrival](#prepare-for-arrival) for its scope and timeout.

### Device operating times

Each controller has **Operation · Minimum device ON time (min)** and
**Operation · Minimum device OFF time (min)**. These govern how long HEM keeps
the device operating or stopped before requesting the opposite state. For a
radiator valve, this is its controlled heating operation.

Both settings accept **0 minutes**, which disables that forced operating
hold, and fractional minutes retain the existing one-second resolution.
For example, **0.5 min** means 30 seconds and **10 min** means 600 seconds.
**Power · Maximum ON time (min)** also displays and accepts minutes, with a
one-minute step and the same supported duration limits as before. These
physical operating limits are shared across the device's operating modes.

Saved durations and entity identities are preserved across installation changes. Existing
settings are converted for display, so 600 stored seconds appears as 10
minutes. Home Assistant number edits and `number.set_value` calls for these
three entities now take minutes. PID measurement/PWM intervals and the
separate supply-switch cooldown retain their own units.

Choose any required
minimum interval from the appliance manufacturer's guidance; compressor
equipment and radiator valves need different operating policies. Aqara's
[E1 guidance](https://www.aqara.com/eu/product/radiator-thermostat-e1/faq/)
also notes that frequent on/off cycling increases valve motor use and battery
consumption.

HEM preserves existing effective timings until you explicitly edit
one of these minimums. Editing one preserves the other minimum. An ON minimum
already recorded for a running cycle completes first; following cycles use
the new setting. Zero does not fabricate device feedback or skip confirmation
of a pending command. Existing external supply-switch protections remain
independent of the newly chosen operating hold.

### Targets and profiles

Review heating, cooling and humidity targets for **Comfort**, **Home**, **Away**,
**Sleep** and **Eco**. Presence, sleep context and an explicit preset influence
the active profile.

Each mode's target numbers initially follow the room's profile. An explicit
mode target overrides only that mode and profile, including a separate Manual
target. The card and native configuration numbers retain the requested value.
For Automatic/PID dehumidification in a monitored room with mold indication
enabled, each profile's percentage target applies to the calibrated surface
humidity indication. With mold indication disabled, it applies to room-air
relative humidity. Switching profile immediately selects that profile's saved
target and recomputes the required room-air target. The general mold warning
threshold is separate from these control targets.

| Profile | Default percentage target when no target is saved |
| --- | --- |
| Comfort, Home, Away, Sleep | **65%** |
| Eco | **70%** |

Your saved targets remain in effect. These are HEM's starting control values;
adjust them to your room and supported appliance range.

Advanced ISO 7730 comfort inputs are optional. Ordinary temperature/humidity
control does not require them. When a maximum native target is enabled, HEM
requests it after confirmed native ON. When stopping is permitted, HEM requests
OFF directly. Demand, minimum operating times and device protections determine
the ON period, and native OFF feedback confirms shutdown.

### Optional PID calibration

First select **PID** in the relevant operating-mode panel on the appliance's
controller, then open that mode's **Parameters**.

For a first adaptive setup, **PID · Calibration → Adaptive · Suggest & approve**
learns from normal operation. Review the proposed gains and confidence, then
choose **Approve** or **Discard**. If approval is held, the proposal remains
pending. Resolve the displayed condition and press **Approve** again.
**Adaptive · Automatic (max 10% per change)** is a separate opt-in mode that
applies validated, bounded adjustments automatically.

Adaptive calibration uses the **same supplied measurement that drives PID**:
temperature, humidity, CO₂ or PM2.5, including the exact room average and its
contributing sensors. Actuator feedback serves a different purpose. HEM requires a
fresh report of physical activity, such as heating, drying, actual valve position
or measured fan RPM, before crediting an active interval. Unknown activity breaks
the observation segment. Reported idle or OFF periods supply a baseline.

The observer assesses normal measurements from short cycles and continuously
modulating outputs. There is no fixed 75-minute ON requirement or daily tuning
timer. Observations must still contain enough fresh samples and useful output
variation to identify a response; a flat or noisy trace cannot establish which
new gains would improve it. **Good control retains the current gains.** For
CO₂ and particle limits, measurements below the limit count as success.
Performance information updates with fresh reports. Model identification
starts after at least 32 qualified reports, which can span several short
cycles. The current implementation tests bounded Kp/Ki adjustments and preserves
Kd and any deliberately disabled zero gains.

When improvement is justified, a small candidate is checked against a local
response model, independent validation observations and HEM's actual PID and
actuator constraints. The observer distinguishes tuning problems from stale
measurements, limited capacity, dwell limits and unconfirmed actuation. Normal
calibration does not force an experimental cycle or shorten device protections.
On a native thermostat HEM checks both its command or target acknowledgement
and the reported activity. An enabled relay, fan speed setting or confirmed
setpoint alone supplies insufficient evidence for automatic gain changes.
Previously applied gains remain in place. New observations use a separate
evidence history from versions that accepted commands alone.

Only one gain trial is evaluated at a time. Switching outputs apply at a safe,
confirmed OFF boundary; continuous outputs preserve the current PID demand
when transferring to the new gains. Comparable subsequent observations decide
whether to retain the change or restore the previous gains. Changing sources,
targets, modes, controller settings or manual gains invalidates incompatible
evidence. A restart preserves completed evidence and committed changes but
starts a fresh observation segment, so time offline never counts as measured
response. The card explains whether HEM is observing, retaining good gains,
waiting for a constraint, proposing a change or verifying an applied trial.

For a measured model, choose **IMC / λ** or **Cohen-Coon**, enter the measured
process gain, time constant, dead time and λ where applicable, then use
**PID · Apply · Calibration** with the native output off and its state confirmed.
This calculates gains from your inputs; it does not run a live measurement test.
Calibration inputs, applied gains and reviews stay with the observed mode;
heating evidence cannot be applied as a drying calibration.

## Presence and sleep

### Home Occupancy

In **General settings**, select direct home sources under
**Home · Occupancy · Devices**. A fresh positive source means someone is home.
When all configured direct sources are freshly away/off/zero, home presence
becomes Away and overrides room activity. Automatic profile selection uses Away
unless an explicit preset is selected. Unknown or unavailable evidence does not
prove that everybody is away.

While configured home-presence sources are unresolved, Automatic/PID cannot
start an appliance or increase its output using a fallback Home target. HEM
rechecks the live presence and target before a command, including after a
restart. A valid explicit preset or Manual selection keeps its own control
semantics. Physical OFF protections and settings editing remain available.

Sensor values marked as restored by Home Assistant are ignored until the
sensor publishes a real reading. A restored old temperature cannot lower a
room's current average and create heating demand.

Without direct home sources, HEM can derive home presence from room evidence.
The Home occupancy away-delay setting applies to that room-derived absence.
It is separate from the announcement repeat interval, even when both show
10 minutes.

### Prepare for arrival

When HEM confirms that everyone is away, press **Prepare for arrival** in the
card header or on the **Home Environment** device. HEM temporarily uses the
room's configured **Home** targets for eligible automatic controllers so heating,
cooling and humidity control can begin before you get home. Devices still run
according to measured demand; the action does not turn every appliance on.

To start preparation automatically, select **Residents to track** in Home
settings. Choose one person or GPS tracker per resident. The two radii are
measured in metres from the centre of Home Assistant’s Home zone. Zero
disables each rule independently.

| Setting | When it takes effect |
| --- | --- |
| **Occupied radius** | The home counts as occupied while at least one resident is confidently inside. |
| **Preparation radius** | After all selected residents were confirmed outside, the first entry starts the Prepare for arrival timer if the home is still Away. |

For example, set preparation to 5,000 m and occupancy to 500 m to start
conditioning on the approach and switch to normal Home control nearer home.
GPS uncertainty at the boundary, startup inside it and repeated updates during
one approach do not start additional timers.

Set **Home - Prepare - Max Time** on the Home Environment device, or
open that setting from the duration control in the card. The default is
**60 minutes**; the allowed range is **1-1440 minutes**. Changing the setting
affects the next press and leaves a running deadline unchanged.

| Event | Result |
| --- | --- |
| Press Prepare while confirmed Away | Start the configured duration using Home targets. |
| Press the native Prepare button again | Renew from now using the current timeout setting. |
| Someone arrives | End preparation and let normal home/room presence and sleep rules select the profile. |
| Timeout expires while still Away | Return automatic profile selection to Away. |
| Press Cancel in the card or on the device | End preparation immediately and recalculate from actual presence and current settings. |
| Presence becomes unknown | Suspend the preparation effect; the original countdown continues. Resume only if Away is confirmed before expiry. |
| Home Assistant restarts | Restore the original expiry time; never restart the full duration. |

The card shows the remaining time and changes the action to **Cancel** while
preparation is active. Narrow cards use an accessible icon with the full action
in its tooltip. Start is unavailable when someone is home or home presence is
unknown; it does not queue an action for a later absence.

Preparation applies to **Automatic/PID with automatic profile selection** and
eligible automatic room control. It includes devices normally restricted to
occupied rooms when their managed controller already has permission and support
for native ON/OFF control. Actual home and room presence remain unchanged, and empty-room
requirements continue to use the actual absence. Explicit presets, Manual, Off
and manual pauses retain their authority. Window checks, valid sensor inputs,
device availability, minimum ON/OFF times, power limits and startup protections
continue to apply. Therefore cancellation or expiry can change the requested
profile before an appliance's permitted physical transition occurs.

Existing room controllers and migrated controls authorized only to change a
setpoint keep their original presence restrictions. Unrestricted ones can follow
Home and Away targets normally. Preparation does not grant them new power
control or leave an elevated Home setpoint behind a closed presence gate.
An already-running native thermostat also receives the current profile's
setpoint when the room is within the profile's temperature range, without a
mode change, so its temporary Home setpoint can return to Away after expiry.

### Room presence and shared lists

Select local presence sensors on each room's source page, or configure a shared
occupied-rooms source in General settings. For a shared list, select **State**
or the attribute containing the list. For example:

```json
["living_room", "bedroom"]
```

Use your actual Home Assistant area IDs, names or unambiguous aliases. A valid
list takes priority over local room sensors: listed rooms are occupied and
omitted rooms are unoccupied. `[]` or an empty state means no rooms are occupied.
An unchanged list remains valid overnight; it does not need to publish the same
value repeatedly. The same applies to binary occupancy/presence sensors that
remain On or Off.

When no shared list is configured, or its entity is missing, unavailable or
awaiting a live report, HEM checks local presence sensors. Any selected sensor
that is On means the room is occupied; all selected sensors Off means unoccupied.
A room with no presence sources is also treated as unoccupied for control and
room display. Unavailable selected sources can still produce Unknown. Malformed
lists and unknown room names remain Unknown rather than using sensor fallback.
Sampled numeric occupancy counts retain their configured freshness limit.
Verified whole-home Away takes precedence over room activity.

### What the room sleep settings do

| Setting | Purpose |
| --- | --- |
| **Sleep · Sleeping now** | Marks the room as currently sleeping for climate sleep behavior |
| **Sleep · Use schedule** | Enables the local-time sleep interval; the default is **22:00-07:00** |
| **Shared sleeping-room list** | Activates Sleep when the room is both occupied and in the selected list |
| **Noise · Room used for sleeping** | Classifies the room for calibrated nighttime noise assessment |

Sleep context can select sleep targets or a device's configured sleep/quiet
behavior. Turning **Sleeping now** off does not override an active schedule or
shared sleeping-room list. The noise classification does not activate climate
Sleep.

### Leave Sleep before an alarm

In **General settings**, select both of these inputs:

| Setting | What to select |
| --- | --- |
| **Sleep · Next alarm** | A timestamp sensor such as a phone's next alarm, a date-and-time helper, or a time entity/helper |
| **Sleep · Minutes before alarm** | A numeric sensor, Number or Input Number helper containing a nonnegative number of minutes |

For example, an alarm at **07:00** and a minutes value of **30** make HEM leave
automatic Sleep at **06:30**. Devices then use their normal automatic targets
and sleep-related pauses or quiet limits are released. Other quiet settings
still apply. This gives the room time
to warm, cool or adjust humidity before waking. It does not guarantee that a
target will be reached by the alarm; that depends on the room and equipment.

Use **0** to leave Sleep when the alarm rings. A time-only source repeats in
Home Assistant's configured local timezone; a dated timestamp identifies a
specific alarm. The minutes source can have a minutes unit or no unit. Select
neither input to disable the feature.

Changes to the alarm or lead time are applied immediately. Once an alarm has
rung, a phone clearing it or publishing tomorrow's alarm will not put devices
back to Sleep during the same sleep episode. The episode ends when its room or
household sleep condition ends. A reload preserves an already-triggered wake
episode. Missing or invalid alarm inputs cannot start a new wake transition.

This feature releases **automatic** Sleep. An explicitly selected Sleep preset,
Manual control, Away behavior, window checks and device protection delays keep
their normal priority.

### Keep selected devices off when everybody is sleeping

Each HEM device controller has **Sleep · Keep device off when all asleep**,
disabled by default. Enable it for a device that should stop while everybody
is sleeping, such as a living-room purifier while occupants sleep in bedrooms.

HEM applies this option when **at least one room is occupied and every occupied
room is also in the shared sleeping-room list**. It checks occupied rooms
throughout Home Assistant, including rooms without HEM equipment. An empty
occupied-room list does not mean everybody is sleeping, and an occupied room
outside the sleeping-room list ends household Sleep.

This option applies separately to each device in **Automatic** or **PID**
control. It requests OFF even if that device's separate room sleep behavior is
Normal or Sleep targets, while retaining minimum ON time, native confirmation,
manual override and device protection checks. It does not mark its own room as
occupied. Unknown evidence and a verified empty home do not prove that everyone
is asleep. Turning the option off, a confirmed awake occupant, or the configured
alarm preparation time releases this household hold. The device's own room
sleep and presence rules still apply, and Manual control retains its authority.

## Optional solar shading

1. Select the eligible blinds, shades or shutters in the room's source settings.
2. Open each cover's HEM controller and select its **associated window contact**.
3. Set the closing-temperature threshold on the cover controller. Review
   **Shading · Minimum sun elevation for shading (°)** on the
   **{Room} Environment** device.
4. If wanted, enable movement announcements or add a lux sensor and minimum lux.
5. Enable **Shading · Automatic solar shade cooling** for the intended cover.

Closing also needs current room temperature, sunlight/elevation, suitable
selected weather and available cover feedback. An open linked window holds
movement. A missing reading on the assigned contact raises a room warning and
allows the other shading conditions to determine whether the cover moves.
Selecting a cover alone does not enable movement. When movement announcements
are enabled, failure to submit the announcement holds the movement.

Low lux alone does not trigger reopening. HEM automatically reopens only covers
whose earlier automatic closure it confirmed and owns. Manual movement holds
further automatic ownership until you explicitly re-enable it.

## Mold indication measurement

Mold indication estimates humidity at the coldest surface using a calibrated
temperature relationship. It does not detect mold growth or spores.

For an authorized Automatic/PID dehumidifier, enabling mold indication makes
the active **Home, Away, Comfort, Eco or Sleep target** a surface-humidity
target. The exact per-device and operating-mode override takes precedence over
the room profile, as it does for ordinary humidity control. HEM converts that
target into the room-air humidity needed under the current temperatures and
calibration. It displays the chosen surface target and measured indication
separately from the derived room-air target and the physical appliance's own
reported setpoint.

The general mold warning threshold remains an advisory threshold; it does not
replace the active profile target. A profile can therefore request drying
before the warning threshold is crossed. Missing calibration or required fresh
inputs makes the selected mold target unavailable, instead of silently using
the same percentage as a room-air target. Native and room operating limits
still apply, and diagnostics identify a target those limits cannot reach.
Humidifying devices retain their room-air targets and existing mold protection.

Mold-based control requires selected indoor temperature and humidity reports
no older than **10 minutes**, or the configured maximum age if that is shorter.
Outdoor weather follows its configured maximum age. The monitoring display can
retain an estimate under its longer monitoring age; that displayed number alone
does not authorize a device command without current control inputs.

1. Enable **Use mold indication instead of raw room RH** in General settings.
2. Select room temperature and humidity sensors, plus weather sources providing
   usable outdoor temperature.
3. Open the card's **Mold indication measurement** explanation and the room's
   **Room controls** / **{Room} Environment** device.
4. Choose settled conditions with the room **at least 10°C warmer than outdoors**
   for a useful cold-surface measurement. Check that heating, ventilation and
   direct sun have not just changed the surface conditions.
5. Measure the coldest relevant surface with a thermometer. Enter
   **Mold · Measured coldest surface temperature (°C)**.
6. Press **Mold · Recalculate calibration factor** while the indoor, outdoor and
   surface readings represent the same conditions.

The panel colours the temperature readings **green** when the recommended
temperature contrast is met, **red** when it is too small or outdoors is not
colder, and neutral when readings are missing. Green confirms temperature
contrast; you still need to check that conditions are stable.

The recalculation button saves the factor from the surface measurement and
current selected room/weather temperatures. Recalculate after changing the
surface measurement. For background, see Home Assistant's
[mold-indicator calibration guide](https://www.home-assistant.io/integrations/mold_indicator/#calibration).

## Announcements

Configure delivery in **General settings**, then enable
**Announcement · Automatic notifications** and/or
**Announcement · Automatic speech** on the Home device.

- With **Announcement Hub**, enable **Announcement · Use Announcement Hub**
  and configure recipients and destinations in that integration.
- For direct delivery, select notification entities and/or a TTS engine with
  media players. Check their Home Assistant area assignments for room targeting.
- Set the announcement repeat interval as needed. **0** disables repeats while
  allowing the initial announcement.
- For optional AI wording, choose the agent in General settings, then enable
  **Announcement · AI wording** on the Home device. AI rewrites the wording;
  it does not decide climate control or ventilation rules.

A running Hub handles its own routing and rejected jobs. HEM uses configured
direct fallback when Hub is disabled or unavailable.

To explicitly announce current actionable recommendations, open
**Developer tools → Actions** and run:

```yaml
action: environment_manager.announce
data:
  channels: both
```

Use `tts` or `notification` to limit the channel. Optional `areas` contains Home
Assistant area IDs. This action announces current recommendations; it does not
send arbitrary text, and there may be nothing to announce when no action is
recommended.

## History storage and removing HEM

Individual sensor charts read Home Assistant's recorded history. Their coverage
depends on Recorder exclusions and retention. Room averages and derived mold
charts use HEM's own bounded local history, saved through Home Assistant's
storage helper and restored after restart. Average history retains up to seven
days and 672 observations per room/metric, shared across its exact contributor
groups. Environmental snapshots retain up to eight days and 2,600 observations
per room; mold charts show the latest seven days. The normal sampling intervals
are 15 minutes for averages and five minutes for environmental snapshots,
with relevant transitions recorded separately. **All** means all retained
observations, not an unlimited archive.

The detailed charts read the stored observations, not the sparse overview
preview. They cannot recover periods that were never recorded, have expired,
or were already discarded. Mold history is the estimate computed at the time;
it is not recalculated retrospectively using a new calibration factor.

Controller target and output history starts with v0.7.5b2. It shares the local
environment-history journal and retains up to seven days within fixed point
and controller limits; frequent changes or many controllers can shorten that
window. Target, profile and output changes are recorded from observed control
decisions and device reports. It does not reconstruct earlier settings or use
the current target to fill older history. Restart, source and availability
boundaries stay visible, and values are never extended beyond their observed
interval merely because a chart was opened. Loading control history does not
change the device, its targets or its PID settings.

To remove a configured HEM integration, use **Settings → Devices & services →
Home Environment Manager → Delete**. Permanent removal stops its writers and
deletes the entry's 16 owned storage journals, including history, calibration
and controller recovery state. It also dismisses identifiable owned persistent
notifications. Home Assistant removes that entry's entities, devices and
associated configuration. A reload, restart or disable keeps its saved data.
With multiple HEM entries, removal is scoped to the selected entry.

After the last entry is removed, HEM unregisters its added frontend script for
new page loads. An already open dashboard can retain loaded JavaScript until
refreshed. Per-browser display preferences can remain in browser storage;
server-side removal cannot clear offline browsers. Manually added dashboard
cards, automations and scripts are user
configuration and remain for you to remove or reuse. HEM does not uninstall
its own code: remove the installed package separately through HACS after
deleting the configured integration. Removing the package first prevents its
cleanup hook from running. Old backups and journal files from integrations
deleted before this cleanup was available are not scanned or erased.

Source sensors, physical device integrations and Recorder data are preserved.
Recorder follows its own retention policy; permanent HEM removal does not
purge its database or clear long-term statistics. If you separately intend to
delete recorded entity history, Home Assistant provides explicit Recorder
purge actions. Avoid broad domain or wildcard purges when you only intend to
remove particular entities.

References: [Home Assistant config-entry removal](https://contributors.home-assistant.io/core/integrations/config-entries/#remove-a-config-entry),
[Recorder configuration](https://www.home-assistant.io/integrations/recorder/)
and [entity-specific Recorder purging](https://www.home-assistant.io/actions/recorder.purge_entities/).

## Troubleshooting

| What you see | What to check |
| --- | --- |
| A sensor or device is missing from a room picker | Its HA area assignment, native entity type/device class and units; room names in entity IDs do not assign areas |
| “No window sensors” | Select actual window-contact binary sensors, or explicitly enroll a suitable `door`/`opening` balcony-door contact; shades have a separate source group |
| No opening recommendation | Read the reason, then check indoor demand, weather, outdoor air quality, AQI scale and ventilation limits |
| Missing readings or history gaps | Check live source values, freshness and recorded samples; new history needs time to collect |
| A selected appliance is not operating | Check Control · Method, current authorization, feedback, window/presence rules and minimum ON/OFF timing |
| PID keeps waiting while the room is below its heating target | Check the controller's effective PID target and measurement, demand percentage, remaining minimum OFF time and next PWM window; the room overview and appliance's own sensor can show different values |
| Control stops after a source change | Check the selected appliance and sensors, then explicitly choose the control method again |
| PID calibration is held | Check method/model inputs, that the physical output is off, and that its reported state has been confirmed |
| Mold controls are absent or uncalibrated | Enable mold indication, allow the reload, provide fresh room/weather readings, measure the surface and recalculate |
| A cover does not move | Check its opt-in, associated closed window, weather/sun, temperature/lux conditions and manual-override status |
| The card is missing after an update | Confirm HEM loaded, restart after installation, refresh the browser, and select the actual Window recommendations sensor |
| Announcements are silent | Check the speech/notification switches, Hub routing or direct destinations, room assignments and whether actionable recommendations exist |
| “Requesting window opening” | A bounded announcement submission is in progress; a failed submission releases the automatic start |
| “Waiting for you to open the window” | The opening request was accepted; the device can resume after the configured timeout if its window stays closed |

For a reproducible problem, open an
[issue](https://github.com/Chreece/HA-Home-Environment-Manager/issues) with the displayed reason, relevant settings, a brief Home Assistant environment description, and
steps to reproduce. Remove personal details from logs and screenshots.
