# Worker And Builder

## Worker Lifecycle

The worker loop:

1. Requeues stale `running` jobs.
2. Claims the oldest `queued` job transactionally.
3. Creates a temporary job directory.
4. Writes `userPrefs.jsonc` and `BUILD_INFO.txt`.
5. Copies `docker/patches/userprefs-ext.patch` into the job input when the build
   has advanced options (see [Advanced Build Options](build-options.md)).
6. Runs either fake mode or Docker mode.
7. Stores the ZIP under `artifact_dir/<public_token>.zip`.
8. Records SHA256, size, finish time, and expiry time.
9. Periodically expires old artifacts.

Run once:

```bash
python3 -m meshtastic_builder.worker --once
```

Run continuously:

```bash
python3 -m meshtastic_builder.worker
```

## Fake Mode

Fake mode exercises the queue, ZIP creation, and status update without Docker:

```bash
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.worker --once
```

The fake ZIP contains:

- `BUILD_INFO.txt`
- `userPrefs.jsonc`
- `firmware-<env>.txt`

## Docker Mode

Docker mode supports two transports.

`bind` uses local bind mounts:

```bash
docker run --rm \
  --network <MB_DOCKER_NETWORK> \
  --cpus <MB_DOCKER_CPUS> \
  --memory <MB_DOCKER_MEMORY> \
  --pids-limit <MB_DOCKER_PIDS_LIMIT> \
  -v <job-input>:/work/input:ro \
  -v <job-output>:/work/output \
  <MB_BUILDER_IMAGE> \
  <firmware-tag> \
  <firmware-sha> \
  <platformio-env>
```

`copy` is for remote Docker daemons. It creates a container, copies local inputs into
the container with `docker cp`, starts the build, copies `/work/output` back, and
then removes the container.

`MB_DOCKER_TRANSPORT=auto` selects `copy` when `DOCKER_HOST` starts with
`ssh://`, `tcp://`, `http://`, or `https://`; otherwise it selects `bind`.

`auto` cannot detect one important case: a worker running *inside* a container
with the host Docker socket mounted. There `DOCKER_HOST` is unset, so `auto`
picks `bind`, but the daemon resolves the job paths on the host, not in the
worker container. `compose.yml` therefore pins `copy` for its worker.

`MB_DOCKER_NETWORK` defaults to `bridge` because users can select historical
firmware tags whose PlatformIO dependencies may differ from the image build ref.
Set it to `none` only for a prewarmed image that covers the supported tag/device
matrix.

Only the worker needs Docker access.

Builder containers still run with CPU, memory, PID, and network limits. The CPU
limit defaults to 4 because T114/nRF52 builds are CPU-bound and the old 2-CPU
cap left the compiler saturated for several minutes longer on the remote test
host.

The remote Docker path has been validated with `DOCKER_HOST=ssh://docker-host.example`,
`MB_DOCKER_TRANSPORT=copy`, and `MB_DOCKER_NETWORK=bridge`.

## Builder Image

`docker/builder.Dockerfile`:

- starts from Debian,
- installs Git, Python, PlatformIO CLI, Zip tools,
- clones `meshtastic/firmware` with tags and submodules,
- checks out `MESHTASTIC_REF` (`latest` = newest release tag at image build time),
- prewarms PlatformIO dependencies for `PREWARM_ENVS` against that ref,
- installs PlatformIO pinned to `PLATFORMIO_VERSION` (6.1.19),
- disables PlatformIO telemetry and upgrade checks,
- installs `docker/build_firmware.sh` as the entrypoint.

The default `PREWARM_ENVS` is `heltec-v4 nrf52_promicro_diy_tcxo`: the two most
requested devices, covering the ESP32-S3 and nRF52 toolchains. For production
images, pass a wider list explicitly:

```bash
docker build \
  --build-arg PREWARM_ENVS="tbeam heltec-v3 heltec-v4 heltec-mesh-node-t114 tracker-t1000-e heltec-wsl-v3 rak4631 nrf52_promicro_diy_tcxo" \
  -f docker/builder.Dockerfile \
  -t meshtastic-firmware-builder:local .
```

At runtime, the entrypoint checks out the requested SHA/tag directly inside
`/opt/firmware`. It only runs `git fetch` when that SHA is not already in the
image, which is what lets the image build firmware tags released after the
image itself; the fetch is best-effort, so a prewarmed offline image still
works for the tags it already has. Each Docker build runs in its own ephemeral container
filesystem, so this does not mutate shared service state, avoids copying the
firmware checkout per request, and lets PlatformIO reuse warmed `.pio` artifacts
from the single builder image when they are still valid.

PlatformIO stays pinned to 6.1.19 on purpose. Core 6.2.0 requires tool-scons
4.11 while pioarduino platform-espressif32 pins 4.8.1 and replaces the package
under the running SCons, so every ESP32-S3 hybrid build fails with
`No module named 'SCons.Tool.FortranCommon'`
([platform-espressif32#529](https://github.com/pioarduino/platform-espressif32/issues/529)).
Even on 6.1.19 the first run after a platform change can fail during that swap,
so both prewarm and the runtime entrypoint retry `pio run` once. Bump the pin
only after a real `heltec-v4` build passes.

Entrypoint contract:

```bash
build-firmware <firmware-tag> <firmware-sha> <platformio-env>
```

Inputs:

- `/work/input/userPrefs.jsonc`
- `/work/input/BUILD_INFO.txt`
- `/work/input/userprefs-ext.patch` (optional)

The optional patch is applied with `git apply` after checkout and before
`pio run`. Its presence is the only signal; the positional argument contract is
unchanged. A failed `git apply` exits 3 with `CODE_OPTIONS_PATCH_FAILED` so a
build can never compile with the defines present but unread.

Output:

- one ZIP under `/work/output/`

## Version Reproducibility

The API stores both:

- `firmware_tag`
- `firmware_sha`

The builder first tries to checkout the SHA and falls back to the tag. The ZIP includes metadata so the build can be audited later.
