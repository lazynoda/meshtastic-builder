from __future__ import annotations

import json
import re
from typing import Any


KEY_RE = re.compile(r"^[A-Z0-9_]+$")
IANA_TZ_RE = re.compile(r"^[A-Za-z_]+/[A-Za-z_]+$")
# Firmware >= 2.8.0 reads channels 0..7 even though userPrefs.jsonc only lists the first few.
CHANNEL_KEY_RE = re.compile(
    r"^USERPREFS_CHANNEL_([0-7])_(NAME|PSK|PRECISION|IS_MUTED|UPLINK_ENABLED|DOWNLINK_ENABLED)$"
)
CHANNEL_PRECISION_RE = re.compile(r"^USERPREFS_CHANNEL_[0-7]_PRECISION$")
CHANNEL_BOOL_RE = re.compile(r"^USERPREFS_CHANNEL_[0-7]_(IS_MUTED|UPLINK_ENABLED|DOWNLINK_ENABLED)$")

# bin/platformio-custom.py passes values starting with `meshtastic_` or `{` unquoted into -D flags,
# and the flags reach the compiler through a shell. Everything else is quoted, but " \ $ ` would
# still break out of those quotes.
ENUM_VALUE_RE = re.compile(r"^meshtastic_[A-Za-z0-9_]+$")
BYTE_ARRAY_RE = re.compile(r"^\{\s*(0x[0-9a-fA-F]{1,2}(\s*,\s*0x[0-9a-fA-F]{1,2})*)?\s*\}$")
UNSAFE_STRING_RE = re.compile(r'["\\$`\x00-\x1f\x7f]')

ALLOWED_DEVICE_ROLES = {
    "meshtastic_Config_DeviceConfig_Role_CLIENT",
    "meshtastic_Config_DeviceConfig_Role_CLIENT_MUTE",
    "meshtastic_Config_DeviceConfig_Role_CLIENT_HIDDEN",
    "meshtastic_Config_DeviceConfig_Role_TRACKER",
    "meshtastic_Config_DeviceConfig_Role_SENSOR",
    "meshtastic_Config_DeviceConfig_Role_TAK",
    "meshtastic_Config_DeviceConfig_Role_TAK_TRACKER",
}

# Superset across supported tags; the UI hides identifiers the selected firmware does not know.
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
    "meshtastic_Config_LoRaConfig_RegionCode_ITU2_2M",
    "meshtastic_Config_LoRaConfig_RegionCode_ITU3_2M",
    "meshtastic_Config_LoRaConfig_RegionCode_ITU1_70CM",
    "meshtastic_Config_LoRaConfig_RegionCode_ITU2_70CM",
    "meshtastic_Config_LoRaConfig_RegionCode_ITU3_70CM",
    "meshtastic_Config_LoRaConfig_RegionCode_ITU2_125CM",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_866",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_874",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_917",
    "meshtastic_Config_LoRaConfig_RegionCode_EU_N_868",
}

ALLOWED_MODEM_PRESETS = {
    "meshtastic_Config_LoRaConfig_ModemPreset_LONG_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_MEDIUM_SLOW",
    "meshtastic_Config_LoRaConfig_ModemPreset_MEDIUM_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_MEDIUM_TURBO",
    "meshtastic_Config_LoRaConfig_ModemPreset_SHORT_SLOW",
    "meshtastic_Config_LoRaConfig_ModemPreset_SHORT_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_LONG_MODERATE",
    "meshtastic_Config_LoRaConfig_ModemPreset_SHORT_TURBO",
    "meshtastic_Config_LoRaConfig_ModemPreset_LONG_TURBO",
    "meshtastic_Config_LoRaConfig_ModemPreset_LITE_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_LITE_SLOW",
    "meshtastic_Config_LoRaConfig_ModemPreset_NARROW_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_NARROW_SLOW",
    "meshtastic_Config_LoRaConfig_ModemPreset_TINY_FAST",
    "meshtastic_Config_LoRaConfig_ModemPreset_TINY_SLOW",
}

ALLOWED_REBROADCAST_MODES = {
    f"meshtastic_Config_DeviceConfig_RebroadcastMode_{mode}"
    for mode in ("ALL", "ALL_SKIP_DECODING", "LOCAL_ONLY", "KNOWN_ONLY", "NONE", "CORE_PORTNUMS_ONLY")
}

ALLOWED_GPS_MODES = {
    f"meshtastic_Config_PositionConfig_GpsMode_{mode}" for mode in ("DISABLED", "ENABLED", "NOT_PRESENT")
}

ALLOWED_SIGNATURE_POLICIES = {
    f"meshtastic_Config_SecurityConfig_PacketSignaturePolicy_PACKET_SIGNATURE_POLICY_{policy}"
    for policy in ("COMPATIBLE", "BALANCED", "STRICT")
}

ENUM_KEYS = {
    "USERPREFS_CONFIG_DEVICE_ROLE": (ALLOWED_DEVICE_ROLES, "Rol de dispositivo no permitido"),
    "USERPREFS_CONFIG_LORA_REGION": (ALLOWED_LORA_REGIONS, "Region LoRa no permitida"),
    "USERPREFS_LORACONFIG_MODEM_PRESET": (ALLOWED_MODEM_PRESETS, "Preset LoRa no permitido"),
    "USERPREFS_CONFIG_DEVICE_REBROADCAST_MODE": (ALLOWED_REBROADCAST_MODES, "Modo de retransmision no permitido"),
    "USERPREFS_CONFIG_SECURITY_PACKET_SIGNATURE_POLICY": (ALLOWED_SIGNATURE_POLICIES, "Politica de firma no permitida"),
    "USERPREFS_CONFIG_GPS_MODE": (ALLOWED_GPS_MODES, "Modo de GPS no permitido"),
}

BOOL_KEYS = {
    "USERPREFS_CONFIG_LORA_IGNORE_MQTT",
    "USERPREFS_NETWORK_WIFI_ENABLED",
    "USERPREFS_CONFIG_SMART_POSITION_ENABLED",
    "USERPREFS_CONFIG_ENVIRONMENT_MEASUREMENT_ENABLED",
    "USERPREFS_CONFIG_SECURITY_IS_MANAGED",
    "USERPREFS_MQTT_TLS_ENABLED",
    "USERPREFS_MQTT_ENCRYPTION_ENABLED",
}

# Inclusive (min, max); None means unbounded. Firmware clamps node-info to >= 3600 itself.
INT_RANGE_KEYS = {
    "USERPREFS_LORACONFIG_TX_POWER": (0, 30),
    "USERPREFS_CONFIG_DEVICE_NODE_INFO_BROADCAST_SECS": (3600, None),
    "USERPREFS_CONFIG_DEVICE_TELEM_UPDATE_INTERVAL": (0, None),
    "USERPREFS_CONFIG_ENV_TELEM_UPDATE_INTERVAL": (0, None),
    # Bluetooth passkey. Setting it also switches pairing to FIXED_PIN mode.
    "USERPREFS_FIXED_BLUETOOTH": (0, 999999),
    "USERPREFS_CONFIG_GPS_UPDATE_INTERVAL": (0, None),
    "USERPREFS_CONFIG_POSITION_BROADCAST_INTERVAL": (0, None),
    "USERPREFS_BLOCK_POSITION_ON_EVENT_CHANNEL": (0, 1),
}

# The firmware multiplies these into an int32 (`USERPREFS_FIXED_GPS_LAT * 1e7`), so the
# value has to reach the compiler as a bare number. bin/platformio-custom.py only leaves
# it bare when it looks like plain decimal, so anything else (1e5, .5, 0x10) is refused.
PLAIN_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

PLAIN_INT_RE = re.compile(r"^-?\d+$")

FLOAT_RANGE_KEYS = {
    "USERPREFS_FIXED_GPS_LAT": (-90.0, 90.0),
    "USERPREFS_FIXED_GPS_LON": (-180.0, 180.0),
}

SIGNED_INT_RANGE_KEYS = {
    "USERPREFS_FIXED_GPS_ALT": (-500, 100000),
}

# nanopb buffer sizes from module_config.pb.h minus the terminator.
MAX_BYTES_KEYS = {
    "USERPREFS_MQTT_ADDRESS": 63,
    "USERPREFS_NETWORK_WIFI_SSID": 32,
    "USERPREFS_NETWORK_WIFI_PSK": 64,
    "USERPREFS_MQTT_USERNAME": 63,
    "USERPREFS_MQTT_PASSWORD": 31,
    "USERPREFS_MQTT_ROOT_TOPIC": 31,
}


# Keys the firmware consumes as C strings (strncpy, string literals). bin/platformio-custom.py
# only quotes a value that does not already look like a number, bool, enum, hex or byte array,
# so an all-digit SSID or password would reach the compiler bare and fail the build with an
# unreadable C++ error an hour in. Reject it at submit time instead.
STRING_MACRO_KEYS = {
    "USERPREFS_CONFIG_OWNER_LONG_NAME",
    "USERPREFS_CONFIG_OWNER_SHORT_NAME",
    "USERPREFS_MQTT_USERNAME",
    "USERPREFS_MQTT_PASSWORD",
    "USERPREFS_MQTT_ROOT_TOPIC",
    "USERPREFS_NETWORK_WIFI_SSID",
    "USERPREFS_NETWORK_WIFI_PSK",
}

CHANNEL_NAME_RE = re.compile(r"^USERPREFS_CHANNEL_[0-7]_NAME$")

UNQUOTED_HEX_RE = re.compile(r"0[xX][0-9a-fA-F]+")


def _reaches_compiler_unquoted(value: str) -> bool:
    """Mirror of the branch order in upstream bin/platformio-custom.py."""
    return (
        value.startswith("{")
        or value.lstrip("-").replace(".", "").isdigit()
        or bool(UNQUOTED_HEX_RE.fullmatch(value))
        or value in {"true", "false"}
        or value.startswith("meshtastic_")
    )


# PlatformIO's StringifyMacro renders a string pref as -DKEY=\"value\": the quotes are escaped,
# so the shell that runs the compiler sees the value as a bare word. SCons only wraps an
# argument in real double quotes when it contains a space or a tab. A value without
# whitespace therefore reaches /bin/sh unquoted, and `|`, `;`, `&`, `<`, `>`, `(`, `)`,
# globs or a stray `'` are interpreted (a long name "A|B" piped the compiler into `B`).
# The firmware itself accepts these characters, so instead of rejecting them the builder
# backslash-escapes them in the file the compiler reads. With whitespace the value sits
# inside SCons' double quotes, where a backslash before these characters would survive
# into the string, so those values are left alone.
SHELL_META_CHARS = frozenset("|&;<>()'*?[]~#{}!^")
SHELL_QUOTED_TEMPLATE_RE = re.compile(r"^'[^']*'$")


def shell_escape_for_compiler(value: str) -> str:
    """Escape what /bin/sh would interpret in an unquoted string pref.

    Leaves untouched: values the firmware passes unquoted (numbers, enums, byte
    arrays...), values containing whitespace (SCons quotes them), and values written
    in upstream's own `'host'` form, where the shell strips the single quotes on purpose.
    """
    if _reaches_compiler_unquoted(value):
        return value
    if " " in value or "\t" in value:
        return value
    if SHELL_QUOTED_TEMPLATE_RE.match(value):
        return value
    return "".join("\\" + ch if ch in SHELL_META_CHARS else ch for ch in value)


def prefs_for_compiler(prefs_text: str) -> str:
    """The userPrefs.jsonc the builder container compiles with (shell-escaped values)."""
    parsed = parse_jsonc(prefs_text)
    if not isinstance(parsed, dict):
        return prefs_text
    escaped = {
        key: shell_escape_for_compiler(value) if isinstance(value, str) else value
        for key, value in parsed.items()
    }
    if escaped == parsed:
        return prefs_text
    return json.dumps(escaped, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


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
    if isinstance(value, bool):
        raise JsoncValidationError(f"La clave {key} debe ser un numero entero.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise JsoncValidationError(f"La clave {key} debe ser un numero entero.")


def _parse_bool_string(value: Any, key: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in ("true", "false"):
        return value == "true"
    raise JsoncValidationError(f"La clave {key} debe ser true o false.")


def _channel_key_allowed(key: str, max_channels: int) -> bool:
    match = CHANNEL_KEY_RE.match(key)
    return match is not None and int(match.group(1)) < max_channels


def to_firmware_value(value: Any) -> str:
    """Render a scalar the way the firmware build expects it.

    Upstream `bin/platformio-custom.py` calls string methods on every value in
    `userPrefs.jsonc`, so a JSON number or boolean would abort the build with an
    AttributeError instead of a useful message.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    return str(value)


def _validate_string_shape(key: str, value: str) -> None:
    if value.startswith("meshtastic_"):
        if not ENUM_VALUE_RE.match(value):
            raise JsoncValidationError(f"El valor de {key} no es un identificador valido.")
    elif value.startswith("{"):
        if not BYTE_ARRAY_RE.match(value):
            raise JsoncValidationError(f"El valor de {key} debe ser una lista de bytes como {{ 0x01, 0x02 }}.")
    elif UNSAFE_STRING_RE.search(value):
        raise JsoncValidationError(f"El valor de {key} contiene caracteres no permitidos.")


def validate_userpref_value(key: str, value: Any, max_channels: int = 3) -> None:
    if value is None:
        raise JsoncValidationError(f"La clave {key} no puede ser nula.")
    if isinstance(value, str):
        _validate_string_shape(key, value)
    if key in ENUM_KEYS:
        allowed, message = ENUM_KEYS[key]
        if value not in allowed:
            raise JsoncValidationError(f"{message}: {value}.")
    if key in BOOL_KEYS or CHANNEL_BOOL_RE.match(key):
        _parse_bool_string(value, key)
    if key in INT_RANGE_KEYS:
        low, high = INT_RANGE_KEYS[key]
        number = _parse_int_string(value, key)
        if number < low or (high is not None and number > high):
            limit = f"entre {low} y {high}" if high is not None else f"mayor o igual que {low}"
            raise JsoncValidationError(f"{key} debe estar {limit}.")
    if key in FLOAT_RANGE_KEYS:
        low, high = FLOAT_RANGE_KEYS[key]
        text = str(value).strip()
        if not PLAIN_DECIMAL_RE.match(text):
            raise JsoncValidationError(f"{key} debe ser un numero decimal simple, por ejemplo 41.3851.")
        if not low <= float(text) <= high:
            raise JsoncValidationError(f"{key} debe estar entre {low} y {high}.")

    if key in SIGNED_INT_RANGE_KEYS:
        low, high = SIGNED_INT_RANGE_KEYS[key]
        text = str(value).strip()
        if not PLAIN_INT_RE.match(text):
            raise JsoncValidationError(f"{key} debe ser un numero entero.")
        if not low <= int(text) <= high:
            raise JsoncValidationError(f"{key} debe estar entre {low} y {high}.")

    if key in MAX_BYTES_KEYS and isinstance(value, str) and len(value.encode("utf-8")) > MAX_BYTES_KEYS[key]:
        raise JsoncValidationError(f"{key} no puede superar {MAX_BYTES_KEYS[key]} bytes.")
    if (key in STRING_MACRO_KEYS or CHANNEL_NAME_RE.match(key)) and isinstance(value, str):
        if value and _reaches_compiler_unquoted(value):
            raise JsoncValidationError(
                f"{key} no puede ser solo digitos ni parecer un numero, booleano o enum: "
                "el firmware lo compilaria sin comillas."
            )

    if key == "USERPREFS_TZ_STRING":
        if not isinstance(value, str) or not value.strip():
            raise JsoncValidationError("USERPREFS_TZ_STRING debe contener un TZ POSIX.")
        if IANA_TZ_RE.match(value.strip()):
            raise JsoncValidationError("USERPREFS_TZ_STRING debe ser un TZ POSIX, no un nombre IANA como Europe/Madrid.")
    if key == "USERPREFS_CHANNELS_TO_WRITE":
        channel_count = _parse_int_string(value, key)
        if channel_count < 1 or channel_count > max_channels:
            raise JsoncValidationError(f"USERPREFS_CHANNELS_TO_WRITE debe estar entre 1 y {max_channels}.")
    if CHANNEL_PRECISION_RE.match(key):
        precision = _parse_int_string(value, key)
        if precision < 0 or precision > 32:
            raise JsoncValidationError(f"{key} debe estar entre 0 y 32.")


def validate_and_normalize_userprefs(
    text: str,
    allowed_keys: set[str],
    max_bytes: int,
    max_channels: int = 3,
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
        if allowed_keys and key not in allowed_keys and not _channel_key_allowed(key, max_channels):
            raise JsoncValidationError(f"La clave {key} no existe en userPrefs.jsonc para esta version.")
        if isinstance(value, (dict, list)):
            raise JsoncValidationError(f"La clave {key} debe ser escalar, no objeto ni lista.")
        if isinstance(value, str) and len(value) > 8192:
            raise JsoncValidationError(f"El valor de {key} es demasiado largo.")
        validate_userpref_value(key, value, max_channels)
        normalized[key] = value

    normalized_text = json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return normalized_text, normalized


def validate_and_merge_userprefs(
    text: str,
    template_text: str,
    max_bytes: int,
    extra_keys: dict[str, Any] | None = None,
    max_channels: int = 3,
) -> tuple[str, dict[str, Any]]:
    """Merge validated user overrides onto the tag template.

    `extra_keys` are server-generated macros that may not exist in the template.
    They are applied last so users cannot override them from prefsJsonc.
    `max_channels` widens the accepted `USERPREFS_CHANNEL_<n>_*` keys beyond the
    template for firmware that reads more channel slots than it documents.
    """
    allowed_keys = extract_userpref_keys(template_text)
    _override_text, overrides = validate_and_normalize_userprefs(text, allowed_keys, max_bytes, max_channels)
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
    if extra_keys:
        merged.update(extra_keys)
    merged = {key: to_firmware_value(value) for key, value in merged.items()}
    normalized_text = json.dumps(merged, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return normalized_text, merged
