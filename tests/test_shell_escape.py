"""String prefs must reach the compiler intact through /bin/sh.

PlatformIO renders a string pref as -DKEY=\\"value\\" (StringifyMacro) and SCons
wraps an argument in double quotes only when it has whitespace (quote_spaces).
These tests rebuild that exact command-line fragment and run it through the
same POSIX shell, so they fail if the escaping drifts from what the shell does.
"""

import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path

from meshtastic_builder.builder import run_build
from meshtastic_builder.config import load_config
from meshtastic_builder.jsonc import prefs_for_compiler, shell_escape_for_compiler, strip_octal_leading_zeros

SH = shutil.which("dash") or "/bin/sh"


def stringify_macro(value: str) -> str:
    # platformio/builder/tools/piobuild.py::StringifyMacro (PlatformIO 6.1.19)
    return '\\"%s\\"' % value.replace('"', '\\\\\\"')


def quote_spaces(arg: str) -> str:
    # SCons/Subst.py::quote_spaces (scons-local 4.8.1)
    if " " in arg or "\t" in arg:
        return '"%s"' % arg
    return arg


def compiler_sees(value: str) -> str:
    """The -D argument the compiler receives for a string pref holding `value`."""
    arg = quote_spaces("-DKEY=" + stringify_macro(value))
    proc = subprocess.run(
        [SH, "-c", "printf '%s\\n' " + arg],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        return f"<shell exit {proc.returncode}: {proc.stderr.strip()}>"
    return proc.stdout.rstrip("\n")


NAMES = [
    "TAC-BEARD7V|P.Coms⚠️",
    "A;B",
    "A&B",
    "A(B)",
    "A<B>C",
    "O'Brien",
    "*",
    "Node?",
    "[x]",
    "~home",
    "#tag",
    "{x}y",
    "λ{x}",
    "Hi!",
    "a^b",
    "plain-name",
    "Ñandú",
]


class ShellEscapeTests(unittest.TestCase):
    def test_names_without_spaces_reach_the_compiler_unchanged(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.assertEqual(compiler_sees(shell_escape_for_compiler(name)), f'-DKEY="{name}"')

    def test_names_with_spaces_reach_the_compiler_unchanged(self):
        for name in ("Mi nodo A|B", "Mi nodo; (x) & <y>", "O'Brien base", "a\tb|c"):
            with self.subTest(name=name):
                escaped = shell_escape_for_compiler(name)
                self.assertEqual(escaped, name)
                self.assertEqual(compiler_sees(escaped), f'-DKEY="{name}"')

    def test_pipe_name_breaks_without_escaping(self):
        # The failure seen in production: the compiler only got the part before the pipe.
        self.assertNotEqual(compiler_sees("TAC-BEARD7V|P.Coms⚠️"), '-DKEY="TAC-BEARD7V|P.Coms⚠️"')

    def test_upstream_single_quoted_host_keeps_its_meaning(self):
        # Upstream writes "'mqtt.example.org'" and relies on the shell dropping the quotes.
        self.assertEqual(shell_escape_for_compiler("'mqtt.meshtastic.es'"), "'mqtt.meshtastic.es'")
        self.assertEqual(compiler_sees("'mqtt.meshtastic.es'"), '-DKEY="mqtt.meshtastic.es"')

    def test_unquoted_firmware_values_are_untouched(self):
        for value in ("{ 0x01, 0x02 }", "42", "-1.5", "0x1F", "true", "meshtastic_Config_X"):
            with self.subTest(value=value):
                self.assertEqual(shell_escape_for_compiler(value), value)

    def test_prefs_for_compiler_only_rewrites_when_needed(self):
        clean = json.dumps({"USERPREFS_CONFIG_OWNER_LONG_NAME": "Node"}, indent=2) + "\n"
        self.assertIs(prefs_for_compiler(clean), clean)
        dirty = json.dumps({"USERPREFS_CONFIG_OWNER_LONG_NAME": "A|B", "USERPREFS_LORACONFIG_CHANNEL_NUM": "4"})
        out = json.loads(prefs_for_compiler(dirty))
        self.assertEqual(out["USERPREFS_CONFIG_OWNER_LONG_NAME"], "A\\|B")
        self.assertEqual(out["USERPREFS_LORACONFIG_CHANNEL_NUM"], "4")


class LeadingZeroTests(unittest.TestCase):
    def test_leading_zeros_are_dropped(self):
        cases = {
            "012389": "12389",
            "000123": "123",
            "09": "9",
            "-007": "-7",
            "0": "0",
            "000": "0",
            "-0": "-0",
            "-000": "0",
            "121212": "121212",
            "10": "10",
            "": "",
            "0.5": "0.5",
            "0x1F": "0x1F",
            "0A": "0A",
            "{ 0x01 }": "{ 0x01 }",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(strip_octal_leading_zeros(value), expected)

    def test_ble_pin_with_leading_zero_reaches_the_compiler_as_decimal(self):
        # Real failure: a PIN starting with 0 and holding an 8 or 9 was read as octal by
        # GCC (`invalid digit "9" in octal constant`); one without 8/9 compiled to another PIN.
        prefs = json.dumps({"USERPREFS_FIXED_BLUETOOTH": "012389"})
        out = json.loads(prefs_for_compiler(prefs))
        # platformio-custom.py passes all-digit values bare (-DKEY=12389), and a C integer
        # literal without a leading 0 is decimal.
        self.assertEqual(out["USERPREFS_FIXED_BLUETOOTH"], "12389")

    def test_stored_request_keeps_the_typed_pin(self):
        prefs = json.dumps({"USERPREFS_FIXED_BLUETOOTH": "121212"})
        self.assertIs(prefs_for_compiler(prefs), prefs)


class StagedPrefsTests(unittest.TestCase):
    def test_build_input_is_escaped_and_stored_prefs_are_not(self):
        prefs = json.dumps({"USERPREFS_CONFIG_OWNER_LONG_NAME": "TAC|X"}) + "\n"
        build = {
            "public_token": "token-esc",
            "device_id": "tbeam",
            "platformio_env": "tbeam",
            "firmware_tag": "v-test",
            "firmware_sha": "abc123",
            "prefs_jsonc": prefs,
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = replace(
                load_config(),
                data_dir=tmp_path,
                artifact_dir=tmp_path / "artifacts",
                job_dir=tmp_path / "jobs",
                builder_mode="fake",
            )
            artifact = run_build(config, build)
            with zipfile.ZipFile(artifact.path) as zf:
                staged = json.loads(zf.read("userPrefs.jsonc"))
        self.assertEqual(staged["USERPREFS_CONFIG_OWNER_LONG_NAME"], "TAC\\|X")
        self.assertEqual(build["prefs_jsonc"], prefs)


if __name__ == "__main__":
    unittest.main()
