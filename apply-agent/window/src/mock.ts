// A pretend Apply, in the shape of `Dashboard.state()`, with a pretend queue and
// Usage: the window's fixtures. Pick one with ?scenario=start|needs|questions|ready|quiet,
// the day's model use with ?usage=near|cap, and the start screen's queue with
// ?queue=empty|unread|refused (refused: Start gives #613's error). Answers and
// approvals change it as Apply would, so the whole flow can be clicked through.
import type { ApplyState, Shown } from "./apply.ts";
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

const SCENARIOS: Record<string, () => ApplyState> = {
  start: () => ({ tiles: [], items: [], run: { queued: 0 } }),
  questions: () => ({ tiles: [stripe], items: [ramp], run: { queued: 2 } }),
  needs: () => ({ tiles: [stripe, linear], items: [ramp, nvidia, figma, notion, vercel, datadog], run: { queued: 6 } }),
  ready: () => ({ tiles: [stripe], items: [notion, vercel], run: { queued: 3 } }),
  quiet: () => ({ tiles: [stripe, { ...linear }], items: [vercel, datadog], run: { queued: 4 } }),
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
): Bridge {
  let state = structuredClone((SCENARIOS[scenario] ?? SCENARIOS.needs)());
  const listeners = new Set<(s: ApplyState) => void>();
  const push = () => listeners.forEach((on) => on(structuredClone(state)));
  const later = (change: () => void, ms = 1500) => setTimeout(() => (change(), push()), ms);
  const find = (id: string) => state.items.find((i) => String(i.id) === id);
  return {
    watch(on) {
      listeners.add(on);
      on(structuredClone(state));
      return () => listeners.delete(on);
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
      const item = find(id);
      if (item) Object.assign(item, { tone: "filling", kind: undefined, filled: 2, asked: 22 });
      push();
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
      status: async () => ({ running: false, said: "" }),
      usage: async (): Promise<Usage> => ({ used, cap: CAP, resets_at: new Date(Date.now() + 5 * 3600_000).toISOString() }),
      settings: async () => alert("Settings: #613's page opens here."),
    }),
  };
}
