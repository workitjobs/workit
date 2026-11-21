import assert from "node:assert/strict";
import { test } from "node:test";

import type { FeedFilters } from "@/app/(seeker)/jobs/filter-query";

import { ANY_ROLES, previewJobs } from "./preview-jobs.ts";

const NONE: FeedFilters = {
  places: [],
  workStyles: [],
  roles: [],
  customRoles: [],
  levels: [],
  jobTypes: [],
  postedWithin: null,
  minPay: null,
  maxPay: null,
  payPer: "year",
  startTerms: [],
  visa: null,
  autoApply: false,
};

const title = (v: string) => v.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
const labels = { role: title, place: title, jobType: title, workplace: title };
const jobs = (change: Partial<FeedFilters>) => previewJobs({ ...NONE, ...change }, labels);

test("no role picked shows no postings: the panel draws blank cards", () => {
  assert.deepEqual(jobs({}), []);
});

test("a role shows three real employers that hire for it", () => {
  const shown = jobs({ roles: ["data_scientist"] });
  assert.deepEqual(
    shown.map((j) => j.company),
    ["Meta", "Spotify", "Uber"],
  );
  // Each employer's own team, so one role never shows one title three times.
  assert.deepEqual(
    shown.map((j) => j.title),
    ["Data Scientist, Ads", "Data Scientist, Personalization", "Data Scientist, Marketplace"],
  );
});

test("two roles take turns", () => {
  const shown = jobs({ roles: ["software_engineer", "product_designer"] });
  assert.deepEqual(
    shown.map((j) => j.company),
    ["Google", "Figma", "Stripe"],
  );
});

test("a role with no row still shows postings", () => {
  assert.equal(jobs({ roles: ["astronaut"] }).length, 3);
});

test("the job type and level shape the title, and an intern is paid by the hour", () => {
  const intern = jobs({ roles: ["software_engineer"], jobTypes: ["internship"] })[0];
  assert.equal(intern.title, "Software Engineer Intern, Search");
  assert.match(intern.pay, /\/hr$/);
  assert.equal(
    jobs({ roles: ["software_engineer"], levels: ["experienced"] })[0].title,
    "Senior Software Engineer, Search",
  );
  assert.equal(
    jobs({ roles: ["software_engineer"], levels: ["new_grad"] })[0].title,
    "New Grad Software Engineer, Search",
  );
});

test("the workplace and place shape the line under the title", () => {
  assert.equal(jobs({ roles: ["software_engineer"], workStyles: ["remote"] })[0].where, "Remote");
  assert.equal(
    jobs({ roles: ["software_engineer"], workStyles: ["hybrid"], places: ["seattle"] })[0].where,
    "Seattle · Hybrid",
  );
  assert.equal(jobs({ roles: ["software_engineer"] })[0].where, "Mountain View, CA");
});

test("a posting under the minimum pay drops off", () => {
  const all = jobs({ roles: ["software_engineer"] });
  const some = jobs({ roles: ["software_engineer"], minPay: 150_000 });
  assert.equal(all.length, 3);
  assert.deepEqual(
    some.map((j) => j.company),
    ["Google", "Stripe"],
  );
});

test("a role the student typed shows postings under its own name", () => {
  const shown = jobs({ customRoles: ["UX Researcher"] });
  assert.equal(shown.length, 3);
  assert.ok(shown.every((j) => j.title.startsWith("UX Researcher, ")));
  // Beside a listed role, the two take turns.
  assert.deepEqual(
    jobs({ roles: ["data_scientist"], customRoles: ["UX Researcher"] }).map((j) => j.company),
    ["Meta", "Google", "Spotify"],
  );
});

test("a student not sure of their role sees a mix of roles, never an empty list", () => {
  assert.deepEqual(previewJobs(NONE, labels), []);
  const jobs = previewJobs(NONE, labels, 3, true);
  assert.equal(jobs.length, 3);
  // One posting from each of the mix's roles, each with its own employers.
  for (const [i, slug] of ANY_ROLES.entries()) assert.ok(jobs[i].title.startsWith(title(slug)));
});
