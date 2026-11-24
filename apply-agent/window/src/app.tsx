// The window: one screen that answers "what do I do now?".
import { ArrowClockwiseIcon, CheckIcon, GearSixIcon, MagnifyingGlassIcon, PlusIcon, StopCircleIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";

import type { ApplyState, Run } from "./apply.ts";
import type { AppliedJob, App as AppMethods, Bridge, Queued, Usage } from "./bridge.ts";
import { TodoCard } from "./cards.tsx";
import { Find } from "./find.tsx";
import { Report } from "./report.tsx";
import { Button, Logo, cx, pressed } from "./ui.tsx";
import { type Job, type View, type Waits, addsJobs, appliedJobs, bar, chosen, headline, limit, notStarted, queueNote, STARTING_WAIT, startWords, usageLine, usedShare, view } from "./view.ts";
import { said } from "./words.ts";

type Fail = (message: string) => void;

export function App({ bridge }: { bridge: Bridge }) {
  const [state, setState] = useState<ApplyState | null>(null);
  const [app, setApp] = useState<AppMethods>({});
  const [page, setPage] = useState<"home" | "applied" | "add" | "find">("home");
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
  // A run started from Find jobs or the queue: its board is home now.
  useEffect(() => {
    if (v?.running && (page === "add" || page === "find")) setPage("home");
  }, [v?.running, page]);
  if (!v) return <Connecting lost={lost} />;
  // No run going: the queue, when the window has one to show (app_window.Bridge's app methods).
  // Add jobs brings it back once there is something else to show.
  const first =
    !!app.queue &&
    page !== "applied" &&
    (page === "add" || page === "find" || (!v.todo.length && !v.working.length && !v.queued && !v.applied.length && !v.stopped.length));
  const add = () => setPage("add");
  // Find jobs (find.tsx) is where a student picks jobs, when the window can read their matches; the queue and a
  // pasted link stay a click away from it.
  const finds = !!app.matches && page !== "add";
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 flex h-13 items-center gap-2 border-b border-border bg-app/90 pr-5 pl-21 backdrop-blur">
        <button className="flex cursor-pointer items-center gap-2 font-semibold" onClick={() => setPage("home")}>
          <span className="grid size-5.5 place-items-center rounded-control bg-brand text-note text-on-brand">W</span>
          WorkIt Auto Apply
        </button>
        <nav className="ml-auto flex items-center gap-1 text-note">
          {v.running && !first && <Stop bridge={bridge} fail={setToast} />}
          {addsJobs(v, !!app.start) && !!app.matches && (
            <Button tone="quiet" className={cx("h-8 px-3", first && finds && "bg-hover text-ink")} onClick={() => setPage("find")}>
              <MagnifyingGlassIcon className="size-4" /> Find jobs
            </Button>
          )}
          {addsJobs(v, !!app.start) && !app.matches && !first && (
            <Button tone="quiet" className="h-8 px-3" onClick={add}>
              <PlusIcon className="size-4" /> Add jobs
            </Button>
          )}
          {(!first || app.applied) && (
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
      <main className={cx("mx-auto px-6 pb-16", first && finds ? "max-w-3xl pt-6" : "max-w-window pt-12")}>
        <Limit app={app} run={state?.run} filling={v.working.map((j) => j.key).join("\n")} />
        {lost && (
          <p role="alert" className="mb-6 rounded-card border border-border bg-panel px-4 py-3 text-note text-ink-meta">
            {NOT_RUNNING} This window shows what it last heard, and catches up once Apply is back.
          </p>
        )}
        {page === "applied" ? (
          <Applied jobs={v.applied} app={app} />
        ) : first && finds ? (
          <Find app={app} queue={add} />
        ) : first ? (
          <Start app={app} back={page === "add" ? () => setPage("home") : undefined} />
        ) : (
          <Home v={v} bridge={bridge} app={app} fail={setToast} add={app.queue && addsJobs(v, !!app.start) ? add : undefined} />
        )}
      </main>
      {toast && <div role="alert" className="rise fixed right-4 bottom-4 rounded-card bg-ink px-4 py-2.5 text-note text-on-brand shadow-lift">{toast}</div>}
    </div>
  );
}

const NOT_RUNNING = "WorkIt Auto Apply isn't answering. If you quit it, open it again.";

// Before Apply's first state: never a blank page. If Apply doesn't answer at all, say so.
function Connecting({ lost }: { lost: boolean }) {
  return (
    <div role="status" className="grid min-h-dvh place-items-center px-6 text-center">
      <div>
        <span className="mx-auto grid size-10 place-items-center rounded-card bg-brand text-subtitle font-semibold text-on-brand">W</span>
        <p className={cx("mt-4 text-body text-ink-meta", !lost && "animate-pulse")}>{lost ? NOT_RUNNING : "Connecting to WorkIt Auto Apply…"}</p>
      </div>
    </div>
  );
}

// Stop applying: asked once more, since the run ends. Nothing is submitted, and filled forms stay as they are;
// app_window.Bridge then shows the queue again (the page reloads).
function Stop({ bridge, fail }: { bridge: Bridge; fail: Fail }) {
  const [step, setStep] = useState<"idle" | "asking" | "stopping">("idle");
  const stop = () => {
    setStep("stopping");
    bridge.stop().catch((e: Error) => (setStep("idle"), fail(e.message)));
  };
  if (step === "idle")
    return (
      <Button tone="quiet" className="h-8 px-3" onClick={() => setStep("asking")}>
        <StopCircleIcon className="size-4" /> Stop applying
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

// Today's usage: a bar of the share of the Usage cap used, never a token count. It is read each minute, and again
// whenever a form leaves "Still working on" (`filling` changes), so the bar moves on by what that form used. A failed
// reading keeps the last one, so a WorkIt hiccup doesn't make the bar vanish; a reading from before a newer one
// started is dropped (`live`), so a slow one can't move the bar back. From 80% the words say so; at the cap (or a run
// paused at it) a banner on top, so no "We're on it" below reads as if applying goes on.
function Limit({ app, run, filling }: { app: AppMethods; run?: Run; filling: string }) {
  const [usage, setUsage] = useState<Usage | null>(null);
  useEffect(() => {
    if (!app.usage) return;
    let live = true;
    const read = () => app.usage!().then((u) => live && setUsage(u), () => {});
    read();
    const t = setInterval(read, 60_000);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, [app, filling]);
  const line = limit(usage, undefined, run);
  const reached = !!run?.paused || (!!usage && usage.used >= usage.cap);
  if (!usage && !line) return null;
  const share = usage ? usedShare(usage) : 0;
  return (
    <section className="mb-6">
      {reached && line && <p role="status" className="mb-3 rounded-card bg-warning-tint px-4 py-3 font-semibold text-warning-deep">{line}</p>}
      {usage && (
        <>
          <div className="flex items-baseline justify-between gap-4 text-note text-ink-meta">
            <span>Today's usage</span>
            <span>{usageLine(usage)}</span>
          </div>
          <div role="progressbar" aria-label="Today's usage" aria-valuemin={0} aria-valuemax={100} aria-valuenow={share} className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-border">
            <span className={cx("block h-full rounded-full transition-[width] duration-700", share >= 80 ? "bg-warning-fill" : "bg-brand")} style={{ width: `${share}%` }} />
          </div>
          {!reached && line && <p role="status" className="mt-1.5 text-note text-ink-meta">{line}</p>}
        </>
      )}
    </section>
  );
}

function Home({ v, bridge, app, fail, add }: { v: View; bridge: Bridge; app: AppMethods; fail: Fail; add?: () => void }) {
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
      <h1 className="text-heading">{headline(v)}</h1>
      {v.todo.length ? (
        <div className="mt-6">
          <TodoCard job={v.todo[i]} bridge={bridge} app={app} at={i} of={v.todo.length} skip={() => setAt(i + 1)} fail={fail} />
        </div>
      ) : (
        <div className="rise mt-6 flex items-center gap-4 rounded-shell border border-border bg-panel px-6 py-5">
          <span className="grid size-10 shrink-0 place-items-center rounded-full bg-positive-tint text-positive-ink">
            <CheckIcon weight="bold" className="size-5" />
          </span>
          <p className="flex-1 text-ink-meta">
            {v.working.length || v.queued
              ? "Nothing needs you right now. We'll send a notification when something does."
              : v.stopped.length
                ? "The reason for each one is below. Try again where it's offered."
                : "Every application is done."}
          </p>
          {add && !v.working.length && !v.queued && (
            <Button tone="primary" onClick={add}>
              <PlusIcon className="size-4" /> Add jobs
            </Button>
          )}
        </div>
      )}
      {(v.working.length > 0 || v.queued > 0 || v.waiting.length > 0) && (
        <section className="mt-10">
          <h3 className="mb-2 text-note font-semibold text-ink-meta">Still working on</h3>
          {v.working.map((job) => (
            <Row key={job.key} job={job} watch={app.frames} />
          ))}
          {v.queued > 0 && <p className="px-0.5 pt-2 text-note text-ink-meta">and {v.queued} more waiting to start</p>}
          {v.waiting.map((w) => (
            <Waiting key={w.link} job={w} bridge={bridge} fail={fail} />
          ))}
        </section>
      )}
      {v.stopped.length > 0 && (
        <section className="mt-10">
          <h3 className="mb-2 text-note font-semibold text-ink-meta">Didn't go through</h3>
          {v.stopped.map((job) => (
            <Stopped key={job.key} job={job} bridge={bridge} app={app} fail={fail} />
          ))}
        </section>
      )}
    </>
  );
}

// A job that failed or was skipped, with why, and Try again where Apply still holds its form to fill anew. Once
// pressed, the job moves to "Still working on" as Apply starts filling it.
function Stopped({ job, bridge, app, fail }: { job: Job; bridge: Bridge; app: AppMethods; fail: Fail }) {
  const [trying, setTrying] = useState(false);
  const retry = () => {
    setTrying(true);
    bridge.fillAgain(job.retry!).catch((e: Error) => (setTrying(false), fail(e.message)));
  };
  return (
    <div className="py-2.5">
      <div className="flex items-center gap-3">
        <Logo company={job.company} src={job.source} size="md" />
        <div className="min-w-0 flex-1">
          <div className="font-semibold">{job.company}</div>
          <div className="truncate text-note text-ink-meta">{job.role}</div>
          <div className="mt-0.5 text-note text-ink-meta">{job.reason}</div>
        </div>
        {job.retry && (
          <Button className="h-8 px-3 text-note" disabled={trying} onClick={retry}>
            <ArrowClockwiseIcon className="size-3.5" /> {trying ? "Trying again…" : "Try again"}
          </Button>
        )}
      </div>
      <Under job={job} app={app} />
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
    <div className={cx("flex items-center gap-3 py-2.5", removing && "opacity-50")}>
      <Logo company={job.company} src={job.source} size="md" />
      <div className="min-w-0 flex-1">
        <div className="truncate font-semibold">{job.company}</div>
        {job.role && <div className="truncate text-note text-ink-meta">{job.role}</div>}
      </div>
      <Button tone="quiet" className="h-8 px-3 text-note" disabled={removing} onClick={remove} aria-label={`Remove ${job.company}`}>
        <XIcon className="size-3.5" /> Remove
      </Button>
    </div>
  );
}

// `app` on the Applied page, where a submitted Application has Report a problem; none for a job still being filled.
// `watch`, on a job still being filled: Watch shows its form as the Worker's Chrome has it now.
function Row({ job, app, watch }: { job: Job; app?: AppMethods; watch?: AppMethods["frames"] }) {
  const submitted = job.status === "submitted";
  const [watching, setWatching] = useState(false);
  const live = !!watch && job.worker !== undefined && !submitted;
  return (
    <div className="py-2.5">
      <div className="flex items-center gap-3">
        <Logo company={job.company} src={job.source} size="md" />
        <div className="min-w-0 flex-1">
          <div className="font-semibold">{job.company}</div>
          <div className="truncate text-note text-ink-meta">{job.role}</div>
        </div>
        {submitted ? (
          <span className="flex items-center gap-1.5 text-note font-semibold text-positive-ink">
            <CheckIcon weight="bold" className="size-3.5" /> Submitted
          </span>
        ) : (
          <span className="w-28 text-right">
            {live && (
              <button onClick={() => setWatching(!watching)} className="mb-1 text-note font-semibold text-brand-ink hover:underline">
                {watching ? "Hide" : "Watch"}
              </button>
            )}
            <span className="block text-note text-ink-meta">{job.status === "checking" ? "Checking answers" : "Filling out"}</span>
            <span className="mt-1.5 block h-1 overflow-hidden rounded-full bg-border">
              {bar(job) === "unknown" ? (
                <span className="sweep block h-full w-1/3 rounded-full bg-brand" />
              ) : (
                <span className="block h-full rounded-full bg-brand transition-[width] duration-700" style={{ width: `${Math.max(8, (bar(job) as number) * 100)}%` }} />
              )}
            </span>
          </span>
        )}
      </div>
      {app && <Under job={job} app={app} />}
      {live && watching && <Live tile={job.worker!} frames={watch!} />}
    </div>
  );
}

// A form as its Worker's Chrome shows it, newest screen first: each call waits for a newer one than it has.
function Live({ tile, frames }: { tile: number; frames: NonNullable<AppMethods["frames"]> }) {
  const [shot, setShot] = useState("");
  useEffect(() => {
    let on = true;
    const seen: Record<number, number> = {}; // every tile's last screen, or each call answers at once with the others'
    (async () => {
      while (on) {
        const found = await frames(seen).catch(() => []);
        if (!on) return;
        for (const f of found) seen[f.tile] = f.number;
        const mine = found.find((f) => f.tile === tile);
        if (mine) setShot(`data:image/jpeg;base64,${mine.jpeg}`);
        if (!found.length) await new Promise((r) => setTimeout(r, 500));
      }
    })();
    return () => void (on = false);
  }, [tile, frames]);
  return (
    <div className="mt-3 overflow-hidden rounded-card border border-border bg-panel">
      {shot ? (
        <img src={shot} alt="The form as it's being filled" className="block w-full" />
      ) : (
        <p className="px-4 py-10 text-center text-note text-ink-meta">Waiting for the form's screen…</p>
      )}
    </div>
  );
}

// A row's Report a problem, under its text: open, its form spans the row and leaves the logo and button in place.
const Under = ({ job, app }: { job: Job; app: AppMethods }) => (
  <div className="pl-11">
    <Report job={job} app={app} />
  </div>
);

// The student's Auto Apply queue on WorkIt, every job ticked, and one pasted link: Start runs them. Once it is
// pressed the queue leaves the view; app_window.Bridge swaps in the run's board, and this screen again when the run ends.
function Start({ app, back }: { app: AppMethods; back?: () => void }) {
  const [queue, setQueue] = useState<Queued[] | Error | null>(null);
  const [ticked, setTicked] = useState<boolean[]>([]);
  const [link, setLink] = useState("");
  const [started, setStarted] = useState(false);
  const [why, setWhy] = useState(""); // why the last run couldn't start or stopped
  useEffect(() => {
    app.queue!().then(
      (jobs) => (setQueue(jobs), setTicked(jobs.map(() => true))),
      (e: Error) => setQueue(e),
    );
    app.status?.().then(
      (s) => s.said && setWhy(said(s.said)),
      () => {},
    );
  }, [app]);
  const jobs = Array.isArray(queue) ? queue : [];
  const links = chosen(jobs, ticked, link);
  const note = queueNote(queue);
  // A run whose board never shows: once STARTING_WAIT has passed, and each 5 s after, ask whether it still goes.
  useEffect(() => {
    if (!started || !app.status) return;
    let live = true;
    let timer = setTimeout(function look() {
      app.status!().then(notStarted, (e: Error) => notStarted(e)).then((line) => {
        if (!live) return;
        if (line) setStarted(false), setWhy(line);
        else timer = setTimeout(look, 5_000);
      });
    }, STARTING_WAIT);
    return () => ((live = false), clearTimeout(timer));
  }, [started, app]);
  const start = () => {
    setStarted(true);
    setWhy("");
    app.start!(links).catch((e: Error) => (setStarted(false), setWhy(e.message)));
  };
  return (
    <div className="pt-4">
      <h1 className="text-center text-heading">What should we apply to?</h1>
      <p className="mt-1.5 text-center text-body text-ink-meta">We fill out the applications. You check each one and press Submit.</p>
      {started ? (
        <p role="status" className="mt-8 text-center text-ink-meta">
          Starting {links.length === 1 ? "your application" : `${links.length} applications`}…
        </p>
      ) : (
        <>
          {jobs.length > 0 && (
            <div className="mt-8 rounded-card border border-border bg-panel px-4 py-1.5">
              {jobs.map((q, i) => (
                <label key={q.url} className="flex cursor-pointer items-center gap-3 border-b border-border py-2.5 last:border-0">
                  <input
                    type="checkbox"
                    checked={!!ticked[i]}
                    onChange={() => setTicked(ticked.map((t, j) => (j === i ? !t : t)))}
                    className="size-4.5 accent-brand"
                  />
                  <Logo company={q.company ?? ""} src={q} size="md" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold">{q.title || "A job"}</span>
                    <span className="block text-note text-ink-meta">{q.company}</span>
                  </span>
                </label>
              ))}
            </div>
          )}
          {note && <p className="mt-8 rounded-card border border-border bg-panel px-4 py-3.5 text-center text-note text-ink-meta">{note}</p>}
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
      {why && (
        <p role="alert" className="mt-3 text-center text-note text-ink-meta">
          {why}
        </p>
      )}
      <p className="mt-4 text-center text-note text-ink-meta">WorkIt never presses Submit for you.</p>
      {back && !started && (
        <div className="mt-6 text-center">
          <Button tone="quiet" onClick={back}>
            Back to your applications
          </Button>
        </div>
      )}
    </div>
  );
}

// What the student submitted: this run's, then what WorkIt has from before (app_window.Bridge.applied), each once.
function Applied({ jobs, app }: { jobs: Job[]; app: AppMethods }) {
  // undefined while WorkIt's list is still coming, so a slow read never says "Nothing submitted yet."
  const [earlier, setEarlier] = useState<AppliedJob[] | null | undefined>(app.applied ? undefined : null);
  useEffect(() => {
    app.applied?.().then(setEarlier, () => setEarlier(null));
  }, [app]);
  const all = appliedJobs(jobs, earlier ?? null);
  return (
    <>
      <h1 className="text-heading">Applied</h1>
      <p className="mt-1 text-body text-ink-meta">Everything you submitted, today and before. It's in your Tracker on WorkIt too.</p>
      <div className="mt-6">{all.length ? (
          all.map((job) => <Row key={job.key} job={job} app={app} />)
        ) : (
          <p className={cx("text-ink-meta", earlier === undefined && "animate-pulse")}>{earlier === undefined ? "Finding what you applied to…" : "Nothing submitted yet."}</p>
        )}</div>
    </>
  );
}
