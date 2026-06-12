# AGENTS.md

Guidance for AI agents working on this repository.

## Project Objective

This project is a Meshtastic custom firmware build service.

End state:

- A user opens a web page.
- The user selects a supported Meshtastic device.
- The user selects a Meshtastic firmware version from `meshtastic/firmware` Git tags.
- The user edits `userPrefs.jsonc`.
- The user enters an email address and submits a build request.
- The request is stored in a simple database.
- A separate worker claims queued requests one by one.
- The worker runs each build in an ephemeral Docker container.
- The container builds Meshtastic firmware with PlatformIO.
- The worker stores a ZIP artifact.
- The user receives an email with a private download link.
- ZIP download links are random-token based and expire after 7 days.

## Current Implementation

The implementation is intentionally dependency-light:

- Python standard library HTTP server.
- SQLite database.
- Vanilla HTML/CSS/JS frontend.
- SMTP or local JSONL outbox.
- Docker image for the real Meshtastic/PlatformIO build.
- Fake builder mode for fast local verification without Docker.

Core modules:

- `meshtastic_builder.app`: web server, API, static files, downloads.
- `meshtastic_builder.submissions`: validates and creates build requests.
- `meshtastic_builder.db`: schema, queue state transitions, artifact metadata.
- `meshtastic_builder.firmware`: GitHub tag sync and userPrefs template cache.
- `meshtastic_builder.worker`: queue loop and build lifecycle.
- `meshtastic_builder.builder`: fake builder and Docker builder invocation.
- `meshtastic_builder.mailer`: SMTP/outbox delivery.
- `meshtastic_builder.cleanup`: artifact expiry and deletion.

Submitted `userPrefs.jsonc` is validated as JSONC, checked against the selected
tag's template keys, and merged onto that template before storage. This prevents
partial override payloads from producing firmware builds with missing
`USERPREFS_*` macros.

Current enabled device IDs and PlatformIO environments:

- `tbeam` -> `tbeam`
- `heltec-v3` -> `heltec-v3`
- `heltec-mesh-node-t114` -> `heltec-mesh-node-t114`
- `tracker-t1000-e` -> `tracker-t1000-e`
- `heltec-wsl-v3` -> `heltec-wsl-v3`
- `rak4631` -> `rak4631`

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

The Dockerfile default prewarms only `tbeam` to keep local/CI iteration bounded.
Use `--build-arg PREWARM_ENVS="tbeam heltec-v3 rak4631"` when validating a wider
production image.

Run the Compose stack in fast fake mode:

```bash
MB_BUILDER_MODE=fake docker compose -f compose.yml up --build
```

Run the Compose stack with real firmware builds:

```bash
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
MB_BUILDER_MODE=docker docker compose -f compose.yml up --build
```

Then open `http://localhost:8080`, submit a build, follow the worker, and inspect
the local email outbox:

```bash
docker compose -f compose.yml logs -f worker
docker compose -f compose.yml exec web tail -n 20 /data/mail/outbox.jsonl
```

The complete operational checklist is in `docs/compose-flow.md`.

Current remote Compose handoff state as of 2026-06-12:

- Remote Docker daemon: `ssh://docker-host.example`
- Public test URL for phone/browser: `http://docker-host.example:9990`
- Stack mode: `MB_BUILDER_MODE=fake`
- Published port: `9990 -> web:8080`
- Services are named `meshtastic-builder-web-1` and `meshtastic-builder-worker-1`
- The worker has processed a fake build successfully for `heltec-mesh-node-t114`

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

A real remote-Docker smoke test has passed for:

- `DOCKER_HOST=ssh://docker-host.example`
- `MB_DOCKER_TRANSPORT=copy`
- `MB_DOCKER_NETWORK=bridge`
- firmware tag `v2.7.25.104df5f`
- firmware SHA `104df5f9e590119e99b289b8331e0ea59940514c`
- device/env `tbeam`

The resulting ZIP contained firmware `.bin`, `.factory.bin`, `.elf`, `.map`,
LittleFS, bootloader, partitions, `BUILD_INFO.txt`, and `userPrefs.jsonc`.

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
- Local email outbox: `var/mail/outbox.jsonl`

Do not commit runtime data, ZIPs, caches, or generated `__pycache__`.

## Testing Expectations

Before finishing any code change, run:

```bash
python3 -B -m unittest discover -s tests
```

Existing tests cover:

- JSONC parsing and normalization.
- Preference key extraction.
- Email and token validation.
- GitHub tag pagination.
- Automatic support policy for latest firmware tags.
- Submission validation.
- Worker fake-mode flow.
- Artifact ZIP creation.
- Outbox email writing.
- Artifact expiry and deletion.
- Docker command construction.
- Docker daemon diagnostics.

If changing queue semantics, builder behavior, validation, downloads, or email delivery, add or update tests.

Fake mode is useful but does not prove real Meshtastic builds. A production-ready change must eventually be validated with a real Docker build.

## High-Priority Gaps

These are the current main unfinished items:

1. Add automated smoke-test status for firmware tags and devices.
2. Add persistent rate limiting before public deployment.
3. Configure and verify real SMTP or Mailpit in compose.
4. Consider S3/MinIO or another persistent artifact store for production.

## Meshtastic Notes

Use primary sources when validating build behavior:

- Official docs: `https://meshtastic.org/docs/development/firmware/build/`
- Firmware repo: `https://github.com/meshtastic/firmware`
- PlatformIO docs: `https://docs.platformio.org/`

Meshtastic environments are not all in the root `platformio.ini`; the root config includes files under `variants/**`. Do not validate device names by checking only the root file.

The selected firmware tag must be resolved to and stored with a commit SHA. The worker should build the SHA when possible.

Historical tags may require different dependencies or may not build with the current Docker image. Do not assume every tag is supported.

## Security Constraints

Keep these invariants:

- The web process must not invoke Docker.
- The worker is the only component that runs Docker.
- Device IDs must map to allowlisted PlatformIO environments.
- Users must not submit arbitrary PlatformIO environments or Git refs.
- Public URLs must use cryptographically random tokens, not DB IDs.
- Public status endpoints must not expose email addresses or full `userPrefs.jsonc`.
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
