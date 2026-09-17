import unittest
from pathlib import Path

from meshtastic_builder.devices import enabled_devices


class DeviceTests(unittest.TestCase):
    def test_requested_devices_are_enabled_with_expected_platformio_envs(self):
        by_id = {device.id: device for device in enabled_devices(Path.cwd())}

        expected = {
            "heltec-v4": ("Heltec V4", "heltec-v4", "esp32-s3"),
            "nrf52-promicro-diy": ("NRF52 Pro-micro DIY", "nrf52_promicro_diy_tcxo", "nrf52840"),
            "heltec-mesh-node-t114": ("Heltec Mesh Node T114", "heltec-mesh-node-t114", "nrf52840"),
            "tracker-t1000-e": ("Seeed SenseCAP T1000-E", "tracker-t1000-e", "nrf52840"),
            "heltec-wsl-v3": ("Heltec Wireless Stick Lite V3", "heltec-wsl-v3", "esp32-s3"),
        }

        for device_id, (label, platformio_env, family) in expected.items():
            self.assertIn(device_id, by_id)
            self.assertEqual(by_id[device_id].label, label)
            self.assertEqual(by_id[device_id].platformio_env, platformio_env)
            self.assertEqual(by_id[device_id].family, family)

    def test_catalogue_is_unique_and_covers_the_common_boards(self):
        devices = enabled_devices(Path.cwd())
        self.assertGreater(len(devices), 80)
        self.assertEqual(len({device.id for device in devices}), len(devices))
        self.assertEqual(len({device.label for device in devices}), len(devices))
        self.assertEqual(len({device.platformio_env for device in devices}), len(devices))
        # The first entry is the default selection on the page.
        self.assertEqual(devices[0].id, "tbeam")


if __name__ == "__main__":
    unittest.main()
