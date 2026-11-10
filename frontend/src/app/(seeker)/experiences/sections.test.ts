import assert from "node:assert/strict";
import { test } from "node:test";

import { holdsTools, splitList, TOOL_COMMA, toolsLine } from "./sections.ts";

test("only a project holds tools", () => {
  assert.equal(holdsTools("projects"), true);
  assert.equal(holdsTools("experience"), false);
  assert.equal(holdsTools("education"), false);
});

test("a typed list splits at commas, trimmed, with no empty items", () => {
  assert.deepEqual(splitList(" Algorithms,, Operating Systems ,"), [
    "Algorithms",
    "Operating Systems",
  ]);
});

test("tools keep a comma inside parentheses, as the API splits a typed tools line", () => {
  assert.deepEqual(splitList("Next.js, Supabase (PostgreSQL, pgvector), FastAPI", TOOL_COMMA), [
    "Next.js",
    "Supabase (PostgreSQL, pgvector)",
    "FastAPI",
  ]);
});

test("the tools line is the list as the resume prints it, or nothing", () => {
  assert.equal(toolsLine({ tools: ["Next.js", "TypeScript"] }), "Next.js, TypeScript");
  assert.equal(toolsLine({ tools: [] }), null);
});
