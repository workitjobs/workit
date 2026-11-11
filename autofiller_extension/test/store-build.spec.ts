// The Chrome Web Store package (KAN-463, store/build.mjs): what the Store gets, read back out of the zip itself.
import { execFileSync } from "node:child_process";
import { appendFileSync, cpSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

const EXTENSION = join(__dirname, "..");
let out: string;
let zip: string;

test.beforeAll(() => {
  out = mkdtempSync(join(tmpdir(), "workit-store-build-"));
  execFileSync("node", [join(EXTENSION, "store", "build.mjs"), out]);
  zip = join(out, "workit-extension.zip");
});
test.afterAll(() => rmSync(out, { recursive: true, force: true }));

const files = () => execFileSync("unzip", ["-Z1", zip], { encoding: "utf8" }).trim().split("\n");
const read = (file: string) => execFileSync("unzip", ["-p", zip, file], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

test("no file in the zip names localhost, a Vercel host or the prototype", () => {
  for (const file of files().filter((f) => !f.endsWith("/") && !/\.(png|woff2?)$/.test(f))) {
    const text = read(file);
    expect(text, file).not.toContain("localhost");
    expect(text, file).not.toContain("vercel.app");
    // A word, so the engine's Object.getPrototypeOf is not one.
    expect(text, file).not.toMatch(/\bPrototype\b/);
  }
});

test("the zip holds what Chrome loads and nothing of the repo's own", () => {
  const list = files();
  for (const file of ["manifest.json", "src/background/background.js", "fill-engine/dist/engine.js", "icons/icon-128.png"]) expect(list).toContain(file);
  expect(list.filter((f) => /^(test|store)\/|CLAUDE\.md|README\.md|fill-engine\/(src|test)\//.test(f))).toEqual([]);
});

test("every script in the zip is minified, starts with the copyright notice and has no source map", () => {
  const scripts = files().filter((f) => f.endsWith(".js"));
  expect(scripts.length).toBeGreaterThan(10);
  expect(files().filter((f) => f.endsWith(".map"))).toEqual([]);
  for (const file of scripts) {
    const text = read(file);
    // The copyright notice (store/build.mjs, BANNER) is its first line.
    expect(text, file).toMatch(/^\/\*! WorkIt\. Copyright \(c\) 2026 [^\n]+ \*\/\n/);
    expect(text, file).not.toContain("sourceMappingURL");
    // Minified: no comment line is left (a template string's CSS keeps its own lines, so this, not a line count).
    expect(text, file).not.toMatch(/^\s*\/\/ /m);
  }
  const size = (texts: string[]) => texts.reduce((sum, text) => sum + text.length, 0);
  const dev = size(scripts.map((f) => readFileSync(join(EXTENSION, f), "utf8")));
  expect(size(scripts.map(read))).toBeLessThan(dev * 0.6);
});

test("the engine ships once, minified, and smaller than its readable bundle", () => {
  expect(files().filter((f) => f.startsWith("fill-engine/") && !f.endsWith("/"))).toEqual(["fill-engine/dist/engine.js"]);
  const engine = read("fill-engine/dist/engine.js");
  expect(engine.length).toBeLessThan(readFileSync(join(EXTENSION, "fill-engine", "dist", "engine.js"), "utf8").length * 0.7);
  // What the extension reads from it survives: the global and its version.
  expect(engine).toContain("globalThis.FillEngine=");
});

test("the Store manifest is WorkIt's, at its launch version, with no dev key", () => {
  const manifest = JSON.parse(read("manifest.json"));
  expect(manifest.name).toBe("WorkIt");
  expect(manifest.version).toBe(JSON.parse(readFileSync(join(EXTENSION, "store", "store.json"), "utf8")).version);
  expect(manifest.description.length).toBeLessThanOrEqual(132);
  // The Store signs the item with its own key; its ID is the one the dev manifest's key pins (manifest.json).
  expect(manifest.key).toBeUndefined();
  expect(manifest.host_permissions).toContain("https://api.workitjobs.ai/*");
  expect(manifest.externally_connectable.matches).toEqual(["https://workitjobs.ai/*"]);
});

test("the Store build's config has no dev servers and no test hooks", () => {
  const config = read("src/shared/config.js");
  // Minified: esbuild writes false as !1.
  expect(config).toMatch(/\bDEV_API_URL=null\b/);
  expect(config).toMatch(/\bDEV_WEB_URL=null\b/);
  expect(config).toMatch(/\bTEST_HOOKS=!1\b/);
});

test("the dev manifest is left as it is", () => {
  const manifest = JSON.parse(readFileSync(join(EXTENSION, "manifest.json"), "utf8"));
  expect(manifest.host_permissions).toContain("http://localhost:8000/*");
  expect(manifest.key).toBeTruthy();
});

/** store/build.mjs's perSiteData for the package at `dir`, run as the module it is (it uses import.meta). */
const perSiteData = (dir: string): string[] => JSON.parse(execFileSync("node", ["--input-type=module", "-e",
  `import { perSiteData } from ${JSON.stringify(join(EXTENSION, "store", "build.mjs"))}; console.log(JSON.stringify(perSiteData(process.argv[1])));`, dir], { encoding: "utf8" }));

// The Store engine (KAN-777): no job system's data in the package, which the build itself checks (perSiteData).
test("the packaged engine bundles no job system's data and only the basic answer rules", () => {
  const scope: any = {};
  runInNewContext(read("fill-engine/dist/engine.js"), scope);
  const engine = scope.FillEngine;
  const table = engine.bundledRules();
  const full = JSON.parse(readFileSync(join(EXTENSION, "fill-engine", "dist", "rules-table.json"), "utf8"));
  expect(Object.keys(table.systems).sort()).toEqual(Object.keys(full.systems).sort());
  for (const site of Object.keys(full.systems)) {
    expect(table.systems[site], site).toEqual({});
    expect(engine.supported(site), site).toBe(false);
  }
  expect(table.answers.length).toBeGreaterThan(0);
  expect(table.answers.length).toBeLessThan(full.answers.length);
  expect(table.answers.every((rule: object) => engine.isBasicRule(rule))).toBe(true);
  // The package's engine is not the full one.
  expect(read("fill-engine/dist/engine.js")).not.toContain(full.systems.ashby.strings.SUBMIT);
});

test("the build's check finds a job system's selector in any packaged file", () => {
  const copy = join(out, "leaky");
  cpSync(join(out, "extension"), copy, { recursive: true });
  expect(perSiteData(copy)).toEqual([]);
  const full = JSON.parse(readFileSync(join(EXTENSION, "fill-engine", "dist", "rules-table.json"), "utf8"));
  const selector = full.systems.ashby.strings.SUBMIT;
  appendFileSync(join(copy, "src", "content", "overlay.js"), `\nconst x = ${JSON.stringify(selector)};\n`);
  expect(perSiteData(copy)).toEqual([`src/content/overlay.js holds ashby SUBMIT: ${selector}`]);
});
