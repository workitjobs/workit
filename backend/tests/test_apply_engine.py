"""
The Fill engine's download (KAN-836, W7; routers/apply_app.py,
services/engine_builds.py, scripts/publish_engine.py): a build the publish
script signed comes back whole, decrypted only with this session's key; the
newest build that fits the app's version is the one sent; an expired or
another session's key opens nothing. An in-memory bucket stands in for
Storage, so nothing reaches Supabase.
"""

import base64
import datetime
import hashlib
import json
import uuid

import httpx
import pytest
from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings
from app.deps import get_current_account
from app.main import app
from app.routers import apply_app
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.scripts import publish_engine
from app.services import engine_builds

pytestmark = pytest.mark.anyio

NOW = datetime.datetime(2026, 11, 15, 12, 0, 0, tzinfo=datetime.UTC)
BUNDLE = b"var FillEngine = {version: '0.3.48', call() {}};\n"
SIGNER = Ed25519PrivateKey.generate()


class Bucket:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def download(self, path):
        if path not in self.files:
            raise RuntimeError(f"Object not found: {path}")
        return self.files[path]

    def upload(self, path, data, options=None):
        if path in self.files and (options or {}).get("upsert") != "true":
            raise RuntimeError("The resource already exists")
        self.files[path] = data

    def list(self, path=None, options=None):
        search = (options or {}).get("search", "")
        return [{"name": name} for name in self.files if search in name]


class Storage:
    def __init__(self):
        self.bucket = Bucket()

    def from_(self, name):
        assert name == engine_builds.BUCKET
        return self.bucket


class Supabase:
    def __init__(self):
        self.storage = Storage()


def _account(account_type=AccountType.APPLICANT):
    return AuthenticatedAccount(id=uuid.uuid4(), email="sam@example.com", full_name="Sam Seeker",
                                account_type=account_type, onboarding_completed=True)


@pytest.fixture
def supabase(monkeypatch):
    client = Supabase()
    monkeypatch.setattr(apply_app, "get_supabase", lambda: client)
    monkeypatch.setattr(apply_app, "_now", lambda: NOW)
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key-for-tests")
    get_settings.cache_clear()
    engine_builds._index = None
    engine_builds._bundles.clear()
    yield client
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def _signed_in(account=None, session="session-1"):
    account = account or _account()
    app.dependency_overrides[get_current_account] = lambda: account
    app.dependency_overrides[apply_app._session_id] = lambda: session


def _publish(client, bundle=BUNDLE, min_app="0.1.0"):
    line = publish_engine.entry(bundle, SIGNER, min_app, NOW)
    publish_engine.publish(client.storage, bundle, line)
    engine_builds._index = None
    return line


def _api():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000")


async def _download(app_version="0.1.0"):
    async with _api() as api:
        got = await api.get("/apply-app/engine", params={"app_version": app_version})
        if got.status_code != 200:
            return got, None
        sent = got.json()
        key = await api.post("/apply-app/engine-key", json={"key_id": sent["key_id"], "expires_at": sent["expires_at"]})
        return sent, key


def _open(sent, key) -> bytes:
    raw = AESGCM(base64.b64decode(key.json()["key"]))
    return raw.decrypt(base64.b64decode(sent["nonce"]), base64.b64decode(sent["ciphertext"]), None)


async def test_a_published_build_comes_back_whole_and_its_signature_holds(supabase):
    _publish(supabase)
    _signed_in()
    sent, key = await _download()
    plain = _open(sent, key)
    assert plain == BUNDLE
    assert sent["sha256"] == hashlib.sha256(BUNDLE).hexdigest()
    SIGNER.public_key().verify(base64.b64decode(sent["signature"]), plain)
    assert BUNDLE not in base64.b64decode(sent["ciphertext"])


async def test_the_newest_build_that_fits_the_app_is_sent(supabase):
    _publish(supabase, b"var FillEngine = 1;", "0.1.0")
    _publish(supabase, b"var FillEngine = 2;", "0.2.0")
    _publish(supabase, b"var FillEngine = 3;", "0.1.0")  # a fix for the older apps, published later
    _signed_in()
    assert _open(*await _download("0.1.9")) == b"var FillEngine = 3;"
    assert _open(*await _download("0.2")) == b"var FillEngine = 2;"
    refused, _ = await _download("0.0.9")
    assert refused.status_code == 404


async def test_another_sessions_key_opens_nothing(supabase):
    _publish(supabase)
    account = _account()
    _signed_in(account, "session-1")
    async with _api() as api:
        sent = (await api.get("/apply-app/engine", params={"app_version": "0.1.0"})).json()
        _signed_in(account, "session-2")
        key = await api.post("/apply-app/engine-key", json={"key_id": sent["key_id"], "expires_at": sent["expires_at"]})
    with pytest.raises(InvalidTag):
        _open(sent, key)


@pytest.mark.parametrize("shift", [0, engine_builds.KEY_TTL.total_seconds() + 1])
async def test_a_key_is_refused_once_expired_or_asked_for_too_far_ahead(supabase, shift):
    _signed_in()
    expires = int(NOW.timestamp() + shift)
    async with _api() as api:
        refused = await api.post("/apply-app/engine-key", json={"key_id": "a" * 22, "expires_at": expires})
    assert refused.status_code == 410


async def test_bytes_that_are_not_the_named_build_are_never_sent(supabase):
    line = _publish(supabase)
    supabase.storage.bucket.files[f"{line['sha256']}.js"] = b"var FillEngine = 'swapped';"
    _signed_in()
    refused, _ = await _download()
    assert refused.status_code == 503


async def test_no_builds_yet_is_a_503_not_a_crash(supabase):
    _signed_in()
    refused, _ = await _download()
    assert refused.status_code == 503


async def test_a_company_account_gets_no_engine(supabase):
    _publish(supabase)
    _signed_in(_account(AccountType.COMPANY))
    refused, _ = await _download()
    assert refused.status_code == 403


async def test_a_token_with_no_session_gets_no_key(monkeypatch):
    async def claims(token):
        return {"sub": str(uuid.uuid4())}

    monkeypatch.setattr(apply_app, "decode_access_token", claims)
    with pytest.raises(apply_app.HTTPException) as refused:
        await apply_app._session_id(apply_app.HTTPAuthorizationCredentials(scheme="Bearer", credentials="t"))
    assert refused.value.status_code == 403


def test_the_script_refuses_a_bundle_with_a_source_map():
    with pytest.raises(SystemExit):
        publish_engine.entry(BUNDLE + b"//# sourceMappingURL=engine.js.map\n", SIGNER, "0.1.0", NOW)


async def test_a_publish_again_adds_nothing_and_a_reverted_pointer_serves_the_older_build(supabase):
    first, second = b"var FillEngine = 1;", b"var FillEngine = 2;"
    old = _publish(supabase, first)
    _publish(supabase, second)
    again = publish_engine.entry(second, SIGNER, "0.1.0", NOW)
    assert publish_engine.publish(supabase.storage, second, again) is None  # a re-run of the workflow
    _publish(supabase, first)  # main's engine pointer moved back
    _signed_in()
    sent, _ = await _download()
    assert sent["sha256"] == old["sha256"]
    assert len(json.loads(supabase.storage.bucket.files[engine_builds.INDEX])) == 2


def test_a_key_apply_does_not_hold_signs_nothing(tmp_path, monkeypatch, capsys):
    key, engine, held = tmp_path / "key.pem", tmp_path / "engine.js", tmp_path / "engine_download.py"
    public = publish_engine.make_key(key)
    engine.write_bytes(BUNDLE)
    monkeypatch.setattr(publish_engine, "APP_KEY", held)
    dry_run = ["publish", "--key", str(key), "--engine", str(engine), "--dry-run"]
    for text in ('PUBLIC_KEY = ""\n', f'PUBLIC_KEY = "{publish_engine.public_key(SIGNER)}"\n'):
        held.write_text(text)
        with pytest.raises(SystemExit):
            publish_engine.main(dry_run)
    held.write_text(f'PUBLIC_KEY = "{public}"\n')
    publish_engine.main(dry_run)
    assert "Dry run" in capsys.readouterr().out


def test_a_new_key_is_never_written_over_an_old_one(tmp_path):
    path = tmp_path / "engine-key.pem"
    public = publish_engine.make_key(path)
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        publish_engine.make_key(path)
    private = publish_engine.load_key(path)
    Ed25519PublicKey.from_public_bytes(base64.b64decode(public)).verify(private.sign(b"x"), b"x")
    with pytest.raises(InvalidSignature):
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public)).verify(SIGNER.sign(b"x"), b"x")
