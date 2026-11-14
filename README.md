<p align="center">
  <img src=".github/assets/hem-banner.svg" alt="Home Environment Manager - smarter air quality, comfort, ventilation and climate control" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src=".github/assets/ko-fi-banner.svg" alt="Support Chreece on Ko-fi" width="500"></a>
</p>

<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <strong>English (default)</strong> · <a href="docs/i18n/README.ar.md">العربية</a> · <a href="docs/i18n/README.bg.md">Български</a> · <a href="docs/i18n/README.bn.md">বাংলা</a> · <a href="docs/i18n/README.cs.md">Čeština</a> · <a href="docs/i18n/README.da.md">Dansk</a> · <a href="docs/i18n/README.de.md">Deutsch</a> · <a href="docs/i18n/README.el.md">Ελληνικά</a> · <a href="docs/i18n/README.es.md">Español</a> · <a href="docs/i18n/README.fa.md">فارسی</a> · <a href="docs/i18n/README.fi.md">Suomi</a> · <a href="docs/i18n/README.fr.md">Français</a> · <a href="docs/i18n/README.he.md">עברית</a> · <a href="docs/i18n/README.hi.md">हिन्दी</a> · <a href="docs/i18n/README.hr.md">Hrvatski</a> · <a href="docs/i18n/README.hu.md">Magyar</a> · <a href="docs/i18n/README.id.md">Bahasa Indonesia</a> · <a href="docs/i18n/README.it.md">Italiano</a> · <a href="docs/i18n/README.ja.md">日本語</a> · <a href="docs/i18n/README.ko.md">한국어</a> · <a href="docs/i18n/README.nb.md">Norsk bokmål</a> · <a href="docs/i18n/README.nl.md">Nederlands</a> · <a href="docs/i18n/README.pl.md">Polski</a> · <a href="docs/i18n/README.pt.md">Português</a> · <a href="docs/i18n/README.pt-BR.md">Português (Brasil)</a> · <a href="docs/i18n/README.ro.md">Română</a> · <a href="docs/i18n/README.ru.md">Русский</a> · <a href="docs/i18n/README.sk.md">Slovenčina</a> · <a href="docs/i18n/README.sr.md">Српски</a> · <a href="docs/i18n/README.sv.md">Svenska</a> · <a href="docs/i18n/README.ta.md">தமிழ்</a> · <a href="docs/i18n/README.th.md">ไทย</a> · <a href="docs/i18n/README.tr.md">Türkçe</a> · <a href="docs/i18n/README.uk.md">Українська</a> · <a href="docs/i18n/README.ur.md">اردو</a> · <a href="docs/i18n/README.vi.md">Tiếng Việt</a> · <a href="docs/i18n/README.zh-Hans.md">简体中文</a> · <a href="docs/i18n/README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Home Environment Manager

<p align="center">
  <img src=".github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Your whole home's environment, in one Home Assistant card.</strong></p>

**HEM helps your home understand its surroundings and react to what each room actually needs.** It brings your Home Assistant sensors, weather data, occupancy information and compatible climate devices together so you can monitor air quality, receive useful ventilation advice, manage comfort and automate the equipment you choose.

For example, HEM can reduce heating while everybody is away, prepare selected rooms before you return, use a different humidity target while you sleep, or ask you to open a window before running a dehumidifier. It can also just **monitor and recommend**, without controlling any device.

**You stay in charge.** Every room has its own settings. Each supported appliance has its own controller, operating modes, targets and safety limits. HEM never assumes that selecting a device gives it permission to operate that device.

[Explore the features](#what-can-hem-do) · [See the interface](#see-hem-in-action) · [Install HEM](#installation) · [Set up your home](#getting-started) · [Detailed guide](docs/advanced-configuration.md)

## What can HEM do?

| Your situation | How HEM can help |
| --- | --- |
| **The house is empty** | Switch to Away targets, respect each room's presence rules and avoid running selected equipment unnecessarily. |
| **You're on your way home** | Press **Prepare for arrival** to temporarily use Home comfort targets for eligible automatic controllers, even though everyone is still away. |
| **Someone is sleeping** | Use Sleep targets, reduce fan noise, or keep chosen devices off while every occupied room is sleeping. |
| **One room is humid** | Compare its humidity and mold indication with targets, suggest useful airing, or operate an authorized dehumidifier using Automatic or PID control. |
| **It's hot and sunny** | Evaluate room temperature, sunlight, weather and connected window contacts before moving opted-in shades. |
| **The outdoor air looks better** | Recommend ventilation using indoor demand, outdoor pollution, temperature, humidity, wind and available pollen or weather warnings. |
| **A heater or TRV stops responding** | Show its unavailable or waiting state, retain its configured controller and report supported device faults without assuming a battery or relay has recovered. |

These are examples, not actions that HEM forces on every home. The results depend on your selected sensors, each device's actual Home Assistant capabilities and your opt-in settings.

## Explore the features

### A complete home dashboard

The HEM card gives you a useful overview without opening several integrations.

- See outdoor conditions, air quality and whether ventilation is advisable.
- Compare all monitored rooms at a glance: temperature, relative humidity, AQI, PM2.5, mold indication, light and other supported readings.
- Expand any room for detailed measurements, window and door information, climate status, active controllers, reasons for waiting and building-physics estimates.
- View histories and trends, see which sensors contributed to an average and distinguish missing readings from measured values.
- Group rooms by actual Home Assistant floors, or use a simple room list when you have no floors.

### Different settings for the home, each room and each device

HEM keeps shared policies separate from local decisions.

| Settings level | What you can configure |
| --- | --- |
| **Home** | Outdoor weather and pollution sources, monitored rooms, global ventilation limits, household presence, arrival preparation and announcement delivery. |
| **Room** | Indoor temperature and humidity sources, air-quality thresholds, window and door contacts, sleep and occupancy behavior, room-specific comfort targets, ventilation and shading choices. |
| **Individual device** | Its available control modes, Automatic/Manual/PID method, per-profile targets, sensors, quiet fan settings, minimum operating times, power protections, window behavior and device-error notifications. |

All three levels are accessible through grouped, searchable settings in the card. Advanced controls are available when needed, without crowding everyday settings. You can refresh source choices as your Home Assistant setup changes.

### Climate control and PID, device by device

HEM can work with compatible Home Assistant **climate**, **humidifier** and **fan** devices, including heating, cooling, dehumidifying, humidifying and supported air-circulation or air-cleaning equipment.

For each **supported physical operating mode**, choose the control method independently:

| Method | What it means |
| --- | --- |
| **Existing** | Leave operation with the existing controller path. |
| **Automatic** | Follow HEM's measured demand, situation-based targets and permissions. |
| **PID** | Use feedback-based proportional, integral and derivative control where the device and measurement support it. |
| **Manual** | Control through explicit supported requests and targets. |
| **Off** | Keep that controller off, subject to physical protection and feedback requirements. |

For example, one air conditioner may use **PID for Heating** and **Automatic for Cooling**. A dehumidifier can have its own PID calibration, targets and cycle timing. Eligible fans can use PID when suitable feedback and purpose-specific control are available.

PID is **not** a universal override: HEM only offers the methods a particular device, operating mode and feedback source can support. Advanced options include per-mode tuning and calibration, suggested/adaptive adjustments, quiet operation and supported staged fan settings. You approve suggested changes unless you explicitly opt into bounded automatic adaptation.

### Comfortable when you're home, economical when you're away

HEM can choose among **Comfort, Home, Away, Sleep and Eco** targets based on the household situation, room evidence and your explicit selections.

- **Home and Away:** Use different heating, cooling and humidity goals depending on verified home presence.
- **Room presence:** Run an eligible device always when there is demand, only while its room is occupied, or only while the room is empty.
- **Sleep:** Apply overnight targets and quieter fan behavior. A selected device can remain off when all occupied rooms are sleeping.
- **Eco:** Use economical targets where configured. A closed interior door can participate in a guarded Eco policy when the room is verified empty and other conditions are met; a closed door alone does not prove the room is isolated.
- **Wake-up preparation:** Use a configured next-alarm source to leave automatic Sleep before the alarm and give eligible devices time to respond.

If occupancy, device availability or other required evidence is uncertain, HEM does not simply assume it is safe to start an automatic device.

### Prepare your environment before you arrive

**Prepare for arrival** is a timed action for a confirmed Away home. Start it from the card header or HEM's Home device.

HEM temporarily applies the configured **Home targets** to eligible Automatic/PID controllers so rooms can begin warming, cooling or adjusting humidity before you return. This may also temporarily permit a controller normally restricted to occupied rooms, **only when it already has the necessary physical control permission**.

Preparation is not a command to turn everything on. Devices still need genuine demand, valid sensors and authorization, and must respect windows, minimum ON/OFF times and their own protections. The action ends when someone arrives, you cancel it, or the configured timer expires. A Home Assistant restart does not start the full timer over.

### Ventilation advice, windows, doors and shading

HEM compares **what a room needs** with **whether outdoor air can help**.

- Recommend opening or closing windows using current indoor measurements, outdoor humidity, pollution, temperature, wind, weather alerts and optional pollen context.
- Use selected window and door contacts to explain room conditions and avoid treating an unknown contact as closed.
- Optionally ask you to try opening a window before starting a supported automatic appliance, then continue normal control after the configured response wait if needed.
- Use door information for room boundary awareness, ventilation cautions and optional guarded Eco behavior.
- Manage opted-in shutters, blinds and shades using suitable window, temperature, weather, sun-elevation and optional illuminance evidence.

HEM can give ventilation advice without any controllable windows. It does not open a window by itself merely because airing would help.

### Humidity, mold indication and air quality

HEM combines supported readings such as **temperature, humidity, CO₂, particulate matter, VOC, AQI and illuminance** to help you understand each room. Available measurements depend on what your Home Assistant setup provides.

Its **mold indication** estimates moisture conditions at a cold surface from room and outdoor temperatures and a calibration measurement. When properly configured, it can influence a supported automatic humidity controller's effective target.

**Mold indication is an estimate, not a mold or spore detector.** Missing or stale sensor data cannot justify a new mold-based device command.

### Announcements, diagnostics and protection

You can send relevant recommendations and alerts through configured Home Assistant notifications, TTS/media players or **Announcement Hub**, with optional AI wording. AI can change how a message is phrased; HEM's physical control decisions remain deterministic.

HEM also includes device-specific protections and diagnostics:

- Minimum ON and OFF durations, maximum operating-time settings and supported external power-switch handling.
- Window and occupancy restrictions, manual-override handling and native command acknowledgment checks.
- Error and unavailable-device reporting, with a choice of notification behavior for each device.
- An optional post-shutdown watchdog for suspected continued heating after an OFF command, with guarded monitoring and limited recovery attempts.
- Clear waiting reasons, current operating status and source availability, so you can investigate before enabling more control.

**Safety boundaries remain in effect even when an alert is disabled.** HEM never treats a successful command dispatch as proof that an appliance physically responded.

## See HEM in action

These English-language illustrations use sample rooms and measurements. They demonstrate the interface rather than showing live data from a particular house.

### Home at a glance

Get ventilation advice, weather conditions and the status of every monitored room in a single card.

<p align="center">
  <img src="docs/images/hem-dashboard-overview.svg" alt="HEM home dashboard with ventilation advice and environmental readings across five rooms" width="900">
</p>

### Expand a room for full details

Inspect air quality, mold indication, presence, window state, climate controllers and explanations for each decision.

<p align="center">
  <img src="docs/images/hem-room-expanded.svg" alt="Expanded bathroom dashboard with readings and independent device controllers" width="760">
</p>

### Home settings

Manage outdoor sources, house-wide presence, monitored rooms, ventilation limits, preparation and notifications.

<p align="center">
  <img src="docs/images/hem-home-settings.svg" alt="HEM Home settings with searchable groups and source and room management" width="900">
</p>

### Room settings

Choose what matters to each room: its own sensors, targets, occupancy, doors, windows, ventilation, shading and safeguards.

<p align="center">
  <img src="docs/images/hem-room-settings.svg" alt="Grouped HEM room settings for sensors, device controls, sleep, windows and protection" width="760">
</p>

### Device settings

Fine-tune one device without changing the others, including supported control methods, PID, quiet operation, timing and fault reporting.

<p align="center">
  <img src="docs/images/hem-device-settings.svg" alt="Grouped HEM device settings with control, PID, power protection and notifications" width="900">
</p>

## Getting started

1. **Organize your rooms.** In Home Assistant, create or check your Areas and assign the appropriate sensors and devices to each one.
2. **Choose what to monitor.** Add HEM, select the rooms you care about and review the suggested temperature, humidity, window, air-quality and device sources. You can leave unused groups empty.
3. **Configure shared information.** Select available outdoor weather/air-quality sources, household occupancy evidence and any announcement destinations you want.
4. **Add the card.** Open a dashboard in edit mode and add the **Home Environment Manager** card. Start with room monitoring, readings and ventilation advice.
5. **Enable control only where useful.** Open a room, choose a supported appliance, review its controller and explicitly select Automatic or PID for the modes you want HEM to operate.

You do **not** need a smart appliance in every room. Start with the sensors you have, and introduce automatic control one device at a time.

### Add the card manually

The integration normally registers its own Lovelace card. If you prefer YAML, use:

~~~yaml
type: custom:home-environment-manager-card
~~~

If your Home Assistant installation has more than one HEM recommendation sensor, you may need to set the appropriate **entity** explicitly:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

For step-by-step instructions about room sources, profiles, PID settings, window policies, preparation, mold calibration, solar shading and announcement delivery, use the [detailed configuration guide](docs/advanced-configuration.md).

## Installation

### HACS / Home Assistant Community Store

1. Open **HACS** in Home Assistant.
2. Add **https://github.com/Chreece/HA-Home-Environment-Manager** as a **custom repository** in the **Integration** category if it is not already listed.
3. Find **Home Environment Manager** and install it.
4. Restart **Home Assistant** to load the integration.
5. Go to **Settings → Devices & services → Add integration**, search for **Home Environment Manager** and complete the setup.

### Manual installation

Copy the repository's **custom_components/environment_manager** folder into the matching **custom_components** directory in your Home Assistant configuration, keeping the directory name **environment_manager**. Restart Home Assistant and add the integration through **Settings → Devices & services**.

For subsequent installation changes, keep your existing HEM integration entry and settings. Reload the dashboard in your browser if the card's appearance does not refresh immediately.

## Common questions

**Can I use HEM without giving it control of my devices?**

Yes. Monitoring, measurements, ventilation advice, history and many environmental indications work without enabling device actuation.

**Will HEM automatically control every device it discovers?**

No. You select the physical devices you want to manage and explicitly choose the control method for supported modes. Sensor eligibility and native device capabilities still determine what is possible.

**Does every appliance support PID?**

No. HEM supports PID for **eligible** heating, cooling, humidity or fan-control paths when the appliance and selected measurements provide the necessary capabilities and feedback. Unsupported modes are not given artificial PID control.

**Can I give each room different rules?**

Yes. Occupancy conditions, sleep behavior, sources, targets and some safety preferences can differ by room, while each physical device has its own operating and protection settings.

**Can HEM prepare my home while I'm away?**

Yes. **Prepare for arrival** temporarily lets eligible, already-authorized automatic controllers use Home targets for a bounded period. It does not bypass physical protections or guarantee a target will be reached.

**Does a “good for ventilation” recommendation open my windows?**

No. It explains when airing may help. Automatic movement is a separate, opt-in feature for eligible supported shades or covers, subject to their own safety checks.

**What if a sensor or a device becomes unavailable?**

HEM distinguishes unknown data from real readings, retains configured controller information where possible and exposes waiting reasons and diagnostics. Automatic control still requires valid current authority and evidence.

## Help and troubleshooting

If something seems wrong, check the relevant room or controller's **Reason**, **Diagnostics**, source availability and current control method. The [detailed configuration guide](docs/advanced-configuration.md) covers common waiting states, presence policies, PID eligibility, windows and device-response troubleshooting.

For a reproducible problem, [open a GitHub issue](https://github.com/Chreece/HA-Home-Environment-Manager/issues) with the expected behavior, actual behavior, relevant room/device settings and steps to reproduce. Remove private information from logs and images.

Contributions and improvements are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Support and license

If HEM is useful to you, you can [support Chreece on Ko-fi](https://ko-fi.com/chreece).

Distributed under the [MIT license](LICENSE).
