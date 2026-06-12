import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from meshtastic_builder.config import load_config
from meshtastic_builder.mailer import outbox_path, send_build_failure, send_build_success


def build_row():
    return {
        "public_token": "token-123",
        "email": "user@example.com",
        "device_id": "tbeam",
        "firmware_tag": "v-test",
        "firmware_sha": "abc123",
        "expires_at": "2026-06-19T00:00:00+00:00",
        "artifact_sha256": "sha256",
    }


class MailerTests(unittest.TestCase):
    def test_success_email_writes_outbox_when_smtp_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = replace(
                load_config(),
                mail_dir=Path(tmp),
                smtp_host="",
                base_url="http://example.test",
            )

            send_build_success(config, build_row())

            lines = outbox_path(config).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["to"], "user@example.com")
            self.assertIn("http://example.test/download/token-123", payload["body"])

    def test_failure_email_writes_outbox_when_smtp_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = replace(load_config(), mail_dir=Path(tmp), smtp_host="")

            send_build_failure(config, build_row())

            payload = json.loads(outbox_path(config).read_text(encoding="utf-8").splitlines()[0])
            self.assertIn("No se pudo compilar", payload["body"])


if __name__ == "__main__":
    unittest.main()

