from __future__ import annotations

import argparse
import socket
import time
import traceback

from .build_failures import CODE_INTERNAL, BuildFailure, classify_build_log, failure_summary
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


def process_one(config: Config, worker_id: str) -> bool:
    reset_stale_running(config)
    build = claim_next_build(config, worker_id)
    if build is None:
        return False

    token = build["public_token"]
    print(f"Claimed build {token} for {build['platformio_env']} at {build['firmware_tag']}")
    try:
        artifact = run_build(config, build)
        mark_build_success(
            config,
            int(build["id"]),
            artifact_path=artifact.path,
            artifact_sha256=artifact.sha256,
            artifact_size_bytes=artifact.size_bytes,
            build_log=artifact.log,
        )
        print(f"Build {token} succeeded: {artifact.path}")
        return True
    except BuildFailure as failure:
        _record_failure(config, build, failure.code, failure.phase, failure.detail, failure.log)
        return True
    except Exception as exc:  # noqa: BLE001
        # Nothing named it, so the traceback is the log and the exception is the
        # evidence line. Still classified, in case a builder marker made it into
        # an exception message on the way up.
        trace = traceback.format_exc()
        code, phase, detail = classify_build_log(str(exc))
        if code == "unknown":
            code, phase, detail = CODE_INTERNAL, "worker", str(exc)
        _record_failure(config, build, code, phase, detail, trace)
        return True


def _record_failure(
    config: Config,
    build: dict[str, object],
    code: str,
    phase: str,
    detail: str,
    log: str,
) -> None:
    """Store the failure and print the one line an operator needs to triage it."""
    summary = failure_summary(code, phase, detail)
    mark_build_failure(
        config,
        int(build["id"]),
        error_message=detail,
        error_code=code,
        # The summary leads, so `head` on a stored log answers "what broke".
        build_log=f"{summary}\n{log}",
    )
    print(
        f"Build {build['public_token']} FAILED "
        f"[{code}/{phase or 'unknown'}] {build['platformio_env']} at {build['firmware_tag']}: {detail}"
    )


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

