// Sequential Reviewer — implement-then-review loop
//
// This template drives a two-phase workflow per issue:
//   Phase 1 (Implement): An agent picks an open KAN issue, works on it
//                        on a dedicated branch, commits the changes, and signals
//                        completion.
//   Phase 2 (Review):    A second agent reviews the branch diff and either
//                        approves it or makes corrections directly on the branch.
//
// Both phases share a single sandbox created via createSandbox(), so the
// implementer and reviewer work on the same explicit branch.
//
// The outer loop repeats up to MAX_ITERATIONS times, processing one issue per
// iteration and stopping early once the backlog is exhausted (an implement
// phase that produces no commits). This is a middle-complexity option between
// the simple-loop (no review gate) and the parallel-planner (concurrent
// execution with a planning phase).
//
// Usage, from the repo root:
//   npm --prefix .sandcastle install   (once)
//   npm --prefix .sandcastle start

import { mkdtempSync, realpathSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import * as sandcastle from "@ai-hero/sandcastle";
import { bwrap } from "@ai-hero/sandcastle/sandboxes/bwrap";
import { seatbelt } from "@ai-hero/sandcastle/sandboxes/seatbelt";

// `npm --prefix .sandcastle start` runs this from .sandcastle/; Sandcastle
// expects the repo root.
process.chdir(fileURLToPath(new URL("..", import.meta.url)));

// The OS's own process sandbox: Seatbelt on macOS, Bubblewrap on Linux and
// on Windows inside WSL2.
//
// Claude Code keeps its scratch files under CLAUDE_CODE_TMPDIR, default /tmp,
// which the sandbox can't write (EPERM on /tmp/claude-<uid>). Each sandbox
// gets its own host temp dir for it, mounted in and removed on close.
const sandboxProvider = (claudeTmp: string) => {
  const options = {
    env: { CLAUDE_CODE_TMPDIR: claudeTmp },
    mounts: [{ hostPath: claudeTmp, sandboxPath: claudeTmp }],
  };
  return process.platform === "darwin" ? seatbelt(options) : bwrap(options);
};

const MODEL = "claude-opus-5-5";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

// Maximum number of implement→review cycles to run before stopping.
// Each cycle works on one issue. Raise this to process more issues per run.
const MAX_ITERATIONS = 10;

// Hooks run before the agent starts each iteration.
// - On the host: fetch the Fill engine submodule, which apply-agent/ and the
//   extension's tests load. The sandbox can't write git's control files, so
//   this can't run inside it.
// - In the sandbox: `npm ci` in frontend/ (the root package.json has no
//   dependencies). It installs exactly the lockfile; `npm install` rewrote
//   frontend/package-lock.json and left a change in every agent's worktree.
// The Python packages sync on demand through `uv run`. Env files are not
// copied in, so the agent never holds the team's secrets.
const hooks = {
  host: { onWorktreeReady: [{ command: "git submodule update --init" }] },
  sandbox: { onSandboxReady: [{ command: "npm --prefix frontend ci" }] },
};

// ---------------------------------------------------------------------------
// Main loop
// ---------------------------------------------------------------------------

for (let iteration = 1; iteration <= MAX_ITERATIONS; iteration++) {
  console.log(`\n=== Iteration ${iteration}/${MAX_ITERATIONS} ===\n`);

  // Generate a unique branch name for this iteration.
  const branch = `sandcastle/sequential-reviewer/${Date.now()}`;

  // Create a single sandbox that both the implementer and reviewer share.
  // This gives both agents a real, named branch that persists across phases.
  const claudeTmp = mkdtempSync(join(realpathSync(tmpdir()), "sandcastle-claude-"));
  const sandbox = await sandcastle.createSandbox({
    branch,
    sandbox: sandboxProvider(claudeTmp),
    hooks,
  });

  try {
    // -----------------------------------------------------------------------
    // Phase 1: Implement
    //
    // The agent picks the next open issue, writes the
    // implementation (using RGR: Red → Green → Repeat → Refactor), and
    // commits the result.
    //
    // The agent signals completion via <promise>COMPLETE</promise> when done.
    // -----------------------------------------------------------------------
    // One iteration so each outer pass implements a single issue on its own
    // branch, then hands it to the reviewer. A higher value lets the agent
    // drain the whole backlog onto this one branch in a single pass, which
    // defeats the per-issue review.
    const implement = await sandbox.run({
      name: "implementer",
      maxIterations: 1,
      agent: sandcastle.claudeCode(MODEL),
      promptFile: "./.sandcastle/implement-prompt.md",
    });

    if (!implement.commits.length) {
      // No commits means the backlog is empty or every remaining issue is
      // blocked — there is nothing left to implement or review, so stop.
      console.log("Implementation agent made no commits. Stopping.");
      break;
    }

    console.log(`\nImplementation complete on branch: ${branch}`);
    console.log(`Commits: ${implement.commits.length}`);

    // -----------------------------------------------------------------------
    // Phase 2: Review
    //
    // A second agent reviews the diff of the branch produced by
    // Phase 1. It uses the {{BRANCH}} prompt argument to inspect the right
    // branch, and either approves or makes corrections directly on the branch.
    // -----------------------------------------------------------------------
    await sandbox.run({
      name: "reviewer",
      maxIterations: 1,
      agent: sandcastle.claudeCode(MODEL),
      promptFile: "./.sandcastle/review-prompt.md",
      promptArgs: {
        BRANCH: branch,
      },
    });

    console.log("\nReview complete.");
  } finally {
    await sandbox.close();
    rmSync(claudeTmp, { recursive: true, force: true });
  }
}

console.log("\nAll done.");
