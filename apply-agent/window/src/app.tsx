// The window: one screen that answers "what do I do now?".
import { ArrowClockwiseIcon, CheckIcon, GearSixIcon, StopIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";

import type { ApplyState, Run } from "./apply.ts";
import type { App as AppMethods, Bridge, Queued, Usage } from "./bridge.ts";
import { TodoCard } from "./cards.tsx";
import { Button, Logo, cx, pressed } from "./ui.tsx";
import { type Job, type View, type Waits, chosen, headline, limit, queueNote, startWords, view } from "./view.ts";

type Fail = (message: string) => void;

export function App({ bridge }: { bridge: Bridge }) {
  const [state, setState] = useState<ApplyState | null>(null);
  const [app, setApp] = useState<AppMethods>({});
  const [page, setPage] = useState<"home" | "applied">("home");
  const [toast, setToast] = useState("");
  const [lost, setLost] = useState(false); // /state's last ask got no answer: Apply stopped, or is restarting
  useEffect(
    () =>
      bridge.watch(
        (s) => (setState(s), setLost(false)),
        () => setLost(true),
      ),
    [bridge],
  );
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
  if (!v) return <Connecting lost={lost} />;
  // No run going: the queue, when the window has one to show (#613's app methods).
  const first = !!app.queue && !v.todo.length && !v.working.length && !v.queued && !v.applied.length && !v.stopped.length;
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 flex h-[52px] items-center gap-2 border-b border-border bg-app/90 pr-5 pl-[84px] backdrop-blur">
        <button className="flex cursor-pointer items-center gap-2 font-semibold" onClick={() => setPage("home")}>
          <span className="grid size-[22px] place-items-center rounded-md bg-brand text-xs text-on-brand">W</span>
          WorkIt Auto Apply
        </button>
        <nav className="ml-auto flex items-center gap-1 text-[13px]">
          {v.running && !first && <Stop bridge={bridge} fail={setToast} />}
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
        {lost && (
          <p role="alert" className="mb-6 rounded-[14px] border border-border bg-panel px-4 py-3 text-[13px] text-ink-meta">
            {NOT_RUNNING} This window shows what it last heard, and catches up once Apply is back.
          </p>
        )}
        {first ? <Start app={app} /> : page === "applied" ? <Applied jobs={v.applied} /> : <Home v={v} bridge={bridge} fail={setToast} />}
        <Limit app={app} run={state?.run} />
      </main>
      {toast && <div role="alert" className="rise fixed right-4 bottom-4 rounded-card bg-ink px-4 py-2.5 text-[13px] text-white shadow-[var(--shadow-focus)]">{toast}</div>}
    </div>
  );
}

const NOT_RUNNING = "WorkIt Auto Apply isn't answering. If you quit it, open it again.";

// Before Apply's first state: never a blank page. If Apply doesn't answer at all, say so.
function Connecting({ lost }: { lost: boolean }) {
  return (
    <div role="status" className="grid min-h-dvh place-items-center px-6 text-center">
      <div>
        <span className="mx-auto grid size-10 place-items-center rounded-xl bg-brand text-lg font-semibold text-on-brand">W</span>
        <p className={cx("mt-4 text-[15px] text-ink-meta", !lost && "animate-pulse")}>{lost ? NOT_RUNNING : "Connecting to WorkIt Auto Apply…"}</p>
      </div>
    </div>
  );
}

// Stop applying: asked once more, since the run ends. Nothing is submitted, and filled forms stay as they are;
// #613 then shows the queue again (the page reloads).
function Stop({ bridge, fail }: { bridge: Bridge; fail: Fail }) {
  const [step, setStep] = useState<"idle" | "asking" | "stopping">("idle");
  const stop = () => {
    setStep("stopping");
    bridge.stop().catch((e: Error) => (setStep("idle"), fail(e.message)));
  };
  if (step === "idle")
    return (
      <Button tone="quiet" className="h-8 px-3" onClick={() => setStep("asking")}>
        <StopIcon className="size-4" /> Stop applying
      </Button>
    );
  return (
    <span role="group" aria-label="Stop applying" className="flex items-center gap-1">
      <span className="px-1 text-ink-meta">{step === "stopping" ? "Stopping…" : "Stop every application? Nothing gets submitted."}</span>
      {step === "asking" && (
        <>
          <Button tone="primary" className="h-8 px-3" onClick={stop}>
            Stop
          </Button>
          <Button tone="quiet" className="h-8 px-3" onClick={() => setStep("idle")}>
            Keep going
          </Button>
        </>
      )}
    </span>
  );
}

// The Usage cap in words, read again each minute: nothing until the student is close to it. A run Apply paused
// at the cap says so from /state as well.
function Limit({ app, run }: { app: AppMethods; run?: Run }) {
  const [usage, setUsage] = useState<Usage | null>(null);
  useEffect(() => {
    if (!app.usage) return;
    const read = () => app.usage!().then(setUsage, () => setUsage(null));
    read();
    const t = setInterval(read, 60_000);
    return () => clearInterval(t);
  }, [app]);
  const said = limit(usage, undefined, run);
  return said ? <p className="mt-8 text-[13px] text-ink-faint">{said}</p> : null;
}

function Home({ v, bridge, fail }: { v: View; bridge: Bridge; fail: Fail }) {
  // Which to-do is on top. Skip moves it to the next one; a done one leaves the pile by itself.
  const [at, setAt] = useState(0);
  const i = v.todo.length ? at % v.todo.length : 0;
  const more = v.todo.length > 1;
  useEffect(() => {
    if (!more) return;
    const down = (e: KeyboardEvent) => pressed(e, 0) === "skip" && setAt(i + 1);
    window.addEventListener("keydown", down);
    return () => window.removeEventListener("keydown", down);
  }, [more, i]);
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
      {(v.working.length > 0 || v.queued > 0 || v.waiting.length > 0) && (
        <section className="mt-10">
          <h3 className="mb-2 text-[13px] font-semibold text-ink-meta">Still working on</h3>
          {v.working.map((job) => (
            <Row key={job.key} job={job} />
          ))}
          {v.queued > 0 && <p className="px-0.5 pt-2 text-[13px] text-ink-faint">and {v.queued} more waiting to start</p>}
          {v.waiting.map((w) => (
            <Waiting key={w.link} job={w} bridge={bridge} fail={fail} />
          ))}
        </section>
      )}
      {v.stopped.length > 0 && (
        <section className="mt-10">
          <h3 className="mb-2 text-[13px] font-semibold text-ink-meta">Didn't go through</h3>
          {v.stopped.map((job) => (
            <Stopped key={job.key} job={job} bridge={bridge} fail={fail} />
          ))}
        </section>
      )}
    </>
  );
}

// A job that failed or was skipped, with why, and Try again where Apply still holds its form to fill anew. Once
// pressed, the job moves to "Still working on" as Apply starts filling it.
function Stopped({ job, bridge, fail }: { job: Job; bridge: Bridge; fail: Fail }) {
  const [trying, setTrying] = useState(false);
  const retry = () => {
    setTrying(true);
    bridge.fillAgain(job.retry!).catch((e: Error) => (setTrying(false), fail(e.message)));
  };
  return (
    <div className="flex items-center gap-3 py-2.5">
      <Logo company={job.company} src={job.source} size={32} />
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{job.company}</div>
        <div className="truncate text-xs text-ink-meta">{job.role}</div>
        <div className="mt-0.5 text-xs text-ink-faint">{job.reason}</div>
      </div>
      {job.retry && (
        <Button className="h-8 px-3 text-[13px]" disabled={trying} onClick={retry}>
          <ArrowClockwiseIcon className="size-3.5" /> {trying ? "Trying again…" : "Try again"}
        </Button>
      )}
    </div>
  );
}

// A job not started yet. Remove takes it out of this run; it leaves the list once Apply drops it.
function Waiting({ job, bridge, fail }: { job: Waits; bridge: Bridge; fail: Fail }) {
  const [removing, setRemoving] = useState(false);
  const remove = () => {
    setRemoving(true);
    bridge.remove(job.link).catch((e: Error) => (setRemoving(false), fail(e.message)));
  };
  return (
    <div className={cx("flex items-center gap-3 py-2", removing && "opacity-50")}>
      <Logo company={job.company} src={job.source} size={28} />
      <div className="min-w-0 flex-1">
        <div className="truncate text-[13px] font-semibold">{job.company}</div>
        {job.role && <div className="truncate text-xs text-ink-meta">{job.role}</div>}
      </div>
      <Button tone="quiet" className="h-8 px-3 text-[13px]" disabled={removing} onClick={remove} aria-label={`Remove ${job.company}`}>
        <XIcon className="size-3.5" /> Remove
      </Button>
    </div>
  );
}

function Row({ job }: { job: Job }) {
  const submitted = job.status === "submitted";
  return (
    <div className="flex items-center gap-3 py-2.5">
      <Logo company={job.company} src={job.source} size={32} />
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

// The student's Auto Apply queue on WorkIt, every job ticked, and one pasted link: Start runs them. Once it is
// pressed the queue leaves the view; #613 swaps in the run's board, and this screen again when the run ends.
function Start({ app }: { app: AppMethods }) {
  const [queue, setQueue] = useState<Queued[] | Error | null>(null);
  const [ticked, setTicked] = useState<boolean[]>([]);
  const [link, setLink] = useState("");
  const [started, setStarted] = useState(false);
  const [said, setSaid] = useState(""); // why the last run couldn't start or stopped
  useEffect(() => {
    app.queue!().then(
      (jobs) => (setQueue(jobs), setTicked(jobs.map(() => true))),
      (e: Error) => setQueue(e),
    );
    app.status?.().then(
      (s) => s.said && setSaid(s.said),
      () => {},
    );
  }, [app]);
  const jobs = Array.isArray(queue) ? queue : [];
  const links = chosen(jobs, ticked, link);
  const note = queueNote(queue);
  const start = () => {
    setStarted(true);
    setSaid("");
    app.start!(links).catch((e: Error) => (setStarted(false), setSaid(e.message)));
  };
  return (
    <div className="pt-4">
      <h1 className="text-center text-[32px] font-bold tracking-[-0.025em]">What should we apply to?</h1>
      <p className="mt-1.5 text-center text-[15px] text-ink-meta">We fill out the applications. You check each one and press Submit.</p>
      {started ? (
        <p role="status" className="mt-8 text-center text-ink-meta">
          Starting {links.length === 1 ? "your application" : `${links.length} applications`}…
        </p>
      ) : (
        <>
          {jobs.length > 0 && (
            <div className="mt-8 rounded-[14px] border border-border bg-panel px-4 py-1.5">
              {jobs.map((q, i) => (
                <label key={q.url} className="flex cursor-pointer items-center gap-3 border-b border-border py-2.5 last:border-0">
                  <input
                    type="checkbox"
                    checked={!!ticked[i]}
                    onChange={() => setTicked(ticked.map((t, j) => (j === i ? !t : t)))}
                    className="size-[18px] accent-brand"
                  />
                  <Logo company={q.company} src={q} size={32} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold">{q.title || "A job"}</span>
                    <span className="block text-xs text-ink-meta">{q.company}</span>
                  </span>
                </label>
              ))}
            </div>
          )}
          {note && <p className="mt-8 rounded-[14px] border border-border bg-panel px-4 py-3.5 text-center text-[13px] text-ink-meta">{note}</p>}
          <input
            value={link}
            onChange={(e) => setLink(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && links.length > 0 && start()}
            placeholder={jobs.length ? "Or paste a job link" : "Paste a job link"}
            aria-label="A job posting's link"
            className={cx("h-10 w-full rounded-control border border-border-surface bg-panel px-3.5 outline-none focus:border-brand", queue ? "mt-3" : "mt-8")}
          />
        </>
      )}
      <Button tone="primary" size="lg" className="mt-6 w-full" disabled={started || !links.length} onClick={start}>
        {startWords(links.length)}
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
