"""The read-only Oracle probe cannot overrun its budget or leave patched readers."""

import sys

import pytest

import diagnose_oracle as diagnostic
from workit_scraper import web
from workit_scraper.providers import fetch
from workit_scraper.providers.systems import oracle


class AllowedRobots:
    def allows(self, url):
        return True

    def pace(self, url):
        pass


def test_actual_get_calls_are_bounded_and_timeout_is_capped(monkeypatch):
    timeouts = []

    def get(url, *, timeout, headers=None):
        timeouts.append(timeout)
        return b"{}"

    def read(*args, **kwargs):
        for _ in range(31):
            web.get("https://example.test", timeout=25)

    monkeypatch.setattr(web, "get", get)
    monkeypatch.setattr(oracle, "oracle", read)
    result = diagnostic.diagnose(diagnostic.TOKENS[0], 200, AllowedRobots())

    assert result["status"] == "BudgetExceeded"
    assert result["requests"] == 30
    assert timeouts == [15] * 30
    assert web.get is get


def test_deadline_prevents_another_request(monkeypatch):
    now = [0.0]
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        now[0] = 181.0
        return b"{}"

    def read(*args, **kwargs):
        web.get("https://example.test", timeout=15)
        web.get("https://example.test", timeout=15)

    monkeypatch.setattr(diagnostic.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(web, "get", get)
    monkeypatch.setattr(oracle, "oracle", read)
    result = diagnostic.diagnose(diagnostic.TOKENS[0], 200, AllowedRobots())

    assert result["status"] == "BudgetExceeded"
    assert result["requests"] == len(calls) == 1


@pytest.mark.parametrize("failed", [False, True])
def test_capture_is_sanitized_and_patches_are_restored(monkeypatch, failed):
    def get(url, **kwargs):
        return b"{}"

    def get_json(url):
        web.get(url, timeout=25)
        if failed:
            raise ValueError("private response and URL must not be persisted")
        return {
            "items": [
                {
                    "TotalJobsCount": 1,
                    "Offset": 0,
                    "Limit": 100,
                    "requisitionList": [{"Id": "42", "Title": "Private response content"}],
                }
            ]
        }

    monkeypatch.setattr(web, "get", get)
    monkeypatch.setattr(fetch, "_get_json", get_json)
    original_size = oracle.ORACLE_PAGE
    result = diagnostic.diagnose(diagnostic.TOKENS[0], 100, AllowedRobots())

    assert web.get is get
    assert fetch._get_json is get_json
    assert original_size == oracle.ORACLE_PAGE
    assert result["requests"] == 1
    assert "private" not in str(result).lower()
    if failed:
        assert result["status"] == result["error"] == "ValueError"
    else:
        assert result["status"] == "complete"
        assert result["total_unique"] == 1
        assert result["pages"] == [
            {
                "requested_offset": 0,
                "requested_limit": 100,
                "TotalJobsCount": 1,
                "Offset": 0,
                "Limit": 100,
                "row_count": 1,
                "ids": ["42"],
            }
        ]


def test_robots_denial_prevents_listing_requests(monkeypatch):
    class BlockedRobots(AllowedRobots):
        def allows(self, url):
            return False

    def no_request(*args, **kwargs):
        pytest.fail("A disallowed listing must not be requested")

    monkeypatch.setattr(web, "get", no_request)
    result = diagnostic.diagnose(diagnostic.TOKENS[0], 200, BlockedRobots())

    assert result["status"] == "PermissionError"
    assert result["requests"] == 0
    assert result["pages"] == []


def test_existing_output_is_rejected_before_any_probe(monkeypatch, tmp_path):
    marker = tmp_path / "summary.json"
    marker.write_text("preserve existing report", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["diagnose_oracle.py", "--output", str(tmp_path)])

    def no_probe(*args, **kwargs):
        pytest.fail("Existing output must be rejected before probing")

    monkeypatch.setattr(diagnostic, "diagnose", no_probe)
    with pytest.raises(SystemExit) as error:
        diagnostic.main()

    assert error.value.code == 2
    assert marker.read_text(encoding="utf-8") == "preserve existing report"
