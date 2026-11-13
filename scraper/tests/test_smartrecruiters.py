"""SmartRecruiters reader and page reader: real response shapes, pagination and
empty boards.

Each fixture in ``fixtures/providers/`` is a trimmed SmartRecruiters API
response. Where a test pages, the page size is shrunk, never the data.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from workit_scraper import providers

FIXTURES = Path(__file__).parent / "fixtures" / "providers"


def fixture(name: str) -> object:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return json.loads(text)


class TestSmartRecruiters:
    def test_the_list_reads_postings_with_all_fields(self, monkeypatch) -> None:
        asked: list[str] = []
        payload = fixture("smartrecruiters-list.json")
        monkeypatch.setattr(
            providers.fetch, "_get_json", lambda url: asked.append(url) or payload
        )
        jobs = providers.smartrecruiters("ExampleCorp", "Example Corp")
        assert len(asked) == 1
        assert "limit=100&offset=0" in asked[0]
        assert len(jobs) == 3

        first = jobs[0]
        assert first.title == "Software Engineering Intern - Summer 2027"
        assert first.external_id == "743999900001001"
        assert first.apply_url == "https://jobs.smartrecruiters.com/ExampleCorp/743999900001001"
        assert first.location == "San Francisco, California, US"
        assert first.department == "Engineering"
        assert first.posted_at is not None and first.posted_at.startswith("2026-10-15")
        # No page from the list: the describe function reads it.
        assert first.page is None

    def test_empty_location_slots_are_cleaned(self, monkeypatch) -> None:
        """London, , UK -> London, UK."""
        payload = fixture("smartrecruiters-list.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: payload)
        jobs = providers.smartrecruiters("ExampleCorp", "Example Corp")
        london = jobs[1]
        assert london.location == "London, UK"

    def test_pagination_across_two_pages(self, monkeypatch) -> None:
        """Two pages, offset stepping by SR_PAGE."""
        page1 = {
            "offset": 0,
            "limit": 2,
            "totalFound": 3,
            "content": fixture("smartrecruiters-list.json")["content"][:2],
        }
        page2 = {
            "offset": 2,
            "limit": 2,
            "totalFound": 3,
            "content": fixture("smartrecruiters-list.json")["content"][2:],
        }
        pages = iter([page1, page2])
        asked: list[str] = []
        paced: list[str] = []

        monkeypatch.setattr(
            providers.fetch, "_get_json", lambda url: asked.append(url) or next(pages)
        )
        # Shrink page size so the fixture triggers pagination.
        monkeypatch.setattr(
            "workit_scraper.providers.systems.smartrecruiters.SR_PAGE", 2
        )
        jobs = providers.smartrecruiters(
            "ExampleCorp", "Example Corp", pace=paced.append
        )
        assert len(jobs) == 3
        assert len(asked) == 2
        assert "offset=0" in asked[0]
        assert "offset=2" in asked[1]
        # Pace called before the second page, not the first.
        assert len(paced) == 1

    def test_an_empty_board_returns_no_jobs(self, monkeypatch) -> None:
        """An invalid slug returns 200 with totalFound: 0 -- not BoardNotFound."""
        monkeypatch.setattr(
            providers.fetch,
            "_get_json",
            lambda url: {"offset": 0, "limit": 100, "totalFound": 0, "content": []},
        )
        jobs = providers.smartrecruiters("NoSuchCompany", "No Such Company")
        assert jobs == []


class TestDescribeSmartRecruiters:
    def test_description_and_facts_from_detail(self, monkeypatch, swap_provider) -> None:
        detail = fixture("smartrecruiters-detail.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: detail)
        job = providers.Job(
            ats="smartrecruiters",
            token="ExampleCorp",
            company="Example Corp",
            external_id="743999900001001",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://jobs.smartrecruiters.com/ExampleCorp/743999900001001",
            location="San Francisco, California, US",
        )
        result = providers.describe_smartrecruiters(job)
        assert result.page is not None
        # The description concatenates jobDescription + qualifications +
        # additionalInformation, skipping companyDescription.
        assert "real projects with experienced engineers" in (result.description or "")
        assert "Currently pursuing" in (result.description or "")
        assert "12-week paid internship" in (result.description or "")
        # companyDescription is skipped.
        assert "leading technology company" not in (result.description or "")
        # Pay from compensation.
        assert result.facts.pay is not None
        assert result.facts.pay.currency == "USD"
        assert result.facts.pay.low == 30.0
        assert result.facts.pay.high == 45.0
        assert result.facts.pay.period == "hour"

    def test_remote_from_location_flag(self, monkeypatch) -> None:
        detail = deepcopy(fixture("smartrecruiters-detail.json"))
        detail["location"]["remote"] = True
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: detail)
        job = providers.Job(
            ats="smartrecruiters",
            token="ExampleCorp",
            company="Example Corp",
            external_id="743999900001001",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://jobs.smartrecruiters.com/ExampleCorp/743999900001001",
        )
        result = providers.describe_smartrecruiters(job)
        assert result.facts.work_style == "Remote"

    def test_hybrid_from_location_flag(self, monkeypatch) -> None:
        detail = deepcopy(fixture("smartrecruiters-detail.json"))
        detail["location"]["remote"] = False
        detail["location"]["hybrid"] = True
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: detail)
        job = providers.Job(
            ats="smartrecruiters",
            token="ExampleCorp",
            company="Example Corp",
            external_id="743999900001001",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://jobs.smartrecruiters.com/ExampleCorp/743999900001001",
        )
        result = providers.describe_smartrecruiters(job)
        assert result.facts.work_style == "Hybrid"

    def test_no_sections_gives_no_description(self, monkeypatch) -> None:
        detail = deepcopy(fixture("smartrecruiters-detail.json"))
        detail["jobAd"]["sections"] = {}
        detail.pop("compensation", None)
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: detail)
        job = providers.Job(
            ats="smartrecruiters",
            token="ExampleCorp",
            company="Example Corp",
            external_id="743999900001001",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://jobs.smartrecruiters.com/ExampleCorp/743999900001001",
        )
        result = providers.describe_smartrecruiters(job)
        assert result.page is not None
        assert result.description is None


class TestProviderRecord:
    def test_apply_link_matches_jobs_domain(self) -> None:
        pattern = providers.PROVIDERS["smartrecruiters"].apply_link
        m = pattern.search("https://jobs.smartrecruiters.com/ExampleCorp/123-title")
        assert m and m.group(1) == "ExampleCorp"

    def test_apply_link_matches_careers_domain(self) -> None:
        pattern = providers.PROVIDERS["smartrecruiters"].apply_link
        m = pattern.search("https://careers.smartrecruiters.com/MyCompany/456")
        assert m and m.group(1) == "MyCompany"

    def test_skip_robots_is_set(self) -> None:
        assert providers.PROVIDERS["smartrecruiters"].skip_robots is True

    def test_paged_is_set(self) -> None:
        assert providers.PROVIDERS["smartrecruiters"].paged is True
