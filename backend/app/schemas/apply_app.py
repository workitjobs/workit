"""WorkIt Auto Apply's Model route shapes (KAN-723, routers/apply_app.py).

A call is one of Apply's `ask`s by its kind: the server builds the prompt and
the schema from the call's data (app/apply_prompts/, D5), so no request
carries a prompt or a schema. The free-form call that did, with its schema
checks, went once every kind was built on the server (2026-11-14)."""

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AskCall(BaseModel):
    """One of Apply's calls by its kind (app/apply_prompts/): the server
    builds its prompt and schema from `data`, which the kind's own model
    checks."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}(?:\.[a-z][a-z0-9_]{0,39})?$")
    version: int = Field(default=1, ge=1, le=1000)
    data: dict[str, Any]


class Usage(BaseModel):
    """The student's model use today (UTC), in tokens, against the cap."""

    used: int
    cap: int
    resets_at: datetime.datetime


class ModelAnswer(BaseModel):
    answer: dict[str, Any]
    # Tokens this call spent, every provider tried included.
    tokens: int
    usage: Usage


class SignInStart(BaseModel):
    """The website's /app-sign-in page, for the app: the app's PKCE challenge
    (RFC 7636's S256, base64url with no padding, 43 characters)."""

    model_config = ConfigDict(extra="forbid")

    challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class SignInCode(BaseModel):
    """The one-time code the page gives to the app, and its seconds to live.
    `paste`: whether the page may show the code to copy. Only WorkIt's admins
    (WORKIT_ADMINS), whose Developer checkout macOS can't hand the app's
    link; a student's page opens the link and shows no code, so nobody can
    talk a student into sending one."""

    code: str
    expires_in: int
    paste: bool


class SessionTrade(BaseModel):
    """The app's code and the verifier its challenge was made from."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    verifier: str = Field(pattern=r"^[A-Za-z0-9._~-]{43,128}$")


class AppSession(BaseModel):
    """A Supabase session of the app's own: it refreshes it at Supabase Auth."""

    access_token: str
    refresh_token: str
    expires_at: int


class EngineDownload(BaseModel):
    """One download of the Fill engine (KAN-836, W7; app/services/engine_builds.py): the newest build that fits the
    app, encrypted with AES-GCM under a key made for this download alone. The app asks for that key with
    `key_id` and `expires_at` (POST /apply-app/engine-key), decrypts in memory, and checks `signature`, the
    Ed25519 signature of the plain bundle, with the public key compiled into it. Bytes are base64."""

    sha256: str
    signature: str
    key_id: str
    expires_at: int
    nonce: str
    ciphertext: str


class EngineKeyAsk(BaseModel):
    """The download whose key the app asks for, as GET /apply-app/engine answered it."""

    model_config = ConfigDict(extra="forbid")

    key_id: str = Field(pattern=r"^[A-Za-z0-9_-]{16,64}$")
    expires_at: int


class EngineKey(BaseModel):
    """The download's AES-256 key, base64."""

    key: str
