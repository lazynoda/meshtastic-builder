# Roadmap

## Implemented

- Web form for device, firmware tag, email, and generated `userPrefs.jsonc` preferences.
- SQLite-backed request queue.
- Random public tokens for status/download URLs.
- GitHub tag sync with pagination.
- Admin commands to refresh, list, support, and unsupport firmware versions.
- Admin command to validate allowlisted devices against a local Meshtastic firmware checkout.
- Admin command to check Docker daemon reachability before real builds.
- Tag-specific `userPrefs.jsonc` template fetch/cache.
- Submitted `userPrefs.jsonc` overrides are merged onto the selected tag template.
- UI controls for common preferences: owner names, LoRa region, allowed role, preset, channels, MQTT, POSIX TZ string, and remote admin key.
- Worker process.
- Fake builder mode for fast local testing.
- Docker builder image for Meshtastic firmware.
- Real remote-Docker firmware smoke test for `v2.7.25.104df5f`/`tbeam`.
- ZIP artifact storage.
- Email via SMTP or local outbox.
- 7-day artifact expiry.
- Unit tests for core contracts.

## Next Milestones

1. Add automated smoke-test status for supported firmware tags and devices.
2. Generate preference UI controls from a maintained schema.
3. Add persistent rate limiting.
4. Add production object storage support.
5. Add Postgres backend if queue concurrency or deployment scale requires it.

## Latest Local Validation

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
