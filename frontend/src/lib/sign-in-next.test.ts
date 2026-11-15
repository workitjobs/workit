import assert from "node:assert/strict";
import { test } from "node:test";

import { signInNext } from "./sign-in-next.ts";

test("a sign-in goes back only to the pages that send one there", () => {
  assert.equal(signInNext("/app-sign-in?challenge=abc"), "/app-sign-in?challenge=abc");
  assert.equal(signInNext("/connect/claude?request=1"), "/connect/claude?request=1");
  assert.equal(
    signInNext("/onboarding/applicant?step=extension"),
    "/onboarding/applicant?step=extension",
  );
  assert.equal(signInNext("/home"), null);
  assert.equal(signInNext(undefined), null);
});

test("a next that would leave the site is refused", () => {
  assert.equal(signInNext("//evil.example/app-sign-in?x"), null);
  assert.equal(signInNext("/app-sign-in?x=//evil.example"), null);
  assert.equal(signInNext("https://evil.example/app-sign-in?x"), null);
});
