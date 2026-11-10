# The ask model (`ask_model`)

`ask_model` in `policies.yaml` picks the model behind `ask`: every text
call that answers, writes, edits or checks (one-off answers, essays, the
Pre-submit review, re-plans, the story map). KAN-723 added it, as the first
step from `claude -p` to a model a desktop app may call
(`../../docs/desktop_application_auto_apply.md`, section 8).

| `ask_model` | `ask` goes to | Claude fill, Rescue, company briefs |
|---|---|---|
| `claude` (default) | `claude -p` on your own login (`claude_cli.py`) | `claude -p` |
| `groq` | Groq's chat API (`groq.py`) | `claude -p`, still |

## Rules

- **One seam.** `groq.live_claude` builds the Claude adapter from the
  policies. Every place that builds a live adapter for `ask` calls it
  (`cli.live_adapters`, `apply story-map`, an Own application pasted with
  no run going). `GroqAsk` sends `ask` to Groq and everything else
  (`drive`, `research`) to the `ClaudeCLI` it wraps; `spent()` adds both,
  per thread, so a rehearsal's token line still counts its own calls.
  Repairs (`work`, a Claude Code session) and doctor's usage reading
  stay on `ClaudeCLI`.
- **Models.** `groq.MODELS` maps Apply's names to Groq's: `opus` and
  `sonnet` to `openai/gpt-oss-120b`, `haiku` to `openai/gpt-oss-20b` with
  `reasoning_effort: low` (as `claude -p` gives Haiku `--effort low`).
  `groq_models` in `policies.yaml` overrides them key by key. Use Groq's
  production models only: preview models can go at short notice.
- **Schemas.** Groq's strict mode needs every property required and every
  object closed. `groq.strict` rewrites the schema: a property the schema
  didn't require becomes nullable, and its null is dropped from the answer,
  so callers get the shape `claude -p` gives. A schema strict mode refuses
  (HTTP 400, an unsupported keyword) goes again in best-effort mode. Every
  answer is checked against the schema (`_misfit`: types, required
  properties, enums, items); one that never fits is a `ClaudeError`.
- **Errors map onto Claude's.** A refused key (401, 403) is a
  `SetupError` with the fix. A 429 that asks for 60 s or less (a
  tokens-a-minute limit) waits and tries again; a longer one is a `UsageLimitHit` with its reset time, so a
  run pauses as it does at Claude's limit. A 5xx or a dropped connection is
  tried again after 2, 5 and 15 s, then a `ClaudeError`, which callers
  already handle.
- **Groq's free tier is too small for essays** (seen 2026-11-10, Test
  Person's sample data): it allows 8,000 tokens a minute per model, and a
  request over that is refused (HTTP 413, a `ClaudeError` with Groq's
  message; a 429 when the minute's tokens are partly spent, which waits).
  The essay plan for one short essay is about 5,600 prompt tokens and fits;
  two essays asked 8,577. The writing call for one short essay asked
  11,344 and can't fit. One-off answers alone fit (about 4,400 tokens).
  A real student's Story bank and profile are longer than Test Person's.
  Use a key on Groq's Developer tier (250,000 tokens a minute).
- **What fills the prompts** (one short essay): the plan's system prompt
  lists all 16 Question types' guides (about 10,500 characters) though the
  plan keeps the type each question already has; the writing call's system
  prompt is about 26,000 characters (rules, weak and strong example
  answers, the type list), and its prompt carries the whole Applicant
  profile (about 5,400 characters) because one-off questions are drafted
  in the same call. Shortening any of them changes Claude's prompts too.
- **gpt-oss and the plan's quote check:** the plan must copy each quote
  word for word from the sources. In 6 plan calls, gpt-oss passed once:
  it rewrote quotes ("every 5 minutes," as "every five minutes"), and one
  correct quote failed only on its non-breaking hyphen (U+2011), which
  `essays._plain` now reads as "-". An essay whose plan fails twice comes
  back empty with a question for the student (Needs you), as designed.
- **The key** is `GROQ_API_KEY`, else Keychain (service `apply-groq`,
  account `api.groq.com`). It is a developer's own key for testing.
  Never ship a key in an app: a student build calls Groq through a WorkIt
  route that holds the key (the desktop plan, section 8). `apply doctor`
  prints an "Ask model" line only with `ask_model: groq`, failing when
  there is no key; it never prints the key.
- **Privacy.** With `groq`, each prompt (the profile, the sources, the
  company material) goes to Groq. Traces keep the answer as `claude -p`'s
  do, with `backend` and `groq_model` added.
- **Tests** never reach Groq: `tests/test_groq.py` fakes the HTTPS post,
  and `conftest.py` drops `ask_model` from the data folder's policies, so a
  test always runs on `claude`.

## To try it

```sh
security add-generic-password -s apply-groq -a api.groq.com -w   # asks for the key
```

Then set `ask_model: groq` in `policies.yaml` in the data folder, run
`uv run apply doctor` (the "Ask model" line), and rehearse a posting you
rehearsed on `claude` before. Compare the two Records' answers.
