<p align="center">
  <img src=".github/assets/hem-banner.svg" alt="Home Environment Manager — air quality, comfort, ventilation and climate control" width="1200">
</p>
<p align="center">
  <a href="https://ko-fi.com/chreece">
    <img src=".github/assets/ko-fi-banner.svg" alt="Support Chreece on Ko-fi" width="500">
  </a>
</p>

# Home Environment Manager

**Understand each room. Know when to ventilate. Control the devices you choose.**

Home Environment Manager (HEM) is a Home Assistant custom integration that brings
room conditions, outdoor air quality, ventilation advice, moisture and optional
climate control into one dashboard. It uses the sensors and appliances already
connected to Home Assistant.

**Current release:** [v0.6.1b7](https://github.com/Chreece/HA-Home-Environment-Manager/releases/tag/v0.6.1b7)
· **Requires:** Home Assistant 2026.10.0 or newer
· **Status:** Beta

[Install](#installation) · [First setup](#first-setup) ·
[Dashboard](#add-the-dashboard-card) · [Device control](#enable-device-control) ·
[Presence and sleep](#presence-and-sleep) · [Mold](#mold-indication-measurement) ·
[Troubleshooting](#troubleshooting)

## What you can do

- View temperature, humidity and supported air-quality readings room by room.
- Get window-opening and closing advice using indoor demand, outdoor pollution,
  weather, window contacts and optional pollen inputs.
- Follow measurement history and see why a room or controller needs attention.
- Enable automatic or PID control individually for supported climate devices,
  humidifiers and fans.
- Use home occupancy, room presence and sleep context to select operating targets.
- Prepare your home before arrival with a timed Home-target override while away.
- Configure solar shading, mold indication and spoken or written announcements.

You can start with monitoring and advice. Selecting an appliance during setup
creates its controls; choose its control method when you want HEM to operate it.

## Installation

### HACS

1. In HACS, add `https://github.com/Chreece/HA-Home-Environment-Manager` as a
   **custom repository**, with category **Integration**.
2. Open **Home Environment Manager**, enable **Show beta versions** in version
   selection, and download the **current release shown above**.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**, then choose
   **Home Environment Manager**.

For updates, download the new published version, restart Home Assistant, and
refresh the dashboard to load the bundled card. Keep your existing integration
entry and use **Configure** to edit it.

### Manual installation

Download the **Manual installation ZIP** from the
[Releases page](https://github.com/Chreece/HA-Home-Environment-Manager/releases).
Extract its `custom_components/environment_manager` directory into Home
Assistant's configuration directory, restart, then add the integration as above.

The release ZIP already includes the correct installation path. The repository
itself uses a flat layout for HACS. The integration domain is
`environment_manager`.

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
| **Windows** | Actual window-contact binary sensors with the `window` device class |
| **Air quality and environmental sensors** | Supported pollutant sensors and optional environmental readings, such as illuminance |
| **Temperature** | Room temperature measurements |
| **Humidity** | Room relative-humidity measurements |
| **Devices** | Native `climate.*`, `humidifier.*` and `fan.*` appliances |
| **Window blinds, shades and shutters** | Supported `cover.*` shading devices |

Leave unused groups empty. Saved empty selections stay empty. A blind or shutter
belongs in the shading group; window-state inputs come from window contacts.

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
AQI source. Select the provider's actual scale, or configure a custom scale and
limit. A number without a known scale cannot be compared meaningfully.

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
and accepts **0–30 minutes**. These appear beside the device's control settings
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
`custom:air-quality-advisor-card` type remains supported.

### Using the card

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
- Average history keeps separate records for each exact group of contributing
  sensors. Temporary startup outages do not replace the original group's
  samples. A returning group resumes its history with a visible gap.
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
While demand and authority remain valid, HEM retries the requested native
command every **60 seconds**. After **three unsuccessful dispatch attempts** it
announces that the device is not responding to HEM, while continuing to retry.
Unavailable checks do not count as dispatch attempts. Device availability,
window policy and minimum operating times still constrain each attempt.

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
operation becomes eligible again, HEM calculates a fresh cycle. Normal PWM
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

When Automatic/PID has permission to control native ON/OFF operation, HEM uses
the appliance's reported target maximum during heating or humidifying and its
reported minimum during cooling or drying. This keeps the appliance's internal
thermostat or humidistat from ending HEM's requested ON period early when its
local sensor differs from the selected room sensor. The room target still
controls when HEM requests OFF, with the configured operating minimums and
confirmed feedback. Devices authorized only for setpoint changes keep their
bounded target adjustments; Dry modes without a native humidity setter use
their supported mode control.

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

### Minimum device ON and OFF times

Each controller has **Operation · Minimum device ON time (s)** and
**Operation · Minimum device OFF time (s)**. These govern how long HEM keeps
the device operating or stopped before requesting the opposite state. For a
radiator valve, this is its controlled heating operation.

Both settings accept **0 seconds**, which disables that forced operating
hold, and can be adjusted in one-second increments. Choose any required
minimum interval from the appliance manufacturer's guidance; compressor
equipment and radiator valves need different operating policies. Aqara's
[E1 guidance](https://www.aqara.com/eu/product/radiator-thermostat-e1/faq/)
also notes that frequent on/off cycling increases valve motor use and battery
consumption.

Updating HEM preserves existing effective timings until you explicitly edit
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
target. The card and native configuration numbers retain the requested value;
the controller also reports an effective humidity target when calibrated mold
protection needs a lower value.

| Profile | Default humidity target when no target is saved |
| --- | --- |
| Comfort, Home, Away, Sleep | **65%** |
| Eco | **70%** |

Your saved targets remain in effect. These are HEM's starting control values;
adjust them to your room and supported appliance range.

Advanced ISO 7730 comfort inputs are optional. Ordinary temperature/humidity
control does not require them. **Timed setpoints (30 s)** is also optional and
off by default; consult its device help before enabling it.

### Optional PID calibration

First select **PID** in the relevant operating-mode panel on the appliance's
controller, then open that mode's **Parameters**.

For a first adaptive setup, **PID · Calibration → Adaptive · Suggest & approve**
learns from normal operation. Review the proposed gains and confidence, then
choose **Approve** or **Discard**. If approval is held, the proposal remains
pending. Resolve the displayed condition and press **Approve** again.
**Adaptive · Automatic (max 10%/day)** is a separate opt-in mode that applies
bounded adjustments automatically.

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

Set **Arrival preparation timeout (min)** on the Home Environment device, or
open that setting from the duration control in the card. The default is
**60 minutes**; the allowed range is **1–1440 minutes**. Changing the setting
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
| **Sleep · Use schedule** | Enables the local-time sleep interval; the default is **22:00–07:00** |
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

### Let other devices sleep when everybody is sleeping

Each HEM device controller has **Sleep · When everyone is sleeping**, disabled
by default. Enable it for devices that should follow household sleep, such as
a living-room purifier while everybody is sleeping in bedrooms.

HEM applies this option when **at least one room is occupied and every occupied
room is also in the shared sleeping-room list**. It checks occupied rooms
throughout Home Assistant, including rooms without HEM equipment. An empty
occupied-room list does not mean everybody is sleeping, and an occupied room
outside the sleeping-room list ends household Sleep.

This option applies separately to each device in **Automatic** or **PID**
control. The device follows its configured Sleep behavior, targets and quiet
settings. The alarm wake-up feature releases this inherited Sleep too.

## Optional solar shading

1. Select the eligible blinds, shades or shutters in the room's source settings.
2. Open each cover's HEM controller and select its **associated window contact**.
3. Set the closing-temperature threshold on the cover controller. Review
   **Shading · Minimum sun elevation for shading (°)** on the
   **{Room} Environment** device.
4. If wanted, enable movement announcements or add a lux sensor and minimum lux.
5. Enable **Shading · Automatic solar shade cooling** for the intended cover.

Closing also needs current room temperature, a known closed linked window,
sunlight/elevation, suitable selected weather and available cover feedback.
Selecting a cover alone does not enable movement. When movement announcements
are enabled, failure to submit the announcement holds the movement.

Low lux alone does not trigger reopening. HEM automatically reopens only covers
whose earlier automatic closure it confirmed and owns. Manual movement holds
further automatic ownership until you explicitly re-enable it.

## Mold indication measurement

Mold indication estimates humidity at the coldest surface using a calibrated
temperature relationship. It does not detect mold growth or spores.

For an authorized Automatic/PID humidity controller, valid calibration also
sets the upper room-humidity target needed to respect the configured surface
humidity limit. A room can therefore need dehumidification even when its room
humidity is below its usual comfort target. HEM derives this target from the
same current temperatures and calibration as the indication, keeps your saved
comfort target, and reports both values. Missing or stale evidence does not
create mold-based device demand. Native and room minimum limits still apply;
diagnostics identify a mold target that those limits cannot reach.

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

## Troubleshooting

| What you see | What to check |
| --- | --- |
| A sensor or device is missing from a room picker | Its HA area assignment, native entity type/device class and units; room names in entity IDs do not assign areas |
| “No window sensors” | Select actual window-contact binary sensors; shades have a separate source group |
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
[issue](https://github.com/Chreece/HA-Home-Environment-Manager/issues) with your
HEM and Home Assistant versions, the displayed reason, relevant settings and
steps to reproduce. Remove personal details from logs and screenshots.

## Releases and development

Install published betas from the
[Releases page](https://github.com/Chreece/HA-Home-Environment-Manager/releases).
Read the [current release notes](.github/releases/v0.6.1b7.md) for recent changes.

| Branch | Purpose |
| --- | --- |
| `main` | Latest working, validated integration |
| `dev` | Development and testing before promotion to `main` |

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development and release workflow.
The [validation workflow](https://github.com/Chreece/HA-Home-Environment-Manager/actions/workflows/validate.yml)
checks the integration, existing regressions, browser interactions and installation
ZIP before promotion. New beta versions are published after their `main` commit
passes validation; already published versions are never overwritten.
Publishing a new version retains all existing releases, assets and tags.

## Support and license

If HEM is useful to you, you can
[support Chreece on Ko-fi](https://ko-fi.com/chreece).

Released under the [MIT license](LICENSE).
