"""The SuccessFactors diagnostic is bounded and leaves the reader intact."""

import sys

import pytest

import diagnose_successfactors as diagnostic
from workit_scraper import web
from workit_scraper.providers import fetch
from workit_scraper.providers.systems import successfactors


class AllowedRobots:
    def allows(self, url):
        return True

    def pace(self, url):
        pass


def test_request_limit_and_timeout(monkeypatch):
    timeouts = []

    def get(url, *, timeout, headers=None):
        timeouts.append(timeout)
        return b""

    def read(*args, **kwargs):
        for _ in range(36):
            web.get("https://example.test", timeout=25)

    monkeypatch.setattr(web, "get", get)
    monkeypatch.setattr(successfactors, "successfactors", read)
    result = diagnostic.diagnose(AllowedRobots())
    assert result["status"] == "BudgetExceeded"
    assert result["requests"] == 35
    assert timeouts == [15] * 35
    assert web.get is get


def test_deadline_stops_the_next_request(monkeypatch):
    now = [0.0]
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        now[0] = 241.0
        return b""

    def read(*args, **kwargs):
        web.get("https://example.test", timeout=15)
        web.get("https://example.test", timeout=15)

    monkeypatch.setattr(diagnostic.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(web, "get", get)
    monkeypatch.setattr(successfactors, "successfactors", read)
    result = diagnostic.diagnose(AllowedRobots())
    assert result["status"] == "BudgetExceeded"
    assert result["requests"] == len(calls) == 1


@pytest.mark.parametrize("failed", [False, True])
def test_sanitization_and_restoration(monkeypatch, failed):
    def get(url, **kwargs):
        return b""

    def get_text(url):
        web.get(url, timeout=25)
        if failed:
            raise ValueError("private response text")
        return (
            '<span class="paginationLabel">Results <b>1</b> of <b>1</b></span>'
            '<tr class="data-row"><a href="/job/42/" class="jobTitle-link">Intern</a></tr>'
            "<div>private response text</div>"
        )

    monkeypatch.setattr(web, "get", get)
    monkeypatch.setattr(fetch, "_get_text", get_text)
    result = diagnostic.diagnose(AllowedRobots())
    assert web.get is get
    assert fetch._get_text is get_text
    assert result["requests"] == 1
    assert "private" not in str(result).lower()
    if failed:
        assert result["status"] == result["error"] == "ValueError"
    else:
        assert result["status"] == "complete"
        assert result["jobs"] == result["total_unique"] == 1
        assert result["pages"] == [
            {
                "startrow": 0,
                "pagination_labels": ["Results 1 of 1"],
                "row_count": 1,
                "paths": ["/job/42/"],
            }
        ]


def test_robots_denial_prevents_listing_read(monkeypatch):
    class BlockedRobots(AllowedRobots):
        def allows(self, url):
            return False

    def forbidden(*args, **kwargs):
        pytest.fail("Disallowed board must not be read")

    monkeypatch.setattr(web, "get", forbidden)
    result = diagnostic.diagnose(BlockedRobots())
    assert result["status"] == "PermissionError"
    assert result["requests"] == 0
    assert result["pages"] == []


def test_existing_output_is_preserved(monkeypatch, tmp_path):
    marker = tmp_path / "summary.json"
    marker.write_text("original", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["diagnose_successfactors.py", "--output", str(tmp_path)])

    def forbidden(*args, **kwargs):
        pytest.fail("Existing output must be rejected before any probe")

    monkeypatch.setattr(diagnostic, "diagnose", forbidden)
    with pytest.raises(SystemExit) as error:
        diagnostic.main()
    assert error.value.code == 2
    assert marker.read_text(encoding="utf-8") == "original"
