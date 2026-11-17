"""
Score the resume reading against hand-checked answer keys (KAN-900). By hand,
never in CI.

    uv run python -m app.scripts.reading_score                    the made-up set
    uv run python -m app.scripts.reading_score --set reading_set_private
    uv run python -m app.scripts.reading_score --misses           every miss, listed
    uv run python -m app.scripts.reading_score --offline          saved AI replies only
    uv run python -m app.scripts.reading_score --json out.json    the whole result, for a diff

Each resume is read the way an upload reads it (`text_extraction.extract`,
then `bank_import.read_resume`), and three readings are scored field by
field against its answer key:

- **the rule-based parser** alone (`bank_import.read`),
- **the AI reading** alone: the model's entries after the check against the
  text (`model_drafts`), with the tools split out of titles, before the
  rule-based parser fills anything,
- **the combined reading**: what `read_resume` returns, which is what an
  upload saves. When the model fails, it is the rule-based parser's.

**A score is the share of the answer key's fields the reading got right.**
One field is one unit: a title, an organization, a location, a start, an
end, a degree, a major, a GPA, a link, an issuer, an award's date, and each
bullet, course and tool. An entry the reading lacks loses all its units. A
scalar field the key leaves out must be empty in the reading ("Intern
Brooklyn, NY" must not become a location). Text is compared after folding
case, spaces, dashes and quotes, and a bullet's last period; nothing else is
forgiven ("B.S" is not "B.S."). Entries are paired by the words of their
title and organization, in any section, so a job read as a project is found
and loses its `section` unit. Skills are scored apart: only skills the
skills catalog knows can be saved, so only those count.

**The model's replies are saved** in `.reading_cache/` (git-ignored), keyed by
the prompt and the model, so a second run reads the same replies for free:
change the rule-based parser and run again, and only its part changes. A
new prompt or model asks the model again. `--fresh` asks again anyway.
The model is the one the `SCOUT_*` settings name, as for the API.

The answer key is `<name>.json` beside `<name>.pdf` or `<name>.docx`
(`app/utils/CLAUDE.md`, The reading score, has the format). The committed
set is made-up people, made by `app.scripts.make_reading_set`. Real resumes
go in the git-ignored `reading_set_private/` with keys written the same
way; never commit one: the repo is public.
"""

import argparse
import asyncio
import datetime
import hashlib
import json
import logging
import re
import statistics
import sys
import time
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values
from workit_scout.identity import Identity
from workit_scout.llm import LLM
from workit_scout.settings import Endpoint, ScoutSettings

from app.config import ENV_FILE
from app.schemas.bank import DraftEntry
from app.services import bank_import, skill_catalog
from app.services.text_extraction import extract

BACKEND = Path(__file__).resolve().parents[2]
DEFAULT_SET = BACKEND / "data" / "reading_set"
CACHE = BACKEND / ".reading_cache"
READERS = ("rule-based", "AI", "combined")

# The scalar fields each section's answer key is scored on, as the key names
# them; a field the key leaves out must be empty in the reading.
FIELDS = {
    "education": ("title", "location", "degree", "field_of_study", "gpa", "start", "end"),
    "experience": ("title", "organization", "location", "start", "end"),
    "leadership": ("title", "organization", "location", "start", "end"),
    "projects": ("title", "start", "end"),
    "awards": ("title", "organization", "date"),
    "certifications": ("title", "issuer"),
    "custom": ("title",),
}
# Fields scored only when the key gives them: the AI never sees a link, and
# a key that does not say whether a project has one says nothing.
OPTIONAL = ("link",)
LISTS = ("bullets", "coursework", "tools")


# --- Reading ----------------------------------------------------------------


class MeteredLLM(LLM):
    """The model seam as the API builds it, also keeping, for each call, the
    model that answered, the seconds it took, its tokens and the messages
    it sent, after the seam took identity data out."""

    def __init__(self, chain):
        super().__init__(chain)
        self.meter: list[dict] = []

    async def _complete_schema(self, client, endpoint, messages, name, schema, max_tokens=None):
        start = time.perf_counter()
        call = {"model": endpoint.model, "sent": [m["content"] for m in messages]}
        self.meter.append(call)
        try:
            text, spent = await super()._complete_schema(client, endpoint, messages, name, schema, max_tokens)
        except Exception as exc:
            call |= {"seconds": time.perf_counter() - start, "error": type(exc).__name__}
            raise
        call |= {"seconds": time.perf_counter() - start, "input_tokens": spent.input_tokens,
                 "output_tokens": spent.output_tokens}
        return text, spent


class CachedLLM:
    """The model, with each reply saved by its prompt. `read_resume` asks it
    through `complete_json` alone, so this stands in for an `LLM`. A saved
    reply keeps its call's time and tokens, so a run that reads it reports
    what the call cost when it was made."""

    def __init__(self, llm: MeteredLLM | None, models: str, *, fresh: bool, retries: int = 2, pause: float = 0):
        self.llm = llm
        self.models = models
        self.fresh = fresh
        self.retries = retries
        self.pause = pause
        self.last = None
        self.calls = 0
        self.meter: list[dict] = []

    async def complete_json(self, messages, schema, *, identity, **kwargs):
        body = json.dumps([self.models, list(messages), sorted(kwargs.items())], sort_keys=True, default=str)
        path = CACHE / f"{hashlib.sha256(body.encode()).hexdigest()[:24]}.json"
        if path.exists() and not self.fresh:
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.meter = saved["meter"]
            self.last = schema.model_validate(saved["reply"])
            return self.last
        if self.llm is None:
            raise RuntimeError("offline: no saved reply for this resume")
        if self.calls and self.pause:
            await asyncio.sleep(self.pause)
        self.calls += 1
        self.llm.meter = []
        # A provider's 503 or 429 says nothing about how well its model reads,
        # so a failed call is tried again; each failure stays in the meter,
        # and the report counts them.
        for attempt in range(self.retries + 1):
            try:
                reply = await self.llm.complete_json(messages, schema, identity=identity, **kwargs)
                break
            except Exception:
                if attempt == self.retries:
                    self.meter = self.llm.meter
                    raise
                await asyncio.sleep(5)
        self.meter = self.llm.meter
        CACHE.mkdir(exist_ok=True)
        path.write_text(json.dumps({"reply": reply.model_dump(mode="json"), "meter": self.meter}), encoding="utf-8")
        self.last = reply
        return reply


@dataclass
class Readings:
    text: str | None
    entries: dict[str, list[DraftEntry]]
    skills: dict[str, list[str]]
    ai_failed: bool
    seconds: dict[str, float] = field(default_factory=dict)
    meter: list[dict] = field(default_factory=list)


async def read_three(raw_text: str | None, llm: CachedLLM, identity: Identity) -> Readings:
    start = time.perf_counter()
    rules_entries, rules_skills = bank_import.read(raw_text)
    rules_seconds = time.perf_counter() - start
    llm.last = None
    llm.meter = []
    combined = await bank_import.read_resume(raw_text, llm, identity)
    ai_entries: list[DraftEntry] = []
    ai_skills: list[str] = []
    if llm.last is not None and raw_text:
        reading = llm.last
        text = unicodedata.normalize("NFKC", bank_import.fix_symbols(raw_text))
        drafts = bank_import.model_drafts(bank_import.with_own_wording(reading, rules_entries), text)
        drafts, tools = bank_import.with_tools_split(drafts)
        ai_entries = bank_import.tidy_drafts(drafts)
        found = bank_import.model_skills(reading, text) + [(t, None) for t in tools]
        ai_skills = [name for name, _ in bank_import.skill_pairs(found)]
    return Readings(
        raw_text,
        {"rule-based": rules_entries, "AI": ai_entries, "combined": combined.entries},
        {
            "rule-based": [name for name, _ in rules_skills],
            "AI": ai_skills,
            "combined": [name for name, _ in combined.skills],
        },
        ai_failed=combined.read_by != "model",
        # The answered call's time, as an upload without the retries waits;
        # when none answered, every attempt's.
        seconds={"rule-based": rules_seconds,
                 "AI": sum(c["seconds"] for c in llm.meter if "error" not in c)
                 or sum(c.get("seconds", 0) for c in llm.meter)},
        meter=llm.meter,
    )


# --- Comparing --------------------------------------------------------------

_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_QUOTES = {ord("‘"): "'", ord("’"): "'", ord("“"): '"', ord("”"): '"'}


def fold(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value)).translate(_DASHES).translate(_QUOTES)
    return " ".join(text.split()).casefold()


def fold_line(value: object) -> str:
    return fold(value).rstrip(".").strip()


def _words(*values: object) -> set[str]:
    return {w for v in values if v for w in re.findall(r"[a-z0-9]+", fold(v))}


def _month(value: datetime.date | None) -> str | None:
    return value.strftime("%Y-%m") if value else None


def got_value(entry: DraftEntry, name: str) -> object:
    """The reading's value for an answer key field, in the key's terms."""
    years = set(entry.year_only)
    if name == "start":
        return _date(entry.start_month, "start_month" in years)
    if name == "end":
        if entry.end_kind and entry.end_kind.value == "present":
            return "present"
        end = _date(entry.end_month, "end_month" in years)
        return f"expected {end}" if end and entry.end_kind and entry.end_kind.value == "expected" else end
    if name == "date":
        return _date(entry.award_date, "award_date" in years)
    if name == "organization" and entry.section.value == "certifications":
        return entry.issuer
    if name == "gpa":
        return float(entry.gpa) if entry.gpa is not None else None
    return getattr(entry, name)


def _date(value: datetime.date | None, year_only: bool) -> str | None:
    if value is None:
        return None
    return str(value.year) if year_only else _month(value)


def want_value(key: dict, name: str) -> object:
    if name == "end" and key.get("expected") and key.get("end"):
        return f"expected {key['end']}"
    return key.get(name)


def same(name: str, want: object, got: object) -> bool:
    if want in (None, "", []) or got in (None, "", []):
        return want in (None, "", []) and got in (None, "", [])
    if name == "gpa":
        return abs(float(want) - float(got)) < 0.005
    if name == "link":
        return fold(want).removeprefix("https://").rstrip("/") == fold(got).removeprefix("https://").rstrip("/")
    return fold(want) == fold(got)


def pair(keys: list[dict], got: list[DraftEntry]) -> dict[int, int]:
    """Each key entry's reading entry, by the words their titles and
    organizations share, the closest pairs first."""
    scores = []
    for i, key in enumerate(keys):
        want = _words(key.get("title"), key.get("organization"))
        for j, entry in enumerate(got):
            have = _words(entry.title, entry.organization, entry.issuer)
            if not want or not have:
                continue
            score = len(want & have) / len(want | have)
            if entry.section.value == key["section"]:
                score += 0.2
            if score >= 0.35:
                scores.append((score, i, j))
    pairs: dict[int, int] = {}
    taken: set[int] = set()
    for _, i, j in sorted(scores, reverse=True):
        if i not in pairs and j not in taken:
            pairs[i] = j
            taken.add(j)
    return pairs


@dataclass
class Score:
    right: int = 0
    total: int = 0
    entries_found: int = 0
    entries: int = 0
    extra_entries: int = 0
    extra_lines: int = 0
    skills_found: int = 0
    skills: int = 0
    extra_skills: int = 0
    by_field: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    misses: list[str] = field(default_factory=list)

    def unit(self, name: str, ok: bool, miss: str) -> None:
        self.total += 1
        self.right += ok
        self.by_field[name][1] += 1
        self.by_field[name][0] += ok
        if not ok:
            self.misses.append(miss)

    def add(self, other: "Score") -> None:
        for name in ("right", "total", "entries_found", "entries", "extra_entries", "extra_lines",
                     "skills_found", "skills", "extra_skills"):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        for name, (r, t) in other.by_field.items():
            self.by_field[name][0] += r
            self.by_field[name][1] += t
        self.misses += other.misses


def _label(key: dict) -> str:
    org = key.get("organization") or key.get("issuer")
    return f"{key['section']}: {key['title']}" + (f", {org}" if org else "")


def score(answer: dict, entries: list[DraftEntry], skills: list[str]) -> Score:
    s = Score()
    keys = answer["entries"]
    pairs = pair(keys, entries)
    s.entries = len(keys)
    s.entries_found = len(pairs)
    s.extra_entries = len(entries) - len(pairs)
    for i, key in enumerate(keys):
        label = _label(key)
        entry = entries[pairs[i]] if i in pairs else None
        names = FIELDS[key["section"]] + tuple(n for n in OPTIONAL if n in key)
        if entry is None:
            for name in ("section", *names):
                if name == "section" or key.get(name) not in (None, "", []):
                    s.unit(name, False, f"{label}: not found")
            for name in LISTS:
                for item in key.get(name, []):
                    s.unit(name, False, f"{label}: not found")
            continue
        s.unit("section", entry.section.value == key["section"],
               f"{label}: section {entry.section.value!r}")
        for name in names:
            want, got = want_value(key, name), got_value(entry, name)
            ok = same(name, want, got)
            # One date alone ("2023") read as a start and an end of it says
            # the same thing.
            if name == "start" and not ok and want is None and key.get("end") and got == got_value(entry, "end"):
                ok = same("end", key["end"], got)
            s.unit(name, ok, f"{label}: {name} {got!r}, not {want!r}")
        for name in LISTS:
            have = [fold_line(x) for x in getattr(entry, name)]
            wanted = [fold_line(x) for x in key.get(name, [])]
            for item in key.get(name, []):
                s.unit(name, fold_line(item) in have, f"{label}: {name[:-1] if name != 'coursework' else 'course'} missing: {item!r}")
            extra = [x for x in have if x not in wanted]
            if name == "bullets":
                s.extra_lines += len(extra)
                s.misses += [f"{label}: extra line: {x!r}" for x in extra]
    for j, entry in enumerate(entries):
        if j not in pairs.values():
            s.misses.append(f"extra entry: {entry.section.value}: {entry.title}"
                            + (f", {entry.organization}" if entry.organization else ""))

    known = {skill_catalog.canonical(x): x for x in answer.get("skills", []) if skill_catalog.is_skill(x)}
    have = {skill_catalog.canonical(x) or fold(x) for x in skills}
    s.skills = len(known)
    s.skills_found = len(known.keys() & have)
    s.extra_skills = len(have - known.keys())
    s.misses += [f"skill missing: {known[k]}" for k in known.keys() - have]
    s.misses += [f"extra skill: {x}" for x in skills if (skill_catalog.canonical(x) or fold(x)) not in known]
    return s


# --- Running ----------------------------------------------------------------


def _resume_file(key_path: Path, answer: dict) -> Path:
    path = key_path.parent / answer["file"]
    if not path.exists():
        raise SystemExit(f"{key_path.name}: {answer['file']} is not beside it")
    return path


async def read_file(path: Path) -> str | None:
    data = path.read_bytes()
    if path.suffix == ".txt":
        return data.decode("utf-8")
    return await extract(data, path.suffix)


def _pct(right: int, total: int) -> str:
    return f"{100 * right / total:5.1f}%" if total else "    - "


# Chains to compare by name (`--chain`), each with the key the root .env
# holds for it. Unnamed, the chain is the SCOUT_* settings', as the API's.
_GEMINI = ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-3.5-flash-lite", "minimal")
_GROQ = "https://api.groq.com/openai/v1"
PRESETS = {
    "gemini": [_GEMINI],
    "gpt-oss-20b": [(_GROQ, "openai/gpt-oss-20b", "low")],
    "gpt-oss-120b": [(_GROQ, "openai/gpt-oss-120b", None)],
}


def chain_of(name: str | None, settings: ScoutSettings) -> list[Endpoint]:
    if not name:
        return settings.chain()
    env = dotenv_values(ENV_FILE)
    out = []
    for item in name.split(","):
        for base, model, effort in PRESETS[item]:
            key = env.get("GROQ_API_KEY") if base == _GROQ else (
                settings.api_key if settings.base_url == base else env.get("GEMINI_API_KEY"))
            if not key:
                raise SystemExit(f"No API key for {model} in the root .env")
            out.append(Endpoint(base, model, key, effort))
    return out


def show(stem: str, raw_text: str | None, readings: Readings) -> None:
    """One resume through each step: the text the file gave, what the model
    was sent, what it answered, and each reading's entries."""
    print(f"\n===== {stem}: the text extraction gave =====\n{raw_text}")
    for call in readings.meter:
        print(f"\n===== Sent to {call['model']} (the resume part; the instructions come first) =====")
        print(call["sent"][-1])
    for reader in READERS:
        print(f"\n===== {reader} reading =====")
        for e in readings.entries[reader]:
            print("  " + e.model_dump_json(exclude_defaults=True, exclude={"year_only"}))
        print(f"  skills: {', '.join(readings.skills[reader])}")


async def main(args: argparse.Namespace) -> int:
    settings = ScoutSettings(_env_file=ENV_FILE)
    chain = chain_of(args.chain, settings)
    models = ", ".join(e.model for e in chain)
    llm = CachedLLM(None if args.offline else MeteredLLM(chain), models, fresh=args.fresh, pause=args.pause)

    keys = sorted(p for folder in args.set for p in Path(folder).glob("*.json"))
    if args.show:
        keys = [k for k in keys if k.stem.startswith(args.show)]
    if not keys:
        print(f"No answer keys in {', '.join(map(str, args.set))}")
        return 1
    total = {r: Score() for r in READERS}
    rows = []
    failed = []
    times: dict[str, list[float]] = defaultdict(list)
    tokens: dict[str, list[int]] = defaultdict(list)
    errors: dict[str, int] = defaultdict(int)
    for key_path in keys:
        answer = json.loads(key_path.read_text(encoding="utf-8"))
        person = answer.get("person", {})
        identity = Identity(person.get("name"), person.get("email"), person.get("phone"), person.get("links", ()))
        start = time.perf_counter()
        raw_text = await read_file(_resume_file(key_path, answer))
        extract_seconds = time.perf_counter() - start
        readings = await read_three(raw_text, llm, identity)
        if args.show:
            show(key_path.stem, raw_text, readings)
        if readings.ai_failed:
            why = ", ".join(c["error"] for c in readings.meter if "error" in c) or "no entry the text backs"
            failed.append(f"{key_path.stem} ({why})")
        times["text extraction"].append(extract_seconds)
        times["rule-based parser"].append(readings.seconds["rule-based"])
        times["AI call"].append(readings.seconds["AI"])
        times["upload, in all"].append(extract_seconds + readings.seconds["rule-based"] + readings.seconds["AI"])
        for call in readings.meter:
            if "error" in call:
                errors[call["error"]] += 1
        answered = [c for c in readings.meter if "input_tokens" in c]
        if answered:
            tokens["sent"].append(sum(c["input_tokens"] for c in answered))
            tokens["answered"].append(sum(c["output_tokens"] for c in answered))
            tokens["in all"].append(tokens["sent"][-1] + tokens["answered"][-1])
        row = {"resume": key_path.stem, "layout": answer.get("layout", "")}
        for reader in READERS:
            s = score(answer, readings.entries[reader], readings.skills[reader])
            s.misses = [f"{key_path.stem} [{reader}] {m}" for m in s.misses]
            total[reader].add(s)
            row[reader] = s
        rows.append(row)

    print(f"\nResume reading score: {len(keys)} resumes, model {models or 'none'}"
          f"{' (saved replies only)' if args.offline else ''}; {llm.calls} new model calls\n")
    print(f"{'':12}{'Fields right':>22}{'Entries found':>17}{'Extra entries':>15}{'Extra lines':>13}"
          f"{'Skills found':>15}{'Extra skills':>14}")
    for reader in READERS:
        s = total[reader]
        print(f"{reader:12}{s.right:>8}/{s.total:<5} {_pct(s.right, s.total)}{s.entries_found:>9}/{s.entries:<5}"
              f"{s.extra_entries:>11}{s.extra_lines:>13}{s.skills_found:>9}/{s.skills:<5}{s.extra_skills:>11}")
    if failed:
        print(f"\nThe AI reading failed on {len(failed)} (scored as empty; the combined reading is the "
              f"rule-based one there): {', '.join(failed)}")
    if errors:
        print(f"\nThe provider failed {sum(errors.values())} calls, each tried again "
              f"(an upload would have saved the rule-based reading): "
              + ", ".join(f"{n} {name}" for name, n in errors.items()))

    print(f"\n{'Time, seconds':24}{'median':>10}{'slowest':>10}")
    for name, values in times.items():
        print(f"  {name:22}{statistics.median(values):>10.2f}{max(values):>10.2f}")
    print("  (A saved reply keeps the time its call took. The upload also writes to the database.)")
    if tokens:
        print(f"\n{'Tokens per AI reading':24}{'median':>10}{'largest':>10}{'all resumes':>13}")
        for name, values in tokens.items():
            print(f"  {name:22}{statistics.median(values):>10.0f}{max(values):>10}{sum(values):>13}")

    print(f"\n{'By field':24}" + "".join(f"{r:>12}" for r in READERS) + f"{'units':>8}")
    for name in sorted(total["combined"].by_field, key=lambda n: -total["combined"].by_field[n][1]):
        cells = "".join(f"{_pct(*total[r].by_field[name]):>12}" for r in READERS)
        print(f"  {name:22}{cells}{total['combined'].by_field[name][1]:>8}")

    print(f"\n{'By resume':36}" + "".join(f"{r:>12}" for r in READERS))
    for row in rows:
        cells = "".join(f"{_pct(row[r].right, row[r].total):>12}" for r in READERS)
        print(f"  {row['resume'][:22]:22}{row['layout'][:12]:12}{cells}")

    if args.misses:
        for reader in READERS:
            print(f"\nMisses, {reader}:")
            for miss in total[reader].misses:
                print(f"  {miss}")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "models": models,
            "totals": {r: _plain(total[r]) for r in READERS},
            "resumes": [{"resume": row["resume"], "layout": row["layout"],
                         **{r: _plain(row[r]) for r in READERS}} for row in rows],
            "ai_failed": failed,
        }, indent=1), encoding="utf-8")
    return 0


def _plain(s: Score) -> dict:
    return {
        "right": s.right, "total": s.total, "entries_found": s.entries_found, "entries": s.entries,
        "extra_entries": s.extra_entries, "extra_lines": s.extra_lines, "skills_found": s.skills_found,
        "skills": s.skills, "extra_skills": s.extra_skills,
        "by_field": {k: list(v) for k, v in s.by_field.items()}, "misses": s.misses,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--set", action="append", help="a folder of resumes and answer keys (repeatable)")
    parser.add_argument("--misses", action="store_true", help="list every miss")
    parser.add_argument("--offline", action="store_true", help="use saved AI replies only; ask no model")
    parser.add_argument("--fresh", action="store_true", help="ask the model again, over the saved replies")
    parser.add_argument("--json", help="write the whole result to this file")
    parser.add_argument("--chain", help=f"read with these models in order, not SCOUT_*'s: {', '.join(PRESETS)}")
    parser.add_argument("--show", help="print each step for the resumes whose name starts with this")
    parser.add_argument("--pause", type=float, default=0,
                        help="seconds to wait between model calls (Groq's free tier allows a few readings a minute)")
    parsed = parser.parse_args()
    parsed.set = parsed.set or [DEFAULT_SET]
    # The seam logs why each endpoint failed (an HTTP 503, a reply in the
    # wrong shape); the API's logs show the same lines.
    logging.basicConfig(level=logging.WARNING, format="  %(message)s")
    sys.exit(asyncio.run(main(parsed)))
