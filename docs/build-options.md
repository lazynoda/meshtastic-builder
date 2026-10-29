# Advanced Build Options

Most customization goes through `userPrefs.jsonc` (see
[userPrefs Support](userprefs-support.md)). A few useful settings are missing
from `userPrefs.jsonc` entirely. Those are exposed as **advanced build
options**.

Firmware **2.8.0 and newer reads these macros natively** — the keys are simply
absent from the shipped `userPrefs.jsonc`, so the server injects them and
nothing else is needed. Older supported tags additionally need a small
repo-controlled patch, because their `installDefaultConfig()` never reads the
macros.

## How It Works

Upstream [`bin/platformio-custom.py`](https://github.com/meshtastic/firmware/blob/develop/bin/platformio-custom.py) turns *every* key in `userPrefs.jsonc` into
a `-D` compiler define. Below 2.8.0 the missing half is the firmware reading
them, so a single repo-controlled patch,
`docker/patches/userprefs-ext.patch`, adds the missing `#ifdef` blocks to
`src/mesh/NodeDB.cpp`:

| Macro | Firmware field |
| --- | --- |
| `USERPREFS_CONFIG_LORA_OK_TO_MQTT` | `config.lora.config_ok_to_mqtt` (upstream 2.8.0 calls it `USERPREFS_CONFIG_LORA_CONFIG_OK_TO_MQTT`) |
| `USERPREFS_LORACONFIG_USE_PRESET` | `config.lora.use_preset` |
| `USERPREFS_LORACONFIG_BANDWIDTH` | `config.lora.bandwidth` |
| `USERPREFS_LORACONFIG_SPREAD_FACTOR` | `config.lora.spread_factor` |
| `USERPREFS_LORACONFIG_CODING_RATE` | `config.lora.coding_rate` |

The block is inserted after the existing `USERPREFS_LORACONFIG_MODEM_PRESET`
handling, so it overrides the unconditional `config_ok_to_mqtt = false` set
earlier in the same function.

On 2.8.0 the same reads exist upstream, with one naming difference: the MQTT
flag is `USERPREFS_CONFIG_LORA_CONFIG_OK_TO_MQTT`. `data/build_options.json`
carries both names (`macro` and `nativeMacro`) and the server picks by version.
The LoRa macro names are identical, so only the MQTT flag switches.

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
4. The worker copies the patch into `input/patches/` only when the build has
   code options **and** the tag is below `nativeSinceFirmwareVersion`.
5. `docker/build_firmware.sh` applies every patch in `input/patches/`, in name
   order, after checkout and **before** `pio run`. If `git apply` fails, the
   build stops with exit code 3 and prints
   `MB_FAILURE code=patch_failed phase=patches detail=<patch file>`, which the
   worker turns into the `patch_failed` reason the page renders.

That ordering is the safety property: a build never silently compiles with the
defines present but nothing reading them.

## The Two Patches

There are two, for unrelated reasons and with opposite firmware windows. Both
are repo-controlled files under `docker/patches/`; users never supply patch
content, and both are described on `/about` because they change what ends up on
someone's radio.

| Patch | Applied when | Why |
| --- | --- | --- |
| `userprefs-ext.patch` | code options requested **and** tag `< 2.8.0` | `installDefaultConfig()` never reads the LoRa/MQTT macros there, so the defines would compile in and be ignored. |
| `fixed-gps-nodedb.patch` | prefs define `USERPREFS_FIXED_GPS` **and** tag `>= 2.8.0` | The 2.8 NodeDB restructuring left the fixed-position block using a removed `info` local, so the build fails to compile. |

### fixed-gps-nodedb.patch

Upstream commit `94bb21ecc`
([PR #10413](https://github.com/meshtastic/firmware/pull/10413), "2.8: NodeDB
shrink, decoupling, and restructuring") dropped

```cpp
meshtastic_NodeInfoLite *info = getOrCreateMeshNode(getNodeNum());
```

from `NodeDB::NodeDB()` but left the `#ifdef USERPREFS_FIXED_GPS` block using
`info`, so the build dies with:

```
src/mesh/NodeDB.cpp:705:27: error: 'info' was not declared in this scope
```

Upstream CI never hits it: their shipped `userPrefs.jsonc` keeps all four
`USERPREFS_FIXED_GPS*` keys commented out, so the block is never compiled there.
This service sets `USERPREFS_FIXED_GPS` whenever the user asks for a fixed
position (`static/app.js`), so every 2.8.x fixed-position build hits it.

The patch is upstream's own fix, taken verbatim from
[PR #11825](https://github.com/meshtastic/firmware/pull/11825), merged to the
firmware `develop` branch as `df47f95ff`. Nothing about it is
locally invented: keeping the compiled firmware as close to upstream as possible
is the point.

Tags below `2.8.0` still declare `info` and compile the block as shipped, so
fixed position works there with **no patch at all**. Only the patch is gated,
never the feature.

`fixedGpsPatch.fixedSinceFirmwareVersion` is `2.8.1`, the first release that
ships PR #11825; from that tag on the patch is no longer applied. Leaving it
unset made `git apply` fail and stopped every fixed-position build on 2.8.1.

Verified with `git apply --check`: applies on `v2.8.0.7239fe8` and
`v2.8.0.47db0e3`, refuses on `v2.7.26.54e0d8d` and `v2.8.1.8e6a88d` (which do
not need it).

## Available Options

| Option | Values | Notes |
| --- | --- | --- |
| `okToMqtt` | `true` / `false` | Sets `config.lora.config_ok_to_mqtt`. The UI checks it by default. |
| `customLora.bandwidthKhz` | `31`, `62`, `125`, `250`, `500` | Firmware bandwidth codes. `31` means 31.25 kHz and `62` means 62.5 kHz. |
| `customLora.spreadFactor` | `5`–`12` | |
| `customLora.codingRate` | `5`–`8` | Denominator of 4/N; the UI shows the bare number. |
| `customLora.channelNum` | `0`–`255` | Frequency slot. `0` derives the slot from the channel name. Uses the pre-existing `USERPREFS_LORACONFIG_CHANNEL_NUM` key. |
| `customLora.overrideFrequencyMhz` | `0`–`1000`, float | Transmit frequency in MHz. `0` keeps the region frequency. Emits `USERPREFS_LORACONFIG_OVERRIDE_FREQUENCY`. |

The defaults in `data/build_options.json` describe a narrow-band setup rather
than a copy of a modem preset: bandwidth `62` (62.5 kHz), spread factor `7`,
coding rate `5`, slot `0`, frequency `869.618` MHz. Every field is sent on each
submission, so changing a default changes what a user gets when they tick the
box without touching the controls.

From `nativeSinceFirmwareVersion` the MQTT forwarding flag is an ordinary key in
the tag's template, so the page writes it through `setPref` and it appears in the
preview like any other setting. Below that version it exists only because of the
NodeDB patch, so it stays a code option there and the preview lists it among the
injected macros.

Sending `customLora` also emits `USERPREFS_LORACONFIG_USE_PRESET: "false"`, so
the modem preset is ignored by the radio. The UI disables the preset selector
while manual LoRa configuration is on.

Validation is numeric only. Whether a given bandwidth or slot is *legal* in the
user's region is not checked; the UI shows a warning instead. Explicit MHz
frequency overrides are deliberately not offered because a slot index cannot
leave the region band plan while a raw frequency can.

## Version Support

`data/build_options.json` carries these version fences:

| Key | Meaning |
| --- | --- |
| `minFirmwareVersion` (`2.6.4`) | Below this the options are rejected with a 400 and the panel is hidden. |
| `nativeSinceFirmwareVersion` (`2.8.0`) | From this version the firmware reads the macros itself; no patch is shipped. |
| `eightChannelsSinceFirmwareVersion` (`2.8.0`) | From this version 8 channels are accepted instead of 3. |
| `longName` (`maxBytes` 24 from `sinceFirmwareVersion` 2.8.0, `legacyMaxBytes` 39 before) | Byte limit of the owner long name. Firmware 2.8.0 clamps it to 24 bytes on first boot and replaces a character cut in half with `?`. |
| `fixedGpsPatch.minFirmwareVersion` (`2.8.0`) | From this version a fixed position needs `fixed-gps-nodedb.patch`. |
| `fixedGpsPatch.fixedSinceFirmwareVersion` (`2.8.1`) | The first release carrying upstream PR #11825; from it, that patch is no longer applied. |

The patch applies cleanly from `v2.6.4` to `v2.7.26`, fails on `v2.2.x` and
older, and **also fails on `v2.8.0`** because upstream rewrote the surrounding
block — which is exactly why it is not shipped there. Never widen the patch
range past 2.8.0 without re-checking; a failed `git apply` stops the build.

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

1. Check whether current firmware already reads the macro. If it does, only
   `nativeMacro` handling is needed; otherwise extend
   `docker/patches/userprefs-ext.patch` with another `#ifdef` block.
2. Re-verify the patch across the supported tag range and update
   `minFirmwareVersion` if the floor moves.
3. Add the option to `data/build_options.json`.
4. Teach `meshtastic_builder/code_options.py` to validate and expand it.
5. Add a control to `static/index.html` plus strings in `static/i18n.js`.
6. Add tests to `tests/test_code_options.py`.
