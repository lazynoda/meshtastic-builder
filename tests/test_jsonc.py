import json
import unittest

from meshtastic_builder.jsonc import (
    JsoncValidationError,
    extract_userpref_keys,
    parse_jsonc,
    validate_and_merge_userprefs,
    validate_and_normalize_userprefs,
    validate_userpref_value,
)


class JsoncTests(unittest.TestCase):
    def test_parse_jsonc_preserves_url_like_strings(self):
        parsed = parse_jsonc(
            """
            {
              // comment
              "USERPREFS_URL": "https://example.com/path//kept",
              "USERPREFS_FLAG": true,
            }
            """
        )
        self.assertEqual(parsed["USERPREFS_URL"], "https://example.com/path//kept")
        self.assertTrue(parsed["USERPREFS_FLAG"])

    def test_extract_keys_from_template(self):
        keys = extract_userpref_keys(
            """
            {
              // "USERPREFS_IGNORED": false,
              "USERPREFS_ALPHA": "a",
              "USERPREFS_BETA_2": 2
            }
            """
        )
        self.assertEqual(keys, {"USERPREFS_IGNORED", "USERPREFS_ALPHA", "USERPREFS_BETA_2"})

    def test_merged_values_are_strings_for_the_firmware_build(self):
        normalized, parsed = validate_and_merge_userprefs(
            '{"USERPREFS_FLAG": true, "USERPREFS_COUNT": 3}',
            '{"USERPREFS_FLAG": "false", "USERPREFS_COUNT": "1", "USERPREFS_KEPT": true}',
            1000,
        )
        self.assertEqual(parsed["USERPREFS_FLAG"], "true")
        self.assertEqual(parsed["USERPREFS_COUNT"], "3")
        self.assertEqual(parsed["USERPREFS_KEPT"], "true")
        for value in json.loads(normalized).values():
            self.assertIsInstance(value, str)

    def test_null_preference_values_are_rejected(self):
        with self.assertRaises(JsoncValidationError):
            validate_and_merge_userprefs(
                '{"USERPREFS_FLAG": null}',
                '{"USERPREFS_FLAG": "false"}',
                1000,
            )

    def test_commented_template_keys_can_be_submitted(self):
        normalized, parsed = validate_and_merge_userprefs(
            '{"USERPREFS_CHANNEL_0_NAME": "LongFast"}',
            """
            {
              // "USERPREFS_CHANNEL_0_NAME": "REPLACEME",
              "USERPREFS_TZ_STRING": "CET-1CEST,M3.5.0,M10.5.0/3"
            }
            """,
            1000,
        )
        self.assertEqual(parsed["USERPREFS_CHANNEL_0_NAME"], "LongFast")
        self.assertIn('"USERPREFS_CHANNEL_0_NAME": "LongFast"', normalized)

    def test_ignore_mqtt_is_accepted_as_a_boolean(self):
        template = '{\n  // "USERPREFS_CONFIG_LORA_IGNORE_MQTT": "true"\n}'
        _normalized, parsed = validate_and_merge_userprefs(
            '{"USERPREFS_CONFIG_LORA_IGNORE_MQTT": "true"}',
            template,
            1000,
        )
        self.assertEqual(parsed["USERPREFS_CONFIG_LORA_IGNORE_MQTT"], "true")
        with self.assertRaises(JsoncValidationError):
            validate_and_merge_userprefs(
                '{"USERPREFS_CONFIG_LORA_IGNORE_MQTT": "yes"}',
                template,
                1000,
            )

    def test_wifi_and_bluetooth_values(self):
        template = (
            '{\n'
            '  // "USERPREFS_NETWORK_WIFI_ENABLED": "true",\n'
            '  // "USERPREFS_NETWORK_WIFI_SSID": "wifi_ssid",\n'
            '  // "USERPREFS_NETWORK_WIFI_PSK": "wifi_psk",\n'
            '  // "USERPREFS_FIXED_BLUETOOTH": "121212"\n'
            '}'
        )
        _text, parsed = validate_and_merge_userprefs(
            '{"USERPREFS_NETWORK_WIFI_ENABLED": "true", "USERPREFS_NETWORK_WIFI_SSID": "MiRed_5G",'
            ' "USERPREFS_NETWORK_WIFI_PSK": "clave-secreta", "USERPREFS_FIXED_BLUETOOTH": "482913"}',
            template,
            2000,
        )
        self.assertEqual(parsed["USERPREFS_NETWORK_WIFI_SSID"], "MiRed_5G")
        self.assertEqual(parsed["USERPREFS_FIXED_BLUETOOTH"], "482913")

        for payload in (
            '{"USERPREFS_FIXED_BLUETOOTH": "1234567"}',
            # Leading zero or under six digits: octal on the compiler, and setPIN on
            # nRF52 refuses a passkey that is not six characters long.
            '{"USERPREFS_FIXED_BLUETOOTH": "012389"}',
            '{"USERPREFS_FIXED_BLUETOOTH": "012345"}',
            '{"USERPREFS_FIXED_BLUETOOTH": "99999"}',
            '{"USERPREFS_FIXED_BLUETOOTH": "0"}',
            '{"USERPREFS_NETWORK_WIFI_ENABLED": "yes"}',
            '{"USERPREFS_NETWORK_WIFI_SSID": "' + "x" * 33 + '"}',
        ):
            with self.subTest(payload=payload), self.assertRaises(JsoncValidationError):
                validate_and_merge_userprefs(payload, template, 2000)

    def test_c_string_keys_reject_values_the_build_would_not_quote(self):
        """bin/platformio-custom.py emits digits, bools, hex and enums without quotes."""
        keys = (
            "USERPREFS_NETWORK_WIFI_PSK",
            "USERPREFS_NETWORK_WIFI_SSID",
            "USERPREFS_MQTT_PASSWORD",
            "USERPREFS_CONFIG_OWNER_LONG_NAME",
            "USERPREFS_CHANNEL_0_NAME",
        )
        for key in keys:
            for value in ("12345678", "-4.5", "0xAB12", "true", "meshtastic_Thing"):
                with self.subTest(key=key, value=value), self.assertRaises(JsoncValidationError):
                    validate_userpref_value(key, value)
        # Anything the build script would quote is still fine.
        for value in ("5GHome", "clave-secreta", "12345678a", "Nodo 12"):
            validate_userpref_value("USERPREFS_NETWORK_WIFI_PSK", value)

    def test_position_values(self):
        for key, value in (
            ("USERPREFS_FIXED_GPS_LAT", "41.3851"),
            ("USERPREFS_FIXED_GPS_LON", "-3.7038"),
            ("USERPREFS_FIXED_GPS_ALT", "-5"),
            ("USERPREFS_FIXED_GPS", ""),
            ("USERPREFS_CONFIG_GPS_MODE", "meshtastic_Config_PositionConfig_GpsMode_NOT_PRESENT"),
        ):
            with self.subTest(key=key, value=value):
                validate_userpref_value(key, value)

        for key, value in (
            ("USERPREFS_FIXED_GPS_LAT", "95"),
            ("USERPREFS_FIXED_GPS_LON", "-181"),
            # Scientific notation and a bare decimal point would not reach the
            # compiler as plain numbers, and the firmware multiplies them.
            ("USERPREFS_FIXED_GPS_LAT", "1e2"),
            ("USERPREFS_FIXED_GPS_LON", ".5"),
            ("USERPREFS_FIXED_GPS_ALT", "3.5"),
            ("USERPREFS_CONFIG_GPS_MODE", "meshtastic_Config_PositionConfig_GpsMode_NOPE"),
            ("USERPREFS_BLOCK_POSITION_ON_EVENT_CHANNEL", "2"),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(JsoncValidationError):
                validate_userpref_value(key, value)

    def test_validate_rejects_unknown_key(self):
        with self.assertRaises(JsoncValidationError):
            validate_and_normalize_userprefs(
                '{"USERPREFS_UNKNOWN": true}',
                {"USERPREFS_ALLOWED"},
                1000,
            )

    def test_validate_normalizes_json(self):
        normalized, parsed = validate_and_normalize_userprefs(
            '{"USERPREFS_ALLOWED": "x",}',
            {"USERPREFS_ALLOWED"},
            1000,
        )
        self.assertEqual(parsed, {"USERPREFS_ALLOWED": "x"})
        self.assertIn('"USERPREFS_ALLOWED": "x"', normalized)

    def test_validate_and_merge_keeps_template_defaults(self):
        normalized, parsed = validate_and_merge_userprefs(
            '{"USERPREFS_ALPHA": "override"}',
            """
            {
              "USERPREFS_ALPHA": "default",
              "USERPREFS_BETA": true,
              "USERPREFS_TZ_STRING": "CET-1CEST,M3.5.0,M10.5.0/3"
            }
            """,
            1000,
        )
        self.assertEqual(parsed["USERPREFS_ALPHA"], "override")
        self.assertTrue(parsed["USERPREFS_BETA"])
        self.assertEqual(parsed["USERPREFS_TZ_STRING"], "CET-1CEST,M3.5.0,M10.5.0/3")
        self.assertIn('"USERPREFS_TZ_STRING": "CET-1CEST,M3.5.0,M10.5.0/3"', normalized)

    def test_validate_rejects_blocked_device_role(self):
        with self.assertRaisesRegex(JsoncValidationError, "Rol de dispositivo"):
            validate_and_normalize_userprefs(
                '{"USERPREFS_CONFIG_DEVICE_ROLE": "meshtastic_Config_DeviceConfig_Role_ROUTER"}',
                {"USERPREFS_CONFIG_DEVICE_ROLE"},
                1000,
            )

    def test_validate_rejects_iana_timezone_name(self):
        with self.assertRaisesRegex(JsoncValidationError, "TZ POSIX"):
            validate_and_normalize_userprefs(
                '{"USERPREFS_TZ_STRING": "Europe/Madrid"}',
                {"USERPREFS_TZ_STRING"},
                1000,
            )

    def test_validate_accepts_posix_timezone_string(self):
        _normalized, parsed = validate_and_normalize_userprefs(
            '{"USERPREFS_TZ_STRING": "CET-1CEST,M3.5.0,M10.5.0/3"}',
            {"USERPREFS_TZ_STRING"},
            1000,
        )
        self.assertEqual(parsed["USERPREFS_TZ_STRING"], "CET-1CEST,M3.5.0,M10.5.0/3")

    def test_validate_rejects_deprecated_modem_preset(self):
        with self.assertRaisesRegex(JsoncValidationError, "Preset LoRa"):
            validate_and_normalize_userprefs(
                '{"USERPREFS_LORACONFIG_MODEM_PRESET": "meshtastic_Config_LoRaConfig_ModemPreset_LONG_SLOW"}',
                {"USERPREFS_LORACONFIG_MODEM_PRESET"},
                1000,
            )

    def test_validate_rejects_channel_count_above_ui_limit(self):
        with self.assertRaisesRegex(JsoncValidationError, "entre 1 y 3"):
            validate_and_normalize_userprefs(
                '{"USERPREFS_CHANNELS_TO_WRITE": "4"}',
                {"USERPREFS_CHANNELS_TO_WRITE"},
                1000,
            )


class HardeningTests(unittest.TestCase):
    """bin/platformio-custom.py passes some values unquoted into -D flags."""

    def assert_rejected(self, key, value):
        with self.assertRaises(JsoncValidationError):
            validate_and_normalize_userprefs(
                json.dumps({key: value}),
                {key},
                1000,
            )

    def test_enum_like_values_must_be_plain_identifiers(self):
        self.assert_rejected("USERPREFS_FIXED_BLUETOOTH", "meshtastic_X -DEVIL=1")
        self.assert_rejected("USERPREFS_FIXED_BLUETOOTH", "meshtastic_X)(")

    def test_brace_values_must_be_byte_arrays(self):
        self.assert_rejected("USERPREFS_USE_ADMIN_KEY_1", "{ system(\"rm\") }")
        normalized, parsed = validate_and_normalize_userprefs(
            '{"USERPREFS_USE_ADMIN_KEY_1": "{ 0x01, 0xff }"}',
            {"USERPREFS_USE_ADMIN_KEY_1"},
            1000,
        )
        self.assertEqual(parsed["USERPREFS_USE_ADMIN_KEY_1"], "{ 0x01, 0xff }")
        self.assertIn("0xff", normalized)

    def test_empty_brace_value_is_allowed(self):
        _text, parsed = validate_and_normalize_userprefs(
            '{"USERPREFS_USE_ADMIN_KEY_2": "{}"}',
            {"USERPREFS_USE_ADMIN_KEY_2"},
            1000,
        )
        self.assertEqual(parsed["USERPREFS_USE_ADMIN_KEY_2"], "{}")

    def test_text_keys_may_start_with_a_brace(self):
        # A short name like `{λ}` was refused as "debe ser una lista de bytes".
        for key, value in (
            ("USERPREFS_CONFIG_OWNER_SHORT_NAME", "{λ}"),
            ("USERPREFS_CONFIG_OWNER_LONG_NAME", "{lazynoda} base"),
            ("USERPREFS_CHANNEL_0_NAME", "{Test}"),
        ):
            with self.subTest(key=key):
                _text, parsed = validate_and_normalize_userprefs(
                    json.dumps({key: value}, ensure_ascii=False),
                    {key},
                    1000,
                )
                self.assertEqual(parsed[key], value)

    def test_byte_keys_still_need_a_byte_array(self):
        self.assert_rejected("USERPREFS_CHANNEL_0_PSK", "{λ}")
        self.assert_rejected("USERPREFS_CONFIG_SECURITY_PRIVATE_KEY", "{ rm }")

    def test_text_keys_still_refuse_quotes(self):
        self.assert_rejected("USERPREFS_CONFIG_OWNER_SHORT_NAME", '{"}')

    def test_quoted_values_cannot_escape_the_macro(self):
        self.assert_rejected("USERPREFS_MQTT_USERNAME", 'me" -DEVIL=1 "')
        self.assert_rejected("USERPREFS_CONFIG_OWNER_LONG_NAME", "node`id`")
        self.assert_rejected("USERPREFS_CONFIG_OWNER_LONG_NAME", "node\nmore")


class NewKeyValidationTests(unittest.TestCase):
    def normalize(self, payload, max_channels=3):
        return validate_and_normalize_userprefs(
            json.dumps(payload),
            set(payload),
            4000,
            max_channels,
        )[1]

    def test_tx_power_range(self):
        self.assertEqual(self.normalize({"USERPREFS_LORACONFIG_TX_POWER": "27"})["USERPREFS_LORACONFIG_TX_POWER"], "27")
        with self.assertRaises(JsoncValidationError):
            self.normalize({"USERPREFS_LORACONFIG_TX_POWER": "31"})

    def test_node_info_interval_floor(self):
        self.normalize({"USERPREFS_CONFIG_DEVICE_NODE_INFO_BROADCAST_SECS": "3600"})
        with self.assertRaises(JsoncValidationError):
            self.normalize({"USERPREFS_CONFIG_DEVICE_NODE_INFO_BROADCAST_SECS": "600"})

    def test_rebroadcast_and_signature_enums_are_allowlisted(self):
        self.normalize(
            {
                "USERPREFS_CONFIG_DEVICE_REBROADCAST_MODE": "meshtastic_Config_DeviceConfig_RebroadcastMode_LOCAL_ONLY",
                "USERPREFS_CONFIG_SECURITY_PACKET_SIGNATURE_POLICY": (
                    "meshtastic_Config_SecurityConfig_PacketSignaturePolicy_PACKET_SIGNATURE_POLICY_STRICT"
                ),
            }
        )
        with self.assertRaises(JsoncValidationError):
            self.normalize(
                {"USERPREFS_CONFIG_DEVICE_REBROADCAST_MODE": "meshtastic_Config_DeviceConfig_RebroadcastMode_MADEUP"}
            )

    def test_mqtt_strings_respect_nanopb_buffer_sizes(self):
        self.normalize({"USERPREFS_MQTT_PASSWORD": "x" * 31})
        with self.assertRaises(JsoncValidationError):
            self.normalize({"USERPREFS_MQTT_PASSWORD": "x" * 32})

    def test_boolean_keys_reject_other_values(self):
        self.normalize({"USERPREFS_MQTT_TLS_ENABLED": "true"})
        with self.assertRaises(JsoncValidationError):
            self.normalize({"USERPREFS_MQTT_TLS_ENABLED": "yes"})

    def test_new_presets_and_regions_are_accepted(self):
        self.normalize(
            {
                "USERPREFS_LORACONFIG_MODEM_PRESET": "meshtastic_Config_LoRaConfig_ModemPreset_TINY_FAST",
                "USERPREFS_CONFIG_LORA_REGION": "meshtastic_Config_LoRaConfig_RegionCode_ITU2_2M",
            }
        )


class ChannelCapTests(unittest.TestCase):
    TEMPLATE = '{"USERPREFS_CHANNELS_TO_WRITE": "1", "USERPREFS_CHANNEL_0_NAME": "LongFast"}'

    def merge(self, payload, max_channels):
        return validate_and_merge_userprefs(json.dumps(payload), self.TEMPLATE, 4000, max_channels=max_channels)[1]

    def test_channel_beyond_the_template_is_rejected_on_old_firmware(self):
        with self.assertRaises(JsoncValidationError):
            self.merge({"USERPREFS_CHANNEL_5_NAME": "Ops"}, 3)

    def test_channel_beyond_the_template_is_accepted_when_eight_are_allowed(self):
        merged = self.merge({"USERPREFS_CHANNEL_5_NAME": "Ops", "USERPREFS_CHANNEL_5_IS_MUTED": "true"}, 8)
        self.assertEqual(merged["USERPREFS_CHANNEL_5_NAME"], "Ops")
        self.assertEqual(merged["USERPREFS_CHANNEL_5_IS_MUTED"], "true")

    def test_channel_index_above_the_cap_is_still_rejected(self):
        with self.assertRaises(JsoncValidationError):
            self.merge({"USERPREFS_CHANNEL_8_NAME": "Nope"}, 8)

    def test_channels_to_write_follows_the_cap(self):
        self.merge({"USERPREFS_CHANNELS_TO_WRITE": "8"}, 8)
        with self.assertRaises(JsoncValidationError):
            self.merge({"USERPREFS_CHANNELS_TO_WRITE": "8"}, 3)


if __name__ == "__main__":
    unittest.main()
