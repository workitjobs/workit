"""The rules a Wikidata answer passes before it is proposed (docs/logos.md,
"Wikidata proposals"). Items are trimmed from Wikidata's real answers of
2026-11-09 and 2026-11-10."""

import json
import urllib.error
from datetime import date
from email.message import Message

import pytest

import domain_pr
from workit_scraper import wikidata


def item(qid, label, *sites, aliases=(), description=None, rank="normal", dissolved=False):
    claims = {
        "P856": [{"mainsnak": {"datavalue": {"value": site}}, "rank": rank} for site in sites]
    }
    if dissolved:
        claims["P576"] = [{"mainsnak": {"datavalue": {"value": {"time": "+2020"}}}}]
    return {
        "id": qid,
        "labels": {"en": {"value": label}},
        "aliases": {"en": [{"value": a} for a in aliases]},
        "descriptions": {"en": {"value": description}} if description else {},
        "claims": claims,
    }


CMS = item(
    "Q5013012",
    "CMS Energy",
    "http://www.cmsenergy.com/",
    description="electric and gas company in Jackson, Michigan, US",
)
SIMON = item("Q2287759", "Simon Property Group", "http://www.simon.com", "https://www.simon.com/")
SIMON_HQ = item("Q7519585", "Simon Property Group Headquarters")
SPA = item("Q7663846", "Systems Planning and Analysis", "http://www.spa.com")


class TestKey:
    def test_names_compare_without_case_punctuation_or_legal_words(self) -> None:
        assert wikidata.key("CMS Energy Corporation") == wikidata.key("CMS Energy")
        assert wikidata.key("U-Haul") == wikidata.key("Uhaul")
        assert wikidata.key("Systems Planning & Analysis") == wikidata.key(
            "Systems Planning and Analysis (SPA)"
        )
        assert wikidata.key("The Boeing Company") == wikidata.key("Boeing")

    def test_a_legal_word_alone_is_kept(self) -> None:
        assert wikidata.key("Company") == "company"


class TestPick:
    def test_the_item_named_like_the_company_gives_its_domain(self) -> None:
        answer = wikidata.pick("CMS Energy", [CMS])
        assert answer == wikidata.Answer(
            "cmsenergy.com", "Q5013012", "electric and gas company in Jackson, Michigan, US"
        )
        assert wikidata.pick("Simon Property Group", [SIMON, SIMON_HQ]).domain == "simon.com"
        assert wikidata.pick("Systems Planning and Analysis (SPA)", [SPA]).domain == "spa.com"

    def test_a_similar_name_does_not_count(self) -> None:
        law = item("Q1", "CMS", "https://cms.law/")
        assert wikidata.pick("CMS Energy", [law]) == wikidata.NONE

    def test_an_alias_counts(self) -> None:
        haul = item("Q2", "U-Haul International", "https://www.uhaul.com", aliases=["U-Haul"])
        assert wikidata.pick("Uhaul", [haul]).domain == "uhaul.com"

    def test_two_websites_for_one_name_give_nothing(self) -> None:
        one = item("Q3", "Global Infrastructure", "https://gi-partners.example")
        other = item("Q4", "Global Infrastructure", "https://gi-design.example")
        assert wikidata.pick("Global Infrastructure", [one, other]) == wikidata.NONE

    def test_no_website_or_a_dissolved_company_gives_nothing(self) -> None:
        # "Workshop" matched only ideas (a studio, a factory): none has a website.
        idea = item("Q656720", "workshop")
        assert wikidata.pick("Workshop", [idea]) == wikidata.NONE
        gone = item("Q5", "Acme Widgets", "https://acme.example", dissolved=True)
        assert wikidata.pick("Acme Widgets", [gone]) == wikidata.NONE

    def test_a_one_word_company_needs_its_own_name_as_its_domain(self) -> None:
        paccar = item("Q6", "Paccar", "https://www.paccar.com")
        assert wikidata.pick("Paccar", [paccar]).domain == "paccar.com"
        # Another company of the same name, or one of its parts (trial, 2026-11-10).
        kroll = item("Q13", "Kroll", "https://www.krollshop.de", description="publisher in Germany")
        chubb = item("Q14", "Chubb", "https://www.chubbfs.com")
        teledyne = item("Q15", "Teledyne", "https://www.teledyne-e2v.com")
        for name, it in (("Kroll", kroll), ("Chubb", chubb), ("Teledyne", teledyne)):
            assert wikidata.pick(name, [it]) == wikidata.NONE

    def test_a_one_word_domain_may_add_a_company_word(self) -> None:
        for name, site in (
            ("Safran", "https://www.safran-group.com"),
            ("Clorox", "https://www.thecloroxcompany.com"),
            ("Envista", "https://www.envistaco.com"),
            ("Legrand", "https://www.legrandgroup.com"),
        ):
            assert wikidata.pick(name, [item("Q16", name, site)]).domain, name

    def test_a_thing_that_never_hires_gives_nothing(self) -> None:
        horse = item("Q17", "Secretariat", "https://www.secretariat.com")
        horse["claims"]["P31"] = [{"mainsnak": {"datavalue": {"value": {"id": "Q726"}}}}]
        band = item("Q18", "Black Box", "https://www.blackboxhouse.eu")
        band["claims"]["P31"] = [{"mainsnak": {"datavalue": {"value": {"id": "Q215380"}}}}]
        assert wikidata.pick("Secretariat", [horse]) == wikidata.NONE
        assert wikidata.pick("Black Box", [band]) == wikidata.NONE
        # Only the never-hiring kinds: a business keeps its answer.
        band["claims"]["P31"][0]["mainsnak"]["datavalue"]["value"]["id"] = "Q4830453"
        assert wikidata.pick("Black Box", [band]).domain == "blackboxhouse.eu"

    def test_preferred_websites_win_and_deprecated_ones_never_count(self) -> None:
        both = item("Q9", "Ryder System", "https://ryder.com")
        both["claims"]["P856"].append(
            {"mainsnak": {"datavalue": {"value": "https://old.example"}}, "rank": "deprecated"}
        )
        assert wikidata.pick("Ryder System", [both]).domain == "ryder.com"
        split = item("Q10", "Ryder System", "https://ryder.com", "https://other.example")
        assert wikidata.pick("Ryder System", [split]) == wikidata.NONE
        split["claims"]["P856"][0]["rank"] = "preferred"
        assert wikidata.pick("Ryder System", [split]).domain == "ryder.com"

    def test_a_subdomain_gives_the_registered_domain_and_a_vendor_none(self) -> None:
        sub = item("Q11", "GE Vernova", "https://careers.gevernova.com")
        assert wikidata.pick("GE Vernova", [sub]).domain == "gevernova.com"
        vendor = item("Q12", "Acme Health", "https://acme.icims.com")
        assert wikidata.pick("Acme Health", [vendor]) == wikidata.NONE


class TestLookUp:
    def test_searches_then_reads_every_result(self, monkeypatch) -> None:
        asked = []

        def get(url, timeout):
            asked.append(url)
            if "wbsearchentities" in url:
                return json.dumps({"search": [{"id": "Q5013012"}]}).encode()
            return json.dumps({"entities": {"Q5013012": CMS}}).encode()

        monkeypatch.setattr(wikidata.web, "get", get)
        assert wikidata.look_up("CMS Energy", sleep=lambda _: None).domain == "cmsenergy.com"
        assert len(asked) == 2 and all("maxlag=5" in url for url in asked)

    def test_a_busy_server_is_retried_then_stops_the_run(self, monkeypatch) -> None:
        waits = []
        headers = Message()
        headers["Retry-After"] = "120"

        def get(url, timeout):
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", headers, None)

        monkeypatch.setattr(wikidata.web, "get", get)
        with pytest.raises(wikidata.Busy):
            wikidata.look_up("CMS Energy", sleep=waits.append)
        assert wikidata.LONGEST_WAIT_S in waits and 120 not in waits


class TestProposals:
    BOARDS = [
        {"board": "workday/a", "company": "A Corp", "roles": 9},
        {"board": "icims/b", "company": "B", "roles": 5},
        {"board": "oracle/c", "company": "C", "roles": 3},
        {"board": "jibe/d", "company": "D", "roles": 1},
    ]

    def test_a_board_is_asked_once_and_a_miss_again_after_the_wait(self) -> None:
        today = date(2026, 11, 10)
        ledger = {
            "icims/b": {"domain": "b.com", "looked_up": "2026-01-01"},
            "oracle/c": {"domain": None, "looked_up": "2026-11-01"},
            "jibe/d": {"domain": None, "looked_up": "2026-08-01"},
        }
        picked = domain_pr.due(self.BOARDS, {"workday/a"}, ledger, today, 10)
        assert [b["board"] for b in picked] == ["jibe/d"]
        assert domain_pr.due(self.BOARDS, set(), {}, today, 2) == self.BOARDS[:2]

    def test_answers_become_rows_and_every_board_joins_the_ledger(self, tmp_path) -> None:
        (tmp_path / "scraper").mkdir()
        checked = tmp_path / domain_pr.CHECKED
        checked.write_text("# note\nboard,website,company,note\nx/y,y.com,Y,\n", encoding="utf-8")
        answers = {
            "A Corp": wikidata.Answer("a.com", "Q1", "maker of things, in Ohio"),
            "B": wikidata.NONE,
        }
        added = domain_pr.look_up_all(
            tmp_path, self.BOARDS[:2], date(2026, 11, 10), lambda name: answers[name]
        )
        assert added == 1
        assert domain_pr.checked_boards(checked) == {"x/y", "workday/a"}
        assert checked.read_text(encoding="utf-8").endswith(
            'workday/a,a.com,A Corp,"Wikidata Q1 (maker of things, in Ohio) names it '
            'the official website; proposed 2026-11-10"\n'
        )
        ledger = json.loads((tmp_path / domain_pr.LEDGER).read_text(encoding="utf-8"))
        assert ledger["icims/b"] == {
            "company": "B",
            "domain": None,
            "item": None,
            "looked_up": "2026-11-10",
        }

    def test_a_busy_wikidata_keeps_what_was_found(self, tmp_path) -> None:
        (tmp_path / "scraper").mkdir()
        (tmp_path / domain_pr.CHECKED).write_text("board,website,company,note\n", encoding="utf-8")

        def look_up(name):
            if name == "B":
                raise wikidata.Busy("busy")
            return wikidata.Answer("a.com", "Q1")

        assert domain_pr.look_up_all(tmp_path, self.BOARDS, date(2026, 11, 10), look_up) == 1
        ledger = json.loads((tmp_path / domain_pr.LEDGER).read_text(encoding="utf-8"))
        assert list(ledger) == ["workday/a"]

    def test_a_pr_closed_without_merging_pauses_the_runs(self) -> None:
        merged = {"number": 4, "state": "closed", "merged_at": "2026-11-01"}
        closed = {"number": 7, "state": "closed", "merged_at": None}
        assert domain_pr.current_pr([merged]) is None
        assert domain_pr.next_branch([merged]) == "codex/company-domains-after-4"
        with pytest.raises(ValueError, match="closed without merging"):
            domain_pr.current_pr([merged, closed])
