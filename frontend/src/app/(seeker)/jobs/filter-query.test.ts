import assert from "node:assert/strict";
import { test } from "node:test";

import {
  facetsOn,
  payUnits,
  filtersFromPreferences,
  filtersQuery,
  NO_FILTERS,
  preferencesBody,
  readFilters,
  roleOptions,
  roleValues,
  splitRoleValues,
  tidyCustomRoles,
} from "./filter-query.ts";

test("no picks count none", () => {
  assert.equal(facetsOn(NO_FILTERS), 0);
});

test("a facet counts once, whatever it holds", () => {
  assert.equal(facetsOn({ ...NO_FILTERS, places: ["US-CA", "US-NY"], roles: ["designer"] }), 2);
});

test("salary is one facet, either end of it", () => {
  assert.equal(facetsOn({ ...NO_FILTERS, minPay: 30 }), 1);
  assert.equal(facetsOn({ ...NO_FILTERS, minPay: 30, maxPay: 50 }), 1);
});

test("the panel's own facets count too", () => {
  assert.equal(
    facetsOn({
      ...NO_FILTERS,
      postedWithin: 7,
      startTerms: ["summer-2027"],
      visa: "sponsors",
      autoApply: true,
    }),
    4,
  );
});

test("a custom role is one Role filter with the picked roles", () => {
  assert.equal(facetsOn({ ...NO_FILTERS, roles: ["designer"], customRoles: ["UX Researcher"] }), 1);
  assert.equal(facetsOn({ ...NO_FILTERS, customRoles: ["UX Researcher"] }), 1);
});

test("custom roles are kept as the API takes them", () => {
  assert.deepEqual(
    tidyCustomRoles([
      " UX Researcher ",
      "ux researcher",
      "x",
      "--",
      "a".repeat(61),
      "Game Designer",
    ]),
    ["UX Researcher", "Game Designer"],
  );
  assert.equal(
    tidyCustomRoles(["Role A", "Role B", "Role C", "Role D", "Role E", "Role F"]).length,
    5,
  );
});

test("custom roles round-trip through the address and the saved preferences", () => {
  const filters = { ...NO_FILTERS, roles: ["software_engineer"], customRoles: ["UX Researcher"] };
  const query = filtersQuery(filters);
  assert.equal(query, "?role=software_engineer&custom_role=UX+Researcher");
  const params: Record<string, string[]> = {};
  for (const [k, v] of new URLSearchParams(query)) (params[k] ??= []).push(v);
  assert.deepEqual(readFilters(params).customRoles, ["UX Researcher"]);
  assert.deepEqual(preferencesBody(filters).custom_role, ["UX Researcher"]);
  assert.deepEqual(filtersFromPreferences(preferencesBody(filters)).customRoles, ["UX Researcher"]);
  // None typed: the key is left out, so an older API still takes the body.
  assert.equal("custom_role" in preferencesBody(NO_FILTERS), false);
});

test("a Role picker holds custom roles beside the slugs and gives them back", () => {
  const values = roleValues({ roles: ["software_engineer"], customRoles: ["UX Researcher"] });
  assert.deepEqual(values, ["software_engineer", "custom:UX Researcher"]);
  assert.deepEqual(
    roleOptions(
      [{ value: "software_engineer", label: "Software Engineer" }],
      ["UX Researcher"],
    ).map((o) => o.label),
    ["UX Researcher", "Software Engineer"],
  );
  assert.deepEqual(splitRoleValues(values), {
    roles: ["software_engineer"],
    customRoles: ["UX Researcher"],
  });
});

test("each job type offers the pay units it is paid in, and a mix offers all of them", () => {
  assert.deepEqual(payUnits([]), ["hour", "year"]);
  assert.deepEqual(payUnits(["internship"]), ["hour"]);
  assert.deepEqual(payUnits(["part_time"]), ["hour"]);
  assert.deepEqual(payUnits(["internship", "part_time"]), ["hour"]);
  assert.deepEqual(payUnits(["full_time"]), ["year"]);
  assert.deepEqual(payUnits(["contract"]), ["hour", "year"]);
  assert.deepEqual(payUnits(["internship", "full_time"]), ["hour", "year"]);
  assert.deepEqual(payUnits(["full_time", "part_time"]), ["hour", "year"]);
});
