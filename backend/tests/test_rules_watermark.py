"""
The per-account watermark on a served Rules table (KAN-756,
app/services/rules_watermark.py): a marked table fills exactly as the
engine's own, and a leaked one names the account it was served to.

The tests on the engine's real table need the fill-engine submodule (its
dist/rules-table.json, and node for the engine's round trip); they skip
without it. CI checks it out when FILL_ENGINE_TOKEN is set.
"""

import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from app.config import get_settings
from app.services import rules_table
from app.services.rules_watermark import (
    _is_selector_list,
    _parts,
    _regex_places,
    _spell,
    fingerprint,
    score,
    trace,
    watermark,
)

ENGINE = Path(__file__).parents[2] / "autofiller_extension" / "fill-engine"
needs_engine = pytest.mark.skipif(
    not get_settings().rules_table_path.is_file(),
    reason="no fill-engine submodule (git submodule update --init autofiller_extension/fill-engine)",
)

# A table in the engine's shape, small enough to read.
TABLE = {
    "version": 2,
    "answers": [
        {"pattern": {"source": "^first name$"}, "value": "fact", "args": ["identity.legal_first_name"]},
        {"pattern": {"source": r"available to (begin|start)\b.{0,60}\bbefore [a-z]+ \d{4}"}, "value": "fact", "args": ["x"]},
        {"pattern": {"source": r"[ \d]+\s+years? of [^ ]+ experience", "flags": "u"}, "value": "answer", "args": ["5"]},
        {"pattern": {"source": "only in a v class [ ]", "flags": "v"}, "value": "consent"},
    ],
    "systems": {
        "tiktok": {
            "strings": {
                "ITEM": ".atsx-form-item, .ud-formily-item",
                "LABEL": ".atsx-form-item-label label, .atsx-form-item-label, .ud-formily-item-label-content, .ud-formily-item-label",
                "OPTION": "li.atsx-select-dropdown-menu-item, .ud__select__list__item",
                "SUBMIT": '[data-test="applyResumeBtn"]',
            },
        },
        "workday": {
            "strings": {
                "SELECT_ONE": "Select One",
                "INTRO": "h3, h4, h5, [data-automation-id=richText], p",
                "REVIEW": "Review",
            },
            "patterns": {"SENDS": {"source": r"\b(submit|send|apply|finish|complete|confirm)\b", "flags": "i"}},
        },
    },
}


def _same_meaning(original: dict, marked: dict) -> None:
    """
    Everything but the watermark's choices is as it was: the same rules, names, values, flags and list
    parts, and each pattern the same regex once its places are spelled plain (` `, `\\d`, `\\s+`, `\\s*`,
    each of which is the same regex as `[ ]`, `[0-9]`, `\\s{1,}`, `\\s{0,}` outside a class).
    """
    plain = lambda p: (_spell(_regex_places(p["source"])), p.get("flags"))
    assert marked.keys() == original.keys()
    assert [{**r, "pattern": None} for r in marked["answers"]] == [{**r, "pattern": None} for r in original["answers"]]
    assert [plain(r["pattern"]) for r in marked["answers"]] == [plain(r["pattern"]) for r in original["answers"]]
    for site, data in original["systems"].items():
        got = marked["systems"][site]
        assert {n: plain(p) for n, p in got.get("patterns", {}).items()} == {n: plain(p) for n, p in data.get("patterns", {}).items()}
        for name, value in data.get("strings", {}).items():
            if _is_selector_list(value):
                parts = [p for p in _parts(got["strings"][name]) if not re.fullmatch(r"\[data-v-[0-9a-f]{10}\]", p)]
                assert sorted(parts) == sorted(_parts(value)), name
                assert len(_parts(got["strings"][name])) - len(parts) <= 1, name
            else:
                assert got["strings"][name] == value, name


def test_the_same_account_always_gets_the_same_copy_and_another_a_different_one():
    a, b = uuid.uuid4(), uuid.uuid4()
    assert watermark(TABLE, a) == watermark(TABLE, a)
    assert watermark(TABLE, a) != watermark(TABLE, b)
    assert watermark(watermark(TABLE, b), a) == watermark(TABLE, a)  # re-marking reads through any earlier marks


def test_a_marked_table_keeps_every_rule_name_and_value_and_only_respells_or_reorders():
    original = json.loads(json.dumps(TABLE))
    for _ in range(20):
        marked = watermark(TABLE, uuid.uuid4())
        _same_meaning(TABLE, marked)
    assert TABLE == original  # the served table is a copy: the engine's stays as it was


def test_wordings_and_single_selectors_and_v_flag_patterns_are_never_changed():
    for _ in range(20):
        marked = watermark(TABLE, uuid.uuid4())
        assert marked["systems"]["workday"]["strings"]["SELECT_ONE"] == "Select One"
        assert marked["systems"]["workday"]["strings"]["REVIEW"] == "Review"
        assert marked["systems"]["tiktok"]["strings"]["SUBMIT"] == '[data-test="applyResumeBtn"]'
        assert marked["answers"][3]["pattern"] == TABLE["answers"][3]["pattern"]
        # A character class keeps its own spelling: [ \d] is not [[ ][0-9]].
        assert marked["answers"][2]["pattern"]["source"].startswith(r"[ \d]+")


def test_regex_classes_and_literal_braces_keep_their_spelling():
    for source in (r"a[]b c", r"a[^] c", "a{b [c d]} e", r"x{2} y{0,3}"):
        table = {"version": 2, "answers": [{"pattern": {"source": source}, "value": "consent"}]}
        for _ in range(10):
            marked = watermark(table, uuid.uuid4())["answers"][0]["pattern"]["source"]
            plain = marked.replace("[ ]", " ")
            # Only spaces outside every class change: [c d]'s space never does.
            assert plain == source or plain.replace("[0-9]", r"\d") == source, marked
            assert "[c[ ]d]" not in marked


def test_wordings_with_full_stops_or_colons_are_not_selector_lists():
    for wording in ("Mr., Mrs.", "Note: one, Note: two", "Yes, No"):
        assert not _is_selector_list(wording), wording
    for selector in (".a, .b", "h3, p", "spl-input, spl-textarea", "a > b, [x=y]", "li:not(.x), :focus"):
        assert _is_selector_list(selector), selector


def test_each_site_gets_one_decoy_naming_the_account():
    account = uuid.uuid4()
    marked = watermark(TABLE, account)
    for site in ("tiktok", "workday"):
        decoys = [p for s in marked["systems"][site]["strings"].values() for p in _parts(s) if p.startswith("[data-v-")]
        assert decoys == [f"[data-v-{fingerprint(account)}]"]


def test_recovers_the_account_a_leaked_table_was_served_to():
    accounts = [uuid.uuid4() for _ in range(50)]
    leaked = watermark(TABLE, accounts[17])
    found = trace(leaked, accounts)
    assert found is not None and found.account_id == accounts[17] and found.decoy


def test_recovers_it_from_the_regex_spellings_alone_once_the_decoy_and_order_are_stripped():
    table = {"version": 2, "answers": [
        {"pattern": {"source": f"question {i} about your work history and the start date you can do"}, "value": "consent"}
        for i in range(10)
    ]}
    accounts = [uuid.uuid4() for _ in range(50)]
    leaked = watermark(table, accounts[3])
    found = trace(leaked, accounts)
    assert found is not None and found.account_id == accounts[3] and not found.decoy and found.share == 1.0
    assert trace(table, accounts) is None  # the unmarked table names no one
    assert trace(leaked, accounts[:3] + accounts[4:]) is None  # nor a copy served to someone outside the candidates


@needs_engine
def test_every_site_of_the_engines_table_carries_enough_marks_to_name_its_account():
    a, b = uuid.uuid4(), uuid.uuid4()
    for site in rules_table.sites():
        marked = watermark(rules_table.for_site(site), a)
        _same_meaning(rules_table.for_site(site), marked)
        mine, theirs = score(marked, a), score(marked, b)
        assert mine.share == 1.0 and mine.marks > 500, site
        assert 0.4 < theirs.share < 0.6 and not theirs.decoy, site
        assert trace(marked, [b, a]).account_id == a


@needs_engine
@pytest.mark.skipif(shutil.which("node") is None or not (ENGINE / "test" / "fixtures" / "planner").is_dir(), reason="needs node and the engine's fixtures")
def test_the_engine_plans_the_same_from_every_sites_marked_table(tmp_path):
    """The engine's own round trip on the built engine: loadRules takes each marked table, every pattern
    answers every saved label the same, and every saved research form plans the same. Saved labels reach
    only some rules; _same_meaning's plain spelling covers the rest."""
    tables = [watermark(rules_table.for_site(site), uuid.uuid4()) for site in sorted(rules_table.sites())]
    (tmp_path / "tables.json").write_text(json.dumps(tables))
    run = subprocess.run(
        ["node", str(Path(__file__).with_name("rules_round_trip.mjs")), str(ENGINE), str(tmp_path / "tables.json")],
        capture_output=True, text=True, timeout=120, check=False,
    )
    assert run.stdout.strip() == "ok", run.stdout + run.stderr


@needs_engine
@pytest.mark.skipif(not (ENGINE / "src").is_dir(), reason="needs the engine's source")
def test_the_engine_uses_every_marked_list_only_as_whole_selectors():
    """
    Reordering a list or adding a part to it is harmless only where the engine hands the whole string to
    a selector function, or puts it whole into a larger list. `${SEL.ITEM} input` would turn a list into
    another selector, and `.split(",")` or `.includes(SEL.X)` would read it as text. Each use of a list
    the watermark touches is one of: the selector argument of querySelector(All), closest, matches, or
    the engine's own $$, deep, first and Lever's shown (each a querySelectorAll); or a template part `${SEL.X}` between the
    template's ends and commas. Comments are left out.
    """
    allowed = re.compile(
        r"""(?:\b(?:querySelector|querySelectorAll|closest|matches)(?:<[^>]*>)?\(\s*|\$\$(?:<[^>]*>)?\(\s*|\b(?:deep|first)(?:<[^>]*>)?\([^,()]+,\s*|\bshown\(\s*)SEL\.(\w+)\s*\)"""
        r"""|(?:`|,\s*)\$\{SEL\.(\w+)\}\s*(?=`|,)"""
    )
    for site in rules_table.sites():
        lists = {n for n, v in (rules_table.bundled()["systems"][site].get("strings") or {}).items() if _is_selector_list(v)}
        for file in (ENGINE / "src").glob("*.ts"):
            code = re.sub(r"//[^\n]*", lambda m: " " * len(m.group()), file.read_text(encoding="utf-8"))
            if f'siteStrings("{site}")' not in code:
                continue
            uses = {m.start() for m in re.finditer(r"SEL\.(\w+)", code) if m.group(1) in lists}
            ok = {code.index("SEL.", m.start()) for m in allowed.finditer(code) if (m.group(1) or m.group(2)) in lists}
            bad = sorted(uses - ok)
            assert not bad, f"{file.name}: {[code[max(0, i - 30):i + 40] for i in bad]}"
