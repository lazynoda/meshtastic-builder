import unittest
from dataclasses import replace
from http import HTTPStatus

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


TOKEN = "nzUnfX_mrNxcpo45GO48jII22MQ17dQrbclGPScTpdw"


class RoutingHandler(MeshtasticBuilderHandler):
    """Records which page or redirect a path resolves to, without a socket."""

    def __init__(self):  # noqa: D107
        self.config = load_config()
        self.served = None
        self.status = None
        self.headers_sent = {}
        self.payload = None

    def serve_static(self, relative_name, *, send_body=True):
        self.served = relative_name

    def json_response(self, payload, status=HTTPStatus.OK):
        self.status = status
        self.payload = payload

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, keyword, value):
        self.headers_sent[keyword] = value

    def end_headers(self):
        return None

    def get(self, path):
        self.path = path
        self.handle_get_like(send_body=True)
        return self


class BuildPermalinkTests(unittest.TestCase):
    def test_root_still_serves_the_builder_page(self):
        handler = RoutingHandler().get("/")
        self.assertEqual(handler.served, "index.html")

    def test_build_path_serves_the_same_page(self):
        handler = RoutingHandler().get(f"/build/{TOKEN}")
        self.assertEqual(handler.served, "index.html")

    def test_legacy_query_link_redirects_to_the_build_path(self):
        handler = RoutingHandler().get(f"/?build={TOKEN}")
        self.assertIsNone(handler.served)
        self.assertEqual(handler.status, HTTPStatus.MOVED_PERMANENTLY)
        self.assertEqual(handler.headers_sent["Location"], f"/build/{TOKEN}")

    def test_about_path_serves_the_about_page(self):
        handler = RoutingHandler().get("/about")
        self.assertEqual(handler.served, "about.html")

    def test_bad_token_never_reaches_the_page(self):
        for path in (f"/build/{'../' * 3}etc/passwd", "/build/short", "/?build=%2e%2e%2f"):
            with self.subTest(path=path):
                handler = RoutingHandler().get(path)
                self.assertIsNone(handler.served)
                self.assertEqual(handler.status, HTTPStatus.BAD_REQUEST)


class VersionFooterTests(unittest.TestCase):
    def serve(self, name):
        import io

        from meshtastic_builder import __version__

        handler = MeshtasticBuilderHandler.__new__(MeshtasticBuilderHandler)
        handler.config = load_config()
        handler.wfile = io.BytesIO()
        sent = {}
        handler.send_response = lambda code, message=None: sent.setdefault("status", code)
        handler.send_header = lambda key, value: sent.__setitem__(key, value)
        handler.end_headers = lambda: None
        handler.serve_static(name)
        body = handler.wfile.getvalue()
        return body, sent, __version__

    def test_pages_show_the_running_version(self):
        for name in ("index.html", "about.html"):
            with self.subTest(page=name):
                body, sent, version = self.serve(name)
                self.assertIn(f">v{version}</a>".encode(), body)
                self.assertIn(f"/releases/tag/v{version}".encode(), body)
                self.assertNotIn(b"__MB_VERSION__", body)
                # Content-Length must match the substituted body, not the file.
                self.assertEqual(int(sent["Content-Length"]), len(body))

    def test_non_html_is_served_untouched(self):
        from pathlib import Path

        body, _sent, _version = self.serve("app.js")
        self.assertEqual(body, (Path(load_config().root_dir) / "static" / "app.js").read_bytes())


if __name__ == "__main__":
    unittest.main()
