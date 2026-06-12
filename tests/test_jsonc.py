import unittest

from meshtastic_builder.jsonc import (
    JsoncValidationError,
    extract_userpref_keys,
    parse_jsonc,
    validate_and_merge_userprefs,
    validate_and_normalize_userprefs,
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


if __name__ == "__main__":
    unittest.main()
