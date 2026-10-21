from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from .config import Config, load_config
from .db import (
    connection,
    get_build_by_token,
    get_firmware_version,
    initialize_database,
    list_firmware_versions,
)
from .devices import enabled_devices
from .firmware import refresh_firmware_versions


def set_firmware_supported(
    config: Config,
    tag: str,
    supported: bool,
    firmware_id: str = "meshtastic",
) -> dict[str, object]:
    initialize_database(config)
    if get_firmware_version(config, tag, firmware_id=firmware_id) is None:
        raise ValueError(f"Firmware tag not found in local cache: {firmware_id} {tag}")
    with connection(config) as conn:
        conn.execute(
            "UPDATE firmware_versions SET supported = ? WHERE firmware_id = ? AND tag = ?",
            (1 if supported else 0, firmware_id, tag),
        )
    updated = get_firmware_version(config, tag, firmware_id=firmware_id)
    if updated is None:
        raise RuntimeError(f"Firmware tag disappeared after update: {tag}")
    return updated


def extract_platformio_envs(repo_path: Path) -> dict[str, Path]:
    if not repo_path.exists():
        raise ValueError(f"Meshtastic firmware repo path does not exist: {repo_path}")
    envs: dict[str, Path] = {}
    for ini_path in repo_path.rglob("*.ini"):
        try:
            text = ini_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ini_path.read_text(errors="ignore")
        for match in re.finditer(r"^\[env:([^\]]+)\]", text, re.MULTILINE):
            envs[match.group(1)] = ini_path.relative_to(repo_path)
    return envs


def validate_devices_against_repo(config: Config, repo_path: Path) -> list[dict[str, object]]:
    envs = extract_platformio_envs(repo_path)
    results: list[dict[str, object]] = []
    for device in enabled_devices(config.root_dir):
        path = envs.get(device.platformio_env)
        results.append(
            {
                "device_id": device.id,
                "label": device.label,
                "platformio_env": device.platformio_env,
                "valid": path is not None,
                "definition": str(path) if path is not None else None,
            }
        )
    return results


def docker_status(config: Config, *, timeout_seconds: int = 10) -> dict[str, object]:
    try:
        proc = subprocess.run(
            [config.docker_binary, "info", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "error": f"Docker binary not found: {config.docker_binary}",
            "stdout": "",
            "stderr": "",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": f"Docker info timed out after {timeout_seconds}s",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }

    return {
        "ok": proc.returncode == 0,
        "error": "" if proc.returncode == 0 else f"Docker info exited with {proc.returncode}",
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def print_versions(config: Config, *, include_unsupported: bool, firmware_id: str = "meshtastic") -> None:
    versions = list_firmware_versions(config, supported_only=not include_unsupported, firmware_id=firmware_id)
    for item in versions:
        state = "supported" if item["supported"] else "unsupported"
        print(f"{item['tag']}\t{item['sha']}\t{state}\t{item['smoke_test_status']}")


def print_build_log(config: Config, token: str, *, tail_lines: int = 40, full: bool = False) -> None:
    """Show why one build failed, without opening SQLite by hand.

    Build logs carry the whole PlatformIO `-D` dump, which includes the WiFi PSK
    and the MQTT password, so they are never served over HTTP. This is an
    operator command on the host, and it prints the tail by default.
    """
    initialize_database(config)
    build = get_build_by_token(config, token)
    if build is None:
        raise ValueError(f"No build with token {token}")

    print(f"token:    {build['public_token']}")
    print(f"status:   {build['status']}")
    print(f"device:   {build['device_id']} ({build['platformio_env']})")
    print(
        f"firmware: {build.get('firmware_id') or 'meshtastic'} {build['firmware_tag']} "
        f"({build['firmware_sha']}, version {build.get('firmware_version') or build['firmware_tag']})"
    )
    print(f"options:  {build['code_options'] or 'none'}")
    print(f"created:  {build['created_at']}   finished: {build['finished_at'] or '-'}")
    if build["status"] == "failed":
        print(f"code:     {build.get('error_code') or 'unknown'}")
        print(f"detail:   {build['error_message'] or '-'}")

    log = str(build["build_log"] or "")
    if not log.strip():
        print("\n(no build log stored)")
        return
    lines = log.splitlines()
    if full or len(lines) <= tail_lines:
        shown = lines
    else:
        print(f"\n--- last {tail_lines} of {len(lines)} log lines (use --full for all) ---")
        shown = lines[-tail_lines:]
    print("\n".join(shown))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m meshtastic_builder.admin")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("refresh-versions")

    list_parser = sub.add_parser("list-versions")
    list_parser.add_argument("--all", action="store_true", help="Include unsupported versions.")

    supported = sub.add_parser("set-supported")
    supported.add_argument("tag")

    unsupported = sub.add_parser("set-unsupported")
    unsupported.add_argument("tag")

    validate = sub.add_parser("validate-devices")
    validate.add_argument("repo_path", type=Path)
    validate.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    docker = sub.add_parser("docker-status")
    docker.add_argument("--timeout-seconds", type=int, default=10)
    docker.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    args = parser.parse_args()
    config = load_config()

    if args.command == "refresh-versions":
        versions = refresh_firmware_versions(config)
        print(f"Refreshed {len(versions)} firmware version(s).")
    elif args.command == "list-versions":
        print_versions(config, include_unsupported=args.all)
    elif args.command == "set-supported":
        item = set_firmware_supported(config, args.tag, True)
        print(f"{item['tag']} supported=1")
    elif args.command == "set-unsupported":
        item = set_firmware_supported(config, args.tag, False)
        print(f"{item['tag']} supported=0")
    elif args.command == "validate-devices":
        results = validate_devices_against_repo(config, args.repo_path)
        if args.json:
            print(json.dumps({"devices": results}, indent=2))
        else:
            invalid = False
            for item in results:
                status = "OK" if item["valid"] else "MISSING"
                print(f"{status}\t{item['device_id']}\t{item['platformio_env']}\t{item['definition'] or ''}")
                invalid = invalid or not bool(item["valid"])
            if invalid:
                raise SystemExit(1)
    elif args.command == "docker-status":
        status = docker_status(config, timeout_seconds=args.timeout_seconds)
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print("OK" if status["ok"] else "ERROR")
            if status["error"]:
                print(status["error"])
            if status["stderr"]:
                print(str(status["stderr"]).strip())
        if not status["ok"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
