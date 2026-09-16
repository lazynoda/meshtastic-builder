from __future__ import annotations

import json
from email.message import Message
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .code_options import parse_version
from .config import Config
from .db import get_firmware_version, list_firmware_versions, upsert_firmware_versions
from .security import safe_tag_for_path


class FirmwareLookupError(RuntimeError):
    pass


def _http_get(url: str, timeout: int = 15) -> tuple[str, Message]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": "meshtastic-builder/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8"), response.headers


def _http_get_text(url: str, timeout: int = 15) -> str:
    body, _headers = _http_get(url, timeout=timeout)
    return body


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        if section.startswith("<") and ">" in section:
            return section[1 : section.index(">")]
    return None


def refresh_firmware_versions(config: Config) -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    seen_tags: set[str] = set()
    url: str | None = config.github_tags_url
    page_count = 0

    while url and page_count < config.github_max_tag_pages:
        raw, headers = _http_get(url)
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise FirmwareLookupError("La respuesta de tags de GitHub no es una lista.")

        for item in payload:
            tag = item.get("name")
            sha = (item.get("commit") or {}).get("sha")
            if not tag or not sha or tag in seen_tags:
                continue
            seen_tags.add(tag)
            supported = (
                1
                if config.auto_support_latest_tags <= 0
                or len(versions) < config.auto_support_latest_tags
                else 0
            )
            versions.append(
                {
                    "tag": tag,
                    "sha": sha,
                    "release_name": tag,
                    "published_at": None,
                    "supported": supported,
                    "smoke_test_status": "untested",
                }
            )

        page_count += 1
        url = _next_link(headers.get("Link"))

    if not versions:
        raise FirmwareLookupError("GitHub no devolvio tags utilizables.")

    upsert_firmware_versions(config, versions)
    return versions


def list_versions_with_refresh(config: Config, *, force_refresh: bool = False) -> list[dict[str, Any]]:
    if force_refresh or not list_firmware_versions(config, supported_only=False):
        try:
            refresh_firmware_versions(config)
        except (urllib.error.URLError, TimeoutError, FirmwareLookupError, json.JSONDecodeError):
            if not list_firmware_versions(config, supported_only=False):
                raise FirmwareLookupError(
                    "No se pudieron obtener tags de Meshtastic y no hay cache local."
                )
    versions = list_firmware_versions(config, supported_only=True)
    # Newest first: rows are stored in insertion order, so tags added by a later refresh would sink to the bottom.
    versions.sort(key=lambda item: parse_version(item["tag"]) or (0, 0, 0), reverse=True)
    return versions


def resolve_supported_version(config: Config, tag: str) -> dict[str, Any]:
    version = get_firmware_version(config, tag)
    if version is None:
        try:
            refresh_firmware_versions(config)
        except Exception as exc:  # noqa: BLE001 - surface as domain error
            raise FirmwareLookupError(f"No se pudo refrescar la lista de tags: {exc}") from exc
        version = get_firmware_version(config, tag)

    if version is None:
        raise FirmwareLookupError("Version de firmware no encontrada.")
    if not version["supported"]:
        raise FirmwareLookupError("Version de firmware no soportada por el builder.")
    return version


def userprefs_cache_path(config: Config, tag: str) -> Path:
    return config.cache_dir / "userprefs" / f"{safe_tag_for_path(tag)}.jsonc"


def get_userprefs_template(config: Config, tag: str, *, force_refresh: bool = False) -> str:
    cache_path = userprefs_cache_path(config, tag)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and not force_refresh:
        return cache_path.read_text(encoding="utf-8")

    url = config.raw_userprefs_url.format(tag=tag)
    try:
        text = _http_get_text(url)
        if "USERPREFS_" not in text:
            raise FirmwareLookupError("El userPrefs.jsonc remoto no contiene claves USERPREFS.")
        cache_path.write_text(text, encoding="utf-8")
        return text
    except Exception:
        fallback = config.root_dir / "data" / "userPrefs.fallback.jsonc"
        return fallback.read_text(encoding="utf-8")
