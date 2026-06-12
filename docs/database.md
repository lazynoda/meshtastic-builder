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
- `email`: recipient for build completion email.
- `device_id`: UI device id.
- `platformio_env`: allowlisted PlatformIO environment.
- `firmware_tag`: selected Meshtastic tag.
- `firmware_sha`: resolved commit SHA.
- `prefs_jsonc`: normalized submitted preferences.
- `prefs_hash`: SHA256 of normalized preferences.
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

This keeps concurrency conservative for the initial single-worker design.

## Expiry

Successful builds get:

```text
expires_at = finished_at + MB_ARTIFACT_TTL_DAYS
```

Downloads check expiry before serving. Cleanup deletes files and marks rows `expired`.

