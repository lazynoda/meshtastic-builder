import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

from meshtastic_builder.admin import (
    docker_status,
    extract_platformio_envs,
    set_firmware_supported,
    validate_devices_against_repo,
)
from meshtastic_builder.config import load_config
from meshtastic_builder.db import get_firmware_version, initialize_database, upsert_firmware_versions


class AdminTests(unittest.TestCase):
    def test_extract_platformio_envs_from_variant_ini_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            variant = root / "variants" / "esp32" / "tbeam"
            variant.mkdir(parents=True)
            (variant / "platformio.ini").write_text(
                "[env:tbeam]\nextends = esp32_base\n\n[env:tbeam-displayshield]\n",
                encoding="utf-8",
            )

            envs = extract_platformio_envs(root)

            self.assertEqual(envs["tbeam"], Path("variants/esp32/tbeam/platformio.ini"))
            self.assertEqual(envs["tbeam-displayshield"], Path("variants/esp32/tbeam/platformio.ini"))

    def test_validate_devices_against_repo_reports_missing_envs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "firmware"
            variant = repo / "variants" / "esp32" / "tbeam"
            variant.mkdir(parents=True)
            (variant / "platformio.ini").write_text("[env:tbeam]\n", encoding="utf-8")
            config = replace(load_config(), root_dir=Path.cwd())

            results = validate_devices_against_repo(config, repo)

            by_id = {item["device_id"]: item for item in results}
            self.assertTrue(by_id["tbeam"]["valid"])
            self.assertFalse(by_id["heltec-v3"]["valid"])

    def test_set_firmware_supported_toggles_cached_tag(self):
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

            set_firmware_supported(config, "v-test", False)
            self.assertEqual(get_firmware_version(config, "v-test")["supported"], 0)
            set_firmware_supported(config, "v-test", True)
            self.assertEqual(get_firmware_version(config, "v-test")["supported"], 1)

    def test_docker_status_reports_success(self):
        config = replace(load_config(), docker_binary="docker")
        with patch("meshtastic_builder.admin.subprocess.run") as run:
            run.return_value = CompletedProcess(args=["docker"], returncode=0, stdout='{"ServerVersion":"x"}', stderr="")

            status = docker_status(config, timeout_seconds=1)

        self.assertTrue(status["ok"])
        self.assertEqual(status["error"], "")

    def test_docker_status_reports_timeout(self):
        config = replace(load_config(), docker_binary="docker")
        with patch("meshtastic_builder.admin.subprocess.run") as run:
            run.side_effect = TimeoutExpired(cmd=["docker"], timeout=1)

            status = docker_status(config, timeout_seconds=1)

        self.assertFalse(status["ok"])
        self.assertIn("timed out", status["error"])


if __name__ == "__main__":
    unittest.main()
