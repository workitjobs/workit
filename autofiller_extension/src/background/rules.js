// The Fill engine's Rules table from WorkIt's API (KAN-756's contract, KAN-773):
// each job system's selectors, wordings and patterns, and the answer rules,
// served after sign-in for the job system of the posting open, one at a time.
//
// A posting opening (panel/where, a batch tab's openTab) fetches its job
// system's table at once, before the student fills: a site token (POST
// /extension/rules/token, with the page's link), then the table (GET
// /extension/rules). The table is held in memory only, never chrome.storage,
// IndexedDB or disk: here, for the service worker's life, and in the page's
// isolated world (the launcher's `window.WIA.rules`), which outlives a service
// worker Chrome stopped while the student read the posting. Each injection of
// the engine loads it (content-scripts.js `loadRulesIn`), and the background's
// own engine, which plans, holds every site's table it has.
//
// Any failure (no answer, a 4xx or 5xx, a table the engine refuses, another
// job system than the page's) leaves the bundled table, which the engine
// fills with when nothing is loaded. A fill never waits for the API: a table
// still on its way when the fill starts is the next fill's (on Workday, the
// next step's, each a fill of its own).
//
// The Store package's engine ships no job system's data (fill-engine's engine.store.js, KAN-777): there a
// fill whose table hasn't come yet waits for it a while (TABLE_WAIT_MS), and with none the fill is a basic
// one (background/engine.js planBasic). The dev extension's engine bundles the full table, so it never waits.
//
// The strings are used as received: the API watermarks each account's copy
// (selector order, a never-matching selector part, equivalent regex
// spellings), so nothing here sorts, dedupes or rewrites them.

import { ApiError, rulesTable, rulesToken } from "./api.js";
import { getSession } from "./auth.js";
import { readWebappSession } from "./webapp-session.js";
import { jobOf } from "./engine.js";
import { turnedOff } from "./remote-config.js";

const engine = globalThis.FillEngine;
/** The bundled table: what loadRules goes back to. */
const BUNDLED = { version: engine.RULES_VERSION };
/** A site token this close to its expiry is not used: a new one is asked for. */
const MARGIN_MS = 15_000;
/** How long a fill waits for a table still on its way when the engine has no data of its own for the site. */
const TABLE_WAIT_MS = 5_000;

/** The account the tokens and tables are for: another sign-in drops them all. */
let owner = null;
/** Each job system's site token: `{ token, until }` (ms). */
const tokens = new Map();
/** Each job system's table: `{ table, until }`, fetched while its token held until `until`. In the order held:
 * the background's engine takes the version and answer rules from the last (loadBackground). */
const tables = new Map();
/** The fetch under way for each job system: its callers share it. */
const fetching = new Map();

/** Whether a token or table held until `until` (ms) is still good for a while. */
const fresh = (kept) => Boolean(kept) && kept.until - MARGIN_MS > Date.now();

/** Holds `kept` as `site`'s table, last, if the background's engine takes it; else drops it. */
function hold(site, kept) {
  tables.delete(site);
  tables.set(site, kept);
  if (loadBackground()) return true;
  tables.delete(site);
  loadBackground();
  return false;
}

/** Drops every token and table when `account` isn't the one they are for. */
function ownedBy(account) {
  if (owner === account) return;
  owner = account;
  tokens.clear();
  tables.clear();
  fetching.clear();
  loadBackground();
}

/**
 * Loads every held table into the background's engine, which plans for every
 * tab: the answer rules (each table carries all of them) and each site's data.
 * A table the engine refuses is dropped, and the rest loaded again.
 * @returns {boolean} whether every held table loaded
 */
function loadBackground() {
  const held = [...tables.values()].map((kept) => kept.table);
  if (!held.length) {
    engine.loadRules(BUNDLED);
    return true;
  }
  const last = held[held.length - 1];
  const union = { version: last.version, systems: Object.assign({}, ...held.map((table) => table.systems ?? {})) };
  if (last.answers !== undefined) union.answers = last.answers;
  try {
    engine.loadRules(union);
    return true;
  } catch (error) {
    console.warn("[rules] the background's engine refused the Rules table; the bundled one fills:", error.message);
    engine.loadRules(BUNDLED);
    return false;
  }
}

/** A site token for `site` still good for a while, else a new one for the posting at `url`, for `account`. */
async function siteToken(url, site, account) {
  const kept = tokens.get(site);
  if (fresh(kept)) return kept;
  const answer = await rulesToken(url);
  // Another sign-in while it was asked: never kept for the next account.
  if (owner !== account) throw new Error("another account signed in");
  if (answer?.job_system !== site) throw new Error(`the API named ${answer?.job_system} for a ${site} page`);
  const token = { token: answer.token, until: Date.now() + Number(answer.expires_in) * 1000 };
  tokens.set(site, token);
  return token;
}

/** The token's table; on its 401, one new token and one more fetch (the contract's retry). */
async function fetchTable(url, site, account) {
  const token = await siteToken(url, site, account);
  try {
    return { table: await rulesTable(token.token), until: token.until };
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    tokens.delete(site);
    const renewed = await siteToken(url, site, account);
    try {
      return { table: await rulesTable(renewed.token), until: renewed.until };
    } catch (again) {
      // Refused too: the next posting asks for another, never this one again.
      tokens.delete(site);
      throw again;
    }
  }
}

/** The link the API names the job system from: a practice form (WorkIt's own, Lever's form) asks for Lever's table
 * with a Lever link for its job, since the API knows no job system on WorkIt's site. */
const tokenLink = (url, job) => (job.practice ? `https://jobs.lever.co/${job.company}/${job.job}/apply` : url);

/** Fetches `site`'s table, checks the engine takes it, and holds it; null on any failure. */
async function fetchRules(url, site, account) {
  try {
    const kept = await fetchTable(url, site, account);
    if (owner !== account) return null;
    if (!kept.table || typeof kept.table !== "object") throw new Error("the API's answer is no table");
    // The engine checks the whole table before using any of it: one it refuses is never held.
    return hold(site, kept) ? kept.table : null;
  } catch (error) {
    console.warn(`[rules] ${site}'s Rules table wasn't fetched; the bundled one fills:`, error.message);
    return null;
  }
}

/**
 * Fetches the Rules table for the posting at `url`, as it opens: resolves to
 * `{ owner, site, table }` once it is held, or null (not a job system's page,
 * a practice form, a job system turned off, signed out, or any failure).
 * A table fetched with a token that still holds is used again.
 * @param {string} url the link the engine reads for the page (site-access.js pageJobUrl)
 */
export async function prefetchRules(url) {
  const job = url ? jobOf(url) : null;
  if (!job) return null;
  const { site } = job;
  try {
    if (await turnedOff(url)) return null;
    const session = await getSession();
    // Signed out: the last account's tables go.
    ownedBy(session ? String(session.user_id) : null);
    if (!session) return null;
    const account = owner;
    const kept = tables.get(site);
    if (fresh(kept)) return { owner: account, site, table: kept.table };
    if (!fetching.has(site)) {
      const fetch = fetchRules(tokenLink(url, job), site, account).finally(() => fetching.get(site) === fetch && fetching.delete(site));
      fetching.set(site, fetch);
    }
    const table = await fetching.get(site);
    return table ? { owner: account, site, table } : null;
  } catch (error) {
    console.warn("[rules] no Rules table:", error.message);
    return null;
  }
}

/**
 * The table an injection of the engine loads for `site`: the one held here,
 * else the page's own copy (`page`, the launcher's, when Chrome stopped the
 * service worker since), else null, the bundled table. Only when the engine has no data of its own for
 * the site (the Store package) does it wait, at most TABLE_WAIT_MS, for a fetch (the one on its way, else
 * a new one for `url`).
 * @param {string | null} site
 * @param {{ owner: string, site: string, table: object } | null | undefined} page
 * @param {string | null} [url] the page's link, for a new fetch when the engine has no data of its own
 */
export async function rulesFor(site, page, url = null) {
  if (!site) return null;
  // The cookie's account, with no refresh: the fill's own reads ask for the session.
  const session = await readWebappSession().catch(() => null);
  ownedBy(session ? String(session.user_id) : null);
  if (!session) return null;
  const account = owner;
  const held = tables.get(site)?.table;
  if (held) return held;
  if (page?.owner === account && page.site === site && page.table) {
    // The page's copy, held here again so the background's engine plans with it too.
    if (hold(site, { table: page.table, until: 0 })) return page.table;
  }
  // An engine with no data of its own for the site (the Store package's) waits a while for its table: one on
  // its way, else a new fetch for the page (one that failed as the posting opened may answer now).
  if (engine.supported(site)) return null;
  const fetch = fetching.get(site) ?? (url ? prefetchRules(url).then((got) => got?.table ?? null) : null);
  if (!fetch) return null;
  let timer;
  const late = new Promise((done) => (timer = setTimeout(() => done(null), TABLE_WAIT_MS)));
  const table = await Promise.race([fetch, late]).finally(() => clearTimeout(timer));
  // Another sign-in while it waited: never the last account's table.
  return table && owner === account ? table : null;
}
