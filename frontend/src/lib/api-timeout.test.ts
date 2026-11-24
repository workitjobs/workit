import assert from "node:assert/strict";
import { test } from "node:test";

import { withReadTimeout } from "./api-timeout.ts";

test("a read gets a signal", () => {
  assert.ok(withReadTimeout().signal instanceof AbortSignal);
  assert.ok(withReadTimeout({ method: "GET" }).signal instanceof AbortSignal);
  assert.ok(withReadTimeout({ method: "get" }).signal instanceof AbortSignal);
});

test("a write is never limited", () => {
  for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
    const init = { method, body: "{}" };
    assert.equal(withReadTimeout(init), init);
  }
});

test("a read aborts once the limit passes", async () => {
  const { signal } = withReadTimeout({}, 20);
  assert.equal(signal?.aborted, false);
  await new Promise((resolve) => setTimeout(resolve, 60));
  assert.equal(signal?.aborted, true);
  assert.equal((signal?.reason as Error).name, "TimeoutError");
});

test("a caller's own signal still stops the read", () => {
  const own = new AbortController();
  const { signal } = withReadTimeout({ signal: own.signal });
  assert.equal(signal?.aborted, false);
  own.abort();
  assert.equal(signal?.aborted, true);
});

test("the rest of init is kept", () => {
  const init = withReadTimeout({ headers: { A: "1" }, cache: "no-store" });
  assert.deepEqual(init.headers, { A: "1" });
  assert.equal(init.cache, "no-store");
});
