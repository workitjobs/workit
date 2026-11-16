import assert from "node:assert/strict";
import { test } from "node:test";

import { logoSources } from "./logo.ts";

const acme = { company_domain: "acme.com", logo_url: "https://www.google.com/s2/favicons?domain=acme.com" };

test("a job's logo comes from Brandfetch by its domain first, then the scraper's logo, as the website's jobLogo", () => {
  assert.deepEqual(logoSources(acme, "client-id"), [
    "https://cdn.brandfetch.io/acme.com/fallback/404/icon?c=client-id",
    "https://www.google.com/s2/favicons?domain=acme.com",
  ]);
});

test("no domain, or no client id in the build, skips Brandfetch: a domain is never guessed from the name", () => {
  assert.deepEqual(logoSources({ logo_url: acme.logo_url }, "client-id"), [acme.logo_url]);
  assert.deepEqual(logoSources(acme, ""), [acme.logo_url]);
});

test("a job with neither source has none, so it shows its initials", () => {
  assert.deepEqual(logoSources({ company_domain: null, logo_url: null }, "client-id"), []);
  assert.deepEqual(logoSources({}, "client-id"), []);
});
