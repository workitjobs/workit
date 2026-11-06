"""The Jibe diagnostic is bounded, sanitized, and leaves the real reader intact."""

import sys

import pytest

import diagnose_jibe as diagnostic
from workit_scraper import web
from workit_scraper.providers import fetch
from workit_scraper.providers.systems import jibe


class AllowedRobots:
    def allows(self, url):
        return True

    def pace(self, url):
        pass


def test_request_limit_and_timeout(monkeypatch):
    timeouts = []

    def get(url, *, timeout, headers=None):
        timeouts.append(timeout)
        return b"{}"

    def read(*args, **kwargs):
        for _ in range(31):
            web.get("https://example.test", timeout=25)

    monkeypatch.setattr(web, "get", get)
    monkeypatch.setattr(jibe, "jibe", read)
    result = diagnostic.diagnose(AllowedRobots())
    assert result["status"] == "BudgetExceeded"
    assert result["requests"] == 30
    assert timeouts == [15] * 30
    assert web.get is get


def test_deadline_stops_the_next_request(monkeypatch):
    now = [0.0]
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        now[0] = 241.0
        return b"{}"

    def read(*args, **kwargs):
        web.get("https://example.test", timeout=15)
        web.get("https://example.test", timeout=15)

    monkeypatch.setattr(diagnostic.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(web, "get", get)
    monkeypatch.setattr(jibe, "jibe", read)
    result = diagnostic.diagnose(AllowedRobots())
    assert result["status"] == "BudgetExceeded"
    assert result["requests"] == len(calls) == 1


@pytest.mark.parametrize("failed", [False, True])
def test_sanitization_qualification_and_restoration(monkeypatch, failed):
    def get(url, **kwargs):
        return b"{}"

    def get_json(url):
        web.get(url, timeout=25)
        if failed:
            raise ValueError("private response text")
        return {
            "totalCount": 1,
            "jobs": [
                {
                    "data": {
                        "slug": "42",
                        "req_id": "req42",
                        "ats_code": "icims",
                        "title": "Software Engineering Intern",
                        "description": "private response text",
                    }
                }
            ],
        }

    monkeypatch.setattr(web, "get", get)
    monkeypatch.setattr(fetch, "_get_json", get_json)
    original_size = jibe.JIBE_PAGE
    result = diagnostic.diagnose(AllowedRobots())
    assert web.get is get
    assert fetch._get_json is get_json
    assert original_size == jibe.JIBE_PAGE
    assert result["requests"] == 1
    assert "private" not in str(result).lower()
    if failed:
        assert result["status"] == result["error"] == "ValueError"
        assert "qualifying" not in result
    else:
        assert result["status"] == "complete"
        assert result["jobs"] == result["qualifying"] == result["total_unique"] == 1
        assert result["pages"] == [
            {
                "page": 1,
                "limit": 100,
                "totalCount": 1,
                "row_count": 1,
                "identifiers": [{"slug": "42", "req_id": "req42", "ats_code": "icims"}],
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
    monkeypatch.setattr(sys, "argv", ["diagnose_jibe.py", "--output", str(tmp_path)])

    def forbidden(*args, **kwargs):
        pytest.fail("Existing output must be rejected before any probe")

    monkeypatch.setattr(diagnostic, "diagnose", forbidden)
    with pytest.raises(SystemExit) as error:
        diagnostic.main()
    assert error.value.code == 2
    assert marker.read_text(encoding="utf-8") == "original"
