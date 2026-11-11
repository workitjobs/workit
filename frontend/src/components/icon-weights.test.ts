import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import ts from "typescript";

import loader from "../../scripts/phosphor-weights-loader.cjs";
import { ICON_WEIGHTS } from "./icon-weights.ts";

const SRC = fileURLToPath(new URL("..", import.meta.url));
const DEFS = fileURLToPath(
  new URL("../../node_modules/@phosphor-icons/react/dist/defs/", import.meta.url),
);

/**
 * Glyphs drawn at a weight through a variable, which the scan cannot follow:
 * `"<file under src/> <Tag>"` to the Phosphor glyphs the tag can be. A new
 * one fails the test until it is listed here and its glyphs in
 * icon-weights.ts.
 */
const INDIRECT: Record<string, string[]> = {
  // Play or Pause, by state.
  "app/(landing)/motion-toggle.tsx <Icon>": ["Play", "Pause"],
  // SECTION_ICONS, every group's mark.
  "app/(seeker)/experiences/section-icons.tsx <Glyph>": [
    "Briefcase",
    "Certificate",
    "GraduationCap",
    "ListBullets",
    "RocketLaunch",
    "Trophy",
    "UsersThree",
    "Wrench",
  ],
  // KINDS, a change's type.
  "app/(seeker)/jobs/[jobId]/tailor/tailor-suggestions.tsx <Icon>": [
    "ArrowsDownUp",
    "Minus",
    "PencilSimple",
    "Plus",
  ],
};

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(entry.name) && !entry.name.endsWith(".test.ts") ? [path] : [];
  });
}

/** Every weight each Phosphor glyph is drawn at in src/, regular left out. */
function weightsInUse() {
  const used = new Map<string, Set<string>>();
  const unresolved: string[] = [];
  const indirectSeen = new Set<string>();
  const note = (glyph: string, weight: string) => {
    if (weight === "regular") return;
    if (!used.has(weight)) used.set(weight, new Set());
    used.get(weight)!.add(glyph);
  };

  for (const file of sourceFiles(SRC)) {
    const text = readFileSync(file, "utf8");
    if (!text.includes("weight")) continue;
    const name = relative(SRC, file).split(sep).join("/");
    const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

    // Local name to Phosphor glyph, and the names a custom-icons file draws.
    const phosphor = new Map<string, string>();
    const custom = new Set<string>();
    for (const statement of source.statements) {
      if (!ts.isImportDeclaration(statement)) continue;
      const from = (statement.moduleSpecifier as ts.StringLiteral).text;
      const bindings = statement.importClause?.namedBindings;
      if (!bindings || !ts.isNamedImports(bindings)) continue;
      for (const element of bindings.elements) {
        const imported = (element.propertyName ?? element.name).text;
        if (from === "@phosphor-icons/react/ssr") {
          phosphor.set(element.name.text, imported.replace(/Icon$/, ""));
        } else if (from.endsWith("custom-icons")) custom.add(element.name.text);
      }
    }

    const visit = (node: ts.Node) => {
      if (ts.isJsxSelfClosingElement(node) || ts.isJsxOpeningElement(node)) {
        const attribute = node.attributes.properties.find(
          (p) => ts.isJsxAttribute(p) && p.name.getText(source) === "weight",
        );
        if (attribute) {
          const weights: string[] = [];
          const collect = (n: ts.Node) => {
            if (ts.isStringLiteral(n)) weights.push(n.text);
            ts.forEachChild(n, collect);
          };
          collect(attribute);
          const tag = node.tagName.getText(source);
          const key = `${name} <${tag}>`;
          const glyphs = phosphor.has(tag) ? [phosphor.get(tag)!] : INDIRECT[key];
          if (glyphs) {
            if (!phosphor.has(tag)) indirectSeen.add(key);
            for (const glyph of glyphs) for (const weight of weights) note(glyph, weight);
          } else if (!custom.has(tag)) {
            const line = source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1;
            unresolved.push(`${name}:${line} <${tag}>`);
          }
        }
      }
      ts.forEachChild(node, visit);
    };
    visit(source);
  }
  return { used, unresolved, indirectSeen };
}

test("every weight drawn is kept, and nothing else", () => {
  const { used, unresolved, indirectSeen } = weightsInUse();
  assert.deepEqual(
    unresolved,
    [],
    "A weight is set on a tag the scan cannot trace to a Phosphor glyph: list it in INDIRECT",
  );
  assert.deepEqual(
    Object.keys(INDIRECT).filter((key) => !indirectSeen.has(key)),
    [],
    "An INDIRECT entry no longer sets a weight: remove it",
  );
  const kept = Object.fromEntries(
    Object.entries(ICON_WEIGHTS).map(([weight, glyphs]) => [weight, [...glyphs].sort()]),
  );
  const drawn = Object.fromEntries(
    Object.keys(ICON_WEIGHTS).map((weight) => [weight, [...(used.get(weight) ?? [])].sort()]),
  );
  assert.deepEqual(
    drawn,
    kept,
    "icon-weights.ts must name exactly the glyphs drawn at each weight",
  );
  const other = [...used.keys()].filter((weight) => !(weight in ICON_WEIGHTS));
  assert.deepEqual(other, [], "light and thin are never kept: draw another weight");
});

test("every glyph named is one of Phosphor's", () => {
  const missing = Object.values(ICON_WEIGHTS)
    .flat()
    .filter((glyph) => !existsSync(join(DEFS, `${glyph}.es.js`)));
  assert.deepEqual(missing, []);
});

test("the loader keeps regular and the named weights, as valid code", () => {
  const source = readFileSync(join(DEFS, "X.es.js"), "utf8");
  const out = loader.stripWeights(source, "X", ["bold"]);
  const weights = [...out.matchAll(/^ {4}"(\w+)",$/gm)].map((m) => m[1]);
  assert.deepEqual(weights, ["bold", "regular"]);
  const { diagnostics } = ts.transpileModule(out, { reportDiagnostics: true });
  assert.deepEqual(diagnostics, []);
  assert.ok(out.length < source.length / 2);
});

test("the loader stops the build on a table it cannot read", () => {
  assert.throws(
    () => loader.stripWeights("export default new Map([]);", "X", []),
    /layout changed/,
  );
});
