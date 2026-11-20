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
 * and `.ats-*` classes in landing.css). No attribute in the server's HTML,
 * so the first screen shows finished without script.
 *
 * The frame is flat grey, not a `StudioBox` sky: these screens are the
 * search as it is, not WorkIt's features, and the user found the gradient
 * wrong here (2026-11-20). The open card is a white `.surface-card`, the
 * closed ones flat grey, and only the open one shows WorkIt's answer: with
 * a paragraph and an answer under every problem the section read as too
 * dense. The closed answers keep their room from md up, so the row never
 * jumps; below md a closed card is its glyph and title alone.
 *
 * The cards are buttons with `aria-pressed`, not tabs: the screens are
 * pictures (`aria-hidden`), and each card's words are its button's name.
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
    <div className="mt-10 sm:mt-14">
      <div
        ref={frameRef}
        data-arrived={mounted ? String(arrived && !hold) : undefined}
        // From lg up the frame takes what the screen has left once the
        // header and the cards are counted (about 25rem, with room to spare), so the frame and
        // the cards show together: at 16:7 the cards ran below a laptop's
        // screen (the user's catch, 2026-11-20).
        className="bg-well relative h-[22rem] overflow-hidden rounded-2xl sm:h-[26rem] lg:h-[clamp(18rem,calc(100svh-25rem),30rem)]"
      >
        {/* Keyed by `mounted` too: the scene mounts afresh once hydrated,
            so a CSS animation the server's HTML started off screen starts
            again, held until the frame is seen. */}
        <div key={mounted ? at : "server"} className="absolute inset-0">
          {scenes[at]}
        </div>
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
                // 20px in: at 24px the first title missed one line by 4px.
                "flex flex-col rounded-2xl p-5 text-left transition-[background-color,box-shadow] duration-300",
                "focus-visible:outline-ink focus-visible:outline-2 focus-visible:outline-offset-2",
                open ? "surface-card" : "bg-slate-900/[0.035] hover:bg-slate-900/[0.06]",
              )}
            >
              <span
                className={cn(
                  "grid size-9 place-items-center rounded-[10px] transition-colors duration-300",
                  open ? "bg-ink text-white" : "text-ink-meta bg-white",
                )}
              >
                <Icon aria-hidden="true" className="size-[18px]" />
              </span>
              <span
                className={cn(
                  TYPE.item,
                  "mt-4 block text-balance transition-colors",
                  open ? "text-ink" : "text-ink-muted",
                )}
              >
                {problem.title}
              </span>
              <span
                className={cn(
                  "text-ink-meta mt-1.5 block text-[15px] leading-snug text-pretty",
                  !open && "max-md:hidden",
                )}
              >
                {problem.body}
              </span>
              <span
                className={cn(
                  "text-ink mt-4 flex items-start gap-2 border-t border-slate-900/[0.07] pt-4 text-[15px] leading-snug text-pretty transition-opacity duration-300",
                  !open && "invisible opacity-0 max-md:hidden",
                )}
              >
                <Logo size="mark" decorative className="mt-[3px] h-3.5 shrink-0" />
                <span>{problem.fix}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

const noSubscribe = () => () => {};
