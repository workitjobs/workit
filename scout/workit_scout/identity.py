"""
Identity-data removal: the one function that strips a student's identity data
from text before any model sees it. See ../CLAUDE.md, "Identity data never
reaches a model".
"""

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# A path after a host, ending before any trailing punctuation and before a
# "<": a link never holds one, and in "<url>...</url>" it starts the tag.
_TAIL = r"""(?:[^\s<]*[^\s<.,;:!?)\]'"])?"""
_PATH = rf"(?:/{_TAIL})?"
# The last label starts with a letter (".com", ".io"), so a number with a
# slash ("GPA: 3.81/4.00", "1.5/2 days") is never a host.
_HOST = r"[\w-]+(?:\.[\w-]+)*\.[A-Za-z][\w-]*"
# A scheme or "www." marks a link; a bare host counts only with a path
# ("github.com/jd"), so tool names such as Node.js and ASP.NET survive.
_URL = re.compile(
    rf"""https?://[^\s<]*[^\s<.,;:!?)\]'"]|(?<![\w@.])www\.{_HOST}{_PATH}"""
    rf"|(?<![\w@./-]){_HOST}/{_TAIL}"
)
# Digit groups joined by at most one space, dot or dash, with an optional
# country code; only a run of 10 to 15 digits counts, so dates, years,
# percentages and counts in a bullet survive.
_GROUP = r"(?:\(\d{1,4}\)|\d{1,4})"
_PHONE = re.compile(
    rf"(?<![\w+])(?:\+\d{{1,3}}[\s.-]?)?{_GROUP}(?:[\s.-]?{_GROUP}){{1,5}}(?!\w)"
)


# What `remove_identity` puts in place of identity data. A model that saw
# de-identified text can echo one back; a caller that saves or shows model
# text checks it with `placeholders_in` first, since nothing maps a
# placeholder back to its value.
PLACEHOLDERS = ("[name]", "[email]", "[phone]", "[link]")


def placeholders_in(text: str) -> list[str]:
    """The placeholders `text` holds, each once, in PLACEHOLDERS order."""
    return [p for p in PLACEHOLDERS if p in text]


# What takes a found value's place: its kind ("name", "email", "phone",
# "link") and the value as written in, its replacement out.
Put = Callable[[str, str], str]


def _plain(kind: str, value: str) -> str:
    return f"[{kind}]"


def _literal(text: str, value: str | None, kind: str, put: Put) -> str:
    if not value or not value.strip():
        return text
    return re.sub(re.escape(value.strip()), lambda m: put(kind, m[0]), text, flags=re.IGNORECASE)


def _profile_link(text: str, link: str, put: Put) -> str:
    core = re.sub(r"^(?:https?://)?(?:www\.)?", "", link.strip(), flags=re.IGNORECASE)
    core = core.rstrip("/")
    if not core:
        return text
    found = rf"(?:https?://)?(?:www\.)?{re.escape(core)}{_PATH}(?![\w-])"
    return re.sub(found, lambda m: put("link", m[0]), text, flags=re.IGNORECASE)


def _profile_phone(text: str, phone: str | None, put: Put) -> str:
    # The profile's number in any formatting: its last ten digits with any
    # separators between them, plus whatever country code precedes them.
    digits = re.sub(r"\D", "", phone or "")[-10:]
    if len(digits) < 7:
        return text
    between = r"[\s().-]*"
    found = rf"(?:\+\d{{1,3}}{between})?\(?" + between.join(digits)
    return re.sub(rf"(?<![\w+]){found}(?!\d)", lambda m: put("phone", m[0]), text)


def _removed(
    text: str,
    put: Put,
    *,
    name: str | None,
    email: str | None,
    phone: str | None,
    links: Iterable[str | None],
    any_link: bool = True,
) -> str:
    # The profile's own fields first, then any email, URL or phone by
    # pattern, the name last so a name inside an email or a link cannot
    # break that match. Without `any_link`, only the profile's own links go.
    text = _literal(text, email, "email", put)
    text = _EMAIL.sub(lambda m: put("email", m[0]), text)
    for link in links:
        text = _profile_link(text, link or "", put)
    if any_link:
        text = _URL.sub(lambda m: put("link", m[0]), text)
    text = _profile_phone(text, phone, put)
    text = _PHONE.sub(
        lambda m: put("phone", m[0]) if 10 <= sum(c.isdigit() for c in m[0]) <= 15 else m[0], text
    )
    if name:
        parts = sorted({name.strip(), *name.split()}, key=len, reverse=True)
        words = "|".join(re.escape(p) for p in parts if len(p) > 1)
        if words:
            text = re.sub(
                rf"(?<!\w)(?:{words})(?!\w)", lambda m: put("name", m[0]), text, flags=re.IGNORECASE
            )
    return text


def remove_identity(
    text: str,
    *,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    links: Iterable[str | None] = (),
) -> str:
    """
    Return `text` with identity data replaced by `[name]`, `[email]`, `[phone]`
    and `[link]`. The profile's own fields are matched first, then any email,
    URL or phone by pattern, the name last so a name inside an email or a link
    cannot break that match. Each part of the name is replaced on its own, in
    any case, even where it is also a common word: privacy wins over wording.
    Nothing maps a placeholder back to its value, by design; `Masked` is the
    one exception.
    """
    return _removed(text, _plain, name=name, email=email, phone=phone, links=links)


@dataclass(frozen=True)
class Identity:
    """
    One student's identity fields, as the model seam needs them: `LLM` takes
    one on every call and runs every message through `remove`, so no caller
    can send a model text that skipped removal. An empty Identity still
    removes any email, URL or phone by pattern.
    """

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    links: Sequence[str | None] = ()

    def remove(self, text: str) -> str:
        return remove_identity(
            text, name=self.name, email=self.email, phone=self.phone, links=self.links
        )


class Masked:
    """
    Identity data behind placeholders that can be put back, for one model
    call whose answer must hold the real values: WorkIt Auto Apply's Model
    route (`LLM.complete_schema`), whose answers the desktop app types into
    forms. The map from placeholder to value lives in memory for that one
    call; it is never stored or logged. Each distinct value gets its own
    placeholder, the first of a kind `[email]`, then `[email2]`, `[email3]`,
    so two emails come back as the right two. A placeholder already in the
    text (the app's own) is never used, so putting back never touches it.
    Only the student's own links are hidden, never every link: the calls read
    employers' links (the job posting among a page's links), which say
    nothing about the student.
    """

    def __init__(self, identity: Identity, texts: Iterable[str]):
        self._identity = identity
        self._seen = "\n".join(texts)
        self._placeholders: dict[tuple[str, str], str] = {}
        self._values: dict[str, str] = {}

    def _put(self, kind: str, value: str) -> str:
        if (kind, value) not in self._placeholders:
            n = 1
            while (p := f"[{kind}]" if n == 1 else f"[{kind}{n}]") in self._seen or p in self._values:
                n += 1
            self._placeholders[kind, value] = p
            self._values[p] = value
        return self._placeholders[kind, value]

    def hide(self, text: str) -> str:
        i = self._identity
        return _removed(text, self._put, name=i.name, email=i.email, phone=i.phone, links=i.links, any_link=False)

    def put_back(self, text: str, escape: Callable[[str], str] = lambda value: value) -> str:
        """`text` with each placeholder this mask made replaced by its value,
        in one pass, so a value is never read again as a placeholder.
        `escape` writes a value as `text` needs it (as inside a JSON string)."""
        if not self._values:
            return text
        found = "|".join(re.escape(p) for p in self._values)
        return re.sub(found, lambda m: escape(self._values[m[0]]), text)
