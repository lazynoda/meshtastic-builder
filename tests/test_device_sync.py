import tempfile
import unittest
from pathlib import Path

from meshtastic_builder.device_sync import device_id_for, devices_json, flasher_boards, sync_devices
from meshtastic_builder.devices import Device, load_devices

ROOT = Path(__file__).resolve().parent.parent

INI = """
[env:keep_me]
custom_meshtastic_architecture = nrf52840
custom_meshtastic_actively_supported = true
custom_meshtastic_display_name = Keep Me
board_level = release

[env:new_board]
custom_meshtastic_architecture = esp32-s3
custom_meshtastic_actively_supported = true
custom_meshtastic_display_name = Alpha Board

[env:extra_board]
custom_meshtastic_actively_supported = true
custom_meshtastic_display_name = Extra
board_level = extra

[env:unsupported]
custom_meshtastic_actively_supported = false
custom_meshtastic_display_name = Old

[env:no_name]
custom_meshtastic_actively_supported = true
"""


def device(env, label, family="nrf52840", device_id=None):
    return Device(id=device_id or device_id_for(env), label=label, platformio_env=env, family=family, enabled=True)


class FlasherBoardsTests(unittest.TestCase):
    def test_reads_only_the_web_flasher_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini = Path(tmp) / "variants" / "x" / "platformio.ini"
            ini.parent.mkdir(parents=True)
            ini.write_text(INI, encoding="utf-8")
            boards = flasher_boards(Path(tmp))
        self.assertEqual(sorted(boards), ["keep_me", "new_board"])
        self.assertEqual(boards["new_board"].family, "esp32-s3")
        self.assertEqual(boards["new_board"].label, "Alpha Board")

    def test_rejects_a_directory_that_is_not_a_firmware_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                flasher_boards(Path(tmp))


class SyncTests(unittest.TestCase):
    def boards(self, *items):
        from meshtastic_builder.device_sync import FlasherBoard

        return {env: FlasherBoard(env=env, label=label, family=family, source="x") for env, label, family in items}

    def test_keeps_ids_and_labels_adds_new_and_drops_gone(self):
        current = [
            device("nrf52_promicro_diy_tcxo", "NRF52 Pro-micro DIY", device_id="nrf52-promicro-diy"),
            device("zeta", "Zeta"),
            device("gone_board", "Gone"),
        ]
        boards = self.boards(
            ("nrf52_promicro_diy_tcxo", "Different upstream label", "nrf52840"),
            ("zeta", "Zeta", "nrf52840"),
            ("seeed_wio_tracker_L2", "Beta", "esp32-s3"),
        )
        result = sync_devices(current, boards)
        self.assertEqual([d.id for d in result.devices], ["nrf52-promicro-diy", "seeed-wio-tracker-l2", "zeta"])
        self.assertEqual(result.devices[0].label, "NRF52 Pro-micro DIY")
        self.assertEqual([d.id for d in result.added], ["seeed-wio-tracker-l2"])
        self.assertEqual([d.id for d in result.removed], ["gone-board"])

    def test_shared_display_name_gets_a_suffix(self):
        result = sync_devices([device("a", "Same")], self.boards(("a", "Same", "esp32"), ("b", "Same", "esp32")))
        self.assertEqual(result.added[0].label, "Same (b)")

    def test_family_follows_the_firmware(self):
        result = sync_devices([device("a", "A", family="esp32")], self.boards(("a", "A", "esp32-s3")))
        self.assertEqual(result.devices[0].family, "esp32-s3")
        self.assertEqual(len(result.family_changed), 1)

    def test_no_change_is_a_no_op(self):
        current = [device("a", "A")]
        result = sync_devices(current, self.boards(("a", "A", "nrf52840")))
        self.assertFalse(result.changed)

    def test_shipped_file_round_trips_byte_for_byte(self):
        # The generator's output format is the file's format, so a sync that
        # changes nothing leaves no diff.
        path = ROOT / "data" / "devices.json"
        self.assertEqual(devices_json(load_devices(ROOT)), path.read_text(encoding="utf-8"))

    def test_excluded_family_is_kept_out_and_reported(self):
        result = sync_devices(
            [device("a", "A")],
            self.boards(("a", "A", "nrf52840"), ("xiao_nrf54l15_lr2021", "XIAO", "nrf54l15")),
        )
        self.assertEqual([d.platformio_env for d in result.devices], ["a"])
        self.assertEqual([env for env, _ in result.excluded], ["xiao_nrf54l15_lr2021"])

    def test_excluded_family_is_dropped_from_cached_lists_too(self):
        from unittest.mock import patch as mock_patch

        from meshtastic_builder import board_catalog
        from meshtastic_builder.firmwares import get_firmware

        cached = [device("a", "A"), device("xiao_nrf54l15_lr2021", "XIAO", family="nrf54l15")]
        with mock_patch.object(board_catalog, "_devices_for", return_value=(cached, True)):
            devices, _ = board_catalog.devices_for(None, get_firmware(ROOT, "meshtastic"), "a" * 40)
        self.assertEqual([d.platformio_env for d in devices], ["a"])

    def test_shipped_list_has_no_excluded_board(self):
        from meshtastic_builder.device_sync import exclusion_reason

        self.assertFalse([d.id for d in load_devices(ROOT) if exclusion_reason(d.platformio_env, d.family)])

    def test_generated_ids_follow_the_existing_convention(self):
        self.assertEqual(device_id_for("tlora-v2-1-1_6"), "tlora-v2-1-1-6")
        self.assertEqual(device_id_for("CDEBYTE_EoRa-S3"), "cdebyte-eora-s3")
        self.assertEqual(device_id_for("seeed_wio_tracker_L1_Pro_1W"), "seeed-wio-tracker-l1-pro-1w")


if __name__ == "__main__":
    unittest.main()
