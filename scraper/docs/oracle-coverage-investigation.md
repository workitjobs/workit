# Oracle incomplete-read investigation (KAN-722 O1)

Date: 2026-11-06. Outcome: reproduced all four recorded failures; no reader repair or production rollout justified by the evidence. Keep the existing completeness tolerance and incomplete-read outcome.

## Experiment

Read the four boards sequentially through the real Oracle reader, once with its normal page size of 200, then with page size 100. Each board had a 30-request cap (including robots and retries), a 180-second soft deadline, and a 15-second timeout per HTTP request. Used the existing User-Agent, same-origin redirect policy, robots checks, shared provider pacing and retry behavior. No descriptions, databases, catalogs, publication or task state were changed.

The initial capture used the local diagnostic harness `tasks/oracle_probe.py`; the retained equivalent is `scraper/diagnose_oracle.py`. The production reader file matched fetched origin/main during inspection. All totals and IDs in the committed fixture are unmodified observations; response fields unrelated to pagination were removed. No credentials or request headers are retained.

| Oracle board token | Reported total | Distinct returned | Gap | Requests, size 200 / 100 | Seconds, size 200 / 100 |
|---|---:|---:|---:|---:|---:|
| `ebwg.fa.us2/CX` | 120 | 118 | 2 | 2 / 3 | 3.766 / 3.515 |
| `eofe.fa.us2/CX_1001` | 1,286 | 1,283 | 3 | 8 / 14 | 18.937 / 24.891 |
| `fa-eomf-saasfaprod1.fa.ocs/CX_1002` | 261 | 258 | 3 | 3 / 4 | 3.828 / 4.266 |
| `hdpn.fa.us6/CX_1` | 218 | 216 | 2 | 3 / 4 | 4.078 / 4.703 |

Requests include one robots read per board per pass. Totals: 41 requests, about 68 seconds summed across board runs. No retries were needed (request counts equal listing pages plus robots). Timing is from one local Windows run per page size, not a production capacity benchmark.

## Diagnosis

The pass/fail loop is an offline replay through the real `oracle()` function. For example the first capture raises `Incomplete: read 118 distinct postings of 120`. Regression tests assert that exact outcome; they pass because rejecting this response is the safe behavior.

Tested hypotheses:

1. **Reported totals exceed retrievable listings.** Supported: each pass returns the same deficit, with stable totals throughout.
2. **Advancing by 200 skips postings after short pages.** Not supported for these captures: pages are full until the final page, and halving page size produces exactly the same ordered IDs.
3. **Overlapping pages or inventory movement loses jobs.** Not observed: no duplicate IDs within/across pages, unchanged totals, identical ordered IDs between passes.

This does not prove why Oracle counts the extra records, or that every possible query would return the same inventory. It establishes that ordinary page-size adjustment does not fix these four failures. Two closely spaced passes are not evidence of long-term stability. No alternate sort, provider-specific filter, tail probe or authenticated view was tested.

The existing reader accepts a deficit of at most `max(1, total // 500)`, with positive-count/zero-results always incomplete. All four exceed that tolerance. Increasing it would convert an unresolved discrepancy into closure evidence. That is not a demonstrated reader fix and was not done.

## Coverage and cost result

- Four boards partially readable; zero newly complete-readable boards.
- Zero additional published qualifying apply URLs: no publication occurred.
- Potential additional qualifying URLs: unmeasured. The 1,875 observed distinct board-local posting IDs are raw listings, not an eligibility result or globally deduplicated verified inventory.
- Page size 100 recovered zero additional raw IDs while raising listing/robots request count from 16 to 25. Retain page size 200.
- Verified-active qualifying inventory and the gap to 200,000 remain unmeasured by this experiment. Do not substitute raw/feed counts.
- Production refresh capacity and description cost were not assessed. No discovery expansion is admitted by this result.

## Reproduction

From `scraper/`, run the offline regression and existing complete-read tests:

```text
uvx pytest tests/test_oracle_coverage.py tests/test_providers.py -q
```

The committed `tests/fixtures/providers/oracle-incomplete.json` includes both page sizes, real page offsets, totals and IDs. Tests reconstruct only the fields the reader needs to reproduce the failure. Complete/mapped responses remain covered by `TestOracle` in `test_providers.py`; the new tests also cover the existing empty-result contract, initial missing board and first/later request timeouts.

To repeat the bounded live experiment from `scraper/`, use two new output directories:

```text
python diagnose_oracle.py --page-size 200 --output ../tasks/oracle-probe-200
python diagnose_oracle.py --page-size 100 --output ../tasks/oracle-probe-100
```

Each directory contains a `summary.json` diagnostic artifact, not a production input. Compare each board's totals, unique IDs, ordered IDs, requests, retries and runtime. A changed upstream response is new evidence, not a reason to edit the fixture until tests pass. The wall deadline is soft: an in-flight request or existing retry wait may finish after it; the next request must not start after the budget. Run the fixed sample only, not a full scrape.

## Rollout and rollback

Verification: full scraper suite **1,054 passed** (69.09 seconds, UTF-8 mode on Windows). Focused diagnostic/Oracle suite **77 passed**. Whole-scraper `ruff check` and `ruff format --check` passed. No production adapter, dependency, eligibility, scheduling or publication code changed.

There is no production reader change to promote. The two live passes are the bounded read-only experiment; no publication canary is claimed. The CLI and regression fixtures can be reviewed independently of pending backend publication changes.

Rollback consists of removing the diagnostic CLI, its tests, fixtures and this report. Nothing in production storage needs reverting. Do not relax completeness, remove source history or mark these boards refreshed to obtain a positive coverage number.

Next action: record O1 as a completed negative investigation and prioritize the named Jibe/SuccessFactors reproductions. If partial positive observations from these Oracle boards are to be published, design that separately against Ticket 2's partial-read/source-support guarantees; they still cannot provide absence evidence.
