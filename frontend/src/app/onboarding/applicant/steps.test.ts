import assert from "node:assert/strict";
import { test } from "node:test";

import {
  EXTENSION_STEP_PATH,
  ONBOARDING_STEPS,
  railStep,
  startStep,
  WIZARD_PAGES,
} from "./steps.ts";

test("?step=extension, the extension's install tab (KAN-471), opens a finished seeker on the extension step", () => {
  assert.equal(EXTENSION_STEP_PATH, "/onboarding/applicant?step=extension");
  assert.equal(startStep("extension", true), 4);
});

test("a seeker with no saved answers starts at the first step, whatever the link asks", () => {
  assert.equal(startStep("extension", false), 0);
  assert.equal(startStep("2", false), 0);
  assert.equal(startStep(undefined, false), 0);
});

test("?step=2 still opens Profile, and anything else the first step", () => {
  assert.equal(startStep("2", true), 2);
  assert.equal(startStep(undefined, true), 0);
  assert.equal(startStep(["extension"], true), 0);
  assert.equal(startStep("practice", true), 0);
});

test("the Add Claude page (KAN-507) sits between the extension and the practice batch", () => {
  const at = (name: (typeof WIZARD_PAGES)[number]) => WIZARD_PAGES.indexOf(name);
  assert.equal(at("Claude"), at("Extension") + 1);
  assert.equal(at("Practice"), at("Claude") + 1);
  // The install tab still opens the extension's page, not the one after it.
  assert.equal(startStep("extension", true), at("Extension"));
});

test("the rail keeps five marks: Availability sits under Profile and Add Claude under Practice", () => {
  assert.deepEqual(ONBOARDING_STEPS, ["Role", "Resume", "Profile", "Extension", "Practice"]);
  assert.deepEqual(
    WIZARD_PAGES.map((_, page) => ONBOARDING_STEPS[railStep(page)]),
    ["Role", "Resume", "Profile", "Profile", "Extension", "Practice", "Practice"],
  );
});
