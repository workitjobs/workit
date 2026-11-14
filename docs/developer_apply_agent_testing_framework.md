# Developer Apply agent testing framework (KAN-723, not built)

**Status (2026-11-14): urgent, not built.** Once Apply's calls send
kinds (W1's "Prompts on the server" in `desktop_application_auto_apply.md`),
`ask_model: claude` stops working for every ported kind, since the
prompts are no longer in the app. Build this before a developer needs
Claude for a ported kind again. It records how developers keep testing
Apply once its prompts live on WorkIt's server (D5).

## The problem it solves

Apply's prompts and answering guides are moving from the app to
`backend/app/apply_prompts/`. The app sends a call's kind and its data
to `POST /apply-app/ask`, and WorkIt builds the prompt, calls the model
and counts the tokens. So a Developer checkout with `ask_model: claude`,
which ran each prompt through `claude -p` on the developer's own Claude
login, has no prompt to run once a kind is ported.

Until this is built, a developer runs `ask_model: workit` against the
local API (D30), which uses the local `.env`'s model keys.

## The design

- **`POST /apply-app/prompt {kind, version, data}`**: the same body as
  `/apply-app/ask`. It builds the prompt as `/ask` does and answers
  `{model, system, prompt, schema}` without calling a model. Nothing
  counts against the Usage cap.
- **Only developer accounts may call it.** Every other account gets 403.
  The list is a setting (for example `APPLY_APP_DEVELOPERS`, a list of
  account ids in the API's secrets), so adding a developer needs no
  migration and no deploy of the app.
- **The Developer checkout's `claude` provider** sends each `ask` to
  that route and runs the prompt it gets back with `claude -p`. Every
  path then uses the server's prompts, so a prompt change is tested
  the same way on Claude and on the hosted models.
- **The prompts stay as the server built them**, placeholders included
  (`@NAME@`, D8): the app puts the values back into the answer, as it
  does for `/ask`.

## What else belongs here

The same framework makes the app testable for developers:

- **Replay:** run a captured `{kind, version, data}` against the
  server's prompts, to compare a prompt change on the same form.
- **A developer Usage cap** of its own, so testing does not spend a
  student's share of the free tiers.
- **Test Person's sample data** as the default data for a developer
  account, as Apply's data folder has it today.

## Not decided

- Whether the developer list is a setting or a flag on the account
  (Supabase `app_metadata`).
- Whether `/apply-app/prompt` logs which developer fetched which kind.
