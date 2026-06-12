import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from meshtastic_builder.config import load_config
from meshtastic_builder.firmware import _next_link, refresh_firmware_versions


class FirmwareVersionTests(unittest.TestCase):
    def test_next_link_parses_github_link_header(self):
        header = '<https://api.github.test/tags?page=2>; rel="next", <https://api.github.test/tags?page=9>; rel="last"'
        self.assertEqual(_next_link(header), "https://api.github.test/tags?page=2")

    def test_refresh_firmware_versions_follows_pagination(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = replace(
                load_config(),
                data_dir=tmp_path,
                db_path=tmp_path / "test.sqlite",
                artifact_dir=tmp_path / "artifacts",
                job_dir=tmp_path / "jobs",
                cache_dir=tmp_path / "cache",
                mail_dir=tmp_path / "mail",
                github_tags_url="https://api.github.test/tags?page=1",
                github_max_tag_pages=5,
            )

            def fake_http_get(url, timeout=15):
                if url.endswith("page=1"):
                    return (
                        json.dumps([{"name": "v2", "commit": {"sha": "222"}}]),
                        {"Link": '<https://api.github.test/tags?page=2>; rel="next"'},
                    )
                return (
                    json.dumps([{"name": "v1", "commit": {"sha": "111"}}]),
                    {},
                )

            with patch("meshtastic_builder.firmware._http_get", fake_http_get):
                versions = refresh_firmware_versions(config)

            self.assertEqual([item["tag"] for item in versions], ["v2", "v1"])

    def test_refresh_auto_supports_only_latest_configured_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = replace(
                load_config(),
                data_dir=tmp_path,
                db_path=tmp_path / "test.sqlite",
                artifact_dir=tmp_path / "artifacts",
                job_dir=tmp_path / "jobs",
                cache_dir=tmp_path / "cache",
                mail_dir=tmp_path / "mail",
                github_tags_url="https://api.github.test/tags?page=1",
                github_max_tag_pages=1,
                auto_support_latest_tags=1,
            )

            def fake_http_get(url, timeout=15):
                return (
                    json.dumps(
                        [
                            {"name": "v-new", "commit": {"sha": "222"}},
                            {"name": "v-old", "commit": {"sha": "111"}},
                        ]
                    ),
                    {},
                )

            with patch("meshtastic_builder.firmware._http_get", fake_http_get):
                versions = refresh_firmware_versions(config)

            by_tag = {item["tag"]: item for item in versions}
            self.assertEqual(by_tag["v-new"]["supported"], 1)
            self.assertEqual(by_tag["v-old"]["supported"], 0)


if __name__ == "__main__":
    unittest.main()
