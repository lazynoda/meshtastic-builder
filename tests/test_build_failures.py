import unittest

from meshtastic_builder.build_failures import (
    CODE_COMPILE_ERROR,
    CODE_FIRMWARE_TOO_BIG,
    CODE_NO_ARTIFACTS,
    CODE_PATCH_FAILED,
    CODE_UNKNOWN,
    BuildFailure,
    classify_build_log,
    failure_summary,
)


COMPILE_LOG = """
Compiling .pio/build/nrf52_promicro_diy_tcxo/src/mesh/NodeDB.cpp.o
src/mesh/NodeDB.cpp: In constructor 'NodeDB::NodeDB()':
src/mesh/NodeDB.cpp:705:27: error: 'info' was not declared in this scope
*** [.pio/build/nrf52_promicro_diy_tcxo/src/mesh/NodeDB.cpp.o] Error 1
"""


class ClassifyTests(unittest.TestCase):
    def test_a_tool_that_cannot_run_is_infrastructure_not_unknown(self):
        # Real tail of an nRF54 build on an arm64 image with a 32-bit srec_cat.
        log = (
            "(.text._read_r+0x10): warning: _read is not implemented and will always fail\n"
            "sh: 1: /opt/platformio/packages/tool-sreccat/srec_cat: not found\n"
            "*** [.pio/build/xiao_nrf54l15_lr2021/firmware.hex] Error 127\n"
        )
        code, phase, detail = classify_build_log(log)
        self.assertEqual(code, "infrastructure")
        self.assertEqual(phase, "compile")
        self.assertIn("srec_cat: not found", detail)

    def test_not_found_without_error_127_is_not_classified(self):
        self.assertEqual(classify_build_log("sh: 1: foo: not found\n")[0], CODE_UNKNOWN)

    def test_builder_marker_wins(self):
        log = "applying\nMB_FAILURE code=patch_failed phase=patches detail=fixed-gps-nodedb.patch\n"
        self.assertEqual(
            classify_build_log(log),
            (CODE_PATCH_FAILED, "patches", "fixed-gps-nodedb.patch"),
        )

    def test_marker_without_detail(self):
        code, phase, detail = classify_build_log("MB_FAILURE code=no_artifacts phase=package\n")
        self.assertEqual((code, phase, detail), (CODE_NO_ARTIFACTS, "package", ""))

    def test_unknown_marker_code_does_not_leak_through(self):
        code, _phase, _detail = classify_build_log("MB_FAILURE code=whatever phase=package\n")
        self.assertEqual(code, CODE_UNKNOWN)

    def test_compiler_diagnostic_is_found_and_quoted(self):
        code, phase, detail = classify_build_log(COMPILE_LOG)
        self.assertEqual((code, phase), (CODE_COMPILE_ERROR, "compile"))
        self.assertEqual(detail, "src/mesh/NodeDB.cpp:705:27: error: 'info' was not declared in this scope")

    def test_flash_overflow_gets_its_own_code(self):
        log = "/usr/bin/ld: region `FLASH' overflowed by 4096 bytes\ncollect2: error: ld returned 1\n"
        code, _phase, detail = classify_build_log(log)
        self.assertEqual(code, CODE_FIRMWARE_TOO_BIG)
        self.assertIn("overflowed by 4096 bytes", detail)

    def test_nothing_recognisable_stays_unknown(self):
        self.assertEqual(classify_build_log("just some chatter\n"), (CODE_UNKNOWN, "", ""))

    def test_secrets_in_the_flag_dump_are_never_quoted(self):
        """The detail line is shown to the user, and the log carries the -D dump."""
        log = (
            '-DUSERPREFS_NETWORK_WIFI_PSK=\\"hunter2\\"\n'
            '-DUSERPREFS_MQTT_PASSWORD=\\"large4cats\\"\n'
            "make: *** error: something went wrong\n"
        )
        _code, _phase, detail = classify_build_log(log)
        self.assertNotIn("hunter2", detail)
        self.assertNotIn("large4cats", detail)

    def test_detail_is_clipped(self):
        long_error = "src/a.cpp:1:1: error: " + ("x" * 500)
        _code, _phase, detail = classify_build_log(long_error)
        self.assertLessEqual(len(detail), 300)


class BuildFailureTests(unittest.TestCase):
    def test_unknown_code_is_normalised(self):
        self.assertEqual(BuildFailure("not-a-code").code, CODE_UNKNOWN)

    def test_detail_is_collapsed_to_one_line(self):
        failure = BuildFailure(CODE_COMPILE_ERROR, detail="line one\n   line two")
        self.assertEqual(failure.detail, "line one line two")

    def test_summary_leads_the_stored_log(self):
        summary = failure_summary(CODE_COMPILE_ERROR, "compile", "boom")
        self.assertTrue(summary.startswith("===== BUILD FAILED ====="))
        self.assertIn("code:   compile_error", summary)
        self.assertIn("phase:  compile", summary)
        self.assertIn("detail: boom", summary)


if __name__ == "__main__":
    unittest.main()
