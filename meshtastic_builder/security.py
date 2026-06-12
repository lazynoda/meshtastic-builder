from __future__ import annotations

import re
import secrets


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,80}$")


def generate_public_token() -> str:
    return secrets.token_urlsafe(32)


def validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) > 254 or not EMAIL_RE.match(normalized):
        raise ValueError("Email invalido.")
    return normalized


def validate_public_token(token: str) -> str:
    if not TOKEN_RE.match(token):
        raise ValueError("Token invalido.")
    return token


def safe_tag_for_path(tag: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", tag)

