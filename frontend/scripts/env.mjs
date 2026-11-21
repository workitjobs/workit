// `npm run env`: the root .env and frontend/.env from Infisical's workit-dev
// project (docs/secrets.md, "Get your local .env files"). Plain Node so it
// behaves the same on macOS and Windows.
//
// - It needs the Infisical CLI, signed in as yourself (`infisical login`).
// - Each file gets every key of its folder, then the lines Infisical does
//   not have (LOCAL_FILES_DIR, anything only this computer needs), kept as
//   they were under a comment at the end. A key Infisical has always takes
//   Infisical's value.
// - It prints key names, never a value.
// - It pulls both folders before it writes either, and a failed or empty
//   pull writes nothing, so a bad pull never wipes a working file.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// workit-dev's ID, from the project's settings in Infisical. Not a secret:
// reading a value needs an Infisical login with access to the project.
const PROJECT_ID = "99db2e5f-640f-43c0-9092-952a418ce225";

const FILES = [
  { file: ".env", folder: "/root_env" },
  { file: join("frontend", ".env"), folder: "/frontend_env" },
];

// Next reads frontend/.env.local over frontend/.env, so a key there hides
// the value just pulled.
const SHADOW = join("frontend", ".env.local");

const KEPT = "# Only on this computer: Infisical does not have these, so npm run env keeps them.";

const KEY = /^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$/;

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

function fail(message) {
  console.error(message);
  process.exit(1);
}

// The KEY=value entries of a dotenv text, each with its lines as written.
// A quoted value with no closing quote on its first line runs on to the line
// that has one (a PEM key). Comments and other lines are not entries.
function entries(text) {
  const found = [];
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const match = KEY.exec(lines[i]);
    if (!match) continue;
    const block = [lines[i]];
    const value = match[2].trim();
    const quote = value[0];
    if (["'", '"', "`"].includes(quote) && value.indexOf(quote, 1) === -1) {
      while (i + 1 < lines.length) {
        block.push(lines[++i]);
        if (lines[i].includes(quote)) break;
      }
    }
    found.push({ key: match[1], text: block.join("\n"), value: bare(value, block) });
  }
  return found;
}

// A value without its quotes, so KEY=x and KEY='x' read as the same value.
function bare(value, block) {
  if (block.length > 1) return block.join("\n");
  const quote = value[0];
  return ["'", '"', "`"].includes(quote) && value.endsWith(quote) && value.length > 1
    ? value.slice(1, -1)
    : value;
}

function pull(folder) {
  const args = [
    "export",
    "--projectId",
    PROJECT_ID,
    "--env",
    "dev",
    "--path",
    folder,
    "--format",
    "dotenv",
  ];
  const run = spawnSync("infisical", args, { cwd: root, encoding: "utf8" });
  if (run.error?.code === "ENOENT") {
    fail(
      "The Infisical CLI is not installed. On macOS: brew install infisical/get-cli/infisical." +
        " On Windows: winget install infisical. Then run infisical login (docs/secrets.md).",
    );
  }
  if (run.error) fail(`infisical could not run: ${run.error.message}`);
  if (run.status !== 0) {
    fail(
      `Infisical refused workit-dev ${folder}, so nothing was written:\n${run.stderr.trim()}\n` +
        "Not signed in? Run infisical login. No access? Ask an Admin to add you to workit-dev (docs/secrets.md).",
    );
  }
  const pulled = entries(run.stdout);
  if (pulled.length === 0)
    fail(`Infisical sent no keys for workit-dev ${folder}, so nothing was written.`);
  return pulled;
}

function names(list) {
  return list.length ? list.join(", ") : "none";
}

const pulls = FILES.map(({ file, folder }) => ({ file, folder, pulled: pull(folder) }));

for (const { file, folder, pulled } of pulls) {
  const path = join(root, file);
  const current = existsSync(path) ? entries(readFileSync(path, "utf8")) : [];
  const had = new Map(current.map((e) => [e.key, e.value]));
  const keys = new Set(pulled.map((e) => e.key));
  const kept = current.filter((e) => !keys.has(e.key));

  let text = pulled.map((e) => e.text).join("\n") + "\n";
  if (kept.length) text += `\n${KEPT}\n${kept.map((e) => e.text).join("\n")}\n`;
  writeFileSync(path, text);

  const added = pulled.filter((e) => !had.has(e.key)).map((e) => e.key);
  const changed = pulled
    .filter((e) => had.has(e.key) && had.get(e.key) !== e.value)
    .map((e) => e.key);
  console.log(`${file}: ${pulled.length} keys from workit-dev ${folder}.`);
  console.log(
    `  New: ${names(added)}. Changed: ${names(changed)}. Kept from this computer: ${names(kept.map((e) => e.key))}.`,
  );
}

const shadow = join(root, SHADOW);
if (existsSync(shadow)) {
  const pulled = new Set(pulls[1].pulled.map((e) => e.key));
  const hidden = entries(readFileSync(shadow, "utf8"))
    .filter((e) => pulled.has(e.key))
    .map((e) => e.key);
  if (hidden.length) {
    console.warn(
      `${SHADOW} also sets ${hidden.join(", ")}, and Next reads it over frontend/.env.` +
        " Delete those lines there, or the app keeps the old values.",
    );
  }
}
