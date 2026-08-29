# Advanced Build Options

Most customization goes through `userPrefs.jsonc` (see
[userPrefs Support](userprefs-support.md)). A few useful settings have no
`USERPREFS_*` key at all because upstream `installDefaultConfig()` never reads
one. Those are exposed as **advanced build options** and require patching the
firmware source before compiling.

## How It Works

Upstream `bin/platformio-custom.py` turns *every* key in `userPrefs.jsonc` into
a `-D` compiler define. The missing half is the firmware reading them. A single
repo-controlled patch, `docker/patches/userprefs-ext.patch`, adds the missing
`#ifdef` blocks to `src/mesh/NodeDB.cpp`:

| Macro | Firmware field |
| --- | --- |
| `USERPREFS_CONFIG_LORA_OK_TO_MQTT` | `config.lora.config_ok_to_mqtt` |
| `USERPREFS_LORACONFIG_USE_PRESET` | `config.lora.use_preset` |
| `USERPREFS_LORACONFIG_BANDWIDTH` | `config.lora.bandwidth` |
| `USERPREFS_LORACONFIG_SPREAD_FACTOR` | `config.lora.spread_factor` |
| `USERPREFS_LORACONFIG_CODING_RATE` | `config.lora.coding_rate` |

The block is inserted after the existing `USERPREFS_LORACONFIG_MODEM_PRESET`
handling, so it overrides the unconditional `config_ok_to_mqtt = false` set
earlier in the same function.

Values then travel through the normal pipeline: the server injects them as
synthetic keys into the merged `userPrefs.jsonc`, which means they are covered
by `prefs_hash` and shipped inside the artifact ZIP for auditing.

Macro values are always emitted as **strings** (`"true"`, `"250"`) because
`platformio-custom.py` calls string methods on every value.

## Request Flow

1. The client posts an optional `codeOptions` object to `POST /api/builds`.
2. `meshtastic_builder.code_options` validates it against `data/build_options.json`.
3. Valid options are stored in `build_requests.code_options` and expanded into
   synthetic `USERPREFS_*` keys merged onto the tag template.
4. The worker copies the patch into the job input directory only when the build
   has code options.
5. `docker/build_firmware.sh` applies the patch after checkout and **before**
   `pio run`. If `git apply` fails, the build stops with exit code 3 and prints
   `CODE_OPTIONS_PATCH_FAILED`, which the worker turns into a readable error.

That ordering is the safety property: a build never silently compiles with the
defines present but nothing reading them.

## Available Options

| Option | Values | Notes |
| --- | --- | --- |
| `okToMqtt` | `true` / `false` | Sets `config.lora.config_ok_to_mqtt`. The UI checks it by default. |
| `customLora.bandwidthKhz` | `31`, `62`, `125`, `250`, `500` | Firmware bandwidth codes. `31` means 31.25 kHz and `62` means 62.5 kHz. |
| `customLora.spreadFactor` | `7`–`12` | |
| `customLora.codingRate` | `5`–`8` | 4/5 through 4/8. |
| `customLora.channelNum` | `0`–`255` | Frequency slot. `0` derives the slot from the channel name. Uses the pre-existing `USERPREFS_LORACONFIG_CHANNEL_NUM` key. |

Sending `customLora` also emits `USERPREFS_LORACONFIG_USE_PRESET: "false"`, so
the modem preset is ignored by the radio. The UI disables the preset selector
while manual LoRa configuration is on.

Validation is numeric only. Whether a given bandwidth or slot is *legal* in the
user's region is not checked; the UI shows a warning instead. Explicit MHz
frequency overrides are deliberately not offered because a slot index cannot
leave the region band plan while a raw frequency can.

## Version Support

`data/build_options.json` carries `minFirmwareVersion`. Submissions that request
code options for an older tag are rejected with a 400 before anything is queued,
and the frontend hides the panel for those versions.

The current floor is **2.6.4**: the patch was verified to apply cleanly on every
tag from `v2.6.4` to `v2.7.26` and to fail on `v2.2.x` and older. If a future tag
moves the surrounding code, `git apply` fails loudly and the patch needs a
refresh.

Re-check applicability across the supported tag range like this:

```bash
mkdir -p /tmp/tagtest/src/mesh && cd /tmp/tagtest && git init -q .
for tag in $(python3 -m meshtastic_builder list-versions | awk '{print $1}'); do
  curl -fsSL "https://raw.githubusercontent.com/meshtastic/firmware/$tag/src/mesh/NodeDB.cpp" \
    -o src/mesh/NodeDB.cpp || continue
  git apply --check /path/to/repo/docker/patches/userprefs-ext.patch \
    && echo "OK   $tag" || echo "FAIL $tag"
done
```

## Adding A New Option

1. Extend `docker/patches/userprefs-ext.patch` with another `#ifdef` block.
2. Re-verify the patch across the supported tag range and update
   `minFirmwareVersion` if the floor moves.
3. Add the option to `data/build_options.json`.
4. Teach `meshtastic_builder/code_options.py` to validate and expand it.
5. Add a control to `static/index.html` plus strings in `static/i18n.js`.
6. Add tests to `tests/test_code_options.py`.
