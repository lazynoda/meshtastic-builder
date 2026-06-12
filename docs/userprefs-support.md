# userPrefs Support

`userPrefs.jsonc` is a build-time Meshtastic mechanism. The firmware build reads
the file and turns active `USERPREFS_*` keys into compiler defines. Most values
are only applied on first boot or after a factory reset; they are not a runtime
configuration API.

This service intentionally exposes only a conservative subset in the web UI.
The backend still validates submitted JSONC because users can bypass the page.

## Supported In The UI

| Area | Keys | Notes |
| --- | --- | --- |
| Owner identity | `USERPREFS_CONFIG_OWNER_LONG_NAME`, `USERPREFS_CONFIG_OWNER_SHORT_NAME` | Short name is limited to 4 UTF-8 bytes. |
| LoRa region | `USERPREFS_CONFIG_LORA_REGION` | Values must match known `RegionCode` enum constants from Meshtastic protobufs. |
| Device role | `USERPREFS_CONFIG_DEVICE_ROLE` | Only roles accepted by firmware for `userPrefs`: `CLIENT`, `CLIENT_MUTE`, `CLIENT_HIDDEN`, `TRACKER`, `SENSOR`, `TAK`, `TAK_TRACKER`. |
| Modem preset | `USERPREFS_LORACONFIG_MODEM_PRESET` | Deprecated presets such as `LONG_SLOW` and `VERY_LONG_SLOW` are rejected. |
| Channels | `USERPREFS_CHANNELS_TO_WRITE`, `USERPREFS_CHANNEL_0_*`, `USERPREFS_CHANNEL_1_*`, `USERPREFS_CHANNEL_2_*` | Firmware userPrefs supports only the first 3 channels. Channel names are currently treated as plain strings; PSKs are entered as base64 and serialized to brace byte arrays. |
| MQTT broker | `USERPREFS_MQTT_ADDRESS`, `USERPREFS_MQTT_ENABLED` | Broker address is serialized with the extra single quotes expected by Meshtastic examples. |
| Remote admin key | `USERPREFS_USE_ADMIN_KEY_0` | Entered as base64 and serialized to a 32-byte brace array. |
| Timezone | `USERPREFS_TZ_STRING` | Must be a POSIX TZ string, not an IANA name. Examples: peninsula Spain `CET-1CEST,M3.5.0,M10.5.0/3`, Canary Islands `WET0WEST,M3.5.0/1,M10.5.0`. |

## Rejected Or Hidden

| Area | Status | Reason |
| --- | --- | --- |
| Router-like roles | Rejected | Firmware explicitly demotes `ROUTER`, `ROUTER_LATE`, and `LOST_AND_FOUND` from `USERPREFS_CONFIG_DEVICE_ROLE` to `CLIENT` for security. The UI does not offer them and the backend rejects them. |
| IANA timezone names | Rejected | Meshtastic passes `USERPREFS_TZ_STRING` to `TZ`/`tzset`; it expects POSIX TZ database strings, not names like `Europe/Madrid`. |
| Deprecated modem presets | Rejected | `LONG_SLOW` and `VERY_LONG_SLOW` are deprecated in current firmware. |
| OEM branding | Hidden for now | Valid build-time keys exist, but logo/image data needs stricter validation and a dedicated UI. |
| Firmware edition / event mode | Hidden for now | Event mode changes mesh behavior and applies congestion controls; it should not be a casual public toggle. |
| Ringtone / RTTTL | Hidden for now | Valid keys exist, but need format validation. |
| NodeInfo reply suppression / test logs / IPv6 | Hidden for now | Advanced or test-specific settings. |
| WiFi credentials | Hidden for now | Only useful for WiFi-capable devices and requires careful secret handling. |
| Fixed GPS position | Hidden for now | Valid for static deployments, but needs clear first-boot/factory-reset semantics in the UI. |

## Firmware Evidence

The analysis is based on the local firmware checkout at
`../firmware`:

- `userPrefs.jsonc` lists available build-time keys, mostly commented out.
- `userPrefs_guide.md` documents the intended userPrefs surface.
- `protobufs/meshtastic/config.proto` defines region, modem preset, and role enums.
- `src/mesh/NodeDB.cpp` rejects router-like roles from `USERPREFS_CONFIG_DEVICE_ROLE`.
- `src/main.cpp` applies `USERPREFS_TZ_STRING` through the POSIX `TZ` environment.

## Backend Validation

The backend validates:

- preference key names and tag-specific template membership,
- scalar-only values,
- allowed device roles,
- known LoRa regions,
- allowed non-deprecated modem presets,
- POSIX-looking timezone strings, rejecting obvious IANA names,
- channel count `1..3`,
- channel precision `0..32`.

