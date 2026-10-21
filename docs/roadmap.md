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
- Builds against a remote Docker daemon (`DOCKER_HOST=ssh://...`).
- ZIP artifact storage.
- Private build URL returned at submit time; no email is requested or sent.
- 7-day artifact expiry.
- Unit tests for core contracts.
- Advanced build options (`ok_to_mqtt`, manual LoRa config): native on firmware
  2.8.0 and newer, and through a repo-controlled firmware patch below it.
- Value hardening so no preference can inject extra compiler flags.
- Frontend restyled on the shared [meshtastic.es](https://meshtastic.es) design system, with Spanish and
  English UI and shareable `/?build=<token>` links.
- Reverse-proxy readiness (`MB_TRUST_PROXY`) and a sample Caddyfile.

## Next Milestones

1. Bring build times back down with ccache (see below).
2. Add automated smoke-test status for supported firmware tags and devices,
   including `git apply --check` of every `docker/patches/*.patch` per tag.
3. Generate preference UI controls from a maintained schema.
4. Add persistent rate limiting.
5. Add production object storage support.
6. Add Postgres backend if queue concurrency or deployment scale requires it.

## Planned: ccache

Every build is a full compile — about 167s for `nrf52_promicro_diy_tcxo` on a tag
the image already has checked out, and up to 46 min for a cold ESP32 env. A
PlatformIO build cache got that to 43s, and was reverted because it
silently shipped ZIPs with nothing flashable in them. `docs/worker-and-builder.md`
has the full mechanism; the short version is that `build_cache_dir` is a SCons
`CacheDir`, SCons skips a target's post-actions on a cache hit, and Meshtastic
writes the `.uf2` and the `.factory.bin` inside post-actions as side effects
rather than declared targets.

ccache avoids that entirely: it caches below SCons, so every target is still
genuinely built and every post-action still runs. It also keys on preprocessed
output, so a changed `userPrefs.jsonc` correctly misses the cache while the
unchanged framework and libdeps objects hit it.

Two ways to wire it in, and the choice matters:

- **Wrap the toolchain binaries inside the builder image.** Preferred. Keeps the
  firmware untouched, which matters because we only ever ship upstream-accepted
  patches. Needs checking how PlatformIO resolves the compiler for both the nRF52
  (`arm-none-eabi-gcc`) and ESP32 (`xtensa-*-gcc`, `riscv32-*-gcc`) toolchains —
  whether it invokes a bare name through `env["ENV"]["PATH"]` or an absolute path
  into the platform package — since that decides whether a PATH shim is enough or
  the package binaries have to be replaced with wrappers.
- **An `extra_scripts` entry doing `env.Replace(CC="ccache " + env["CC"], ...)`.**
  Simpler, but it is a firmware-side file, so it would mean carrying a patch that
  upstream never accepted. Rejected on those grounds unless the first approach
  turns out to be impossible.

Whichever way, the cache has to live in a named Docker volume (the daemon is
remote, so a host path does not resolve), needs `CCACHE_DIR` pointed at it, and
wants a `CCACHE_MAXSIZE` — the reverted PlatformIO cache had nothing pruning it.

Acceptance is not "builds got faster". It is: a second identical build still
produces a `.uf2` for nRF52 and a `.factory.bin` for ESP32. The test in
`tests/test_builder.py` that forbids `PLATFORMIO_BUILD_CACHE_DIR` should stay;
ccache is a different mechanism and must not reopen that door.
