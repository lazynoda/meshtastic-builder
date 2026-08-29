# API

All API responses are JSON unless noted.

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
frontend uses it to render controls and to hide the advanced panel on firmware
versions below `minFirmwareVersion`. See [Advanced Build Options](build-options.md).

## `GET /api/firmware-versions`

Returns supported cached firmware versions. If the cache is empty, the server attempts to fetch tags from GitHub.

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
  "email": "user@example.com",
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

- `email` must look like a valid email address.
- `deviceId` must be enabled in `data/devices.json`.
- `firmwareTag` must exist in `firmware_versions` and be supported.
- `prefsJsonc` must parse as JSONC.
- Preference keys must start with `USERPREFS_`.
- Preference keys must exist in the selected tag's `userPrefs.jsonc` template when keys can be extracted.
- Values must be scalar.
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
  "statusUrl": "http://localhost:8080/api/builds/private-random-token",
  "downloadUrl": "http://localhost:8080/download/private-random-token"
}
```

## `GET /api/builds/<token>`

Returns public build status. It never returns the submitter email or full `userPrefs.jsonc`.

## `GET /download/<token>`

Downloads the ZIP when:

- token exists,
- build status is `succeeded`,
- artifact exists on disk,
- artifact has not expired.

Expired artifacts return `410 Gone`. Missing/unavailable artifacts return `404` or `410` depending on state.

`HEAD /download/<token>` is supported for download metadata.
