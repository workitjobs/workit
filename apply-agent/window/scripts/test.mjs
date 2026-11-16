// The window's tests: every src/**/*.test.ts, through Node's own runner with its TypeScript stripping, as the
// website's are. The files are listed here, not by a quoted glob, so it runs the same on Windows (root CLAUDE.md,
// Cross-platform).
import { spawnSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { join } from "node:path";

const tests = readdirSync("src", { recursive: true })
  .filter((file) => file.endsWith(".test.ts"))
  .map((file) => join("src", file));
const ran = spawnSync(process.execPath, ["--experimental-strip-types", "--test", ...tests], { stdio: "inherit" });
process.exit(ran.status ?? 1);
