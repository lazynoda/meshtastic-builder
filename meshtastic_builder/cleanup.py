from __future__ import annotations

from pathlib import Path

from .config import Config, load_config
from .db import list_expired_successes, mark_build_expired, parse_iso, utc_now


def build_is_expired(build: dict[str, object]) -> bool:
    expires_at = build.get("expires_at")
    if not isinstance(expires_at, str) or not expires_at:
        return False
    return parse_iso(expires_at) <= utc_now()


def expire_build_artifact(config: Config, build: dict[str, object]) -> bool:
    artifact_path = build.get("artifact_path")
    if artifact_path:
        path = Path(str(artifact_path))
        if path.exists() and path.is_file():
            path.unlink()
    mark_build_expired(config, int(build["id"]))
    return True


def expire_old_artifacts(config: Config | None = None) -> int:
    config = config or load_config()
    count = 0
    for build in list_expired_successes(config):
        expire_build_artifact(config, build)
        count += 1
    return count


if __name__ == "__main__":
    cfg = load_config()
    expired = expire_old_artifacts(cfg)
    print(f"Expired {expired} build artifact(s).")
