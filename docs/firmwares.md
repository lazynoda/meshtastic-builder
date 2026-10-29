# Firmware Sources

Users pick the firmware to build from a list kept in `data/firmwares.json`.
Every entry is a GitHub repository that builds the same way as upstream
Meshtastic: PlatformIO environments, `userPrefs.jsonc` at the root and
`version.properties` with the firmware version.

```json
{
  "default": "meshtastic",
  "firmwares": [
    {
      "id": "meshtastic",
      "name": "Meshtastic Oficial",
      "url": "https://github.com/meshtastic/firmware",
      "versioning": "tags"
    },
    {
      "id": "nodastic",
      "name": "Nodastic",
      "url": "https://github.com/lazynoda/meshtastic-firmware",
      "versioning": "branch",
      "branch": "nodastic"
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `default` | Id selected when the page opens, and assumed by API clients that send no `firmwareId`. |
| `id` | Stable id stored with every build. Lowercase letters, digits and `-`, up to 32 characters. Never rename it once builds exist. |
| `name` | Label shown in the selector. |
| `url` | `https://github.com/<owner>/<repo>`. Shown under the selector, and the repository the builder fetches from. |
| `versioning` | `tags`: users pick one of the repository's tags. `branch`: no releases, every build compiles the current head of `branch`. |
| `branch` | Only for `branch` versioning. |
| `license` | Optional, written to `BUILD_INFO.txt`. Default `GPL-3.0-or-later`. |
| `unavailableBoards` | Optional. Boards this firmware lists but cannot build yet, keyed by PlatformIO env: `{"<env>": {"reason": "<code>", "issue": "<GitHub issue URL>"}}`. See [Unavailable boards](#unavailable-boards). |

Without the file the builder offers upstream Meshtastic only.

## How versions work

- **Tags.** Each firmware keeps its own tag cache in SQLite
  (`firmware_versions`, keyed by firmware and tag), refreshed from the GitHub
  tags API like upstream's. The admin commands take `--firmware <id>`, e.g.
  `python -m meshtastic_builder list-versions --firmware jentastic`.
- **Branch.** The version selector shows `N/A` and is disabled. The server
  resolves the branch head (cached for five minutes) and reads the firmware
  version from that commit's `version.properties`. The build stores the commit
  it resolved, so the ZIP always says exactly what was compiled.

The version gates (the two patches, eight channels, advanced options) compare
the firmware version `x.y.z`: the tag for tag firmwares, `version.properties`
for branch firmwares. A fork that numbers its versions differently from
upstream (Jentastic's `2.8.104` is upstream 2.8.1 plus its own release 04)
still compares correctly as long as its number does not sort below the upstream
release it is based on.

## Boards

The device list is per firmware and per version. The first time a commit is
requested, the server reads its `variants/` tree through the GitHub API (two
calls) and downloads its `platformio.ini` files from raw.githubusercontent.com
(about 200 for upstream, a few seconds). It applies the Web Flasher's rule
(`custom_meshtastic_display_name`, actively supported, not `board_level =
extra`) and stores the result in SQLite table `board_catalogs`, keyed by
firmware and commit. A commit never changes, so it is never read again; the ini
files themselves are also cached on disk by blob SHA, so another tag of the
same firmware only downloads what changed.

Boards already in `data/devices.json` keep their id and label there. Others get
an id from their env name (`nrf52_promicro_diy_e28` -> `nrf52-promicro-diy-e28`),
and a label shared with another board gets the env name as suffix. A submitted
build is checked against the list of its exact commit and stores the board's
label, so the build page can name boards that only a fork has.

If GitHub cannot be reached and the commit is not cached, the page offers
`data/devices.json` instead.

Only `heltec-v4` and `nrf52_promicro_diy_tcxo` are prewarmed in the builder
image. Any other board, from upstream or from a fork, downloads its libraries
on its first build in each container, which is why builds need
`MB_DOCKER_NETWORK=bridge`.

## Unavailable boards

A board the firmware offers but that cannot be built with it (for now) goes in
that firmware's `unavailableBoards`, with a reason code and the GitHub issue
that tracks the fix. Unlike `EXCLUDED_ENVS`/`EXCLUDED_FAMILIES` in
`device_sync.py`, which hide a board from every firmware, this is per firmware
and the board stays visible:

- `/api/devices` lists it with `"unavailable": {"reason", "issue"}`;
- the page shows it as unavailable, never picks it by default, and when it is
  selected explains why under the picker, links the issue and keeps the submit
  button off;
- `POST /api/builds` refuses it with `400`, naming the reason and the issue.

It applies to every version of that firmware. Remove the entry once a release
fixes the board and a real build of it succeeds; older tags of that firmware
are then offered again for it, so say in the issue which tags stay broken.

Reason codes the page translates (`device.unavailable.<code>` in
`static/i18n.js`): `firmware_too_big`, the image does not fit in the board's
flash. A new code needs an ES and EN text there and in
`UNAVAILABLE_REASONS` in `board_catalog.py`.

Current entries: Jentastic, Heltec Mesh Node T096 and Heltec Mesh Pocket
(5000 and 10000 mAh, with and without InkHUD), which overflow flash
([#3](https://github.com/lazynoda/meshtastic-builder/issues/3)).

## Adding a firmware

1. Add the entry to `data/firmwares.json` and redeploy `web` and `worker`.
2. Check its tags or branch with
   `curl '<base>/api/firmware-versions?firmware=<id>'`.
3. Run one real build for an nRF52 and one for an ESP32 board. The first build
   of a firmware downloads the commits it does not share with upstream, so it
   takes longer.

The builder image does not need rebuilding: it fetches other repositories into
its upstream clone at build time (see
[Worker and Builder](worker-and-builder.md)).
