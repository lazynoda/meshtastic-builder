import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from meshtastic_builder.config import load_config
from meshtastic_builder.db import (
    create_build_request,
    get_build_by_token,
    initialize_database,
    upsert_firmware_versions,
)
from meshtastic_builder.worker import process_one


class FakeWorkerFlowTests(unittest.TestCase):
    def test_worker_processes_build_to_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = replace(
                load_config(),
                data_dir=tmp_path,
                db_path=tmp_path / "test.sqlite",
                artifact_dir=tmp_path / "artifacts",
                job_dir=tmp_path / "jobs",
                cache_dir=tmp_path / "cache",
                builder_mode="fake",
                base_url="http://example.test",
            )
            initialize_database(config)
            upsert_firmware_versions(
                config,
                [
                    {
                        "tag": "v-test",
                        "sha": "abc123",
                        "release_name": "v-test",
                        "supported": 1,
                    }
                ],
            )
            build = create_build_request(
                config,
                device_id="tbeam",
                platformio_env="tbeam",
                firmware_tag="v-test",
                firmware_sha="abc123",
                prefs_jsonc='{"USERPREFS_CONFIG_OWNER_SHORT_NAME": "TST"}\n',
            )

            self.assertTrue(process_one(config, "test-worker"))
            updated = get_build_by_token(config, build["public_token"])
            self.assertIsNotNone(updated)
            self.assertEqual(updated["status"], "succeeded")
            self.assertTrue(Path(updated["artifact_path"]).exists())


if __name__ == "__main__":
    unittest.main()

