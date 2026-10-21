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

The worker mounts the host Docker socket at `/var/run/docker.sock` so it can
create ephemeral firmware builder containers. The host side comes from
`MB_DOCKER_SOCKET` (default `/var/run/docker.sock`). With rootless Docker set it
to `/run/user/<uid>/docker.sock`: if the host path does not exist, the worker
fails to start after the next reboot with `error mounting "/var/run/docker.sock"
... not a directory`. The web service does not need Docker socket access.

## Fast End-To-End Test With Fake Builds

Use this first when validating the web app, queue, worker, and download links
without compiling Meshtastic firmware.

```bash
MB_BUILDER_MODE=fake docker compose -f compose.yml up --build
```

Open:

```text
http://localhost:8080
```

Submit a build from the UI. The page shows a private build URL; keep it open or
reopen it later. The worker should complete the build quickly.

Follow the worker:

```bash
docker compose -f compose.yml logs -f worker
```

Open the download link on the build page and verify that a ZIP downloads.

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
- firmware tag: `v2.8.0.47db0e3` if available and supported
- preferences: set the visible form controls; the page generates `userPrefs.jsonc`

The first real build can take several minutes because PlatformIO may download
dependencies for the selected historical tag.

Monitor logs:

```bash
docker compose -f compose.yml logs -f worker
```

When the worker reports success, open the download link on the build page. A
successful real ZIP should include firmware binaries plus `BUILD_INFO.txt` and
`userPrefs.jsonc`.

## Real Build Test By API

This script submits a build and polls status without using browser UI:

```bash
python3 - <<'PY'
import json
import time
import urllib.request

base = "http://localhost:8080"
tag = "v2.8.0.47db0e3"

prefs = urllib.request.urlopen(f"{base}/api/prefs-template?tag={tag}").read().decode()
payload = {
    "deviceId": "tbeam",
    "firmwareTag": tag,
    "prefsJsonc": prefs,
    # Optional. Exercises the userPrefs patch path; drop it for a plain build.
    "codeOptions": {
        "okToMqtt": True,
        "customLora": {"bandwidthKhz": 250, "spreadFactor": 11, "codingRate": 5},
    },
}

req = urllib.request.Request(
    f"{base}/api/builds",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
created = json.load(urllib.request.urlopen(req))
print("buildUrl:", created["buildUrl"])
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

When `codeOptions` is included, verify the patch actually took effect:

```bash
unzip -p <artifact>.zip BUILD_INFO.txt | grep code_options
unzip -p <artifact>.zip userPrefs.jsonc | grep -E 'USE_PRESET|OK_TO_MQTT|BANDWIDTH'
```

On firmware below 2.8.0 the build log should show `git apply` succeeding. On
2.8.0 and newer no patch is shipped at all; only the `-DUSERPREFS_...` flags in
the PlatformIO flag dump should appear.

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

- `MB_DOCKER_TRANSPORT=copy`
- `MB_DOCKER_NETWORK=bridge`

`copy` is the Compose default, and it is not optional there. The worker reaches
the host daemon through the mounted socket, so a bind mount of
`/data/jobs/<token>/input` would be resolved against the *host* filesystem,
where that path does not exist — the builder would start with an empty input
directory. `copy` streams the inputs into the container instead. Use `bind` only
when the worker and the daemon genuinely share a filesystem.

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

The worker image installs the Docker **client** from Debian's `docker-cli`
package. On Debian trixie the older `docker.io` package no longer ships
`/usr/bin/docker`, so a worker built from it fails every real build with
`[Errno 2] No such file or directory: 'docker'` while looking perfectly healthy
at startup.

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
