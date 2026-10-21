# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-10-21

### Changed

- The node's long and short names are required and no longer prefilled. The
  form used to open with "Mi nodo Meshtastic" / "MESH", and many nodes were
  flashed with that name. Submitting without either name now marks the empty
  field, and `POST /api/builds` refuses a build whose merged `userPrefs.jsonc`
  lacks either name.

## [1.1.0] - 2026-10-21

### Firmwares

- Choose the firmware to build, not only the official one. The list lives in
  `data/firmwares.json` (id, name, GitHub URL, versioning) and ships with
  Meshtastic Oficial (default), [Jentastic](https://github.com/derpyspike/jentastic)
  and [Nodastic](https://github.com/lazynoda/meshtastic-firmware). See
  [Firmware Sources](docs/firmwares.md).
- Firmwares versioned by tags keep their own tag cache in SQLite, keyed by
  firmware and tag. Firmwares built from a branch show the version as `N/A`
  and always build the branch head; the commit is resolved at submit time and
  stored with the build.
- Version gates (patches, channel count, advanced options) compare the
  firmware's own version: the tag, or `version.properties` for branch
  firmwares.
- The `userPrefs.jsonc` template, `BUILD_INFO.txt` (`firmware`, `source`,
  `firmware_version`) and the ZIP name come from the chosen firmware.
- The builder image fetches other repositories into its upstream clone at
  build time. Adding a firmware needs no image rebuild.
- The firmware's GitHub link is shown under its selector.

### Devices

- The device list is read from the chosen firmware at the chosen version
  (`variants/**/platformio.ini`, the Web Flasher's rule) and cached per commit.
  Forks show their own boards (Jentastic adds the Pro-micro E28 2.4 GHz,
  2.4 GHz TCXO, SX1262 and NiceRF LR1121 variants), and older tags only offer
  the boards they had. A board the selected commit lacks is refused at submit
  time instead of failing to compile.
- Builds store the board's label, so the build page names fork-only boards.
- `sync-devices` regenerates `data/devices.json` from a firmware checkout,
  keeping existing ids and labels. Added LILYGO T-Connect Pro.
- nRF54L15 boards are excluded until they can be flashed from the ZIP
  ([#2](https://github.com/lazynoda/meshtastic-builder/issues/2)).

### Interface

- Section 1 is now "Firmware and device": firmware, version, then device.
- Every dropdown uses the same picker as the device selector. Short lists open
  as a menu; long ones can be filtered by typing.
- The running version is shown in the footer, linked to its release.
- The "Refresh tags" button is gone. Tags are refreshed by an operator
  (`refresh-versions`, all firmwares by default), for example from a daily
  timer; see [Operations](docs/operations.md#firmware-version-admin).

### Fixed

- Picking an option in a dropdown now closes it. The click also reached the
  surrounding label, which refocused the input and reopened the list.
- Tags deleted from a firmware's repository stop being offered after the next
  refresh. Their rows stay, unsupported, so old builds still resolve.
- nRF54 builds no longer die on the last step on arm64 hosts: PlatformIO's
  32-bit ARM `srec_cat` is replaced by Debian's native one when it cannot run.
- A build tool that cannot be started is reported as an infrastructure
  failure instead of an unknown one.

### Upgrading

- Rebuild the builder image (`docker build -f docker/builder.Dockerfile …`).
  Only the layers after the prewarm change: `srecord` is installed and
  `build-firmware` takes the repository URL as a fourth argument.
- The database migrates itself on start: `firmware_versions` is rebuilt with
  `(firmware_id, tag)` as key, and `build_requests` gains `firmware_id`,
  `firmware_version` and `device_label`. Back it up first.
- Rebuild and restart `web` and `worker`.

## [1.0.0] - 2026-10-21

First tagged release: the version running on
<https://builder.meshtastic.lazynoda.es>.

### Builds

- Web form that compiles custom Meshtastic firmware from the official
  [meshtastic/firmware](https://github.com/meshtastic/firmware) repository,
  with the user's settings baked into `userPrefs.jsonc`.
- Firmware versions taken from upstream's GitHub tags. The newest 20 are
  offered, and `refresh-versions`, `list-versions`, `set-supported` and
  `set-unsupported` manage the cache.
- 95 devices, the same set the Meshtastic Web Flasher offers, generated from
  the firmware's own variant metadata. The Pro-micro DIY is the default.
- SQLite queue and a worker that compiles each build in a throwaway Docker
  container with PlatformIO. The web process never touches Docker.
- Builder image with the firmware cloned and PlatformIO prewarmed for
  `heltec-v4` and `nrf52_promicro_diy_tcxo`. PlatformIO is pinned to 6.1.19,
  because 6.2.0 breaks ESP32-S3 builds.
- Builds against a remote or rootless Docker daemon (`copy` transport,
  `MB_DOCKER_SOCKET`).

### Settings

- Node long and short name, timezone with Peninsula and Canary Islands presets.
- LoRa region, modem preset, TX power, and manual LoRa parameters (bandwidth,
  spreading factor, coding rate, frequency slot). The form opens on the
  SFNarrow profile at 869.618 MHz.
- `ok_to_mqtt` and `ignore_mqtt`.
- Device role, rebroadcast mode, node info and telemetry intervals.
- Up to 8 channels (3 before firmware 2.8.0) with name, PSK, position
  precision and mute, reorderable by drag and drop.
- Bluetooth PIN, WiFi, MQTT broker, credentials, root topic and TLS.
- Position: GPS mode, broadcast interval, smart position, fixed position.
- Admin keys, managed mode and packet signature policy.
- Any other key in the selected tag's `userPrefs.jsonc`, through a free-form
  key/value section.
- Options and enum values are gated by firmware version. A live preview shows
  the exact `userPrefs.jsonc` that will be compiled, template defaults included.

### Firmware patches

- `userprefs-ext.patch` adds the advanced options to firmware older than 2.8.0,
  which reads them natively.
- `fixed-gps-nodedb.patch` (upstream PR #11825) makes fixed positions compile
  on 2.8.0. It is no longer applied from 2.8.1, which ships the fix.

### Results

- No account and no email. Every build gets a private permalink,
  `/build/<token>`. Old `/?build=<token>` links redirect to it.
- The ZIP holds only flashable files plus `FLASHING.txt` with the steps for its
  chip, `userPrefs.jsonc` and `BUILD_INFO.txt`. ESP32 builds ship the app image
  as `*-update.bin`, so the Web Flasher accepts the ZIP as is.
- ZIPs are kept for 7 days, then cleaned up automatically.
- A failed build shows a translated reason (patch failed, compile error,
  firmware too big, timeout…) and one quoted line of evidence, never the raw
  log, which holds the WiFi and MQTT passwords.

### Security

- Every value is shape-checked so that no setting can inject extra compiler
  flags. Enum, range and byte-length rules apply per key.
- Devices and PlatformIO environments come from an allowlist.
- Builder containers run with CPU, memory and PID limits.
- Per-IP rate limit on submissions. `MB_TRUST_PROXY` is used behind a reverse
  proxy.

### Operations

- Public `/api/health` endpoint with aggregate queue counts and no per-build
  data.
- `build-log`, `docker-status` and `validate-devices` admin commands.
- Spanish and English interface, an `/about` page, and the AGPL source link on
  every page.

### License

- AGPL-3.0-only. The firmware patches stay under GPL-3.0.

[1.1.1]: https://github.com/lazynoda/meshtastic-builder/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/lazynoda/meshtastic-builder/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/lazynoda/meshtastic-builder/releases/tag/v1.0.0
