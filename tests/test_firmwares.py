import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from meshtastic_builder.builder import build_info, builder_args, build_firmware_source, stage_patches
from meshtastic_builder.config import load_config
from meshtastic_builder.db import (
    connection,
    get_firmware_version,
    initialize_database,
    list_firmware_versions,
    upsert_firmware_versions,
)
from meshtastic_builder.firmware import (
    list_versions_with_refresh,
    parse_version_properties,
    resolve_supported_version,
    userprefs_cache_path,
)
from meshtastic_builder.firmwares import get_firmware, list_firmwares, load_firmware_catalog
from meshtastic_builder.submissions import create_build_submission

ROOT = Path(__file__).resolve().parent.parent
NODASTIC_SHA = "d" * 40
NAMED_PREFS = '{"USERPREFS_CONFIG_OWNER_LONG_NAME": "Test Node", "USERPREFS_CONFIG_OWNER_SHORT_NAME": "TST"}'
TEMPLATE = '{"USERPREFS_CONFIG_OWNER_LONG_NAME": "", "USERPREFS_CONFIG_OWNER_SHORT_NAME": "DEF", "USERPREFS_FIXED_GPS": ""}'


def temp_config(tmp_path: Path):
    return replace(
        load_config(),
        root_dir=ROOT,
        data_dir=tmp_path,
        db_path=tmp_path / "test.sqlite",
        artifact_dir=tmp_path / "artifacts",
        job_dir=tmp_path / "jobs",
        cache_dir=tmp_path / "cache",
        base_url="http://example.test",
    )


VARIANTS_SHA = "f" * 40
INI_BLOB = "b" * 40
BOARD_INI = """
[env:tbeam]
custom_meshtastic_architecture = esp32
custom_meshtastic_actively_supported = true
custom_meshtastic_display_name = LILYGO T-Beam

[env:nrf52_promicro_diy_e28]
custom_meshtastic_architecture = nrf52840
custom_meshtastic_actively_supported = true
custom_meshtastic_display_name = NRF52 Pro-micro E28 DIY
"""


def fake_github(url, timeout=15):
    if url == f"https://api.github.com/repos/lazynoda/meshtastic-firmware/git/trees/{NODASTIC_SHA}":
        return json.dumps({"tree": [{"path": "variants", "type": "tree", "sha": VARIANTS_SHA}]}), {}
    if url == f"https://api.github.com/repos/lazynoda/meshtastic-firmware/git/trees/{VARIANTS_SHA}?recursive=1":
        tree = [{"path": "diy/e28/platformio.ini", "type": "blob", "sha": INI_BLOB, "size": 300}]
        return json.dumps({"truncated": False, "tree": tree}), {}
    if url == f"https://raw.githubusercontent.com/lazynoda/meshtastic-firmware/{NODASTIC_SHA}/variants/diy/e28/platformio.ini":
        return BOARD_INI, {}
    if url.startswith("https://api.github.com/repos/derpyspike/jentastic/tags"):
        return json.dumps([{"name": "v2.8.104", "commit": {"sha": "j" * 40}}]), {}
    if url == "https://api.github.com/repos/lazynoda/meshtastic-firmware/commits/nodastic":
        return json.dumps({"sha": NODASTIC_SHA}), {}
    if url == f"https://raw.githubusercontent.com/lazynoda/meshtastic-firmware/{NODASTIC_SHA}/version.properties":
        return "[VERSION]  \nmajor = 2\nminor = 8\nbuild = 1\n", {}
    raise AssertionError(f"unexpected URL {url}")


class CatalogTests(unittest.TestCase):
    def test_shipped_catalog_lists_the_three_firmwares_with_upstream_default(self):
        default, firmwares = load_firmware_catalog(ROOT)
        self.assertEqual(default, "meshtastic")
        self.assertEqual([item.id for item in firmwares], ["meshtastic", "jentastic", "nodastic"])
        nodastic = get_firmware(ROOT, "nodastic")
        self.assertEqual(nodastic.versioning, "branch")
        self.assertEqual(nodastic.branch, "nodastic")
        self.assertEqual(nodastic.clone_url, "https://github.com/lazynoda/meshtastic-firmware.git")

    def test_shipped_catalog_marks_jentastic_boards_that_do_not_fit(self):
        jentastic = get_firmware(ROOT, "jentastic")
        boards = (
            "heltec-mesh-node-t096",
            "heltec-mesh-pocket-5000",
            "heltec-mesh-pocket-5000-inkhud",
            "heltec-mesh-pocket-10000",
            "heltec-mesh-pocket-10000-inkhud",
        )
        for env in boards:
            item = jentastic.unavailable(env)
            self.assertIsNotNone(item, env)
            self.assertEqual(item.reason, "firmware_too_big")
            self.assertEqual(item.issue, "https://github.com/lazynoda/meshtastic-builder/issues/3")
        self.assertIsNone(jentastic.unavailable("heltec-mesh-node-t114-inkhud"))
        self.assertIsNone(get_firmware(ROOT, "meshtastic").unavailable("heltec-mesh-node-t096"))
        self.assertIsNone(get_firmware(ROOT, "nodastic").unavailable("heltec-mesh-node-t096"))

    def test_catalog_rejects_malformed_unavailable_boards(self):
        base = {"id": "x", "name": "X", "url": "https://github.com/a/b", "versioning": "tags"}
        cases = [
            ["t096"],
            {"bad env!": {"reason": "firmware_too_big", "issue": "https://github.com/a/b/issues/1"}},
            {"t096": {"issue": "https://github.com/a/b/issues/1"}},
            {"t096": {"reason": "firmware_too_big", "issue": "https://evil.test/issues/1"}},
            {"t096": {"reason": "firmware_too_big"}},
        ]
        for unavailable in cases:
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "data").mkdir()
                entry = {**base, "unavailableBoards": unavailable}
                (Path(tmp) / "data" / "firmwares.json").write_text(json.dumps({"firmwares": [entry]}))
                with self.assertRaises(ValueError, msg=repr(unavailable)):
                    load_firmware_catalog(Path(tmp))

    def test_missing_catalog_falls_back_to_upstream_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([item.id for item in list_firmwares(Path(tmp))], ["meshtastic"])

    def test_catalog_rejects_non_github_urls_and_bad_branches(self):
        cases = [
            {"id": "x", "name": "X", "url": "https://evil.test/a/b", "versioning": "tags"},
            {"id": "x", "name": "X", "url": "https://github.com/a/b", "versioning": "branch", "branch": "a b"},
            {"id": "x", "name": "X", "url": "https://github.com/a/b", "versioning": "branch"},
        ]
        for entry in cases:
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "data").mkdir()
                (Path(tmp) / "data" / "firmwares.json").write_text(json.dumps({"firmwares": [entry]}))
                with self.assertRaises(ValueError):
                    load_firmware_catalog(Path(tmp))

    def test_unknown_firmware_is_a_user_error(self):
        with self.assertRaises(ValueError):
            get_firmware(ROOT, "nope")


class MigrationTests(unittest.TestCase):
    def test_legacy_tag_cache_becomes_upstream_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            config.db_path.parent.mkdir(parents=True, exist_ok=True)
            legacy = sqlite3.connect(config.db_path)
            legacy.executescript(
                """
                CREATE TABLE firmware_versions (
                  tag TEXT PRIMARY KEY, sha TEXT NOT NULL, release_name TEXT, published_at TEXT,
                  supported INTEGER NOT NULL DEFAULT 1,
                  smoke_test_status TEXT NOT NULL DEFAULT 'untested', last_checked_at TEXT NOT NULL
                );
                INSERT INTO firmware_versions VALUES ('v2.8.1.8e6a88d', 'abc', 'v2.8.1.8e6a88d', NULL, 0, 'untested', 'x');
                """
            )
            legacy.commit()
            legacy.close()

            initialize_database(config)
            initialize_database(config)  # idempotent

            row = get_firmware_version(config, "v2.8.1.8e6a88d", firmware_id="meshtastic")
            self.assertEqual(row["sha"], "abc")
            self.assertEqual(row["supported"], 0)
            conn = sqlite3.connect(config.db_path)
            build_columns = {r[1] for r in conn.execute("PRAGMA table_info(build_requests)")}
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            conn.close()
            self.assertIn("firmware_id", build_columns)
            self.assertIn("firmware_version", build_columns)
            self.assertNotIn("firmware_versions_legacy", tables)


class VersionTests(unittest.TestCase):
    def test_same_tag_name_is_kept_apart_per_firmware(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            upsert_firmware_versions(config, [{"tag": "v2.8.104", "sha": "a"}], firmware_id="meshtastic")
            upsert_firmware_versions(config, [{"tag": "v2.8.104", "sha": "b"}], firmware_id="jentastic")
            self.assertEqual(get_firmware_version(config, "v2.8.104", "meshtastic")["sha"], "a")
            self.assertEqual(get_firmware_version(config, "v2.8.104", "jentastic")["sha"], "b")
            self.assertEqual(len(list_firmware_versions(config, firmware_id="jentastic")), 1)

    def test_jentastic_tags_come_from_its_own_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            with patch("meshtastic_builder.firmware._http_get", fake_github):
                versions = list_versions_with_refresh(config, firmware_id="jentastic")
            self.assertEqual([item["tag"] for item in versions], ["v2.8.104"])
            self.assertEqual(versions[0]["version"], "v2.8.104")
            self.assertFalse(versions[0]["branch"])
            self.assertEqual(list_firmware_versions(config, firmware_id="meshtastic"), [])

    def test_branch_firmware_resolves_head_and_its_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            with patch("meshtastic_builder.firmware._http_get", fake_github):
                versions = list_versions_with_refresh(config, firmware_id="nodastic")
                # Whatever tag a client sends, a branch firmware builds its head.
                resolved = resolve_supported_version(config, "v9.9.9", firmware_id="nodastic")
            self.assertEqual(len(versions), 1)
            self.assertEqual(versions[0]["tag"], "nodastic")
            self.assertEqual(versions[0]["sha"], NODASTIC_SHA)
            self.assertEqual(versions[0]["version"], "2.8.1")
            self.assertTrue(versions[0]["branch"])
            self.assertEqual(resolved["sha"], NODASTIC_SHA)

    def test_branch_head_falls_back_to_cache_when_github_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            with patch("meshtastic_builder.firmware._http_get", fake_github):
                list_versions_with_refresh(config, firmware_id="nodastic")

            def broken(url, timeout=15):
                raise TimeoutError("down")

            with patch("meshtastic_builder.firmware._http_get", broken):
                versions = list_versions_with_refresh(config, firmware_id="nodastic", force_refresh=True)
            self.assertEqual(versions[0]["sha"], NODASTIC_SHA)

    def test_tags_deleted_upstream_stop_being_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            pages = {
                "before": [{"name": "v2.8.104", "commit": {"sha": "a" * 40}},
                           {"name": "v2.8.104-001", "commit": {"sha": "b" * 40}}],
                "after": [{"name": "v2.8.104", "commit": {"sha": "a" * 40}}],
            }
            state = {"page": "before"}

            def github(url, timeout=15):
                return json.dumps(pages[state["page"]]), {}

            with patch("meshtastic_builder.firmware._http_get", github):
                list_versions_with_refresh(config, firmware_id="jentastic")
                state["page"] = "after"
                tags = [v["tag"] for v in list_versions_with_refresh(config, firmware_id="jentastic", force_refresh=True)]
            self.assertEqual(tags, ["v2.8.104"])
            # Kept, unsupported, so builds made from it still resolve.
            self.assertEqual(get_firmware_version(config, "v2.8.104-001", "jentastic")["supported"], 0)

    def test_a_page_cap_never_retires_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = replace(temp_config(Path(tmp)), github_max_tag_pages=1)
            upsert_firmware_versions(config, [{"tag": "v-old", "sha": "o"}], firmware_id="jentastic")

            def github(url, timeout=15):
                return (
                    json.dumps([{"name": "v-new", "commit": {"sha": "n" * 40}}]),
                    {"Link": '<https://api.github.test/tags?page=2>; rel="next"'},
                )

            with patch("meshtastic_builder.firmware._http_get", github):
                list_versions_with_refresh(config, firmware_id="jentastic", force_refresh=True)
            self.assertEqual(get_firmware_version(config, "v-old", "jentastic")["supported"], 1)

    def test_version_properties_parsing(self):
        self.assertEqual(parse_version_properties("[VERSION]  \nmajor = 2\nminor = 8\nbuild = 104\n"), "2.8.104")
        self.assertIsNone(parse_version_properties("[VERSION]\nmajor = 2\n"))
        self.assertIsNone(parse_version_properties(""))

    def test_template_cache_is_per_firmware_and_upstream_path_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            self.assertEqual(
                userprefs_cache_path(config, "v2.8.1"), config.cache_dir / "userprefs" / "v2.8.1.jsonc"
            )
            self.assertNotEqual(
                userprefs_cache_path(config, "v2.8.1", "jentastic"), userprefs_cache_path(config, "v2.8.1")
            )


class SubmissionTests(unittest.TestCase):
    def submit(self, config, payload):
        return create_build_submission(
            config,
            {"deviceId": "tbeam", "prefsJsonc": NAMED_PREFS, **payload},
        )

    def test_nodastic_submission_stores_branch_head_and_firmware_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            cache = userprefs_cache_path(config, NODASTIC_SHA, "nodastic")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(TEMPLATE, encoding="utf-8")
            with patch("meshtastic_builder.firmware._http_get", fake_github):
                result = self.submit(config, {"firmwareId": "nodastic"})
            row = result["row"]
            self.assertEqual(row["firmware_id"], "nodastic")
            self.assertEqual(row["firmware_tag"], "nodastic")
            self.assertEqual(row["firmware_sha"], NODASTIC_SHA)
            self.assertEqual(row["firmware_version"], "2.8.1")
            self.assertEqual(result["public"]["firmwareId"], "nodastic")

    def test_submission_without_firmware_id_means_upstream(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            upsert_firmware_versions(config, [{"tag": "v-test", "sha": "abc"}])
            cache = userprefs_cache_path(config, "v-test")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(TEMPLATE, encoding="utf-8")
            row = self.submit(config, {"firmwareTag": "v-test"})["row"]
            self.assertEqual(row["firmware_id"], "meshtastic")
            self.assertEqual(row["firmware_version"], "v-test")

    def test_tag_firmware_still_requires_a_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            with self.assertRaises(ValueError):
                self.submit(config, {"firmwareId": "jentastic"})

    def test_upstream_tag_is_not_accepted_for_another_firmware(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            upsert_firmware_versions(config, [{"tag": "v2.8.1.8e6a88d", "sha": "abc"}])
            with patch("meshtastic_builder.firmware._http_get", fake_github):
                with self.assertRaises(Exception):
                    self.submit(config, {"firmwareId": "jentastic", "firmwareTag": "v2.8.1.8e6a88d"})


class BoardCatalogTests(unittest.TestCase):
    def test_boards_come_from_the_firmware_commit_and_are_cached(self):
        from meshtastic_builder.board_catalog import devices_for

        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            calls = []

            def counting(url, timeout=15):
                calls.append(url)
                return fake_github(url, timeout)

            source = get_firmware(ROOT, "nodastic")
            with patch("meshtastic_builder.firmware._http_get", counting):
                devices, from_firmware = devices_for(config, source, NODASTIC_SHA)
                first_calls = len(calls)
                again, _ = devices_for(config, source, NODASTIC_SHA)
            self.assertTrue(from_firmware)
            by_env = {d.platformio_env: d for d in devices}
            # Known board keeps the id from data/devices.json; the fork's own one gets a new id.
            self.assertEqual(by_env["tbeam"].id, "tbeam")
            self.assertEqual(by_env["nrf52_promicro_diy_e28"].id, "nrf52-promicro-diy-e28")
            self.assertEqual(by_env["nrf52_promicro_diy_e28"].label, "NRF52 Pro-micro E28 DIY")
            self.assertEqual(len(devices), 2)
            self.assertEqual(first_calls, 3)
            self.assertEqual(len(calls), first_calls)  # second lookup served from SQLite
            self.assertEqual([d.id for d in again], [d.id for d in devices])

    def test_github_down_falls_back_to_the_static_list(self):
        from meshtastic_builder.board_catalog import devices_for
        from meshtastic_builder.devices import enabled_devices

        def broken(url, timeout=15):
            raise TimeoutError("down")

        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            with patch("meshtastic_builder.firmware._http_get", broken):
                devices, from_firmware = devices_for(config, get_firmware(ROOT, "nodastic"), NODASTIC_SHA)
            self.assertFalse(from_firmware)
            self.assertEqual(len(devices), len(enabled_devices(ROOT)))

    def test_submission_refuses_a_board_the_firmware_does_not_have(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            cache = userprefs_cache_path(config, NODASTIC_SHA, "nodastic")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(TEMPLATE, encoding="utf-8")
            with patch("meshtastic_builder.firmware._http_get", fake_github):
                with self.assertRaises(ValueError):
                    create_build_submission(
                        config,
                        {"deviceId": "heltec-v4", "firmwareId": "nodastic", "prefsJsonc": NAMED_PREFS},
                    )
                row = create_build_submission(
                    config,
                    {"deviceId": "nrf52-promicro-diy-e28", "firmwareId": "nodastic", "prefsJsonc": NAMED_PREFS},
                )["row"]
            self.assertEqual(row["platformio_env"], "nrf52_promicro_diy_e28")
            self.assertEqual(row["device_label"], "NRF52 Pro-micro E28 DIY")

    def test_unavailable_board_is_listed_with_its_reason_but_refused(self):
        from meshtastic_builder.app import device_json
        from meshtastic_builder.board_catalog import devices_for
        from meshtastic_builder.firmwares import UnavailableBoard

        issue = "https://github.com/lazynoda/meshtastic-builder/issues/3"
        source = replace(
            get_firmware(ROOT, "nodastic"),
            unavailable_boards=(UnavailableBoard("nrf52_promicro_diy_e28", "firmware_too_big", issue),),
        )
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            cache = userprefs_cache_path(config, NODASTIC_SHA, "nodastic")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(TEMPLATE, encoding="utf-8")
            with patch("meshtastic_builder.firmware._http_get", fake_github), patch(
                "meshtastic_builder.submissions.get_firmware", return_value=source
            ):
                devices, _ = devices_for(config, source, NODASTIC_SHA)
                listed = {d.platformio_env: device_json(d, source) for d in devices}
                with self.assertRaises(ValueError) as refused:
                    create_build_submission(
                        config,
                        {"deviceId": "nrf52-promicro-diy-e28", "firmwareId": "nodastic", "prefsJsonc": NAMED_PREFS},
                    )
                # Another board of the same firmware still builds.
                row = create_build_submission(
                    config,
                    {"deviceId": "tbeam", "firmwareId": "nodastic", "prefsJsonc": NAMED_PREFS},
                )["row"]
            self.assertEqual(
                listed["nrf52_promicro_diy_e28"]["unavailable"], {"reason": "firmware_too_big", "issue": issue}
            )
            self.assertNotIn("unavailable", listed["tbeam"])
            self.assertIn(issue, str(refused.exception))
            self.assertEqual(row["platformio_env"], "tbeam")
            with connection(config) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM build_requests").fetchone()[0], 1)

    def test_hostile_env_names_are_dropped(self):
        from meshtastic_builder.device_sync import parse_boards

        text = """
[env:ok]
custom_meshtastic_actively_supported = true
custom_meshtastic_display_name = Ok
[env:bad;rm -rf]
custom_meshtastic_actively_supported = true
custom_meshtastic_display_name = Bad
"""
        self.assertEqual(sorted(parse_boards([("variants/x/platformio.ini", text)])), ["ok"])


class BuilderTests(unittest.TestCase):
    def build_row(self, **overrides):
        row = {
            "public_token": "t" * 43,
            "device_id": "tbeam",
            "platformio_env": "tbeam",
            "firmware_id": "nodastic",
            "firmware_tag": "nodastic",
            "firmware_sha": NODASTIC_SHA,
            "firmware_version": "2.8.1",
            "prefs_jsonc": '{"USERPREFS_FIXED_GPS": ""}',
        }
        row.update(overrides)
        return row

    def test_builder_gets_the_firmware_repository(self):
        config = temp_config(Path("/tmp"))
        row = self.build_row()
        args = builder_args(row, build_firmware_source(config, row))
        self.assertEqual(args, ["nodastic", NODASTIC_SHA, "tbeam", "https://github.com/lazynoda/meshtastic-firmware.git"])

    def test_legacy_rows_build_upstream(self):
        config = temp_config(Path("/tmp"))
        row = self.build_row(firmware_tag="v2.8.1.8e6a88d")
        del row["firmware_id"], row["firmware_version"]
        self.assertEqual(builder_args(row, build_firmware_source(config, row))[-1], "https://github.com/meshtastic/firmware.git")

    def test_build_info_names_the_firmware_source(self):
        config = temp_config(Path("/tmp"))
        row = self.build_row()
        info = build_info(row, build_firmware_source(config, row))
        self.assertIn("source=https://github.com/lazynoda/meshtastic-firmware", info)
        self.assertIn("firmware=Nodastic", info)
        self.assertIn("firmware_version=2.8.1", info)

    def test_patch_gates_use_the_branch_version_not_the_branch_name(self):
        # Nodastic 2.8.1 already carries upstream's fixed-GPS fix: the patch must
        # not be staged. With the branch name as version it would be unparseable.
        with tempfile.TemporaryDirectory() as tmp:
            config = temp_config(Path(tmp))
            self.assertEqual(stage_patches(config, self.build_row(), Path(tmp)), [])
            staged = stage_patches(config, self.build_row(firmware_version="2.8.0"), Path(tmp))
            self.assertEqual(staged, ["fixed-gps-nodedb.patch"])


if __name__ == "__main__":
    unittest.main()
