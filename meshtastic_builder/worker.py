from __future__ import annotations

import argparse
import socket
import time
import traceback

from .builder import run_build
from .cleanup import expire_old_artifacts
from .config import Config, ensure_directories, load_config
from .db import (
    claim_next_build,
    initialize_database,
    mark_build_failure,
    mark_build_success,
    reset_stale_running,
)
from .mailer import send_build_failure, send_build_success


def process_one(config: Config, worker_id: str) -> bool:
    reset_stale_running(config)
    build = claim_next_build(config, worker_id)
    if build is None:
        return False

    token = build["public_token"]
    print(f"Claimed build {token} for {build['platformio_env']} at {build['firmware_tag']}")
    try:
        artifact = run_build(config, build)
        updated = mark_build_success(
            config,
            int(build["id"]),
            artifact_path=artifact.path,
            artifact_sha256=artifact.sha256,
            artifact_size_bytes=artifact.size_bytes,
            build_log=artifact.log,
        )
        try:
            send_build_success(config, updated)
        except Exception as exc:  # noqa: BLE001
            print(f"Build succeeded but success email failed: {exc}")
        print(f"Build {token} succeeded: {artifact.path}")
        return True
    except Exception as exc:  # noqa: BLE001
        log = traceback.format_exc()
        updated = mark_build_failure(config, int(build["id"]), error_message=str(exc), build_log=log)
        try:
            send_build_failure(config, updated)
        except Exception as mail_exc:  # noqa: BLE001
            print(f"Build failed and failure email failed: {mail_exc}")
        print(f"Build {token} failed: {exc}")
        return True


def run_worker(config: Config | None = None, *, once: bool = False, poll_seconds: float = 5.0) -> None:
    config = config or load_config()
    ensure_directories(config)
    initialize_database(config)
    worker_id = f"{socket.gethostname()}:{time.time_ns()}"
    print(f"Worker {worker_id} started in {config.builder_mode} mode.")

    cleanup_tick = 0
    while True:
        did_work = process_one(config, worker_id)
        cleanup_tick += 1
        if cleanup_tick >= 12:
            expired = expire_old_artifacts(config)
            if expired:
                print(f"Expired {expired} artifact(s).")
            cleanup_tick = 0
        if once:
            break
        if not did_work:
            time.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process at most one build and exit.")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    args = parser.parse_args()
    run_worker(once=args.once, poll_seconds=args.poll_seconds)


if __name__ == "__main__":
    main()

