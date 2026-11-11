# The ask model (`ask_model`)

`ask_model` in `policies.yaml` picks the model behind `ask`: every text
call that answers, writes, edits or checks (one-off answers, essays, the
Pre-submit review, re-plans, the story map). KAN-723 added it, as the first
step from `claude -p` to a model a desktop app may call
(`../../docs/desktop_application_auto_apply.md`, section 8). The goal of a
hosted model is a run that works and is usable, not Claude's quality.

| `ask_model` | `ask` goes to | Essay prompts | Claude fill, Rescue, company briefs |
|---|---|---|---|
| `claude` (default) | `claude -p` on your own login (`claude_cli.py`) | full | `claude -p` |
| `groq` | Groq: `openai/gpt-oss-120b`, `gpt-oss-20b` for Haiku's calls | lean | `claude -p`, still |
| `gemini` | Gemini: `gemini-3.5-flash-lite` | lean | `claude -p`, still |
| `[groq, gemini]` | Groq, and Gemini for each call Groq can't take | lean | `claude -p`, still |

## Rules

- **One seam.** `ask_model.live_claude` builds the Claude adapter from the
  policies. Every place that builds a live adapter for `ask` calls it
  (`cli.live_adapters`, `apply story-map`, an Own application pasted with
  no run going). `HostedAsk` sends `ask` to its endpoints and everything
  else (`drive`, `research`) to the `ClaudeCLI` it wraps; `spent()` adds
  both, per thread, so a rehearsal's token line still counts its own calls.
  Repairs (`work`, a Claude Code session) and doctor's usage reading stay
  on `ClaudeCLI`.
- **Providers** are `ask_model.PROVIDERS`: each one's URL (all take
  OpenAI's chat completions format), model names, reasoning effort and key.
  `ask_models.<provider>` in `policies.yaml` overrides the model names key
  by key. Use production models only: preview models can go at short notice.
- **The chain.** A list tries each provider in order. A call moves to the
  next one when the provider refuses it as too large (413, or a 400 that
  says so), rate-limits it (429: an earlier endpoint hands on at once; the
  last waits up to 60 s, and a longer wait is a `UsageLimitHit`, so a run
  pauses as it does at Claude's limit), is down (5xx or unreachable, after
  retries at 2, 5 and 15 s), or gives an answer that never fits the schema.
  A refused key (401, 403) is a `SetupError` with the fix and never moves
  on: it is a setup error, not a busy provider.
- **Schemas.** Each call tries up to three modes, the next one after a 400:
  Groq's strict mode (`strict` rewrites the schema: every property required,
  every object closed, a property the schema didn't require nullable, its
  null dropped from the answer, so callers get `claude -p`'s shape); the
  schema as given; then plain JSON with the schema in the system prompt.
  Every answer is checked against the schema (`_misfit`: types, required
  properties, enums, items). A reply in a code fence is read.
- **Lean essay prompts** (`adapters.lean`: a hosted adapter is lean,
  `claude -p` never is). They fit Groq's free tier: 8,000 tokens a minute
  per model, and a request over that is refused.
  - The plan lists only the Question types its questions were matched to
    (`LEAN_PLAN`), not all 16.
  - The writer gets the rules for every answer cut to each rule's lead
    (`answering.rules(lean=True)`) and each type's guide cut to its Order
    and Rules (`answering.guide_text(..., lean=True)`); the quoted readers,
    the Pairs and the model letters stay out.
  - One-off questions are drafted in a call of their own, so the essay
    call holds no Applicant profile.

  Measured on Test Person's sample data (2026-11-10): the plan for one
  short essay went from 5,566 to 3,227 prompt tokens. The writing call went
  from 11,344 tokens, which Groq refused, to about 6,100. For two essays and
  two one-off questions, the largest call was 6,303 tokens. A real student's
  Story bank and profile are longer than Test Person's.
- **Quotes that differ only in form still count** (all backends). The plan
  must back each slot with a quote from the sources. `essays._quotable`
  compares words only: punctuation, markdown, quote marks and hyphen kinds
  drop out (gpt-oss writes "made‑up" with U+2011), and small numbers match
  as digits ("every five minutes" holds "every 5 minutes,"). The same
  words must still come in the same order, whole. `essays._fact_quoted`
  backs a company-fact slot with the brief line its plan's company_fact
  names, when the model named a fact and copied no line.
- **The key** is each provider's environment variable, else its Keychain
  item (`no_key` prints the command). It is a developer's own key for
  testing. Never ship a key in an app: a student build calls through a
  WorkIt route that holds the key (the desktop plan, section 8). `apply
  doctor` prints an "Ask model" line only for a hosted `ask_model`,
  failing when a provider in it has no key; it never prints a key.
- **Privacy.** With a hosted model, each prompt (the profile, the sources,
  the company material) goes to that provider. Traces keep the answer as
  `claude -p`'s do, with `backend` and `provider_model` added, and a
  `moved_on` event for each call one provider handed on. An error keeps
  no organization id.
- **Tests** never reach a provider: `tests/test_ask_model.py` fakes the
  HTTPS post, and `conftest.py` drops `ask_model` from the data folder's
  policies, so a test always runs on `claude`. `LeanClaude` in
  `tests/test_claude_answers.py` checks the lean prompts.

## What a comparison showed (2026-11-10, Test Person's sample data)

- **Groq alone on the free tier** can't write essays with the full prompts,
  and runs slowly with lean ones: each call can wait most of a minute.
  `[groq, gemini]` wrote a short job (one essay, one dropdown) in 19 s, and
  two essays with two one-off questions in 39 s, with Gemini taking most
  calls after Groq's minute ran out.
- **Answers:** dropdowns matched Claude's. Open one-off answers were
  generic ("Backend/Systems" where Claude tied the answer to the company's
  fleet dashboard). Essays were plain and correct, and one was short: the
  length gate held it for the student, as it did one of Claude's.
- **Plans:** before the quote fixes, gpt-oss passed the plan's quote check
  in 1 of 6 tries; after them, its first plans passed.

## To try it

```sh
security add-generic-password -s apply-groq -a api.groq.com -w                      # asks for the key
security add-generic-password -s apply-gemini -a generativelanguage.googleapis.com -w
```

Then set `ask_model: [groq, gemini]` in `policies.yaml` in the data folder,
run `uv run apply doctor` (the "Ask model" line), and rehearse a posting
you rehearsed on `claude` before. Compare the two Records' answers.
