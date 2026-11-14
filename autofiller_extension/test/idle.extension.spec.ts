// No work on pages that aren't job forms (KAN-749). The manifest's content
// script runs on every page of the job systems' hosts, most of which are no
// form: Greenhouse's own site, a Workday tenant's search, a board's list. There
// only launcher.js runs: one wait for the page's load, one panel/where to the
// worker, and nothing more. The panel's files, their observers and listeners
// load only once the worker says the page is a job system's (panel/shell).
// Measured in the content scripts' own isolated world (loaded-extension.ts
// PROBE) and by the extension scripts Chrome parsed in the page (CDP).
import { expect, test, type Page } from "@playwright/test";
import { FakeApi } from "./fake-api";
import { SavedForms } from "./fake-job-systems";
import { loadExtension, probeOf, signIn, webapp, type Handler, type Loaded } from "./loaded-extension";

const ANDURIL = "greenhouse-anduril";
// A page on Greenhouse's host that is no job form, with frames of the same host (the content script runs in every frame).
const ABOUT = "https://www.greenhouse.io/about";
const about: Handler = ({ url }) => {
  if (url.host !== "www.greenhouse.io") return undefined;
  const page = url.pathname === "/about"
    ? "<!doctype html><title>About</title><h1>About Greenhouse</h1><form><input name=q></form><iframe src=/frame></iframe><iframe src=/frame></iframe>"
    : "<!doctype html><title>Frame</title><p>A frame.";
  return { headers: { "content-type": "text/html" }, body: page };
};

let loaded: Loaded;
test.afterEach(() => loaded?.close());

/** The extension's files Chrome parsed in `page`'s frames from now on (CDP's Debugger.scriptParsed). */
async function extensionScripts(page: Page): Promise<string[]> {
  const parsed: string[] = [];
  const cdp = await page.context().newCDPSession(page);
  cdp.on("Debugger.scriptParsed", ({ url }) => {
    if (url.startsWith("chrome-extension://")) parsed.push(new URL(url).pathname.slice(1));
  });
  await cdp.send("Debugger.enable");
  return parsed;
}

async function start(): Promise<SavedForms> {
  const forms = new SavedForms([ANDURIL]);
  loaded = await loadExtension([new FakeApi().handler, webapp, forms.handler, about], { probe: true });
  await signIn(loaded.context);
  return forms;
}

test("a job system's page that is no form runs only the launcher: no panel files, observers or listeners", async () => {
  await start();
  const page = await loaded.context.newPage();
  const parsed = await extensionScripts(page);
  await page.goto(ABOUT);
  await page.waitForTimeout(4000);

  const probe = await probeOf(loaded, ABOUT);
  console.log(`[idle] ${ABOUT}: ${JSON.stringify(probe)}; parsed ${parsed.length}: ${[...new Set(parsed)].join(", ")}`);
  expect(probe.observers).toBe(0);
  expect(probe.intervals).toBe(0);
  // The launcher's wait for the page's load and its one second after it.
  expect(probe.listeners).toBeLessThanOrEqual(1);
  expect(probe.timeouts).toBeLessThanOrEqual(1);
  expect(probe.messages).toEqual(["panel/where"]);
  expect(probe.globals).toEqual(["launched"]);
  // The launcher alone, in each of the three frames, and no panel drawn.
  expect(parsed.filter((file) => file !== "test-probe.js")).toEqual(["src/content/launcher.js", "src/content/launcher.js", "src/content/launcher.js"]);
  await expect(page.locator("#workit-autofiller-overlay-host")).toHaveCount(0);
});

test("a job form still gets the panel's files, and its edge tab", async () => {
  const forms = await start();
  const page = await loaded.context.newPage();
  const parsed = await extensionScripts(page);
  await page.goto(forms.url(ANDURIL));
  await expect(page.locator("#workit-autofiller-overlay-host").getByRole("button", { name: "Show WorkIt panel" })).toBeVisible({ timeout: 15_000 });

  const probe = await probeOf(loaded, forms.url(ANDURIL));
  console.log(`[idle] ${forms.url(ANDURIL)}: observers ${probe.observers}, listeners ${probe.listeners}; parsed ${parsed.length}`);
  expect(probe.globals).toEqual(expect.arrayContaining(["panel", "panelStates", "ui"]));
  expect(parsed).toEqual(expect.arrayContaining(["src/content/launcher.js", "src/content/panel.js", "src/content/panel-states.js"]));
  expect(forms.submissions).toEqual([]);
});
