# Database

SQLite is used as the initial simple database and queue.

Schema lives in `meshtastic_builder.db`.

## `firmware_versions`

Stores cached Meshtastic firmware tags.

| Column | Purpose |
| --- | --- |
| `tag` | Git tag, primary key. |
| `sha` | Commit SHA resolved from the tag API. |
| `release_name` | Display name. |
| `published_at` | Reserved for richer release metadata. |
| `supported` | Whether the UI/API may accept this version. |
| `smoke_test_status` | `untested`, `tested`, etc. |
| `last_checked_at` | Last tag sync timestamp. |

## `build_requests`

Stores user requests and build lifecycle state.

Important columns:

- `public_token`: cryptographically random token used in status/download URLs.
- `device_id`: UI device id.
- `platformio_env`: allowlisted PlatformIO environment.
- `firmware_tag`: selected Meshtastic tag.
- `firmware_sha`: resolved commit SHA.
- `prefs_jsonc`: normalized submitted preferences, including any synthetic macros generated from `code_options`.
- `prefs_hash`: SHA256 of normalized preferences.
- `code_options`: JSON text of the requested advanced build options, or `NULL`. See [Advanced Build Options](build-options.md).
- `status`: `queued`, `running`, `succeeded`, `failed`, `expired`.
- `artifact_path`: ZIP path.
- `artifact_sha256`: ZIP digest.
- `artifact_size_bytes`: ZIP size.
- `expires_at`: download expiry timestamp.

## Queue Semantics

`claim_next_build` uses `BEGIN IMMEDIATE` to make claiming atomic in SQLite:

1. Select oldest `queued` row.
2. Update it to `running`.
3. Increment attempts.
4. Set `worker_id` and `started_at`.
5. Commit.

This keeps concurrency conservative for the initial single-worker design. The
claim itself is already race-free, so raising throughput is a matter of running
more workers (`docker compose up -d --scale worker=N`) rather than changing code.

## Migrations

`initialize_database` runs the schema script and then reconciles columns with
`ALTER TABLE`: it adds `code_options` when missing and drops the legacy `email`
column when present. Existing databases upgrade in place on the next start;
there is no migration tool.

## Expiry

Successful builds get:

```text
expires_at = finished_at + MB_ARTIFACT_TTL_DAYS
```

Downloads check expiry before serving. Cleanup deletes files and marks rows `expired`.

