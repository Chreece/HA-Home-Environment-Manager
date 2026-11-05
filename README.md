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

**Current release:** [v0.6.0b118](https://github.com/Chreece/HA-Home-Environment-Manager/releases/tag/v0.6.0b118)
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
- Configure solar shading, mold indication and spoken or written announcements.

You can start with monitoring and advice. Selecting an appliance during setup
creates its controls; choose its control method when you want HEM to operate it.

## Installation

### HACS

1. In HACS, add `https://github.com/Chreece/HA-Home-Environment-Manager` as a
   **custom repository**, with category **Integration**.
2. Open **Home Environment Manager**, enable **Show beta versions** in version
   selection, and download **v0.6.0b118**.
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
  your configured Announcement Hub. Choose the language and optional AI agent here too.
- **Mold indication and ventilation limits:** enable mold indication if you will
  calibrate it, and review the outdoor temperature, humidity, wind and pollution limits.

After saving, review **Ventilation · AQI scale** on the HEM Home device for each
AQI source. Select the provider's actual scale, or configure a custom scale and
limit. A number without a known scale cannot be compared meaningfully.

The maximum wind-speed setting limits when HEM can recommend opening windows.
The other ventilation limits serve the same purpose for their conditions; they
are separate from a room's heating or cooling targets. Open each setting's help
for its purpose, units and effect.

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
  measurements and device controllers.
- Open information and warning details to understand missing inputs or the
  reason for a recommendation.
- Use a room's settings gear to edit its selected sources. **Room controls**
  opens the room's Home Assistant device page.
- Open an averaged room reading (**≈**, with multiple contributing sensors) for
  HEM's trend view and choose **6 h**, **24 h**, **7 d** or **All**. Inspect points
  with the pointer, touch/drag or keyboard; gaps represent missing readings.
  Single-source badges open the sensor's native Home Assistant details/history.
- For a waiting controller, read its **Reason** and **Diagnostics** before
  changing settings.

Opening advice needs usable weather and configured outdoor air-quality data.
Active weather warnings, confirmed outdoor pollution and unsuitable conditions
can block it. Missing or stale readings appear as incomplete data; check the
displayed reason to see what is affecting the decision.

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
changes. Removing a monitored room revokes its automatic controls; changing a
device or its feedback sources can require choosing its control method again.

## Enable device control

1. Select the appliance in the room's **Devices** group and save.
2. Open its HEM controller through **Device controllers** in the card or the
   integration's device list.
3. Review its feedback sensors, targets, presence/sleep behavior and supported
   limits. For fans, check the intended purpose and minimum/maximum speed.
4. Choose **Control · Method**.

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

A manual change on the appliance can pause automatic control. Use
**Control · Continue Automatic** when you want HEM to resume. Window state,
availability, presence policies and minimum ON/OFF times still apply; the reason
display explains ordinary waiting periods.

### Targets and profiles

Review heating, cooling and humidity targets for **Comfort**, **Home**, **Away**,
**Sleep** and **Eco**. Presence, sleep context and an explicit preset influence
the active profile.

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

First select **PID** under **Control · Method** on that appliance's controller.

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

## Presence and sleep

### Home Occupancy

In **General settings**, select direct home sources under
**Home · Occupancy · Devices**. A fresh positive source means someone is home.
When all configured direct sources are freshly away/off/zero, home presence
becomes Away and overrides room activity. Automatic profile selection uses Away
unless an explicit preset is selected. Unknown or unavailable evidence does not
prove that everybody is away.

Without direct home sources, HEM can derive home presence from room evidence.
The Home occupancy away-delay setting applies to that room-derived absence.
It is separate from the announcement repeat interval, even when both show
10 minutes.

### Room presence and shared lists

Select local presence sensors on each room's source page, or configure a shared
occupied-rooms source in General settings. For a shared list, select **State**
or the attribute containing the list. For example:

```json
["living_room", "bedroom"]
```

Use your actual Home Assistant area IDs, names or unambiguous aliases. A valid
list takes priority over local room sensors: listed rooms are occupied and
omitted rooms are unoccupied. `[]` or a fresh empty state means no rooms are
occupied. Missing/stale evidence can fall back to local sensors; malformed lists
or unknown room names remain unknown. Verified whole-home Away takes precedence.

### What the room sleep settings do

| Setting | Purpose |
| --- | --- |
| **Sleep · Sleeping now** | Marks the room as currently sleeping for climate sleep behavior |
| **Sleep · Use schedule** | Enables the local-time sleep interval; the default is **22:00–07:00** |
| **Shared sleeping-room list** | Supplies current sleep context from your selected entity/list |
| **Noise · Room used for sleeping** | Classifies the room for calibrated nighttime noise assessment |

Sleep context can select sleep targets or a device's configured sleep/quiet
behavior. Turning **Sleeping now** off does not override an active schedule or
shared sleeping-room list. The noise classification does not activate climate
Sleep.

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
| Control stops after a source change | Check the selected appliance and sensors, then explicitly choose the control method again |
| PID calibration is held | Check method/model inputs, that the physical output is off, and that its reported state has been confirmed |
| Mold controls are absent or uncalibrated | Enable mold indication, allow the reload, provide fresh room/weather readings, measure the surface and recalculate |
| A cover does not move | Check its opt-in, associated closed window, weather/sun, temperature/lux conditions and manual-override status |
| The card is missing after an update | Confirm HEM loaded, restart after installation, refresh the browser, and select the actual Window recommendations sensor |
| Announcements are silent | Check the speech/notification switches, Hub routing or direct destinations, room assignments and whether actionable recommendations exist |

For a reproducible problem, open an
[issue](https://github.com/Chreece/HA-Home-Environment-Manager/issues) with your
HEM and Home Assistant versions, the displayed reason, relevant settings and
steps to reproduce. Remove personal details from logs and screenshots.

## Releases and development

Install published betas from the
[Releases page](https://github.com/Chreece/HA-Home-Environment-Manager/releases).
Read the [current release notes](.github/releases/v0.6.0b118.md) for recent changes.

| Branch | Purpose |
| --- | --- |
| `main` | Latest working, validated integration |
| `dev` | Development and testing before promotion to `main` |

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development and release workflow.
The [validation workflow](https://github.com/Chreece/HA-Home-Environment-Manager/actions/workflows/validate.yml)
checks the integration, existing regressions, browser interactions and installation
ZIP before promotion. New beta versions are published after their `main` commit
passes validation; already published versions are never overwritten.

## Support and license

If HEM is useful to you, you can
[support Chreece on Ko-fi](https://ko-fi.com/chreece).

Released under the [MIT license](LICENSE).
