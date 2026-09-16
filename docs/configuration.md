# Configuration

Configuration is read from environment variables.

## Core

| Variable | Default | Description |
| --- | --- | --- |
| `MB_BASE_URL` | `http://localhost:8080` | Public base URL used in the build/status/download links returned at submit time. |
| `MB_HOST` | `127.0.0.1` | HTTP bind host. |
| `MB_PORT` | `8080` | HTTP bind port. |
| `MB_TRUST_PROXY` | `0` | Trust the first `X-Forwarded-For` hop for rate limiting. Enable only when the app is reachable exclusively through a reverse proxy, otherwise clients can spoof the header. |
| `MB_DATA_DIR` | `./var` | Runtime data root. |
| `MB_DB_PATH` | `./var/meshtastic-builder.sqlite` | SQLite database path. |
| `MB_ARTIFACT_DIR` | `./var/artifacts` | ZIP artifact directory. |
| `MB_JOB_DIR` | `./var/jobs` | Temporary per-build job directory. |
| `MB_CACHE_DIR` | `./var/cache` | Cache directory for firmware metadata/templates. |

## Firmware Metadata

| Variable | Default | Description |
| --- | --- | --- |
| `MB_GITHUB_TAGS_URL` | GitHub tags API for `meshtastic/firmware` | Tag source URL. |
| `MB_GITHUB_MAX_TAG_PAGES` | `20` | Maximum GitHub tag pages to follow. |
| `MB_AUTO_SUPPORT_LATEST_TAGS` | `20` | Number of newest tags to mark supported on first cache insert. Set `0` to auto-support all new tags. |
| `MB_RAW_USERPREFS_URL` | Raw GitHub URL template | Source for tag-specific `userPrefs.jsonc`. |

## Builder

| Variable | Default | Description |
| --- | --- | --- |
| `MB_BUILDER_MODE` | `docker` | `docker` or `fake`. |
| `MB_BUILDER_IMAGE` | `meshtastic-firmware-builder:local` | Docker image used by the worker. |
| `MB_DOCKER_BINARY` | `docker` | Docker CLI executable. |
| `MB_DOCKER_NETWORK` | `bridge` | Network mode for builder containers. Use `none` only with images prewarmed for the target tag/device set. |
| `MB_DOCKER_TRANSPORT` | `auto` | `auto`, `bind`, or `copy`. `auto` uses `copy` for remote `DOCKER_HOST` values such as `ssh://...` and `bind` otherwise. |
| `MB_DOCKER_CPUS` | `4` | CPU quota for firmware builder containers. T114/nRF52 builds are CPU-bound, so this default keeps a limit while avoiding the previous 2-CPU bottleneck. |
| `MB_DOCKER_MEMORY` | `4g` | Memory limit for firmware builder containers. |
| `MB_DOCKER_PIDS_LIMIT` | `512` | PID limit for firmware builder containers. |
| `MB_BUILD_TIMEOUT_SECONDS` | `3600` | Per-build timeout. |
| `MB_STALE_RUNNING_SECONDS` | `7200` | Running jobs older than this are requeued. |
| `MB_ARTIFACT_TTL_DAYS` | `7` | Download availability after successful build. |

## Validation

| Variable | Default | Description |
| --- | --- | --- |
| `MB_MAX_PREFS_BYTES` | `65536` | Maximum submitted `userPrefs.jsonc` size. |

## Advanced Build Options

Options that `userPrefs.jsonc` cannot express are allowlisted in
`data/build_options.json`, not in environment variables. See
[Advanced Build Options](build-options.md).

## Supported Devices

Supported devices are allowlisted in `data/devices.json`.

Current enabled IDs and PlatformIO environments:

| Device ID | Label | PlatformIO env | Family |
| --- | --- | --- | --- |
| `tbeam` | LILYGO T-Beam | `tbeam` | `esp32` |
| `heltec-v3` | Heltec LoRa 32 V3 | `heltec-v3` | `esp32-s3` |
| `heltec-v4` | Heltec LoRa 32 V4 | `heltec-v4` | `esp32-s3` |
| `heltec-mesh-node-t114` | Heltec Mesh Node T114 | `heltec-mesh-node-t114` | `nrf52` |
| `tracker-t1000-e` | Seeed SenseCAP T1000-E | `tracker-t1000-e` | `nrf52` |
| `heltec-wsl-v3` | Heltec Wireless Stick Lite V3 | `heltec-wsl-v3` | `esp32-s3` |
| `rak4631` | RAK4631 WisBlock | `rak4631` | `nrf52` |
| `nrf52-promicro-diy` | NRF52 Pro-micro DIY | `nrf52_promicro_diy_tcxo` | `nrf52` |

Validate the allowlist against a Meshtastic firmware checkout after changing it:

```bash
python3 -m meshtastic_builder validate-devices /path/to/meshtastic/firmware
```

## Notifications

There are none. The service never asks for an email address and never sends one.
A submitted build is addressable only through the private URL returned by
`POST /api/builds`.
