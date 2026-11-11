// The coverage badge (KAN-749): before a fill, the panel says whether WorkIt
// fully supports the site (a job system filled in one form), partly supports
// it (one whose form comes in steps) or doesn't. On a site it doesn't, the
// toolbar popup's Show My Answers opens the panel there with the student's
// answers, each with Copy. Saved forms and the fake API; nothing is submitted.
import { expect, test, type Page } from "@playwright/test";
import { FakeApi } from "./fake-api";
import { FakeWorkdays, SavedForms } from "./fake-job-systems";
import { EXTENSION_ID, loadExtension, signIn, webapp, type Loaded } from "./loaded-extension";

const ANDURIL = "greenhouse-anduril";
// Where screenshots for Lisul go (none when unset).
const SHOTS = process.env.CHECKLIST_SHOTS;

let loaded: Loaded;
test.afterEach(() => loaded?.close());

const hostOf = (page: Page) => page.locator("#workit-autofiller-overlay-host");
const edgeTab = (page: Page) => hostOf(page).getByRole("button", { name: "Show WorkIt panel" });
const coverage = (page: Page) => hostOf(page).locator('[data-slot="coverage"]');

test("a Greenhouse form is fully supported until the fill takes the panel", async () => {
  test.setTimeout(120_000);
  const forms = new SavedForms([ANDURIL]);
  loaded = await loadExtension([new FakeApi().handler, webapp, forms.handler]);
  await signIn(loaded.context);
  const page = await loaded.context.newPage();
  await page.goto(forms.url(ANDURIL));
  await edgeTab(page).click({ timeout: 15_000 });

  await expect(coverage(page)).toContainText("Fully supported");
  await expect(coverage(page)).toContainText("WorkIt fills this Greenhouse form.");
  await expect(hostOf(page).locator("[data-answers]")).toHaveCount(0);
  if (SHOTS) await hostOf(page).locator(".panel").screenshot({ path: `${SHOTS}/coverage-full.png` });

  await hostOf(page).getByRole("button", { name: "Autofill This Page" }).click();
  await expect(coverage(page)).toBeHidden({ timeout: 60_000 });
  expect(forms.submissions).toEqual([]);
});

test("a Workday step is partly supported: the student signs in and checks each step", async () => {
  test.setTimeout(90_000);
  const workdays = new FakeWorkdays(["workday-caci"]);
  loaded = await loadExtension([new FakeApi().handler, webapp, workdays.handler]);
  await signIn(loaded.context);
  const page = await loaded.context.newPage();
  await page.goto(workdays.url(0));
  await edgeTab(page).click({ timeout: 15_000 });

  await expect(coverage(page)).toContainText("Partly supported");
  await expect(coverage(page)).toContainText("WorkIt fills Workday one step at a time. You sign in and check each step yourself.");
  await expect(hostOf(page).getByRole("button", { name: "Fill this step" })).toBeVisible();
  if (SHOTS) await hostOf(page).locator(".panel").screenshot({ path: `${SHOTS}/coverage-partial.png` });
});

test("on a site WorkIt can't fill, Show My Answers opens the panel with each answer and its Copy", async () => {
  test.setTimeout(90_000);
  const HOST = "jobs.example-ats.com";
  const link = `https://${HOST}/acme/jobs/42`;
  const site = ({ url }: { url: URL }) =>
    url.host === HOST ? { headers: { "content-type": "text/html" }, body: "<!doctype html><title>Intern</title><h1>Software Intern</h1><input name=email>" } : undefined;
  const api = new FakeApi();
  // Focused: the clipboard takes text only from a page that has focus, as the student's clicked tab does.
  loaded = await loadExtension([api.handler, webapp, site], { grantHosts: [`https://${HOST}/*`], focused: true });
  await loaded.context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: `https://${HOST}` });
  await signIn(loaded.context);
  const tab = await loaded.context.newPage();
  await tab.goto(link);
  // No job system here: the launcher doesn't run on this host, and nothing is drawn until the student asks.
  await tab.waitForTimeout(2000);
  await expect(hostOf(tab)).toHaveCount(0);

  const tabId = await loaded.worker.evaluate(async (url) => (await chrome.tabs.query({ url }))[0].id, link);
  const popup = await loaded.context.newPage();
  await popup.goto(`chrome-extension://${EXTENSION_ID}/src/popup/popup.html?tab=${tabId}`);
  await expect(popup.getByText("WorkIt can't fill this site yet")).toBeVisible();
  await popup.getByRole("button", { name: "Show My Answers" }).click();

  await tab.bringToFront();
  await expect(hostOf(tab).locator(".panel")).toBeVisible({ timeout: 15_000 });
  await expect(coverage(tab)).toContainText("Not supported");
  await expect(coverage(tab)).toContainText("WorkIt can't fill this site yet. Copy your answers into the form yourself.");
  // No fill button: there is nothing WorkIt fills here.
  await expect(hostOf(tab).getByRole("button", { name: "Autofill This Page" })).toHaveCount(0);
  const answers = hostOf(tab).locator("[data-answers]");
  await expect(answers.getByRole("heading", { name: "Contact info" })).toBeVisible();
  await expect(answers).toContainText("test.person@example.com");
  await expect(answers).toContainText("Example State University");
  // No self-identification answer (the fake student's race is Asian).
  await expect(answers).not.toContainText("Asian");
  if (SHOTS) await hostOf(tab).locator(".panel").screenshot({ path: `${SHOTS}/coverage-none.png` });

  await answers.getByRole("button", { name: "Copy Email" }).click();
  await expect(answers.getByRole("button", { name: "Copied Email" })).toHaveText("Copied");
  expect(await tab.evaluate(() => navigator.clipboard.readText())).toBe("test.person@example.com");
  // Another Copy takes over Copied.
  await answers.getByRole("button", { name: "Copy Phone" }).click();
  await expect(answers.getByRole("button", { name: "Copy Email" })).toHaveText("Copy");
  expect(await tab.evaluate(() => navigator.clipboard.readText())).toBe("+1 555 010 0199");
});
