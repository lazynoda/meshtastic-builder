# Meshtastic Builder

Web app and worker for requesting custom Meshtastic firmware builds.

The current implementation is intentionally dependency-light: it uses Python standard library modules, SQLite, vanilla HTML/CSS/JS, and a Docker-based firmware builder image. Users select a Meshtastic firmware tag, choose an allowed device, configure common `userPrefs.jsonc` fields through form controls, and submit. The page then shows a private build URL where progress is tracked and the ZIP can be downloaded for 7 days. No email address is asked for and none is sent.

A few settings that `userPrefs.jsonc` cannot express, such as `ok_to_mqtt` and
manual (non-preset) LoRa parameters, are offered as advanced build options.
Firmware 2.8.0 and newer reads those macros itself; older supported tags get a
small repo-controlled firmware patch. See
[docs/build-options.md](docs/build-options.md).

The UI is available in Spanish and English.

## Components

- `meshtastic_builder.app`: HTTP server and API.
- `meshtastic_builder.worker`: queue worker that claims builds and runs Docker.
- `meshtastic_builder.code_options`: advanced build option allowlist.
- `meshtastic_builder.cleanup`: expires old artifacts.
- `docker/builder.Dockerfile`: PlatformIO/Meshtastic build image.
- `docker/patches/userprefs-ext.patch`: adds the missing `USERPREFS_*` reads.
- `data/devices.json`: allowlisted devices and PlatformIO environments.
- `data/build_options.json`: allowlisted advanced build options.
- `static/`: the frontend, served as-is with no build step.

Full documentation lives in [docs/README.md](docs/README.md).

AI agent handoff notes live in [AGENTS.md](AGENTS.md).

## Quick Start

```bash
cp .env.example .env
python3 -m meshtastic_builder.db
python3 -m meshtastic_builder.app
```

In another terminal:

```bash
python3 -m meshtastic_builder.worker
```

For local queue testing without Docker:

```bash
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.worker --once
```

Build the firmware builder image:

```bash
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
```

Then start the web server at `http://localhost:8080`.

## Docker Compose Flow

Fast end-to-end test without compiling firmware:

```bash
MB_BUILDER_MODE=fake docker compose -f compose.yml up --build
```

Real firmware build flow:

```bash
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
MB_BUILDER_MODE=docker docker compose -f compose.yml up --build
```

Then open `http://localhost:8080`, submit a build, and watch worker logs:

```bash
docker compose -f compose.yml logs -f worker
```

Detailed Compose instructions, including remote Docker via
`DOCKER_HOST=ssh://docker-host.example`, are in
[docs/compose-flow.md](docs/compose-flow.md).

Current remote phone-test stack:

```text
http://docker-host.example:9990
```

It is intentionally running in `MB_BUILDER_MODE=fake` for quick UI, queue, and
download testing from a phone.

## Firmware Version Handling

The server fetches tags from `meshtastic/firmware` via the GitHub tags API and caches them in SQLite. A submitted build stores both the selected `firmware_tag` and the resolved `firmware_sha`. The worker compiles the SHA when possible and falls back to the tag only if the image does not have that SHA locally.

Historical tags can require different toolchains. The DB has a `supported` flag on `firmware_versions`; the API returns only supported versions by default. New caches auto-support only the latest `MB_AUTO_SUPPORT_LATEST_TAGS` tags unless that value is set to `0`.

The tag sync follows GitHub pagination up to `MB_GITHUB_MAX_TAG_PAGES`. If the network is unavailable, the app keeps serving versions already cached in SQLite.

## Build Security Model

- Device environments are allowlisted in `data/devices.json`.
- Firmware versions must be selected from cached GitHub tags.
- `userPrefs.jsonc` is parsed and normalized before storage.
- Unknown preference keys are rejected based on the selected tag's `userPrefs.jsonc` template.
- Advanced build options are allowlisted in `data/build_options.json`; the firmware patch is repo-controlled and never user-supplied.
- Public download paths use cryptographically random tokens, not DB ids.
- ZIPs expire after `MB_ARTIFACT_TTL_DAYS` days, are blocked at download time after expiry, and are deleted by cleanup.
- Submitted preference values are shape-checked before they reach the compiler, because the firmware build turns them into `-D` defines.
- The web process never invokes Docker; only the worker does.

## Artifact Contents

The builder ZIP includes compiled firmware files and `BUILD_INFO.txt` with tag, SHA, device environment, timestamp, and source URL metadata.

## Tests

```bash
python3 -m unittest discover -s tests
```
