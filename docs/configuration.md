# Configuration

Configuration is read from environment variables.

## Core

| Variable | Default | Description |
| --- | --- | --- |
| `MB_BASE_URL` | `http://localhost:8080` | Public base URL used in email links. |
| `MB_HOST` | `127.0.0.1` | HTTP bind host. |
| `MB_PORT` | `8080` | HTTP bind port. |
| `MB_DATA_DIR` | `./var` | Runtime data root. |
| `MB_DB_PATH` | `./var/meshtastic-builder.sqlite` | SQLite database path. |
| `MB_ARTIFACT_DIR` | `./var/artifacts` | ZIP artifact directory. |
| `MB_JOB_DIR` | `./var/jobs` | Temporary per-build job directory. |
| `MB_CACHE_DIR` | `./var/cache` | Cache directory for firmware metadata/templates. |
| `MB_MAIL_DIR` | `./var/mail` | Local outbox directory when SMTP is disabled. |

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
| `MB_BUILD_TIMEOUT_SECONDS` | `3600` | Per-build timeout. |
| `MB_STALE_RUNNING_SECONDS` | `7200` | Running jobs older than this are requeued. |
| `MB_ARTIFACT_TTL_DAYS` | `7` | Download availability after successful build. |

## Validation

| Variable | Default | Description |
| --- | --- | --- |
| `MB_MAX_PREFS_BYTES` | `65536` | Maximum submitted `userPrefs.jsonc` size. |

## Supported Devices

Supported devices are allowlisted in `data/devices.json`.

Current enabled IDs and PlatformIO environments:

| Device ID | Label | PlatformIO env | Family |
| --- | --- | --- | --- |
| `tbeam` | LILYGO T-Beam | `tbeam` | `esp32` |
| `heltec-v3` | Heltec LoRa 32 V3 | `heltec-v3` | `esp32-s3` |
| `heltec-mesh-node-t114` | Heltec Mesh Node T114 | `heltec-mesh-node-t114` | `nrf52` |
| `tracker-t1000-e` | Seeed SenseCAP T1000-E | `tracker-t1000-e` | `nrf52` |
| `heltec-wsl-v3` | Heltec Wireless Stick Lite V3 | `heltec-wsl-v3` | `esp32-s3` |
| `rak4631` | RAK4631 WisBlock | `rak4631` | `nrf52` |

Validate the allowlist against a Meshtastic firmware checkout after changing it:

```bash
python3 -m meshtastic_builder validate-devices /path/to/meshtastic/firmware
```

## SMTP

| Variable | Default | Description |
| --- | --- | --- |
| `MB_SMTP_HOST` | empty | If empty, emails are written to `outbox.jsonl`. |
| `MB_SMTP_PORT` | `587` | SMTP port. |
| `MB_SMTP_USERNAME` | empty | Optional SMTP username. |
| `MB_SMTP_PASSWORD` | empty | Optional SMTP password. |
| `MB_SMTP_FROM` | `Meshtastic Builder <no-reply@example.local>` | Sender address. |
| `MB_SMTP_TLS` | `1` | Enable STARTTLS. |
