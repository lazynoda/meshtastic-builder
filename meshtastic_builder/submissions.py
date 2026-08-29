from __future__ import annotations

import json
from typing import Any

from .code_options import validate_code_options
from .config import Config
from .db import create_build_request, public_build_view
from .devices import get_enabled_device
from .firmware import get_userprefs_template, resolve_supported_version
from .jsonc import validate_and_merge_userprefs
from .security import validate_email


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Falta el campo {key}.")
    return value


def create_build_submission(config: Config, payload: dict[str, Any]) -> dict[str, Any]:
    email = validate_email(_required_str(payload, "email"))
    device = get_enabled_device(config.root_dir, _required_str(payload, "deviceId"))
    firmware_tag = _required_str(payload, "firmwareTag")
    version = resolve_supported_version(config, firmware_tag)
    prefs_raw = _required_str(payload, "prefsJsonc")
    code_options, code_macros = validate_code_options(
        config.root_dir,
        payload.get("codeOptions"),
        version["tag"],
    )
    template = get_userprefs_template(config, firmware_tag)
    prefs_jsonc, _prefs = validate_and_merge_userprefs(
        prefs_raw,
        template,
        config.max_prefs_bytes,
        extra_keys=code_macros,
    )
    row = create_build_request(
        config,
        email=email,
        device_id=device.id,
        platformio_env=device.platformio_env,
        firmware_tag=version["tag"],
        firmware_sha=version["sha"],
        prefs_jsonc=prefs_jsonc,
        code_options=json.dumps(code_options, sort_keys=True) if code_options else None,
    )
    token = row["public_token"]
    return {
        "row": row,
        "public": public_build_view(row),
        "statusUrl": f"{config.base_url}/api/builds/{token}",
        "downloadUrl": f"{config.base_url}/download/{token}",
    }
