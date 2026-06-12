# Worker And Builder

## Worker Lifecycle

The worker loop:

1. Requeues stale `running` jobs.
2. Claims the oldest `queued` job transactionally.
3. Creates a temporary job directory.
4. Writes `userPrefs.jsonc` and `BUILD_INFO.txt`.
5. Runs either fake mode or Docker mode.
6. Stores the ZIP under `artifact_dir/<public_token>.zip`.
7. Records SHA256, size, finish time, and expiry time.
8. Sends a success or failure email.
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

Fake mode exercises the queue, ZIP creation, status update, and mailer without Docker:

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
- clones `meshtastic/firmware`,
- fetches tags,
- prewarms PlatformIO dependencies for `PREWARM_ENVS` during image build,
- installs `docker/build_firmware.sh` as the entrypoint.

The default `PREWARM_ENVS` is `tbeam heltec-mesh-node-t114` so the common ESP32
path and the T114/nRF52 path are both warmed in the single builder image. For
production images, pass a wider list explicitly:

```bash
docker build \
  --build-arg PREWARM_ENVS="tbeam heltec-v3 heltec-mesh-node-t114 tracker-t1000-e heltec-wsl-v3 rak4631" \
  -f docker/builder.Dockerfile \
  -t meshtastic-firmware-builder:local .
```

At runtime, the entrypoint checks out the requested SHA/tag directly inside
`/opt/firmware`. Each Docker build runs in its own ephemeral container
filesystem, so this does not mutate shared service state, avoids copying the
firmware checkout per request, and lets PlatformIO reuse warmed `.pio` artifacts
from the single builder image when they are still valid.

Entrypoint contract:

```bash
build-firmware <firmware-tag> <firmware-sha> <platformio-env>
```

Inputs:

- `/work/input/userPrefs.jsonc`
- `/work/input/BUILD_INFO.txt`

Output:

- one ZIP under `/work/output/`

## Version Reproducibility

The API stores both:

- `firmware_tag`
- `firmware_sha`

The builder first tries to checkout the SHA and falls back to the tag. The ZIP includes metadata so the build can be audited later.
