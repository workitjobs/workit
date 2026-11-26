import assert from "node:assert/strict";
import { test } from "node:test";

import { routes } from "./bridge.ts";
import { said } from "./words.ts";

test("each refusal Apply's routes and app methods can send reads in the student's words", () => {
  // As dashboard.py's routes and app_window.Bridge write them today.
  const cases: [string, string][] = [
    ["No run is going.", "Nothing is being applied to right now."],
    ["That job has started already: it isn't waiting any more.", "That job has already started, so it can't be removed."],
    ["Attach the file on the form itself.", "This file goes on the form itself. Open the form and attach it there."],
    ["That question is no longer waiting for you.", "That question is already answered."],
    ["Write an answer.", "Type an answer first."],
    ["Not saved: [Errno 28] No space left on device", "Your answer wasn't saved. Try again."],
    ["That is too big to be an answer.", "That file is too big to attach."],
    ["That essay is too long.", "That answer is too long."],
    ["Only the Apply window may answer for you.", "This window couldn't do that. Quit WorkIt Auto Apply and open it again."],
    ["That browser has no window to open: it runs headless, or it closed.", "That form's window is closed."],
    ["That form isn't held for you now: Fill again works once Apply has stopped on it, before Submit.", "That form is closed now, so it can't be tried again."],
    ["That form isn't held for you now: it's closed already.", "That form is already closed."],
    ["No such form.", "That didn't work. Try again."],
    ["WorkIt Auto Apply couldn't read your queue (WorkIt didn't answer). Paste a link instead.", "We couldn't read your Auto Apply queue on WorkIt. Paste a job's link instead."],
    ["A run is going: its forms are in the window.", "WorkIt is already applying. Stop it first, or wait until it's done."],
    ["The run stopped: KeyError: 'url'", "Applying stopped because something went wrong. Press Start to try again."],
    ["Google Chrome isn't installed: install it from https://www.google.com/chrome/", "Google Chrome isn't installed. Get it from google.com/chrome, then press Start again."],
  ];
  for (const [raw, words] of cases) assert.equal(said(raw), words, raw);
});

test("a line in Apply's developer words never reaches the student; plain ones pass as they are", () => {
  assert.equal(said("ask_model: workit needs a WorkIt sign-in: run uv run apply login"), "Something went wrong. Try again.");
  assert.equal(said("Worker 2's Chrome profile is in use by another Chrome"), "Something went wrong. Try again.");
  assert.equal(said("handoff: Workday didn't answer its sign-in form (https://acme.wd5.myworkdayjobs.com/x)"), "Something went wrong. Try again.");
  assert.equal(said("Tick a job in your queue, or paste a job posting's link."), "Tick a job in your queue, or paste a job posting's link.");
});

test("a route's refusal reaches the page in the student's words", async () => {
  globalThis.fetch = (async () => new Response(JSON.stringify({ error: "No run is going." }), { status: 409 })) as typeof fetch;
  await assert.rejects(routes("tok", Promise.resolve({})).stop(), { message: "Nothing is being applied to right now." });
});
