"use client";

import { useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { useArrived } from "./hooks";

type Problem = { title: string; body: string };
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
 * on a phone. From lg up the heading, the hub and the figure fit one
 * screen under the floating header: the stage is `clamp(17.5rem, 100svh -
 * 31.5rem, 26rem)` tall, what is left once the header, the heading, its
 * line and the figure are counted (measured at 1440 × 800 and 1280 × 720).
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
    <div className={cn("grid content-center gap-2.5", className)}>
      {problems.slice(from, to).map((problem, j) => {
        const i = from + j;
        const open = i === at;
        return (
          <button
            key={problem.title}
            type="button"
            aria-pressed={open}
            onClick={() => pick(i)}
            onFocus={() => pick(i)}
            onPointerEnter={(event) => event.pointerType === "mouse" && pick(i)}
            className={cn(
              "rounded-2xl px-4 py-3.5 text-left transition-[background-color,box-shadow] duration-200",
              "focus-visible:outline-ink focus-visible:outline-2 focus-visible:outline-offset-2",
              open ? "surface-card" : "bg-slate-900/[0.035] hover:bg-slate-900/[0.06]",
            )}
          >
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
          </button>
        );
      })}
    </div>
  );

  return (
    <div className="mt-8 sm:mt-10">
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-[15.5rem_minmax(0,1fr)_15.5rem] lg:gap-4 xl:grid-cols-[17.5rem_minmax(0,1fr)_17.5rem]">
        {column(0, half, "lg:order-1")}
        <div
          ref={stageRef}
          data-arrived={mounted ? String(arrived && !hold) : undefined}
          className="bg-well relative order-first h-[22rem] overflow-hidden rounded-2xl md:col-span-2 md:h-[24rem] lg:order-2 lg:col-span-1 lg:h-[clamp(17.5rem,calc(100svh-31.5rem),26rem)]"
        >
          {/* Keyed by `mounted` too: the visual mounts afresh once hydrated,
              so a transition the server's HTML would skip plays when seen. */}
          <div key={mounted ? at : "server"} className="absolute inset-0">
            {scenes[at]}
          </div>
        </div>
        {column(half, problems.length, "lg:order-3")}
      </div>
      {/* The section's one figure, a dark box with the number in red so it
          stands out as the fact behind the problems (the user's ask): its
          sentence under it in white, the source below as a link. */}
      <figure className="bg-ink mx-auto mt-6 grid max-w-3xl items-center gap-x-7 gap-y-2 rounded-2xl px-6 py-5 text-center sm:grid-cols-[auto_minmax(0,1fr)] sm:px-8 sm:text-left">
        <p className="font-display text-[3.5rem] leading-none font-medium tracking-[-0.04em] text-[color-mix(in_oklab,var(--color-danger)_70%,white)] sm:row-span-2">
          {stat.figure}
        </p>
        <p className="text-[16px] leading-snug text-pretty text-white">{stat.text}</p>
        <figcaption className="text-[13px] text-white/60">
          Source:{" "}
          <a
            href={stat.href}
            target="_blank"
            rel="noopener noreferrer"
            className="underline decoration-white/30 underline-offset-2 hover:text-white"
          >
            {stat.source}
          </a>
        </figcaption>
      </figure>
    </div>
  );
}

const noSubscribe = () => () => {};
