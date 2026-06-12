from __future__ import annotations

import argparse
from pathlib import Path

from .admin import (
    docker_status,
    print_versions,
    refresh_firmware_versions,
    set_firmware_supported,
    validate_devices_against_repo,
)
from .app import run_server
from .cleanup import expire_old_artifacts
from .db import initialize_database
from .config import load_config
from .worker import run_worker


def main() -> None:
    parser = argparse.ArgumentParser(prog="meshtastic-builder")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve")
    sub.add_parser("init-db")
    sub.add_parser("cleanup")
    sub.add_parser("refresh-versions")
    list_versions = sub.add_parser("list-versions")
    list_versions.add_argument("--all", action="store_true")
    set_supported = sub.add_parser("set-supported")
    set_supported.add_argument("tag")
    set_unsupported = sub.add_parser("set-unsupported")
    set_unsupported.add_argument("tag")
    validate_devices = sub.add_parser("validate-devices")
    validate_devices.add_argument("repo_path")
    docker_status_parser = sub.add_parser("docker-status")
    docker_status_parser.add_argument("--timeout-seconds", type=int, default=10)
    worker = sub.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = load_config()

    if args.command == "serve":
        run_server(config)
    elif args.command == "init-db":
        initialize_database(config)
    elif args.command == "cleanup":
        print(f"Expired {expire_old_artifacts(config)} artifact(s).")
    elif args.command == "refresh-versions":
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
        results = validate_devices_against_repo(config, Path(args.repo_path))
        invalid = False
        for item in results:
            status = "OK" if item["valid"] else "MISSING"
            print(f"{status}\t{item['device_id']}\t{item['platformio_env']}\t{item['definition'] or ''}")
            invalid = invalid or not bool(item["valid"])
        if invalid:
            raise SystemExit(1)
    elif args.command == "docker-status":
        status = docker_status(config, timeout_seconds=args.timeout_seconds)
        print("OK" if status["ok"] else "ERROR")
        if status["error"]:
            print(status["error"])
        if status["stderr"]:
            print(str(status["stderr"]).strip())
        if not status["ok"]:
            raise SystemExit(1)
    elif args.command == "worker":
        run_worker(config, once=args.once)


if __name__ == "__main__":
    main()
