import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

import io
from contextlib import redirect_stdout

from meshtastic_builder.admin import (
    docker_status,
    extract_platformio_envs,
    print_build_log,
    set_firmware_supported,
    validate_devices_against_repo,
)
from meshtastic_builder.config import load_config
from meshtastic_builder.db import (
    create_build_request,
    get_firmware_version,
    initialize_database,
    mark_build_failure,
    upsert_firmware_versions,
)


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


class BuildLogTests(unittest.TestCase):
    """`build-log` is how a failure gets triaged without opening SQLite."""

    def _failed_build(self, tmp, log_lines):
        config = replace(
            load_config(),
            data_dir=Path(tmp),
            db_path=Path(tmp) / "test.sqlite",
            artifact_dir=Path(tmp) / "artifacts",
            job_dir=Path(tmp) / "jobs",
            cache_dir=Path(tmp) / "cache",
        )
        initialize_database(config)
        build = create_build_request(
            config,
            device_id="tbeam",
            platformio_env="tbeam",
            firmware_tag="v-test",
            firmware_sha="abc123",
            prefs_jsonc="{}\n",
            code_options=None,
        )
        mark_build_failure(
            config,
            int(build["id"]),
            error_message="src/mesh/NodeDB.cpp:705:27: error: 'info' was not declared in this scope",
            error_code="compile_error",
            build_log="\n".join(log_lines),
        )
        return config, str(build["public_token"])

    def test_prints_the_code_and_the_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, token = self._failed_build(tmp, [f"line {n}" for n in range(100)])
            out = io.StringIO()
            with redirect_stdout(out):
                print_build_log(config, token, tail_lines=5)
            text = out.getvalue()

            self.assertIn("code:     compile_error", text)
            self.assertIn("'info' was not declared", text)
            self.assertIn("line 99", text)
            self.assertNotIn("line 50", text)

    def test_full_prints_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, token = self._failed_build(tmp, [f"line {n}" for n in range(100)])
            out = io.StringIO()
            with redirect_stdout(out):
                print_build_log(config, token, tail_lines=5, full=True)

            self.assertIn("line 0", out.getvalue())

    def test_unknown_token_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, _token = self._failed_build(tmp, ["only line"])
            with self.assertRaises(ValueError):
                print_build_log(config, "not-a-real-token")
