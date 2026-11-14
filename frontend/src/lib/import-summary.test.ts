import assert from "node:assert/strict";
import { test } from "node:test";

import { headerSummary } from "./import-summary.ts";

test("the note names what the header added, in the profile's order", () => {
  assert.equal(
    headerSummary({
      added: { phone_number: "(631) 555-0100", location: "Stony Brook, NY" },
      offers: [],
      overflow: false,
    }),
    "Added your phone and location to your profile.",
  );
  assert.equal(
    headerSummary({
      added: { github_url: "https://github.com/x", phone_number: "1", resume_header_extra: "x" },
      offers: [],
      overflow: false,
    }),
    "Added your phone, GitHub and additional header line to your profile.",
  );
});

test("more header text than fits points at the Header panel", () => {
  assert.equal(
    headerSummary({ added: {}, offers: [], overflow: true }),
    "We found more header text than fits. Add it in the Header panel.",
  );
});

test("a header that changed nothing says nothing", () => {
  assert.equal(headerSummary({ added: {}, offers: [], overflow: false }), "");
  assert.equal(headerSummary(undefined), "");
});
