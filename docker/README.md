# Firmware Builder Image

Build:

```bash
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
```

The image clones `meshtastic/firmware`, fetches tags, installs PlatformIO, and prewarms packages for the environments in `PREWARM_ENVS`.

The Dockerfile default prewarms only `tbeam`. For broader validation or
production images, pass:

```bash
docker build \
  --build-arg PREWARM_ENVS="tbeam heltec-v3 rak4631" \
  -f docker/builder.Dockerfile \
  -t meshtastic-firmware-builder:local .
```

Runtime contract:

```bash
docker run --rm \
  -v "$PWD/var/jobs/example/input:/work/input:ro" \
  -v "$PWD/var/jobs/example/output:/work/output" \
  meshtastic-firmware-builder:local \
  v2.7.15.567b8ea \
  567b8ea \
  tbeam
```

The input directory must contain `userPrefs.jsonc` and `BUILD_INFO.txt`. The output directory receives a ZIP.

When the Docker daemon is remote, use the application worker's copy transport
instead of bind mounts:

```bash
DOCKER_HOST=ssh://docker-host.example \
MB_DOCKER_TRANSPORT=copy \
MB_DOCKER_NETWORK=bridge \
python3 -m meshtastic_builder.worker --once
```
