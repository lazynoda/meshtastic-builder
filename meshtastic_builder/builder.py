from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .db import iso_now


PATCH_RELATIVE_PATH = Path("docker") / "patches" / "userprefs-ext.patch"

PATCH_FAILURE_MARKER = "CODE_OPTIONS_PATCH_FAILED"


@dataclass(frozen=True)
class BuildArtifact:
    path: Path
    sha256: str
    size_bytes: int
    log: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_info(build: dict[str, object]) -> str:
    return "\n".join(
        [
            "Meshtastic Builder Artifact",
            f"created_at={iso_now()}",
            f"build_token={build['public_token']}",
            f"device_id={build['device_id']}",
            f"platformio_env={build['platformio_env']}",
            f"firmware_tag={build['firmware_tag']}",
            f"firmware_sha={build['firmware_sha']}",
            f"code_options={build.get('code_options') or 'none'}",
            "source=https://github.com/meshtastic/firmware",
            "license=GPL-3.0-or-later",
            "",
        ]
    )


def run_build(config: Config, build: dict[str, object]) -> BuildArtifact:
    config.artifact_dir.mkdir(parents=True, exist_ok=True)
    token = str(build["public_token"])
    final_zip = config.artifact_dir / f"{token}.zip"
    job_root = config.job_dir / token
    input_dir = job_root / "input"
    output_dir = job_root / "output"

    if job_root.exists():
        shutil.rmtree(job_root)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "userPrefs.jsonc").write_text(str(build["prefs_jsonc"]), encoding="utf-8")
    (input_dir / "BUILD_INFO.txt").write_text(build_info(build), encoding="utf-8")
    if build.get("code_options"):
        patch = config.root_dir / PATCH_RELATIVE_PATH
        if not patch.is_file():
            raise RuntimeError(f"Falta el parche de opciones avanzadas en {patch}.")
        shutil.copyfile(patch, input_dir / "userprefs-ext.patch")

    try:
        if config.builder_mode == "fake":
            log = run_fake_build(build, input_dir, final_zip)
        else:
            log = run_docker_build(config, build, input_dir, output_dir, final_zip)
        return BuildArtifact(
            path=final_zip,
            sha256=sha256_file(final_zip),
            size_bytes=final_zip.stat().st_size,
            log=log,
        )
    finally:
        if job_root.exists():
            shutil.rmtree(job_root, ignore_errors=True)


def run_fake_build(build: dict[str, object], input_dir: Path, final_zip: Path) -> str:
    with zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(input_dir / "BUILD_INFO.txt", "BUILD_INFO.txt")
        zf.write(input_dir / "userPrefs.jsonc", "userPrefs.jsonc")
        zf.writestr(
            f"firmware-{build['platformio_env']}.txt",
            "Fake firmware artifact for local queue testing.\n",
        )
    return "Fake builder mode completed successfully."


def run_docker_build(
    config: Config,
    build: dict[str, object],
    input_dir: Path,
    output_dir: Path,
    final_zip: Path,
) -> str:
    transport = docker_transport(config)
    if transport == "copy":
        return run_docker_build_copy(config, build, input_dir, output_dir, final_zip)
    if transport != "bind":
        raise ValueError(f"Unsupported Docker transport: {config.docker_transport}")
    return run_docker_build_bind(config, build, input_dir, output_dir, final_zip)


def raise_build_failure(returncode: int, log: str) -> None:
    if PATCH_FAILURE_MARKER in log:
        raise RuntimeError(
            "Las opciones avanzadas no se pudieron aplicar a esta version de firmware. "
            "Prueba con una version mas reciente o desactiva las opciones avanzadas."
        )
    raise RuntimeError(f"Docker build failed with exit code {returncode}.\n{log[-4000:]}")


def docker_transport(config: Config) -> str:
    configured = config.docker_transport.strip().lower()
    if configured != "auto":
        return configured
    docker_host = os.getenv("DOCKER_HOST", "").strip().lower()
    if docker_host.startswith(("ssh://", "tcp://", "http://", "https://")):
        return "copy"
    return "bind"


def run_docker_build_bind(
    config: Config,
    build: dict[str, object],
    input_dir: Path,
    output_dir: Path,
    final_zip: Path,
) -> str:
    command = [
        config.docker_binary,
        "run",
        "--rm",
        "--network",
        config.docker_network,
        "--cpus",
        config.docker_cpus,
        "--memory",
        config.docker_memory,
        "--pids-limit",
        str(config.docker_pids_limit),
        "-v",
        f"{input_dir.resolve()}:/work/input:ro",
        "-v",
        f"{output_dir.resolve()}:/work/output",
        config.builder_image,
        str(build["firmware_tag"]),
        str(build["firmware_sha"]),
        str(build["platformio_env"]),
    ]
    proc = subprocess.run(
        command,
        cwd=str(config.root_dir),
        capture_output=True,
        text=True,
        timeout=config.build_timeout_seconds,
        check=False,
    )
    log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    if proc.returncode != 0:
        raise_build_failure(proc.returncode, log)

    zip_candidates = sorted(output_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    if zip_candidates:
        shutil.copy2(zip_candidates[0], final_zip)
        return log

    files = [path for path in output_dir.rglob("*") if path.is_file()]
    if not files:
        raise RuntimeError("Docker build completed but produced no files.")
    with zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(output_dir))
    return log + "\nPackaged output directory because builder did not emit a zip."


def run_docker_build_copy(
    config: Config,
    build: dict[str, object],
    input_dir: Path,
    output_dir: Path,
    final_zip: Path,
) -> str:
    create_command = [
        config.docker_binary,
        "create",
        "--network",
        config.docker_network,
        "--cpus",
        config.docker_cpus,
        "--memory",
        config.docker_memory,
        "--pids-limit",
        str(config.docker_pids_limit),
        config.builder_image,
        str(build["firmware_tag"]),
        str(build["firmware_sha"]),
        str(build["platformio_env"]),
    ]
    create_proc = subprocess.run(
        create_command,
        cwd=str(config.root_dir),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    create_log = (create_proc.stdout or "") + ("\n" + create_proc.stderr if create_proc.stderr else "")
    if create_proc.returncode != 0:
        raise RuntimeError(
            f"Docker container creation failed with exit code {create_proc.returncode}.\n{create_log[-4000:]}"
        )
    container_id = (create_proc.stdout or "").strip().splitlines()[-1].strip()
    if not container_id:
        raise RuntimeError("Docker container creation did not return a container id.")

    logs = [create_log]
    try:
        copy_input = subprocess.run(
            [config.docker_binary, "cp", f"{input_dir.resolve()}/.", f"{container_id}:/work/input"],
            cwd=str(config.root_dir),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        logs.append((copy_input.stdout or "") + ("\n" + copy_input.stderr if copy_input.stderr else ""))
        if copy_input.returncode != 0:
            raise RuntimeError(
                f"Docker input copy failed with exit code {copy_input.returncode}.\n{logs[-1][-4000:]}"
            )

        start_proc = subprocess.run(
            [config.docker_binary, "start", "-a", container_id],
            cwd=str(config.root_dir),
            capture_output=True,
            text=True,
            timeout=config.build_timeout_seconds,
            check=False,
        )
        logs.append((start_proc.stdout or "") + ("\n" + start_proc.stderr if start_proc.stderr else ""))
        if start_proc.returncode != 0:
            raise_build_failure(start_proc.returncode, "".join(logs))

        copy_output = subprocess.run(
            [config.docker_binary, "cp", f"{container_id}:/work/output/.", str(output_dir.resolve())],
            cwd=str(config.root_dir),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        logs.append((copy_output.stdout or "") + ("\n" + copy_output.stderr if copy_output.stderr else ""))
        if copy_output.returncode != 0:
            raise RuntimeError(
                f"Docker output copy failed with exit code {copy_output.returncode}.\n{logs[-1][-4000:]}"
            )

        log = "".join(logs)
        zip_candidates = sorted(output_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
        if zip_candidates:
            shutil.copy2(zip_candidates[0], final_zip)
            return log

        files = [path for path in output_dir.rglob("*") if path.is_file()]
        if not files:
            raise RuntimeError("Docker build completed but produced no files.")
        with zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                zf.write(path, path.relative_to(output_dir))
        return log + "\nPackaged output directory because builder did not emit a zip."
    finally:
        subprocess.run(
            [config.docker_binary, "rm", "-f", container_id],
            cwd=str(config.root_dir),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
