import assert from "node:assert/strict";
import { test } from "node:test";

import { SIGNED_IN_HINT, sessionCookieWrites } from "./cookies.ts";

const TOKEN = "sb-abc-auth-token";
const hintOf = (writes: ReturnType<typeof sessionCookieWrites>) =>
  writes.find((write) => write.name === SIGNED_IN_HINT);

test("writing a session sets the hint, readable by page scripts, with no token in it", () => {
  const writes = sessionCookieWrites([{ name: TOKEN, value: "base64-xyz", options: {} }]);
  assert.equal(writes[0].options.httpOnly, true);
  const hint = hintOf(writes);
  assert.equal(hint?.value, "1");
  assert.equal(hint?.options.httpOnly, false);
  assert.equal(hint?.options.maxAge, writes[0].options.maxAge);
});

test("signing out clears the hint", () => {
  const writes = sessionCookieWrites([
    { name: `${TOKEN}.0`, value: "", options: { maxAge: 0 } },
    { name: `${TOKEN}.1`, value: "", options: { maxAge: 0 } },
  ]);
  assert.equal(hintOf(writes)?.options.maxAge, 0);
});

test("a chunked session that drops a stale chunk keeps the hint", () => {
  const writes = sessionCookieWrites([
    { name: `${TOKEN}.0`, value: "base64-xyz", options: {} },
    { name: `${TOKEN}.1`, value: "", options: { maxAge: 0 } },
  ]);
  assert.equal(hintOf(writes)?.value, "1");
});

test("a batch with no session cookie leaves the hint alone", () => {
  const writes = sessionCookieWrites([
    { name: "sb-abc-auth-token-code-verifier", value: "v", options: {} },
  ]);
  assert.equal(hintOf(writes), undefined);
});
