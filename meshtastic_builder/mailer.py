from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from pathlib import Path

from .config import Config
from .db import iso_now


def _write_outbox(config: Config, message: dict[str, str]) -> None:
    config.mail_dir.mkdir(parents=True, exist_ok=True)
    path = config.mail_dir / "outbox.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"created_at": iso_now(), **message}, ensure_ascii=False) + "\n")


def _send(config: Config, *, to: str, subject: str, body: str) -> None:
    if not config.smtp_host:
        _write_outbox(config, {"to": to, "subject": subject, "body": body})
        return

    msg = EmailMessage()
    msg["From"] = config.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=20) as smtp:
        if config.smtp_tls:
            smtp.starttls()
        if config.smtp_username:
            smtp.login(config.smtp_username, config.smtp_password)
        smtp.send_message(msg)


def send_build_success(config: Config, build: dict[str, object]) -> None:
    token = str(build["public_token"])
    download_url = f"{config.base_url}/download/{token}"
    body = "\n".join(
        [
            "Tu firmware personalizado de Meshtastic esta listo.",
            "",
            f"Dispositivo: {build['device_id']}",
            f"Version: {build['firmware_tag']}",
            f"SHA: {build['firmware_sha']}",
            f"Descarga: {download_url}",
            f"Disponible hasta: {build['expires_at']}",
            f"SHA256 del ZIP: {build['artifact_sha256']}",
            "",
            "El enlace es privado y expirara automaticamente.",
        ]
    )
    _send(config, to=str(build["email"]), subject="Tu firmware Meshtastic esta listo", body=body)


def send_build_failure(config: Config, build: dict[str, object]) -> None:
    body = "\n".join(
        [
            "No se pudo compilar tu firmware personalizado de Meshtastic.",
            "",
            f"Dispositivo: {build['device_id']}",
            f"Version: {build['firmware_tag']}",
            "Puedes revisar los parametros y crear una nueva solicitud.",
        ]
    )
    _send(config, to=str(build["email"]), subject="No se pudo compilar tu firmware Meshtastic", body=body)


def outbox_path(config: Config) -> Path:
    return config.mail_dir / "outbox.jsonl"

