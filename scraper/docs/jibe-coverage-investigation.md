# Jibe incomplete-read investigation (KAN-722 J1)

Date: 2026-11-06. Target: `joinus.ies-co.com` only. Historical symptom: local `scrape.log` records `Incomplete: read 759 postings of 760`. The original response pages were not retained, so the cause of that historical one-row deficit cannot be established.

## Result

Two bounded live reads completed successfully with the same 753 posting IDs in the same order. The existing shortlist, applied to the captured listing descriptions, returned the same 36 qualifying apply URLs on both runs. The historical incomplete read did not reproduce; do not relax the served-row completeness check or infer a persistent pagination bug.

During failure-path testing, a separate concrete defect reproduced: after a successful first page, a second-page 404 propagated as `BoardNotFound`. The shared `read_board` classified that result as `MISSING`, potentially supplying absence evidence rather than preserving a failed read. The regression test failed with `ReadStatus.MISSING` where `FAILED` was required.

The fix catches `BoardNotFound` inside Jibe pagination: page 1 retains its missing-board meaning; later pages raise `Incomplete` with the original exception as their cause. This matches Oracle and Workday's existing semantics. Eligibility, apply URLs, parsing, page sizes, pacing, caps, served-row accounting and duplicate handling are unchanged.

## Measurements

| Measure | Baseline | Post-fix read-only canary |
|---|---:|---:|
| Advertised / served rows | 753 / 753 | 753 / 753 |
| Distinct posting/apply URLs | 753 | 753 |
| Qualifying apply URLs | 36 | 36 |
| Complete-readable boards | 1 | 1 |
| Listing requests | 8 | 8 |
| Robots requests | 1 | 1 |
| Retries | 0 | 0 |
| Runtime, seconds | 53.531 | 53.250 |

Net additional qualifying apply URLs attributable to the change: **0**. Newly readable boards attributable to the change: **0**. The benefit is correct failure classification and protection against false missing-board evidence. No results were published. These two runs do not establish production refresh capacity or a global verified-active total; the remaining gap to 200,000 is unmeasured here.

Listing totals stayed at 753 throughout each run; every page had 100 rows except the last, which had 53. No page-size mismatch, duplicate IDs or changing totals was observed. The runs used existing robots/pacing, retry and same-origin request behavior, with 30-request and 240-second soft limits and 15-second HTTP timeouts. The deadline stops new requests; an in-flight request or normal wait can finish later.

Offline differential replay of all full baseline responses through the original and fixed readers produced **identical 753 Job records**, including descriptions and extracted facts. A successful-board canary cannot exercise a real upstream 404; the deterministic failure-injection regression covers that path.

## Reproduction and fixtures

From `scraper/`:

```text
uvx pytest tests/test_jibe_coverage.py tests/test_more_providers.py tests/test_diagnose_jibe.py -q
python diagnose_jibe.py --output ../tasks/jibe-diagnostic-new
```

The output directory must be new. The CLI fixes the provider, board, page size and budgets, writes a sanitized `summary.json`, and reports a qualifying count only after a complete read. No production catalog, job storage, task state or publication is touched. Initial live captures were collected by the equivalent local `tasks/jibe_probe.py`; the retained CLI makes future runs reproducible.

`tests/fixtures/providers/jibe-ies-complete.json` retains real totals, row order, slug, requisition ID, title and ATS labels from the complete baseline. Descriptions and unrelated response fields are omitted; it is a pagination fixture, not an eligibility fixture. The local full captures were used for the description/eligibility differential check.

Tests cover the recorded complete board with pacing; complete-empty; incomplete/short final page; timeout; initial 404; later-page 404 through the shared board-read boundary; existing duplicated postings, non-iCIMS filtering and cap behavior. Failure cases are explicitly injected using the existing trimmed response fixture, not represented as captured upstream failures.

## Rollout and rollback

Validation: **1,066 full-suite tests passed** (51.31 seconds, UTF-8 mode on Windows); **25 focused Jibe/diagnostic/provider tests passed**. Whole-scraper Ruff lint and formatting checks passed. The new later-page-404 test was observed failing before the fix and passing afterward.

Review and deploy the focused reader change through the normal scraper/backend package release path. The bounded canary is read-only; production deployment and publication have not occurred. Stop rollout if complete-board parity changes, requests increase, or later-page failure returns missing/complete status. No capacity expansion or new boards are admitted.

Rollback: revert the focused Jibe exception-handling change and its tests through the normal deployment process. It requires no migration or storage restoration, but reintroduces the known later-page-404 risk; prefer stopping affected-board processing without treating the pause as absence evidence if that risk appears. Preserve first-seen dates and source history. Never delete source records or reset complete-read history as part of rollback.

Next independent investigation: SuccessFactors `www.careerprofile.epiroc.com`. Revisit the historical IES shortfall only with a new captured incomplete response; do not infer its cause from today's successful read.
