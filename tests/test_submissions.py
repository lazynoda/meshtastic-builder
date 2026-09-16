import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from meshtastic_builder.config import load_config
from meshtastic_builder.db import initialize_database, upsert_firmware_versions
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
                '{"USERPREFS_CONFIG_OWNER_SHORT_NAME": "DEF", "USERPREFS_TZ_STRING": "CET-1CEST,M3.5.0,M10.5.0/3"}',
                encoding="utf-8",
            )

            result = create_build_submission(
                config,
                {
                    "deviceId": "tbeam",
                    "firmwareTag": "v-test",
                    "prefsJsonc": '{"USERPREFS_CONFIG_OWNER_SHORT_NAME": "TST",}',
                },
            )

            self.assertEqual(result["public"]["firmwareTag"], "v-test")
            self.assertIn(result["public"]["token"], result["buildUrl"])
            self.assertIn(result["public"]["token"], result["downloadUrl"])
            self.assertIn('"USERPREFS_CONFIG_OWNER_SHORT_NAME": "TST"', result["row"]["prefs_jsonc"])
            self.assertIn('"USERPREFS_TZ_STRING": "CET-1CEST,M3.5.0,M10.5.0/3"', result["row"]["prefs_jsonc"])

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
