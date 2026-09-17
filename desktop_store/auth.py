from __future__ import annotations

import hashlib
import hmac
import os
import re

ITERATIONS = 210_000
USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{2,31}$")


def valid_username(username: str) -> bool:
    return bool(USERNAME_RE.match((username or "").strip()))


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return hmac.compare_digest(digest.hex(), hash_hex)
