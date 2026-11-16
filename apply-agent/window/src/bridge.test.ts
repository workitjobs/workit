import assert from "node:assert/strict";
import { test } from "node:test";

import { routes } from "./bridge.ts";

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

test("Stop applying and Remove reach /stop and /remove", async () => {
  const { sent, bridge } = posts();
  await bridge.remove("https://jobs.lever.co/acme/2");
  await bridge.stop();
  assert.deepEqual(sent, [
    { path: "/remove", token: "tok", body: { link: "https://jobs.lever.co/acme/2" } },
    { path: "/stop", token: "tok", body: {} },
  ]);
});
