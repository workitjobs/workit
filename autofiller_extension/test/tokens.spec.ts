// The extension's design tokens (src/shared/tokens.js) are WorkIt's own, copied from the frontend's globals.css.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

const read = (...path: string[]) => readFileSync(join(__dirname, "..", ...path), "utf8");

/** Every `--name: value;` in a stylesheet's text, comments dropped; the first one of a name wins. */
function properties(css: string): Map<string, string> {
  const found = new Map<string, string>();
  for (const [, name, value] of css.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    if (!found.has(name)) found.set(name, value.trim());
  }
  return found;
}

/** A globals.css value as the extension writes it: rem in px (16px to the rem). */
const inPx = (value: string) => value.replace(/(\d*\.?\d+)rem\b/g, (_, n) => `${Number(n) * 16}px`);

const JAKARTA_WEIGHTS = new Set(["--font-weight-normal", "--text-label--font-weight"]);

test("the extension's tokens have globals.css's values", () => {
  const theirs = properties(read("..", "frontend", "src", "app", "globals.css"));
  const ours = properties(read("src", "shared", "tokens.js"));
  expect(ours.size).toBeGreaterThan(20);
  for (const [name, value] of ours) {
    // The font is the frontend's next/font variable there; here, the shipped file's family.
    if (name === "--font-sans") continue;
    // The weights are set for a face: the app's are Inter's since 2026-11-10 (400 regular, 450 medium), and the
    // extension still ships Plus Jakarta Sans, whose 400 reads thin (KAN-365), so it keeps that face's 450 and 500.
    // Checked again once the extension ships Inter.
    if (JAKARTA_WEIGHTS.has(name) && ours.get("--font-sans")!.includes("Jakarta")) continue;
    expect(theirs.has(name), `${name} is not a globals.css token`).toBe(true);
    expect(value, name).toBe(inPx(theirs.get(name)!));
  }
});
