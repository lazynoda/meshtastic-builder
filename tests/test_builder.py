import os
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from meshtastic_builder.builder import docker_transport, run_build, run_docker_build
from meshtastic_builder.config import load_config


def test_build(token="token-123"):
    return {
        "public_token": token,
        "device_id": "tbeam",
        "platformio_env": "tbeam",
        "firmware_tag": "v-test",
        "firmware_sha": "abc123",
        "prefs_jsonc": '{"USERPREFS_ALLOWED": true}\n',
    }


class BuilderTests(unittest.TestCase):
    def test_fake_build_creates_zip_with_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = replace(
                load_config(),
                data_dir=tmp_path,
                artifact_dir=tmp_path / "artifacts",
                job_dir=tmp_path / "jobs",
                builder_mode="fake",
            )

            artifact = run_build(config, test_build())

            self.assertTrue(artifact.path.exists())
            self.assertGreater(artifact.size_bytes, 0)
            with zipfile.ZipFile(artifact.path) as zf:
                names = set(zf.namelist())
                self.assertIn("BUILD_INFO.txt", names)
                self.assertIn("userPrefs.jsonc", names)
                self.assertIn("firmware-tbeam.txt", names)

    def test_docker_build_invokes_expected_command_and_copies_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            final_zip = tmp_path / "final.zip"
            input_dir.mkdir()
            output_dir.mkdir()
            produced = output_dir / "produced.zip"
            produced.write_bytes(b"zip-content")
            config = replace(
                load_config(),
                root_dir=tmp_path,
                docker_binary="docker",
                docker_network="none",
                docker_transport="bind",
                docker_cpus="3",
                docker_memory="5g",
                docker_pids_limit=256,
                builder_image="builder:test",
                build_timeout_seconds=123,
            )

            with patch("meshtastic_builder.builder.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "ok"
                run.return_value.stderr = ""
                log = run_docker_build(config, test_build(), input_dir, output_dir, final_zip)

            self.assertEqual(log, "ok")
            self.assertEqual(final_zip.read_bytes(), b"zip-content")
            command = run.call_args.args[0]
            self.assertIn("--rm", command)
            self.assertIn("--network", command)
            self.assertIn("none", command)
            self.assertIn("--cpus", command)
            self.assertIn("3", command)
            self.assertIn("--memory", command)
            self.assertIn("5g", command)
            self.assertIn("--pids-limit", command)
            self.assertIn("256", command)
            self.assertIn("builder:test", command)
            self.assertEqual(command[-3:], ["v-test", "abc123", "tbeam"])

    def test_docker_build_failure_raises_with_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            final_zip = tmp_path / "final.zip"
            input_dir.mkdir()
            output_dir.mkdir()
            config = replace(load_config(), root_dir=tmp_path, docker_transport="bind")

            with patch("meshtastic_builder.builder.subprocess.run") as run:
                run.return_value.returncode = 42
                run.return_value.stdout = "stdout"
                run.return_value.stderr = "stderr"
                with self.assertRaises(RuntimeError) as ctx:
                    run_docker_build(config, test_build(), input_dir, output_dir, final_zip)

            self.assertIn("exit code 42", str(ctx.exception))
            self.assertIn("stderr", str(ctx.exception))

    def test_auto_docker_transport_uses_copy_for_remote_docker_host(self):
        config = replace(load_config(), docker_transport="auto")
        with patch.dict(os.environ, {"DOCKER_HOST": "ssh://docker-host.example"}):
            self.assertEqual(docker_transport(config), "copy")
        with patch.dict(os.environ, {"DOCKER_HOST": ""}):
            self.assertEqual(docker_transport(config), "bind")

    def test_docker_copy_transport_copies_inputs_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            final_zip = tmp_path / "final.zip"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "userPrefs.jsonc").write_text("{}\n", encoding="utf-8")
            config = replace(
                load_config(),
                root_dir=tmp_path,
                docker_binary="docker",
                docker_network="none",
                docker_transport="copy",
                docker_cpus="3",
                docker_memory="5g",
                docker_pids_limit=256,
                builder_image="builder:test",
                build_timeout_seconds=123,
            )

            def fake_run(command, **kwargs):
                if command[:2] == ["docker", "create"]:
                    return CompletedProcess(command, 0, stdout="cid123\n", stderr="")
                if command == ["docker", "cp", f"{input_dir.resolve()}/.", "cid123:/work/input"]:
                    return CompletedProcess(command, 0, stdout="", stderr="")
                if command == ["docker", "start", "-a", "cid123"]:
                    return CompletedProcess(command, 0, stdout="build ok\n", stderr="")
                if command == ["docker", "cp", "cid123:/work/output/.", str(output_dir.resolve())]:
                    (output_dir / "produced.zip").write_bytes(b"zip-content")
                    return CompletedProcess(command, 0, stdout="", stderr="")
                if command == ["docker", "rm", "-f", "cid123"]:
                    return CompletedProcess(command, 0, stdout="", stderr="")
                raise AssertionError(f"unexpected command: {command}")

            with patch("meshtastic_builder.builder.subprocess.run", side_effect=fake_run) as run:
                log = run_docker_build(config, test_build(), input_dir, output_dir, final_zip)

            self.assertIn("build ok", log)
            self.assertEqual(final_zip.read_bytes(), b"zip-content")
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(commands[0][:2], ["docker", "create"])
            self.assertIn("3", commands[0])
            self.assertIn("5g", commands[0])
            self.assertIn("256", commands[0])
            self.assertEqual(commands[-1], ["docker", "rm", "-f", "cid123"])


if __name__ == "__main__":
    unittest.main()
