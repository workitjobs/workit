// Find jobs: the student's best matches that Auto Apply fills, drawn as the website's Jobs page draws them (its
// search, its filter row, its cards with the match ring), to pick from and start applying in one go.
// app_window.Bridge.matches reads them; a pick starts a run of its link, as a ticked queued job does.
import {
  BuildingsIcon,
  CalendarBlankIcon,
  CaretDownIcon,
  CheckIcon,
  ClockIcon,
  GraduationCapIcon,
  LightningIcon,
  MagnifyingGlassIcon,
  MapPinIcon,
  MoneyIcon,
  PlusIcon,
  WarningCircleIcon,
  XIcon,
} from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import type { App, Filters, Match } from "./bridge.ts";
import { Button, Logo, cx } from "./ui.tsx";
import { ago, facts, filterLabel, level, MENUS, type Menu } from "./find-view.ts";
import { notStarted, STARTING_WAIT } from "./view.ts";
import { said } from "./words.ts";

// The matches last read for each set of filters, so coming back to Find jobs shows them at once.
const read = new Map<string, Match[]>();
// How long "Finding jobs that fit you…" shows before the page says the first search is slow.
const SLOW_MATCHES = 6_000;

export function Find({ app, queue }: { app: App; queue: () => void }) {
  const [filters, setFilters] = useState<Filters>({ job_type: ["internship"] });
  const [q, setQ] = useState("");
  const [jobs, setJobs] = useState<Match[] | null>(null);
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [picked, setPicked] = useState<Map<string, Match>>(new Map());
  const [starting, setStarting] = useState(false);
  const [why, setWhy] = useState(""); // why the last run couldn't start or stopped
  useEffect(() => {
    app.status?.().then(
      (s) => s.said && setWhy(said(s.said)),
      () => {},
    );
  }, [app]);
  // The search box asks once the student stops typing.
  useEffect(() => {
    const want = q.trim();
    // Unchanged words ask nothing again (the first render's empty box among them).
    const t = setTimeout(() => setFilters((f) => ((f.q?.[0] ?? "") === want ? f : { ...f, q: want ? [want] : [] })), 500);
    return () => clearTimeout(t);
  }, [q]);
  const key = JSON.stringify(filters);
  useEffect(() => {
    let live = true;
    setError("");
    setJobs(read.get(key) ?? null);
    app.matches!(filters).then(
      (got) => live && (read.set(key, got), setJobs(got)),
      (e: Error) => live && setError(e.message),
    );
    return () => void (live = false);
  }, [app, key]); // filters is read through key
  // Scoring the first time takes WorkIt up to a minute (app_window.MATCHES_WAIT): past a few seconds, say so.
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    setSlow(false);
    if (jobs || error) return;
    const t = setTimeout(() => setSlow(true), SLOW_MATCHES);
    return () => clearTimeout(t);
  }, [jobs, error]);
  const shown = useMemo(() => (jobs ?? []).filter((j) => !hidden.has(j.url)), [jobs, hidden]);
  const toggle = (job: Match) => {
    const next = new Map(picked);
    if (next.has(job.url)) next.delete(job.url);
    else next.set(job.url, job);
    setPicked(next);
  };
  const top = () => {
    const next = new Map(picked);
    shown.slice(0, 5).forEach((j) => next.set(j.url, j));
    setPicked(next);
  };
  // A run whose board never shows: once STARTING_WAIT has passed, and each 5 s after, ask whether it still goes (as
  // the queue screen's Start does in app.tsx).
  useEffect(() => {
    if (!starting || !app.status) return;
    let live = true;
    let timer = setTimeout(function look() {
      app.status!().then(notStarted, (e: Error) => notStarted(e)).then((line) => {
        if (!live) return;
        if (line) setStarting(false), setWhy(line);
        else timer = setTimeout(look, 5_000);
      });
    }, STARTING_WAIT);
    return () => ((live = false), clearTimeout(timer));
  }, [starting, app]);
  const start = () => {
    setStarting(true);
    setWhy("");
    app.start!([...picked.keys()]).catch((e: Error) => (setStarting(false), setWhy(e.message)));
  };
  const set = (name: Menu["name"], values: string[]) => setFilters((f) => ({ ...f, [name]: values }));
  const filtered = MENUS.some((m) => filters[m.name]?.length);
  return (
    <div className="pb-24">
      <div className="flex items-center gap-2.5">
        <label className="flex h-10 flex-1 items-center gap-2 rounded-full border border-border-surface bg-panel px-4 text-ink-meta focus-within:border-brand">
          <MagnifyingGlassIcon className="size-4" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search jobs or companies" aria-label="Search jobs" className="flex-1 bg-transparent text-ink outline-none" />
        </label>
        <Button tone="quiet" className="h-10 px-3" onClick={queue}>
          Your queue · paste a link
        </Button>
      </div>
      {why && (
        <p role="alert" className="mt-3 rounded-card border border-border bg-panel px-4 py-3 text-note text-ink-meta">
          {why}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {MENUS.map((m) => (
          <Dropdown key={m.name} menu={m} values={filters[m.name] ?? []} set={(v) => set(m.name, v)} />
        ))}
        {filtered && (
          <button className="ml-auto flex cursor-pointer items-center gap-1 text-label text-ink-meta hover:text-ink" onClick={() => setFilters({ q: filters.q })}>
            <XIcon className="size-3.5" /> Clear
          </button>
        )}
      </div>
      <div className="mt-4 mb-2.5 flex items-center justify-between text-note text-ink-meta">
        <span>
          {jobs ? (
            <>
              <b className="text-ink">{shown.length} jobs</b> we can apply to for you · best match first
            </>
          ) : (
            !error && (slow ? "Still scoring jobs against your experience. The first search can take up to a minute." : "Finding jobs that fit you…")
          )}
        </span>
        {shown.length > 0 && (
          <button className="flex cursor-pointer items-center gap-1 font-medium text-brand hover:text-brand-hover" onClick={top}>
            <LightningIcon className="size-3.5" /> Add my top 5
          </button>
        )}
      </div>
      {error ? (
        <p role="alert" className="rounded-card border border-border bg-panel px-4 py-6 text-center text-ink-meta">
          {error}
        </p>
      ) : !jobs ? (
        [0, 1, 2].map((i) => <div key={i} className="mb-2.5 h-52 animate-pulse rounded-card border border-border bg-panel" />)
      ) : !shown.length ? (
        <p className="rounded-card border border-border bg-panel px-4 py-8 text-center text-ink-meta">
          No jobs match these filters.{" "}
          <button className="cursor-pointer font-medium text-brand" onClick={() => (setQ(""), setFilters({}))}>
            Clear filters
          </button>
        </p>
      ) : (
        shown.map((job) => <Card key={job.url} job={job} picked={picked.has(job.url)} toggle={() => toggle(job)} hide={() => (setHidden(new Set(hidden).add(job.url)), setPicked(new Map([...picked].filter(([url]) => url !== job.url))))} />)
      )}
      {picked.size > 0 && (
        <div className="rise fixed inset-x-0 bottom-4 z-20 mx-auto flex w-[min(46rem,calc(100%-2rem))] items-center gap-3 rounded-shell bg-ink py-2.5 pr-2.5 pl-4 text-on-brand shadow-lift">
          <span className="flex">
            {[...picked.values()].slice(0, 4).map((j, i) => (
              <span key={j.url} className={cx("rounded-control ring-2 ring-ink", i > 0 && "-ml-2")}>
                <Logo company={j.company ?? ""} src={j} size="sm" />
              </span>
            ))}
          </span>
          <span className="min-w-0 text-note text-ink-faint">
            <b className="block text-body text-on-brand">{picked.size === 1 ? "1 job ready" : `${picked.size} jobs ready`}</b>
            We fill them out. You check each one and press Submit.
          </span>
          <button className="ml-auto cursor-pointer px-2 text-note text-ink-faint hover:text-on-brand" onClick={() => setPicked(new Map())}>
            Clear
          </button>
          <Button tone="primary" size="lg" disabled={starting} onClick={start}>
            <LightningIcon className="size-4" />
            {starting ? "Starting…" : "Start applying"}
          </Button>
        </div>
      )}
    </div>
  );
}

function Card({ job, picked, toggle, hide }: { job: Match; picked: boolean; toggle: () => void; hide: () => void }) {
  const f = facts(job);
  const lv = level(job.match);
  return (
    <div
      onClick={toggle}
      className={cx(
        "mb-2.5 flex cursor-pointer gap-2 rounded-card border bg-panel p-2 transition hover:border-border-surface",
        picked ? "border-brand ring-1 ring-brand" : "border-border",
      )}
    >
      <div className="min-w-0 flex-1 px-2 pt-2 pb-1.5">
        <div className="flex gap-3">
          <Logo company={job.company ?? ""} src={job} size="xl" />
          <div className="min-w-0">
            <div className="flex gap-1.5 text-note">
              {job.posted_at && <span className="rounded-full bg-positive-tint px-2 text-positive-ink">{ago(job.posted_at)}</span>}
              <span className="flex items-center gap-1 rounded-full bg-brand-tint px-2 text-brand-ink">
                <LightningIcon className="size-3" /> Auto Apply
              </span>
            </div>
            <div className="mt-0.5 text-subtitle">{job.title || "A job"}</div>
            <div className="text-note">{job.company}</div>
          </div>
          <button
            title="Not interested"
            aria-label="Not interested"
            className="ml-auto self-start rounded-control p-1 text-ink-meta hover:bg-hover hover:text-ink"
            onClick={(e) => (e.stopPropagation(), hide())}
          >
            <XIcon className="size-4" />
          </button>
        </div>
        <div className="my-2.5 grid grid-cols-2 gap-x-3 gap-y-1.5 border-y border-border py-2.5 text-label sm:grid-cols-3">
          <Fact icon={<MapPinIcon />}>{f.place}</Fact>
          <Fact icon={<ClockIcon />}>{f.type}</Fact>
          <Fact icon={<MoneyIcon />}>{f.pay}</Fact>
          <Fact icon={<BuildingsIcon />}>{f.style}</Fact>
          <Fact icon={<GraduationCapIcon />}>{f.level}</Fact>
          <Fact icon={<CalendarBlankIcon />}>{f.start}</Fact>
        </div>
        <div className="flex justify-end">
          <Button tone={picked ? "secondary" : "primary"} className={cx(picked && "border-positive/40 bg-positive-tint text-positive-ink hover:bg-positive-tint")}>
            {picked ? <CheckIcon className="size-4" /> : <PlusIcon className="size-4" />}
            {picked ? "Added" : "Add to Auto Apply"}
          </Button>
        </div>
      </div>
      {job.match != null && (
        <div className="flex w-40 shrink-0 flex-col items-center justify-center rounded-control bg-surface px-2.5 py-3 text-center">
          <Ring value={job.match} tone={lv.tone} />
          <div className="mt-2 mb-1.5 font-semibold">{lv.label}</div>
          <div className="grid gap-0.5 text-left text-note">
            {job.highlights.slice(0, 2).map((h) => (
              <span key={h.text} title={h.detail ?? undefined} className="flex items-center gap-1">
                {h.met ? <CheckIcon className="size-3 shrink-0 text-positive" /> : <WarningCircleIcon className="size-3 shrink-0 text-warning-fill" />}
                {h.text}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const Fact = ({ icon, children }: { icon: ReactNode; children: ReactNode }) =>
  children ? (
    <span className="flex min-w-0 items-center gap-1.5 [&>svg]:size-4 [&>svg]:shrink-0 [&>svg]:text-ink-meta">
      {icon}
      <span className="truncate">{children}</span>
    </span>
  ) : (
    <span />
  );

const RING = { positive: "var(--color-positive)", brand: "var(--color-brand)", warning: "var(--color-warning-fill)" };

function Ring({ value, tone }: { value: number; tone: keyof typeof RING }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  return (
    <span className="relative grid size-20 place-items-center">
      <svg viewBox="0 0 80 80" className="absolute inset-0 -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" stroke="var(--color-border)" strokeWidth="7" />
        <circle cx="40" cy="40" r={r} fill="none" stroke={RING[tone]} strokeWidth="7" strokeLinecap="round" strokeDasharray={`${(c * value) / 100} ${c}`} />
      </svg>
      <b className="text-title">
        {value}
        <small className="text-note">%</small>
      </b>
    </span>
  );
}

function Dropdown({ menu, values, set }: { menu: Menu; values: string[]; set: (values: string[]) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => ref.current?.contains(e.target as Node) || setOpen(false);
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);
  const pick = (value: string) => set(menu.single ? (values[0] === value ? [] : [value]) : values.includes(value) ? values.filter((v) => v !== value) : [...values, value]);
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={cx(
          "flex h-9 cursor-pointer items-center gap-1.5 rounded-control border px-3 text-label",
          values.length ? "border-brand bg-brand-tint text-brand-ink" : "border-border-surface bg-panel hover:bg-hover",
        )}
      >
        {filterLabel(menu, values)}
        <CaretDownIcon className="size-3" />
      </button>
      {open && (
        <div className="absolute top-10 left-0 z-30 min-w-48 rounded-card border border-border bg-panel p-1.5 shadow-lift">
          {menu.options.map(([value, label]) => (
            <label key={value} className="flex cursor-pointer items-center gap-2 rounded-control px-2 py-1.5 text-label hover:bg-hover">
              {/* A ticked radio fires no change when pressed again: its click picks it, so a second press clears it. */}
              <input
                type={menu.single ? "radio" : "checkbox"}
                checked={values.includes(value)}
                onChange={() => menu.single || pick(value)}
                onClick={() => menu.single && pick(value)}
                className="accent-brand"
              />
              {label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
