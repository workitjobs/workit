"use client";

import { BrowsersIcon, FunnelSimpleIcon, RepeatIcon } from "@phosphor-icons/react/ssr";
import { useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { Logo } from "@/components/logo";
import { cn } from "@/lib/cn";

import { useArrived } from "./hooks";
import { TYPE } from "./layout-parts";

type Problem = { scene: "screen" | "forms" | "boards"; title: string; body: string; fix: string };

/** Each problem's glyph on its card. */
const ICONS = { screen: FunnelSimpleIcon, forms: RepeatIcon, boards: BrowsersIcon };

/**
 * The problems' one wide screen and the three problem cards under it
 * (problems.tsx, KAN-923). A click on a card shows its screen in the
 * frame; nothing changes on a timer (the taste rules ban timed tabs, and a
 * timer would need a pause control). Each screen plays once as it shows:
 * the frame carries `data-arrived` as `Arrive` does, "false" until it is
 * well on screen, and "false" again for two frames after a click, so the
 * new screen mounts in its waiting pose and then plays (the `.journey-*`
 * and `.scan-*` classes in landing.css). No attribute in the server's HTML,
 * so the first screen shows finished without script.
 *
 * The frame is flat grey, not a `StudioBox` sky: these screens are the
 * search as it is, not WorkIt's features, and the user found the gradient
 * wrong here (2026-11-20). WorkIt's answer to the open problem is the
 * frame's white foot bar, not a line in the card: in the cards it made
 * every card as tall as the open one, and the section did not fit a
 * laptop's screen. So a card is its glyph and title on one row and one
 * short line; the open one is a white `.surface-card`, the closed ones flat
 * grey.
 *
 * The cards are buttons with `aria-pressed`, not tabs: the screens are
 * pictures (`aria-hidden`), and each card's words are its button's name.
 * The foot bar is a polite live region, so a screen reader hears the answer
 * a click brings up.
 */
export function ProblemTabs({
  problems,
  scenes,
}: {
  problems: readonly Problem[];
  scenes: readonly ReactNode[];
}) {
  const [at, setAt] = useState(0);
  const [hold, setHold] = useState(false);
  const frameRef = useRef<HTMLDivElement>(null);
  const mounted = useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
  const arrived = useArrived(frameRef, mounted);

  const pick = (i: number) => {
    if (i === at) return;
    setHold(true);
    setAt(i);
    // Two frames: the new screen paints once in its waiting pose, then plays.
    requestAnimationFrame(() => requestAnimationFrame(() => setHold(false)));
  };

  return (
    <div className="mt-8 sm:mt-10">
      <div
        ref={frameRef}
        data-arrived={mounted ? String(arrived && !hold) : undefined}
        // From lg up the heading, the frame and the cards fit one screen
        // under the floating header: the frame takes what is left once the
        // header (about 6rem), the two-line heading and its gap (about 10rem)
        // and the cards (about 9rem) are counted. Sized from the cards alone,
        // the heading went under the header (the user's catch, 2026-11-20).
        className="bg-well relative h-[22rem] overflow-hidden rounded-2xl sm:h-[26rem] lg:h-[clamp(16rem,calc(100svh-26.5rem),28rem)]"
      >
        {/* Keyed by `mounted` too: the scene mounts afresh once hydrated,
            so a CSS animation the server's HTML started off screen starts
            again, held until the frame is seen. */}
        <div key={mounted ? at : "server"} className="absolute inset-0">
          {scenes[at]}
        </div>
        <p
          aria-live="polite"
          className="text-ink absolute inset-x-0 bottom-0 z-10 flex items-start gap-2.5 border-t border-slate-900/[0.06] bg-white px-4 py-3 text-[14px] leading-snug sm:px-5"
        >
          <Logo size="mark" decorative className="mt-[3px] h-3.5 shrink-0" />
          <span key={at} className="problem-answer">
            {problems[at].fix}
          </span>
        </p>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {problems.map((problem, i) => {
          const open = i === at;
          const Icon = ICONS[problem.scene];
          return (
            <button
              key={problem.title}
              type="button"
              aria-pressed={open}
              onClick={() => pick(i)}
              className={cn(
                "flex flex-col rounded-2xl p-4 text-left transition-[background-color,box-shadow] duration-300 sm:p-5",
                "focus-visible:outline-ink focus-visible:outline-2 focus-visible:outline-offset-2",
                open ? "surface-card" : "bg-slate-900/[0.035] hover:bg-slate-900/[0.06]",
              )}
            >
              <span className="flex items-center gap-3">
                <span
                  className={cn(
                    "grid size-8 shrink-0 place-items-center rounded-[9px] transition-colors duration-300",
                    open ? "bg-ink text-white" : "text-ink-meta bg-white",
                  )}
                >
                  <Icon aria-hidden="true" className="size-4" />
                </span>
                <span
                  className={cn(
                    TYPE.item,
                    "transition-colors",
                    open ? "text-ink" : "text-ink-muted",
                  )}
                >
                  {problem.title}
                </span>
              </span>
              <span className="text-ink-meta mt-2 block text-[15px] leading-snug text-pretty">
                {problem.body}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

const noSubscribe = () => () => {};
