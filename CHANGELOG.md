# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.0]: https://github.com/lazynoda/meshtastic-builder/releases/tag/v1.0.0
