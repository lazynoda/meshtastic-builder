import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from meshtastic_builder.config import load_config
from meshtastic_builder.db import initialize_database, public_build_view, upsert_firmware_versions
from meshtastic_builder.firmware import userprefs_cache_path
from meshtastic_builder.submissions import create_build_submission


class SubmissionTests(unittest.TestCase):
    def test_create_build_submission_resolves_tag_and_normalizes_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = replace(
                load_config(),
                data_dir=tmp_path,
                db_path=tmp_path / "test.sqlite",
                artifact_dir=tmp_path / "artifacts",
                job_dir=tmp_path / "jobs",
                cache_dir=tmp_path / "cache",
                base_url="http://example.test",
            )
            initialize_database(config)
            upsert_firmware_versions(
                config,
                [{"tag": "v-test", "sha": "abc123", "release_name": "v-test", "supported": 1}],
            )
            template_path = userprefs_cache_path(config, "v-test")
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text(
                '{"USERPREFS_CONFIG_OWNER_LONG_NAME": "", "USERPREFS_CONFIG_OWNER_SHORT_NAME": "DEF", "USERPREFS_TZ_STRING": "CET-1CEST,M3.5.0,M10.5.0/3"}',
                encoding="utf-8",
            )

            result = create_build_submission(
                config,
                {
                    "deviceId": "tbeam",
                    "firmwareTag": "v-test",
                    "prefsJsonc": '{"USERPREFS_CONFIG_OWNER_LONG_NAME": "Test Node", "USERPREFS_CONFIG_OWNER_SHORT_NAME": "TST",}',
                },
            )

            self.assertEqual(result["public"]["firmwareTag"], "v-test")
            self.assertIn(result["public"]["token"], result["buildUrl"])
            self.assertIn(result["public"]["token"], result["downloadUrl"])
            self.assertIn('"USERPREFS_CONFIG_OWNER_SHORT_NAME": "TST"', result["row"]["prefs_jsonc"])
            self.assertIn('"USERPREFS_TZ_STRING": "CET-1CEST,M3.5.0,M10.5.0/3"', result["row"]["prefs_jsonc"])
            self.assertEqual(result["public"]["ownerShortName"], "TST")

    def test_owner_names_are_required(self):
        # The form used to prefill them and many nodes went out unnamed; the API
        # must refuse a build without both, including whitespace-only names.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = replace(
                load_config(),
                data_dir=tmp_path,
                db_path=tmp_path / "test.sqlite",
                artifact_dir=tmp_path / "artifacts",
                job_dir=tmp_path / "jobs",
                cache_dir=tmp_path / "cache",
            )
            initialize_database(config)
            upsert_firmware_versions(config, [{"tag": "v-test", "sha": "abc123", "supported": 1}])
            template_path = userprefs_cache_path(config, "v-test")
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text(
                '{"USERPREFS_CONFIG_OWNER_LONG_NAME": "", "USERPREFS_CONFIG_OWNER_SHORT_NAME": ""}',
                encoding="utf-8",
            )
            cases = [
                "{}",
                '{"USERPREFS_CONFIG_OWNER_LONG_NAME": "Nodo Azotea"}',
                '{"USERPREFS_CONFIG_OWNER_SHORT_NAME": "AZO"}',
                '{"USERPREFS_CONFIG_OWNER_LONG_NAME": "   ", "USERPREFS_CONFIG_OWNER_SHORT_NAME": "AZO"}',
            ]
            for prefs in cases:
                with self.subTest(prefs=prefs):
                    with self.assertRaises(ValueError):
                        create_build_submission(
                            config, {"deviceId": "tbeam", "firmwareTag": "v-test", "prefsJsonc": prefs}
                        )
            ok = create_build_submission(
                config,
                {
                    "deviceId": "tbeam",
                    "firmwareTag": "v-test",
                    "prefsJsonc": '{"USERPREFS_CONFIG_OWNER_LONG_NAME": "Nodo Azotea", "USERPREFS_CONFIG_OWNER_SHORT_NAME": "AZO"}',
                },
            )
            self.assertEqual(ok["public"]["ownerLongName"], "Nodo Azotea")

    def test_public_view_exposes_only_the_node_names_from_prefs(self):
        row = {
            "public_token": "t" * 32,
            "status": "queued",
            "device_id": "tbeam",
            "platformio_env": "tbeam",
            "firmware_tag": "v-test",
            "firmware_sha": "abc123",
            "code_options": None,
            "attempts": 0,
            "created_at": "now",
            "started_at": None,
            "finished_at": None,
            "expires_at": None,
            "artifact_sha256": None,
            "artifact_size_bytes": None,
            "error_message": None,
            "prefs_jsonc": (
                '{"USERPREFS_CONFIG_OWNER_LONG_NAME": "lazynoda builder",'
                ' "USERPREFS_CONFIG_OWNER_SHORT_NAME": "lazy",'
                ' "USERPREFS_NETWORK_WIFI_PSK": "hunter2"}'
            ),
        }

        view = public_build_view(row)

        self.assertEqual(view["ownerLongName"], "lazynoda builder")
        self.assertEqual(view["ownerShortName"], "lazy")
        # The ZIP behind the token carries the secrets; the JSON status must not.
        self.assertNotIn("hunter2", str(view))
        self.assertNotIn("prefs_jsonc", view)

    def test_public_view_survives_missing_or_unreadable_prefs(self):
        base = {key: None for key in (
            "public_token", "status", "device_id", "platformio_env", "firmware_tag",
            "firmware_sha", "code_options", "attempts", "created_at", "started_at",
            "finished_at", "expires_at", "artifact_sha256", "artifact_size_bytes",
            "error_message",
        )}
        for prefs in (None, "", "not json", '["a list"]', "{}"):
            with self.subTest(prefs=prefs):
                view = public_build_view({**base, "prefs_jsonc": prefs})
                self.assertIsNone(view["ownerLongName"])
                self.assertIsNone(view["ownerShortName"])

    def test_create_build_submission_rejects_unknown_userpref(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = replace(
                load_config(),
                data_dir=tmp_path,
                db_path=tmp_path / "test.sqlite",
                artifact_dir=tmp_path / "artifacts",
                job_dir=tmp_path / "jobs",
                cache_dir=tmp_path / "cache",
            )
            initialize_database(config)
            upsert_firmware_versions(
                config,
                [{"tag": "v-test", "sha": "abc123", "release_name": "v-test", "supported": 1}],
            )
            template_path = userprefs_cache_path(config, "v-test")
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text('{"USERPREFS_ALLOWED": true}', encoding="utf-8")

            with self.assertRaises(ValueError):
                create_build_submission(
                    config,
                    {
                        "deviceId": "tbeam",
                        "firmwareTag": "v-test",
                        "prefsJsonc": '{"USERPREFS_UNKNOWN": true}',
                    },
                )


if __name__ == "__main__":
    unittest.main()
