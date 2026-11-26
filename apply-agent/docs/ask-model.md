# The ask model (`ask_model`)

`ask_model` in `policies.yaml` picks the model behind `ask`: every text
call that answers, writes, edits or checks (one-off answers, essays, the
Pre-submit review, re-plans, the story map). KAN-723 added it, as the first
step from `claude -p` to a model a desktop app may call
(`../../docs/desktop_application_auto_apply.md`, D1 and W1). The goal of a
hosted model is a run that works and is usable, not Claude's quality.

**`ask_model: workit`** (`WorkItAsk`, 2026-11-14) sends each call as a
kind and its data (`Claude.ask_kind`), as the signed-in student
(`apply login`; a developer's own API with `APPLY_WORKIT_API`). WorkIt
builds the prompt (`../../backend/app/apply_prompts/`), so a call never
carries one. Its per-minute limit is waited out once; its daily Usage cap
raises `UsageLimitHit`, which pauses the run until midnight UTC. It is
also the run's usage (`Adapters.usage`, in the Student build and in a
Developer checkout): `WorkItAsk.reading` reads `GET /apply-app/usage` and
is limited from the moment `used` reaches `cap` until `resets_at`. Until
then a rehearsal, the Student build's run, opens no form
(`rehearsal._after_the_limit`), `apply run` starts no Application
(`orchestrator._resume_at`), and the window shows the pause with its
time. Before (2026-11-15), the Student build's usage was never limited: at
the cap each link left opened its form, was refused at its first ask and
ended paused, and nothing started it again. WorkIt not answering reads as
not limited, since the next ask reports it. In a rehearsal a reading that
fails (a Developer checkout's `claude -p` logged out, or its probe
refused) is no limit too: raised before the link's `try`, it ended the
link's thread holding its Worker's turn, and the run waited until Ctrl-C
(2026-11-16). A form already filled is sent at a limit, since a submit
makes no model call: WorkIt checks the cap before each call, so the
pre-submit review can be the call that reaches it, and a pause at submit
filled that form again after the reset. Every
other adapter refuses a kind with a SetupError (`adapters.NEEDS_WORKIT`):
`claude` can run one again only once the developer prompt route is built
(urgent, `../../docs/developer_apply_agent_testing_framework.md`).
A kind call is a wait the tile shows with Resume (`stuck.Waits.ask_kind`), but its HTTP call
can't be cut short: Resume takes effect once WorkIt answers or the call times out.
`as_applicant.ask_kind` adds the pronouns and the school to the data, and
puts the first name back into the answer, since the prompts say `@NAME@`.
**`workit` is the default** (2026-11-14, `policies.default.yaml`), and
every one of Apply's calls sends a kind, with its prompt only on the
server: the Essay plan and essay call, the claim check and editor's pass,
the default probe, the Pre-submit review and its replan, the story map,
the team name, Own application and Claude fill's sent check. The answering
guides moved with them; Apply fetches each type's front matter, which its
own code reads, from WorkIt (`GET /apply-app/types`, `apply.answering`). `WorkItAsk.ask` refuses a
prompt, and WorkIt's free-form route that took one is gone. In
tests, `FakeClaude.ask_kind` answers a kind from its data and keeps it in
`claude.kinds`, apart from `claude.calls` (drives, and the calls that send
their own prompt). A test that means "no model call" checks
`claude.asked`, both lists: `claude.calls == []` passed while a kind ran,
and tests in the files CI does not run still read calls that had become
kinds until 2026-11-14. Run those files on a Mac after a change to a call.

**`[groq, gemini]` was the default** (2026-11-10 to 2026-11-14).
`claude` is a developer's choice, set in their own `policies.yaml`.
Policies with no `ask_model` key (a test's) read as `claude`, and
`conftest.py` drops the key, so a test never calls a provider. The
launched desktop app calls hosted models only, through a WorkIt route
that holds the keys. The Student build (`apply/build.py`) reads no
`policies.yaml`: its `ask_model` is fixed to `workit`, WorkIt's Model
route, and behind it is `student.NoClaude`, never `claude -p`, so
`drive` and `research` raise `ClaudeError` there.

| `ask_model` | `ask` goes to | Essay prompts | Claude fill, Rescue, company briefs |
|---|---|---|---|
| `workit` (being built, KAN-723 D5) | WorkIt's Model route, `POST /apply-app/ask`, as a kind and its data; WorkIt builds the prompt and runs its own chain | lean, on the server | `claude -p`, still |
| `[groq, gemini]` (default) | Groq, and Gemini for each call Groq can't take | lean | `claude -p`, still |
| `groq` | Groq: `openai/gpt-oss-120b`, `gpt-oss-20b` for Haiku's calls | lean | `claude -p`, still |
| `gemini` | Gemini: `gemini-3.5-flash-lite` | lean | `claude -p`, still |
| `claude` (developers) | `claude -p` on your own login (`claude_cli.py`) | full | `claude -p` |

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
  - The plan lists only the Question types its questions were matched to,
    not all 16.
  - The writer gets the rules for every answer cut to each rule's lead and
    each type's guide cut to its Order and Rules; the quoted readers, the
    Pairs and the model letters stay out. Both are built on WorkIt's
    server now (`../../backend/app/apply_prompts/essays.py` and
    `guides.py`), always lean.
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
  item, else the checkout's root `.env` (`ask_model.DOTENV`): the Scout
  endpoint on the provider's host in `SCOUT_ENDPOINTS`,
  `SCOUT_ENDPOINTS_LARGE` or `_SMALL`, else `SCOUT_API_KEY` with
  `SCOUT_BASE_URL`. Nothing else in the file is read. The team's `.env`
  holds both, so a developer saves no key (`no_key` prints the ways). It is
  a key for testing. Never ship a key in an app: a student build calls through a
  WorkIt route that holds the key (the Model route, the desktop plan's W1). `apply
  doctor` prints an "Ask model" line only for a hosted `ask_model`,
  failing when a provider in it has no key; it never prints a key.
- **Privacy.** With a hosted model, each prompt (the profile, the sources,
  the company material) goes to that provider. Traces keep the answer as
  `claude -p`'s do, with `backend` and `provider_model` added, and a
  `moved_on` event for each call one provider handed on. An error keeps
  no organization id.
  Google's terms let it use Gemini free-tier prompts to improve its
  products. Scout accepts that because it removes identity data
  (`scout/CLAUDE.md`); Apply's prompts carry the applicant's name and,
  for one-off questions, the whole profile. Before a student's data goes
  to a provider, the WorkIt route must use terms that don't train on it,
  or remove the identity data.
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

## To use it

With the team's `.env` in the checkout's root, nothing: `uv run apply
doctor` says "Ask model: groq, then gemini". To keep `claude -p`, set
`ask_model: claude` in `policies.yaml` in the data folder. Your own keys
go in `GROQ_API_KEY` and `GEMINI_API_KEY`, or in Keychain, from `apply-agent/`:

```sh
uv run keyring set apply-groq api.groq.com                      # asks for the key
uv run keyring set apply-gemini generativelanguage.googleapis.com
```

## The Best model on your own plan (`apply app --max-plan`)

With `--max-plan`, the window's asks run on `claude -p` with WorkIt's
prompts built from this checkout (`apply.local_prompts`). Large kinds
(essays, cover letters, story tags) and the Pre-submit review run on
Opus, the Best model; the other small kinds stay on Haiku. Settings has
a switch to put them back on Sonnet. Near the plan's limits (70% of the
5-hour window, or 60% of the week) they drop to Sonnet by themselves,
and Settings says why until a call runs on Opus again.

To run on another subscription than your `claude` login, make a setup
token once and keep it in Keychain:

```sh
claude setup-token              # prints a long-lived token for your subscription
uv run apply claude-token       # asks for it, hidden, and keeps it under apply-claude
uv run apply claude-token --forget
```

Every `claude -p` call then passes it as `CLAUDE_CODE_OAUTH_TOKEN`, which
wins over the login. Settings names which one is in use.
