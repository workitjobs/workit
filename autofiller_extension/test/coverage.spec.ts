// The panel's coverage badge (KAN-749, background/coverage.js): from the Fill
// engine's job system, fully supported, partly supported (a form in steps) or
// not supported; and the answers to copy on a site WorkIt can't fill.
import { expect, test } from "@playwright/test";
import { answerList, coverageOf } from "../src/background/coverage.js";
import { STUDENT } from "./extension";

test("a one-form job system is fully supported, a stepped one partly, none or one turned off not at all", () => {
  expect(coverageOf({ site: "greenhouse" })).toEqual({ level: "full", badge: "Fully supported", said: "WorkIt fills this Greenhouse form." });
  for (const site of ["workday", "oracle", "icims", "successfactors"]) expect(coverageOf({ site }).level, site).toBe("partial");
  expect(coverageOf({ site: "workday" }).said).toBe("WorkIt fills Workday one step at a time. You sign in and check each step yourself.");
  expect(coverageOf({ site: "lever", practice: true }).said).toBe("WorkIt fills this practice form.");
  expect(coverageOf({ site: null })).toEqual({ level: "none", badge: "Not supported", said: "WorkIt can't fill this site yet. Copy your answers into the form yourself." });
  expect(coverageOf({ site: "workday", off: "Workday" }).said).toBe("WorkIt can't fill Workday right now. Copy your answers into the form yourself.");
});

test("the answers to copy are what the fill would type, without files or self-identification", () => {
  const rows = answerList({ ...STUDENT, location: "Stony Brook, NY" });
  const value = (label: string) => rows.find((row) => row.label === label)?.value;
  expect(value("First name")).toBe("Test");
  expect(value("Last name")).toBe("Person");
  expect(value("Email")).toBe("test.person@example.com");
  expect(value("Phone")).toBe("+1 555 010 0199");
  expect(value("LinkedIn")).toBe("https://www.linkedin.com/in/test-person");
  expect(value("Location")).toBe("Stony Brook, NY");
  expect(value("School")).toBe("Example State University");
  expect(value("Major")).toBe("Computer Science");
  expect(value("GPA")).toBe("3.7 / 4");
  expect(value("Graduation date")).toBe("May 2028");
  expect(value("Authorized to work in the US")).toBe("Yes");
  expect(value("Needs visa sponsorship")).toBe("No");
  // Nothing the student hasn't given, no file and no self-identification.
  expect(value("Website")).toBeUndefined();
  expect(rows.map((row) => row.label)).not.toContain("Gender");
  expect(JSON.stringify(rows)).not.toContain("resume.pdf");
  expect(new Set(rows.map((row) => row.group))).toEqual(new Set(["Contact info", "Location", "Education", "Work authorization"]));
});

test("a category the student switched off in Options is left out of the answers to copy", () => {
  const rows = answerList({ ...STUDENT, location: "Stony Brook, NY" }, ["contact", "work_authorization"]);
  expect(rows.map((row) => row.group)).not.toContain("Contact info");
  expect(rows.map((row) => row.group)).not.toContain("Work authorization");
  expect(rows.find((row) => row.label === "School")?.value).toBe("Example State University");
});
