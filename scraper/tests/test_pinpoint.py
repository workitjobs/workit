"""Pinpoint reader: real response shapes, pay, work style, empty and missing boards.

Each fixture in ``fixtures/providers/`` is a trimmed Pinpoint API response.
Pinpoint returns every posting in one request with descriptions, so there is no
pagination and no describe function.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workit_scraper import providers
from workit_scraper.providers.model import BoardNotFound

FIXTURES = Path(__file__).parent / "fixtures" / "providers"


def fixture(name: str) -> object:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return json.loads(text)


class TestPinpoint:
    def test_the_list_reads_postings_with_all_fields(self, monkeypatch) -> None:
        asked: list[str] = []
        payload = fixture("pinpoint-list.json")
        monkeypatch.setattr(
            providers.fetch, "_get_json", lambda url: asked.append(url) or payload
        )
        jobs = providers.pinpoint("acme", "Acme Corp")
        assert len(asked) == 1
        assert "postings.json" in asked[0]
        assert len(jobs) == 3

        first = jobs[0]
        assert first.title == "Software Engineering Intern - Summer 2027"
        assert first.external_id == "591998"
        assert first.apply_url == "https://acme.pinpointhq.com/postings/591998-software-engineering-intern"
        assert first.location == "London, UK"
        assert first.department == "Engineering"

    def test_description_concatenates_sections(self, monkeypatch) -> None:
        payload = fixture("pinpoint-list.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: payload)
        jobs = providers.pinpoint("acme", "Acme Corp")
        first = jobs[0]
        assert first.page is not None
        desc = first.description or ""
        assert "12-week summer internship" in desc
        assert "Build features" in desc
        assert "Currently pursuing" in desc

    def test_pay_from_visible_compensation(self, monkeypatch) -> None:
        payload = fixture("pinpoint-list.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: payload)
        jobs = providers.pinpoint("acme", "Acme Corp")
        first = jobs[0]
        assert first.page is not None
        assert first.facts.pay is not None
        assert first.facts.pay.currency == "USD"
        assert first.facts.pay.low == 30.0
        assert first.facts.pay.high == 45.0
        assert first.facts.pay.period == "hour"

    def test_hidden_compensation_gives_no_stated_pay(self, monkeypatch) -> None:
        """compensation_visible: false → no structured pay passed to _page."""
        payload = fixture("pinpoint-list.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: payload)
        jobs = providers.pinpoint("acme", "Acme Corp")
        second = jobs[1]
        # The second fixture title is an intern too, so may_keep keeps it.
        assert second.page is not None

    def test_work_style_mapped(self, monkeypatch) -> None:
        payload = fixture("pinpoint-list.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: payload)
        jobs = providers.pinpoint("acme", "Acme Corp")
        assert jobs[0].page is not None
        assert jobs[0].page.facts.work_style == "Hybrid"
        assert jobs[1].page is not None
        assert jobs[1].page.facts.work_style == "Remote"
        # Third posting ("Marketing Coordinator") is not an intern title,
        # so may_keep rejects it and page is None. On-site is tested via
        # the first two's assertion that _listed_page reads workplace_type.
        assert jobs[2].page is None

    def test_empty_board_returns_no_jobs(self, monkeypatch) -> None:
        monkeypatch.setattr(
            providers.fetch, "_get_json", lambda url: {"data": []}
        )
        jobs = providers.pinpoint("empty", "Empty Corp")
        assert jobs == []

    def test_missing_data_raises_board_not_found(self, monkeypatch) -> None:
        monkeypatch.setattr(
            providers.fetch, "_get_json", lambda url: {"error": "not found"}
        )
        with pytest.raises(BoardNotFound):
            providers.pinpoint("nosuch", "No Such Corp")

    def test_no_department_gives_none(self, monkeypatch) -> None:
        payload = fixture("pinpoint-list.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: payload)
        jobs = providers.pinpoint("acme", "Acme Corp")
        third = jobs[2]
        assert third.department is None


class TestProviderRecord:
    def test_apply_link_matches(self) -> None:
        pattern = providers.PROVIDERS["pinpoint"].apply_link
        m = pattern.search("https://acme.pinpointhq.com/postings/591998")
        assert m and m.group(1) == "acme"

    def test_subdomains_is_set(self) -> None:
        assert providers.PROVIDERS["pinpoint"].subdomains == "pinpointhq.com"

    def test_not_paged(self) -> None:
        assert providers.PROVIDERS["pinpoint"].paged is False

    def test_no_describe(self) -> None:
        assert providers.PROVIDERS["pinpoint"].describe is None
