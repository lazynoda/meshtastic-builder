from __future__ import annotations

import re
import secrets


TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,80}$")


def generate_public_token() -> str:
    return secrets.token_urlsafe(32)


def validate_public_token(token: str) -> str:
    if not TOKEN_RE.match(token):
        raise ValueError("Token invalido.")
    return token


def safe_tag_for_path(tag: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", tag)
