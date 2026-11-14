// The Store build (KAN-463, store/build.mjs) loaded into Chromium, as a student installs it: it talks only
// to WorkIt's deployed site and API, even with something answering on localhost:8000 as the dev API does
// (a student's own FastAPI app, say), and the deployed site's ping and Start batch still reach it and fill.
// Its engine ships no job system's data (KAN-777): it fills a job system fully with the API's Rules table,
// and without it does a basic fill that the panel names.
import { execFileSync } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium, expect, test, type BrowserContext, type Page } from "@playwright/test";
import { FakeApi } from "./fake-api";
import { SavedForms } from "./fake-job-systems";
import { SESSION_COOKIE, sessionCookie, startFakeNet, type FakeNet, type Handler } from "./loaded-extension";

const ANDURIL = "greenhouse-anduril";
let out: string;
let net: FakeNet;
let context: BrowserContext;
let profile: string;

test.beforeAll(() => {
  out = mkdtempSync(join(tmpdir(), "workit-store-build-"));
  execFileSync("node", [join(__dirname, "..", "store", "build.mjs"), out]);
  // A copy whose panel's shadow root is open, for the locators that read it (the student's stays closed).
  cpSync(join(out, "extension"), join(out, "open"), { recursive: true });
  const panel = join(out, "open", "src", "content", "panel.js");
  const source = readFileSync(panel, "utf8");
  if (!source.includes('attachShadow({mode:"closed"})')) throw new Error("the Store panel no longer attaches a closed root: update this test");
  writeFileSync(panel, source.replace('attachShadow({mode:"closed"})', 'attachShadow({mode:"open"})'));
});
/** The full Rules table's answers and one job system's data, as the API serves it: the copy kept outside the Store package. */
const served = (site: string) => {
  const full = JSON.parse(readFileSync(join(__dirname, "..", "fill-engine", "dist", "rules-table.json"), "utf8"));
  return { version: full.version, answers: full.answers, systems: { [site]: full.systems[site] } };
};
test.afterEach(async () => {
  await context?.close();
  net?.close();
  if (profile) rmSync(profile, { recursive: true, force: true });
});
test.afterAll(() => rmSync(out, { recursive: true, force: true }));

/** The fake API, answering on WorkIt's deployed API host instead of localhost:8000. */
const deployed = (api: FakeApi): Handler => (request) =>
  request.url.host === "api.workitjobs.ai" ? api.handler({ ...request, url: new URL(`${request.url.pathname}${request.url.search}`, "http://localhost:8000") }) : undefined;
/** What answers on localhost:8000: anything at all, /health included. */
const localApp: Handler = ({ url }) => (url.host === "localhost:8000" ? { json: { status: "ok" } } : undefined);
const site: Handler = ({ url }) =>
  url.host === "workitjobs.ai" ? { headers: { "content-type": "text/html" }, body: "<!doctype html><title>WorkIt</title><p>WorkIt" } : undefined;

async function loadStoreBuild(handlers: Handler[], copy = "extension"): Promise<{ id: string; page: Page }> {
  net = await startFakeNet(handlers, join(out, copy));
  profile = mkdtempSync(join(tmpdir(), "workit-extension-"));
  context = await chromium.launchPersistentContext(profile, { channel: "chromium", headless: true, args: net.args });
  const worker = context.serviceWorkers()[0] ?? (await context.waitForEvent("serviceworker"));
  // The deployed site's session cookie: the same token shape FakeApi's default `token` expects
  // (tokenFor's base64url {sub}), not an arbitrary string -- a plain placeholder here 401s every
  // real API call (FakeApi logs a call before checking auth, so the ping test's api.calls.length
  // check never caught it; run/open actually needs the calls to succeed).
  await context.addCookies([{ name: SESSION_COOKIE, value: sessionCookie(), url: "https://workitjobs.ai/" }]);
  const page = await context.newPage();
  await page.goto("https://workitjobs.ai/onboarding");
  return { id: new URL(worker.url()).host, page };
}

const send = (page: Page, id: string, message: unknown) =>
  page.evaluate(([id, message]) => new Promise<any>((resolve) => (window as any).chrome.runtime.sendMessage(id, message, resolve)), [id, message] as const);

test("with something answering on localhost:8000, the Store build sends it nothing and calls WorkIt's API", async () => {
  const api = new FakeApi();
  const { id, page } = await loadStoreBuild([localApp, deployed(api), site]);
  // The webapp's ping signs the student in and fetches their profile (background.js, warmProfile).
  expect(await send(page, id, { type: "ping" })).toMatchObject({ ok: true, installed: true, signedIn: true });
  await expect.poll(() => api.calls.length, { timeout: 15_000 }).toBeGreaterThan(0);
  expect(net.asked.filter((url) => url.includes("localhost"))).toEqual([]);
});

test("the deployed site's Start batch opens the queued job's form in the Store build, and the minified engine fills it with the API's table", async () => {
  test.setTimeout(120_000);
  const forms = new SavedForms([ANDURIL]);
  const api = new FakeApi().queue({ id: "job-0", apply_url: forms.url(ANDURIL) });
  api.rules = served("greenhouse");
  const { id, page } = await loadStoreBuild([localApp, deployed(api), site, forms.handler]);
  expect(await send(page, id, { type: "run/open" })).toMatchObject({ ok: true });
  await expect.poll(() => context.pages().some((p) => p.url() === forms.url(ANDURIL)), { timeout: 30_000 }).toBe(true);
  // Every packaged script is minified (store/build.mjs): the engine and the content scripts still fill.
  const form = context.pages().find((p) => p.url() === forms.url(ANDURIL))!;
  await expect(form.locator("#first_name")).toHaveValue("Test", { timeout: 60_000 });
  // The full fill, which only the served table makes possible: Greenhouse's own pickers (a basic fill types text only).
  await expect.poll(() => form.locator(".select__single-value").count(), { timeout: 60_000 }).toBeGreaterThan(0);
  expect(api.rulesFetches.length).toBeGreaterThan(0);
  expect(forms.submissions).toEqual([]);
  expect(net.asked.filter((url) => url.includes("localhost"))).toEqual([]);
});

test("with the Rules table's API down, the Store build does a basic fill and its panel says why", async () => {
  test.setTimeout(120_000);
  const forms = new SavedForms([ANDURIL]);
  const api = new FakeApi().queue({ id: "job-0", apply_url: forms.url(ANDURIL) });
  api.rules = served("greenhouse");
  // Production before its migration: both routes answer 500.
  api.rulesTokenReply = { status: 500, json: { detail: "Internal Server Error" } };
  const { id, page } = await loadStoreBuild([localApp, deployed(api), site, forms.handler], "open");
  expect(await send(page, id, { type: "run/open" })).toMatchObject({ ok: true });
  await expect.poll(() => context.pages().some((p) => p.url() === forms.url(ANDURIL)), { timeout: 30_000 }).toBe(true);
  const form = context.pages().find((p) => p.url() === forms.url(ANDURIL))!;

  // The basics, by their labels.
  await expect(form.locator("#first_name")).toHaveValue("Test", { timeout: 60_000 });
  await expect(form.locator("#last_name")).toHaveValue("Person");
  await expect(form.locator("#email")).toHaveValue("test.person@example.com");
  const panel = form.locator("#workit-autofiller-overlay-host");
  await expect(panel).toContainText("Basic fill: WorkIt can't reach its server", { timeout: 30_000 });
  await expect(panel).toContainText("your name, email, phone, links and a few common questions");
  // Nothing Greenhouse-only was filled (its pickers need the served table), and nothing was sent.
  expect(await form.locator(".select__single-value").count()).toBe(0);
  expect(forms.submissions).toEqual([]);
});

test("the Store build has no test hooks on its service worker's global", async () => {
  await loadStoreBuild([site]);
  const worker = context.serviceWorkers()[0];
  expect(await worker.evaluate(() => [typeof (globalThis as any).workitToolbar, typeof (globalThis as any).workitCommand])).toEqual(["undefined", "undefined"]);
});
