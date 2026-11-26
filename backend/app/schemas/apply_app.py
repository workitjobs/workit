"""WorkIt Auto Apply's Model route shapes (KAN-723, routers/apply_app.py).

A call is one of Apply's `ask`s by its kind: the server builds the prompt and
the schema from the call's data (app/apply_prompts/, D5), so no request
carries a prompt or a schema. The free-form call that did, with its schema
checks, went once every kind was built on the server (2026-11-14)."""

import datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


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


class UsageNow(Usage):
    """GET /apply-app/usage: today's use, and the version of the student's
    Answer bank (W11; 0 while they have none), which WorkIt Auto Apply reads
    before each Application: it reads the bank again only when this differs
    from the version it holds."""

    bank_version: int


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


class AppProfile(BaseModel):
    """GET /apply-app/profile: the Fill engine's profile and policies for the
    student, built from what WorkIt holds as the extension builds them
    (services/engine_profile.py), and where each file the profile names is
    read: `resume` with `uploaded_resume_id` or `built_resume_id`, and
    `transcript`, each with its `name`. `writing` is the Story bank
    (services/story_bank.py) and the voice (the style card), as Apply's
    essays read them."""

    profile: dict
    policies: dict
    files: dict
    writing: dict = {}


# A Needs you answer as WorkIt Auto Apply keeps it: the question as the form words it, and the answer ("" is a Skip).
AnsweredQuestion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
AnsweredText = Annotated[str, StringConstraints(max_length=20000)]


# A fact's dotted key in the engine profile ("identity.pronouns"): never a file's path, which only the Mac knows.
def _not_reserved(key: str) -> str:
    if key.split(".")[0] in ("files", "answered_questions"):
        raise ValueError("files and answered_questions are not facts")
    return key


FactKey = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+){0,4}$"), AfterValidator(_not_reserved)]


class AnsweredChange(BaseModel):
    """PATCH /apply-app/profile: what the student answered in WorkIt Auto
    Apply's Needs you, at most 100 of each: answers to questions no fact
    answered (the profile's `answered_questions`), and facts the Fill engine
    read from an answer (`remember`), by dotted key."""

    model_config = ConfigDict(extra="forbid")

    answered: dict[AnsweredQuestion, AnsweredText | list[AnsweredText]] = Field(default={}, max_length=100)
    facts: dict[FactKey, AnsweredText | list[AnsweredText] | bool | int | float] = Field(default={}, max_length=100)


class ProfileUpload(BaseModel):
    """POST /apply-app/profile/upload: a Developer checkout's own files
    (`apply upload`): its applicant-profile.yaml as data, and its
    story-bank.md and voice.md as text."""

    model_config = ConfigDict(extra="forbid")

    profile: dict = {}
    story_bank: str = Field(default="", max_length=200_000)
    voice: str = Field(default="", max_length=20_000)


class UploadTaken(BaseModel):
    """What an upload put in: only what WorkIt lacked."""

    facts: int
    answered: int
    samples: int
    style_card: bool
