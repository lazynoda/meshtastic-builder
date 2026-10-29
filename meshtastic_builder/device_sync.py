"""Regenerate data/devices.json from a firmware checkout.

The device list is the set the Meshtastic Web Flasher offers: every env under
variants/**/platformio.ini that declares custom_meshtastic_display_name, sets
custom_meshtastic_actively_supported = true and is not board_level = extra.

Run it against the checkout of the newest supported tag after each firmware
release. Existing entries keep their id and label (stored builds and shared
links reference the ids), new boards are appended, boards the firmware dropped
are removed. Nothing is written without --write.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path

from .devices import Device, load_devices


# They lead the list in this order, ahead of the alphabetical rest: the page
# preselects the first one, and these are the boards most builds are for.
LEAD_IDS = (
    "nrf52-promicro-diy",
    "tbeam",
    "heltec-v3",
    "heltec-v4",
    "heltec-mesh-node-t114",
    "tracker-t1000-e",
    "heltec-wsl-v3",
    "rak4631",
)

# Boards the flasher offers but this builder cannot ship yet. Each needs a
# reason. They stay out of every firmware's list, cached lists included.
EXCLUDED_ENVS: dict[str, str] = {}

# Whole chip families, so a fork's or a later tag's new board of that family is
# kept out too, not only the one board we happened to try.
EXCLUDED_FAMILIES: dict[str, str] = {
    # Compiles (with the native srec_cat), but ships only .hex files: no UF2,
    # no DFU zip, and FLASHING.txt would tell users to drag a UF2 onto it.
    "nrf54l15": "flashing nRF54L15 boards is not supported yet (issue #2)",
}


def exclusion_reason(env: str, family: str) -> str | None:
    return EXCLUDED_ENVS.get(env) or EXCLUDED_FAMILIES.get(family)

_ENV_HEADER_RE = re.compile(r"(?m)^(?=\[env:)")
_ENV_NAME_RE = re.compile(r"^\[env:([^\]]+)\]")


def _key(block: str, name: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*(.+?)\s*$", block)
    return match.group(1) if match else None


@dataclass(frozen=True)
class FlasherBoard:
    env: str
    label: str
    family: str
    source: str
    mui_env: str | None = None


# The Web Flasher's "Meshtastic UI" switch: a board declaring
# custom_meshtastic_has_mui = true whose `<env>-tft` env exists builds that env
# instead. Boards whose own env already ends in -tft (Crowpanel) are that build,
# and a -tft env listed as a board of its own (Heltec V4 TFT) is picked directly.
MUI_SUFFIX = "-tft"


# Env names reach `pio run -e` in the builder; the shell script enforces the same set.
SAFE_ENV_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def parse_boards(files: Iterable[tuple[str, str]]) -> dict[str, FlasherBoard]:
    """Every env the Web Flasher would offer, from (path, platformio.ini text) pairs.

    Keys are read from the env's own block only, which is how the firmware
    declares them: the custom_meshtastic_* keys are never inherited via extends.
    """
    boards: dict[str, FlasherBoard] = {}
    has_mui: set[str] = set()
    # Every env's board_level, listed or not: a -tft variant has no display name of its own.
    levels: dict[str, str] = {}
    for source, text in sorted(files):
        for block in _ENV_HEADER_RE.split(text):
            match = _ENV_NAME_RE.match(block)
            if match is None:
                continue
            levels[match.group(1)] = (_key(block, "board_level") or "").lower()
            label = _key(block, "custom_meshtastic_display_name")
            if not label:
                continue
            if (_key(block, "custom_meshtastic_actively_supported") or "").lower() != "true":
                continue
            if (_key(block, "board_level") or "").lower() == "extra":
                continue
            env = match.group(1)
            if not SAFE_ENV_RE.match(env):
                continue
            if (_key(block, "custom_meshtastic_has_mui") or "").lower() == "true":
                has_mui.add(env)
            boards[env] = FlasherBoard(
                env=env,
                label=label[:120],
                family=(_key(block, "custom_meshtastic_architecture") or "unknown")[:40],
                source=source,
            )
    for env in has_mui:
        mui_env = env + MUI_SUFFIX
        if (
            env.endswith(MUI_SUFFIX)
            or mui_env in boards
            or mui_env not in levels
            or levels[mui_env] == "extra"
            or not SAFE_ENV_RE.match(mui_env)
        ):
            continue
        boards[env] = replace(boards[env], mui_env=mui_env)
    return boards


def flasher_boards(repo_path: Path) -> dict[str, FlasherBoard]:
    """parse_boards() over a local firmware checkout."""
    if not (repo_path / "variants").is_dir():
        raise ValueError(f"Not a Meshtastic firmware checkout (no variants/): {repo_path}")
    return parse_boards(
        (str(ini.relative_to(repo_path)), ini.read_text(encoding="utf-8", errors="ignore"))
        for ini in repo_path.glob("variants/**/platformio.ini")
    )


def device_id_for(env: str) -> str:
    """`seeed_wio_tracker_L1` -> `seeed-wio-tracker-l1`, the convention of the existing ids."""
    return re.sub(r"[^a-z0-9]+", "-", env.lower()).strip("-")


@dataclass
class DeviceSync:
    devices: list[Device]
    added: list[Device] = field(default_factory=list)
    removed: list[Device] = field(default_factory=list)
    family_changed: list[tuple[Device, str]] = field(default_factory=list)
    excluded: list[tuple[str, str]] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed or self.family_changed)


def sync_devices(
    current: list[Device],
    boards: dict[str, FlasherBoard],
    *,
    strict: bool = True,
) -> DeviceSync:
    """Merge the firmware's boards onto `current`, keeping its ids and labels.

    strict=False is the runtime use (a per-firmware list built for the page):
    a board whose generated id collides with another env's id is skipped
    instead of stopping the whole list.
    """
    result = DeviceSync(devices=[])
    excluded = {
        env: reason
        for env, board in boards.items()
        if (reason := exclusion_reason(env, board.family)) is not None
    }
    result.excluded = sorted(excluded.items())
    wanted = {env: board for env, board in boards.items() if env not in excluded}

    kept: list[Device] = []
    for device in current:
        board = wanted.get(device.platformio_env)
        if board is None:
            result.removed.append(device)
            continue
        if board.family != device.family:
            result.family_changed.append((device, board.family))
        kept.append(
            Device(
                id=device.id,
                label=device.label,
                platformio_env=device.platformio_env,
                family=board.family,
                enabled=True,
                mui_env=board.mui_env,
            )
        )

    known_envs = {device.platformio_env for device in kept}
    used_ids = {device.id for device in kept}
    used_labels = {device.label for device in kept}
    for env in sorted(set(wanted) - known_envs):
        board = wanted[env]
        device_id = device_id_for(env)
        if device_id in used_ids:
            if not strict:
                continue
            raise ValueError(f"Generated id {device_id!r} for {env} is already taken; add it by hand.")
        label = board.label
        if label in used_labels:
            # Same rule as the existing entries: a shared display name gets a suffix.
            label = f"{label} ({env})"
        device = Device(
            id=device_id, label=label, platformio_env=env, family=board.family, enabled=True, mui_env=board.mui_env
        )
        result.added.append(device)
        kept.append(device)
        used_ids.add(device_id)
        used_labels.add(label)

    lead = [device for lead_id in LEAD_IDS for device in kept if device.id == lead_id]
    rest = sorted((device for device in kept if device.id not in LEAD_IDS), key=lambda d: d.label.lower())
    result.devices = lead + rest
    return result


def devices_json(devices: list[Device]) -> str:
    payload = [
        {
            "id": device.id,
            "label": device.label,
            "platformio_env": device.platformio_env,
            "family": device.family,
            "enabled": device.enabled,
        }
        for device in devices
    ]
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def run_sync(root_dir: Path, repo_path: Path, *, write: bool) -> DeviceSync:
    result = sync_devices(load_devices(root_dir), flasher_boards(repo_path))
    for device in result.added:
        print(f"ADD\t{device.id}\t{device.platformio_env}\t{device.family}\t{device.label}")
    for device in result.removed:
        print(f"REMOVE\t{device.id}\t{device.platformio_env}\t{device.label}")
    for device, family in result.family_changed:
        print(f"FAMILY\t{device.id}\t{device.family} -> {family}")
    for env, reason in result.excluded:
        print(f"SKIP\t{env}\t{reason}")
    print(f"{len(result.devices)} devices ({len(result.added)} added, {len(result.removed)} removed).")
    if write and result.changed:
        (root_dir / "data" / "devices.json").write_text(devices_json(result.devices), encoding="utf-8")
        print("Wrote data/devices.json.")
    elif result.changed:
        print("Dry run: pass --write to update data/devices.json.")
    return result
