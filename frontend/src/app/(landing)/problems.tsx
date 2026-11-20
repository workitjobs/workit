import { cn } from "@/lib/cn";

import { problems } from "./data";
import { GrowIn } from "./grow-in";
import { CONTAINER, PANEL, PANEL_INSET, TYPE } from "./layout-parts";
import { ProblemHub } from "./problem-hub";
import {
  BoardsScene,
  FormsScene,
  QuestionScene,
  RepliesScene,
  ResumesScene,
  TrackerScene,
} from "./problem-scenes";

/**
 * Applying as it is (KAN-923), right after the logo strip, so the page says
 * why before it says how: what a job seeker goes through day to day,
 * before WorkIt. A centred heading about the whole search ("Applying for
 * jobs has become a full-time job") with its line, then the hub: six
 * problems, three on each side, one large visual in the middle for the open
 * one, and the section's one figure with its source (`ProblemHub`).
 *
 * The user's calls (2026-11-20): the whole job application process, not
 * one problem (the heading was "Many applications stop before a person
 * reads them"); no numbers in the heading, where "Forty tabs, nine forms,
 * and not one reply" confused them; any fact shown as a fact with its
 * source; three problems on each side with the visual between. Before
 * that it was a bento of three cards, which the user found ugly and
 * AI-made, then one wide frame of three clickable screens. The visuals are
 * in problem-scenes.tsx; copy, hedging and sources: `problems` in data.ts.
 */

/** Keyed, since they reach `ProblemHub` as a list. */
const SCENES = {
  boards: <BoardsScene key="boards" />,
  resumes: <ResumesScene key="resumes" />,
  forms: <FormsScene key="forms" />,
  question: <QuestionScene key="question" />,
  tracker: <TrackerScene key="tracker" />,
  replies: <RepliesScene key="replies" />,
};

export function Problems() {
  const { title, subtitle, items, stat } = problems;
  return (
    <section aria-labelledby="problems-title" className={cn(PANEL_INSET, "py-2")}>
      {/* The zoom in: the band grows from 80% as it rises up the screen, a
          scroll-linked scale the browser runs off the main thread
          (`GrowIn`), so What is WorkIt hands over to it as if the camera
          moved in. From lg up and without reduced motion only. */}
      <GrowIn
        from={0.8}
        className={cn(PANEL, "problems-ground relative isolate overflow-hidden py-14 sm:py-20")}
      >
        <div className={CONTAINER}>
          <div className="mx-auto max-w-3xl text-center">
            <h2 id="problems-title" className={cn(TYPE.chapter, "text-white")}>
              {title}
            </h2>
            <p className={cn(TYPE.lead, "mx-auto mt-5 max-w-2xl text-white/70")}>{subtitle}</p>
          </div>
          <ProblemHub
            problems={items}
            scenes={items.map((item) => SCENES[item.scene])}
            stat={stat}
          />
        </div>
      </GrowIn>
    </section>
  );
}
