"use client";

import {
  ArrowUpRightIcon,
  BrowsersIcon,
  ChatTextIcon,
  EnvelopeSimpleIcon,
  FilesIcon,
  KeyboardIcon,
  TableIcon,
} from "@phosphor-icons/react/ssr";
import { useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { useArrived } from "./hooks";

type Scene = "boards" | "resumes" | "forms" | "question" | "tracker" | "replies";
type Problem = { scene: Scene; title: string; body: string };

/** Each problem's glyph: the thing it is about. */
const ICONS = {
  boards: BrowsersIcon,
  resumes: FilesIcon,
  forms: KeyboardIcon,
  question: ChatTextIcon,
  tracker: TableIcon,
  replies: EnvelopeSimpleIcon,
};
type Stat = { figure: string; text: string; source: string; href: string };

/**
 * The problems hub (problems.tsx, KAN-923, the user's layout): the six
 * problems of a search, three before applying on the left and three after
 * on the right, and one large visual in the middle showing the open one,
 * then the section's one figure with its source. A hover (a mouse only), a
 * click, a tap or keyboard focus opens a problem; nothing changes on a timer
 * (the taste rules ban timed tabs, and a timer would need a pause control).
 * Every problem's words stay on screen, so only the picture changes.
 *
 * Each visual plays once as it shows: the stage carries `data-arrived` as
 * `Arrive` does, "false" until it is well on screen and again for two
 * frames after a switch, so the new visual mounts in its waiting pose and
 * then plays (the `.journey-*` classes); it also mounts afresh once
 * hydrated (its key reads `mounted`). No attribute in the server's HTML, so
 * the first visual shows finished without script.
 *
 * Below lg the stage leads, then the problems: in two columns from md, one
 * on a phone. From lg up the hub is one block: each side's three cards
 * share the stage's height (rows of one third each), so their edges meet
 * the stage's; set loosely in the middle of each column, the cards were
 * shorter than the stage and the section read as small and tall at once
 * (the user's catch). The heading, the hub and the figure fit one screen
 * under the floating header: the stage is at least `clamp(19rem, 100svh -
 * 29.5rem, 30rem)` tall and grows to the cards' height, what is left once the header, the heading, its one-line
 * subtitle and the figure are counted (measured at 1440 × 800).
 *
 * Each card has its glyph (`ICONS`) on a white tile, on ink when open.
 *
 * The problems are buttons with `aria-pressed`, not tabs: the visuals are
 * pictures (`aria-hidden`), and each button's words are its name.
 */
export function ProblemHub({
  problems,
  scenes,
  stat,
}: {
  problems: readonly Problem[];
  scenes: readonly ReactNode[];
  stat: Stat;
}) {
  const [at, setAt] = useState(0);
  const [hold, setHold] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);
  const mounted = useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
  const arrived = useArrived(stageRef, mounted);

  const pick = (i: number) => {
    if (i === at) return;
    setHold(true);
    setAt(i);
    // Two frames: the new visual paints once in its waiting pose, then plays.
    requestAnimationFrame(() => requestAnimationFrame(() => setHold(false)));
  };

  const half = Math.ceil(problems.length / 2);
  const column = (from: number, to: number, className: string) => (
    <div className={cn("grid gap-2.5 lg:grid-rows-3", className)}>
      {problems.slice(from, to).map((problem, j) => {
        const i = from + j;
        const open = i === at;
        const Icon = ICONS[problem.scene];
        return (
          <button
            key={problem.title}
            type="button"
            aria-pressed={open}
            onClick={() => pick(i)}
            onFocus={() => pick(i)}
            onPointerEnter={(event) => event.pointerType === "mouse" && pick(i)}
            className={cn(
              "flex items-start gap-3.5 rounded-2xl px-4 py-3.5 text-left transition-[background-color,box-shadow] duration-200 lg:items-center",
              "focus-visible:outline-ink focus-visible:outline-2 focus-visible:outline-offset-2",
              open ? "surface-card" : "bg-slate-900/[0.035] hover:bg-slate-900/[0.06]",
            )}
          >
            <span
              className={cn(
                "grid size-9 shrink-0 place-items-center rounded-[10px] transition-colors duration-200",
                open ? "bg-ink text-white" : "text-ink-meta bg-white",
              )}
            >
              <Icon aria-hidden="true" className="size-[18px]" />
            </span>
            <span className="min-w-0">
              <span
                className={cn(
                  "block text-[15px] leading-snug font-medium transition-colors",
                  open ? "text-ink" : "text-ink-muted",
                )}
              >
                {problem.title}
              </span>
              <span className="text-ink-meta mt-1 block text-[13.5px] leading-snug text-pretty">
                {problem.body}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );

  return (
    <div className="mt-8">
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-[17rem_minmax(0,1fr)_17rem] lg:gap-3 xl:grid-cols-[19rem_minmax(0,1fr)_19rem]">
        {column(0, half, "lg:order-1")}
        <div
          ref={stageRef}
          data-arrived={mounted ? String(arrived && !hold) : undefined}
          className="bg-well relative order-first h-[22rem] overflow-hidden rounded-2xl md:col-span-2 md:h-[24rem] lg:order-2 lg:col-span-1 lg:h-auto lg:min-h-[clamp(19rem,calc(100svh-29.5rem),30rem)]"
        >
          {/* Keyed by `mounted` too: the visual mounts afresh once hydrated,
              so a transition the server's HTML would skip plays when seen. */}
          <div key={mounted ? at : "server"} className="absolute inset-0">
            {scenes[at]}
          </div>
        </div>
        {column(half, problems.length, "lg:order-3")}
      </div>
      {/* The section's one figure: an outlined box with a legend on its top
          edge, the number in red, its sentence and its source. A filled
          dark box read as heavy and out of place (the user's catch); as
          plain text under a hairline it did not read as a sourced fact. */}
      <figure className="relative mx-auto mt-7 grid max-w-3xl items-center gap-x-6 gap-y-1.5 rounded-2xl border border-slate-900/15 px-6 pt-5 pb-4 text-center sm:grid-cols-[auto_minmax(0,1fr)] sm:px-7 sm:text-left">
        <span className="text-danger absolute -top-2.5 left-1/2 -translate-x-1/2 bg-white px-2 text-[11px] font-semibold tracking-[0.08em] whitespace-nowrap uppercase sm:left-6 sm:translate-x-0">
          By the numbers
        </span>
        <p className="font-display text-danger text-[3.25rem] leading-none font-medium tracking-[-0.04em] sm:row-span-2 sm:border-r sm:border-slate-900/10 sm:pr-6">
          {stat.figure}
        </p>
        <p className="text-ink text-[16px] leading-snug text-pretty">{stat.text}</p>
        <figcaption className="text-ink-meta text-[13px]">
          <a
            href={stat.href}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-ink inline-flex items-center gap-1 underline decoration-slate-300 underline-offset-2"
          >
            {stat.source}
            <ArrowUpRightIcon aria-hidden="true" className="size-3" />
          </a>
        </figcaption>
      </figure>
    </div>
  );
}

const noSubscribe = () => () => {};
