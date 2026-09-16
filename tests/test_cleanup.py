import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from meshtastic_builder.cleanup import expire_old_artifacts
from meshtastic_builder.config import load_config
from meshtastic_builder.db import (
    connection,
    create_build_request,
    get_build_by_token,
    initialize_database,
    mark_build_success,
    utc_now,
)


class CleanupTests(unittest.TestCase):
    def test_expire_old_artifacts_deletes_zip_and_marks_expired(self):
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
            artifact = config.artifact_dir / "artifact.zip"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(b"zip")
            build = create_build_request(
                config,
                device_id="tbeam",
                platformio_env="tbeam",
                firmware_tag="v-test",
                firmware_sha="abc123",
                prefs_jsonc='{"USERPREFS_ALLOWED": true}\n',
            )
            mark_build_success(
                config,
                build["id"],
                artifact_path=artifact,
                artifact_sha256="sha",
                artifact_size_bytes=artifact.stat().st_size,
                build_log="ok",
            )
            past = (utc_now() - timedelta(seconds=1)).isoformat()
            with connection(config) as conn:
                conn.execute("UPDATE build_requests SET expires_at = ? WHERE id = ?", (past, build["id"]))

            self.assertEqual(expire_old_artifacts(config), 1)
            updated = get_build_by_token(config, build["public_token"])
            self.assertEqual(updated["status"], "expired")
            self.assertFalse(artifact.exists())


if __name__ == "__main__":
    unittest.main()
