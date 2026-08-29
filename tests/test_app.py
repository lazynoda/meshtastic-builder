import unittest
from dataclasses import replace

from meshtastic_builder.app import MeshtasticBuilderHandler
from meshtastic_builder.config import load_config


def make_handler(trust_proxy: bool, forwarded_for: str | None):
    handler = MeshtasticBuilderHandler.__new__(MeshtasticBuilderHandler)
    handler.config = replace(load_config(), trust_proxy=trust_proxy)
    handler.headers = {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
    handler.client_address = ("10.1.2.3", 54321)
    return handler


class ClientIpTests(unittest.TestCase):
    def test_forwarded_for_is_ignored_by_default(self):
        handler = make_handler(False, "203.0.113.9")
        self.assertEqual(handler.client_ip(), "10.1.2.3")

    def test_first_forwarded_hop_is_used_when_trusted(self):
        handler = make_handler(True, "203.0.113.9, 172.16.0.1")
        self.assertEqual(handler.client_ip(), "203.0.113.9")

    def test_falls_back_to_socket_when_header_missing_or_empty(self):
        for header in (None, "", "   "):
            with self.subTest(header=header):
                self.assertEqual(make_handler(True, header).client_ip(), "10.1.2.3")


if __name__ == "__main__":
    unittest.main()
