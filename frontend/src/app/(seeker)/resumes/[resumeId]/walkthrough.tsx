"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { CoachMark, useTourFits, type CoachAction, type CoachTarget } from "@/components/tour";
import { cn } from "@/lib/cn";

import { CHAPTERS, type ChapterId, type WalkCounts } from "./walkthrough-model.ts";

/** What the walkthrough reads from the editor and asks it to do. */
export type WalkApi = {
  counts: WalkCounts;
  /** The practice examples ticked on (null when the student practises on
   *  their own saved experiences). */
  sampleTicks: number | null;
  /** A line on the page is open for typing. */
  lineOpen: boolean;
  /** The page's settings, to see a Format change land. */
  pageKey: string;
  /** Opens the panel on Sections with this section open ("header" opens
   *  the Header row; null closes both). */
  openSection: (id: string | null) => void;
  openFormat: () => void;
  /** Add Experiences, with the practice examples when nothing is saved. */
  openExperiences: () => void;
  closeExperiences: () => void;
};

type Beat = {
  target: CoachTarget | null;
  /** The control to press, ringed (`CoachMark`'s `beacon`). */
  beacon?: string;
  title: string;
  body: ReactNode;
  art?: ReactNode;
  actions: CoachAction[];
  /** Runs once as the beat opens. */
  enter?: () => void;
  /** Moves on to the next beat by itself once true. */
  advance?: boolean;
};

/** A section's +, in its row. */
const addIn = (id: string) => `[data-tour="section-${id}"] button[aria-label^="Add"]`;

const SECTION_COPY: Record<"education" | "experience" | "projects", [string, string]> = {
  education: ["Add your schools", "Every school you've attended."],
  experience: ["Add your experience", "Jobs, internships and research."],
  projects: ["Add your projects", "What you built in class or on your own."],
};

/**
 * Getting Started (2026-11-18, ./walkthrough-model.ts): one path down the
 * page, header first, each step a coach mark (`CoachMark`). The user had a
 * checklist of nine places to start taken out the same day: it asked a new
 * student to choose before they knew the editor, and a walkthrough should
 * start at the top and go down. Each card is a line or two, and the control
 * to press is shown clicked (`beacon`) rather than named in words: people will
 * not read long cards. A section's step stays open while they add as many as
 * they have, and moves on with Next. The editor holds no logic here but its
 * hooks (`WalkApi`).
 */
export function Walkthrough({
  api,
  onChapter,
  onClose,
}: {
  api: WalkApi;
  /** The step open, so the entry form can show its tip. */
  onChapter: (id: ChapterId | null) => void;
  onClose: () => void;
}) {
  const fits = useTourFits();
  const [at, setAt] = useState(0);
  const [beat, setBeat] = useState(0);
  // What the resume held, and the page looked like, as the step opened
  const [from, setFrom] = useState(api.counts);
  const [pageFrom, setPageFrom] = useState(api.pageKey);
  const chapter = CHAPTERS[at];
  const told = useRef(onChapter);
  useEffect(() => {
    told.current = onChapter;
  });
  useEffect(() => {
    told.current(chapter.id);
    return () => told.current(null);
  }, [chapter.id]);

  const entered = useRef("");
  const leaving = () => {
    if (chapter.id === "reuse") api.closeExperiences();
  };
  const nextChapter = () => {
    leaving();
    if (at === CHAPTERS.length - 1) return onClose();
    setFrom(api.counts);
    setPageFrom(api.pageKey);
    setBeat(0);
    setAt(at + 1);
  };
  const end = () => {
    leaving();
    onClose();
  };

  const beats = beatsOf(chapter.id, api, from, pageFrom, () => setBeat((b) => b + 1), nextChapter);
  const current = beats[Math.min(beat, beats.length - 1)];

  // Each beat's opening move (a panel, a tab) runs once as it opens
  useEffect(() => {
    // The step's number keys it, so a step is entered once per visit
    const key = `${at}:${beat}`;
    if (entered.current === key) return;
    entered.current = key;
    current.enter?.();
  });
  // A beat whose task is done moves on by itself, after a moment: moved on
  // in the frame the student acted, the card changed before they saw their
  // click land (a line opening), which read as a jump (2026-11-18)
  const ready = Boolean(current.advance) && beat < beats.length - 1;
  useEffect(() => {
    if (!ready) return;
    const later = window.setTimeout(() => setBeat((b) => b + 1), 700);
    return () => window.clearTimeout(later);
  }, [ready, beat]);

  if (!fits) return null;
  const last = at === CHAPTERS.length - 1;
  return (
    <CoachMark
      id={`${chapter.id}:${beat}`}
      target={current.target}
      beacon={current.beacon}
      // The step alone: the title already says what the section holds
      eyebrow={`Step ${at + 1} of ${CHAPTERS.length}`}
      title={current.title}
      art={current.art}
      actions={current.actions.map((action) =>
        last && action.label === "Next" ? { ...action, label: "Finish" } : action,
      )}
      onEnd={end}
    >
      {current.body}
    </CoachMark>
  );
}

/** A step's beats, read again on every render, so its words and buttons
 *  follow what the student has done. Each card is a line or two. */
function beatsOf(
  id: ChapterId,
  api: WalkApi,
  from: WalkCounts,
  pageFrom: string,
  next: () => void,
  nextChapter: () => void,
): Beat[] {
  const onward: CoachAction = { label: "Next", onClick: nextChapter };
  const skip: CoachAction = { label: "Skip", variant: "secondary", onClick: nextChapter };
  switch (id) {
    case "contact":
      return [
        {
          enter: () => api.openSection("header"),
          target: { tour: "section-header" },
          title: "Check your details",
          body: <p>This is the top of your resume. Fix anything that&apos;s wrong.</p>,
          actions: [{ label: "Looks Right", onClick: nextChapter }],
        },
      ];
    case "education":
    case "experience":
    case "projects": {
      const n = api.counts[id];
      const added = n > from[id];
      const [title, line] = SECTION_COPY[id];
      const noun = CHAPTERS.find((c) => c.id === id)!.noun!;
      return [
        {
          enter: () => api.openSection(id),
          target: { tour: `section-${id}` },
          beacon: addIn(id),
          title: added ? `${n} ${(n === 1 ? noun[0] : noun[1]).toLowerCase()} added` : title,
          body: <p>{added ? "Add another, or move on." : line}</p>,
          actions: [n > 0 ? onward : skip],
        },
      ];
    }
    case "skills": {
      const n = api.counts.skills;
      const added = n > from.skills;
      return [
        {
          enter: () => api.openSection("skills"),
          target: { tour: "section-skills" },
          beacon: `section:has(> [data-tour="section-skills"]) button[aria-label^="Add"]`,
          title: added ? `${n} ${n === 1 ? "skill" : "skills"} added` : "Add your skills",
          body: (
            <p>
              {added ? "Keep typing to add more." : "Languages and tools. Press Enter after each."}
            </p>
          ),
          actions: [n > 0 ? onward : skip],
        },
      ];
    }
    case "reuse": {
      const sample = api.sampleTicks !== null;
      const ticked = sample
        ? api.sampleTicks! > 0
        : Object.values(api.counts).reduce((a, b) => a + b, 0) >
          Object.values(from).reduce((a, b) => a + b, 0);
      return [
        {
          enter: api.openExperiences,
          target: { tour: "experiences-panel" },
          beacon: `[data-tour="experiences-panel"] [role="checkbox"], [data-tour="experiences-panel"] input[type="checkbox"]`,
          title: "Reuse what you've saved",
          body: (
            <p>
              {sample
                ? "Practise on an example. Nothing here is saved."
                : "Tick one to add it to this resume."}
            </p>
          ),
          advance: ticked,
          actions: [skip],
        },
        {
          target: { tour: "experiences-panel" },
          title: "Pick its bullets",
          body: <p>Open it with the arrow to choose which bullets show.</p>,
          actions: [onward],
        },
      ];
    }
    case "page": {
      const lines = api.counts.education + api.counts.experience + api.counts.projects > 0;
      return [
        {
          enter: () => api.openSection(null),
          target: lines ? { selector: '[data-box$=".bullet"], [data-box$=".title"]' } : null,
          title: "Edit on the page",
          body: (
            <p>
              {lines
                ? "Click this line to change it."
                : "Once you add an entry, click any of its lines to edit it."}
            </p>
          ),
          advance: api.lineOpen,
          actions: [lines ? { ...skip, onClick: next } : skip],
        },
        {
          target: { tour: "toolbar" },
          title: "Editing a line",
          body: <p>Enter saves. The arrows move it. Undo takes it back.</p>,
          actions: [onward],
        },
      ];
    }
    case "format":
      return [
        {
          enter: api.openFormat,
          target: { tour: "panel-body" },
          title: "Format the page",
          body: <p>Fonts, spacing and layout for the whole resume.</p>,
          actions: [{ label: "Next", onClick: next }],
        },
        {
          enter: api.openFormat,
          target: { selector: '[role="group"][aria-label="Body Text"]' },
          beacon: '[role="group"][aria-label="Body Text"] button:last-of-type',
          title: "Try it",
          body: <p>Make the body text bigger.</p>,
          advance: api.pageKey !== pageFrom,
          actions: [{ ...skip, onClick: next }],
        },
        {
          enter: api.openFormat,
          target: { tour: "format-reset" },
          title: "Undo it all",
          body: <p>Reset Formatting puts everything back.</p>,
          actions: [{ label: "Next", onClick: next }],
        },
        {
          target: { tour: "toolbar" },
          title: "Keep it to one page",
          art: <OnePageArt />,
          body: <p>If it runs long, Fit to One Page appears here.</p>,
          actions: [onward],
        },
      ];
    case "download":
      return [
        {
          target: { tour: "download" },
          title: "Download it",
          body: <p>Get a PDF or Word file. WorkIt saves as you go.</p>,
          actions: [onward],
        },
      ];
  }
}

/** Two pages pressed into one: what Fit to One Page does, for a resume that
 *  does not run over yet. Decoration. */
function OnePageArt() {
  const page = (lines: number, short = false) => (
    <span className="bg-panel border-border-surface flex h-16 w-12 flex-col gap-1 rounded-sm border p-1.5">
      {Array.from({ length: lines }, (_, i) => (
        <span
          key={i}
          className={cn("bg-ink/20 h-1 rounded-full", i % 3 === 2 || short ? "w-2/3" : "w-full")}
        />
      ))}
    </span>
  );
  return (
    <div
      aria-hidden
      className="bg-well rounded-control flex items-center justify-center gap-3 py-3"
    >
      <span className="flex gap-1">
        {page(8)}
        {page(3, true)}
      </span>
      <span className="text-ink-meta text-label">→</span>
      {page(9)}
    </div>
  );
}
