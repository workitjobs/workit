"use client";

import { useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { Logo } from "@/components/logo";
import { cn } from "@/lib/cn";

import { useArrived } from "./hooks";
import { StudioBox, TYPE } from "./layout-parts";

type Problem = { title: string; body: string; fix: string };

/**
 * The problems' one wide screen and the three problems under it
 * (problems.tsx, KAN-923). A click on a problem shows its screen in the
 * frame; nothing changes on a timer (the taste rules ban timed tabs, and a
 * timer would need a pause control). Each screen plays once as it shows:
 * the frame carries `data-arrived` as `Arrive` does, "false" until it is
 * well on screen, and "false" again for two frames after a click, so the
 * new screen mounts in its waiting pose and then plays (the `.journey-*`
 * and `.ats-*` classes in landing.css). No attribute in the server's HTML,
 * so the first screen shows finished without script.
 *
 * The problems are buttons with `aria-pressed`, not a tab list: the screens
 * are pictures (`aria-hidden`), and every problem's words stay readable
 * beside them, so a screen reader reads all three as text. Below md only
 * the open problem shows its lines; the others keep them for screen
 * readers (`sr-only`).
 */
export function ProblemTabs({
  problems,
  scenes,
  ground,
}: {
  problems: readonly Problem[];
  scenes: readonly ReactNode[];
  ground: string;
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
    <div className="mt-10 sm:mt-14">
      <div ref={frameRef} data-arrived={mounted ? String(arrived && !hold) : undefined}>
        <StudioBox ground={ground} className="h-[22rem] sm:h-[26rem] lg:aspect-[16/7] lg:h-auto">
          <div key={at} className="absolute inset-0">
            {scenes[at]}
          </div>
        </StudioBox>
      </div>
      <div className="mt-6 grid gap-x-8 md:grid-cols-3">
        {problems.map((problem, i) => {
          const open = i === at;
          return (
            <div
              key={problem.title}
              className={cn(
                "group relative border-t-2 pt-4 pb-5 transition-colors duration-300 sm:pt-5",
                open ? "border-ink" : "border-slate-900/10 hover:border-slate-900/30",
              )}
            >
              {/* The whole column takes the click: the button's ::after
                  covers it, as the tracker's stretched links do. */}
              <button
                type="button"
                aria-pressed={open}
                onClick={() => pick(i)}
                className={cn(
                  TYPE.item,
                  "focus-visible:outline-ink rounded-sm text-left text-balance transition-colors after:absolute after:inset-0 focus-visible:outline-2 focus-visible:outline-offset-4",
                  open ? "text-ink" : "text-ink-meta group-hover:text-ink",
                )}
              >
                {problem.title}
              </button>
              <div className={cn(!open && "max-md:sr-only")}>
                <p className="text-ink-meta mt-2 text-pretty">{problem.body}</p>
                <p className="mt-4 flex items-start gap-2.5 text-[15px] text-pretty">
                  <Logo size="mark" decorative className="mt-1 h-3.5 shrink-0" />
                  <span className={cn("transition-colors", open ? "text-ink" : "text-ink-meta")}>
                    {problem.fix}
                  </span>
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const noSubscribe = () => () => {};
