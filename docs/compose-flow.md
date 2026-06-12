# Docker Compose Flow

This document is the handoff checklist for running the full service with Docker
Compose and testing the request-to-download flow.

## What Compose Starts

Prerequisites:

- Docker CLI with the Docker Compose plugin.
- Docker daemon access from the shell running `docker compose`.
- For real firmware builds, the `meshtastic-firmware-builder:local` image must
  exist in that same daemon.

`compose.yml` starts two services:

- `web`: serves the UI, API, downloads, and static files on port `8080`.
- `worker`: claims queued builds and runs the selected builder mode.

Both services share the named volume `app-data`, mounted at `/data`.

Runtime data in Compose:

- SQLite DB: `/data/meshtastic-builder.sqlite`
- artifacts: `/data/artifacts`
- local email outbox: `/data/mail/outbox.jsonl`

The worker mounts `/var/run/docker.sock` so it can create ephemeral firmware
builder containers. The web service does not need Docker socket access.

## Fast End-To-End Test With Fake Builds

Use this first when validating the web app, queue, worker, download links, and
email outbox without compiling Meshtastic firmware.

```bash
MB_BUILDER_MODE=fake docker compose -f compose.yml up --build
```

Open:

```text
http://localhost:8080
```

Submit a build from the UI. The worker should complete it quickly.

Read the local email outbox:

```bash
docker compose -f compose.yml exec web tail -n 20 /data/mail/outbox.jsonl
```

Open the download URL from the email body and verify that a ZIP downloads.

Stop the stack:

```bash
docker compose -f compose.yml down
```

Remove the persistent test data if you want a clean run:

```bash
docker compose -f compose.yml down -v
```

## Real Firmware Build Test

Build the Meshtastic firmware builder image in the same Docker daemon that will
run Compose:

```bash
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
```

Start the stack in real builder mode:

```bash
MB_BUILDER_MODE=docker docker compose -f compose.yml up --build
```

Refresh firmware tags:

```bash
docker compose -f compose.yml exec web python -m meshtastic_builder refresh-versions
```

Open:

```text
http://localhost:8080
```

Submit a build with:

- device: `LILYGO T-Beam`
- PlatformIO env: `tbeam`
- firmware tag: `v2.7.25.104df5f` if available and supported
- email: any valid address, for example `user@example.com`
- preferences: set the visible form controls; the page generates `userPrefs.jsonc`

The first real build can take several minutes because PlatformIO may download
dependencies for the selected historical tag.

Monitor logs:

```bash
docker compose -f compose.yml logs -f worker
```

Read the email outbox after the worker reports success:

```bash
docker compose -f compose.yml exec web tail -n 20 /data/mail/outbox.jsonl
```

Open the download URL from the email body. A successful real ZIP should include
firmware binaries plus `BUILD_INFO.txt` and `userPrefs.jsonc`.

## Real Build Test By API

This script submits a build and polls status without using browser UI:

```bash
python3 - <<'PY'
import json
import time
import urllib.request

base = "http://localhost:8080"
tag = "v2.7.25.104df5f"

prefs = urllib.request.urlopen(f"{base}/api/prefs-template?tag={tag}").read().decode()
payload = {
    "email": "user@example.com",
    "deviceId": "tbeam",
    "firmwareTag": tag,
    "prefsJsonc": prefs,
}

req = urllib.request.Request(
    f"{base}/api/builds",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
created = json.load(urllib.request.urlopen(req))
print("statusUrl:", created["statusUrl"])
print("downloadUrl:", created["downloadUrl"])

while True:
    status = json.load(urllib.request.urlopen(created["statusUrl"]))["build"]
    print(status["status"], status.get("error"))
    if status["status"] in {"succeeded", "failed", "expired"}:
        break
    time.sleep(30)
PY
```

If the final status is `succeeded`, open the printed `downloadUrl`.

## Remote Docker Daemon

The remote Docker path has been validated with:

```bash
export DOCKER_HOST=ssh://docker-host.example
```

Build the firmware builder image on the remote daemon:

```bash
DOCKER_HOST=ssh://docker-host.example \
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
```

Start Compose on that same remote daemon:

```bash
DOCKER_HOST=ssh://docker-host.example \
MB_BASE_URL=http://docker-host.example:8080 \
MB_BUILDER_MODE=docker \
docker compose -f compose.yml up --build
```

Open:

```text
http://docker-host.example:8080
```

If port `8080` is already in use on the remote host, publish the web service on
another host port. The current phone-test deployment uses `9990`:

```bash
DOCKER_HOST=ssh://docker-host.example \
MB_PORT=9990 \
MB_BASE_URL=http://docker-host.example:9990 \
MB_BUILDER_MODE=fake \
docker compose -f compose.yml up -d --build --force-recreate
```

Open:

```text
http://docker-host.example:9990
```

To switch that same deployment to real firmware builds:

```bash
DOCKER_HOST=ssh://docker-host.example \
MB_PORT=9990 \
MB_BASE_URL=http://docker-host.example:9990 \
MB_BUILDER_MODE=docker \
docker compose -f compose.yml up -d --build --force-recreate
```

Check the current remote stack:

```bash
DOCKER_HOST=ssh://docker-host.example docker compose -f compose.yml ps
DOCKER_HOST=ssh://docker-host.example docker compose -f compose.yml logs -f web worker
```

The worker should use:

- `MB_DOCKER_TRANSPORT=auto`
- `MB_DOCKER_NETWORK=bridge`

Inside Compose this means the worker talks to the mounted Docker socket and uses
bind mounts visible to the daemon. The `copy` transport is still available for a
worker running outside Docker against a remote `DOCKER_HOST`.

## Known Good Smoke Test

On 2026-06-12, this real remote-Docker smoke test passed:

- daemon: `ssh://docker-host.example`
- builder image: `meshtastic-firmware-builder:local`
- transport: `copy`
- network: `bridge`
- firmware tag: `v2.7.25.104df5f`
- firmware SHA: `104df5f9e590119e99b289b8331e0ea59940514c`
- device/env: `tbeam`
- artifact size: `11123897`
- artifact SHA256: `f3da99411de5f9cca1f30e3ecbe171623cf27fcc1fd364513f78ddcf10b25550`

The ZIP contained firmware `.bin`, `.factory.bin`, `.elf`, `.map`, LittleFS,
bootloader, partitions, `BUILD_INFO.txt`, and `userPrefs.jsonc`.

## Current Remote Phone-Test State

As of 2026-06-12:

- URL: `http://docker-host.example:9990`
- Mode: `fake`
- Remote daemon: `ssh://docker-host.example`
- Services: `meshtastic-builder-web-1`, `meshtastic-builder-worker-1`
- Validation: `/api/devices` returned all six enabled devices.
- Validation: a fake build for `heltec-mesh-node-t114` succeeded and produced a
  downloadable ZIP.

## Troubleshooting

Check Docker reachability from the worker image:

```bash
docker compose -f compose.yml exec worker python -m meshtastic_builder docker-status --timeout-seconds 20
```

If the builder image is missing, the worker will fail with an image lookup error.
Build `meshtastic-firmware-builder:local` in the same Docker daemon used by
Compose.

If historical tags fail while `MB_DOCKER_NETWORK=none`, use
`MB_DOCKER_NETWORK=bridge`. Historical tags can require PlatformIO dependencies
that were not prewarmed into the image.

If you need a fully offline or network-isolated builder, build a production image
with every supported tag/device dependency prewarmed and then switch the worker
to `MB_DOCKER_NETWORK=none`.
