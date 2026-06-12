from __future__ import annotations

import json
import re
from typing import Any


KEY_RE = re.compile(r"^[A-Z0-9_]+$")
IANA_TZ_RE = re.compile(r"^[A-Za-z_]+/[A-Za-z_]+$")
CHANNEL_PRECISION_RE = re.compile(r"^USERPREFS_CHANNEL_[0-2]_PRECISION$")

ALLOWED_DEVICE_ROLES = {
    "meshtastic_Config_DeviceConfig_Role_CLIENT",
    "meshtastic_Config_DeviceConfig_Role_CLIENT_MUTE",
    "meshtastic_Config_DeviceConfig_Role_CLIENT_HIDDEN",
    "meshtastic_Config_DeviceConfig_Role_TRACKER",
    "meshtastic_Config_DeviceConfig_Role_SENSOR",
    "meshtastic_Config_DeviceConfig_Role_TAK",
    "meshtastic_Config_DeviceConfig_Role_TAK_TRACKER",
}

ALLOWED_LORA_REGIONS = {
    "meshtastic_Config_LoRaConfig_RegionCode_US",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_433",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_868",
    "meshtastic_Config_LoRaConfig_RegionCode_CN",
    "meshtastic_Config_LoRaConfig_RegionCode_JP",
    "meshtastic_Config_LoRaConfig_RegionCode_ANZ",
    "meshtastic_Config_LoRaConfig_RegionCode_KR",
    "meshtastic_Config_LoRaConfig_RegionCode_TW",
    "meshtastic_Config_LoRaConfig_RegionCode_RU",
    "meshtastic_Config_LoRaConfig_RegionCode_IN",
    "meshtastic_Config_LoRaConfig_RegionCode_NZ_865",
    "meshtastic_Config_LoRaConfig_RegionCode_TH",
    "meshtastic_Config_LoRaConfig_RegionCode_LORA_24",
    "meshtastic_Config_LoRaConfig_RegionCode_UA_433",
    "meshtastic_Config_LoRaConfig_RegionCode_UA_868",
    "meshtastic_Config_LoRaConfig_RegionCode_MY_433",
    "meshtastic_Config_LoRaConfig_RegionCode_MY_919",
    "meshtastic_Config_LoRaConfig_RegionCode_SG_923",
    "meshtastic_Config_LoRaConfig_RegionCode_PH_433",
    "meshtastic_Config_LoRaConfig_RegionCode_PH_868",
    "meshtastic_Config_LoRaConfig_RegionCode_PH_915",
    "meshtastic_Config_LoRaConfig_RegionCode_ANZ_433",
    "meshtastic_Config_LoRaConfig_RegionCode_KZ_433",
    "meshtastic_Config_LoRaConfig_RegionCode_KZ_863",
    "meshtastic_Config_LoRaConfig_RegionCode_NP_865",
    "meshtastic_Config_LoRaConfig_RegionCode_BR_902",
    "meshtastic_Config_LoRaConfig_RegionCode_ITU1_2M",
    "meshtastic_Config_LoRaConfig_RegionCode_ITU23_2M",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_866",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_874",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_917",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_N_868",
}

ALLOWED_MODEM_PRESETS = {
    "meshtastic_Config_LoRaConfig_ModemPreset_LONG_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_MEDIUM_SLOW",
    "meshtastic_Config_LoRaConfig_ModemPreset_MEDIUM_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_SHORT_SLOW",
    "meshtastic_Config_LoRaConfig_ModemPreset_SHORT_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_LONG_MODERATE",
    "meshtastic_Config_LoRaConfig_ModemPreset_SHORT_TURBO",
    "meshtastic_Config_LoRaConfig_ModemPreset_LONG_TURBO",
    "meshtastic_Config_LoRaConfig_ModemPreset_LITE_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_LITE_SLOW",
    "meshtastic_Config_LoRaConfig_ModemPreset_NARROW_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_NARROW_SLOW",
}


class JsoncValidationError(ValueError):
    pass


def strip_jsonc_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    quote = ""
    escaped = False

    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                in_string = False
            i += 1
            continue

        if char in {"'", '"'}:
            in_string = True
            quote = char
            out.append(char)
            i += 1
            continue

        if char == "/" and nxt == "/":
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue

        if char == "/" and nxt == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue

        out.append(char)
        i += 1

    return "".join(out)


def remove_trailing_commas(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    quote = ""
    escaped = False

    while i < len(text):
        char = text[i]

        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                in_string = False
            i += 1
            continue

        if char in {"'", '"'}:
            in_string = True
            quote = char
            out.append(char)
            i += 1
            continue

        if char == ",":
            j = i + 1
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] in "}]":
                i += 1
                continue

        out.append(char)
        i += 1

    return "".join(out)


def parse_jsonc(text: str) -> Any:
    try:
        return json.loads(remove_trailing_commas(strip_jsonc_comments(text)))
    except json.JSONDecodeError as exc:
        raise JsoncValidationError(f"JSONC invalido: {exc.msg} en linea {exc.lineno}.") from exc


def extract_userpref_keys(template_text: str) -> set[str]:
    return set(re.findall(r'"(USERPREFS_[A-Z0-9_]+)"\s*:', template_text))


def _parse_int_string(value: Any, key: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise JsoncValidationError(f"La clave {key} debe ser un numero entero.")


def validate_userpref_value(key: str, value: Any) -> None:
    if key == "USERPREFS_CONFIG_DEVICE_ROLE" and value not in ALLOWED_DEVICE_ROLES:
        raise JsoncValidationError(f"Rol de dispositivo no permitido: {value}.")
    if key == "USERPREFS_CONFIG_LORA_REGION" and value not in ALLOWED_LORA_REGIONS:
        raise JsoncValidationError(f"Region LoRa no permitida: {value}.")
    if key == "USERPREFS_LORACONFIG_MODEM_PRESET" and value not in ALLOWED_MODEM_PRESETS:
        raise JsoncValidationError(f"Preset LoRa no permitido: {value}.")
    if key == "USERPREFS_TZ_STRING":
        if not isinstance(value, str) or not value.strip():
            raise JsoncValidationError("USERPREFS_TZ_STRING debe contener un TZ POSIX.")
        if IANA_TZ_RE.match(value.strip()):
            raise JsoncValidationError("USERPREFS_TZ_STRING debe ser un TZ POSIX, no un nombre IANA como Europe/Madrid.")
    if key == "USERPREFS_CHANNELS_TO_WRITE":
        channel_count = _parse_int_string(value, key)
        if channel_count < 1 or channel_count > 3:
            raise JsoncValidationError("USERPREFS_CHANNELS_TO_WRITE debe estar entre 1 y 3.")
    if CHANNEL_PRECISION_RE.match(key):
        precision = _parse_int_string(value, key)
        if precision < 0 or precision > 32:
            raise JsoncValidationError(f"{key} debe estar entre 0 y 32.")


def validate_and_normalize_userprefs(
    text: str,
    allowed_keys: set[str],
    max_bytes: int,
) -> tuple[str, dict[str, Any]]:
    if len(text.encode("utf-8")) > max_bytes:
        raise JsoncValidationError("El fichero userPrefs.jsonc es demasiado grande.")

    parsed = parse_jsonc(text)
    if not isinstance(parsed, dict):
        raise JsoncValidationError("userPrefs.jsonc debe contener un objeto JSON.")

    normalized: dict[str, Any] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not KEY_RE.match(key) or not key.startswith("USERPREFS_"):
            raise JsoncValidationError(f"Clave no permitida: {key!r}.")
        if allowed_keys and key not in allowed_keys:
            raise JsoncValidationError(f"La clave {key} no existe en userPrefs.jsonc para esta version.")
        if isinstance(value, (dict, list)):
            raise JsoncValidationError(f"La clave {key} debe ser escalar, no objeto ni lista.")
        if isinstance(value, str) and len(value) > 8192:
            raise JsoncValidationError(f"El valor de {key} es demasiado largo.")
        validate_userpref_value(key, value)
        normalized[key] = value

    normalized_text = json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return normalized_text, normalized


def validate_and_merge_userprefs(
    text: str,
    template_text: str,
    max_bytes: int,
) -> tuple[str, dict[str, Any]]:
    allowed_keys = extract_userpref_keys(template_text)
    _override_text, overrides = validate_and_normalize_userprefs(text, allowed_keys, max_bytes)
    template = parse_jsonc(template_text)
    if not isinstance(template, dict):
        raise JsoncValidationError("El template userPrefs.jsonc debe contener un objeto JSON.")

    merged: dict[str, Any] = {}
    for key, value in template.items():
        if not isinstance(key, str) or not key.startswith("USERPREFS_"):
            continue
        if allowed_keys and key not in allowed_keys:
            continue
        if isinstance(value, (dict, list)):
            continue
        merged[key] = value

    merged.update(overrides)
    normalized_text = json.dumps(merged, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return normalized_text, merged
