import json
import tempfile
import unittest
from dataclasses import replace
from http import HTTPStatus
from pathlib import Path

from meshtastic_builder.app import MeshtasticBuilderHandler
from meshtastic_builder.config import load_config
from meshtastic_builder.db import build_stats, create_build_request, initialize_database


def temp_config(tmp_path: Path):
    return replace(
        load_config(),
        data_dir=tmp_path,
        db_path=tmp_path / "test.sqlite",
        artifact_dir=tmp_path / "artifacts",
        job_dir=tmp_path / "jobs",
        cache_dir=tmp_path / "cache",
    )


def queue_build(config, token_suffix: str):
    return create_build_request(
        config,
        device_id="tbeam",
        platformio_env="tbeam",
        firmware_tag=f"v-test-{token_suffix}",
        firmware_sha="abc123",
        prefs_jsonc='{"USERPREFS_ALLOWED": true}\n',
    )


class RecordingHandler(MeshtasticBuilderHandler):
    """Captures a response instead of writing it to a socket."""

    def __init__(self, config):  # noqa: D107
        self.config = config
        self.status = None
        self.payload = None
        self.headers_sent = {}

    def json_response(self, payload, status=HTTPStatus.OK):
        self.status = status
        self.payload = payload

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, keyword, value):
        self.headers_sent[keyword] = value

    def end_headers(self):
        return None


class BuildStatsTests(unittest.TestCase):
    def test_counts_and_last_requested_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            initialize_database(config)

            empty = build_stats(config)
            self.assertEqual(empty["total"], 0)
            self.assertEqual(empty["queued"], 0)
            self.assertIsNone(empty["lastRequestedAt"])

            first = queue_build(config, "1")
            queue_build(config, "2")
            stats = build_stats(config)
            self.assertEqual(stats["total"], 2)
            self.assertEqual(stats["queued"], 2)
            self.assertEqual(stats["byStatus"]["succeeded"], 0)
            self.assertGreaterEqual(stats["lastRequestedAt"], first["created_at"])

    def test_stats_never_expose_request_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            initialize_database(config)
            build = queue_build(config, "secret")
            serialized = json.dumps(build_stats(config))
            self.assertNotIn(build["public_token"], serialized)
            self.assertNotIn("USERPREFS", serialized)
            self.assertNotIn("tbeam", serialized)


class HealthEndpointTests(unittest.TestCase):
    def test_reports_ok_with_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            initialize_database(config)
            queue_build(config, "1")

            handler = RecordingHandler(config)
            handler.serve_health()
            self.assertEqual(handler.status, HTTPStatus.OK)
            self.assertEqual(handler.payload["status"], "ok")
            self.assertEqual(handler.payload["builds"]["queued"], 1)

    def test_reports_unavailable_without_leaking_the_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            # Never initialized, and the path is a directory, so opening it fails.
            broken = replace(config, db_path=config.data_dir)
            handler = RecordingHandler(broken)
            handler.serve_health()
            self.assertEqual(handler.status, HTTPStatus.SERVICE_UNAVAILABLE)
            self.assertEqual(handler.payload["status"], "error")
            self.assertNotIn(str(config.data_dir), json.dumps(handler.payload))


if __name__ == "__main__":
    unittest.main()
