// The WorkIt extension's own engineProfile and enginePolicies (src/background/engine.js) for each student in a JSON
// file, printed as JSON, for tests/test_engine_profile.py to compare with services/engine_profile.py.
// node engine_profile_parity.mjs <autofiller_extension folder> <students.json> <today, YYYY-MM-DD>
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const [, , extension, input, today] = process.argv;
const { engineProfile, enginePolicies } = await import(pathToFileURL(join(extension, "src", "background", "engine.js")).href);
const students = JSON.parse(readFileSync(input, "utf8"));
console.log(JSON.stringify(students.map((s) => ({ profile: engineProfile(s, today), policies: enginePolicies(s) }))));
