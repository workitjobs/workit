"""
The Fill engine builds that WorkIt Auto Apply downloads (KAN-836, W7 of
docs/desktop_application_auto_apply.md; D3, D27).

A build is the engine's one bundle (the fill-engine repo's dist/engine.js),
signed with WorkIt's Ed25519 engine key by `app.scripts.publish_engine`, run
by hand. It lives in the private `ApplyEngine` Storage bucket as
`<sha256>.js`, beside `builds.json`: every build in the order it was
published, each {sha256, signature, min_app, published_at}. A build fits an
app whose version is `min_app` or later. An app gets the build made for the
nearest version at or below its own (the highest `min_app` that fits), and
of those the last published. A build that would break older apps is
published with a higher `min_app`, so those apps keep the build before it,
and a fix for them published later never reaches a newer app.

The server never checks a signature: the app does, with the public key
compiled into it, so a bucket someone else wrote to still can't make an app
run their code.

Each download is encrypted with AES-GCM under a key made for it alone: an
HMAC of the account, its Supabase session, a random key id and the second
the key expires, under a key derived from the API's service key. The key
route makes the same key again, for the same account and session, until it
expires. So the server keeps no key, and every API instance makes the same
one.
"""

import asyncio
import base64
import datetime
import hashlib
import hmac
import json
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BUCKET = "ApplyEngine"
INDEX = "builds.json"
# How long a download's key can be asked for: the app asks at once.
KEY_TTL = datetime.timedelta(minutes=2)
# How long the list of builds is kept in memory; a publish reaches every app within it.
INDEX_TTL = 60.0
VERSION = re.compile(r"^\d{1,4}(?:\.\d{1,4}){0,3}$")

_index: tuple[float, list[dict]] | None = None
_bundles: dict[str, bytes] = {}  # by sha256: a build never changes


class NoBuild(Exception):
    """No published build fits this app's version."""


@dataclass(frozen=True)
class Download:
    sha256: str
    signature: str
    key_id: str
    expires_at: int
    nonce: str
    ciphertext: str


def version(text: str) -> tuple[int, ...]:
    """'0.1.0' as (0, 1, 0), so versions compare by number. A shorter one is padded: 1.2 is 1.2.0."""
    if not VERSION.match(text):
        raise ValueError(f"not a version: {text!r}")
    parts = tuple(int(p) for p in text.split("."))
    return parts + (0,) * (4 - len(parts))


def newest_fit(builds: list[dict], app_version: str) -> dict:
    """The build made for the nearest app version at or below this one (the highest min_app that fits), and of
    those the last published. So a fix published later for older apps never reaches a newer app."""
    have = version(app_version)
    fits = [(version(b["min_app"]), i, b) for i, b in enumerate(builds) if version(b["min_app"]) <= have]
    if not fits:
        raise NoBuild(app_version)
    return max(fits, key=lambda fit: fit[:2])[2]


async def builds(get_supabase: Callable) -> list[dict]:
    """builds.json, kept for INDEX_TTL seconds. A Storage failure raises."""
    global _index
    now = time.monotonic()
    if _index is None or now - _index[0] > INDEX_TTL:
        raw = await asyncio.to_thread(get_supabase().storage.from_(BUCKET).download, INDEX)
        _index = (now, json.loads(raw))
    return _index[1]


async def bundle(get_supabase: Callable, sha256: str) -> bytes:
    """A build's bytes, read once per API process. Bytes that aren't the sha256 the list names raise."""
    if sha256 not in _bundles:
        data = await asyncio.to_thread(get_supabase().storage.from_(BUCKET).download, f"{sha256}.js")
        if hashlib.sha256(data).hexdigest() != sha256:
            raise ValueError(f"{sha256}.js in {BUCKET} is not the build its name says")
        _bundles[sha256] = data
    return _bundles[sha256]


def key(service_key: str, account_id: str, session_id: str, key_id: str, expires_at: int) -> bytes:
    """The AES-256 key of one download."""
    root = hmac.new(service_key.encode(), b"workit apply-engine key", hashlib.sha256).digest()
    return hmac.new(root, f"{account_id}|{session_id}|{key_id}|{expires_at}".encode(), hashlib.sha256).digest()


def encrypt(build: dict, data: bytes, service_key: str, account_id: str, session_id: str,
            now: datetime.datetime) -> Download:
    key_id = secrets.token_urlsafe(16)
    expires_at = int((now + KEY_TTL).timestamp())
    nonce = secrets.token_bytes(12)
    sealed = AESGCM(key(service_key, account_id, session_id, key_id, expires_at)).encrypt(nonce, data, None)
    return Download(sha256=build["sha256"], signature=build["signature"], key_id=key_id, expires_at=expires_at,
                    nonce=_b64(nonce), ciphertext=_b64(sealed))


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()
