// The Rules table from WorkIt's API (KAN-756's contract, KAN-773): a posting
// opening fetches its job system's table (a site token, then the table)
// before the student fills, the engine fills with it, and on any failure
// with its bundled table. The table is held in memory only. Patreon's saved
// Ashby form and the fake API; nothing is ever submitted.
import { expect, test, type Page } from "@playwright/test";
import { FakeApi } from "./fake-api";
import { SavedForms } from "./fake-job-systems";
import { loadExtension, signIn, webapp, type Handler, type Loaded, type Reply } from "./loaded-extension";

const PATREON = "ashby-patreon";
// Ashby's submit button under a name the page doesn't use: an engine that reads it never finds the form.
const RENAMED = ".ashby-application-form-submit-button-kan773";

let loaded: Loaded;
test.afterEach(() => loaded?.close());

const hostOf = (page: Page) => page.locator("#workit-autofiller-overlay-host");
const email = (page: Page) => page.locator("input[type=email]").first();

/** The bundled table with Ashby's SUBMIT selector renamed, as the API would serve it (every answer rule, one site). */
async function renamedTable(loaded: Loaded, version?: number): Promise<object> {
  const bundled = await loaded.worker.evaluate(() => (globalThis as any).FillEngine.bundledRules());
  const ashby = bundled.systems.ashby;
  return { version: version ?? bundled.version, answers: bundled.answers, systems: { ashby: { ...ashby, strings: { ...ashby.strings, SUBMIT: RENAMED } } } };
}

/** The extension signed in, with the fake API serving the renamed table; `before` answers ahead of the API. */
async function start(api: FakeApi, before: Handler[] = []): Promise<SavedForms> {
  const forms = new SavedForms([PATREON]);
  loaded = await loadExtension([...before, api.handler, webapp, forms.handler]);
  await signIn(loaded.context);
  api.rules = await renamedTable(loaded);
  return forms;
}

/** What the renamed selector does: the engine waits for a form it never finds (30 s a field), and fills nothing.
 * The bundled table's fill has typed the email well within this time (the failure tests below). */
async function waitsForTheRenamedForm(page: Page) {
  await expect(hostOf(page)).toContainText("Autofilling", { timeout: 30_000 });
  await page.waitForTimeout(20_000);
  await expect(email(page)).toHaveValue("");
  await expect(hostOf(page)).toContainText("Autofilling");
}

/** Patreon's posting opened by the student; resolves once the table's calls have been made. */
async function open(forms: SavedForms, api: FakeApi, calls = 2): Promise<Page> {
  const page = await loaded.context.newPage();
  await page.goto(forms.url(PATREON));
  const rulesCalls = () => api.calls.filter((c) => c.startsWith("POST /extension/rules/token") || c.startsWith("GET /extension/rules")).length;
  await expect.poll(rulesCalls, { timeout: 15_000 }).toBeGreaterThanOrEqual(calls);
  return page;
}

async function autofill(page: Page) {
  await hostOf(page).getByRole("button", { name: "Show WorkIt panel" }).click({ timeout: 15_000 });
  await hostOf(page).getByRole("button", { name: "Autofill This Page" }).click();
}

test("a posting opening fetches its job system's table before any fill, with a site token for its link", async () => {
  const api = new FakeApi();
  const forms = await start(api);
  const page = await open(forms, api);

  expect(api.siteTokens.map((t) => t.url)).toEqual([forms.url(PATREON)]);
  expect(api.rulesFetches).toEqual([api.siteTokens[0].token]);
  // Token first, then the table, and no fill has run (nothing typed).
  const at = (prefix: string) => api.calls.findIndex((c) => c.startsWith(prefix));
  expect(at("POST /extension/rules/token")).toBeLessThan(at("GET /extension/rules"));
  await expect(email(page)).toHaveValue("");
});

test("the fill uses the fetched table: with Ashby's submit selector renamed, the form is never found and nothing fills", { tag: "@nightly" }, async () => {
  test.setTimeout(120_000);
  const api = new FakeApi();
  const forms = await start(api);
  const page = await open(forms, api);
  await autofill(page);

  await waitsForTheRenamedForm(page);
  expect(forms.submissions).toEqual([]);
});

test("a site token is used again while it holds, and a new one asked for once it expires", { tag: "@nightly" }, async () => {
  const api = new FakeApi();
  // 20 s: within the extension's 15 s margin after 5 s.
  api.tokenSeconds = 20;
  const forms = await start(api);
  const first = await open(forms, api);
  await first.close();
  const second = await open(forms, api);
  expect(api.siteTokens).toHaveLength(1);
  expect(api.rulesFetches).toHaveLength(1);
  await second.close();

  await new Promise((done) => setTimeout(done, 6_000));
  await open(forms, api, 4);
  expect(api.siteTokens).toHaveLength(2);
  expect(api.rulesFetches).toEqual([api.siteTokens[0].token, api.siteTokens[1].token]);
});

test("a 401 for the site token asks for a new token once, and the table it then gets fills", { tag: "@nightly" }, async () => {
  test.setTimeout(120_000);
  const api = new FakeApi();
  let refused = 0;
  const expiredOnce: Handler = ({ url, method }) =>
    url.host === "localhost:8000" && url.pathname === "/extension/rules" && method === "GET" && refused++ === 0
      ? { status: 401, json: { detail: "This site token is missing or has expired. Ask for a new one." } }
      : undefined;
  const forms = await start(api, [expiredOnce]);
  const page = await open(forms, api, 3);
  await expect.poll(() => api.rulesFetches.length).toBe(1);
  expect(api.siteTokens).toHaveLength(2);
  await autofill(page);
  await waitsForTheRenamedForm(page);
});

// Every failure the contract lists, at either call: the fill uses the bundled table, and the form fills.
const json = (status: number, detail: unknown): Reply => ({ status, json: { detail } });
// `smoke`: run on a PR too (ci-smoke.txt): the 500s (production before its migration), the retried 401 and the
// RulesError. `version`: the table served is of this version; `system`: the token names this job system.
type Failure = { name: string; at: "token" | "table" | "check"; reply?: Reply; calls: number; smoke?: true; version?: number; system?: string };
const FAILURES: Failure[] = [
  { name: "the token's 401 (signed out)", at: "token", reply: json(401, "Not signed in"), calls: 1 },
  { name: "the token's 403", at: "token", reply: json(403, "Not allowed"), calls: 1 },
  { name: "the token's 422 (a site WorkIt doesn't fill)", at: "token", reply: json(422, "WorkIt doesn't fill this site."), calls: 1 },
  { name: "the token's 426", at: "token", reply: { status: 426, json: { detail: { message: "Please update WorkIt.", min_version: "9.9.9" } } }, calls: 1 },
  { name: "the token's 429", at: "token", reply: json(429, "You've opened a lot of applications today. Try again tomorrow."), calls: 1 },
  { name: "the token's 500 (the migration not run)", at: "token", reply: json(500, "Internal Server Error"), calls: 1, smoke: true },
  { name: "the token's 503", at: "token", reply: json(503, "WorkIt can't fill right now. Try again soon."), calls: 1 },
  { name: "no answer to the token", at: "token", reply: { drop: true }, calls: 1 },
  { name: "the table's 401 twice (a new token refused too)", at: "table", reply: json(401, "This site token is missing or has expired. Ask for a new one."), calls: 4, smoke: true },
  { name: "the table's 403", at: "table", reply: json(403, "Not allowed"), calls: 2 },
  { name: "the table's 426", at: "table", reply: { status: 426, json: { detail: { message: "Please update WorkIt.", min_version: "9.9.9" } } }, calls: 2 },
  { name: "the table's 429", at: "table", reply: json(429, "You've opened a lot of applications today. Try again tomorrow."), calls: 2 },
  { name: "the table's 500 (the migration not run)", at: "table", reply: json(500, "Internal Server Error"), calls: 2, smoke: true },
  { name: "the table's 503", at: "table", reply: json(503, "WorkIt can't fill right now. Try again soon."), calls: 2 },
  { name: "no answer to the table", at: "table", reply: { drop: true }, calls: 2 },
  { name: "a table of another version (the engine's RulesError)", at: "check", calls: 2, smoke: true, version: 99 },
  { name: "a token for another job system", at: "check", calls: 1, system: "greenhouse" },
];

for (const failure of FAILURES) {
  test(`${failure.name}: the bundled table fills`, { tag: failure.smoke ? [] : ["@nightly"] }, async () => {
    test.setTimeout(120_000);
    const api = new FakeApi();
    const forms = await start(api);
    if (failure.at === "token") api.rulesTokenReply = failure.reply!;
    if (failure.at === "table") api.rulesFetchReply = failure.reply!;
    if (failure.version !== undefined) api.rules = await renamedTable(loaded, failure.version);
    if (failure.system) api.rulesJobSystem = failure.system;
    const page = await open(forms, api, failure.calls);
    await autofill(page);

    await expect(email(page)).not.toHaveValue("", { timeout: 20_000 });
    expect(forms.submissions).toEqual([]);
  });
}

test("a fill before the table arrives fills with the bundled table, without waiting for it", async () => {
  test.setTimeout(120_000);
  const api = new FakeApi();
  let answer: ((reply: Reply) => void) | null = null;
  const held: Handler = ({ url, method }) =>
    url.host === "localhost:8000" && url.pathname === "/extension/rules" && method === "GET" ? new Promise<Reply>((done) => (answer = done)) : undefined;
  const forms = await start(api, [held]);
  const page = await open(forms, api, 1);
  await expect.poll(() => answer !== null).toBe(true);
  await autofill(page);
  await expect(email(page)).not.toHaveValue("", { timeout: 60_000 });
  answer!({ status: 503, json: { detail: "late" } });
});

test("nothing of the table is written to storage, the extension's or the page's", { tag: "@nightly" }, async () => {
  test.setTimeout(120_000);
  const api = new FakeApi();
  const forms = await start(api);
  const page = await open(forms, api);
  await autofill(page);
  await waitsForTheRenamedForm(page);

  const stored = await loaded.worker.evaluate(async () => {
    const all = await Promise.all([chrome.storage.local.get(null), chrome.storage.session.get(null), chrome.storage.sync.get(null)]);
    const databases = await indexedDB.databases();
    const caches_ = await caches.keys();
    return JSON.stringify({ all, databases, caches_ });
  });
  expect(stored).not.toContain(RENAMED);
  expect(stored).not.toContain("site-0-");
  const pageStored = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }));
  expect(pageStored).not.toContain(RENAMED);
});
