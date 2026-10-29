"""The compile step of docker/build_firmware.sh, run with a fake `pio`.

Only the compile block is executed (extracted between its phase banner and the
packaging phase), so these tests need no firmware checkout or Docker.
"""

import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "docker" / "build_firmware.sh"
BASH = shutil.which("bash") or "/bin/bash"


def compile_block() -> str:
    text = SCRIPT.read_text(encoding="utf-8")
    match = re.search(r'phase "compile \$\{PIO_ENV\}"\n(?P<body>.*?)\n# Only what a flasher consumes', text, re.S)
    assert match, "compile block not found in build_firmware.sh"
    return match.group("body")


def run_compile(pio_output: str, *, fails: int) -> tuple[subprocess.CompletedProcess, int]:
    """Run the compile block with a pio that prints `pio_output` and fails `fails` times."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        calls = tmp_path / "calls"
        calls.write_text("0")
        pio = tmp_path / "pio"
        pio.write_text(
            "#!/usr/bin/env bash\n"
            f'n=$(( $(cat "{calls}") + 1 )); echo "$n" > "{calls}"\n'
            f"cat <<'EOF'\n{pio_output}\nEOF\n"
            f'[ "$n" -gt {fails} ]\n'
        )
        pio.chmod(pio.stat().st_mode | stat.S_IEXEC)
        script = (
            "set -euo pipefail\n"
            "PIO_ENV=test-env\n"
            "phase() { :; }\n"
            "use_native_sreccat() { :; }\n"
            'fail() { echo "MB_FAILURE code=$1 phase=$2 detail=$3" >&2; exit "${4:-1}"; }\n'
            + compile_block()
            + "\necho COMPILED\n"
        )
        proc = subprocess.run(
            [BASH, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        )
        return proc, int(calls.read_text())


OVERFLOW = (
    "/opt/platformio/packages/toolchain-gccarmnoneeabi/bin/ld: "
    "region `FLASH' overflowed by 77752 bytes\n"
    "collect2: error: ld returned 1 exit status\n"
    "*** [.pio/build/test-env/firmware.elf] Error 1"
)


@unittest.skipUnless(Path(BASH).exists(), "bash not available")
class CompileRetryTests(unittest.TestCase):
    def test_flash_overflow_fails_once_without_retry(self):
        proc, calls = run_compile(OVERFLOW, fails=99)
        self.assertEqual(calls, 1)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(
            "MB_FAILURE code=firmware_too_big phase=compile detail=region `FLASH' overflowed by 77752 bytes",
            proc.stderr,
        )
        self.assertNotIn("COMPILED", proc.stdout)

    def test_other_failure_is_retried_once(self):
        # pioarduino swapping tool-scons mid-run: the second run succeeds.
        proc, calls = run_compile("ModuleNotFoundError: No module named 'SCons.Tool.FortranCommon'", fails=1)
        self.assertEqual(calls, 2)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("COMPILED", proc.stdout)

    def test_genuine_compile_error_still_fails_after_the_retry(self):
        proc, calls = run_compile("src/main.cpp:1:1: error: boom", fails=99)
        self.assertEqual(calls, 2)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("MB_FAILURE", proc.stderr)

    def test_success_runs_pio_once_and_keeps_its_output(self):
        proc, calls = run_compile("========== [SUCCESS] Took 1.00 seconds ==========", fails=0)
        self.assertEqual(calls, 1)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("[SUCCESS]", proc.stdout)


if __name__ == "__main__":
    unittest.main()
