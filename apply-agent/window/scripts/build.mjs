// The page's build: type-check, then Vite's one-file build (vite.config.ts). A Node script rather than
// `tsc --noEmit && vite build`, so it runs the same on Windows (root CLAUDE.md, Cross-platform).
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { build } from "vite";

const require = createRequire(import.meta.url);
const tsc = join(dirname(require.resolve("typescript/package.json")), "bin", "tsc");
const checked = spawnSync(process.execPath, [tsc, "--noEmit"], { stdio: "inherit" });
if (checked.status !== 0) process.exit(checked.status ?? 1);
await build();
