import assert from "node:assert/strict";
import { test } from "node:test";

import { routes } from "./bridge.ts";
import { SENT_ANYWAY } from "./view.ts";

// What the routes bridge posts, caught where it leaves the page.
function posts() {
  const sent: { path: string; token: string; body: unknown }[] = [];
  globalThis.fetch = (async (path: string, init: RequestInit) => {
    sent.push({ path, token: (init.headers as Record<string, string>)["X-Apply-Token"], body: JSON.parse(String(init.body)) });
    return new Response("{}");
  }) as typeof fetch;
  return { sent, bridge: routes("tok", Promise.resolve({})) };
}

test("an answer, a Skip and a file reach /answer in the shape the route takes", async () => {
  const { sent, bridge } = posts();
  await bridge.answer("4", "Which offices?", "New York; Remote");
  await bridge.answer("4", "Anything else?", "");
  await bridge.answer("4", "Transcript", { name: "transcript.pdf", data: "JVBERi0=" });
  assert.deepEqual(sent, [
    { path: "/answer", token: "tok", body: { id: "4", question: "Which offices?", answer: "New York; Remote" } },
    { path: "/answer", token: "tok", body: { id: "4", question: "Anything else?", answer: "" } },
    { path: "/answer", token: "tok", body: { id: "4", question: "Transcript", answer: "", file: { name: "transcript.pdf", data: "JVBERi0=" } } },
  ]);
});

test("Stop applying, Stop new ones only, Not applying, Approve and submit, Cancel and Remove reach their routes", async () => {
  const { sent, bridge } = posts();
  await bridge.remove("https://jobs.lever.co/acme/2");
  await bridge.letGo("tile-1");
  await bridge.submit("tile-2");
  await bridge.cancelAuto("tile-2");
  await bridge.stop(true);
  await bridge.stop();
  assert.deepEqual(sent, [
    { path: "/remove", token: "tok", body: { link: "https://jobs.lever.co/acme/2" } },
    { path: "/let-go", token: "tok", body: { id: "tile-1" } },
    { path: "/submit", token: "tok", body: { id: "tile-2" } },
    { path: "/auto-cancel", token: "tok", body: { id: "tile-2" } },
    { path: "/stop", token: "tok", body: { new_only: true } },
    { path: "/stop", token: "tok", body: {} },
  ]);
});

test("an emailed code reaches /code with its case kept, and Send anyway /submit with its reason", async () => {
  const { sent, bridge } = posts();
  await bridge.code("tile-3", "OxNbtPnI");
  await bridge.submit("tile-3", SENT_ANYWAY);
  assert.deepEqual(sent, [
    { path: "/code", token: "tok", body: { id: "tile-3", code: "OxNbtPnI" } },
    { path: "/submit", token: "tok", body: { id: "tile-3", override: SENT_ANYWAY } },
  ]);
});

// /state as Apply answers it: each reply in turn, a thrown one a request that never got an answer.
async function watched(replies: (() => Response)[]) {
  const said: string[] = [];
  globalThis.document = { hasFocus: () => false } as Document;
  globalThis.fetch = (async () => replies.shift()!()) as typeof fetch;
  const stop = routes("tok", Promise.resolve({})).watch(
    () => said.push("state"),
    () => said.push("lost"),
  );
  await new Promise((done) => setTimeout(done, 20));
  stop();
  return said;
}

test("a /state that gets no answer says Apply is lost, and a state means it's back", async () => {
  assert.deepEqual(await watched([() => { throw new TypeError("Failed to fetch"); }]), ["lost"]);
  assert.deepEqual(await watched([() => new Response("{}", { status: 500 })]), ["lost"]);
  assert.deepEqual(await watched([() => new Response(JSON.stringify({ tiles: [], items: [] }))]), ["state"]);
});

test("an action Apply never got says Apply didn't take it, in words", async () => {
  globalThis.fetch = (async () => { throw new TypeError("Failed to fetch"); }) as typeof fetch;
  await assert.rejects(routes("tok", Promise.resolve({})).stop(), { message: "Apply didn't take that. Is it still running?" });
});

test("an app method that breaks says Apply didn't take it, and one that refuses says why", async () => {
  globalThis.window = {
    pywebview: {
      api: {
        start: async () => { throw new Error("Traceback (most recent call last): KeyError 'url'"); },
        queue: async () => ({ error: "WorkIt Auto Apply couldn't read your queue." }),
      },
    },
  } as unknown as Window & typeof globalThis;
  const app = await routes("tok").app;
  await assert.rejects(app.start!(["https://a/1"]), { message: "Apply didn't take that." });
  await assert.rejects(app.queue!(), { message: "We couldn't read your Auto Apply queue on WorkIt. Paste a job's link instead." });
});
