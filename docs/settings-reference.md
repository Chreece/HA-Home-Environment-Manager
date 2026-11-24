# HEM settings reference

Open the gear in the card header for home settings or the gear beside a room name for its settings. Expand a device controller for its controls. Basic, Advanced and Expert are cumulative display levels. The registered appliance, selected sources and control permissions determine which items are available.

[Home options](#home-options) · [Room sources](#room-sources) · [Native controls](#native-controls) · [Setup and options fields](#setup-and-options-fields) · [Configuration guide](advanced-configuration.md)

## Home options

| Setting | Level | What it controls |
| --- | --- | --- |
| Weather entities | Basic | At least one weather provider. Rain, storms and extreme wind/temperature block opening. Mold indication uses the current temperature attribute (°C/°F) of a selected weather entity for outdoor temperature. Choose a source that reports temperature. |
| Outdoor air-quality sensors | Basic | Choose genuine outdoor sensors. Available readings above limits block opening; unknown, unavailable or stale readings are reported, not classified as unsafe. |
| Weather warning sensors (optional) | Basic | Optional Home Assistant warning entities. An explicitly active warning adds an outdoor-air caution and blocks automatic window-opening advice. Unavailable or unknown warnings are reported as missing evidence, not treated as active warnings; separate weather, pollution and equipment safety checks still apply. Select verified warning entities rather than ordinary weather conditions. |
| Room · Occupancy · sensor | Basic | A valid occupied-room list in the selected state or attribute has priority: listed rooms are occupied and omitted rooms are empty. When no list is configured, or its source is unavailable, selected room sensors supply fallback evidence. Any ON means occupied; all OFF, or no selected sensors and no configured list, means empty. Numeric counts use 0 for empty and a positive value for occupied. Malformed lists, unknown room names and unavailable or restored selected sources can remain unknown. Unchanged lists and binary room states do not expire overnight. |
| Home · Occupancy · Devices | Basic | Select actual person/device tracker entities for home/away evidence. Unknown trackers do not prove everyone has left. Numbers and input_number helpers can be chosen as presence counts. A finite 0 means empty; a positive value means occupied. Unknown, stale or unavailable never means empty. |
| Occupancy · Room · source (state) | Basic | Select an entity whose state or chosen attribute lists Home Assistant area IDs or names, such as ["living_room"]. A valid list has priority over room sensors: included rooms are occupied, omitted rooms are empty, and [] means all rooms are empty. An unchanged list stays valid overnight. Missing or invalid data is not an empty list. |
| Occupancy · Room · source (attribute) | Basic | Choose State when the entity state itself is a valid room list, or select an actual attribute that contains that list. Choices refresh when changing entity. |
| Sleep · Room · source (state) | Basic | Select an entity listing sleeping rooms by Home Assistant area ID or name, in its state or a chosen attribute. A listed room counts as asleep only while it is also occupied. The list remains valid while unchanged; a missing or invalid source is unknown. Manual Sleeping now and an enabled room schedule are separate sleep inputs. A configured wake alarm can end automatic Sleep before ringing. |
| Sleep · Room · source (attribute) | Basic | Choose the State field or a verified room-list attribute from the selected sleep entity. A missing or unrecognized list makes sleep state unknown. |
| Direct notification entities | Basic | Direct outputs when Announcement Hub is not used. |
| Direct TTS media players | Basic | Direct audio destinations; room assignment controls targeting. |
| Direct TTS engine | Basic | Direct speech provider when Announcement Hub is not used. |
| AI · Select · source | Advanced | Choose Home Assistant default, a conversation agent, or a data-capable Task AI entity. Task AI selections use ai_task.generate_data. |
| Announcement language | Basic | Use the Home Assistant language by default, or choose any announcement language supported by HEM. |
| Use mold indication instead of raw room RH | Basic | When enabled, humidity recommendations use the estimated relative humidity at each room's coldest surface instead of raw RH. Calibrate each room under the Room settings menu; an uncalibrated room remains unknown rather than safe. |
| Pollen · source · Select | Basic | Select existing numeric pollen-index sensors for your location, even when their entity IDs do not contain 'pollen'. HEM interprets each current value using the provider's maximum scale and the high-pollen threshold. With Avoid ventilation with high pollen enabled, a valid high reading becomes an outdoor-air caution and prevents automatic outside-air use; it never closes doors or windows. For a 0–5 provider, set maximum 5 and high threshold 3. Leave this list empty to disable this input. Missing/stale values are unavailable, not proof of clean air; do not mix incompatible provider scales. |
| Announcement · Use Announcement Hub | Basic | Routes HEM announcements through the configured Announcement Hub integration. Configure the hub and its destinations separately. This switch chooses the delivery route; automatic notification and speech switches still govern automatic announcements. |
| Home · Away · cooldown (min) | Basic | After a fresh occupied-room source becomes empty, wait this many minutes before applying Away. Unknown or stale occupancy never starts Away. |
| Alert when windows remain open after everyone leaves | Basic | Off by default. Notify immediately when the selected presence entities all confirm zero people or away. Numeric number/input_number/person-count sensors use 0 for empty and a positive count for occupied; invalid values never prove absence. List actual open windows. No announcement at startup while already away. Report once per departure and again only for newly opened windows. |
| People to notify after leaving | Basic | Select exactly which Home Assistant person.* identities receive this message. Each person must have the selected phone/watch/tablet destination configured in Announcement Hub. Missing destinations are never replaced by room-wide broadcasts. |
| Delivery channels for open-window alerts | Basic | Choose multiple phone, watch, tablet or other device delivery modes. Notification is written push; TTS uses Companion App speech only. Each selected channel routes to its exact person's assigned output, even while away, not to room speakers. |
| Maximum outdoor AQI | Advanced | Outdoor AQI ceiling used for ventilation. Confirm the provider scale with the AQI selector; per-source custom limits override this general ceiling. Exceeding the applicable limit is an outdoor caution and keeps automatic outside-air use blocked. Useful manual airing may still be suggested conditionally, with the air-quality caution included. The default assumes US AQI. |
| Maximum outdoor CO₂ (ppm) | Advanced | Outdoor CO₂ (ppm) ceiling for window-ventilation checks. A current reading above it is reported as a caution and keeps automatic outside-air use blocked. Useful manual airing may still be suggested conditionally, with detected outside concerns included. This operational screen is not a timed health-exposure standard. |
| Maximum outdoor PM2.5 (µg/m³) | Advanced | Outdoor PM2.5 (µg/m³) ceiling for window-ventilation checks. A current reading above it is reported as a caution and keeps automatic outside-air use blocked. Useful manual airing may still be suggested conditionally, with detected outside concerns included. This operational screen is not a timed health-exposure standard. Instantaneous readings are not a WHO 24-hour mean. |
| Maximum outdoor PM10 (µg/m³) | Advanced | Outdoor PM10 (µg/m³) ceiling for window-ventilation checks. A current reading above it is reported as a caution and keeps automatic outside-air use blocked. Useful manual airing may still be suggested conditionally, with detected outside concerns included. This operational screen is not a timed health-exposure standard. This does not replace time-averaged exposure assessment. |
| Maximum outdoor VOC (µg/m³) | Advanced | Outdoor VOC (µg/m³) ceiling for window-ventilation checks. A current reading above it is reported as a caution and keeps automatic outside-air use blocked. Useful manual airing may still be suggested conditionally, with detected outside concerns included. This operational screen is not a timed health-exposure standard. VOC mixtures and sensor calibration vary. |
| Maximum outdoor VOC (ppb) | Advanced | Outdoor VOC (ppb) ceiling for window-ventilation checks. A current reading above it is reported as a caution and keeps automatic outside-air use blocked. Useful manual airing may still be suggested conditionally, with detected outside concerns included. This operational screen is not a timed health-exposure standard. Conversion between ppb and µg/m³ depends on gas identity. |
| Outdoor NO₂ operational screen (µg/m³) | Advanced | Outdoor NO₂ (µg/m³) ceiling for window-ventilation checks. A current reading above it is reported as a caution and keeps automatic outside-air use blocked. Useful manual airing may still be suggested conditionally, with detected outside concerns included. This operational screen is not a timed health-exposure standard. |
| Outdoor O₃ operational screen (µg/m³) | Advanced | Outdoor O₃ (µg/m³) ceiling for window-ventilation checks. A current reading above it is reported as a caution and keeps automatic outside-air use blocked. Useful manual airing may still be suggested conditionally, with detected outside concerns included. This operational screen is not a timed health-exposure standard. |
| Outdoor SO₂ operational screen (µg/m³) | Advanced | Outdoor SO₂ (µg/m³) ceiling for window-ventilation checks. A current reading above it is reported as a caution and keeps automatic outside-air use blocked. Useful manual airing may still be suggested conditionally, with detected outside concerns included. This operational screen is not a timed health-exposure standard. |
| Indoor AQI triggering ventilation | Advanced | Above this indoor AQI threshold, HEM checks whether airing could help. Any useful manual opening suggestion includes detected outside-air and weather cautions; automatic outside-air protections remain active. Match the sensor’s AQI scale. |
| Indoor CO₂ triggering ventilation (ppm) | Advanced | Indoor CO₂ in ppm used to recommend increased fresh-air ventilation. Elevated CO₂ can indicate insufficient ventilation, but low CO₂ does not guarantee healthy air. |
| Indoor PM2.5 triggering ventilation (µg/m³) | Advanced | Indoor PM2.5 in µg/m³ used to identify particle exposure and consider ventilation when outdoor particles are lower. This instant screen is not the WHO 24-hour mean. |
| Indoor PM10 triggering ventilation (µg/m³) | Advanced | Indoor PM10 in µg/m³ used for air-quality attention and safe ventilation comparison. Higher levels can irritate the respiratory system; avoid outside air if worse. |
| Indoor VOC triggering ventilation (µg/m³) | Advanced | Indoor VOC in µg/m³ used to flag possible sources such as cleaners or furnishings. HEM checks whether manual airing could help and includes detected outdoor cautions in any useful opening suggestion. Automatic outside-air guards remain active; individual VOC sensors are not universal health monitors. |
| Indoor VOC triggering ventilation (ppb) | Advanced | Indoor VOC measurement in ppb. Above the configured value, HEM checks whether manual airing could help and includes detected outdoor cautions in any useful opening suggestion. Automatic outside-air guards remain active. ppb cannot generally be converted to µg/m³ without a reference gas. |
| Indoor humidity triggering ventilation (%) | Advanced | Upper indoor relative humidity (%) for ventilation recommendations. Sustained high humidity may promote condensation and mold; a single reading is not a mold diagnosis. |
| Minimum outdoor temperature (°C) | Basic | Below this outdoor temperature (°C), report cold-air discomfort and heating-loss cautions and keep automatic outside-air use blocked. Useful brief manual airing may still be suggested conditionally with those cautions. This is a ventilation threshold, not a heating setpoint. |
| Maximum outdoor temperature (°C) | Basic | Above this outdoor temperature (°C), report a heat caution and keep automatic outside-air use blocked. Useful manual airing for another verified need may still be suggested conditionally, with the hot outside air disclosed. This does not set the air-conditioner target. |
| Maximum outdoor humidity (%) | Basic | Outdoor relative-humidity ceiling (%) for ventilation checks. Higher values become an outdoor caution and keep automatic outside-air use blocked. Useful manual airing may still be suggested conditionally. Drying benefit compares indoor and outdoor water-vapour content because relative humidity depends on temperature. |
| Maximum wind speed (km/h) | Basic | Window-opening advice is blocked when measured wind speed exceeds this km/h value. It prevents suggesting ventilation during potentially unsafe wind. |
| Maximum age of any outdoor reading (minutes) | Basic | Maximum permitted age of an outdoor sensor report in minutes. Older data are marked stale and are not treated as proof that outdoor air is safe or unsafe. |
| Mold indication triggering ventilation (estimated surface RH, %) | Advanced | Estimated critical-surface relative humidity (%) that triggers moisture/mold-risk ventilation advice. This is a physics-based indication, not detection of mold spores. |
| Pollen scale: threshold treated as high | Expert | Pollen reading at or above which the selected provider counts as high. Use the provider's own scale, from 0 up to the configured maximum; e.g. 3 with a maximum of 5. With Avoid ventilation enabled, valid high readings caution against automatic outdoor-air intake. |
| Pollen provider's maximum scale value | Expert | Positive maximum of the selected provider's pollen index (1–100), not the current reading. For a 0–5 scale enter 5. All selected pollen sources must use compatible index scales; HEM does not convert between providers. A zero or invalid scale cannot classify pollen. |
| Avoid window ventilation when pollen is high (opt in) | Basic | Include verified high pollen among outdoor cautions and keep automatic outside-air use blocked while it persists. Useful manual airing may still be suggested conditionally with the pollen warning. The selected source, high threshold and provider maximum define high pollen; enable when pollen avoidance matters to occupants. |
| Home Occupancy · Maximum tracker/count report age (min) | Basic | Maximum report age for confirming Away from person/device trackers and for sampled numeric counts (default 240 minutes). An unchanged positive Home state on a person/device tracker or an ON whole-home binary sensor remains valid overnight. Room-presence and sleep lists also remain valid while unchanged. Missing, unknown, unavailable and restored sources cannot establish Away. |
| Home Occupancy | Basic | A verified person at home always keeps the home occupied. All home is retained for existing configurations and uses this same rule. Away requires verified absence; an unknown selected tracker cannot prove everyone has left. |
| Sleep · Next alarm | Basic | Select the Home Assistant source reporting the next wake alarm. HEM can end an automatically selected sleep profile before the alarm only when a corresponding minutes-before-alarm source is also configured. Both sources must be selected together; an unavailable source never proves that a wake time was reached. |
| Sleep · Minutes before alarm | Basic | Select the source reporting how many minutes before the next wake alarm HEM should end automatic sleep. This must be paired with the next-alarm source, or both left unselected. An invalid/unknown value does not force a wake transition. |
| Wait for window opening (min) | Basic | Wait after an opening request is accepted before new automatic/PID starts resume if still needed. 0–30 minutes, default 5; 0 disables waiting. Existing open-window and device timing protections still apply. |
| Home occupancy · Validity policy | Basic | Automatic: numeric people counters and negative home-tracker reports are accepted for up to 240 minutes; a valid unchanged Home state can remain Home until it changes. Unknown, restored and unavailable sources cannot prove absence. Custom: use the minute value below for sampled reports. Room-list sources remain change-driven. |
| Environment · Validity policy | Basic | Automatic: weather entities can remain valid for 180 minutes, other numeric environmental measurements for 90 minutes, while valid change-driven binary contacts remain usable without an inactivity timeout. Custom: use the minute value below. Availability and restored-state checks always apply. Home Assistant last_reported advances on a repeated same-value write, not merely because time has passed. |
| Wait before suggesting window closure (min) | Basic | After a window opens following HEM opening advice, wait this many minutes before suggesting that it be closed, even when outside conditions are unsuitable. Applies independently to each room. 0–60 minutes, default 5; 0 disables the delay. Device pause and protection rules remain active. |
| Quiet hours | Basic | Use this daily interval for devices with Quiet during quiet hours enabled. Times follow Home Assistant's local time zone; intervals can cross midnight. Off by default. |
| Quiet hours start | Basic | Daily start time, included in quiet hours. Choose a different time from the end. |
| Quiet hours end | Basic | Daily end time, excluded from quiet hours. A time earlier than the start ends the interval the next day. |
| Residents to track | Basic | Choose one Home Assistant person or GPS tracker per resident. |
| Occupied radius (m, 0 = off) | Basic | Count the home as occupied while anyone is within this distance. |
| Preparation radius (m, 0 = off) | Basic | Start Prepare for arrival when the first resident enters after everyone was outside. |
| Show room smileys | Basic | Show condition faces beside every room name. |

## Room sources

| Setting | Level | What it controls |
| --- | --- | --- |
| Windows | Basic | Select this room's real window-contact sensors. They tell the advisor which openings are currently open or closed; they never operate a window. |
| Air quality and environmental sensors | Basic | Select this room's air-quality sensors and optional light sensors (lux). Lux records light history. For solar shading, enable lux on the individual cover controller and choose a same-room sensor or the selected room mean: new automatic closing then requires the configured minimum brightness. Selecting sensors here does not enable movement. |
| Temperature | Basic | Select the room's actual indoor temperature sensors. When several valid sensors are selected, the manager combines them; unavailable readings are ignored. |
| Humidity | Basic | Select indoor relative-humidity sensors. Valid readings inform comfort, drying and mold-risk advice; missing readings are not treated as zero. |
| Devices | Basic | Devices. Select only physical climate.*, humidifier.* and fan.* entities assigned to this room. Their native capabilities determine which heating, cooling, drying, humidity, fan-speed or setpoint controls the Manager can offer. Automatic control and power changes remain off until expressly enabled on each managed device; selecting it here does not operate hardware. Switches and proportional actuators are configured separately. |
| Window blinds, shades and shutters | Basic | Window blinds, shades and shutters. Select native cover.* window blinds, shutters, shades or curtains in this room. Generic covers without device_class are also supported when their native CLOSE feature is advertised; check that they really are window shades. Garages, gates, doors, actual windows, dampers and awnings are excluded. Selection never moves a cover: its own room child device requires a linked window contact, an automatic-control switch, optional advance announcement and a temperature threshold. Unknown/unavailable covers can be selected but never moved until verified available. |
| Occupancy/presence sensors in this room | Basic | A valid occupied-room list in the selected state or attribute has priority: listed rooms are occupied and omitted rooms are empty. When no list is configured, or its source is unavailable, selected room sensors supply fallback evidence. Any ON means occupied; all OFF, or no selected sensors and no configured list, means empty. Numeric counts use 0 for empty and a positive value for occupied. Malformed lists, unknown room names and unavailable or restored selected sources can remain unknown. Unchanged lists and binary room states do not expire overnight. |
| Interior door contacts | Basic | Select real binary_sensor door contacts assigned to this exact Home Assistant room (effective Area). A closed door is not proof of an airtight room. The optional Eco policy is disabled by default and requires stable closure, verified vacancy, known safe indoor temperature/humidity, and all device protections. Door contacts never count as windows or occupancy. |

## Native controls

Look up the label or its translation key when comparing settings across installations. Home Assistant assigns entity IDs locally. Selectors with hardware-dependent choices show the options reported by the paired device. A button performs its named action when pressed.

### Home

| Setting | Level | Control or choices | Translation key |
| --- | --- | --- | --- |
| Announcement · AI wording | Advanced | switch | `home_ai_rewrite_announcements` |
| Announcement · Announce shade movement | Basic | switch | `home_shade_announce_before_movement` |
| Announcement · Automatic notifications | Basic | switch | `home_automatic_notifications` |
| Announcement · Automatic speech | Basic | switch | `home_automatic_tts` |
| Announcement · Language | Basic | select | `home_language` |
| Announcement · Open windows when away | Basic | switch | `home_away_open_window_alert` |
| Announcement · Repeat interval (min) | Advanced | number | `global_setting_announcement_repeat_minutes` |
| Announcement · Use Announcement Hub | Basic | switch | `home_use_announcement_hub` |
| Custom maximum age (minutes) | Basic | number | `global_occupancy_source_stale_minutes` |
| Custom maximum age (minutes) | Basic | number | `global_threshold_max_age_minutes` |
| Home - Prepare - Max Time | Basic | number | `arrival_preparation_timeout` |
| Home Occupancy | Basic | At least one person home, All home (legacy) | `home_global_policy_home_policy` |
| Home Occupancy · Away delay (min) | Basic | number | `global_occupancy_away_cooldown_minutes` |
| Home Occupancy · Away delay (min) | Basic | number | `home_global_occupancy_away_cooldown_minutes` |
| Home Occupancy · Cancel arrival preparation | Basic | button | `cancel_arrival_preparation` |
| Home Occupancy · Prepare for arrival | Basic | button | `prepare_for_arrival` |
| Home occupancy · Report freshness | Basic | Automatic (by source type), Custom timeout | `home_global_policy_source_freshness_mode` |
| Pollen · Avoid window ventilation when pollen is high (opt in) | Basic | switch | `home_global_environment_pollen_avoid_ventilation` |
| Pollen · Pollen provider's maximum scale value | Expert | number | `global_environment_pollen_max_scale` |
| Pollen · Pollen scale: threshold treated as high | Expert | number | `global_environment_pollen_high_from` |
| Quiet hours | Basic | switch | `home_quiet_hours_enabled` |
| Quiet hours end | Basic | time | `home_quiet_hours_end` |
| Quiet hours start | Basic | time | `home_quiet_hours_start` |
| Ventilation · AQI scale | Basic | Automatic (provider), Unknown - no comparison, US EPA AQI (0-500), EEA AQI (1-6), Custom scale | `home_aqi_scale` |
| Ventilation · Custom AQI limit | Basic | number | `home_aqi_custom_limit` |
| Ventilation · Indoor AQI triggering ventilation | Advanced | number | `global_threshold_indoor_aqi` |
| Ventilation · Indoor CO₂ triggering ventilation (ppm) | Advanced | number | `global_threshold_indoor_co2` |
| Ventilation · Indoor PM10 triggering ventilation (µg/m³) | Advanced | number | `global_threshold_indoor_pm10` |
| Ventilation · Indoor PM2.5 triggering ventilation (µg/m³) | Advanced | number | `global_threshold_indoor_pm25` |
| Ventilation · Indoor VOC triggering ventilation (ppb) | Advanced | number | `global_threshold_indoor_voc_parts` |
| Ventilation · Indoor VOC triggering ventilation (µg/m³) | Advanced | number | `global_threshold_indoor_voc` |
| Ventilation · Indoor humidity triggering ventilation (%) | Advanced | number | `global_threshold_indoor_humidity` |
| Ventilation · Maximum outdoor AQI | Advanced | number | `global_threshold_outdoor_aqi` |
| Ventilation · Maximum outdoor CO₂ (ppm) | Advanced | number | `global_threshold_outdoor_co2` |
| Ventilation · Maximum outdoor PM10 (µg/m³) | Advanced | number | `global_threshold_outdoor_pm10` |
| Ventilation · Maximum outdoor PM2.5 (µg/m³) | Advanced | number | `global_threshold_outdoor_pm25` |
| Ventilation · Maximum outdoor VOC (ppb) | Advanced | number | `global_threshold_outdoor_voc_parts` |
| Ventilation · Maximum outdoor VOC (µg/m³) | Advanced | number | `global_threshold_outdoor_voc` |
| Ventilation · Maximum outdoor humidity (%) | Basic | number | `global_threshold_max_outdoor_humidity` |
| Ventilation · Maximum outdoor temperature (°C) | Basic | number | `global_threshold_max_outdoor_temp` |
| Ventilation · Maximum wind speed (km/h) | Basic | number | `global_threshold_max_wind_kmh` |
| Ventilation · Measurement freshness | Basic | Automatic (by source type), Custom timeout | `global_threshold_mode_max_age_mode` |
| Ventilation · Minimum outdoor temperature (°C) | Basic | number | `global_threshold_min_outdoor_temp` |
| Ventilation · Mold indication triggering ventilation (estimated surface RH, %) | Advanced | number | `global_threshold_indoor_mold` |
| Ventilation · Outdoor NO₂ operational screen (µg/m³) | Advanced | number | `global_threshold_outdoor_no2` |
| Ventilation · Outdoor O₃ operational screen (µg/m³) | Advanced | number | `global_threshold_outdoor_o3` |
| Ventilation · Outdoor SO₂ operational screen (µg/m³) | Advanced | number | `global_threshold_outdoor_so2` |
| Ventilation · Wait before suggesting window closure (min) | Basic | number | `global_setting_window_close_cooldown_minutes` |
| Ventilation · Wait for window opening (min) | Basic | number | `global_setting_window_open_timeout_minutes` |

### Room

| Setting | Level | Control or choices | Translation key |
| --- | --- | --- | --- |
| Advanced comfort · Activity (met) | Expert | number | `area_area_environment_met` |
| Advanced comfort · Air speed (m/s) | Expert | number | `area_area_environment_air_speed_m_s` |
| Advanced comfort · Air-speed source | Expert | select | `area_area_science_air_speed_entity` |
| Advanced comfort · Clothing (clo) | Expert | number | `area_area_environment_clo` |
| Advanced comfort · Enable PMV/PPD | Expert | switch | `area_area_environment_enable_pmv` |
| Advanced comfort · Maximum target adjustment (°C) | Expert | number | `area_climate_operating_comfort_adjustment_max_c` |
| Advanced comfort · Radiant temperature source | Expert | select | `area_area_science_radiant_temperature_entity` |
| Advanced comfort · Temperature target method | Expert | Fixed temperature targets, Automatic comfort (measured temperature/RH), Advanced ISO 7730 (measurements required) | `area_climate_policy_target_source` |
| Air cleaning · Air purifier rated particle CADR (m³/h) | Expert | number | `area_area_environment_particle_cadr_m3h` |
| Air cleaning · Annual radon screening reference (Bq/m³) | Expert | number | `area_area_environment_radon_reference_bq_m3` |
| Air cleaning · CO₂ target (ppm) | Advanced | number | `area_area_environment_co2_target_ppm` |
| Air cleaning · Maximum extraction speed (%) | Basic | number | `area_climate_operating_extraction_speed_percent` |
| Air cleaning · Maximum purifier speed (%) | Basic | number | `area_climate_operating_purifier_speed_percent` |
| Air cleaning · PM2.5 fan threshold (µg/m³) | Advanced | number | `area_climate_operating_pm25_action_ug_m3` |
| Air cleaning · Room volume (m³) | Advanced | number | `area_area_environment_room_volume_m3` |
| Announcement · Window efficiency suggestions | Basic | switch | `area_climate_operating_window_efficiency_notify` |
| Custom maximum age (minutes) | Basic | number | `area_climate_operating_occupancy_stale_minutes` |
| Fan · Target speed (%) | Basic | number | `area_device_target_fan_speed_percent` |
| Home Occupancy · Away policy | Basic | At least one person home, All home (legacy) | `area_climate_policy_away_policy` |
| Humidity · Decision hysteresis (pp) | Advanced | number | `area_climate_operating_humidity_hysteresis_rh` |
| Humidity · Drying threshold (% RH) | Basic | number | `area_climate_operating_humidity_high_rh` |
| Humidity · Extra drying margin while cooling (pp) | Advanced | number | `area_climate_operating_cooling_dry_deferral_rh_points` |
| Humidity · Humidification threshold (% RH) | Basic | number | `area_climate_operating_humidity_low_rh` |
| Mold · Measured coldest surface temperature (°C) | Basic | number | `area_mold_surface_critical_temperature_c` |
| Mold · Recalculate calibration factor | Basic | button | `area_recalculate_mold` |
| Noise · Room used for sleeping | Basic | switch | `area_area_environment_sleep_room` |
| PID · Derivative gain Kd (%·minute per °C) | Expert | number | `area_pid_kd` |
| PID · Desired room temperature (°C) | Basic | number | `area_pid_target_c` |
| PID · Gain source | Expert | Defaults, Manual | `area_pid_gain_source` |
| PID · Highest permitted setpoint (°C) | Basic | number | `area_pid_max_setpoint_c` |
| PID · Integral gain Ki (% per °C-minute) | Expert | number | `area_pid_ki` |
| PID · Lowest permitted setpoint (°C) | Basic | number | `area_pid_min_setpoint_c` |
| PID · Maximum percentage-point change per cycle | Expert | number | `area_direct_tuning_max_demand_change` |
| PID · Maximum setpoint change per cycle (°C) | Expert | number | `area_pid_max_change_c` |
| PID · Maximum thermostat setpoint trim (°C) | Expert | number | `area_pid_offset_c` |
| PID · Minimum meaningful percentage-point change | Expert | number | `area_direct_tuning_min_demand_change` |
| PID · Minimum meaningful setpoint change (°C) | Expert | number | `area_pid_min_change_c` |
| PID · Proportional gain Kp (% per °C) | Expert | number | `area_pid_kp` |
| PID · derivative gain (percentage points·minute/°C) | Expert | number | `area_direct_tuning_kd` |
| PID · integral gain (percentage points/(°C·minute)) | Expert | number | `area_direct_tuning_ki` |
| PID · measurement cycle (seconds) | Expert | number | `area_pid_sample_seconds` |
| PID · proportional gain (percentage points/°C) | Expert | number | `area_direct_tuning_kp` |
| PID · sampling period (seconds) | Expert | number | `area_direct_tuning_sample_seconds` |
| Profile · Away · Cooling target (°C) | Basic | number | `area_climate_profile_away_cool` |
| Profile · Away · Heating target (°C) | Basic | number | `area_climate_profile_away_heat` |
| Profile · Away · Humidity target (%) | Basic | number | `area_climate_profile_away_humidity` |
| Profile · Comfort · Cooling target (°C) | Basic | number | `area_climate_profile_comfort_cool` |
| Profile · Comfort · Heating target (°C) | Basic | number | `area_climate_profile_comfort_heat` |
| Profile · Comfort · Humidity target (%) | Basic | number | `area_climate_profile_comfort_humidity` |
| Profile · Eco · Cooling target (°C) | Basic | number | `area_climate_profile_eco_cool` |
| Profile · Eco · Heating target (°C) | Basic | number | `area_climate_profile_eco_heat` |
| Profile · Eco · Humidity target (%) | Basic | number | `area_climate_profile_eco_humidity` |
| Profile · Home · Cooling target (°C) | Basic | number | `area_climate_profile_home_cool` |
| Profile · Home · Heating target (°C) | Basic | number | `area_climate_profile_home_heat` |
| Profile · Home · Humidity target (%) | Basic | number | `area_climate_profile_home_humidity` |
| Profile · Override (automatic recommended) | Basic | Comfort, Home, Away, Sleep, Eco, Automatic | `area_manual_profile` |
| Profile · Sleep · Cooling target (°C) | Basic | number | `area_climate_profile_sleep_cool` |
| Profile · Sleep · Heating target (°C) | Basic | number | `area_climate_profile_sleep_heat` |
| Profile · Sleep · Humidity target (%) | Basic | number | `area_climate_profile_sleep_humidity` |
| Room limits · Legacy maximum fan speed (%) | Basic | number | `area_room_equipment_limit_fan_max_percentage` |
| Room limits · Legacy minimum fan speed (%) | Basic | number | `area_room_equipment_limit_fan_min_percentage` |
| Room limits · Maximum humidity target (%) | Basic | number | `area_room_equipment_limit_humidity_max_limit` |
| Room limits · Maximum temperature target (°C) | Basic | number | `area_room_equipment_limit_temperature_max_limit` |
| Room limits · Minimum humidity target (%) | Basic | number | `area_room_equipment_limit_humidity_min_limit` |
| Room limits · Minimum temperature target (°C) | Basic | number | `area_room_equipment_limit_temperature_min_limit` |
| Room occupancy · Count freshness | Basic | Automatic (by source type), Custom timeout | `area_climate_policy_occupancy_freshness_mode` |
| Room occupancy · Vacancy delay (min) | Basic | number | `area_climate_operating_unoccupied_delay_minutes` |
| Room occupancy · When occupancy is unknown | Basic | Assume occupied, Hold automatic changes | `area_climate_policy_unknown_occupancy` |
| Shading · Automatic solar shade cooling | Basic | switch | `area_shading_enabled` |
| Shading · Close shades above room temperature (°C) | Basic | number | `area_shading_close_above_c` |
| Shading · Minimum sun elevation for shading (°) | Advanced | number | `area_shading_min_sun_elevation` |
| Sleep · End time (local) | Basic | time | `area_climate_sleep_end` |
| Sleep · Sleeping now | Basic | switch | `area_climate_operating_sleep_active` |
| Sleep · Start time (local) | Basic | time | `area_climate_sleep_start` |
| Sleep · Use schedule | Basic | switch | `area_climate_operating_sleep_schedule_enabled` |

### Appliance

| Setting | Level | Control or choices | Translation key |
| --- | --- | --- | --- |
| Announcement · Announce device errors | Basic | switch | `equipment_announce_device_errors` |
| Announcement · Window opening wait (min) | Basic | number | `equipment_window_open_timeout_minutes` |
| Away profile · cool target | Basic | Device or context dependent | `equipment_target_away_cool` |
| Away profile · heat target | Basic | Device or context dependent | `equipment_target_away_heat` |
| Away profile · humidity target | Basic | Device or context dependent | `equipment_target_away_humidity` |
| Comfort profile · cool target | Basic | Device or context dependent | `equipment_target_comfort_cool` |
| Comfort profile · heat target | Basic | Device or context dependent | `equipment_target_comfort_heat` |
| Comfort profile · humidity target | Basic | Device or context dependent | `equipment_target_comfort_humidity` |
| Control · Continue Automatic | Basic | button | `equipment_resume` |
| Control · Maximum target by mode | Basic | switch | `equipment_native_full_output` |
| Control · Method | Basic | Existing room controller, Automatic, Manual, Off, PID | `equipment_control_mode` |
| Control · Pause when a window opens | Basic | switch | `equipment_pause_on_window_open` |
| Coordinate equipment starts across doors | Advanced | Device or context dependent | `equipment_door_start_coordination` |
| Eco profile · cool target | Basic | Device or context dependent | `equipment_target_eco_cool` |
| Eco profile · heat target | Basic | Device or context dependent | `equipment_target_eco_heat` |
| Eco profile · humidity target | Basic | Device or context dependent | `equipment_target_eco_humidity` |
| Fan · Maximum speed (%) | Basic | number | `equipment_fan_max_percentage` |
| Fan · Minimum speed (%) | Basic | number | `equipment_fan_min_percentage` |
| Fan · Purpose | Basic | Air extraction, Particle filtration, Automatic | `equipment_fan_purpose` |
| Home profile · cool target | Basic | Device or context dependent | `equipment_target_home_cool` |
| Home profile · heat target | Basic | Device or context dependent | `equipment_target_home_heat` |
| Home profile · humidity target | Basic | Device or context dependent | `equipment_target_home_humidity` |
| Manual profile · cool target | Basic | Device or context dependent | `equipment_target_manual_cool` |
| Manual profile · heat target | Basic | Device or context dependent | `equipment_target_manual_heat` |
| Manual profile · humidity target | Basic | Device or context dependent | `equipment_target_manual_humidity` |
| Native device preset | Basic | Device or context dependent | `equipment_preset` |
| Native fan mode | Basic | Device or context dependent | `equipment_fan_mode` |
| Native horizontal swing mode | Basic | Device or context dependent | `equipment_swing_horizontal_mode` |
| Native vertical swing mode | Basic | Device or context dependent | `equipment_swing_mode` |
| Operation · Minimum device OFF time (min) | Basic | number | `equipment_min_off_seconds` |
| Operation · Minimum device ON time (min) | Basic | number | `equipment_min_on_seconds` |
| PID · Apply · Calibration | Expert | button | `equipment_pid_apply_calibration` |
| PID · Apply · Calibration | Expert | button | `equipment_pid_apply_fan_capacity` |
| PID · Approve suggestion | Basic | button | `equipment_pid_review_approve` |
| PID · Calibration | Basic | Manual Kp/Ki/Kd, IMC / λ, Cohen-Coon, Adaptive · Suggest & approve, Adaptive · Automatic (max 10% per change) | `equipment_pid_calibration_method` |
| PID · Choose mode | Expert | Choose mode, Heating, Cooling, Drying, Fan | `equipment_pid_fan_capacity_for_mode` |
| PID · Dead time | Expert | number | `equipment_pid_dead_time_minutes` |
| PID · Derivative gain Kd (%·minute per °C) | Advanced | number | `equipment_kd` |
| PID · Discard suggestion | Basic | button | `equipment_pid_review_discard` |
| PID · Fan speed 1 (%) | Expert | number | `equipment_pid_capacity_speed_1` |
| PID · Fan speed 2 (%) | Expert | number | `equipment_pid_capacity_speed_2` |
| PID · Fan speed 3 (%) | Expert | number | `equipment_pid_capacity_speed_3` |
| PID · IMC λ | Expert | number | `equipment_pid_lambda_minutes` |
| PID · Integral gain Ki (% per °C-minute) | Advanced | number | `equipment_ki` |
| PID · PWM cycle duration for slow thermal loads (seconds) | Advanced | number | `equipment_cycle_seconds` |
| PID · Passive adaptation | Expert | Disabled, Observe and suggest, Bounded auto-adapt (10% / day) | `equipment_pid_adaptation_mode` |
| PID · Process gain | Expert | number | `equipment_pid_process_gain` |
| PID · Proportional gain Kp (% per °C) | Advanced | number | `equipment_kp` |
| PID · Relative capacity | Expert | Original (uncalibrated), Measured capacity model | `equipment_pid_fan_capacity_mode` |
| PID · Relative capacity 1 (%) | Expert | number | `equipment_pid_capacity_output_1` |
| PID · Relative capacity 1 (%) | Expert | number | `equipment_pid_capacity_stage_1` |
| PID · Relative capacity 2 (%) | Expert | number | `equipment_pid_capacity_output_2` |
| PID · Relative capacity 2 (%) | Expert | number | `equipment_pid_capacity_stage_2` |
| PID · Relative capacity 3 (%) | Expert | number | `equipment_pid_capacity_output_3` |
| PID · Relative capacity 3 (%) | Expert | number | `equipment_pid_capacity_stage_3` |
| PID · Relative capacity 4 (%) | Expert | number | `equipment_pid_capacity_stage_4` |
| PID · Time constant | Expert | number | `equipment_pid_time_constant_minutes` |
| PID · measurement cycle (seconds) | Advanced | number | `equipment_sample_seconds` |
| Power · Idle cooldown before supply OFF (seconds) | Basic | number | `equipment_power_switch_cooldown_seconds` |
| Power · Maximum ON time (min) | Basic | number | `equipment_max_on_seconds` |
| Power · Upstream supply switch | Basic | select | `equipment_power_switch_entity` |
| Presence · Requirement | Basic | No room-presence restriction, Only while room is occupied, Only while room is empty | `equipment_presence_requirement` |
| Quiet during quiet hours | Basic | switch | `equipment_quiet_hours` |
| Quiet · Fan mode | Basic | select | `equipment_quiet_fan_mode` |
| Quiet · Fan percentage (%) | Basic | number | `equipment_quiet_percentage` |
| Quiet · When occupied | Basic | switch | `equipment_quiet_occupied` |
| Quiet · When sleeping | Basic | switch | `equipment_quiet_sleep` |
| Rated particle CADR of this air purifier (m³/h) | Advanced | number | `equipment_particle_cadr_m3h` |
| Safety · Post-shutdown watchdog | Basic | Monitor and recover, Monitor only, Disabled | `equipment_off_state_watchdog_mode` |
| Sensor · PM2.5 verified | Basic | switch | `equipment_sensor_verified` |
| Sleep profile · cool target | Basic | Device or context dependent | `equipment_target_sleep_cool` |
| Sleep profile · heat target | Basic | Device or context dependent | `equipment_target_sleep_heat` |
| Sleep profile · humidity target | Basic | Device or context dependent | `equipment_target_sleep_humidity` |
| Sleep · Behavior | Basic | Automatic, Hold, Sleep targets | `equipment_sleep_behavior` |
| Sleep · Keep device off when all asleep | Basic | switch | `equipment_sleep_when_everyone_asleep` |
| Suggest opening windows to avoid using this device | Basic | switch | `equipment_announce_before_start` |
| Use Eco with closed doors | Basic | Device or context dependent | `equipment_door_closed_eco` |

### Doors

| Setting | Level | Control or choices | Translation key |
| --- | --- | --- | --- |
| Door coordination policy | Advanced | Device or context dependent | `door_coordination` |
| Energy meter for the doorway policy | Expert | Device or context dependent | `door_energy_meter` |
| Interior or exterior door | Basic | Device or context dependent | `door_kind` |
| Room on the other side of the door | Basic | Device or context dependent | `door_target_area` |

### Shading

| Setting | Level | Control or choices | Translation key |
| --- | --- | --- | --- |
| Announcement · Announce shade movement | Basic | switch | `shade_announce` |
| Shading · Associated window contact | Basic | select | `shade_window_entity` |
| Shading · Automatic solar shade cooling | Basic | switch | `shade_auto_control` |
| Shading · Close shades above room temperature (°C) | Basic | number | `shade_close_above_c` |
| Shading · Minimum illuminance to close (lx) | Advanced | number | `shade_min_lux` |
| Shading · Solar-shading lux sensor | Advanced | select | `shade_lux_entity` |
| Shading · Use lux sensor for solar shading | Advanced | switch | `shade_lux_enabled` |

## Setup and options fields

This index includes the labels in Home Assistant's initial setup and options catalogs, including conditional and older forms. Current availability depends on the setup path. The card's home and room tables above correspond to its active source editors.

**Config / Areas** (`areas`)

Areas to monitor (`areas`), Use mold indication instead of raw room RH (`use_mold_indicator`)

**Config / Window sensor exclusions** (`window_sensors`)

Window entities to exclude (`excluded_window_entities`)

**Config / Room settings - indoor air and mold** (`indoor_sensors`)

Sensors to exclude in this room (`excluded_indoor_entities`), Room temperature sensor for mold calibration (`mold_indoor_temperature`), Measured coldest surface temperature (°C) (`mold_critical_temperature_c`), Recalibrate with current room and outdoor readings (`mold_recalibrate`), Outdoor temperature source for mold calibration (`mold_outdoor_weather_entity`)

**Config / Outdoor air quality** (`outdoor`)

Outdoor air-quality sensors (`outdoor_sensors`)

**Config / Weather and warnings** (`weather`)

Weather entities (`weather_entities`), Weather warning sensors (optional) (`weather_warnings`)

**Config / Announcements (optional)** (`delivery`)

Announcement language (`language`), Speak new recommendations automatically (`automatic_tts`), Notify about new recommendations automatically (`automatic_notifications`), Announcement · Use Announcement Hub (`use_announcement_hub`), Direct notification entities (`notify_entities`), Direct TTS engine (`tts_engine`), Direct TTS media players (`media_players`), Repeat announcements (minutes) (`announcement_repeat_minutes`), Use AI for announcements (`ai_rewrite_announcements`), Conversation agent (`ai_conversation_agent`)

**Config / Advanced thresholds** (`thresholds`)

Maximum outdoor AQI (`outdoor_aqi`), Maximum outdoor CO₂ (ppm) (`outdoor_co2`), Maximum outdoor PM2.5 (µg/m³) (`outdoor_pm25`), Maximum outdoor PM10 (µg/m³) (`outdoor_pm10`), Maximum outdoor VOC (µg/m³) (`outdoor_voc`), Maximum outdoor VOC (ppb) (`outdoor_voc_parts`), Outdoor NO₂ operational screen (µg/m³) (`outdoor_no2`), Outdoor O₃ operational screen (µg/m³) (`outdoor_o3`), Outdoor SO₂ operational screen (µg/m³) (`outdoor_so2`), Indoor AQI triggering ventilation (`indoor_aqi`), Indoor CO₂ triggering ventilation (ppm) (`indoor_co2`), Indoor PM2.5 triggering ventilation (µg/m³) (`indoor_pm25`), Indoor PM10 triggering ventilation (µg/m³) (`indoor_pm10`), Indoor VOC triggering ventilation (µg/m³) (`indoor_voc`), Indoor VOC triggering ventilation (ppb) (`indoor_voc_parts`), Indoor humidity triggering ventilation (%) (`indoor_humidity`), Minimum outdoor temperature (°C) (`min_outdoor_temp`), Maximum outdoor temperature (°C) (`max_outdoor_temp`), Maximum outdoor humidity (%) (`max_outdoor_humidity`), Ventilation · Maximum wind speed (km/h) (`max_wind_kmh`), Ventilation · Maximum reading age (min) (`max_age_minutes`), Mold indication triggering ventilation (estimated surface RH, %) (`indoor_mold`), Environment reading validity (`max_age_mode`)

**Config / Choose rooms** (`setup_rooms`)

Rooms to monitor (`areas`)

**Config / Room · {area_name} · {room_index}/{room_count}** (`setup_room_sources`)

Windows (`windows`), Air quality and environmental sensors (`air_quality`), Temperature (`temperature`), Humidity (`humidity`), Devices (`climate_devices`), Window blinds, shades and shutters (`shades`)

**Config / General settings** (`setup_general`)

Weather entities (`weather_entities`), Outdoor air-quality sensors (`outdoor_sensors`), Weather warning sensors (optional) (`weather_warnings`), Room · Occupancy · sensor (`general_room_occupancy_sensors`), Home · Occupancy · Devices (`general_home_trackers`), Occupancy · Room · source (state) (`general_occupied_rooms_entity`), Occupancy · Room · source (attribute) (`general_occupied_rooms_attribute`), Sleep · Room · source (state) (`general_sleep_rooms_entity`), Sleep · Room · source (attribute) (`general_sleep_rooms_attribute`), Direct notification entities (`notify_entities`), Direct TTS media players (`media_players`), Direct TTS engine (`tts_engine`), AI · Select · source (`ai_conversation_agent`), Announcement language (`language`), Use mold indication instead of raw room RH (`use_mold_indicator`), Pollen · source · Select (`pollen_entities`), Announcement · Use Announcement Hub (`use_announcement_hub`), Home · Away · cooldown (min) (`general_away_cooldown_minutes`), Alert when windows remain open after everyone leaves (`away_open_window_alert`), People to notify after leaving (`away_windows_target_people`), Delivery channels for open-window alerts (`away_windows_delivery_channels`), Maximum outdoor AQI (`global_threshold_outdoor_aqi`), Maximum outdoor CO₂ (ppm) (`global_threshold_outdoor_co2`), Maximum outdoor PM2.5 (µg/m³) (`global_threshold_outdoor_pm25`), Maximum outdoor PM10 (µg/m³) (`global_threshold_outdoor_pm10`), Maximum outdoor VOC (µg/m³) (`global_threshold_outdoor_voc`), Maximum outdoor VOC (ppb) (`global_threshold_outdoor_voc_parts`), Outdoor NO₂ operational screen (µg/m³) (`global_threshold_outdoor_no2`), Outdoor O₃ operational screen (µg/m³) (`global_threshold_outdoor_o3`), Outdoor SO₂ operational screen (µg/m³) (`global_threshold_outdoor_so2`), Indoor AQI triggering ventilation (`global_threshold_indoor_aqi`), Indoor CO₂ triggering ventilation (ppm) (`global_threshold_indoor_co2`), Indoor PM2.5 triggering ventilation (µg/m³) (`global_threshold_indoor_pm25`), Indoor PM10 triggering ventilation (µg/m³) (`global_threshold_indoor_pm10`), Indoor VOC triggering ventilation (µg/m³) (`global_threshold_indoor_voc`), Indoor VOC triggering ventilation (ppb) (`global_threshold_indoor_voc_parts`), Indoor humidity triggering ventilation (%) (`global_threshold_indoor_humidity`), Minimum outdoor temperature (°C) (`global_threshold_min_outdoor_temp`), Maximum outdoor temperature (°C) (`global_threshold_max_outdoor_temp`), Maximum outdoor humidity (%) (`global_threshold_max_outdoor_humidity`), Maximum wind speed (km/h) (`global_threshold_max_wind_kmh`), Maximum age of any outdoor reading (minutes) (`global_threshold_max_age_minutes`), Mold indication triggering ventilation (estimated surface RH, %) (`global_threshold_indoor_mold`), Pollen scale: threshold treated as high (`pollen_high_from`), Pollen provider's maximum scale value (`pollen_max_scale`), Avoid window ventilation when pollen is high (opt in) (`pollen_avoid_ventilation`), Home Occupancy · Maximum tracker/count report age (min) (`general_source_stale_minutes`), Home Occupancy (`general_home_policy`), Sleep · Next alarm (`general_wake_alarm_entity`), Sleep · Minutes before alarm (`general_wake_lead_minutes_entity`), Wait for window opening (min) (`window_open_timeout_minutes`), Wait before suggesting window closure (min) (`window_close_cooldown_minutes`), Quiet hours (`quiet_hours_enabled`), Quiet hours start (`quiet_hours_start`), Quiet hours end (`quiet_hours_end`), Residents to track (`general_proximity_trackers`), Occupied radius (m, 0 = off) (`general_occupied_radius_m`), Preparation radius (m, 0 = off) (`general_arrival_radius_m`), Show room smileys (`show_room_smileys`)

**Config / International air-quality sources and pollen** (`environment`)

Pollen forecast sensor (any country/provider) (`pollen_entity`), Pollen scale: threshold treated as high (`pollen_high_from`), Pollen provider's maximum scale value (`pollen_max_scale`), Avoid window ventilation when pollen is high (opt in) (`pollen_avoid_ventilation`), AQI sensor #1: source scale (`aqi_scale_0`), AQI sensor #1: custom unsafe threshold (`aqi_custom_limit_0`), AQI sensor #2: source scale (`aqi_scale_1`), AQI sensor #2: custom unsafe threshold (`aqi_custom_limit_1`), AQI sensor #3: source scale (`aqi_scale_2`), AQI sensor #3: custom unsafe threshold (`aqi_custom_limit_2`), AQI sensor #4: source scale (`aqi_scale_3`), AQI sensor #4: custom unsafe threshold (`aqi_custom_limit_3`), AQI sensor #5: source scale (`aqi_scale_4`), AQI sensor #5: custom unsafe threshold (`aqi_custom_limit_4`), AQI sensor #6: source scale (`aqi_scale_5`), AQI sensor #6: custom unsafe threshold (`aqi_custom_limit_5`), AQI sensor #7: source scale (`aqi_scale_6`), AQI sensor #7: custom unsafe threshold (`aqi_custom_limit_6`), AQI sensor #8: source scale (`aqi_scale_7`), AQI sensor #8: custom unsafe threshold (`aqi_custom_limit_7`), AQI sensor #9: source scale (`aqi_scale_8`), AQI sensor #9: custom unsafe threshold (`aqi_custom_limit_8`), AQI sensor #10: source scale (`aqi_scale_9`), AQI sensor #10: custom unsafe threshold (`aqi_custom_limit_9`), AQI sensor #11: source scale (`aqi_scale_10`), AQI sensor #11: custom unsafe threshold (`aqi_custom_limit_10`), AQI sensor #12: source scale (`aqi_scale_11`), AQI sensor #12: custom unsafe threshold (`aqi_custom_limit_11`), AQI sensor #13: source scale (`aqi_scale_12`), AQI sensor #13: custom unsafe threshold (`aqi_custom_limit_12`), AQI sensor #14: source scale (`aqi_scale_13`), AQI sensor #14: custom unsafe threshold (`aqi_custom_limit_13`), AQI sensor #15: source scale (`aqi_scale_14`), AQI sensor #15: custom unsafe threshold (`aqi_custom_limit_14`), AQI sensor #16: source scale (`aqi_scale_15`), AQI sensor #16: custom unsafe threshold (`aqi_custom_limit_15`), AQI sensor #17: source scale (`aqi_scale_16`), AQI sensor #17: custom unsafe threshold (`aqi_custom_limit_16`), AQI sensor #18: source scale (`aqi_scale_17`), AQI sensor #18: custom unsafe threshold (`aqi_custom_limit_17`), AQI sensor #19: source scale (`aqi_scale_18`), AQI sensor #19: custom unsafe threshold (`aqi_custom_limit_18`), AQI sensor #20: source scale (`aqi_scale_19`), AQI sensor #20: custom unsafe threshold (`aqi_custom_limit_19`), AQI sensor #21: source scale (`aqi_scale_20`), AQI sensor #21: custom unsafe threshold (`aqi_custom_limit_20`), AQI sensor #22: source scale (`aqi_scale_21`), AQI sensor #22: custom unsafe threshold (`aqi_custom_limit_21`), AQI sensor #23: source scale (`aqi_scale_22`), AQI sensor #23: custom unsafe threshold (`aqi_custom_limit_22`), AQI sensor #24: source scale (`aqi_scale_23`), AQI sensor #24: custom unsafe threshold (`aqi_custom_limit_23`), AQI sensor #25: source scale (`aqi_scale_24`), AQI sensor #25: custom unsafe threshold (`aqi_custom_limit_24`), AQI sensor #26: source scale (`aqi_scale_25`), AQI sensor #26: custom unsafe threshold (`aqi_custom_limit_25`), AQI sensor #27: source scale (`aqi_scale_26`), AQI sensor #27: custom unsafe threshold (`aqi_custom_limit_26`), AQI sensor #28: source scale (`aqi_scale_27`), AQI sensor #28: custom unsafe threshold (`aqi_custom_limit_27`), AQI sensor #29: source scale (`aqi_scale_28`), AQI sensor #29: custom unsafe threshold (`aqi_custom_limit_28`), AQI sensor #30: source scale (`aqi_scale_29`), AQI sensor #30: custom unsafe threshold (`aqi_custom_limit_29`), AQI sensor #31: source scale (`aqi_scale_30`), AQI sensor #31: custom unsafe threshold (`aqi_custom_limit_30`), AQI sensor #32: source scale (`aqi_scale_31`), AQI sensor #32: custom unsafe threshold (`aqi_custom_limit_31`)

**Config / Choose a room for environmental science** (`environment_room`)

Room to configure (`environment_area`)

**Config / Room: {area_name} - ventilation and moisture** (`environment_room_air`)

Room air temperature sensor (optional override) (`temperature_entity`), Measured room air volume (m³) (`room_volume_m3`), Air purifier rated particle CADR (m³/h) (`particle_cadr_m3h`), Air purifier power/fan entity (`purifier_entity`), Mechanical extraction fan/switch entity (`extractor_entity`), CO₂ sensor has verified real NDIR hardware (`co2_ndir_verified`), CO₂ ventilation target (ppm) (`co2_target_ppm`), Noise · Room used for sleeping (`sleep_room`)

**Config / Room: {area_name} - optional specialist sensors** (`environment_room_exposure`)

Dedicated radon sensor (`radon_entity`), Radon sensor uses dedicated calibrated hardware (`radon_sensor_verified`), Annual radon screening reference (Bq/m³) (`radon_reference_bq_m3`), Dedicated formaldehyde sensor (`formaldehyde_entity`), Formaldehyde measurement is real and verified (`formaldehyde_sensor_verified`), Calibrated A-weighted sound level (dB(A)) (`noise_entity`), Sound-level sensor delivers equivalent calibrated readings (`noise_sensor_calibrated`), Illuminance (lux) (`illuminance_entity`), Spectral sensor's melanopic EDI (lx) (`melanopic_edi_entity`), Melanopic EDI comes from a real spectral measurement (`melanopic_spectral_verified`)

**Config / Room: {area_name} - full thermal comfort (advanced)** (`environment_room_comfort`)

Calculate full ISO 7730 PMV/PPD (opt in) (`enable_pmv`), Mean radiant temperature sensor (°C) (`radiant_temperature_entity`), Measured local air-speed sensor (m/s) (`air_speed_entity`), Otherwise: explicitly estimated air speed (m/s) (`air_speed_m_s`), Occupant activity rate (met) (`met`), Occupant clothing insulation (clo) (`clo`)

**Config / Climate PID - select a room** (`pid`)

Monitored room to configure (`pid_area`)

**Config / Climate PID in {area_name} - devices and comfort target** (`pid_room`)

Enable supervisory climate PID for this room (`pid_enabled`), Authorized climate devices (`pid_climate_entities`), Independent room temperature sensor (`pid_temperature_entity`), Existing thermostat mode (`pid_mode`), Desired room temperature (°C) (`pid_target_c`), Pause when any room window is open or unknown (`pid_pause_on_window_open`)

**Config / Climate PID in {area_name} - advanced safety and tuning** (`pid_tuning`)

Proportional gain Kp (% per °C) (`pid_kp`), Integral gain Ki (% per °C-minute) (`pid_ki`), Derivative gain Kd (%·minute per °C) (`pid_kd`), Maximum thermostat setpoint trim (°C) (`pid_offset_c`), Lowest permitted setpoint (°C) (`pid_min_setpoint_c`), Highest permitted setpoint (°C) (`pid_max_setpoint_c`), PID measurement cycle (seconds) (`pid_sample_seconds`), Maximum setpoint change per cycle (°C) (`pid_max_change_c`), Minimum meaningful setpoint change (°C) (`pid_min_change_c`)

**Config / Climate - select room** (`climate`)

Room to configure (`climate_area`)

**Config / Climate - controller, occupancy and away** (`climate_room`)

Enable climate planning for this room (`climate_enabled`), Permit commands to the explicitly selected room controllers (separate opt ins) (`climate_allow_actuation`), Automatically switch between supported heat/cool modes (separate opt in) (`climate_auto_switch_hvac`), Prefer device's native heat_cool target range when available (`climate_prefer_native_auto`), Controller method / device capability (`climate_controller`), Heat, cool, off or automatic selection (`climate_mode`), Explicit room climate device (`climate_entity`), Fresh independent temperature sensor (`climate_temperature_entity`), Mode-switching hysteresis (°C) (`climate_hysteresis_c`)

**Config / Climate - occupancy, away, sleep and comfort** (`climate_presence`)

Occupancy/presence sensors in this room (`climate_occupancy_sensors`), People or device trackers for home/away (`climate_away_entities`), If occupancy is unknown: assume occupied or hold (`climate_unknown_occupancy`), Delay before considering a room unoccupied (minutes) (`climate_unoccupied_delay_minutes`), Room occupancy · Maximum count report age (min) (`climate_occupancy_stale_minutes`), Home Occupancy · Away policy (`climate_away_policy`), Override occupancy/away profile (auto recommended) (`climate_manual_profile`), Sleep · Sleeping now (`climate_sleep_active`), Sleep · Use schedule (`climate_sleep_schedule_enabled`), Sleep · Start time (local) (`climate_sleep_start`), Sleep · End time (local) (`climate_sleep_end`), Thermal comfort method (`climate_target_source`), Maximum comfort adjustment (°C) (`climate_comfort_adjustment_max_c`), Room count freshness (`climate_occupancy_freshness_mode`)

**Config / Climate - additional equipment and humidity** (`climate_equipment`)

Optional dedicated heating climate (radiator / heating zone) (`climate_heat_climate_entity`), Optional dedicated cooling climate (air conditioner / heat pump) (`climate_cool_climate_entity`), Optional climate with native DRY mode (`climate_dry_climate_entity`), Optional climate with FAN_ONLY mode (`climate_fan_climate_entity`), Optional humidifier entity (adds moisture) (`climate_humidifier_entity`), Optional dehumidifier entity (removes moisture) (`climate_dehumidifier_entity`), Optional extract / ventilation fan (`climate_extraction_fan_entity`), Optional air purifier fan (`climate_purifier_fan_entity`), Verified room humidity sensor (choose one if multiple) (`climate_humidity_entity`), Minimum target relative humidity (%) (`climate_humidity_low_rh`), Maximum target relative humidity (%) (`climate_humidity_high_rh`), Humidity decision hysteresis (percentage points) (`climate_humidity_hysteresis_rh`), Defer separate dehumidification while AC cools until RH exceeds upper limit by these percentage points (0 disables) (`climate_cooling_dry_deferral_rh_points`), Allow native humidity setpoint changes on an already-running humidifier (extra opt-in) (`climate_humidity_setpoint_auto`), Notify when a closed window could help replace active heating, cooling or dehumidification (requires trustworthy outdoor conditions) (`climate_window_efficiency_notify`), Allow automatic native AC DRY/FAN_ONLY mode transitions (separate opt-in; requires device commissioning) (`climate_dry_fan_mode_auto`), I confirm this exact AC has independently verified compressor, defrost and minimum-cycle protections (`climate_dry_fan_hardware_confirmed`), Permit native DRY/FAN_ONLY switching without a window contact (extra consent) (`climate_dry_fan_windowless_confirmed`), Minimum native DRY/FAN_ONLY mode dwell (seconds; at least 1800) (`climate_dry_fan_mode_dwell_s`), Allow automatic power control of verified dedicated humidifier/dehumidifier (separate opt-in; draft only) (`climate_humidity_power_auto`), I confirm dedicated equipment has independent tank, frost, overheating and compressor protection (`climate_humidity_power_hardware_confirmed`), Allow moisture control in this room without a window contact (extra opt-in) (`climate_humidity_power_windowless_confirmed`), Minimum power-on dwell before stopping (seconds) (`climate_humidity_power_min_on_s`), Minimum observed power-off dwell before restarting (seconds) (`climate_humidity_power_min_off_s`), Maximum controller-owned continuous operating time (seconds) (`climate_humidity_power_max_on_s`), Allow setpoint-only control of already-on secondary heating/cooling thermostats (extra opt-in) (`climate_secondary_climate_setpoint_auto`)

**Config / Climate - ventilation and air purification** (`climate_air_strategy`)

Allow speed-only adjustment of already-on extraction/purifier fans (extra opt-in) (`climate_fan_speed_auto`), Allow guarded automatic on/off for dedicated extraction/purifier fan.* devices (separate draft opt-in) (`climate_fan_power_auto`), I confirm independent electrical, backdraft, fire and ventilation-pressure protections on selected fans (`climate_fan_power_hardware_confirmed`), Minimum fan operating interval (seconds) (`climate_fan_power_min_on_s`), Minimum observed fan off interval (seconds) (`climate_fan_power_min_off_s`), Maximum continuous controller-owned fan operating time (seconds) (`climate_fan_power_max_on_s`), I have verified this is a real PM2.5 measurement, not an estimated index (`climate_pm25_sensor_verified`), Selected true indoor CO₂ sensor (NDIR verification in environmental room setup) (`climate_co2_entity`), Selected indoor PM2.5 sensor (`climate_pm25_entity`), Short-term PM2.5 operational fan threshold (µg/m³; not WHO exposure guidance) (`climate_pm25_action_ug_m3`), Highest target speed for already-on extraction fan (%) (`climate_extraction_speed_percent`), Highest target speed for already-on purifier fan (%) (`climate_purifier_speed_percent`)

**Config / Climate - temperature bands for each mode** (`climate_profiles`)

Home heat (`home_heat`), Home cool (`home_cool`), Unoccupied heat (`unoccupied_heat`), Unoccupied cool (`unoccupied_cool`), Away heat (`away_heat`), Away cool (`away_cool`), Sleep heat (`sleep_heat`), Sleep cool (`sleep_cool`)

**Config / Direct actuators - verify the equipment and limits** (`climate_actuators`)

I confirm these are non-compressor thermal actuators with independent overtemperature protection (`direct_hardware_confirmed`), Heating switch or proportional output (`heat_actuator`), Cooling switch or proportional output (`cool_actuator`), Minimum energized interval (seconds) (`min_on_s`), Minimum de-energized interval (seconds) (`min_off_s`), Maximum continuous energized runtime (seconds) (`max_on_s`), Minimum delay between heating and cooling (seconds) (`mode_dwell_s`), PID proportional gain (percentage points/°C) (`kp`), PID integral gain (percentage points/(°C·minute)) (`ki`), PID derivative gain (percentage points·minute/°C) (`kd`), PID sampling period (seconds) (`sample_seconds`), PWM cycle duration for slow thermal loads (seconds) (`pwm_period_s`), Maximum percentage-point change per cycle (`max_demand_change`), Minimum meaningful percentage-point change (`min_demand_change`)

**Config / General settings** (`general_settings`)

Room · Occupancy · sensor (`general_room_occupancy_sensors`), Occupancy · Room · source (state) (`general_occupied_rooms_entity`), Occupancy · Room · source (attribute) (`general_occupied_rooms_attribute`), Home · Occupancy · Devices (`general_home_trackers`), Home Occupancy (`general_home_policy`), Sleep · Room · source (state) (`general_sleep_rooms_entity`), Sleep · Room · source (attribute) (`general_sleep_rooms_attribute`), Home Occupancy · Maximum tracker/count report age (min) (`general_source_stale_minutes`), Sleep · Next alarm (`general_wake_alarm_entity`), Sleep · Minutes before alarm (`general_wake_lead_minutes_entity`), Quiet hours (`quiet_hours_enabled`), Quiet hours start (`quiet_hours_start`), Quiet hours end (`quiet_hours_end`), Residents to track (`general_proximity_trackers`), Occupied radius (m, 0 = off) (`general_occupied_radius_m`), Preparation radius (m, 0 = off) (`general_arrival_radius_m`)

**Config / Pollen** (`pollen`)

Pollen forecast sensor (any country/provider) (`pollen_entity`), Pollen scale: threshold treated as high (`pollen_high_from`), Pollen provider's maximum scale value (`pollen_max_scale`), Avoid window ventilation when pollen is high (opt in) (`pollen_avoid_ventilation`)

**Config / Outside · AQI** (`outside_aqi`)

AQI · sensor (`outside_aqi_entity`), AQI scale (`outside_aqi_scale`), Custom AQI limit (`outside_aqi_limit`), AQI · sensor · Required (`outside_aqi_no_sources`)

**Config / Climate devices** (`area_devices`)

Select · Area (`area_devices_area`)

**Config / Climate devices** (`select_devices`)

Select · Devices (`selected_devices`), Configure sensors and hardware permissions now (`configure_device_sources`)

**Config / Select · Devices** (`device_choice`)

Select · Devices (`device_choice`)

**Config / Devices · control** (`device_settings`)

Automatic control (`device_auto_control`), control · source (`device_method`), control · Occupancy (`device_presence_requirement`), Off · Occupancy (`device_absence_action`), Sleep · control (`device_sleep_behavior`), Required · Devices · Power (`device_hardware_confirmed`), Temperature · sensor (`device_temperature_entity`), Humidity · sensor (`device_humidity_entity`), CO₂ · sensor (`device_co2_entity`), PM2.5 · sensor (`device_pm25_entity`), control · Devices (`device_fan_purpose`), sensor · PM2.5 verified (`device_sensor_verified`), Speed (%) (`device_fan_speed_percent`), Humidity · target (%) (`device_humidity_target`), Sleep · Humidity · target (%) (`device_sleep_humidity_target`), Power · min ON (s) (`device_min_on_s`), Power · min OFF (s) (`device_min_off_s`), Power · max ON (s) (`device_max_on_s`), Home · Temperature + · target (°C) (`device_home_heat_c`), Home · Temperature − · target (°C) (`device_home_cool_c`), Room · Off · Temperature + · target (°C) (`device_unoccupied_heat_c`), Room · Off · Temperature − · target (°C) (`device_unoccupied_cool_c`), Heating · Away (°C) (`device_away_heat_c`), Cooling · Away (°C) (`device_away_cool_c`), Sleep · Temperature + · target (°C) (`device_sleep_heat_c`), Sleep · Temperature − · target (°C) (`device_sleep_cool_c`)

**Config / Choose a room** (`room_occupancy`)

Room (`room_occupancy_area`)

**Config / Room presence fallback · {area_name}** (`room_occupancy_sources`)

Selected occupancy/presence sensors (`room_occupancy_sensors`)

**Config / Choose rooms** (`choose_rooms`)

Rooms to monitor (`areas`)

**Config / Settings · {area_name}** (`room_settings`)

Windows (`windows`), Air quality and environmental sensors (`air_quality`), Temperature (`temperature`), Humidity (`humidity`), Devices (`climate_devices`), Window blinds, shades and shutters (`shades`), Occupancy/presence sensors in this room (`occupancy_sensors`)

**Config / Room settings** (`select_room`)

Room (`edit_room_area`)

**Config / Settings · {area_name}** (`edit_room`)

Windows (`windows`), Air quality and environmental sensors (`air_quality`), Temperature (`temperature`), Humidity (`humidity`), Devices (`climate_devices`), Window blinds, shades and shutters (`shades`), Occupancy/presence sensors in this room (`occupancy_sensors`), Interior door contacts (`door_sensors`)

**Options / Window sensor exclusions** (`window_sensors`)

Window entities to exclude (`excluded_window_entities`)

**Options / Areas** (`areas`)

Areas to monitor (`areas`), Use mold indication instead of raw room RH (`use_mold_indicator`)

**Options / Room settings - indoor air and mold** (`indoor_sensors`)

Sensors to exclude in this room (`excluded_indoor_entities`), Room temperature sensor for mold calibration (`mold_indoor_temperature`), Measured coldest surface temperature (°C) (`mold_critical_temperature_c`), Recalibrate with current room and outdoor readings (`mold_recalibrate`), Outdoor temperature source for mold calibration (`mold_outdoor_weather_entity`)

**Options / Outdoor air quality** (`outdoor`)

Outdoor air-quality sensors (`outdoor_sensors`)

**Options / Weather and warnings** (`weather`)

Weather entities (`weather_entities`), Weather warning sensors (optional) (`weather_warnings`)

**Options / Announcements (optional)** (`delivery`)

Announcement language (`language`), Speak new recommendations automatically (`automatic_tts`), Notify about new recommendations automatically (`automatic_notifications`), Announcement · Use Announcement Hub (`use_announcement_hub`), Direct notification entities (`notify_entities`), Direct TTS engine (`tts_engine`), Direct TTS media players (`media_players`), Repeat announcements (minutes) (`announcement_repeat_minutes`), Use AI for announcements (`ai_rewrite_announcements`), Conversation agent (`ai_conversation_agent`)

**Options / Advanced thresholds** (`thresholds`)

Maximum outdoor AQI (`outdoor_aqi`), Maximum outdoor CO₂ (ppm) (`outdoor_co2`), Maximum outdoor PM2.5 (µg/m³) (`outdoor_pm25`), Maximum outdoor PM10 (µg/m³) (`outdoor_pm10`), Maximum outdoor VOC (µg/m³) (`outdoor_voc`), Maximum outdoor VOC (ppb) (`outdoor_voc_parts`), Outdoor NO₂ operational screen (µg/m³) (`outdoor_no2`), Outdoor O₃ operational screen (µg/m³) (`outdoor_o3`), Outdoor SO₂ operational screen (µg/m³) (`outdoor_so2`), Indoor AQI triggering ventilation (`indoor_aqi`), Indoor CO₂ triggering ventilation (ppm) (`indoor_co2`), Indoor PM2.5 triggering ventilation (µg/m³) (`indoor_pm25`), Indoor PM10 triggering ventilation (µg/m³) (`indoor_pm10`), Indoor VOC triggering ventilation (µg/m³) (`indoor_voc`), Indoor VOC triggering ventilation (ppb) (`indoor_voc_parts`), Indoor humidity triggering ventilation (%) (`indoor_humidity`), Minimum outdoor temperature (°C) (`min_outdoor_temp`), Maximum outdoor temperature (°C) (`max_outdoor_temp`), Maximum outdoor humidity (%) (`max_outdoor_humidity`), Ventilation · Maximum wind speed (km/h) (`max_wind_kmh`), Ventilation · Maximum reading age (min) (`max_age_minutes`), Mold indication triggering ventilation (estimated surface RH, %) (`indoor_mold`)

**Options / International air-quality sources and pollen** (`environment`)

Pollen forecast sensor (any country/provider) (`pollen_entity`), Pollen scale: threshold treated as high (`pollen_high_from`), Pollen provider's maximum scale value (`pollen_max_scale`), Avoid window ventilation when pollen is high (opt in) (`pollen_avoid_ventilation`), AQI sensor #1: source scale (`aqi_scale_0`), AQI sensor #1: custom unsafe threshold (`aqi_custom_limit_0`), AQI sensor #2: source scale (`aqi_scale_1`), AQI sensor #2: custom unsafe threshold (`aqi_custom_limit_1`), AQI sensor #3: source scale (`aqi_scale_2`), AQI sensor #3: custom unsafe threshold (`aqi_custom_limit_2`), AQI sensor #4: source scale (`aqi_scale_3`), AQI sensor #4: custom unsafe threshold (`aqi_custom_limit_3`), AQI sensor #5: source scale (`aqi_scale_4`), AQI sensor #5: custom unsafe threshold (`aqi_custom_limit_4`), AQI sensor #6: source scale (`aqi_scale_5`), AQI sensor #6: custom unsafe threshold (`aqi_custom_limit_5`), AQI sensor #7: source scale (`aqi_scale_6`), AQI sensor #7: custom unsafe threshold (`aqi_custom_limit_6`), AQI sensor #8: source scale (`aqi_scale_7`), AQI sensor #8: custom unsafe threshold (`aqi_custom_limit_7`), AQI sensor #9: source scale (`aqi_scale_8`), AQI sensor #9: custom unsafe threshold (`aqi_custom_limit_8`), AQI sensor #10: source scale (`aqi_scale_9`), AQI sensor #10: custom unsafe threshold (`aqi_custom_limit_9`), AQI sensor #11: source scale (`aqi_scale_10`), AQI sensor #11: custom unsafe threshold (`aqi_custom_limit_10`), AQI sensor #12: source scale (`aqi_scale_11`), AQI sensor #12: custom unsafe threshold (`aqi_custom_limit_11`), AQI sensor #13: source scale (`aqi_scale_12`), AQI sensor #13: custom unsafe threshold (`aqi_custom_limit_12`), AQI sensor #14: source scale (`aqi_scale_13`), AQI sensor #14: custom unsafe threshold (`aqi_custom_limit_13`), AQI sensor #15: source scale (`aqi_scale_14`), AQI sensor #15: custom unsafe threshold (`aqi_custom_limit_14`), AQI sensor #16: source scale (`aqi_scale_15`), AQI sensor #16: custom unsafe threshold (`aqi_custom_limit_15`), AQI sensor #17: source scale (`aqi_scale_16`), AQI sensor #17: custom unsafe threshold (`aqi_custom_limit_16`), AQI sensor #18: source scale (`aqi_scale_17`), AQI sensor #18: custom unsafe threshold (`aqi_custom_limit_17`), AQI sensor #19: source scale (`aqi_scale_18`), AQI sensor #19: custom unsafe threshold (`aqi_custom_limit_18`), AQI sensor #20: source scale (`aqi_scale_19`), AQI sensor #20: custom unsafe threshold (`aqi_custom_limit_19`), AQI sensor #21: source scale (`aqi_scale_20`), AQI sensor #21: custom unsafe threshold (`aqi_custom_limit_20`), AQI sensor #22: source scale (`aqi_scale_21`), AQI sensor #22: custom unsafe threshold (`aqi_custom_limit_21`), AQI sensor #23: source scale (`aqi_scale_22`), AQI sensor #23: custom unsafe threshold (`aqi_custom_limit_22`), AQI sensor #24: source scale (`aqi_scale_23`), AQI sensor #24: custom unsafe threshold (`aqi_custom_limit_23`), AQI sensor #25: source scale (`aqi_scale_24`), AQI sensor #25: custom unsafe threshold (`aqi_custom_limit_24`), AQI sensor #26: source scale (`aqi_scale_25`), AQI sensor #26: custom unsafe threshold (`aqi_custom_limit_25`), AQI sensor #27: source scale (`aqi_scale_26`), AQI sensor #27: custom unsafe threshold (`aqi_custom_limit_26`), AQI sensor #28: source scale (`aqi_scale_27`), AQI sensor #28: custom unsafe threshold (`aqi_custom_limit_27`), AQI sensor #29: source scale (`aqi_scale_28`), AQI sensor #29: custom unsafe threshold (`aqi_custom_limit_28`), AQI sensor #30: source scale (`aqi_scale_29`), AQI sensor #30: custom unsafe threshold (`aqi_custom_limit_29`), AQI sensor #31: source scale (`aqi_scale_30`), AQI sensor #31: custom unsafe threshold (`aqi_custom_limit_30`), AQI sensor #32: source scale (`aqi_scale_31`), AQI sensor #32: custom unsafe threshold (`aqi_custom_limit_31`)

**Options / Choose a room for environmental science** (`environment_room`)

Room to configure (`environment_area`)

**Options / Room: {area_name} - ventilation and moisture** (`environment_room_air`)

Room air temperature sensor (optional override) (`temperature_entity`), Measured room air volume (m³) (`room_volume_m3`), Air purifier rated particle CADR (m³/h) (`particle_cadr_m3h`), Air purifier power/fan entity (`purifier_entity`), Mechanical extraction fan/switch entity (`extractor_entity`), CO₂ sensor has verified real NDIR hardware (`co2_ndir_verified`), CO₂ ventilation target (ppm) (`co2_target_ppm`), Noise · Room used for sleeping (`sleep_room`)

**Options / Room: {area_name} - optional specialist sensors** (`environment_room_exposure`)

Dedicated radon sensor (`radon_entity`), Radon sensor uses dedicated calibrated hardware (`radon_sensor_verified`), Annual radon screening reference (Bq/m³) (`radon_reference_bq_m3`), Dedicated formaldehyde sensor (`formaldehyde_entity`), Formaldehyde measurement is real and verified (`formaldehyde_sensor_verified`), Calibrated A-weighted sound level (dB(A)) (`noise_entity`), Sound-level sensor delivers equivalent calibrated readings (`noise_sensor_calibrated`), Illuminance (lux) (`illuminance_entity`), Spectral sensor's melanopic EDI (lx) (`melanopic_edi_entity`), Melanopic EDI comes from a real spectral measurement (`melanopic_spectral_verified`)

**Options / Room: {area_name} - full thermal comfort (advanced)** (`environment_room_comfort`)

Calculate full ISO 7730 PMV/PPD (opt in) (`enable_pmv`), Mean radiant temperature sensor (°C) (`radiant_temperature_entity`), Measured local air-speed sensor (m/s) (`air_speed_entity`), Otherwise: explicitly estimated air speed (m/s) (`air_speed_m_s`), Occupant activity rate (met) (`met`), Occupant clothing insulation (clo) (`clo`)

**Options / Climate PID - select a room** (`pid`)

Monitored room to configure (`pid_area`)

**Options / Climate PID in {area_name} - devices and comfort target** (`pid_room`)

Enable supervisory climate PID for this room (`pid_enabled`), Authorized climate devices (`pid_climate_entities`), Independent room temperature sensor (`pid_temperature_entity`), Existing thermostat mode (`pid_mode`), Desired room temperature (°C) (`pid_target_c`), Pause when any room window is open or unknown (`pid_pause_on_window_open`)

**Options / Climate PID in {area_name} - advanced safety and tuning** (`pid_tuning`)

Proportional gain Kp (% per °C) (`pid_kp`), Integral gain Ki (% per °C-minute) (`pid_ki`), Derivative gain Kd (%·minute per °C) (`pid_kd`), Maximum thermostat setpoint trim (°C) (`pid_offset_c`), Lowest permitted setpoint (°C) (`pid_min_setpoint_c`), Highest permitted setpoint (°C) (`pid_max_setpoint_c`), PID measurement cycle (seconds) (`pid_sample_seconds`), Maximum setpoint change per cycle (°C) (`pid_max_change_c`), Minimum meaningful setpoint change (°C) (`pid_min_change_c`)

**Options / Climate - select room** (`climate`)

Room to configure (`climate_area`)

**Options / Climate - controller, occupancy and away** (`climate_room`)

Enable climate planning for this room (`climate_enabled`), Permit commands to the explicitly selected room controllers (separate opt ins) (`climate_allow_actuation`), Automatically switch between supported heat/cool modes (separate opt in) (`climate_auto_switch_hvac`), Prefer device's native heat_cool target range when available (`climate_prefer_native_auto`), Controller method / device capability (`climate_controller`), Heat, cool, off or automatic selection (`climate_mode`), Explicit room climate device (`climate_entity`), Fresh independent temperature sensor (`climate_temperature_entity`), Mode-switching hysteresis (°C) (`climate_hysteresis_c`)

**Options / Climate - occupancy, away, sleep and comfort** (`climate_presence`)

Occupancy/presence sensors in this room (`climate_occupancy_sensors`), People or device trackers for home/away (`climate_away_entities`), If occupancy is unknown: assume occupied or hold (`climate_unknown_occupancy`), Delay before considering a room unoccupied (minutes) (`climate_unoccupied_delay_minutes`), Room occupancy · Maximum count report age (min) (`climate_occupancy_stale_minutes`), Home Occupancy · Away policy (`climate_away_policy`), Override occupancy/away profile (auto recommended) (`climate_manual_profile`), Sleep · Sleeping now (`climate_sleep_active`), Sleep · Use schedule (`climate_sleep_schedule_enabled`), Sleep · Start time (local) (`climate_sleep_start`), Sleep · End time (local) (`climate_sleep_end`), Thermal comfort method (`climate_target_source`), Maximum comfort adjustment (°C) (`climate_comfort_adjustment_max_c`)

**Options / Climate - additional equipment and humidity** (`climate_equipment`)

Optional dedicated heating climate (radiator / heating zone) (`climate_heat_climate_entity`), Optional dedicated cooling climate (air conditioner / heat pump) (`climate_cool_climate_entity`), Optional climate with native DRY mode (`climate_dry_climate_entity`), Optional climate with FAN_ONLY mode (`climate_fan_climate_entity`), Optional humidifier entity (adds moisture) (`climate_humidifier_entity`), Optional dehumidifier entity (removes moisture) (`climate_dehumidifier_entity`), Optional extract / ventilation fan (`climate_extraction_fan_entity`), Optional air purifier fan (`climate_purifier_fan_entity`), Verified room humidity sensor (choose one if multiple) (`climate_humidity_entity`), Minimum target relative humidity (%) (`climate_humidity_low_rh`), Maximum target relative humidity (%) (`climate_humidity_high_rh`), Humidity decision hysteresis (percentage points) (`climate_humidity_hysteresis_rh`), Defer separate dehumidification while AC cools until RH exceeds upper limit by these percentage points (0 disables) (`climate_cooling_dry_deferral_rh_points`), Allow native humidity setpoint changes on an already-running humidifier (extra opt-in) (`climate_humidity_setpoint_auto`), Notify when a closed window could help replace active heating, cooling or dehumidification (requires trustworthy outdoor conditions) (`climate_window_efficiency_notify`), Allow automatic native AC DRY/FAN_ONLY mode transitions (separate opt-in; requires device commissioning) (`climate_dry_fan_mode_auto`), I confirm this exact AC has independently verified compressor, defrost and minimum-cycle protections (`climate_dry_fan_hardware_confirmed`), Permit native DRY/FAN_ONLY switching without a window contact (extra consent) (`climate_dry_fan_windowless_confirmed`), Minimum native DRY/FAN_ONLY mode dwell (seconds; at least 1800) (`climate_dry_fan_mode_dwell_s`), Allow automatic power control of verified dedicated humidifier/dehumidifier (separate opt-in; draft only) (`climate_humidity_power_auto`), I confirm dedicated equipment has independent tank, frost, overheating and compressor protection (`climate_humidity_power_hardware_confirmed`), Allow moisture control in this room without a window contact (extra opt-in) (`climate_humidity_power_windowless_confirmed`), Minimum power-on dwell before stopping (seconds) (`climate_humidity_power_min_on_s`), Minimum observed power-off dwell before restarting (seconds) (`climate_humidity_power_min_off_s`), Maximum controller-owned continuous operating time (seconds) (`climate_humidity_power_max_on_s`), Allow setpoint-only control of already-on secondary heating/cooling thermostats (extra opt-in) (`climate_secondary_climate_setpoint_auto`)

**Options / Climate - ventilation and air purification** (`climate_air_strategy`)

Allow speed-only adjustment of already-on extraction/purifier fans (extra opt-in) (`climate_fan_speed_auto`), Allow guarded automatic on/off for dedicated extraction/purifier fan.* devices (separate draft opt-in) (`climate_fan_power_auto`), I confirm independent electrical, backdraft, fire and ventilation-pressure protections on selected fans (`climate_fan_power_hardware_confirmed`), Minimum fan operating interval (seconds) (`climate_fan_power_min_on_s`), Minimum observed fan off interval (seconds) (`climate_fan_power_min_off_s`), Maximum continuous controller-owned fan operating time (seconds) (`climate_fan_power_max_on_s`), I have verified this is a real PM2.5 measurement, not an estimated index (`climate_pm25_sensor_verified`), Selected true indoor CO₂ sensor (NDIR verification in environmental room setup) (`climate_co2_entity`), Selected indoor PM2.5 sensor (`climate_pm25_entity`), Short-term PM2.5 operational fan threshold (µg/m³; not WHO exposure guidance) (`climate_pm25_action_ug_m3`), Highest target speed for already-on extraction fan (%) (`climate_extraction_speed_percent`), Highest target speed for already-on purifier fan (%) (`climate_purifier_speed_percent`)

**Options / Climate - temperature bands for each mode** (`climate_profiles`)

Home heat (`home_heat`), Home cool (`home_cool`), Unoccupied heat (`unoccupied_heat`), Unoccupied cool (`unoccupied_cool`), Away heat (`away_heat`), Away cool (`away_cool`), Sleep heat (`sleep_heat`), Sleep cool (`sleep_cool`)

**Options / Direct actuators - verify the equipment and limits** (`climate_actuators`)

I confirm these are non-compressor thermal actuators with independent overtemperature protection (`direct_hardware_confirmed`), Heating switch or proportional output (`heat_actuator`), Cooling switch or proportional output (`cool_actuator`), Minimum energized interval (seconds) (`min_on_s`), Minimum de-energized interval (seconds) (`min_off_s`), Maximum continuous energized runtime (seconds) (`max_on_s`), Minimum delay between heating and cooling (seconds) (`mode_dwell_s`), PID proportional gain (percentage points/°C) (`kp`), PID integral gain (percentage points/(°C·minute)) (`ki`), PID derivative gain (percentage points·minute/°C) (`kd`), PID sampling period (seconds) (`sample_seconds`), PWM cycle duration for slow thermal loads (seconds) (`pwm_period_s`), Maximum percentage-point change per cycle (`max_demand_change`), Minimum meaningful percentage-point change (`min_demand_change`)

**Options / General settings** (`general_settings`)

Room · Occupancy · sensor (`general_room_occupancy_sensors`), Occupancy · Room · source (state) (`general_occupied_rooms_entity`), Occupancy · Room · source (attribute) (`general_occupied_rooms_attribute`), Home · Occupancy · Devices (`general_home_trackers`), Home Occupancy (`general_home_policy`), Sleep · Room · source (state) (`general_sleep_rooms_entity`), Sleep · Room · source (attribute) (`general_sleep_rooms_attribute`), Home Occupancy · Maximum tracker/count report age (min) (`general_source_stale_minutes`), Sleep · Next alarm (`general_wake_alarm_entity`), Sleep · Minutes before alarm (`general_wake_lead_minutes_entity`), Quiet hours (`quiet_hours_enabled`), Quiet hours start (`quiet_hours_start`), Quiet hours end (`quiet_hours_end`), Residents to track (`general_proximity_trackers`), Occupied radius (m, 0 = off) (`general_occupied_radius_m`), Preparation radius (m, 0 = off) (`general_arrival_radius_m`)

**Options / Pollen** (`pollen`)

Pollen forecast sensor (any country/provider) (`pollen_entity`), Pollen scale: threshold treated as high (`pollen_high_from`), Pollen provider's maximum scale value (`pollen_max_scale`), Avoid window ventilation when pollen is high (opt in) (`pollen_avoid_ventilation`)

**Options / Outside · AQI** (`outside_aqi`)

AQI · sensor (`outside_aqi_entity`), AQI scale (`outside_aqi_scale`), Custom AQI limit (`outside_aqi_limit`), AQI · sensor · Required (`outside_aqi_no_sources`)

**Options / Climate devices** (`area_devices`)

Select · Area (`area_devices_area`)

**Options / Climate devices** (`select_devices`)

Select · Devices (`selected_devices`), Configure sensors and hardware permissions now (`configure_device_sources`)

**Options / Select · Devices** (`device_choice`)

Select · Devices (`device_choice`)

**Options / Devices · control** (`device_settings`)

Automatic control (`device_auto_control`), control · source (`device_method`), control · Occupancy (`device_presence_requirement`), Off · Occupancy (`device_absence_action`), Sleep · control (`device_sleep_behavior`), Required · Devices · Power (`device_hardware_confirmed`), Temperature · sensor (`device_temperature_entity`), Humidity · sensor (`device_humidity_entity`), CO₂ · sensor (`device_co2_entity`), PM2.5 · sensor (`device_pm25_entity`), control · Devices (`device_fan_purpose`), sensor · PM2.5 verified (`device_sensor_verified`), Speed (%) (`device_fan_speed_percent`), Humidity · target (%) (`device_humidity_target`), Sleep · Humidity · target (%) (`device_sleep_humidity_target`), Power · min ON (s) (`device_min_on_s`), Power · min OFF (s) (`device_min_off_s`), Power · max ON (s) (`device_max_on_s`), Home · Temperature + · target (°C) (`device_home_heat_c`), Home · Temperature − · target (°C) (`device_home_cool_c`), Room · Off · Temperature + · target (°C) (`device_unoccupied_heat_c`), Room · Off · Temperature − · target (°C) (`device_unoccupied_cool_c`), Heating · Away (°C) (`device_away_heat_c`), Cooling · Away (°C) (`device_away_cool_c`), Sleep · Temperature + · target (°C) (`device_sleep_heat_c`), Sleep · Temperature − · target (°C) (`device_sleep_cool_c`)

**Options / Choose rooms** (`setup_rooms`)

Rooms to monitor (`areas`)

**Options / Room · {area_name} · {room_index}/{room_count}** (`setup_room_sources`)

Windows (`windows`), Air quality and environmental sensors (`air_quality`), Temperature (`temperature`), Humidity (`humidity`), Devices (`climate_devices`), Window blinds, shades and shutters (`shades`)

**Options / General settings** (`setup_general`)

Weather entities (`weather_entities`), Outdoor air-quality sensors (`outdoor_sensors`), Weather warning sensors (optional) (`weather_warnings`), Room · Occupancy · sensor (`general_room_occupancy_sensors`), Home · Occupancy · Devices (`general_home_trackers`), Occupancy · Room · source (state) (`general_occupied_rooms_entity`), Occupancy · Room · source (attribute) (`general_occupied_rooms_attribute`), Sleep · Room · source (state) (`general_sleep_rooms_entity`), Sleep · Room · source (attribute) (`general_sleep_rooms_attribute`), Direct notification entities (`notify_entities`), Direct TTS media players (`media_players`), Direct TTS engine (`tts_engine`), AI · Select · source (`ai_conversation_agent`), Announcement language (`language`), Use mold indication instead of raw room RH (`use_mold_indicator`), Pollen · source · Select (`pollen_entities`), Announcement · Use Announcement Hub (`use_announcement_hub`), Home · Away · cooldown (min) (`general_away_cooldown_minutes`), Alert when windows remain open after everyone leaves (`away_open_window_alert`), People to notify after leaving (`away_windows_target_people`), Delivery channels for open-window alerts (`away_windows_delivery_channels`), Maximum outdoor AQI (`global_threshold_outdoor_aqi`), Maximum outdoor CO₂ (ppm) (`global_threshold_outdoor_co2`), Maximum outdoor PM2.5 (µg/m³) (`global_threshold_outdoor_pm25`), Maximum outdoor PM10 (µg/m³) (`global_threshold_outdoor_pm10`), Maximum outdoor VOC (µg/m³) (`global_threshold_outdoor_voc`), Maximum outdoor VOC (ppb) (`global_threshold_outdoor_voc_parts`), Outdoor NO₂ operational screen (µg/m³) (`global_threshold_outdoor_no2`), Outdoor O₃ operational screen (µg/m³) (`global_threshold_outdoor_o3`), Outdoor SO₂ operational screen (µg/m³) (`global_threshold_outdoor_so2`), Indoor AQI triggering ventilation (`global_threshold_indoor_aqi`), Indoor CO₂ triggering ventilation (ppm) (`global_threshold_indoor_co2`), Indoor PM2.5 triggering ventilation (µg/m³) (`global_threshold_indoor_pm25`), Indoor PM10 triggering ventilation (µg/m³) (`global_threshold_indoor_pm10`), Indoor VOC triggering ventilation (µg/m³) (`global_threshold_indoor_voc`), Indoor VOC triggering ventilation (ppb) (`global_threshold_indoor_voc_parts`), Indoor humidity triggering ventilation (%) (`global_threshold_indoor_humidity`), Minimum outdoor temperature (°C) (`global_threshold_min_outdoor_temp`), Maximum outdoor temperature (°C) (`global_threshold_max_outdoor_temp`), Maximum outdoor humidity (%) (`global_threshold_max_outdoor_humidity`), Maximum wind speed (km/h) (`global_threshold_max_wind_kmh`), Maximum age of any outdoor reading (minutes) (`global_threshold_max_age_minutes`), Mold indication triggering ventilation (estimated surface RH, %) (`global_threshold_indoor_mold`), Pollen scale: threshold treated as high (`pollen_high_from`), Pollen provider's maximum scale value (`pollen_max_scale`), Avoid window ventilation when pollen is high (opt in) (`pollen_avoid_ventilation`), Home Occupancy · Maximum tracker/count report age (min) (`general_source_stale_minutes`), Home Occupancy (`general_home_policy`), Sleep · Next alarm (`general_wake_alarm_entity`), Sleep · Minutes before alarm (`general_wake_lead_minutes_entity`), Wait for window opening (min) (`window_open_timeout_minutes`), Home occupancy · Validity policy (`general_source_freshness_mode`), Environment · Validity policy (`global_threshold_max_age_mode`), Wait before suggesting window closure (min) (`window_close_cooldown_minutes`), Quiet hours (`quiet_hours_enabled`), Quiet hours start (`quiet_hours_start`), Quiet hours end (`quiet_hours_end`), Residents to track (`general_proximity_trackers`), Occupied radius (m, 0 = off) (`general_occupied_radius_m`), Preparation radius (m, 0 = off) (`general_arrival_radius_m`), Show room smileys (`show_room_smileys`)

**Options / Choose a room** (`room_occupancy`)

Room (`room_occupancy_area`)

**Options / Room presence fallback · {area_name}** (`room_occupancy_sources`)

Selected occupancy/presence sensors (`room_occupancy_sensors`)

**Options / Choose rooms** (`choose_rooms`)

Rooms to monitor (`areas`)

**Options / Settings · {area_name}** (`room_settings`)

Windows (`windows`), Air quality and environmental sensors (`air_quality`), Temperature (`temperature`), Humidity (`humidity`), Devices (`climate_devices`), Window blinds, shades and shutters (`shades`), Occupancy/presence sensors in this room (`occupancy_sensors`)

**Options / Room settings** (`select_room`)

Room (`edit_room_area`)

**Options / Settings · {area_name}** (`edit_room`)

Windows (`windows`), Air quality and environmental sensors (`air_quality`), Temperature (`temperature`), Humidity (`humidity`), Devices (`climate_devices`), Window blinds, shades and shutters (`shades`), Occupancy/presence sensors in this room (`occupancy_sensors`), Interior door contacts (`door_sensors`)
