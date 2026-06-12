# Local Development

## Requirements

Minimum:

- Python 3.11+
- SQLite

For real firmware builds:

- Docker
- Docker Compose plugin if using `compose.yml`

For local fake builds, Docker is not required.

## Run The Web App

```bash
cp .env.example .env
python3 -m meshtastic_builder.db
python3 -m meshtastic_builder.app
```

Open:

```text
http://localhost:8080
```

## Run The Worker

Real Docker builder mode:

```bash
python3 -m meshtastic_builder.worker
```

Fake mode for local flow testing:

```bash
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.worker
```

Process at most one job:

```bash
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.worker --once
```

## Build The Firmware Builder Image

```bash
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
```

The image clones `meshtastic/firmware`, installs PlatformIO, fetches tags, and prewarms dependencies for the configured environments.

## Docker Compose

Fast end-to-end test without compiling firmware:

```bash
MB_BUILDER_MODE=fake docker compose -f compose.yml up --build
```

Real firmware build flow:

```bash
docker build -f docker/builder.Dockerfile -t meshtastic-firmware-builder:local .
MB_BUILDER_MODE=docker docker compose -f compose.yml up --build
```

For the full checklist, including remote Docker and API-based submission, see
[Docker Compose Flow](compose-flow.md).

Basic start command:

```bash
docker compose -f compose.yml up --build
```

The worker service mounts `/var/run/docker.sock` so it can create ephemeral builder containers. The web service does not need Docker socket access.

## tmux

If you want persistent local processes during development:

```bash
tmux new -s meshtastic-builder
```

Suggested panes:

```bash
python3 -m meshtastic_builder.app
MB_BUILDER_MODE=fake python3 -m meshtastic_builder.worker
tail -f var/mail/outbox.jsonl
```

Kill the session when done:

```bash
tmux kill-session -t meshtastic-builder
```
