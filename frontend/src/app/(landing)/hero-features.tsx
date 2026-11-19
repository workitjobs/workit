"use client";

import { MotionConfig, motion } from "motion/react";
import { useCallback, useRef, useState, type ComponentType, type KeyboardEvent } from "react";

import { cn } from "@/lib/cn";

import type { FeatureId } from "./feature-data";
import {
  AutoApplyAnimation,
  MatchingAnimation,
  ResumeAnimation,
  UpdatesAnimation,
} from "./features/animations";
import { FEATURES } from "./features/catalog";
import { Fit } from "./fit";
import { StudioBox, studioGround } from "./layout-parts";
import { StopCopy } from "./stop-copy";
import { StoryEnd } from "./story";
import { TOUR_TABS } from "./tour-tabs";

/**
 * Each tab's story, through `features/animations.tsx`, so only the story
 * on show loads: the first one with the page, the next when its tab opens.
 */
const VISUALS: Record<FeatureId, ComponentType> = {
  resumes: ResumeAnimation,
  matching: MatchingAnimation,
  "auto-apply": AutoApplyAnimation,
  updates: UpdatesAnimation,
};

/**
 * The home hero's top features (KAN-923), after Calendly's hero: a row of
 * the four feature tabs and one card for the open one, its copy beside its
 * story in a framed box. Each story plays once, whole, and the next tab
 * opens (`StoryEnd`); once the visitor picks a tab the card stays on it and
 * its story loops. The story holds while off screen, in a hidden tab and on
 * Pause Animations (story.tsx), so the tabs only move while someone watches.
 * It replaced the city hero, the bridge and the pinned tour, which took the
 * whole screen. A WAI tabs pattern: arrow keys move between tabs.
 */
export function HeroFeatures() {
  const [at, setAt] = useState(0);
  const [picked, setPicked] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const next = useCallback(() => setAt((i) => (i + 1) % TOUR_TABS.length), []);

  const pick = (i: number) => {
    setAt(i);
    setPicked(true);
  };
  const onKeyDown = (event: KeyboardEvent) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const i = (at + step + TOUR_TABS.length) % TOUR_TABS.length;
    pick(i);
    tabRefs.current[i]?.focus();
  };

  const tab = TOUR_TABS[at];
  const page = FEATURES[tab.page];
  const Visual = VISUALS[tab.id];

  return (
    // reducedMotion="user": the stories' transforms are instant for
    // visitors who prefer reduced motion, who see each story's still scene.
    <MotionConfig reducedMotion="user">
      <div
        role="tablist"
        aria-label="Features"
        onKeyDown={onKeyDown}
        className="mx-auto flex w-fit gap-1 rounded-full bg-slate-900/[0.05] p-1"
      >
        {TOUR_TABS.map((item, i) => {
          const selected = i === at;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              ref={(el) => {
                tabRefs.current[i] = el;
              }}
              type="button"
              role="tab"
              id={`hero-tab-${item.id}`}
              aria-selected={selected}
              aria-controls="hero-feature"
              tabIndex={selected ? 0 : -1}
              onClick={() => pick(i)}
              className={cn(
                "relative flex h-11 items-center gap-2 rounded-full px-3.5 text-sm font-medium transition-colors duration-300 sm:px-4",
                selected ? "text-ink" : "text-ink-meta hover:text-ink",
              )}
            >
              {/* The white fill slides between tabs, as the old tour's did. */}
              {selected && (
                <motion.span
                  layoutId="hero-tab-fill"
                  aria-hidden="true"
                  className="absolute inset-0 -z-10 rounded-full bg-white shadow-md"
                />
              )}
              <Icon
                className="size-4"
                aria-hidden="true"
                style={selected ? { color: item.glow } : undefined}
              />
              {/* Below sm only the open tab says its name: four names in a
                  row ran past a 390px screen. */}
              <span className={cn(!selected && "max-sm:sr-only")}>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id="hero-feature"
        aria-labelledby={`hero-tab-${tab.id}`}
        className="surface-card mt-5 grid gap-3 rounded-[1.75rem] p-3 text-left lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-6"
      >
        <StopCopy
          id={tab.id}
          className="self-center px-4 pt-5 pb-2 sm:px-8 sm:pt-8 lg:py-8 lg:pr-0"
        />
        <StudioBox
          ref={boxRef}
          ground={studioGround({ tint: page.tint, glow: page.glow })}
          className="flex h-[22rem] items-center justify-center px-3 py-5 sm:h-[27rem] sm:px-6 lg:h-[28rem]"
        >
          <StoryEnd value={picked ? null : next}>
            <Fit box={boxRef} max={1}>
              <Visual key={tab.id} />
            </Fit>
          </StoryEnd>
        </StudioBox>
      </div>
    </MotionConfig>
  );
}
