from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


def load_build_options(root_dir: Path) -> dict[str, Any]:
    path = root_dir / "data" / "build_options.json"
    return json.loads(path.read_text(encoding="utf-8"))


def parse_version(tag: str) -> tuple[int, int, int] | None:
    match = VERSION_RE.match(tag.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def firmware_at_least(firmware_tag: str, minimum: str) -> bool:
    floor = parse_version(minimum)
    current = parse_version(firmware_tag)
    if floor is None or current is None:
        return False
    return current >= floor


def firmware_supports_code_options(options: dict[str, Any], firmware_tag: str) -> bool:
    return firmware_at_least(firmware_tag, str(options["minFirmwareVersion"]))


def code_options_need_patch(options: dict[str, Any], firmware_tag: str) -> bool:
    """Firmware >= nativeSinceFirmwareVersion reads the macros itself; the patch does not even apply there."""
    return not firmware_at_least(firmware_tag, str(options["nativeSinceFirmwareVersion"]))


def max_channels(options: dict[str, Any], firmware_tag: str) -> int:
    return 8 if firmware_at_least(firmware_tag, str(options["eightChannelsSinceFirmwareVersion"])) else 3


def _bool_field(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"La opcion {key} debe ser true o false.")
    return value


def _int_field(payload: dict[str, Any], key: str, spec: dict[str, Any]) -> int:
    value = payload.get(key, spec["default"])
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"La opcion {key} debe ser un numero entero.")
    choices = spec.get("choices")
    if choices is not None:
        if value not in choices:
            allowed = ", ".join(str(item) for item in choices)
            raise ValueError(f"La opcion {key} debe ser uno de: {allowed}.")
        return value
    if value < spec["min"] or value > spec["max"]:
        raise ValueError(f"La opcion {key} debe estar entre {spec['min']} y {spec['max']}.")
    return value


def validate_code_options(
    root_dir: Path,
    payload: Any,
    firmware_tag: str,
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """Validate a codeOptions payload.

    Returns the canonical options (or None when no options were requested) and
    the synthetic USERPREFS_* macros they expand to. Macro values are strings
    because the firmware build script calls str methods on every userPrefs value.
    """
    if payload is None:
        return None, {}
    if not isinstance(payload, dict):
        raise ValueError("codeOptions debe ser un objeto JSON.")

    options = load_build_options(root_dir)
    known = {"okToMqtt", "customLora"}
    unknown = set(payload) - known
    if unknown:
        raise ValueError(f"Opciones de compilacion desconocidas: {', '.join(sorted(unknown))}.")
    if not payload:
        return None, {}

    if not firmware_supports_code_options(options, firmware_tag):
        raise ValueError(
            f"Las opciones avanzadas requieren firmware {options['minFirmwareVersion']} o superior."
        )

    canonical: dict[str, Any] = {}
    macros: dict[str, str] = {}

    if "okToMqtt" in payload:
        ok_to_mqtt = _bool_field(payload, "okToMqtt")
        canonical["okToMqtt"] = ok_to_mqtt
        ok_spec = options["okToMqtt"]
        macro = ok_spec["macro"] if code_options_need_patch(options, firmware_tag) else ok_spec["nativeMacro"]
        macros[macro] = "true" if ok_to_mqtt else "false"

    custom_lora = payload.get("customLora")
    if custom_lora is not None:
        if not isinstance(custom_lora, dict):
            raise ValueError("La opcion customLora debe ser un objeto JSON.")
        spec = options["customLora"]
        unknown_fields = set(custom_lora) - set(spec["fields"])
        if unknown_fields:
            raise ValueError(f"Campos customLora desconocidos: {', '.join(sorted(unknown_fields))}.")
        values = {name: _int_field(custom_lora, name, field) for name, field in spec["fields"].items()}
        canonical["customLora"] = values
        macros[spec["usePresetMacro"]] = "false"
        for name, field in spec["fields"].items():
            macros[field["macro"]] = str(values[name])

    if not canonical:
        return None, {}
    return canonical, macros
