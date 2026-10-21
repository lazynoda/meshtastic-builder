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
| Timezone | `USERPREFS_TZ_STRING` | Must be a POSIX TZ string, not an IANA name. Examples: peninsular Spain `CET-1CEST,M3.5.0,M10.5.0/3`, Canary Islands `WET0WEST,M3.5.0/1,M10.5.0`. |
| LoRa region | `USERPREFS_CONFIG_LORA_REGION` | Values must match known `RegionCode` enum constants from Meshtastic protobufs. |
| Modem preset | `USERPREFS_LORACONFIG_MODEM_PRESET` | Deprecated presets such as `LONG_SLOW` and `VERY_LONG_SLOW` are rejected. |
| LoRa TX power | `USERPREFS_LORACONFIG_TX_POWER` | `0`–`30` dBm. Empty or `0` means the region maximum. |
| Device role | `USERPREFS_CONFIG_DEVICE_ROLE` | Only roles accepted by firmware for `userPrefs`: `CLIENT`, `CLIENT_MUTE`, `CLIENT_HIDDEN`, `TRACKER`, `SENSOR`, `TAK`, `TAK_TRACKER`. |
| Node behaviour | `USERPREFS_CONFIG_DEVICE_REBROADCAST_MODE`, `USERPREFS_CONFIG_DEVICE_NODE_INFO_BROADCAST_SECS` | Rebroadcast mode is allowlisted. The node-info interval is floored at 3600 s, the same clamp the firmware applies. |
| Telemetry | `USERPREFS_CONFIG_DEVICE_TELEM_UPDATE_INTERVAL`, `USERPREFS_CONFIG_ENV_TELEM_UPDATE_INTERVAL`, `USERPREFS_CONFIG_ENVIRONMENT_MEASUREMENT_ENABLED` | Intervals in seconds. |
| Channels | `USERPREFS_CHANNELS_TO_WRITE`, `USERPREFS_CHANNEL_<n>_*` | 3 channels below 2.8.0, 8 from 2.8.0 (`eightChannelsSinceFirmwareVersion`). Per-channel mute (`_IS_MUTED`) is offered where the firmware supports it. PSKs are entered as base64 and serialized to brace byte arrays. |
| Bluetooth | `USERPREFS_FIXED_BLUETOOTH` | Fixed pairing PIN, `0`–`999999`. |
| WiFi | `USERPREFS_NETWORK_WIFI_ENABLED`, `USERPREFS_NETWORK_WIFI_SSID`, `USERPREFS_NETWORK_WIFI_PSK` | Only offered for devices with a WiFi radio, so an nRF52 build never carries WiFi macros. SSID up to 32 bytes, password up to 64. |
| MQTT broker | `USERPREFS_MQTT_ADDRESS`, `USERPREFS_MQTT_ENABLED`, `USERPREFS_MQTT_USERNAME`, `USERPREFS_MQTT_PASSWORD`, `USERPREFS_MQTT_ROOT_TOPIC`, `USERPREFS_MQTT_TLS_ENABLED`, `USERPREFS_MQTT_ENCRYPTION_ENABLED`, `USERPREFS_CONFIG_LORA_IGNORE_MQTT` | Broker address is serialized with the extra single quotes expected by Meshtastic examples. Lengths are capped at the nanopb buffer sizes: address and username 63 bytes, password and root topic 31 bytes. Credentials are compiled into the firmware in clear text; the UI says so. |
| Position | `USERPREFS_CONFIG_GPS_MODE`, `USERPREFS_CONFIG_GPS_UPDATE_INTERVAL`, `USERPREFS_CONFIG_POSITION_BROADCAST_INTERVAL`, `USERPREFS_CONFIG_SMART_POSITION_ENABLED`, `USERPREFS_BLOCK_POSITION_ON_EVENT_CHANNEL` | |
| Fixed position | `USERPREFS_FIXED_GPS`, `USERPREFS_FIXED_GPS_LAT`, `USERPREFS_FIXED_GPS_LON`, `USERPREFS_FIXED_GPS_ALT` | Plain decimal coordinates, range-checked, because the firmware multiplies them into an int32. On 2.8.x this needs a patch; see [Advanced Build Options](build-options.md#fixed-gps-nodedbpatch). |
| Admin keys | `USERPREFS_USE_ADMIN_KEY_0/1/2` | Entered as base64 and serialized to 32-byte brace arrays. |
| Managed mode | `USERPREFS_CONFIG_SECURITY_IS_MANAGED` | Only selectable once an admin key is set; firmware ignores it otherwise and warns. |
| Packet signature policy | `USERPREFS_CONFIG_SECURITY_PACKET_SIGNATURE_POLICY` | `COMPATIBLE`, `BALANCED`, `STRICT`. Firmware 2.8.0 and newer. |
| Anything else | Any other key in the tag's `userPrefs.jsonc` | Set from the *Other config values* section. The server validates the value shape like every other key. |

### Enum Values Change Between Versions

Protobuf enum identifiers are not stable across firmware tags, and an unknown
identifier fails at compile time rather than at submit time. The frontend
therefore tags each region and preset with the version that introduced it and
offers only the ones the selected tag knows:

| Value | Since |
| --- | --- |
| `LITE_FAST`, `LITE_SLOW`, `NARROW_FAST`, `NARROW_SLOW`, `EU_866`, `EU_874`, `EU_917`, `EU_N_868`, `ITU1_2M` | 2.7.23 |
| `ITU2_2M`, `ITU3_2M` (replacing `ITU23_2M`, which existed only in 2.7.23–2.7.24) | 2.7.25 |
| `TINY_FAST`, `TINY_SLOW`, `MEDIUM_TURBO`, `ITU1_70CM`, `ITU2_70CM`, `ITU3_70CM`, `ITU2_125CM`, packet signature policy | 2.8.0 |

The backend allowlist is the superset of all supported tags; version gating is
the frontend's job.

## Beyond userPrefs

Some settings are missing from `userPrefs.jsonc` even though the build would
happily define the macro: `ok_to_mqtt` and the manual (non-preset) LoRa
parameters. Those are offered separately as advanced build options, native on
2.8.0 and patched below it. See [Advanced Build Options](build-options.md).

## Rejected

| Area | Reason |
| --- | --- |
| Router-like roles | Firmware explicitly demotes `ROUTER`, `ROUTER_LATE`, and `LOST_AND_FOUND` from `USERPREFS_CONFIG_DEVICE_ROLE` to `CLIENT` for security. The UI does not offer them and the backend rejects them. |
| IANA timezone names | Meshtastic passes `USERPREFS_TZ_STRING` to `TZ`/`tzset`; it expects POSIX TZ strings, not names like `Europe/Madrid`. |
| Deprecated modem presets | `LONG_SLOW` and `VERY_LONG_SLOW` are deprecated in current firmware. |

OEM branding, event mode, the ringtone, NodeInfo reply suppression and the other
template keys have no dedicated control. They can still be set from *Other
config values*.

## Firmware Evidence

The analysis is based on a checkout of
[meshtastic/firmware](https://github.com/meshtastic/firmware), last verified
against `v2.8.0.47db0e3`:

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
- channel count `1..3` (`1..8` from 2.8.0),
- channel precision `0..32`,
- enum membership for roles, regions, presets, rebroadcast mode and signature policy,
- numeric ranges for TX power and the broadcast/telemetry intervals,
- byte lengths for the MQTT strings,
- the shape of every value, so nothing can inject extra compiler flags.

Merged values are always serialized as JSON strings. Upstream
`bin/platformio-custom.py` calls string methods on every value, so a submitted
JSON number or boolean would otherwise abort the firmware build with an
AttributeError instead of a useful message. Null values are rejected.

That same script decides quoting: values starting with `meshtastic_` or `{`, and
anything numeric or boolean, are passed into `-D` flags **unquoted**; everything
else is quoted. The backend therefore constrains value shape for every key, not
just the ones with an allowlist. See [Security Model](security.md).

