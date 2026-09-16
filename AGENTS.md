# AGENTS.md

Guidance for AI agents working on this repository.

## Project Objective

This project is a Meshtastic custom firmware build service.

End state:

- A user opens a web page.
- The user selects a supported Meshtastic device.
- The user selects a Meshtastic firmware version from `meshtastic/firmware` Git tags.
- The user edits `userPrefs.jsonc` through form controls.
- The user optionally enables advanced build options that `userPrefs.jsonc`
  cannot express.
- The user submits the build request. No email address is requested.
- The page shows a private build URL (`/?build=<token>`) and polls it.
- The request is stored in a simple database.
- A separate worker claims queued requests one by one.
- The worker runs each build in an ephemeral Docker container.
- The container builds Meshtastic firmware with PlatformIO.
- The worker stores a ZIP artifact.
- The user downloads it from the same private URL.
- ZIP download links are random-token based and expire after 7 days.

## Current Implementation

The implementation is intentionally dependency-light:

- Python standard library HTTP server.
- SQLite database.
- Vanilla HTML/CSS/JS frontend, no build step, Spanish and English.
- Docker image for the real Meshtastic/PlatformIO build.
- Fake builder mode for fast local verification without Docker.

Core modules:

- `meshtastic_builder.app`: web server, API, static files, downloads.
- `meshtastic_builder.submissions`: validates and creates build requests.
- `meshtastic_builder.code_options`: advanced build option allowlist and macro expansion.
- `meshtastic_builder.db`: schema, queue state transitions, artifact metadata.
- `meshtastic_builder.firmware`: GitHub tag sync and userPrefs template cache.
- `meshtastic_builder.worker`: queue loop and build lifecycle.
- `meshtastic_builder.builder`: fake builder and Docker builder invocation.
- `meshtastic_builder.cleanup`: artifact expiry and deletion.

Submitted `userPrefs.jsonc` is validated as JSONC, checked against the selected
tag's template keys, and merged onto that template before storage. This prevents
partial override payloads from producing firmware builds with missing
`USERPREFS_*` macros.

Settings missing from `userPrefs.jsonc` (`ok_to_mqtt`, manual non-preset LoRa
parameters) are exposed as advanced build options. They are allowlisted in
`data/build_options.json` and expanded into server-injected synthetic macros.

Firmware `2.8.0` and newer reads those macros natively, so no patch is shipped
there; the MQTT flag is named `USERPREFS_CONFIG_LORA_CONFIG_OK_TO_MQTT` upstream
(`nativeMacro` in the allowlist). Below `2.8.0` a repo-controlled patch,
`docker/patches/userprefs-ext.patch`, is applied inside the builder container
before `pio run`. That patch applies from `v2.6.4` to `v2.7.26` and **fails on
`v2.8.0`** — which is why the version switch exists, not an accident. Older tags
are rejected via `minFirmwareVersion`. Full details in `docs/build-options.md`.
Users never supply patch content.

Preference *values* are shape-checked in `meshtastic_builder/jsonc.py` because
`bin/platformio-custom.py` emits `meshtastic_`- and `{`-prefixed values into
`-D` flags unquoted. Do not relax those regexes.

Current enabled device IDs and PlatformIO environments:

- `tbeam` -> `tbeam`
- `heltec-v3` -> `heltec-v3`
- `heltec-mesh-node-t114` -> `heltec-mesh-node-t114`
- `tracker-t1000-e` -> `tracker-t1000-e`
- `heltec-wsl-v3` -> `heltec-wsl-v3`
- `rak4631` -> `rak4631`
- `nrf52-promicro-diy` -> `nrf52_promicro_diy_tcxo`

The Pro-micro DIY variant is the TCXO release env. Its `-inkhud` and
`-easypromicro` siblings are `board_level = extra` and are not exposed.

Full project documentation is in `docs/`.

## Commands

Run tests:

```bash
python3 -B -m unittest discover -s tests
```

Initialize the database:

```bash
python3 -m meshtastic_builder.db
```

Run the web app:

```bash
python3 -m meshtastic_builder.app
```

Run one fake worker job:

```bash
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.worker --once
```

Build the real firmware builder image:

```bash
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
```

The Dockerfile default prewarms `tbeam` and `heltec-mesh-node-t114` so the
common ESP32 and T114/nRF52 paths are both warmed in the single builder image.
Use `--build-arg PREWARM_ENVS="tbeam heltec-v3 heltec-mesh-node-t114 tracker-t1000-e heltec-wsl-v3 rak4631 nrf52_promicro_diy_tcxo"`
when validating a wider production image.

Run the Compose stack in fast fake mode:

```bash
MB_BUILDER_MODE=fake docker compose -f compose.yml up --build
```

Run the Compose stack with real firmware builds:

```bash
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
MB_BUILDER_MODE=docker docker compose -f compose.yml up --build
```

Then open `http://localhost:8080`, submit a build, and follow the worker:

```bash
docker compose -f compose.yml logs -f worker
```

The complete operational checklist is in `docs/compose-flow.md`.

Current remote Compose handoff state as of 2026-09-12:

- Remote Docker daemon: `ssh://docker-host.example`
- Public test URL for phone/browser: `http://docker-host.example:9990`
- Stack mode: `MB_BUILDER_MODE=docker` (real firmware builds)
- Published port: `9990 -> web:8080`
- Services are named `meshtastic-builder-web-1` and `meshtastic-builder-worker-1`
- Builder image `meshtastic-firmware-builder:local` rebuilt on that host,
  7.95 GB, prewarmed for `tbeam` and `nrf52_promicro_diy_tcxo`
- The worker has completed a real build for `nrf52_promicro_diy_tcxo` at
  `v2.8.0.47db0e3` in about 3 minutes

The stack is left running in this mode. The tag cache only refreshes when it is
empty or when the client asks for it, so after redeploying onto an existing
volume the newest tags appear only after one `?refresh=1` (the page's
"Actualizar tags" button).

Check the running remote stack:

```bash
DOCKER_HOST=ssh://docker-host.example docker compose -f compose.yml ps
DOCKER_HOST=ssh://docker-host.example docker compose -f compose.yml logs -f web worker
```

Recreate the current phone-test stack:

```bash
DOCKER_HOST=ssh://docker-host.example \
MB_PORT=9990 \
MB_BASE_URL=http://docker-host.example:9990 \
MB_BUILDER_MODE=fake \
docker compose -f compose.yml up -d --build --force-recreate
```

Switch the same stack to real firmware builds:

```bash
DOCKER_HOST=ssh://docker-host.example \
MB_PORT=9990 \
MB_BASE_URL=http://docker-host.example:9990 \
MB_BUILDER_MODE=docker \
docker compose -f compose.yml up -d --build --force-recreate
```

Check Docker reachability before a real build:

```bash
python3 -m meshtastic_builder docker-status --timeout-seconds 10
```

Remote Docker over SSH has been validated with:

```bash
DOCKER_HOST=ssh://docker-host.example python3 -m meshtastic_builder docker-status --timeout-seconds 20
```

For remote Docker daemons, leave `MB_DOCKER_TRANSPORT=auto` or set
`MB_DOCKER_TRANSPORT=copy`. Bind mounts only work when the Docker daemon can see
the same filesystem paths as the worker.

`MB_DOCKER_NETWORK` defaults to `bridge` so historical tags can download missing
PlatformIO dependencies. Use `none` only when the image is prewarmed for the
exact supported tag/device matrix.

Builder containers keep resource limits. `MB_DOCKER_CPUS` defaults to `4`
because real T114/nRF52 builds are CPU-bound; lower it on small hosts if needed.

A real remote-Docker smoke test has passed for:

- `DOCKER_HOST=ssh://docker-host.example`
- `MB_DOCKER_TRANSPORT=copy`
- `MB_DOCKER_NETWORK=bridge`
- firmware tag `v2.7.25.104df5f`
- firmware SHA `104df5f9e590119e99b289b8331e0ea59940514c`
- device/env `tbeam`

The resulting ZIP contained firmware `.bin`, `.factory.bin`, `.elf`, `.map`,
LittleFS, bootloader, partitions, `BUILD_INFO.txt`, and `userPrefs.jsonc`.

Re-validated on 2026-08-29 with advanced build options enabled
(`okToMqtt` plus `customLora` bandwidth 125 / SF 9 / CR 6 / slot 20). The build
log showed `Applied patch src/mesh/NodeDB.cpp cleanly.`, the PlatformIO flag dump
included every `-DUSERPREFS_LORACONFIG_*` and `-DUSERPREFS_CONFIG_LORA_OK_TO_MQTT`
define, and the patched `NodeDB.cpp` compiled without errors. Artifact was
10.6 MB, SHA256
`8816e055f9e04446edf9c1edbbc460621a93599dd25b34b6aa1ac4aea261f876`.

The failure path was verified separately by feeding the builder a deliberately
unapplicable patch: it exited 3 with `CODE_OPTIONS_PATCH_FAILED` before `pio run`.

Note the builder image had to be rebuilt from scratch on that host
(about one hour, 8.06 GB). It prewarms against `master`, so older tags still
download extra PlatformIO packages at build time and therefore need
`MB_DOCKER_NETWORK=bridge`.

Run cleanup:

```bash
python3 -m meshtastic_builder.cleanup
```

## Runtime Data

Default runtime data lives in `var/` and is ignored by Git:

- SQLite DB: `var/meshtastic-builder.sqlite`
- Artifacts: `var/artifacts/*.zip`
- Job workdirs: `var/jobs/<token>/`
- UserPrefs cache: `var/cache/userprefs/*.jsonc`

Do not commit runtime data, ZIPs, caches, or generated `__pycache__`.

## Testing Expectations

Before finishing any code change, run:

```bash
python3 -B -m unittest discover -s tests
```

Existing tests cover:

- JSONC parsing and normalization.
- Preference key extraction.
- Public token validation.
- GitHub tag pagination.
- Automatic support policy for latest firmware tags.
- Submission validation.
- Worker fake-mode flow.
- Artifact ZIP creation.
- Artifact expiry and deletion.
- Docker command construction.
- Docker daemon diagnostics.

If changing queue semantics, builder behavior, validation, or downloads, add or update tests.

Fake mode is useful but does not prove real Meshtastic builds. A production-ready change must eventually be validated with a real Docker build.

## High-Priority Gaps

These are the current main unfinished items:

1. Add automated smoke-test status for firmware tags and devices, including
   `git apply --check` of `docker/patches/userprefs-ext.patch` per tag.
2. Add persistent rate limiting before public deployment.
3. Consider S3/MinIO or another persistent artifact store for production.

Deployment to `https://builder.meshtastic.es` is done manually by the user on a
VPS. Keep the app proxy-ready (`MB_TRUST_PROXY`, `Caddyfile.example`) but do not
attempt to provision DNS, TLS, or backups from here.

## Meshtastic Notes

Use primary sources when validating build behavior:

- Official docs: `https://meshtastic.org/docs/development/firmware/build/`
- Firmware repo: `https://github.com/meshtastic/firmware`
- PlatformIO docs: `https://docs.platformio.org/`

Meshtastic environments are not all in the root `platformio.ini`; the root config includes files under `variants/**`. Do not validate device names by checking only the root file.

The selected firmware tag must be resolved to and stored with a commit SHA. The worker should build the SHA when possible.

Historical tags may require different dependencies or may not build with the current Docker image. Do not assume every tag is supported.

## Compose Deployment Notes

Two things are easy to get wrong when the worker runs inside Compose:

- The worker image needs Debian's `docker-cli` package. `docker.io` on trixie
  ships only the daemon, so the worker starts fine and then fails every build
  with `[Errno 2] No such file or directory: 'docker'`.
- The worker must use `MB_DOCKER_TRANSPORT=copy`, which `compose.yml` now pins.
  `auto` resolves to `bind` because `DOCKER_HOST` is unset inside the container,
  but the daemon resolves `/data/jobs/<token>/input` against the host
  filesystem, where it does not exist, and the builder would start with an empty
  input directory.

## Security Constraints

Keep these invariants:

- The web process must not invoke Docker.
- The worker is the only component that runs Docker.
- Device IDs must map to allowlisted PlatformIO environments.
- Users must not submit arbitrary PlatformIO environments or Git refs.
- Users must not supply firmware patches; only allowlisted option flags.
- Synthetic `USERPREFS_*` macros must be merged after user overrides so
  `prefsJsonc` cannot set them.
- A failed `git apply` must fail the build before `pio run`, never continue.
- Public URLs must use cryptographically random tokens, not DB IDs.
- Public status endpoints must not expose the full `userPrefs.jsonc`.
- Preference values must stay shape-checked; they reach the compiler as `-D` flags.
- Downloads must fail after expiry.
- Docker input mount should remain read-only.
- Builder containers should keep CPU, memory, PID, and network limits unless there is a documented reason to change them.

## Style And Scope

Prefer small, testable changes.

This codebase currently avoids external Python dependencies. Do not introduce a framework or package manager unless the benefit is clear and documented.

If introducing dependencies, update:

- `README.md`
- `docs/local-development.md`
- `docs/configuration.md` if config changes
- tests

Keep documentation in `docs/` synchronized with behavior.

## Known Environment Notes

The user's Codex/Desktop environment may expose a reduced PATH in some sessions. In newer unrestricted sessions, the full PATH includes:

- `~/.nvm/versions/node/v24.15.0/bin`
- `/opt/homebrew/bin`

Useful tools observed:

- `ctx7`
- `npm`
- `npx`
- `tmux`
- `docker`
- Docker Compose plugin, installed with Homebrew as `docker-compose` 5.1.4 and
  exposed through Docker CLI via `~/.docker/config.json`

If a tool appears missing, check `printenv PATH` before assuming it is not installed.

Docker note: in one unrestricted session, Docker CLI was present but the active context pointed to `ssh://other-host.example` and `docker-status` timed out. A later session validated Docker at `ssh://docker-host.example`. Verify Docker before starting any long build.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
