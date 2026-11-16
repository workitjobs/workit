// A pretend Apply, in the shape of `Dashboard.state()`, with a pretend queue and
// Usage: the window's fixtures. Pick one with ?scenario=start|needs|questions|ready|quiet|stopped,
// the day's model use with ?usage=near|cap, and the start screen's queue with
// ?queue=empty|unread|refused (refused: Start gives app_window.Bridge's error), and how Apply answers with ?connect=slow|down
// (slow: the first state after 2 s; down: no answer at all). Answers,
// approvals, Remove and Stop change it as Apply would, so the whole flow can be clicked through.
import type { ApplyState, Shown, Waiting } from "./apply.ts";
import type { Bridge, Queued, Usage } from "./bridge.ts";

const ramp: Shown = {
  id: "live-1",
  tone: "needs",
  kind: "missing fact",
  company: "Ramp",
  company_domain: "ramp.com",
  role: "New Grad Software Engineer",
  posting_url: "https://jobs.ashbyhq.com/ramp/1",
  system: "Ashby",
  worker: 1,
  live: true,
  // One question of each kind the card answers: buttons, a list, boxes to tick, a file, a planned answer the form
  // refused, and optional ones to skip.
  questions: [
    "Are you authorized to work in the US?",
    "Which offices could you work from?",
    "How did you hear about us?",
    "Upload your unofficial transcript",
    "When can you start?",
    "Anything else you'd like us to know?",
  ],
  choices: {
    "Are you authorized to work in the US?": { kind: "single", options: ["Yes", "No"] },
    "Which offices could you work from?": { kind: "multi_select", options: ["New York", "San Francisco", "Miami", "Remote"] },
    "How did you hear about us?": { kind: "single", options: ["LinkedIn", "Handshake", "A friend", "Career fair", "WorkIt", "Other"] },
    "Upload your unofficial transcript": { kind: "file", options: [] },
  },
  required: {
    "Are you authorized to work in the US?": true,
    "Which offices could you work from?": true,
    "How did you hear about us?": false,
    "Upload your unofficial transcript": true,
    "When can you start?": true,
    "Anything else you'd like us to know?": false,
  },
  planned: { "When can you start?": "Jun 2027" },
};
const nvidia: Shown = {
  id: "7",
  tone: "needs",
  kind: "needs sign-in",
  company: "NVIDIA",
  company_domain: "nvidia.com",
  role: "SWE Intern, Summer 2027",
  posting_url: "https://nvidia.wd5.myworkdayjobs.com/1",
  system: "Workday",
  worker: 2,
  do: "Sign in to NVIDIA's Workday site once",
};
const figma: Shown = {
  id: "8",
  tone: "needs",
  kind: "held",
  company: "Figma",
  company_domain: "figma.com",
  role: "Software Engineer Intern",
  posting_url: "https://boards.greenhouse.io/figma/1",
  system: "Greenhouse",
  application_id: "a8",
  essays: [
    {
      question: "Why Figma?",
      text: "I started using Figma to lay out the dashboard for my robotics team's micromouse, and what kept me there was how the multiplayer cursors turned design reviews into something the whole team joined…",
    },
  ],
};
const notion: Shown = {
  tone: "ready",
  company: "Notion",
  company_domain: "notion.so",
  role: "Software Engineer",
  posting_url: "https://jobs.ashbyhq.com/notion/1",
  system: "Ashby",
  worker: 0,
  verified: true,
  filled: 22,
  asked: 22,
  files: [{ label: "Resume/CV", name: "Resume.pdf" }],
  essays: [
    {
      question: "Why Notion?",
      text: "I've used Notion to run my robotics team's build season, from part tracking to match notes, and what stuck with me is how one tool bent to fit four different ways of working…",
    },
  ],
};
const stripe: Shown = { tone: "filling", company: "Stripe", company_domain: "stripe.com", role: "Software Engineer Intern", posting_url: "https://stripe/1", worker: 0, filled: 14, asked: 22 };
const linear: Shown = { tone: "verifying", company: "Linear", company_domain: "linear.app", role: "Backend Engineer Intern", posting_url: "https://linear/1", worker: 2 };
const vercel: Shown = { tone: "submitted", company: "Vercel", company_domain: "vercel.com", role: "Software Engineer, New Grad", posting_url: "https://vercel/1", from: "tracker" };
const datadog: Shown = { tone: "submitted", company: "Datadog", company_domain: "datadoghq.com", role: "Software Engineer Intern", posting_url: "https://datadog/1", from: "tracker" };

// Didn't go through: a failed form and a ruled-out one whose pages Apply holds (Try again), and three it can't retry.
const plaid: Shown = { tone: "failed", kind: "failed", status: "failed", label: "Couldn't finish: the page took too long to respond", company: "Plaid", company_domain: "plaid.com", role: "Software Engineer Intern", posting_url: "https://plaid/1", again: true };
const duolingo: Shown = { tone: "ended", kind: "skipped", status: "not eligible", label: "Skipped: you don't qualify (needs a graduation date in 2026)", company: "Duolingo", company_domain: "duolingo.com", role: "Software Engineer, New Grad", posting_url: "https://duolingo/1", again: true };
const airbnb: Shown = { tone: "ended", kind: "skipped", status: "closed", label: "Skipped: no longer taking applications", company: "Airbnb", company_domain: "airbnb.com", role: "Software Engineer Intern", posting_url: "https://airbnb/1", id: 21 };
const coinbase: Shown = { tone: "ended", kind: "skipped", status: "already applied", label: "Already applied", company: "Coinbase", company_domain: "coinbase.com", role: "Software Engineer Intern", posting_url: "https://coinbase/1", id: 22 };

// A run's jobs not started yet: two from the queue and a pasted link. A scenario waits on at most these three.
const WAITING: Waiting[] = [
  { link: "https://jobs.lever.co/spotify/1", company: "Spotify", title: "Backend Engineer Intern", company_domain: "spotify.com" },
  { link: "https://jobs.ashbyhq.com/openai/1", company: "OpenAI", title: "Software Engineer, New Grad", company_domain: "openai.com" },
  { link: "https://careers.example.com/jobs/42" },
];
const running = (queued: number) => ({ mode: "rehearsal", queued, waiting: WAITING.slice(0, queued) });

const SCENARIOS: Record<string, () => ApplyState> = {
  start: () => ({ tiles: [], items: [], run: { queued: 0 } }),
  questions: () => ({ tiles: [stripe], items: [ramp], run: running(2) }),
  needs: () => ({ tiles: [stripe, linear], items: [ramp, nvidia, figma, notion, vercel, datadog], run: running(3) }),
  ready: () => ({ tiles: [stripe], items: [notion, vercel], run: running(3) }),
  quiet: () => ({ tiles: [stripe, { ...linear }], items: [vercel, datadog], run: running(3) }),
  stopped: () => ({ tiles: [stripe, plaid, duolingo], items: [airbnb, coinbase, vercel], run: running(1) }),
};

const QUEUE: Queued[] = [
  { url: "https://stripe/1", company: "Stripe", title: "Software Engineer Intern", company_domain: "stripe.com" },
  { url: "https://jobs.ashbyhq.com/ramp/1", company: "Ramp", title: "New Grad Software Engineer", company_domain: "ramp.com" },
  { url: "https://jobs.ashbyhq.com/notion/1", company: "Notion", title: "Software Engineer", company_domain: "notion.so" },
  { url: "https://nvidia.wd5.myworkdayjobs.com/1", company: "NVIDIA", title: "SWE Intern, Summer 2027", company_domain: "nvidia.com" },
];

const CAP = 400_000;
const USED: Record<string, number> = { near: 340_000, cap: CAP };

export function mock(
  scenario: string,
  used = USED[new URLSearchParams(location.search).get("usage") ?? ""] ?? 52_000,
  queued = new URLSearchParams(location.search).get("queue") ?? "",
  connect = new URLSearchParams(location.search).get("connect") ?? "",
): Bridge {
  let state = structuredClone((SCENARIOS[scenario] ?? SCENARIOS.needs)());
  const listeners = new Set<(s: ApplyState) => void>();
  const push = () => listeners.forEach((on) => on(structuredClone(state)));
  const later = (change: () => void, ms = 1500) => setTimeout(() => (change(), push()), ms);
  const find = (id: string) => state.items.find((i) => String(i.id) === id);
  return {
    watch(on, lost) {
      if (connect === "down") {
        const t = setTimeout(() => lost?.(), 1500);
        return () => clearTimeout(t);
      }
      const t = setTimeout(() => (listeners.add(on), on(structuredClone(state))), connect === "slow" ? 2000 : 0);
      return () => (clearTimeout(t), listeners.delete(on));
    },
    async answer(id, question) {
      const item = find(id);
      if (!item) return;
      item.questions = (item.questions ?? []).filter((q) => q !== question);
      if (!item.questions.length) Object.assign(item, { tone: "filling", kind: undefined, filled: 18, asked: 22 });
      push();
      if (item.tone === "filling") later(() => Object.assign(item, { tone: "ready", verified: true, filled: 22 }), 4000);
    },
    async approve(id) {
      const item = find(id);
      if (item) Object.assign(item, { tone: "ready", kind: undefined, verified: true });
      push();
    },
    async open(worker) {
      // The student presses Submit in that form's Chrome window a moment later.
      const ready = [...state.tiles, ...state.items].find((s) => s.worker === worker && s.tone === "ready");
      if (ready) later(() => Object.assign(ready, { tone: "submitted" }), 2500);
    },
    async fillAgain(id) {
      // Apply opens the form anew a moment later, on the tile that held it.
      const held = id.startsWith("tile-") ? state.tiles[Number(id.slice(5))] : find(id);
      if (held) later(() => Object.assign(held, { tone: "filling", kind: undefined, status: "filling", label: undefined, again: false, filled: 2, asked: 22 }), 800);
    },
    async remove(link) {
      const run = state.run!;
      if (!run.waiting?.some((w) => w.link === link)) throw new Error("That job has started already: it isn't waiting any more.");
      run.waiting = run.waiting.filter((w) => w.link !== link);
      run.queued = (run.queued ?? 1) - 1;
      push();
    },
    async stop() {
      // The run ends, and app_window.Bridge swaps in the idle board: the queue again.
      later(() => (state = structuredClone(SCENARIOS.start())), 800);
    },
    app: Promise.resolve({
      async queue() {
        if (queued === "unread") throw new Error("WorkIt Auto Apply couldn't read your queue (WorkIt didn't answer). Paste a link instead.");
        return queued === "empty" ? [] : QUEUE;
      },
      async start(links: string[]) {
        await new Promise((done) => setTimeout(done, 800));
        if (queued === "refused") throw new Error("Chrome isn't installed. Get it from google.com/chrome, then press Start again.");
        state = structuredClone(SCENARIOS.quiet());
        push();
        return links.length;
      },
      applied: async () => [
        { url: "https://vercel/1", company: "Vercel", title: "Software Engineer, New Grad", company_domain: "vercel.com", applied_at: "2026-11-15T09:00:00Z" },
        { url: "https://jobs.lever.co/palantir/1", company: "Palantir", title: "Forward Deployed Engineer Intern", company_domain: "palantir.com", applied_at: "2026-11-02T14:00:00Z" },
      ],
      status: async () => ({ running: false, said: "" }),
      usage: async (): Promise<Usage> => ({ used, cap: CAP, resets_at: new Date(Date.now() + 5 * 3600_000).toISOString() }),
      settings: async () => alert("Settings: app_window.Bridge's page opens here."),
    }),
  };
}
