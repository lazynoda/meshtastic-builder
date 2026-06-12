# Operations

## Start

Local:

```bash
python3 -m meshtastic_builder.app
python3 -m meshtastic_builder.worker
```

Compose:

```bash
docker compose -f compose.yml up --build
```

For a step-by-step Compose smoke test, including fake mode, real firmware
builds, outbox checks, and remote Docker, see [Docker Compose Flow](compose-flow.md).

## Logs

The current implementation logs to stdout.

Worker logs include:

- worker id,
- claimed token,
- platformio env,
- firmware tag,
- success/failure state.

Build logs are truncated and stored in `build_requests.build_log`.

## Email

If `MB_SMTP_HOST` is unset, emails are written to:

```text
var/mail/outbox.jsonl
```

Each line is a JSON object with `created_at`, `to`, `subject`, and `body`.

## Cleanup

Run manually:

```bash
python3 -m meshtastic_builder.cleanup
```

The worker also runs cleanup periodically.

## Firmware Version Admin

Refresh the local firmware tag cache from GitHub:

```bash
python3 -m meshtastic_builder refresh-versions
```

List supported versions:

```bash
python3 -m meshtastic_builder list-versions
```

List all cached versions, including unsupported:

```bash
python3 -m meshtastic_builder list-versions --all
```

Mark a tag supported or unsupported:

```bash
python3 -m meshtastic_builder set-supported v2.7.25.104df5f
python3 -m meshtastic_builder set-unsupported v2.7.25.104df5f
```

Validate enabled devices against a local checkout of `meshtastic/firmware`:

```bash
python3 -m meshtastic_builder validate-devices /path/to/meshtastic/firmware
```

This checks `variants/**` files, not only the root `platformio.ini`.

Check whether Docker is reachable before attempting a real build:

```bash
python3 -m meshtastic_builder docker-status --timeout-seconds 10
```

If this command times out or fails, do not start a firmware build. Fix the Docker context or daemon first.

## Backups

Back up:

- SQLite database,
- artifact directory if downloads must survive process moves,
- mail outbox if SMTP is disabled.

Do not back up temporary job directories.

## Production Notes

- Set `MB_BASE_URL` to the public HTTPS origin.
- Configure SMTP.
- Build and pin a known-good builder image.
- Decide which firmware tags are supported.
- Run at least one real Docker build smoke test before accepting users.
- Consider moving from SQLite to Postgres if multiple web/worker instances are needed.
