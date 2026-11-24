import assert from "node:assert/strict";
import { test } from "node:test";

import {
  EXTENSION_STEP_PATH,
  PAGE_SLUGS,
  pageOf,
  pageOfSlug,
  progress,
  SETUP_PAGES,
  startStep,
  trackStart,
  UNSURE_PAGES,
  unsureClears,
  nextPage,
  skippedPage,
  WIZARD_PAGES,
} from "./steps.ts";

test("?step=extension, the extension's install tab (KAN-471), opens a finished seeker on the extension track", () => {
  assert.equal(EXTENSION_STEP_PATH, "/onboarding/applicant?step=extension");
  assert.equal(startStep("extension", true), pageOf("Extension"));
});

test("a seeker with no saved answers starts at the first page, whatever the link asks", () => {
  assert.equal(startStep("extension", false), 0);
  assert.equal(startStep(undefined, false), 0);
});

test("every page opens directly from its ?step= slug", () => {
  for (const page of WIZARD_PAGES) {
    assert.equal(pageOfSlug(PAGE_SLUGS[page]), pageOf(page));
    assert.equal(startStep(PAGE_SLUGS[page], true), pageOf(page));
  }
  assert.equal(new Set(Object.values(PAGE_SLUGS)).size, WIZARD_PAGES.length);
});

test("a setup page opens for a new student; an extension page does not", () => {
  assert.equal(startStep("pay", false), pageOf("Pay"));
  assert.equal(startStep("contact", false), pageOf("Contact"));
  assert.equal(startStep("practice", false), 0);
  assert.equal(startStep("claude", false), 0);
});

test("an unknown or repeated ?step= opens the first page", () => {
  assert.equal(startStep("2", true), 0);
  assert.equal(startStep("Pay", true), 0);
  assert.equal(startStep(undefined, true), 0);
  assert.equal(startStep(["extension"], true), 0);
});

test("a seeker who finished onboarding opens on the extension track, even with no saved answers", () => {
  // A finished seeker must not be sent back to Role to fill everything in
  // again (2026-11-01). The extension pages save nothing.
  assert.equal(startStep("extension", false, true), pageOf("Extension"));
  assert.equal(startStep(undefined, false, true), 0);
});

test("setup ends on Contact, which opens the Jobs page; the extension track follows it only by link", () => {
  assert.equal(SETUP_PAGES.at(-1), "Links");
  assert.equal(pageOf("Extension"), SETUP_PAGES.length);
  // The resume comes before Contact, so its header fills Contact's fields.
  assert.ok(pageOf("Resume") < pageOf("Contact"));
  // Add Claude (KAN-507) sits between the install and the practice batch.
  assert.equal(pageOf("Claude"), pageOf("Extension") + 1);
  assert.equal(pageOf("Practice"), pageOf("Claude") + 1);
});

test("each track counts its own progress, and Back stops at its first page", () => {
  assert.equal(progress(0), 1 / SETUP_PAGES.length);
  assert.equal(progress(pageOf("Links")), 1);
  assert.equal(progress(pageOf("Extension")), 1 / 3);
  assert.equal(progress(pageOf("Practice")), 1);
  assert.equal(trackStart(pageOf("Contact")), 0);
  assert.equal(trackStart(pageOf("Claude")), pageOf("Extension"));
  assert.equal(WIZARD_PAGES.length, SETUP_PAGES.length + 3);
});

test("Not Sure Yet is on every setup question, never the resume or Contact", () => {
  assert.deepEqual(UNSURE_PAGES, [
    "Role",
    "JobType",
    "StartDate",
    "Level",
    "Where",
    "Location",
    "Pay",
    "Authorization",
    "Sponsorship",
  ]);
  for (const page of UNSURE_PAGES) assert.ok(SETUP_PAGES.includes(page));
});

test("Not Sure Yet clears the page's own filters, so the Jobs page shows every option", () => {
  assert.deepEqual(unsureClears("Role"), { roles: [], customRoles: [] });
  assert.deepEqual(unsureClears("JobType"), { jobTypes: [], startTerms: [] });
  assert.deepEqual(unsureClears("Level"), { levels: [] });
  assert.deepEqual(unsureClears("Where"), { workStyles: [] });
  assert.deepEqual(unsureClears("Location"), { places: [] });
  assert.deepEqual(unsureClears("Pay"), { minPay: null, maxPay: null });
  assert.equal(unsureClears("Authorization"), null);
  assert.equal(unsureClears("Sponsorship"), null);
  assert.deepEqual(unsureClears("StartDate"), { startTerms: [] });
});

test("Start Date is asked only once Internship is picked", () => {
  const intern = { jobTypes: ["internship" as const], workStyles: [] };
  const fullTime = { jobTypes: ["full_time" as const], workStyles: [] };
  assert.equal(skippedPage("StartDate", intern), false);
  assert.equal(skippedPage("StartDate", fullTime), true);
  assert.equal(skippedPage("Level", fullTime), false);
  // Forward from Job Type and back from Level pass over it without one
  assert.equal(nextPage(pageOf("JobType"), 1, fullTime), pageOf("Level"));
  assert.equal(nextPage(pageOf("Level"), -1, fullTime), pageOf("JobType"));
  assert.equal(nextPage(pageOf("JobType"), 1, intern), pageOf("StartDate"));
  assert.equal(nextPage(pageOf("Level"), -1, intern), pageOf("StartDate"));
});

test("Location is skipped when Remote is the only workplace picked", () => {
  const at = (workStyles: ("onsite" | "hybrid" | "remote")[]) => ({ jobTypes: [], workStyles });
  assert.equal(skippedPage("Location", at(["remote"])), true);
  assert.equal(skippedPage("Location", at(["remote", "hybrid"])), false);
  assert.equal(skippedPage("Location", at(["onsite"])), false);
  // Not Sure Yet on Where leaves no workplace: every job, so ask where
  assert.equal(skippedPage("Location", at([])), false);
  assert.equal(nextPage(pageOf("Where"), 1, at(["remote"])), pageOf("Pay"));
  assert.equal(nextPage(pageOf("Pay"), -1, at(["remote"])), pageOf("Where"));
  assert.equal(nextPage(pageOf("Where"), 1, at(["onsite"])), pageOf("Location"));
});
