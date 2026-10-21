import json
import sqlite3
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from meshtastic_builder.build_failures import BuildFailure
from meshtastic_builder.builder import (
    raise_build_failure,
    run_build,
    run_fake_build,
)
from meshtastic_builder.code_options import (
    code_options_need_patch,
    fixed_gps_patch_needed,
    load_build_options,
    max_channels,
    parse_version,
    validate_code_options,
)
from meshtastic_builder.config import load_config
from meshtastic_builder.db import initialize_database, public_build_view, upsert_firmware_versions
from meshtastic_builder.firmware import userprefs_cache_path
from meshtastic_builder.jsonc import JsoncValidationError
from meshtastic_builder.submissions import create_build_submission


ROOT_DIR = Path(__file__).resolve().parent.parent
SUPPORTED_TAG = "v2.7.25.104df5f"
OLD_TAG = "v2.2.21.7f7c5cb"
NATIVE_TAG = "v2.8.0.47db0e3"


def temp_config(tmp_path: Path):
    return replace(
        load_config(),
        data_dir=tmp_path,
        db_path=tmp_path / "test.sqlite",
        artifact_dir=tmp_path / "artifacts",
        job_dir=tmp_path / "jobs",
        cache_dir=tmp_path / "cache",
        base_url="http://example.test",
    )


def seed_template(config, tag: str) -> None:
    upsert_firmware_versions(
        config,
        [{"tag": tag, "sha": "abc123", "release_name": tag, "supported": 1}],
    )
    path = userprefs_cache_path(config, tag)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"USERPREFS_CONFIG_OWNER_SHORT_NAME": "DEF"}',
        encoding="utf-8",
    )


class CodeOptionValidationTests(unittest.TestCase):
    def test_parse_version_handles_meshtastic_tags(self):
        self.assertEqual(parse_version("v2.7.25.104df5f"), (2, 7, 25))
        self.assertEqual(parse_version("2.6.4"), (2, 6, 4))
        self.assertIsNone(parse_version("v-test"))

    def test_patch_is_needed_below_the_native_version_only(self):
        options = load_build_options(ROOT_DIR)
        self.assertTrue(code_options_need_patch(options, SUPPORTED_TAG))
        self.assertFalse(code_options_need_patch(options, NATIVE_TAG))

    def test_ok_to_mqtt_macro_switches_to_the_upstream_name_on_native_firmware(self):
        _canonical, patched = validate_code_options(ROOT_DIR, {"okToMqtt": True}, SUPPORTED_TAG)
        _canonical, native = validate_code_options(ROOT_DIR, {"okToMqtt": True}, NATIVE_TAG)
        self.assertIn("USERPREFS_CONFIG_LORA_OK_TO_MQTT", patched)
        self.assertIn("USERPREFS_CONFIG_LORA_CONFIG_OK_TO_MQTT", native)
        self.assertNotIn("USERPREFS_CONFIG_LORA_OK_TO_MQTT", native)

    def test_channel_cap_widens_on_native_firmware(self):
        options = load_build_options(ROOT_DIR)
        self.assertEqual(max_channels(options, SUPPORTED_TAG), 3)
        self.assertEqual(max_channels(options, NATIVE_TAG), 8)

    def test_no_options_returns_nothing(self):
        self.assertEqual(validate_code_options(ROOT_DIR, None, SUPPORTED_TAG), (None, {}))
        self.assertEqual(validate_code_options(ROOT_DIR, {}, SUPPORTED_TAG), (None, {}))

    def test_ok_to_mqtt_emits_string_macro(self):
        canonical, macros = validate_code_options(ROOT_DIR, {"okToMqtt": True}, SUPPORTED_TAG)
        self.assertEqual(canonical, {"okToMqtt": True})
        self.assertEqual(macros, {"USERPREFS_CONFIG_LORA_OK_TO_MQTT": "true"})

    def test_custom_lora_fills_defaults_and_disables_preset(self):
        canonical, macros = validate_code_options(
            ROOT_DIR,
            {"customLora": {"spreadFactor": 9}},
            SUPPORTED_TAG,
        )
        self.assertEqual(canonical["customLora"]["spreadFactor"], 9)
        self.assertEqual(canonical["customLora"]["bandwidthKhz"], 62)
        self.assertEqual(macros["USERPREFS_LORACONFIG_USE_PRESET"], "false")
        self.assertEqual(macros["USERPREFS_LORACONFIG_SPREAD_FACTOR"], "9")
        self.assertEqual(macros["USERPREFS_LORACONFIG_BANDWIDTH"], "62")
        self.assertEqual(macros["USERPREFS_LORACONFIG_OVERRIDE_FREQUENCY"], "869.618")
        for value in macros.values():
            self.assertIsInstance(value, str)

    def test_custom_lora_accepts_spread_factor_5_and_override_frequency(self):
        canonical, macros = validate_code_options(
            ROOT_DIR,
            {"customLora": {"spreadFactor": 5, "overrideFrequencyMhz": 869.525}},
            SUPPORTED_TAG,
        )
        self.assertEqual(canonical["customLora"]["spreadFactor"], 5)
        self.assertEqual(canonical["customLora"]["overrideFrequencyMhz"], 869.525)
        self.assertEqual(macros["USERPREFS_LORACONFIG_SPREAD_FACTOR"], "5")
        self.assertEqual(macros["USERPREFS_LORACONFIG_OVERRIDE_FREQUENCY"], "869.525")

    def test_rejects_out_of_range_and_unknown_values(self):
        cases = [
            {"okToMqtt": "yes"},
            {"customLora": {"spreadFactor": 13}},
            {"customLora": {"spreadFactor": 4}},
            {"customLora": {"overrideFrequencyMhz": 1200}},
            {"customLora": {"overrideFrequencyMhz": "869.5"}},
            {"customLora": {"codingRate": 4}},
            {"customLora": {"bandwidthKhz": 300}},
            {"customLora": {"channelNum": 256}},
            {"customLora": {"nope": 1}},
            {"unknownOption": True},
            {"customLora": "wide"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    validate_code_options(ROOT_DIR, payload, SUPPORTED_TAG)

    def test_rejects_firmware_below_minimum_version(self):
        with self.assertRaises(ValueError) as ctx:
            validate_code_options(ROOT_DIR, {"okToMqtt": True}, OLD_TAG)
        self.assertIn("2.6.4", str(ctx.exception))


class CodeOptionSubmissionTests(unittest.TestCase):
    def test_submission_stores_options_and_injects_macros(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            initialize_database(config)
            seed_template(config, SUPPORTED_TAG)

            result = create_build_submission(
                config,
                {
                    "deviceId": "tbeam",
                    "firmwareTag": SUPPORTED_TAG,
                    "prefsJsonc": '{"USERPREFS_CONFIG_OWNER_SHORT_NAME": "TST"}',
                    "codeOptions": {"okToMqtt": True, "customLora": {"bandwidthKhz": 125}},
                },
            )

            prefs = json.loads(result["row"]["prefs_jsonc"])
            self.assertEqual(prefs["USERPREFS_CONFIG_LORA_OK_TO_MQTT"], "true")
            self.assertEqual(prefs["USERPREFS_LORACONFIG_USE_PRESET"], "false")
            self.assertEqual(prefs["USERPREFS_LORACONFIG_BANDWIDTH"], "125")
            self.assertEqual(prefs["USERPREFS_CONFIG_OWNER_SHORT_NAME"], "TST")
            self.assertEqual(
                json.loads(result["row"]["code_options"])["customLora"]["bandwidthKhz"],
                125,
            )
            self.assertEqual(result["public"]["codeOptions"]["okToMqtt"], True)

    def test_submission_without_options_leaves_column_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            initialize_database(config)
            seed_template(config, SUPPORTED_TAG)

            result = create_build_submission(
                config,
                {
                    "deviceId": "tbeam",
                    "firmwareTag": SUPPORTED_TAG,
                    "prefsJsonc": "{}",
                },
            )

            self.assertIsNone(result["row"]["code_options"])
            self.assertIsNone(result["public"]["codeOptions"])
            self.assertNotIn("USERPREFS_LORACONFIG_USE_PRESET", result["row"]["prefs_jsonc"])

    def test_users_cannot_set_synthetic_macros_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            initialize_database(config)
            seed_template(config, SUPPORTED_TAG)

            with self.assertRaises(JsoncValidationError):
                create_build_submission(
                    config,
                    {
                        "deviceId": "tbeam",
                        "firmwareTag": SUPPORTED_TAG,
                        "prefsJsonc": '{"USERPREFS_CONFIG_LORA_OK_TO_MQTT": "true"}',
                    },
                )


class CodeOptionBuilderTests(unittest.TestCase):
    def build_row(self, code_options=None, firmware_tag=SUPPORTED_TAG):
        return {
            "public_token": "token-123",
            "device_id": "tbeam",
            "platformio_env": "tbeam",
            "firmware_tag": firmware_tag,
            "firmware_sha": "abc123",
            "prefs_jsonc": '{"USERPREFS_ALLOWED": "true"}\n',
            "code_options": code_options,
        }

    def run_and_capture_inputs(self, code_options, firmware_tag=SUPPORTED_TAG):
        """Run a fake build and return (input dir listing, BUILD_INFO.txt contents)."""
        seen: list[str] = []
        real_fake_build = run_fake_build

        def spy(build, input_dir, final_zip):
            # Recursive: patches now live in an input subdirectory so the
            # container's glob can never pick up userPrefs.jsonc.
            seen.extend(sorted(str(path.relative_to(input_dir)) for path in input_dir.rglob("*")))
            return real_fake_build(build, input_dir, final_zip)

        with tempfile.TemporaryDirectory() as tmp:
            config = replace(temp_config(Path(tmp)), builder_mode="fake")
            with patch("meshtastic_builder.builder.run_fake_build", side_effect=spy):
                artifact = run_build(config, self.build_row(code_options, firmware_tag))
            with zipfile.ZipFile(artifact.path) as zf:
                return seen, zf.read("BUILD_INFO.txt").decode("utf-8")

    def test_patch_is_shipped_and_recorded_when_options_present(self):
        inputs, info = self.run_and_capture_inputs('{"okToMqtt": true}')
        self.assertIn("patches/userprefs-ext.patch", inputs)
        self.assertIn('code_options={"okToMqtt": true}', info)

    def test_no_patch_shipped_when_firmware_reads_the_macros_natively(self):
        inputs, info = self.run_and_capture_inputs('{"okToMqtt": true}', NATIVE_TAG)
        self.assertNotIn("patches/userprefs-ext.patch", inputs)
        self.assertIn('code_options={"okToMqtt": true}', info)

    def test_no_patch_shipped_without_code_options(self):
        inputs, info = self.run_and_capture_inputs(None)
        self.assertNotIn("patches/userprefs-ext.patch", inputs)
        self.assertIn("code_options=none", info)

    def test_patch_failure_is_named_not_dumped(self):
        with self.assertRaises(BuildFailure) as ctx:
            raise_build_failure(
                3,
                "applying...\nMB_FAILURE code=patch_failed phase=patches detail=userprefs-ext.patch\n",
            )
        self.assertEqual(ctx.exception.code, "patch_failed")
        self.assertEqual(ctx.exception.phase, "patches")
        self.assertEqual(ctx.exception.detail, "userprefs-ext.patch")


class CodeOptionMigrationTests(unittest.TestCase):
    def test_initialize_database_adds_missing_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            config.db_path.parent.mkdir(parents=True, exist_ok=True)
            legacy = sqlite3.connect(config.db_path)
            legacy.executescript(
                """
                CREATE TABLE build_requests (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  public_token TEXT NOT NULL UNIQUE,
                  email TEXT NOT NULL,
                  device_id TEXT NOT NULL,
                  platformio_env TEXT NOT NULL,
                  firmware_tag TEXT NOT NULL,
                  firmware_sha TEXT NOT NULL,
                  prefs_jsonc TEXT NOT NULL,
                  prefs_hash TEXT NOT NULL,
                  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'expired')),
                  attempts INTEGER NOT NULL DEFAULT 0,
                  artifact_path TEXT,
                  artifact_sha256 TEXT,
                  artifact_size_bytes INTEGER,
                  error_message TEXT,
                  build_log TEXT,
                  worker_id TEXT,
                  created_at TEXT NOT NULL,
                  started_at TEXT,
                  finished_at TEXT,
                  expires_at TEXT
                );
                """
            )
            legacy.commit()
            legacy.close()

            initialize_database(config)

            conn = sqlite3.connect(config.db_path)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(build_requests)")}
            conn.close()
            self.assertIn("code_options", columns)
            self.assertNotIn("email", columns)

    def test_public_view_tolerates_rows_without_code_options(self):
        row = {
            "public_token": "t",
            "status": "queued",
            "device_id": "tbeam",
            "platformio_env": "tbeam",
            "firmware_tag": SUPPORTED_TAG,
            "firmware_sha": "abc",
            "attempts": 0,
            "created_at": "now",
            "started_at": None,
            "finished_at": None,
            "expires_at": None,
            "artifact_sha256": None,
            "artifact_size_bytes": None,
            "error_message": None,
        }
        self.assertIsNone(public_build_view(row)["codeOptions"])


if __name__ == "__main__":
    unittest.main()


class FixedGpsPatchTests(unittest.TestCase):
    """The 2.8 fixed-position build fix (upstream PR #11825).

    Only the patch is version-gated. Fixed position itself works on every
    supported tag: below 2.8.0 the firmware compiles that block as shipped.
    """

    def setUp(self):
        self.options = load_build_options(ROOT_DIR)
        self.keys = {"USERPREFS_FIXED_GPS", "USERPREFS_FIXED_GPS_LAT", "USERPREFS_FIXED_GPS_LON"}

    def test_needed_only_from_2_8_0(self):
        self.assertTrue(fixed_gps_patch_needed(self.options, NATIVE_TAG, self.keys))
        self.assertFalse(fixed_gps_patch_needed(self.options, SUPPORTED_TAG, self.keys))
        self.assertFalse(fixed_gps_patch_needed(self.options, OLD_TAG, self.keys))

    def test_not_needed_without_a_fixed_position(self):
        self.assertFalse(fixed_gps_patch_needed(self.options, NATIVE_TAG, {"USERPREFS_TZ_STRING"}))

    def test_shipped_options_skip_the_patch_from_2_8_1(self):
        # v2.8.1 already carries PR #11825, so the patch no longer applies there.
        self.assertTrue(fixed_gps_patch_needed(self.options, "v2.8.0.7239fe8", self.keys))
        self.assertFalse(fixed_gps_patch_needed(self.options, "v2.8.1.8e6a88d", self.keys))

    def test_stops_once_a_release_carries_the_upstream_fix(self):
        options = dict(self.options)
        options["fixedGpsPatch"] = dict(options["fixedGpsPatch"], fixedSinceFirmwareVersion="2.8.1")
        self.assertTrue(fixed_gps_patch_needed(options, NATIVE_TAG, self.keys))
        self.assertFalse(fixed_gps_patch_needed(options, "v2.8.1.abc1234", self.keys))

    def test_patch_ships_only_for_a_fixed_position_build_on_2_8(self):
        prefs_with_gps = (
            '{"USERPREFS_ALLOWED": "true", "USERPREFS_FIXED_GPS": "",\n'
            ' "USERPREFS_FIXED_GPS_LAT": "40.4285", "USERPREFS_FIXED_GPS_LON": "-0.3226"}\n'
        )
        seen: list[str] = []
        real_fake_build = run_fake_build

        def spy(build, input_dir, final_zip):
            seen.extend(sorted(str(p.relative_to(input_dir)) for p in input_dir.rglob("*")))
            return real_fake_build(build, input_dir, final_zip)

        def run(prefs, tag):
            seen.clear()
            with tempfile.TemporaryDirectory() as tmp:
                config = replace(temp_config(Path(tmp)), builder_mode="fake")
                build = {
                    "public_token": "token-fixed-gps",
                    "device_id": "tbeam",
                    "platformio_env": "tbeam",
                    "firmware_tag": tag,
                    "firmware_sha": "abc123",
                    "prefs_jsonc": prefs,
                    "code_options": None,
                }
                with patch("meshtastic_builder.builder.run_fake_build", side_effect=spy):
                    run_build(config, build)
            return list(seen)

        self.assertIn("patches/fixed-gps-nodedb.patch", run(prefs_with_gps, NATIVE_TAG))
        self.assertNotIn("patches/fixed-gps-nodedb.patch", run(prefs_with_gps, SUPPORTED_TAG))
        self.assertNotIn(
            "patches/fixed-gps-nodedb.patch",
            run('{"USERPREFS_ALLOWED": "true"}\n', NATIVE_TAG),
        )
