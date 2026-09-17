# API

All API responses are JSON unless noted.

## `GET /api/health`

Public liveness probe, also served at `GET /health`. Both accept `HEAD`.

It queries the database rather than only answering from the process, so an
unreachable or corrupt SQLite file is reported instead of hidden. `200` with
`"status": "ok"` when the queue is readable, `503` with `"status": "error"` when
it is not. The failure body names no path, driver or query, because the endpoint
is unauthenticated.

Counts are aggregate only. Nothing here is tied to an individual request: no
tokens, no preferences, no device or firmware choices.

```json
{
  "status": "ok",
  "builds": {
    "total": 42,
    "byStatus": {"expired": 4, "failed": 1, "queued": 2, "running": 1, "succeeded": 34},
    "queued": 2,
    "running": 1,
    "lastRequestedAt": "2026-09-17T04:31:25+00:00"
  }
}
```

`lastRequestedAt` is `null` until the first build is requested.

## `GET /api/devices`

Returns enabled devices from `data/devices.json`.

Response:

```json
{
  "devices": [
    {
      "id": "tbeam",
      "label": "LILYGO T-Beam",
      "platformioEnv": "tbeam",
      "family": "esp32"
    }
  ]
}
```

## `GET /api/build-options`

Returns the advanced build option allowlist from `data/build_options.json`. The
frontend uses it to render controls and to gate behaviour by firmware version:

- `minFirmwareVersion`: below this, the advanced panel is hidden and
  `codeOptions` submissions are rejected.
- `nativeSinceFirmwareVersion`: from this version the firmware reads the macros
  itself, so no source patch is shipped and `okToMqtt` uses `nativeMacro`.
- `eightChannelsSinceFirmwareVersion`: from this version 8 channels are
  accepted instead of 3.
- `artifactTtlDays`: added by the server from `MB_ARTIFACT_TTL_DAYS`, not from
  the JSON file. The page prints it next to the submit button and in the result
  panel, so the retention copy cannot drift from what cleanup actually enforces.

See [Advanced Build Options](build-options.md).

## `GET /api/firmware-versions`

Returns supported cached firmware versions, newest first. If the cache is empty, the server attempts to fetch tags from GitHub.

Optional query:

- `refresh=1`: force tag refresh.

Response:

```json
{
  "versions": [
    {
      "tag": "v2.x.y",
      "sha": "commit-sha",
      "release_name": "v2.x.y",
      "published_at": null,
      "supported": 1,
      "smoke_test_status": "untested",
      "last_checked_at": "2026-06-12T00:00:00+00:00"
    }
  ]
}
```

## `GET /api/prefs-template?tag=<tag>`

Returns the `userPrefs.jsonc` template for a supported tag as plain text.

The server uses a local cache under `var/cache/userprefs/`. If fetching from GitHub fails, it falls back to `data/userPrefs.fallback.jsonc`.

## `POST /api/builds`

Creates a queued build request.

Request:

```json
{
  "deviceId": "tbeam",
  "firmwareTag": "v2.x.y",
  "prefsJsonc": "{\"USERPREFS_CONFIG_OWNER_SHORT_NAME\":\"ABC\"}",
  "codeOptions": {
    "okToMqtt": true,
    "customLora": {
      "bandwidthKhz": 250,
      "spreadFactor": 11,
      "codingRate": 5,
      "channelNum": 0
    }
  }
}
```

`codeOptions` is optional. Both sub-options are independent, missing
`customLora` fields fall back to their documented defaults, and the whole object
is rejected for firmware older than `minFirmwareVersion`. See
[Advanced Build Options](build-options.md).

Validation:

- `deviceId` must be enabled in `data/devices.json`.
- `firmwareTag` must exist in `firmware_versions` and be supported.
- `prefsJsonc` must parse as JSONC.
- Preference keys must start with `USERPREFS_`.
- Preference keys must exist in the selected tag's `userPrefs.jsonc` template when keys can be extracted.
- Values must be scalar.
- Values are shape-checked so they cannot inject extra compiler flags: values
  starting with `meshtastic_` must be plain identifiers, values starting with
  `{` must be byte arrays, other strings may not contain quotes, backslashes,
  `$`, backticks or control characters.
- Enum, range and byte-length rules apply per key (roles, regions, presets,
  rebroadcast mode, signature policy, TX power, intervals, MQTT fields).
- `USERPREFS_CHANNEL_<n>_*` keys are accepted for `n` below the channel cap
  even when the tag template does not list them.
- `codeOptions` keys and values must match `data/build_options.json`.

Synthetic macros generated from `codeOptions` are merged last, so they cannot be
set or overridden through `prefsJsonc`.

The submitted preferences are merged onto the selected tag's cached
`userPrefs.jsonc` template before storage. This allows partial overrides while
still giving the firmware build a complete preference file with all expected
`USERPREFS_*` definitions.

Response:

```json
{
  "build": {
    "token": "private-random-token",
    "status": "queued",
    "deviceId": "tbeam",
    "platformioEnv": "tbeam",
    "firmwareTag": "v2.x.y",
    "firmwareSha": "commit-sha",
    "codeOptions": null,
    "attempts": 0,
    "createdAt": "2026-06-12T00:00:00+00:00",
    "startedAt": null,
    "finishedAt": null,
    "expiresAt": null,
    "artifactSha256": null,
    "artifactSizeBytes": null,
    "error": null
  },
  "buildUrl": "http://localhost:8080/?build=private-random-token",
  "statusUrl": "http://localhost:8080/api/builds/private-random-token",
  "downloadUrl": "http://localhost:8080/download/private-random-token"
}
```

`buildUrl` is the page the user is given. No notification is sent, so this URL
is the only way back to the build.

## `GET /api/builds/<token>`

Returns public build status. It never returns the full `userPrefs.jsonc`.

## `GET /download/<token>`

Downloads the ZIP when:

- token exists,
- build status is `succeeded`,
- artifact exists on disk,
- artifact has not expired.

Expired artifacts return `410 Gone`. Missing/unavailable artifacts return `404` or `410` depending on state.

`HEAD /download/<token>` is supported for download metadata.
