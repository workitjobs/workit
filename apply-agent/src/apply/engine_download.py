"""The Fill engine from WorkIt (KAN-836, W7 of docs/desktop_application_auto_apply.md; D3, D27, D28).

The Student build ships no engine: at each launch it downloads the newest build that fits its version
(`GET /apply-app/engine`), asks for that download's key (`POST /apply-app/engine-key`, good for two
minutes and for this session only), decrypts it in memory with AES-GCM, and checks its Ed25519
signature with PUBLIC_KEY, compiled into the app. The plain text is never written anywhere: the Node
process reads it on stdin, CDP Workers get it through page.evaluate, and plain Workers over native
messaging (apply.fill_engine.source). The connection to api.workitjobs.ai trusts only the certificate
authorities Cloudflare uses (apply.workit, D28), so a proxy on the computer can't read the download.

A Developer checkout uses the engine checkout's file unless its policies say `fill_engine: workit`
(policies.default.yaml). WorkIt keeps its builds and their signing key (backend/app/services/engine_builds.py,
backend/app/scripts/publish_engine.py).
"""

import base64
import hashlib
from importlib.metadata import version
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from apply.adapters import SetupError
from apply.model import FillError

if TYPE_CHECKING:
    from apply.workit import WorkIt

# The public half of WorkIt's engine-signing key (`publish_engine make-key`), base64 of its 32 bytes. Only builds
# its private half signed run. Empty until the key is made: then every download is refused.
PUBLIC_KEY = ""

NO_KEY = "this copy of WorkIt Auto Apply has no engine key, so it can't check the Fill engine"
BAD_SIGNATURE = ("the Fill engine from WorkIt failed its signature check, so it did not run. Someone may be "
                 "changing your connection to WorkIt: try another network, then update WorkIt Auto Apply")
UNOPENED = "the Fill engine from WorkIt could not be decrypted. Restart WorkIt Auto Apply to download it again"
NOT_SIGNED_IN = "sign in to WorkIt first: WorkIt Auto Apply downloads its Fill engine from WorkIt at each launch"


class EngineRefused(FillError, SetupError):
    """The engine from WorkIt could not be had or failed its checks: nothing ran, and the run stops."""


def app_version() -> str:
    return version("apply")


def download(client: "WorkIt | None" = None, public_key: str | None = None) -> str:
    """The engine bundle's text, checked: downloaded, decrypted and verified in memory. Raises EngineRefused with
    a sentence for the student, WorkIt not answering included."""
    from apply.workit import LoginExpired, NotLoggedIn, WorkIt, WorkItError

    key = PUBLIC_KEY if public_key is None else public_key
    if not key:
        raise EngineRefused(NO_KEY)
    client = client or WorkIt()
    try:
        sent = client.call("GET", f"/apply-app/engine?app_version={app_version()}")
        opened = client.call("POST", "/apply-app/engine-key", {"key_id": sent["key_id"], "expires_at": sent["expires_at"]})
    except (NotLoggedIn, LoginExpired):
        raise EngineRefused(NOT_SIGNED_IN) from None
    except WorkItError as refused:
        if refused.status == 404:
            raise EngineRefused("no Fill engine fits this version of WorkIt Auto Apply: update the app") from None
        raise EngineRefused(f"WorkIt did not send the Fill engine ({refused})") from None
    except (KeyError, TypeError):  # an answer of another shape: nothing in it is run
        raise EngineRefused(UNOPENED) from None
    try:
        plain = AESGCM(base64.b64decode(opened["key"])).decrypt(
            base64.b64decode(sent["nonce"]), base64.b64decode(sent["ciphertext"]), None)
    except (InvalidTag, ValueError, KeyError, TypeError):
        raise EngineRefused(UNOPENED) from None
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key)).verify(base64.b64decode(sent["signature"]), plain)
    except (InvalidSignature, ValueError, KeyError, TypeError):
        raise EngineRefused(BAD_SIGNATURE) from None
    if hashlib.sha256(plain).hexdigest() != sent.get("sha256"):
        raise EngineRefused(BAD_SIGNATURE)
    return plain.decode()
