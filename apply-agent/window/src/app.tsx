// The window: one screen that answers "what do I do now?".
import { CheckIcon, GearSixIcon } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";

import type { ApplyState } from "./apply.ts";
import type { App as AppMethods, Bridge, Queued } from "./bridge.ts";
import { TodoCard } from "./cards.tsx";
import { Button, Logo, cx } from "./ui.tsx";
import { type Job, type View, headline, limit, view } from "./view.ts";

type Fail = (message: string) => void;

export function App({ bridge }: { bridge: Bridge }) {
  const [state, setState] = useState<ApplyState | null>(null);
  const [app, setApp] = useState<AppMethods>({});
  const [page, setPage] = useState<"home" | "applied">("home");
  const [toast, setToast] = useState("");
  useEffect(() => bridge.watch(setState), [bridge]);
  useEffect(() => void bridge.app.then(setApp), [bridge]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 5000);
    return () => clearTimeout(t);
  }, [toast]);
  const v = useMemo(() => state && view(state), [state]);
  useEffect(() => {
    if (v) document.title = v.todo.length ? `WorkIt Auto Apply (${v.todo.length})` : "WorkIt Auto Apply";
  }, [v]);
  if (!v) return null;
  // No run going: the queue, when the window has one to show (#613's app methods).
  const first = !!app.queue && !v.todo.length && !v.working.length && !v.queued && !v.applied.length;
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 flex h-[52px] items-center gap-2 border-b border-border bg-app/90 pr-5 pl-[84px] backdrop-blur">
        <button className="flex cursor-pointer items-center gap-2 font-semibold" onClick={() => setPage("home")}>
          <span className="grid size-[22px] place-items-center rounded-md bg-brand text-xs text-on-brand">W</span>
          WorkIt Auto Apply
        </button>
        <nav className="ml-auto flex items-center gap-1 text-[13px]">
          {!first && (
            <Button tone="quiet" className={cx("h-8 px-3", page === "applied" && "bg-hover text-ink")} onClick={() => setPage(page === "applied" ? "home" : "applied")}>
              Applied
            </Button>
          )}
          {app.settings && (
            <Button tone="quiet" className="h-8 px-3" onClick={() => app.settings!().catch((e: Error) => setToast(e.message))}>
              <GearSixIcon className="size-4" /> Settings
            </Button>
          )}
        </nav>
      </header>
      <main className="mx-auto max-w-[600px] px-6 pt-12 pb-16">
        {first ? <Start app={app} /> : page === "applied" ? <Applied jobs={v.applied} /> : <Home v={v} bridge={bridge} fail={setToast} />}
        <Limit app={app} />
      </main>
      {toast && <div className="rise fixed right-4 bottom-4 rounded-card bg-ink px-4 py-2.5 text-[13px] text-white shadow-[var(--shadow-focus)]">{toast}</div>}
    </div>
  );
}

// The Usage cap in words, read again each minute: nothing until the student is close to it.
function Limit({ app }: { app: AppMethods }) {
  const [said, setSaid] = useState("");
  useEffect(() => {
    if (!app.usage) return;
    const read = () => app.usage!().then((usage) => setSaid(limit(usage)), () => setSaid(""));
    read();
    const t = setInterval(read, 60_000);
    return () => clearInterval(t);
  }, [app]);
  return said ? <p className="mt-8 text-[13px] text-ink-faint">{said}</p> : null;
}

function Home({ v, bridge, fail }: { v: View; bridge: Bridge; fail: Fail }) {
  // Which to-do is on top. Skip moves it to the next one; a done one leaves the pile by itself.
  const [at, setAt] = useState(0);
  const i = v.todo.length ? at % v.todo.length : 0;
  return (
    <>
      <h1 className="text-[28px] font-bold tracking-[-0.025em]">{headline(v)}</h1>
      {v.todo.length ? (
        <div className="mt-6">
          <TodoCard job={v.todo[i]} bridge={bridge} at={i} of={v.todo.length} skip={() => setAt(i + 1)} fail={fail} />
        </div>
      ) : (
        <div className="rise mt-6 flex items-center gap-4 rounded-[18px] border border-border bg-panel px-6 py-5">
          <span className="grid size-10 shrink-0 place-items-center rounded-full bg-positive-tint text-positive-ink">
            <CheckIcon weight="bold" className="size-5" />
          </span>
          <p className="flex-1 text-ink-meta">
            {v.working.length || v.queued ? "Nothing needs you right now. We'll send a notification when something does." : "Every application is done."}
          </p>
        </div>
      )}
      {(v.working.length > 0 || v.queued > 0) && (
        <section className="mt-10">
          <h3 className="mb-2 text-[13px] font-semibold text-ink-meta">Still working on</h3>
          {v.working.map((job) => (
            <Row key={job.key} job={job} />
          ))}
          {v.queued > 0 && <p className="px-0.5 pt-2 text-[13px] text-ink-faint">and {v.queued} more waiting to start</p>}
        </section>
      )}
    </>
  );
}

function Row({ job }: { job: Job }) {
  const submitted = job.status === "submitted";
  return (
    <div className="flex items-center gap-3 py-2.5">
      <Logo company={job.company} size={32} />
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{job.company}</div>
        <div className="truncate text-xs text-ink-meta">{job.role}</div>
      </div>
      {submitted ? (
        <span className="flex items-center gap-1.5 text-[13px] font-semibold text-positive-ink">
          <CheckIcon weight="bold" className="size-3.5" /> Submitted
        </span>
      ) : (
        <span className="w-28 text-right">
          <span className="block text-xs text-ink-meta">{job.status === "checking" ? "Checking answers" : "Filling out"}</span>
          <span className="mt-1.5 block h-1 overflow-hidden rounded-full bg-border">
            <span
              className={cx("block h-full rounded-full bg-brand transition-[width] duration-700", job.status === "checking" && "animate-pulse")}
              style={{ width: `${job.status === "checking" ? 95 : Math.max(8, (job.progress ?? 0.3) * 100)}%` }}
            />
          </span>
        </span>
      )}
    </div>
  );
}

// The student's Auto Apply queue on WorkIt, every job ticked, and one pasted link: Start runs them.
function Start({ app }: { app: AppMethods }) {
  const [queue, setQueue] = useState<Queued[]>([]);
  const [picked, setPicked] = useState<boolean[]>([]);
  const [link, setLink] = useState("");
  const [said, setSaid] = useState("");
  useEffect(() => {
    app.queue!().then(
      (jobs) => (setQueue(jobs), setPicked(jobs.map(() => true))),
      (e: Error) => setSaid(e.message),
    );
    app.status?.().then((s) => s.said && setSaid(s.said));
  }, [app]);
  const pasted = /^https?:\/\//.test(link.trim()) ? [link.trim()] : [];
  const links = [...queue.filter((_, i) => picked[i]).map((q) => q.url), ...pasted];
  return (
    <div className="pt-4">
      <h1 className="text-center text-[32px] font-bold tracking-[-0.025em]">What should we apply to?</h1>
      <p className="mt-1.5 text-center text-[15px] text-ink-meta">We fill out the applications. You check each one and press Submit.</p>
      {queue.length > 0 && (
        <div className="mt-8 rounded-[14px] border border-border bg-panel px-4 py-1.5">
          {queue.map((q, i) => (
            <label key={q.url} className="flex cursor-pointer items-center gap-3 border-b border-border py-2.5 last:border-0">
              <input type="checkbox" checked={picked[i]} onChange={() => setPicked(picked.map((p, j) => (j === i ? !p : p)))} className="size-[18px] accent-brand" />
              <Logo company={q.company} size={32} />
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{q.title}</span>
                <span className="block text-xs text-ink-meta">{q.company}</span>
              </span>
            </label>
          ))}
        </div>
      )}
      <input
        value={link}
        onChange={(e) => setLink(e.target.value)}
        placeholder={queue.length ? "Or paste a job link" : "Paste a job link"}
        className="mt-3 h-10 w-full rounded-control border border-border-surface bg-panel px-3.5 outline-none focus:border-brand"
      />
      <Button
        tone="primary"
        size="lg"
        className="mt-6 w-full"
        disabled={!links.length}
        onClick={() => app.start!(links).then(() => setSaid("Starting…"), (e: Error) => setSaid(e.message))}
      >
        Start applying to {links.length} {links.length === 1 ? "job" : "jobs"}
      </Button>
      {said && (
        <p role="alert" className="mt-3 text-center text-[13px] text-ink-meta">
          {said}
        </p>
      )}
      <p className="mt-4 text-center text-xs text-ink-faint">WorkIt never presses Submit for you.</p>
    </div>
  );
}

function Applied({ jobs }: { jobs: Job[] }) {
  return (
    <>
      <h1 className="text-[28px] font-bold tracking-[-0.025em]">Applied</h1>
      <p className="mt-1 text-[15px] text-ink-meta">Everything you submitted. It's in your Tracker on WorkIt too.</p>
      <div className="mt-6">{jobs.length ? jobs.map((job) => <Row key={job.key} job={job} />) : <p className="text-ink-meta">Nothing submitted yet.</p>}</div>
    </>
  );
}
