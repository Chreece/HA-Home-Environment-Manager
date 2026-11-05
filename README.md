# Home Environment Manager

Home Environment Manager (HEM) is a Home Assistant custom integration for room
conditions, ventilation, air quality, moisture and optional automatic/PID device
control. It uses the sensors and devices configured in Home Assistant and
provides a compact room dashboard.

## Current version and branches

The current tested release is
[**v0.6.0b112**](https://github.com/Chreece/HA-Home-Environment-Manager/releases/tag/v0.6.0b112).
It includes per-device fan limits, simpler ordinary-room comfort settings,
reported-device activity colours, directional PID target cutoffs, and optional
30-second timed setpoints.

| Branch | Purpose |
| --- | --- |
| `main` | Latest working, validated integration |
| `dev` | Development and testing before promotion to `main` |

Install a published version from the
[Releases page](https://github.com/Chreece/HA-Home-Environment-Manager/releases).
Beta versions remain marked as prereleases.

## Install or update with HACS

Requires Home Assistant **2026.10.0 or newer**.

1. Add `https://github.com/Chreece/HA-Home-Environment-Manager` as a HACS custom
   repository with category **Integration**, if it is not already present.
2. Open **Home Environment Manager** in HACS. Enable **Show beta versions** in
   version selection and choose **v0.6.0b112**.
3. Download the update and restart Home Assistant.
4. For a new installation, open **Settings → Devices & services → Add integration**
   and choose **Home Environment Manager**. For an existing installation, use its
   existing integration entry and **Configure**.
5. Refresh the dashboard after an update to load the bundled card JavaScript.

The integration's current domain is **`environment_manager`**.

### Manual installation

Download the **Manual installation ZIP** attached to the published release and
extract its `custom_components/environment_manager` directory into Home
Assistant's configuration directory. Restart Home Assistant, then follow the
setup or update steps above.

The repository uses a flat integration layout for HACS. The release asset
already contains the `custom_components/environment_manager/` installation
path.

## Configuration

Select the rooms and their Home Assistant sensors and devices through the
integration's configuration. Device controllers expose their own control
settings, including supported fan minimum/maximum speed limits. Advanced ISO
7730 comfort inputs are optional and disabled by default for ordinary rooms.
The **Timed setpoints (30 s)** option is also off by default and can be enabled
per device.

For the full behavior changes in the current version, see the
[release notes](.github/releases/v0.6.0b112.md).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the `dev` → `main` workflow,
validation and release process. The
[validation workflow](https://github.com/Chreece/HA-Home-Environment-Manager/actions/workflows/validate.yml)
runs the existing runtime and browser regressions on both branches. Publication
is a separate, deliberate release action.

## License

[MIT](LICENSE).
