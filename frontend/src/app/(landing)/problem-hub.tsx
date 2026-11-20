"use client";

import {
  ArrowUpRightIcon,
  CopyIcon,
  EnvelopeSimpleIcon,
  FilesIcon,
  HourglassIcon,
  MapTrifoldIcon,
  TableIcon,
  XIcon,
} from "@phosphor-icons/react/ssr";
import { useRef, useState, useSyncExternalStore, type ComponentProps, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { useArrived } from "./hooks";

type Scene = "boards" | "resumes" | "forms" | "question" | "tracker" | "replies";
type Problem = { scene: Scene; title: string; body: string };

/** A letter with a cross at its corner: ghosted or rejected. Phosphor has
 *  no such glyph, so the cross sits on a knock-out of the tile's own fill
 *  (`background: inherit`), white or violet as the tile is. */
function EnvelopeXIcon({ className, ...props }: ComponentProps<"span">) {
  return (
    <span className={cn("relative block [background:inherit]", className)} {...props}>
      <EnvelopeSimpleIcon className="size-full" />
      <span className="absolute -right-0.5 -bottom-0.5 grid size-[9px] place-items-center rounded-full [background:inherit]">
        <XIcon weight="bold" className="size-[8px]" />
      </span>
    </span>
  );
}

/** Each problem's glyph: the thing it is about (the user's picks,
 *  2026-11-20). */
const ICONS = {
  boards: MapTrifoldIcon,
  resumes: FilesIcon,
  forms: CopyIcon,
  question: HourglassIcon,
  tracker: TableIcon,
  replies: EnvelopeXIcon,
};
type Stat = { figure: string; text: string; source: string; href: string };

/**
 * The problems hub (problems.tsx, KAN-923, the user's layout): the six
 * problems of a search, three before applying on the left and three after
 * on the right, and one large visual in the middle showing the open one,
 * then the section's one figure with its source. Only a click, a tap or
 * Enter opens a problem (the user's call: opened on hover, the cards
 * changed under a passing pointer); nothing changes on a timer (the taste
 * rules ban timed tabs, and a timer would need a pause control).
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
 * fill the stage's height, each row as tall as its words and the spare
 * room shared out, so their edges meet the stage's. Rows of one third
 * each made every card as tall as the longest (the spreadsheet card's two
 * lines and four), and the section ran 96px past a 1440 × 800 screen.
 * Set loosely in the middle of each column, the cards were
 * shorter than the stage and the section read as small and tall at once
 * (the user's catch). The heading, the hub and the figure fit one screen
 * under the floating header: the stage is at least `clamp(19rem, 100svh -
 * 29.5rem, 30rem)` tall and grows to the cards' height, what is left once the header, the heading, its one-line
 * subtitle and the figure are counted (measured at 1440 × 800).
 *
 * Each card has its glyph (`ICONS`) on a white tile. The open card is
 * tinted violet (`brand-tint`, its glyph on solid `brand`), with no edge,
 * so it reads as the selected item, as a selected row does in the app: as
 * a white `.surface-card` beside flat grey ones it was hard to pick out,
 * and a violet edge read as an outline button (the user's calls,
 * 2026-11-20).
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
    <div className={cn("grid gap-2.5", className)}>
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
            className={cn(
              "flex items-start gap-3.5 rounded-2xl px-4 py-3.5 text-left transition-[background-color,box-shadow] duration-200 lg:items-center",
              "focus-visible:outline-ink focus-visible:outline-2 focus-visible:outline-offset-2",
              open ? "bg-brand-tint" : "bg-slate-900/[0.035] hover:bg-slate-900/[0.06]",
            )}
          >
            <span
              className={cn(
                "grid size-9 shrink-0 place-items-center rounded-[10px] transition-colors duration-200",
                open ? "bg-brand text-white" : "text-ink-meta bg-white",
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
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-[17rem_minmax(0,1fr)_17rem] lg:gap-3 xl:grid-cols-[20.5rem_minmax(0,1fr)_20.5rem]">
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
      {/* The section's one figure as a quote: an outlined box with a large
          opening quote breaking its top-left edge and a closing one its
          bottom-right (the user's ask), the number in red, its sentence and
          its source. A filled dark box read as heavy and out of place; as
          plain text under a hairline it did not read as a sourced fact. */}
      <figure className="relative mx-auto mt-7 grid max-w-3xl items-center gap-x-6 gap-y-1.5 rounded-2xl border border-slate-900/15 px-6 pt-5 pb-4 text-center sm:grid-cols-[auto_minmax(0,1fr)] sm:px-8 sm:text-left">
        {/* Each mark is a 20px white tile centred on the outline (its top
            and its foot), breaking the line; the glyph sits in it so its
            ink, about 9 to 23px down a 60px Plus Jakarta line, is centred on
            the line too (measured: set by their line boxes, both sat high).
            Grey, as the outline is: red marks competed with the figure. */}
        <span aria-hidden="true" className="absolute -top-[10.5px] left-5 h-5 bg-white px-1.5">
          <span className="font-display text-ink-meta -mt-1.5 block text-[3.75rem] leading-none">
            “
          </span>
        </span>
        <span
          aria-hidden="true"
          className="absolute top-[calc(100%-9.5px)] right-5 h-5 bg-white px-1.5"
        >
          <span className="font-display text-ink-meta -mt-1.5 block text-[3.75rem] leading-none">
            ”
          </span>
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
