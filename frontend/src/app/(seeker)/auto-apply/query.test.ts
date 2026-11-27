import assert from "node:assert/strict";
import { test } from "node:test";

import { activityHref, parseActivityQuery } from "./query.ts";

test("Live Activity filtered to Applied opens on the latest application first", () => {
  assert.equal(parseActivityQuery(new URLSearchParams("status=applied")).sort, "applied");
  assert.equal(parseActivityQuery(new URLSearchParams("status=applied&sort=queue")).sort, "queue");
  assert.equal(parseActivityQuery(new URLSearchParams("status=applied,queued")).sort, "queue");
  assert.equal(parseActivityQuery(new URLSearchParams("")).sort, "queue");
});

test("picking Applied on the default sort keeps the URL plain; an own sort stays", () => {
  const plain = parseActivityQuery(new URLSearchParams(""));
  assert.equal(activityHref(plain, { statuses: ["applied"] }), "/auto-apply?status=applied");
  const applied = parseActivityQuery(new URLSearchParams("status=applied"));
  assert.equal(activityHref(applied, { statuses: [] }), "/auto-apply");
  assert.equal(activityHref(applied, { sort: "queue" }), "/auto-apply?status=applied&sort=queue");
  const byMatch = parseActivityQuery(new URLSearchParams("sort=match"));
  assert.equal(
    activityHref(byMatch, { statuses: ["applied"] }),
    "/auto-apply?status=applied&sort=match",
  );
});
