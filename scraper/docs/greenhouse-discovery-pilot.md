# Greenhouse discovery pilot (KAN-722 D1-G-001)

2026-11-06. Two isolated runs found the same **seven qualifying apply URLs absent from the supplied local feed**, across three boards. This is measured candidate yield, not seven newly published jobs or proof of absence from current production.

## Frozen batch and eligibility

`greenhouse-pilot-manifest.json` names the 20 candidates and pins the open-jobs source URL/hash, catalog hash, discovery rejection-ledger hash/ref, and selection rule. Its 5,473 Greenhouse tokens contained 4,605 valid tokens absent from the current catalog. Candidates were selected deterministically by SHA-256 ordering, not by choosing successful examples afterward. None appeared in the discovery branch's existing proposals or rejections (39 entries, zero rejections). The checkout/main had no ledger; the existing discovery branch was checked before any board reads.

The pilot uses existing provider readers, robots rules, pacing, company-name validation and eligibility classification. It preserves the current Greenhouse title gate, then fetches the selected postings' descriptions. A posting counts only after a nonempty description and a valid provider-reported company name are available. Required detail failures/deferred reads are explicitly counted. No rule was weakened and no title-only candidate was included in the seven.

The title gate means this is a lower-bound yield assessment under current Greenhouse behavior: roles discoverable only from descriptions behind otherwise unselected titles were not examined. A readable board with zero selected titles is not proof that it has no potentially eligible jobs.

## Results

| Measure | Run 1 | Run 2 |
|---|---:|---:|
| Candidate boards | 20 | 20 |
| Complete-readable boards | 19 | 19 |
| Missing boards | 1 | 1 |
| Complete-empty boards (included in readable) | 3 | 3 |
| Named boards passing existing validation | 18 | 18 |
| Raw postings | 278 | 278 |
| Title candidates / successfully described | 7 / 7 | 7 / 7 |
| Qualifying distinct URLs | 7 | 7 |
| Overlap with supplied feed | 0 | 0 |
| Requests, including robots | 47 | 47 |
| Retries / failed or deferred details | 0 / 0 | 0 / 0 |
| Wall seconds | 9.954 | 9.500 |

Both runs returned exactly the same seven qualifying URLs. `kca` was missing; `thena` was complete-empty and lacked a valid reported name. Other complete-empty boards were `sadaindia` and `biofourmis`.

| Candidate rollout subtask | Company | Qualifying URLs | Measured requests per pass | Board seconds, run 1 / 2 |
|---|---|---:|---:|---:|
| D1-G-Toradex: `toradex` | Toradex | 3 | 5 | 1.375 / 1.266 |
| D1-G-Maddox: `maddoxindustrialtransformer` | Maddox Industrial Transformer | 2 | 4 | 0.922 / 0.812 |
| D1-G-NetEase: `neteasegames` | NetEase Games | 2 | 4 | 0.890 / 0.875 |

Toradex has the highest observed yield per request; Maddox and NetEase tie on that measure. Their individual timings are too close and too few to establish a reliable ordering. Each named subtask is complete when the board remains valid, those URLs have current eligibility evidence, an isolated canary satisfies publication/source safeguards, and refresh demand fits observed production headroom. Preserve company names reported by the provider rather than inferring them from tokens.

## Cost and admission

Each pass used 20 listing requests, 19 company-name requests, seven detail requests and one shared robots request. The three yielding boards accounted for 13 requests per pass excluding shared robots. This measures repeated cold description reads and name validation, not warmed-cache demand. It does not measure database persistence/publication, embeddings or background description-refresh cost. Do not claim the second pass establishes long-term freshness or spare production capacity.

Ticket 1/KAN-605 is merged in [PR #374](https://github.com/workitjobs/workit/pull/374). A completed numeric capacity report was not located in the inspected repository/PR discussion; that is an evidence limitation, not a claim that the ticket is unfinished. Existing discovery defaults allow 20 validations; this pilot independently caps itself at 200 actual HTTP calls, a 300-second soft deadline and 20 selected detail attempts per board. An in-flight call/backoff may finish after the deadline; another HTTP call cannot start afterward.

Recommendation: carry the three yielding boards forward as the next bounded production-canary candidates. Do not add all 20 boards. Production admission still requires the agreed capacity/freshness observation window and safe source/publication rollback. This pilot does not modify the catalog, discovery ledger, worker tasks, database or published feed.

The comparison feed contains 25,018 distinct URLs and is an older local snapshot; its exact hash is retained in both results. Global verified-active inventory is not established here. Report the remaining gap as `max(0, 200000 - verified_active_qualifying_urls)` once that global total is available; neither 25,018 nor 25,025 is a verified denominator.

## Reproduction, canary and rollback

Validation: eight pilot tests passed; whole-scraper Ruff lint/format passed. Full suite: 1,089 passed and one existing localhost Workday POST test failed with Windows socket error 10053. That test failed once more when run with the pilot tests, then passed alone (the pilot tests also passed). The complete suite was not all-green in this run; no production HTTP code was changed to conceal the intermittent socket failure. Manifest hashes and the repeated seven-URL result were independently checked.

From `scraper/`, with the existing snapshot supplied explicitly and a new output directory:

```text
python pilot_greenhouse.py --manifest docs/greenhouse-pilot-manifest.json --existing-feed feed.json --output ../tasks/greenhouse-pilot-new
uvx pytest tests/test_pilot_greenhouse.py -q
```

`greenhouse-pilot-results.json` retains both measured runs, per-board stage timings, statuses and URLs. Source/catalog/feed hashes distinguish changing inputs. No full descriptions or secrets are retained. The source pool was fetched once before the pilot, outside its per-run request totals.

Stop a repeat on budget exhaustion; deferred details remain uncounted. Failures or missing-name evidence must not become admitted boards. A future production rollout must observe two complete reconciliation opportunities and the selected freshness window; these two closely spaced isolated passes do not satisfy that gate. Roll back this experiment by removing its CLI/artifacts; no production state changed. Future production rollback must stop the admitted batch without treating paused sources as absence evidence or deleting history.
