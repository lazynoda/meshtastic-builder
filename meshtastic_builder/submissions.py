from __future__ import annotations

import json
from typing import Any

from .code_options import load_build_options, max_channels, validate_code_options
from .config import Config
from .db import create_build_request, public_build_view
from .board_catalog import get_device_for_build
from .firmware import get_userprefs_template, resolve_supported_version
from .firmwares import VERSIONING_BRANCH, get_firmware
from .jsonc import validate_and_merge_userprefs


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Falta el campo {key}.")
    return value


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"El campo {key} debe ser texto.")
    return value.strip() or None


def create_build_submission(config: Config, payload: dict[str, Any]) -> dict[str, Any]:
    device_id = _required_str(payload, "deviceId")
    # Absent on clients older than the firmware selector: those meant upstream.
    source = get_firmware(config.root_dir, _optional_str(payload, "firmwareId"))
    firmware_tag = _optional_str(payload, "firmwareTag")
    if source.versioning != VERSIONING_BRANCH and not firmware_tag:
        raise ValueError("Falta el campo firmwareTag.")
    version = resolve_supported_version(config, firmware_tag, firmware_id=source.id)
    # Checked against the boards of this exact commit, so a board the chosen
    # firmware or tag lacks is refused here instead of failing to compile.
    device = get_device_for_build(config, source, version["sha"], device_id)
    # Version gates (patches, channel count, code options) compare x.y.z, which
    # for a branch comes from its version.properties rather than from a tag.
    gate_version = version["version"]
    prefs_raw = _required_str(payload, "prefsJsonc")
    code_options, code_macros = validate_code_options(
        config.root_dir,
        payload.get("codeOptions"),
        gate_version,
    )
    template_ref = version["sha"] if version["branch"] else version["tag"]
    template = get_userprefs_template(config, version["tag"], firmware_id=source.id, ref=template_ref)
    prefs_jsonc, _prefs = validate_and_merge_userprefs(
        prefs_raw,
        template,
        config.max_prefs_bytes,
        extra_keys=code_macros,
        max_channels=max_channels(load_build_options(config.root_dir), gate_version),
    )
    row = create_build_request(
        config,
        device_id=device.id,
        platformio_env=device.platformio_env,
        firmware_tag=version["tag"],
        firmware_sha=version["sha"],
        prefs_jsonc=prefs_jsonc,
        code_options=json.dumps(code_options, sort_keys=True) if code_options else None,
        firmware_id=source.id,
        firmware_version=gate_version,
        device_label=device.label,
    )
    token = row["public_token"]
    return {
        "row": row,
        "public": public_build_view(row),
        "buildUrl": f"{config.base_url}/build/{token}",
        "statusUrl": f"{config.base_url}/api/builds/{token}",
        "downloadUrl": f"{config.base_url}/download/{token}",
    }
