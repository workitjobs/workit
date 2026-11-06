# SuccessFactors investigation (KAN-722 S1)

2026-11-06; fixed sample: `www.careerprofile.epiroc.com`.

## Findings and change

The historical log records `Incomplete: read 278 distinct postings of 10` (interleaved with another provider's output). Its response pages were not retained. Today's baseline and post-fix canary both completed all **308** advertised listings, in the same order, without retries.

A separate bounded request at `startrow=308`, just beyond the result set, returned **10 fallback rows** and the label `Results 309 – 10 of 10`. This is a plausible mechanism for the historical total shrinking to 10, not proof of the original cause. The count parser matched the actual label; no cross-element regex failure was observed. Inconsistent/fallback responses remain incomplete; the experiment does not justify weakening completeness or retrying indefinitely.

Two deterministic failure-injection tests exposed actual defects in the reader:

1. A later-page 404 propagated as `BoardNotFound`; the shared board reader classified it as `MISSING`. The fix converts later-page 404s to `Incomplete`. Initial-page 404 behavior is unchanged.
2. A nonempty page containing only already-seen postings added no distinct IDs. Because pagination uses the distinct count as its next offset, the reader requested the same offset indefinitely until an external budget intervened. The fix raises `Incomplete` as soon as that page adds no postings. It preserves successful overlapping pages that add postings and eventually reach the total.

Both tests were observed failing before the fix. Production changes are confined to these two failure paths. Apply-URL identity, eligibility, description parsing, source support and closure rules remain unchanged; failed reads cannot provide missing/complete evidence. No publication or database writes occurred.

## Measurements and limits

| Measure | Baseline | Read-only canary |
|---|---:|---:|
| Advertised / distinct listings | 308 / 308 | 308 / 308 |
| Complete-readable boards | 1 | 1 |
| Listing requests / robots requests | 13 / 1 | 13 / 1 |
| Retries | 0 | 0 |
| Runtime, seconds | 13.828 | 11.375 |

The tail probe added one robots request and one listing request, separate from this table. Normal reads used a 35-request cap, a 240-second soft deadline and a 15-second per-request timeout, preserving existing robots, pacing, retry and same-origin handling. Two local runs are not a reliable speedup or production capacity measurement.

Offline replay of the full baseline HTML through the original and modified readers produced identical **308 Job records**. Live before/after ordered posting IDs were also identical. The forced no-progress case now stops after two requests instead of making a third request to the same offset; no production-wide runtime saving is claimed.

Net additional readable boards and listing URLs attributable to the fix: **0** on this sample. No jobs were published. Qualifying inventory was **not measured**: SuccessFactors requires posting-detail requests for eligibility evidence, which this listing-only investigation did not fetch. The gap to 200,000 verified-active qualifying jobs remains unmeasured. No discovery expansion is authorized by these measurements.

## Reproduction and fixtures

From `scraper/`:

```text
uvx pytest tests/test_successfactors_coverage.py tests/test_more_providers.py tests/test_diagnose_successfactors.py -q
python diagnose_successfactors.py --output ../tasks/successfactors-diagnostic-new
```

The CLI fixes the target and budgets, requires a new output directory, and retains only pagination labels, posting paths, counts, controlled status and timings in `summary.json`. It does not fetch descriptions or persist production state. The initial live capture used the equivalent local `tasks/sf_probe.py` harness. An in-flight request or existing pacing/backoff can finish after the soft deadline; a subsequent HTTP call cannot start.

`tests/fixtures/providers/successfactors-epiroc.json` retains exact observed pagination labels and parsed listing fields for the 13 normal pages and the out-of-range tail, omitting unrelated HTML. Tests reconstruct minimal table markup around those fields. The fallback test deliberately substitutes the real tail response for the final page; it is a constructed failure scenario, not a claim that the live canary returned that sequence.

Coverage includes complete, empty, partial overlap, successful overlap, first/later timeout, initial/later 404, no-progress repetition, captured 308-row pagination and the inconsistent fallback. Existing description parsing tests remain unchanged.

## Rollout and rollback

Validation: **1,082 full-suite tests passed** (73.43 seconds, UTF-8 mode on Windows), **29 focused tests passed**, and whole-scraper Ruff lint/format checks passed. Both targeted failure regressions were red before the reader change and green afterward.

Deploy through the normal scraper/backend package release after review. The completed canary was read-only, not a production publication run. Stop promotion on successful-board parity changes, request growth or failed pages providing missing/complete evidence. This change neither expands the catalog nor alters runtime budgets.

Rollback is a focused revert of the two reader guards and associated tests; no migration or data restoration is needed. It restores the known repeated-offset and later-page-missing risks, so prefer pausing affected work through a mechanism that does not itself supply absence evidence. Preserve source records and first-seen history.

The original Epiroc failure remains unattributed without its responses. Further count/ordering repair requires new captured evidence. Discovery batches and oversized boards remain separate subtasks, subject to measured refresh capacity.
