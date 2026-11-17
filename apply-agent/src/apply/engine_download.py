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
import time
from collections.abc import Callable
from importlib.metadata import version
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from apply.adapters import SetupError
from apply.model import FillError

if TYPE_CHECKING:
    from apply.workit import WorkIt

# The public half of WorkIt's engine-signing key (`publish_engine make-key`, made 2026-11-17), base64 of its 32
# bytes. Only builds its private half signed run; that half is the apply-engine environment's secret
# (.github/CLAUDE.md, "Publish the Fill engine"). A new key needs a new app: every installed app refuses its builds.
PUBLIC_KEY = "yeZhwmvme9x7H7Xi4zaS7ifioYXXzMTu3XaU2o35zrk="

NO_KEY = "this copy of WorkIt Auto Apply has no engine key, so it can't check the Fill engine"
BAD_SIGNATURE = ("the Fill engine from WorkIt failed its signature check, so it did not run. Someone may be "
                 "changing your connection to WorkIt: try another network, then update WorkIt Auto Apply")
UNOPENED = "the Fill engine from WorkIt could not be decrypted. Start the run again"
NOT_SIGNED_IN = "sign in to WorkIt first: WorkIt Auto Apply downloads its Fill engine from WorkIt at each launch"
NO_BUILD = "no Fill engine fits this version of WorkIt Auto Apply: update the app"
# A download that another try may get past (WorkIt not answering, a download that did not decrypt) is tried this
# many times, the waits between tries growing by WAIT seconds.
TRIES = 3
WAIT = 2.0


class EngineRefused(FillError, SetupError):
    """The engine from WorkIt could not be had or failed its checks: nothing ran, and the run stops. `lasting`: no
    later try in this process can change it (no engine key, a wrong signature), so Apply keeps it until it restarts;
    any other refusal is tried again at the next use."""

    def __init__(self, message: str, lasting: bool = False):
        super().__init__(message)
        self.lasting = lasting


class _Again(Exception):
    """One try failed in a way another try may get past."""


def app_version() -> str:
    return version("apply")


def download(client: "WorkIt | None" = None, public_key: str | None = None,
             sleep: Callable[[float], None] = time.sleep) -> str:
    """The engine bundle's text, checked: downloaded, decrypted and verified in memory, in up to TRIES tries. Raises
    EngineRefused with a sentence for the student."""
    from apply.workit import WorkIt

    key = PUBLIC_KEY if public_key is None else public_key
    if not key:
        raise EngineRefused(NO_KEY, lasting=True)
    client = client or WorkIt()
    for attempt in range(TRIES):
        try:
            return _once(client, key)
        except _Again as again:
            if attempt == TRIES - 1:
                raise EngineRefused(str(again)) from None
            sleep(WAIT * (attempt + 1))


def _once(client: "WorkIt", key: str) -> str:
    from apply.workit import LoginExpired, NotLoggedIn, WorkItError

    try:
        sent = client.call("GET", f"/apply-app/engine?app_version={app_version()}")
        opened = client.call("POST", "/apply-app/engine-key", {"key_id": sent["key_id"], "expires_at": sent["expires_at"]})
    except (NotLoggedIn, LoginExpired):
        raise EngineRefused(NOT_SIGNED_IN) from None
    except WorkItError as refused:
        if refused.status == 404:
            raise EngineRefused(NO_BUILD) from None
        raise _Again(f"WorkIt did not send the Fill engine ({refused}). Check your connection and start the run again") from None
    except (KeyError, TypeError):  # an answer of another shape: nothing in it is run
        raise _Again(UNOPENED) from None
    try:
        plain = AESGCM(base64.b64decode(opened["key"])).decrypt(
            base64.b64decode(sent["nonce"]), base64.b64decode(sent["ciphertext"]), None)
    except (InvalidTag, ValueError, KeyError, TypeError):
        raise _Again(UNOPENED) from None
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key)).verify(base64.b64decode(sent["signature"]), plain)
    except (InvalidSignature, ValueError, KeyError, TypeError):
        raise EngineRefused(BAD_SIGNATURE, lasting=True) from None
    return plain.decode()  # the signature holds for these exact bytes: no other check adds anything
