"""The Fill engine from WorkIt (KAN-836, W7; apply.engine_download, apply.fill_engine.source): a download WorkIt
signed comes back as text; a wrong signature, a changed download, no engine key, no sign-in or no build for this
version each stop it with one sentence; WorkIt's engine reaches Node on stdin with no engine file anywhere; and
the live API's connection trusts only Cloudflare's CAs. The server half is backend/tests/test_apply_engine.py."""

import base64
import hashlib
import secrets
import ssl

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from apply import build, engine_download, fill_engine, rehearsal, workit
from apply.adapters import SetupError
from apply.engine_download import EngineRefused
from apply.plain import extension
from apply.workit import NotLoggedIn, Unreachable, WorkItError

SIGNER = Ed25519PrivateKey.generate()
PUBLIC = base64.b64encode(SIGNER.public_key().public_bytes(serialization.Encoding.Raw,
                                                           serialization.PublicFormat.Raw)).decode()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


class WorkIt:
    """WorkIt's two engine routes as the server answers them, with the bundle sealed under a fresh key."""

    def __init__(self, bundle: bytes, signer=SIGNER, refuse: Exception | None = None, failures: int = 0):
        self.key, nonce = secrets.token_bytes(32), secrets.token_bytes(12)
        self.sent = {"sha256": hashlib.sha256(bundle).hexdigest(), "signature": b64(signer.sign(bundle)),
                     "key_id": "k" * 22, "expires_at": 2_000_000_000, "nonce": b64(nonce),
                     "ciphertext": b64(AESGCM(self.key).encrypt(nonce, bundle, None))}
        self.refuse = refuse
        self.failures = failures  # the first tries WorkIt doesn't answer
        self.calls = []

    def call(self, method, path, body=None, timeout=None):
        self.calls.append((method, path, body))
        if self.refuse:
            raise self.refuse
        if self.failures and path.startswith("/apply-app/engine?"):
            self.failures -= 1
            raise Unreachable("api.workitjobs.ai: timed out")
        if path.startswith("/apply-app/engine?"):
            return self.sent
        assert body == {"key_id": self.sent["key_id"], "expires_at": self.sent["expires_at"]}
        return {"key": b64(self.key)}


def test_a_signed_download_comes_back_as_its_text_and_names_the_apps_version():
    client = WorkIt(b"var FillEngine = {};")
    assert engine_download.download(client, PUBLIC) == "var FillEngine = {};"
    assert client.calls[0][1] == f"/apply-app/engine?app_version={engine_download.app_version()}"


def no_wait(seconds):
    pass


def test_a_wrong_signature_stops_it_at_once_with_its_one_sentence():
    client = WorkIt(b"var FillEngine = {};", signer=Ed25519PrivateKey.generate())
    with pytest.raises(EngineRefused, match="signature check") as refused:
        engine_download.download(client, PUBLIC, sleep=no_wait)
    assert isinstance(refused.value, SetupError)  # a run reports it as setup, never as a fill bug
    assert refused.value.lasting and len(client.calls) == 2  # one try: another would get the same file


def test_workit_not_answering_is_tried_again_with_growing_waits():
    client, waits = WorkIt(b"var FillEngine = {};", failures=2), []
    assert engine_download.download(client, PUBLIC, sleep=waits.append) == "var FillEngine = {};"
    assert waits == [engine_download.WAIT, 2 * engine_download.WAIT]


def test_after_its_last_try_it_says_to_check_the_connection_and_may_try_again_later():
    client, waits = WorkIt(b"x", failures=engine_download.TRIES), []
    with pytest.raises(EngineRefused, match="Check your connection") as refused:
        engine_download.download(client, PUBLIC, sleep=waits.append)
    assert not refused.value.lasting and len(waits) == engine_download.TRIES - 1


def test_a_download_changed_on_the_way_is_never_run():
    client = WorkIt(b"var FillEngine = {};")
    sealed = bytearray(base64.b64decode(client.sent["ciphertext"]))
    sealed[0] ^= 1
    client.sent["ciphertext"] = b64(bytes(sealed))
    with pytest.raises(EngineRefused, match="could not be decrypted") as refused:
        engine_download.download(client, PUBLIC, sleep=no_wait)
    assert not refused.value.lasting
    assert sum(path.startswith("/apply-app/engine?") for _, path, _ in client.calls) == engine_download.TRIES


def test_an_answer_of_another_shape_is_refused_not_a_crash():
    client = WorkIt(b"var FillEngine = {};")
    client.sent = {"error": "not an engine"}
    with pytest.raises(EngineRefused, match="could not be decrypted"):
        engine_download.download(client, PUBLIC, sleep=no_wait)


def test_with_no_engine_key_nothing_is_downloaded():
    client = WorkIt(b"var FillEngine = {};")
    with pytest.raises(EngineRefused, match="no engine key") as refused:
        engine_download.download(client, "")
    assert refused.value.lasting
    assert client.calls == []


@pytest.mark.parametrize(("refusal", "said"), [
    (NotLoggedIn("no login"), "sign in to WorkIt first"),
    (WorkItError("GET: 404", 404), "update the app"),
    (WorkItError("GET: 503", 503), "WorkIt did not send"),
])
def test_workit_refusing_says_what_to_do(refusal, said):
    with pytest.raises(EngineRefused, match=said):
        engine_download.download(WorkIt(b"x", refuse=refusal), PUBLIC, sleep=no_wait)


@pytest.fixture
def from_workit(monkeypatch, tmp_path):
    """This process on WorkIt's engine, its download the checkout's real bundle; no engine file it can read."""
    real = fill_engine.ENGINE.read_text()
    downloads = []

    def download():
        downloads.append(1)
        return real

    monkeypatch.setattr(engine_download, "download", download)
    monkeypatch.setattr(fill_engine, "_policy_says_workit", lambda: True)
    monkeypatch.setattr(fill_engine, "ENGINE", tmp_path / "no-engine-here.js")
    monkeypatch.setattr(fill_engine, "_download", {})
    monkeypatch.setattr(fill_engine, "_nodes", {})
    monkeypatch.setattr(fill_engine, "_loaded", {})
    yield downloads
    for node in fill_engine._nodes.values():
        node.kill()


def test_workits_engine_runs_in_node_from_memory_downloaded_once(from_workit):
    assert fill_engine.call_without_page("textOf", "<p>one</p>") == "one"
    fill_engine.ready()
    assert fill_engine.source() == fill_engine.source()
    assert not fill_engine.fresh()  # the download stays the launch's engine
    assert from_workit == [1]
    assert not fill_engine.ENGINE.exists()
    assert extension.engine_identity()["sha256"] == hashlib.sha256(fill_engine.source().encode()).hexdigest()


def test_a_wrong_signature_is_refused_again_at_once(from_workit, monkeypatch):
    def refuse():
        from_workit.append(1)
        raise EngineRefused(engine_download.BAD_SIGNATURE, lasting=True)

    monkeypatch.setattr(engine_download, "download", refuse)
    for _ in range(2):
        with pytest.raises(EngineRefused):
            fill_engine.ready()
    assert from_workit == [1]


def test_a_network_refusal_is_tried_again_at_the_next_run(from_workit, monkeypatch):
    real = engine_download.download

    def once_down():
        if not from_workit:
            from_workit.append(1)
            raise EngineRefused("WorkIt did not send the Fill engine")
        return real()

    monkeypatch.setattr(engine_download, "download", once_down)
    with pytest.raises(EngineRefused):
        fill_engine.ready()
    fill_engine.ready()  # the next run: downloaded this time
    assert from_workit == [1, 1]


def test_a_refused_engine_stops_a_run_before_it_opens_anything(monkeypatch):
    def refuse():
        raise EngineRefused(engine_download.BAD_SIGNATURE, lasting=True)

    class Untouched:  # the run's adapters and profile: any use of them comes after the engine check, too late
        def __getattr__(self, name):
            raise AssertionError(f"the run used {name} before its engine was checked")

    monkeypatch.setattr(fill_engine, "ready", refuse)
    with pytest.raises(EngineRefused, match="signature check"):
        rehearsal.rehearse(["https://job-boards.greenhouse.io/acme/jobs/1"], Untouched(), Untouched())


def test_the_student_build_always_runs_workits_engine(monkeypatch):
    monkeypatch.setattr(build, "STUDENT", True)
    monkeypatch.setattr(fill_engine, "_policy_says_workit", lambda: False)
    assert fill_engine.from_workit()
    assert build.STUDENT_POLICIES["fill_engine"] == "workit"


def test_the_live_api_and_its_session_refresh_are_pinned_to_cloudflares_cas_and_nothing_else():
    assert workit._pinned("http://localhost:8000/apply-app/engine") is None
    assert workit._pinned("https://example.com/") is None
    # The refresh at Supabase carries the session: unpinned, it gave the download away.
    assert workit._pinned(workit.LIVE.auth + "/auth/v1/token?grant_type=refresh_token") is not None
    pinned = workit._pinned(workit.LIVE.api + "/apply-app/engine")
    names = {dict(part[0] for part in ca["subject"])["commonName"] for ca in pinned.get_ca_certs()}
    assert names == {"ISRG Root X1", "ISRG Root X2", "GTS Root R1", "GTS Root R3", "GTS Root R4",
                     "SSL.com TLS RSA Root CA 2022", "SSL.com TLS ECC Root CA 2022",
                     "SSL.com Root Certification Authority RSA", "SSL.com Root Certification Authority ECC",
                     "USERTrust RSA Certification Authority", "USERTrust ECC Certification Authority",
                     "Sectigo Public Server Authentication Root R46", "Sectigo Public Server Authentication Root E46"}
    assert pinned.verify_mode == ssl.CERT_REQUIRED and pinned.check_hostname

