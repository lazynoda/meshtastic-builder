# Roadmap

## Implemented

- Web form for device, firmware tag, and generated `userPrefs.jsonc` preferences.
- SQLite-backed request queue.
- Random public tokens for status/download URLs.
- GitHub tag sync with pagination.
- Admin commands to refresh, list, support, and unsupport firmware versions.
- Admin command to validate allowlisted devices against a local Meshtastic firmware checkout.
- Admin command to check Docker daemon reachability before real builds.
- Tag-specific `userPrefs.jsonc` template fetch/cache.
- Submitted `userPrefs.jsonc` overrides are merged onto the selected tag template.
- UI controls for common preferences: owner names, LoRa region, allowed role, preset, TX power, channels (8 from 2.8.0, with per-channel mute), node behaviour and telemetry intervals, MQTT broker plus credentials and root topic, POSIX TZ string, three admin keys, managed mode, and packet signature policy.
- Firmware-version gating of protobuf enum values in the UI.
- Worker process.
- Fake builder mode for fast local testing.
- Docker builder image for Meshtastic firmware.
- Real remote-Docker firmware smoke test for `v2.7.25.104df5f`/`tbeam`.
- ZIP artifact storage.
- Private build URL returned at submit time; no email is requested or sent.
- 7-day artifact expiry.
- Unit tests for core contracts.
- Advanced build options (`ok_to_mqtt`, manual LoRa config): native on firmware
  2.8.0 and newer, and through a repo-controlled firmware patch below it.
- Value hardening so no preference can inject extra compiler flags.
- Frontend restyled on the shared meshtastic.es design system, with Spanish and
  English UI and shareable `/?build=<token>` links.
- Reverse-proxy readiness (`MB_TRUST_PROXY`) and a sample Caddyfile.

## Next Milestones

1. Add automated smoke-test status for supported firmware tags and devices,
   including `git apply --check` of the userPrefs patch per tag.
2. Generate preference UI controls from a maintained schema.
3. Add persistent rate limiting.
4. Add production object storage support.
5. Add Postgres backend if queue concurrency or deployment scale requires it.

## Latest Local Validation

On 2026-09-12 (firmware 2.8.0 support, email removal):

- **Real Docker build passed on `v2.8.0.47db0e3` / `nrf52_promicro_diy_tcxo`**,
  Compose stack on `ssh://docker-host.example`, copy transport, network `bridge`.
  Queued to succeeded in 3 minutes, artifact 2 093 798 bytes, SHA256
  `5ee8808f854db3231c82a9732719fbc71e28494ff58ac8e162e115ca4d96ab27`, ZIP with
  `.uf2`, `.elf`, `.hex`, `BUILD_INFO.txt` and `userPrefs.jsonc`. The shipped
  `userPrefs.jsonc` carried `USERPREFS_CONFIG_LORA_CONFIG_OK_TO_MQTT` (the
  native name), the manual LoRa macros, TX power, rebroadcast mode and
  per-channel mute. The patch was provably not applied: it fails `git apply` on
  2.8.0, so shipping it would have exited 3 before `pio run`.
- Two deployment bugs found by that first real Compose build and fixed:
  the worker image needs Debian's `docker-cli` (trixie's `docker.io` ships no
  client binary), and the Compose worker must use `MB_DOCKER_TRANSPORT=copy`
  because `auto` picks `bind` against host paths the container does not share.
- Builder image rebuilt on the remote host (7.95 GB), prewarming `tbeam` and
  `nrf52_promicro_diy_tcxo`.
- `python3 -B -m unittest discover -s tests` passed with 68 tests.
- Verified against the upstream checkout at `v2.8.0.47db0e3`: `NodeDB.cpp`
  natively reads the LoRa macros and `USERPREFS_CONFIG_LORA_CONFIG_OK_TO_MQTT`,
  the LoRa keys are still absent from `userPrefs.jsonc`, channels 0–7 are
  supported, and `git apply --check` of `docker/patches/userprefs-ext.patch`
  **fails** on both 2.8.0 tags while still passing on `v2.7.26`.
- Fake-mode browser run with `playwright-cli`: no email field, version-gated
  controls and enums, 8-channel cap on 2.8.0, private build URL with copy, and
  a completed build downloadable from that URL.
- Not yet done: a real Docker build on 2.8.0. It needs a builder image rebuild
  so the image carries the new `git fetch --tags` entrypoint step and the 2.8.0
  tags.

On 2026-08-29:

- `python3 -B -m unittest discover -s tests` passed with 52 tests.
- `docker/patches/userprefs-ext.patch` verified with `git apply --check` against
  the 40 newest tags: clean on every tag from `v2.6.4` to `v2.7.26`, failing on
  `v2.2.x` and older. `minFirmwareVersion` set to `2.6.4` from that result.
- Builder image rebuilt on `ssh://docker-host.example` (8.06 GB).
- Real firmware build passed with advanced options enabled:
  - tag `v2.7.25.104df5f`, device/env `tbeam`, transport `copy`
  - options: `okToMqtt`, `customLora` bandwidth 125 / SF 9 / CR 6 / slot 20
  - log showed `Applied patch src/mesh/NodeDB.cpp cleanly.` and every expected
    `-DUSERPREFS_*` define
  - artifact 10.6 MB, SHA256 `8816e055f9e04446edf9c1edbbc460621a93599dd25b34b6aa1ac4aea261f876`
  - shipped `userPrefs.jsonc` contained all six synthetic macros as strings
- Failure path verified: an unapplicable patch exits 3 with
  `CODE_OPTIONS_PATCH_FAILED` before `pio run`.
- Fake-mode browser run verified the restyled UI, the ES/EN toggle, advanced
  option gating by firmware version, and `/?build=<token>` deep links.
- `MB_TRUST_PROXY=1` verified: rate limiting keys on the first `X-Forwarded-For`
  hop, and ignores the header when disabled.

On 2026-06-12:

- `python3 -B -m unittest discover -s tests` passed with 33 tests.
- `python3 -m meshtastic_builder refresh-versions` cached 326 firmware tags from GitHub.
- New tag caches auto-support only the latest `MB_AUTO_SUPPORT_LATEST_TAGS` tags by default.
- `python3 -m meshtastic_builder validate-devices /private/tmp/meshtastic-firmware-check` confirmed:
  - `tbeam`
  - `heltec-v3`
  - `heltec-mesh-node-t114`
  - `tracker-t1000-e`
  - `heltec-wsl-v3`
  - `rak4631`
- `docker compose -f compose.yml config` passed.
- `DOCKER_HOST=ssh://docker-host.example python3 -B -m meshtastic_builder docker-status --timeout-seconds 20` passed.
- Remote image build passed:
  - `DOCKER_HOST=ssh://docker-host.example docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .`
- Remote Docker smoke test passed with `MB_DOCKER_TRANSPORT=copy` and `MB_DOCKER_NETWORK=bridge`:
  - tag: `v2.7.25.104df5f`
  - SHA: `104df5f9e590119e99b289b8331e0ea59940514c`
  - device/env: `tbeam`
  - artifact size: `11123897`
  - artifact SHA256: `f3da99411de5f9cca1f30e3ecbe171623cf27fcc1fd364513f78ddcf10b25550`
  - ZIP files included firmware `.bin`, `.factory.bin`, `.elf`, `.map`, LittleFS, bootloader, partitions, `BUILD_INFO.txt`, and `userPrefs.jsonc`.
- Remote Compose phone-test deployment is running at `http://docker-host.example:9990`
  in `MB_BUILDER_MODE=fake`.
- Remote API `/api/devices` returned all six enabled devices.
- Remote fake build for `heltec-mesh-node-t114` succeeded and returned a
  downloadable ZIP.
