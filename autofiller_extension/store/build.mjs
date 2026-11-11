#!/usr/bin/env node
// The Chrome Web Store package (KAN-463): the checked-in dev extension, minus everything that is only for
// development. `node autofiller_extension/store/build.mjs [outDir]` writes <outDir>/extension/ (the
// package, unpacked) and <outDir>/workit-extension.zip, and fails if any packaged file still names
// localhost, a Vercel host or "Prototype". outDir defaults to autofiller_extension/.store-build/.
//
// - manifest.json: store.json's name, version, description and toolbar title; no localhost or Vercel
//   host in host_permissions or externally_connectable; no `key` (the Store signs with its own, and
//   the dev `key` is the Store item's public key, so both have one ID: CLAUDE.md, "Extension ID").
// - src/shared/config.js: DEV_API_URL and DEV_WEB_URL null (never probe or call localhost), the
//   Vercel site gone (KAN-296), TEST_HOOKS false (no hooks on the service worker's global).
//
// - every .js file: minified by esbuild (KAN-744), no source map, and BANNER, the copyright notice, as
//   its first line. The engine ships only as its minified dist/engine.js.
// - the engine is the Store bundle (fill-engine's dist/engine.store.js, KAN-777): its code with no job
//   system's data and only the basic answer rules. Every site's selectors, patterns, kinds and timeouts
//   come from the API's Rules table; without it the extension does a basic fill. The build fails if any
//   per-site data is in the package (`perSiteData`). The dev extension and its tests keep the full bundle.
//
// The dev manifest and config stay as they are, for the tests. KAN-447's publish workflow uploads
// this zip rather than packaging the folder itself. Needs `zip` (macOS and ubuntu-latest have it) and
// esbuild (`npm ci --prefix store` from autofiller_extension/).
import { execFileSync } from "node:child_process";
import { transform } from "esbuild";
import { cpSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";

const EXTENSION = resolve(dirname(fileURLToPath(import.meta.url)), "..");
/** What Chrome loads, each [from, to]: never test/, store/, the docs, or the engine's source. Of the
 *  engine's dist/ only the Store bundle, as engine.js: rules-table.json is for the API to serve (KAN-756),
 *  and the full engine.js bundles every job system's data, so neither is ever packaged. */
const PARTS = [["manifest.json"], ["icons"], ["fonts"], ["src"], ["fill-engine/dist/engine.store.js", "fill-engine/dist/engine.js"]];
/** The full Rules table, outside the package: what `perSiteData` looks for in it. */
const FULL_TABLE = join(EXTENSION, "fill-engine", "dist", "rules-table.json");
/** The extension's own scripts that still carry a job system's table values (the stepped systems' walk:
 *  Workday, Oracle, iCIMS, SuccessFactors; Workable's and TikTok's checks in the background), by file:
 *  tolerated there only, until KAN-778 reads them from the served table. Any other is a leak. */
const KNOWN = JSON.parse(readFileSync(join(EXTENSION, "store", "extension-site-data.json"), "utf8"));
/** Job systems' table values that are also the engine's own generic code: label patterns any form's
 *  labels may carry (a phone format "###-###-####", a label ending "(required)"). */
const GENERIC = new Set([String.raw`(?:\(#{3}\) ?|#{3}[-. ]?)#{3}[-. ]?#{4}`, String.raw`\s*\(required\)$`]);
const DEV_ONLY = /localhost|vercel\.app/;
/** What no packaged file may contain. "Prototype" as a word: the engine's Object.getPrototypeOf is fine. */
export const FORBIDDEN = /localhost|vercel\.app|\bPrototype\b/;
/** The first line of every packaged script. The holders are the repo's LICENSE line. */
export const BANNER = "/*! WorkIt. Copyright (c) 2026 Xiang Liu, Brian Cao, Andrew Shi, Lisul Elvitigala, Vedant Vyas. */";

/** One packaged script, minified, with no source map. No `format`, so esbuild keeps a classic script's
 *  top-level names (the content scripts share them through `window.WIA`) and a module's imports and
 *  exports (it renames a module's other names); no `target`, so it lowers no syntax and adds no helper
 *  an `executeScript` `func` would lack. A bundled `/*!` licence comment moves to the file's end. */
async function minify(file) {
  const { code } = await transform(readFileSync(file, "utf8"), { minify: true, legalComments: "eof", sourcemap: false, banner: BANNER });
  writeFileSync(file, code);
}

/** The Store manifest from the dev one. */
export function storeManifest(dev, store) {
  const manifest = structuredClone(dev);
  delete manifest.key;
  manifest.name = store.name;
  manifest.version = store.version;
  manifest.description = store.description;
  manifest.action.default_title = store.default_title;
  manifest.host_permissions = manifest.host_permissions.filter((host) => !DEV_ONLY.test(host));
  manifest.externally_connectable.matches = manifest.externally_connectable.matches.filter((host) => !DEV_ONLY.test(host));
  return manifest;
}

/** The Store config.js from the dev one; throws if a line it rewrites has changed shape. */
export function storeConfig(dev) {
  let config = dev;
  const swap = (pattern, to) => {
    if (!pattern.test(config)) throw new Error(`config.js no longer matches ${pattern}: update store/build.mjs`);
    config = config.replace(pattern, to);
  };
  swap(/^export const DEV_API_URL = .*;$/m, "export const DEV_API_URL = null;");
  swap(/^export const DEV_WEB_URL = .*;$/m, "export const DEV_WEB_URL = null;");
  swap(/^export const TEST_HOOKS = .*;$/m, "export const TEST_HOOKS = false;");
  swap(/^.*vercel\.app.*\n/m, "");
  return config;
}

/** Every file under `dir`, relative to it. */
function walk(dir, root = dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path, root) : [relative(root, path)];
  });
}

/**
 * What of the job systems' data the package at `dir` holds, as lines (none: it holds none). Its engine,
 * run on its own, must bundle no site's data and only basic answer rules, and no packaged file may hold
 * a selector, wording or pattern of the full table that looks like one (8 characters or more, with one
 * of . # [ = > : \ or a parenthesis), other than GENERIC's and the extension's own KNOWN ones (KAN-778).
 */
export function perSiteData(dir) {
  const leaks = [];
  const scope = {};
  runInNewContext(readFileSync(join(dir, "fill-engine", "dist", "engine.js"), "utf8"), scope);
  const engine = scope.FillEngine;
  const shipped = engine.bundledRules();
  for (const [site, data] of Object.entries(shipped.systems ?? {})) if (Object.keys(data).length) leaks.push(`the engine bundles ${site}'s data`);
  for (const rule of shipped.answers ?? []) if (!engine.isBasicRule(rule)) leaks.push(`the engine bundles the answer rule /${rule.pattern.source}/ (${rule.value})`);
  const full = JSON.parse(readFileSync(FULL_TABLE, "utf8"));
  const values = Object.entries(full.systems).flatMap(([site, data]) => [
    ...Object.entries(data.strings ?? {}).map(([name, value]) => [`${site} ${name}`, value]),
    ...Object.entries(data.patterns ?? {}).map(([name, value]) => [`${site} ${name}`, value.source]),
  ]).filter(([, value]) => value.length >= 8 && /[.#[=>:\\(]/.test(value) && !GENERIC.has(value));
  for (const file of walk(dir).filter((f) => !/\.(png|woff2?)$/.test(f))) {
    const text = readFileSync(join(dir, file), "utf8");
    for (const [name, value] of values) {
      if (KNOWN[file]?.includes(name)) continue;
      if (text.includes(value) || text.includes(JSON.stringify(value).slice(1, -1))) leaks.push(`${file} holds ${name}: ${value}`);
    }
  }
  return leaks;
}

export async function build(out = join(EXTENSION, ".store-build")) {
  const dir = join(out, "extension");
  const zip = join(out, "workit-extension.zip");
  rmSync(dir, { recursive: true, force: true });
  rmSync(zip, { force: true });
  mkdirSync(dir, { recursive: true });
  for (const [from, to = from] of PARTS) cpSync(join(EXTENSION, from), join(dir, to), { recursive: true });

  const store = JSON.parse(readFileSync(join(EXTENSION, "store", "store.json"), "utf8"));
  const manifest = storeManifest(JSON.parse(readFileSync(join(EXTENSION, "manifest.json"), "utf8")), store);
  writeFileSync(join(dir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  const config = join(dir, "src", "shared", "config.js");
  writeFileSync(config, storeConfig(readFileSync(config, "utf8")));

  for (const file of walk(dir).filter((f) => f.endsWith(".js"))) await minify(join(dir, file));

  const found = walk(dir)
    .filter((file) => !/\.(png|woff2?)$/.test(file))
    .filter((file) => FORBIDDEN.test(readFileSync(join(dir, file), "utf8")));
  if (found.length) throw new Error(`The Store package still names localhost, vercel.app or Prototype in: ${found.join(", ")}`);
  const leaks = perSiteData(dir);
  if (leaks.length) throw new Error(`The Store package holds job systems' data:\n${leaks.join("\n")}`);

  execFileSync("zip", ["-qrX", zip, "."], { cwd: dir });
  return { dir, zip };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const { zip } = await build(process.argv[2] ? resolve(process.argv[2]) : undefined);
    console.log(zip);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
