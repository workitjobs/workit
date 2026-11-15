# .sandcastle/

[Sandcastle](https://github.com/mattpocock/sandcastle) runs an unattended
implement-then-review loop over KAN issues, each pass in the OS's own process
sandbox (Seatbelt on macOS, Bubblewrap on Linux and on Windows inside WSL2;
Windows outside WSL2 is unsupported). Self-contained like the other folders:
its own `package.json` and lockfile, nothing at the root.

## Running it

```
npm --prefix .sandcastle install   # once per checkout
cp .sandcastle/.env.example .sandcastle/.env
npm --prefix .sandcastle start     # from the repo root
```

`.sandcastle/.env` (gitignored) needs `CLAUDE_CODE_OAUTH_TOKEN` (from
`claude setup-token`), `JIRA_EMAIL` and `JIRA_API_TOKEN`. The sandbox hides
the host's logins, so these are the only credentials the agent holds. App env
files are never copied in: tests that need a database or a secret skip or
fail, and the agent says so in its hand-off.

## How work flows

- **Opt-in by label.** The loop picks up only open KAN issues labelled
  `sandcastle`, one per pass, skipping any with an open `is blocked by` link.
  A person adds the label; the loop never chooses work on its own.
- Each pass commits on a new `sandcastle/sequential-reviewer/<time>` branch;
  a second agent then reviews that diff and may commit refinements. Commits
  use the repo's `KAN-<n>: <summary>` subject.
- **It never closes an issue.** On finishing it comments and swaps the label
  to `sandcastle-done`; when stuck, to `sandcastle-blocked`. A person renames
  the branch to the `KAN-<n>-...` convention, opens the PR and moves the issue
  to Done when it merges. Swapping the label is what stops the next pass
  picking the same issue again.
- A pass that makes no commits ends the run (empty queue or all blocked).

## Learned the hard way

- Claude Code writes scratch files under `CLAUDE_CODE_TMPDIR` (default
  `/tmp`), which Seatbelt denies: the agent exited at once with `EPERM ...
  /tmp/claude-<uid>`. `main.mts` gives each sandbox its own mounted temp dir.
- `npm install` in the sandbox rewrote `frontend/package-lock.json`, leaving
  a change in every agent's worktree that it could commit. The hook runs
  `npm ci`, which installs the lockfile as it is.
- The Fill engine submodule is not in a fresh worktree, so apply-agent's
  tests could not run. A host hook runs `git submodule update --init`; it
  cannot run in the sandbox, where git's control files are read-only.
- Jira comments and label changes appear under the name of whoever owns the
  `JIRA_API_TOKEN`, not as a bot.

## Files

- `main.mts` — the loop: sandbox, hooks, models, iteration count.
- `implement-prompt.md`, `review-prompt.md` — what each agent is told.
  `` !`cmd` `` lines run before the prompt is sent and inline their output.
- `CODING_STANDARDS.md` — the reviewer's checklist; it points at the
  `CLAUDE.md` files rather than copying them.
- `jira.mjs` — the only bridge to Jira (`list`, `view`, `done`, `block`), over
  the REST API with the token above. The Atlassian MCP server is not
  available inside the sandbox.
