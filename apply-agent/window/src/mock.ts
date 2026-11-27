// A pretend Apply, in the shape of `Dashboard.state()`, with a pretend queue and
// Usage: the window's fixtures. Pick one with ?scenario=start|needs|questions|ready|auto|quiet|stopped|done,
// the day's model use with ?usage=near|cap, and the start screen's queue with
// ?queue=empty|unread|refused (refused: Start gives app_window.Bridge's error), Find jobs' matches with ?matches=empty|unread, and how Apply answers with ?connect=slow|down
// (slow: the first state after 2 s; down: no answer at all). Answers,
// approvals, Remove and Stop change it as Apply would, so the whole flow can be clicked through. Report a problem
// shows on the jobs with an application_id (Figma, Notion, Plaid) and sends nothing.
import type { BankView } from "./bank.ts";
import type { ApplyState, Shown, Waiting } from "./apply.ts";
import type { Bridge, Match, Queued, Usage } from "./bridge.ts";

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
// A Workday step it won't leave: the card names the fields it wants. Made up.
const sierra: Shown = {
  id: "11",
  tone: "needs",
  kind: "handoff",
  company: "Sierra Space",
  company_domain: "sierraspace.com",
  role: "Software Engineer Intern",
  posting_url: "https://sierraspace.wd5.myworkdayjobs.com/1",
  system: "Workday",
  worker: 4,
  why: "Workday won't leave its 'Application Questions 1 of 2' step: Error-Are you currently employed? The field Are you currently employed? is required and must have a value. Error-Do you have intellectual property? The field Do you have intellectual property? is required and must have a value.",
};
// A captcha, and an emailed code: each card says how to hand the form back.
const gecko: Shown = { id: "12", tone: "needs", kind: "captcha", company: "Gecko", company_domain: "geckorobotics.com", role: "Software Engineer Intern", posting_url: "https://gecko/1", worker: 5 };
const lucid: Shown = { id: "13", tone: "needs", kind: "needs code", company: "Lucid", company_domain: "lucidmotors.com", role: "Software Engineer Intern", posting_url: "https://lucid/1", worker: 6 };
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
  application_id: "a10",
  verified: true,
  filled: 22,
  asked: 22,
  files: [{ label: "Resume/CV", name: "Resume.pdf" }],
  // What the held card's "What we filled" lists, and what the Pre-submit review changed after checking. Made up.
  answers: [
    { question: "First Name", answer: "Test", from: "profile", kind: "text", topic: "" },
    { question: "Email", answer: "test.person@example.com", from: "profile", kind: "text", topic: "" },
    { question: "Resume/CV", answer: "Resume.pdf", from: "profile", kind: "file", topic: "file" },
    { question: "Are you legally authorized to work in the United States?", answer: "Yes", from: "profile", kind: "select", topic: "legal" },
    { question: "Will you now or in the future require sponsorship?", answer: "No", from: "profile", kind: "select", topic: "legal" },
    { question: "Expected graduation date", answer: "May 2028", from: "profile", kind: "text", topic: "school" },
    { question: "How did you hear about us?", answer: "WorkIt", from: "saved", kind: "select", topic: "" },
    { question: "Gender", answer: "Decline to self-identify", from: "profile", kind: "select", topic: "eeo" },
    {
      question: "Why Notion?",
      answer:
        "I've used Notion to run my robotics team's build season, from part tracking to match notes, and what stuck with me is how one tool bent to fit four different ways of working. I want to help build the parts of it that make that possible, and I'd bring the habit of shipping small, testable pieces that I learned keeping a robot running between matches.",
      from: "written",
      kind: "textarea",
      topic: "",
    },
  ],
  fixed: [{ question: "Expected graduation date", was: "May 2027", now: "May 2028" }],
  essays: [
    {
      question: "Why Notion?",
      text: "I've used Notion to run my robotics team's build season, from part tracking to match notes, and what stuck with me is how one tool bent to fit four different ways of working…",
    },
  ],
};
// A form verifying flagged: the check card lists each flag first, then what was filled.
const asana: Shown = {
  id: "9",
  tone: "needs",
  kind: "check",
  company: "Asana",
  company_domain: "asana.com",
  role: "Software Engineer Intern",
  posting_url: "https://jobs.ashbyhq.com/asana/1",
  system: "Ashby",
  worker: 3,
  flags: [{ field: "Expected graduation date", why: "the form shows May 2027, but your profile says May 2028" }],
  answers: [
    { question: "Expected graduation date", answer: "May 2028", from: "profile", kind: "text", topic: "school" },
    { question: "Desired hourly pay", answer: "$30", from: "written", kind: "text", topic: "pay" },
  ],
};
const stripe: Shown = { tone: "filling", company: "Stripe", company_domain: "stripe.com", role: "Software Engineer Intern", posting_url: "https://stripe/1", worker: 0, filled: 14, asked: 22, doing: "Writing answers for page 2" };
const linear: Shown = { tone: "verifying", company: "Linear", company_domain: "linear.app", role: "Backend Engineer Intern", posting_url: "https://linear/1", worker: 2 };
const vercel: Shown = { tone: "submitted", company: "Vercel", company_domain: "vercel.com", role: "Software Engineer, New Grad", posting_url: "https://vercel/1", from: "tracker" };
// Submitted in this run (no `from`), so the run's count has one done.
const lyft: Shown = { tone: "submitted", company: "Lyft", company_domain: "lyft.com", role: "Software Engineer Intern", posting_url: "https://lyft/1" };
const datadog: Shown = { tone: "submitted", company: "Datadog", company_domain: "datadoghq.com", role: "Software Engineer Intern", posting_url: "https://datadog/1", from: "tracker" };

// Didn't go through: a failed form and a ruled-out one whose pages Apply holds (Try again), and three it can't retry.
const plaid: Shown = { tone: "failed", kind: "failed", status: "failed", label: "Couldn't finish: the page took too long to respond", company: "Plaid", company_domain: "plaid.com", role: "Software Engineer Intern", posting_url: "https://plaid/1", again: true, application_id: "a9" };
const duolingo: Shown = { tone: "ended", kind: "skipped", status: "not eligible", label: "Skipped: you don't qualify (needs a graduation date in 2026)", company: "Duolingo", company_domain: "duolingo.com", role: "Software Engineer, New Grad", posting_url: "https://duolingo/1", again: true };
const airbnb: Shown = { tone: "ended", kind: "skipped", status: "closed", label: "Skipped: no longer taking applications", company: "Airbnb", company_domain: "airbnb.com", role: "Software Engineer Intern", posting_url: "https://airbnb/1", id: 21 };
const coinbase: Shown = { tone: "ended", kind: "skipped", status: "already applied", label: "Already applied", company: "Coinbase", company_domain: "coinbase.com", role: "Software Engineer Intern", posting_url: "https://coinbase/1", id: 22 };

// Raw failures the row never shows: a held form, one whose Worker moved on, and a taken-down Workday posting. Made up.
const brex: Shown = { tone: "failed", kind: "failed", status: "failed", label: "Couldn't finish: the page took too long to respond", why: "PortTimeoutError: Locator.click: Timeout 30000ms exceeded.", company: "Brex", company_domain: "brex.com", role: "Software Engineer Intern", posting_url: "https://brex/1", worker: 3, again: true };
const oracle: Shown = { tone: "failed", kind: "failed", status: "failed", label: "Couldn't finish: the page took too long to respond", company: "Oracle", company_domain: "oracle.com", role: "Cloud Engineer Intern", posting_url: "https://oracle/1", id: 23 };
const workday: Shown = { tone: "ended", kind: "skipped", status: "closed", label: "Skipped: no longer taking applications", why: "Closed: the page doesn't exist, so it was skipped", company: "Sierra Space", company_domain: "sierraspace.com", role: "Systems Intern", posting_url: "https://sierraspace.wd5.myworkdayjobs.com/2", id: 24 };

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
  needs: () => ({ tiles: [stripe, linear], items: [ramp, nvidia, asana, sierra, gecko, lucid, figma, notion, lyft, vercel, datadog], run: running(3) }),
  ready: () => ({ tiles: [stripe, { ...notion, worker: 1, again: true }], items: [notion, vercel], run: running(3) }),
  // Auto-submit counting down on a clean form (a Developer checkout's policy).
  auto: () => ({ tiles: [stripe, { ...notion, worker: 1, again: true, auto_at: Date.now() / 1000 + 582 }], items: [notion, vercel], run: running(3) }),
  quiet: () => ({ tiles: [stripe, { ...linear }], items: [vercel, datadog, lyft], run: running(3) }),
  // Everything done: two submitted this run, and one from before that the line leaves out.
  done: () => ({ tiles: [{ ...vercel, from: undefined }, { ...datadog, from: undefined }], items: [{ ...vercel, from: "tracker", posting_url: "https://old/1", company: "Palantir" }], run: running(0) }),
  stopped: () => ({ tiles: [stripe, plaid, duolingo, brex], items: [airbnb, coinbase, vercel, oracle, workday], run: running(1) }),
};

// How many minutes ago each pretend job took its status: what a to-do has waited, or a form has filled.
const MINUTES: Record<string, number> = { Ramp: 2, NVIDIA: 3, Asana: 5, Figma: 8, Notion: 12, Stripe: 6, Linear: 2 };
const dated = (state: ApplyState): ApplyState => {
  for (const s of [...state.tiles, ...state.items]) if (s.company && s.company in MINUTES) s.since = Date.now() / 1000 - MINUTES[s.company] * 60;
  return state;
};

const QUEUE: Queued[] = [
  { url: "https://stripe/1", company: "Stripe", title: "Software Engineer Intern", company_domain: "stripe.com" },
  { url: "https://jobs.ashbyhq.com/ramp/1", company: "Ramp", title: "New Grad Software Engineer", company_domain: "ramp.com" },
  { url: "https://jobs.ashbyhq.com/notion/1", company: "Notion", title: "Software Engineer", company_domain: "notion.so" },
  { url: "https://nvidia.wd5.myworkdayjobs.com/1", company: "NVIDIA", title: "SWE Intern, Summer 2027", company_domain: "nvidia.com" },
];

// Find jobs' matches (?matches=empty|unread for none, or the empty-bank refusal).
const match = (company: string, company_domain: string, title: string, score: number, over: Partial<Match> = {}): Match => ({
  id: company, url: `https://jobs.example/${company}`, company, company_domain, title, match: score,
  highlights: [{ text: `Uses ${Math.round(score / 9)} of your skills`, met: true }, { text: "Fits your experience", met: true }],
  location: "New York, NY", work_style: "hybrid", job_type: "internship", experience_level: "student",
  salary_min: 45, salary_max: 55, salary_period: "hour", start_term: "Summer 2027",
  posted_at: new Date(Date.now() - (score % 7) * 86_400_000).toISOString(), ...over,
});
const MATCHES: Match[] = [
  match("Stripe", "stripe.com", "Software Engineer Intern (Summer 2027)", 94),
  match("Datadog", "datadoghq.com", "Software Engineer Intern", 89, { salary_min: 48, salary_max: 48 }),
  match("Waymo", "waymo.com", "ML Engineer Intern", 86, { location: "Mountain View, CA", work_style: "onsite", highlights: [{ text: "Uses 7 of your skills", met: true }, { text: "Prefers a PhD", met: false }] }),
  match("Formlabs", "formlabs.com", "Embedded Software Intern", 84, { location: "Somerville, MA", work_style: "onsite", salary_min: null, salary_max: null }),
  match("Ramp", "ramp.com", "Backend Engineer, New Grad", 81, { job_type: "full_time", experience_level: "new_grad", salary_min: 150000, salary_max: 180000, salary_period: "year", start_term: "Aug 2027" }),
  match("Zillow", "zillow.com", "Data Engineer Intern", 72, { location: "Remote (US)", work_style: "remote", highlights: [{ text: "Uses 4 of your skills", met: true }, { text: "Missing Spark", met: false }] }),
];

const CAP = 80_000; // production's Usage cap (D6)
const USED: Record<string, number> = { near: 68_000, cap: CAP };

export function mock(
  scenario: string,
  used = USED[new URLSearchParams(location.search).get("usage") ?? ""] ?? 52_000,
  queued = new URLSearchParams(location.search).get("queue") ?? "",
  connect = new URLSearchParams(location.search).get("connect") ?? "",
): Bridge {
  let state = dated(structuredClone((SCENARIOS[scenario] ?? SCENARIOS.needs)()));
  window.REPORT_CATEGORIES = { form: "A form was filled wrong", answer: "An essay or an answer", sign_in: "Signing in, or a job-site account", app: "The app itself", other: "Something else" };
  const listeners = new Set<(s: ApplyState) => void>();
  const push = () => listeners.forEach((on) => on(structuredClone(state)));
  const later = (change: () => void, ms = 1500) => setTimeout(() => (change(), push()), ms);
  const find = (id: string) => state.items.find((i) => String(i.id) === id);
  // The Answer bank, as the Answers tab shows it: a draft to review, the student's own, a list answer.
  const bank: BankView = {
    bank_note: "",
    bank: [
      { question: "How did you hear about this job?", answer: "From WorkIt's Jobs page.", reviewed: false },
      { question: "Are you open to working in person?", answer: "Yes", reviewed: true },
      { question: "Which of these tools have you used?", answer: ["Git", "Docker"], reviewed: true },
    ],
  };
  return {
    bank: async () => structuredClone(bank),
    async changeBank(edit, { question, answer }) {
      await new Promise((done) => setTimeout(done, 400));
      // WorkIt's rule keeps out an answer about one company (answer_bank.Rule.kept_out).
      if (/Vercel/.test(`${question} ${answer ?? ""}`)) throw new Error("WorkIt keeps this out of your Answer bank. It names Vercel, so it stays on this form.");
      const found = bank.bank.find((e) => e.question === question);
      bank.bank = bank.bank.filter((e) => e.question !== question);
      if (edit !== "delete") bank.bank.push({ question, answer: answer ?? found?.answer ?? "", reviewed: true });
      return structuredClone(bank);
    },
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
    async submit(id) {
      // Apply presses Submit; the job site confirms a moment later.
      const held = state.tiles[Number(id.slice(5))];
      if (held) {
        Object.assign(held, { submitting: true, submit_said: "" });
        later(() => Object.assign(held, { tone: "submitted", submitting: false, again: false }), 1800);
      }
      push();
    },
    async cancelAuto(id) {
      const held = state.tiles[Number(id.slice(5))];
      if (held) Object.assign(held, { auto_at: null, auto_said: "Auto-submit cancelled: it's yours to approve." });
      push();
    },
    async letGo(id) {
      const held = state.tiles[Number(id.slice(5))];
      if (held) Object.assign(held, { let_go: true, again: false });
      push();
    },
    async remove(link) {
      const run = state.run!;
      if (!run.waiting?.some((w) => w.link === link)) throw new Error("That job has started already: it isn't waiting any more.");
      run.waiting = run.waiting.filter((w) => w.link !== link);
      run.queued = (run.queued ?? 1) - 1;
      push();
    },
    async stop(newOnly) {
      // Stop new ones only: no job waits to start any more, and every filled form stays open.
      if (newOnly) return void later(() => Object.assign(state.run!, { queued: 0, waiting: [] }), 300);
      // The run ends, and app_window.Bridge swaps in the idle board: the queue again.
      later(() => (state = structuredClone(SCENARIOS.start())), 800);
    },
    app: Promise.resolve({
      async queue() {
        if (queued === "unread") throw new Error("WorkIt Auto Apply couldn't read your queue (WorkIt didn't answer). Paste a link instead.");
        return queued === "empty" ? [] : QUEUE;
      },
      async matches(filters) {
        await new Promise((done) => setTimeout(done, 1200));
        const matches = new URLSearchParams(location.search).get("matches");
        if (matches === "unread") throw new Error("Add your experience on WorkIt first, so we can find jobs that fit you.");
        if (matches === "empty") return [];
        const q = filters.q?.[0]?.toLowerCase();
        return MATCHES.filter((m) => (!q || `${m.title} ${m.company}`.toLowerCase().includes(q)) && (!filters.job_type?.length || filters.job_type.includes(m.job_type!)) && (!filters.work_style?.length || filters.work_style.includes(m.work_style!)));
      },
      async start(links: string[]) {
        await new Promise((done) => setTimeout(done, 800));
        if (queued === "refused") throw new Error("Chrome isn't installed. Get it from google.com/chrome, then press Start again.");
        state = dated(structuredClone(SCENARIOS.quiet()));
        push();
        return links.length;
      },
      applied: async () => [
        { url: "https://vercel/1", company: "Vercel", title: "Software Engineer, New Grad", company_domain: "vercel.com", applied_at: "2026-11-15T09:00:00Z" },
        { url: "https://jobs.lever.co/palantir/1", company: "Palantir", title: "Forward Deployed Engineer Intern", company_domain: "palantir.com", applied_at: "2026-11-02T14:00:00Z" },
      ],
      status: async () => ({ running: false, said: "" }),
      usage: async (): Promise<Usage> => ({ used, cap: CAP, resets_at: new Date(Date.now() + 5 * 3600_000).toISOString() }),
      open_posting: async (url: string) => (window.open(url, "_blank"), true),
      settings: async () => alert("Settings: app_window.Bridge's page opens here."),
      review_report: async (_category: string, _note: string, contact: boolean, id: string, include: boolean) => ({
        parts: [`Your words${contact ? ", and WorkIt may email you about them" : ""}`, `Which application: ${id}`, ...(include ? ["answers.json (4 KB)", "form.png (310 KB)", "The step-by-step log (12 KB), your personal details hidden"] : [])],
      }),
      send_report: async () => ({ said: "Sent. WorkIt keeps your report until its problem is fixed, then deletes it." }),
    }),
  };
}
