// Check before Submit (KAN-747), the extension's copy of Apply's Pre-submit
// check: after a fill, the panel lists every answer the fill filled or
// wrote, flagged ones first (still needing the student, then WorkIt's
// guesses, then what their Claude wrote), each going to its field when
// pressed. Review and submit opens it; its button then reads Go to Submit,
// which rings the employer's Submit and never presses it. The ⋯ menu opens it
// at any time after a fill.
import { expect, test, type Page } from "@playwright/test";
import { PRACTICE_JOBS, practiceFormUrl, practicePage } from "../../frontend/src/lib/practice-form";
import { FakeApi } from "./fake-api";
import { SavedForms } from "./fake-job-systems";
import { loadExtension, menuItem, sendFromWebapp, signIn, webapp, type Handler, type Loaded } from "./loaded-extension";

const ANDURIL = "greenhouse-anduril";
const ASKED = "question_13130330007"; // Anduril: in person for 12 weeks, no answer (red)
const GUESS = "question_13130335007"; // Anduril: how they heard of Anduril, guessed (amber)

let loaded: Loaded;
test.afterEach(() => loaded?.close());

const hostOf = (page: Page) => page.locator("#workit-autofiller-overlay-host");
const mainButton = (page: Page) => hostOf(page).locator('[data-slot="primary"] .primary-button').first();
const view = (page: Page) => hostOf(page).locator('[data-slot="check"]');
const rowsOf = (page: Page) => view(page).locator(".row[data-key]");

/** Anduril's form opened by the student, filled with Autofill This Page. */
async function filled(forms: SavedForms): Promise<Page> {
  loaded = await loadExtension([new FakeApi().handler, webapp, forms.handler]);
  await signIn(loaded.context);
  const page = await loaded.context.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(forms.url(ANDURIL));
  await hostOf(page).getByRole("button", { name: "Show WorkIt panel" }).click({ timeout: 15_000 });
  await mainButton(page).click();
  await expect(mainButton(page)).toContainText(/^Answer \d+ of \d+$/, { timeout: 60_000 });
  return page;
}

test("the list holds every filled answer, flagged first, and each row goes to its field", async () => {
  test.setTimeout(120_000);
  const forms = new SavedForms([ANDURIL]);
  const page = await filled(forms);

  await (await menuItem(hostOf(page), "Check before Submit")).click();
  await expect(view(page)).toBeVisible();
  await expect(view(page).getByRole("heading", { name: "Check before Submit" })).toBeVisible();
  await expect(hostOf(page).locator(".tab[data-tab=\"autofill\"]")).toBeHidden();

  // Every filled field of the checklist is in the list, and every red one.
  const listed = await rowsOf(page).evaluateAll((rows) => rows.map((r) => (r as HTMLElement).dataset.key!));
  const filledKeys = await hostOf(page)
    .locator('[data-tab="autofill"] .row[data-key][data-mark="filled"], [data-tab="autofill"] .row[data-key][data-mark="check"], [data-tab="autofill"] .row[data-key][data-mark="needs-you"]')
    .evaluateAll((rows) => rows.map((r) => (r as HTMLElement).dataset.key!));
  for (const key of filledKeys) expect(listed).toContain(key);
  expect(listed).toContain(ASKED);
  expect(listed).toContain(GUESS);

  // Flagged rows come first: what needs the student, then the guesses, then the rest, filled.
  const tiers = await rowsOf(page).evaluateAll((rows) => rows.map((r) => Number((r as HTMLElement).dataset.flagged ?? 9)));
  expect(tiers).toEqual([...tiers].sort((a, b) => a - b));
  expect(tiers[0]).toBe(0);
  expect(tiers).toContain(1);
  expect(tiers.at(-1)).toBe(9);
  await expect(view(page).locator(`.row[data-key="${ASKED}"] .check-why`)).toHaveText("Required, and still empty.");
  await expect(view(page).locator(`.row[data-key="${GUESS}"] .check-why`)).toHaveText(/WorkIt guessed this/);
  await expect(view(page).locator(`.row[data-key="${GUESS}"] .check-answer`)).not.toBeEmpty();
  // A plain filled row shows what the page holds, and where it came from.
  await expect(view(page).locator('.row[data-key="first_name"] .check-answer')).not.toBeEmpty();
  await expect(view(page).locator('.row[data-key="first_name"] .source')).toHaveText("Profile");

  // A row's press goes to its field: scrolled to and focused.
  await view(page).locator('.row[data-key="first_name"] .label').click();
  await expect.poll(() => page.evaluate(() => document.activeElement?.id)).toBe("first_name");
  await expect(page.locator("#first_name")).toBeInViewport();

  // Back leaves the view for the Autofill tab.
  await view(page).getByRole("button", { name: "Back" }).click();
  await expect(view(page)).toBeHidden();
  await expect(hostOf(page).locator(".tab[data-tab=\"autofill\"]")).toBeVisible();
  expect(forms.submissions).toEqual([]);
});

test("Review and submit opens the list, and Go to Submit rings the employer's Submit and sends nothing", async () => {
  test.setTimeout(150_000);
  const forms = new SavedForms([ANDURIL]);
  const page = await filled(forms);
  // The student answers whatever needs them (panel-primary's way: the first option of each red dropdown).
  for (let n = 0; n < 15 && !/Review and submit/.test(await mainButton(page).innerText()); n++) {
    await mainButton(page).click();
    const row = hostOf(page).locator("[data-current]");
    await expect(row).toHaveCount(1);
    const key = (await row.getAttribute("data-key"))!;
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
    await expect(hostOf(page).locator(`.row[data-key="${key}"]`)).not.toHaveAttribute("data-mark", "needs-you", { timeout: 10_000 });
  }
  await expect(mainButton(page)).toHaveText("Review and submit");

  await mainButton(page).click();
  await expect(view(page)).toBeVisible();
  // Nothing red is left: the guesses lead the list.
  await expect(rowsOf(page).first()).toHaveAttribute("data-flagged", "1");
  await expect(view(page).locator('.row[data-flagged="0"]')).toHaveCount(0);
  await expect(mainButton(page)).toHaveText("Go to Submit");

  await mainButton(page).click();
  const submit = page.getByRole("button", { name: /^Submit/ });
  await expect(submit).toBeInViewport();
  await expect(page.locator("#workit-marks-host").locator(".ring")).toBeAttached();
  await page.waitForTimeout(1000);
  expect(forms.submissions).toEqual([]);
});

// Lumen's practice form, queued as a batch application, asks one written question (panel-answers.extension.spec.ts).
const WEB = "http://localhost:3000";
const LUMEN = practiceFormUrl(WEB, PRACTICE_JOBS[1]);
const ANSWER = "I want to build data pipelines that help clinics call the right patients.";
const practice: Handler = ({ url }) => {
  if (url.host !== "localhost:3000") return undefined;
  const html = { "content-type": "text/html; charset=utf-8" };
  const [, company, job, page] = /^\/practice\/([^/]+)\/([^/]+)\/([^/]+)$/.exec(url.pathname) ?? [];
  if (company) return { headers: html, body: practicePage(company, job, page) ?? "" };
  return { headers: html, body: "<!doctype html><title>WorkIt</title><p>WorkIt" };
};

test("an answer the student's Claude wrote is flagged in the list, with its words, after waiting there for their Claude", async () => {
  test.setTimeout(150_000);
  const api = new FakeApi().queue({ id: "job-0", apply_url: LUMEN });
  loaded = await loadExtension([api.handler, practice]);
  await signIn(loaded.context);
  const start = loaded.context.pages()[0] ?? (await loaded.context.newPage());
  await start.goto(`${WEB}/auto-apply`);
  await sendFromWebapp(start, { type: "run/open" });
  await expect.poll(() => api.written.get("job-0")?.length, { timeout: 60_000 }).toBe(1);
  const name = api.written.get("job-0")![0].name;
  const form = loaded.context.pages().find((p) => p.url() === LUMEN)!;
  await expect(hostOf(form).locator(`.row[data-key="${name}"]`)).toHaveAttribute("data-mark", "waiting", { timeout: 30_000 });

  await (await menuItem(hostOf(form), "Check before Submit")).click();
  const row = view(form).locator(`.row[data-key="${name}"]`);
  await expect(row).toHaveAttribute("data-flagged", "3");
  await expect(row.locator(".check-why")).toHaveText("Waiting for your Claude to write it.");

  // Their Claude's answer lands while the list shows: the row is redrawn as Claude's words to read.
  api.saveAnswer("job-0", name, ANSWER);
  await expect(row).toHaveAttribute("data-flagged", "2", { timeout: 30_000 });
  await expect(row.locator(".check-why")).toHaveText(/Your Claude wrote this|A new answer/);
  await expect(row.locator(".check-answer")).toHaveText(ANSWER);
});
