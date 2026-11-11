// The Fill engine's own round trip (fill-engine test/rules-table.spec.ts, "plans every research form
// the same"), run on watermarked tables: the built engine plans every saved research form, then loads
// each table and plans them again, and every pattern answers every saved label as the bundled one does.
// Called by tests/test_rules_watermark.py:  node rules_round_trip.mjs <fill-engine dir> <tables.json>
// Prints "ok", or the first difference and exits 1.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [engineDir, tablesPath] = process.argv.slice(2).map((p) => path.resolve(p));
createRequire(import.meta.url)(path.join(engineDir, "dist/engine.js"));
const E = globalThis.FillEngine;
const fixture = (name) => pathToFileURL(path.join(engineDir, "test/fixtures/planner", name)).href;
const { plannerProfile } = await import(fixture("profile.ts"));
const { POLICIES } = await import(fixture("policies.ts"));
const FORMS = JSON.parse(readFileSync(new URL(fixture("research-forms.json")), "utf8"));
const tables = JSON.parse(readFileSync(tablesPath, "utf8"));

// As the engine's spec reads a research form (its KINDS and researchForm).
const KINDS = {
  input_text: "text", textarea: "textarea", input_file: "file", multi_value_single_select: "select", multi_value_multi_select: "multi_select",
  String: "text", Email: "text", Phone: "text", Url: "text", Number: "text", Date: "text", Location: "text", LongText: "textarea",
  File: "file", ValueSelect: "select", Boolean: "select", MultiValueSelect: "multi_select", text: "text", university: "text",
  "file-upload": "file", dropdown: "select", select: "select", "multiple-choice": "select", "multiple-select": "multi_select",
};
function researchForm(form) {
  const questions = [];
  form.questions.forEach((q, i) => {
    const kind = q.type === "std:resume" ? "file" : q.type.startsWith("std:") ? "text" : KINDS[q.type];
    if (kind) questions.push({ name: `q${i}`, label: q.label, kind, required: q.required, options: q.type === "Boolean" ? ["Yes", "No"] : q.options ?? [] });
  });
  return [questions, { id: form.company, company: form.company, title: form.title, url: form.url }];
}
const planAll = () => JSON.stringify(FORMS.map((form) => {
  const [questions, posting] = researchForm(form);
  return E.plan(questions, plannerProfile(), POLICIES, null, { posting, today: "2026-11-10" });
}));

const fail = (message) => { console.log(message); process.exit(1); };
const bundled = E.bundledRules();
const before = planAll();
const labels = FORMS.flatMap((f) => f.questions.flatMap((q) => [q.label, q.label.toLowerCase(), ...(q.options ?? [])]));
const same = (a, b, where) => {
  const [x, y] = [new RegExp(a.source, a.flags), new RegExp(b.source, b.flags)];
  for (const s of labels) if (JSON.stringify(x.exec(s)) !== JSON.stringify(y.exec(s))) fail(`${where}: ${a.source} and ${b.source} differ on ${JSON.stringify(s)}`);
};

for (const table of tables) {
  table.answers.forEach((r, i) => same(bundled.answers[i].pattern, r.pattern, `answers[${i}]`));
  for (const [site, data] of Object.entries(table.systems)) {
    for (const [name, p] of Object.entries(data.patterns ?? {})) same(bundled.systems[site].patterns[name], p, `${site}.${name}`);
  }
  E.loadRules(table); // throws a RulesError on anything the engine refuses
  if (planAll() !== before) fail(`plans differ with the table for ${Object.keys(table.systems)}`);
  E.loadRules({ version: 1 });
}
console.log("ok");
