import { cn } from "@/lib/cn";

import { problems } from "./data";
import { CONTAINER, studioGround, TYPE } from "./layout-parts";
import { BoardsScene, FormsScene, ScreenScene } from "./problem-scenes";
import { ProblemTabs } from "./problem-tabs";

/**
 * Where applications get lost (KAN-923), right after the logo strip, so the
 * page says why before it says how: the user asked for the common problems
 * with applying, the hiring system's screen first, designed rather than set
 * as text. The heading on the left with its line beside it, then one wide
 * frame holding one real-looking screen, and the three problems under it as
 * columns; a click on a problem shows its screen (`ProblemTabs`). Each
 * problem says what goes wrong, then one line on what WorkIt does, after
 * the WorkIt mark.
 *
 * It follows the taste rules' "chapter" (one feature area: a paragraph, a
 * wide frame of the product doing it, the names under it). It replaced a
 * bento of three cards, each a small scene centred in a coloured box, which
 * the user found ugly and AI-made; the taste rules say why: the three
 * problems are equal but the bento made one twice the size, the product
 * showed only as small pieces on coloured panels, and the boxes nested three
 * deep. The screens are in problem-scenes.tsx.
 *
 * The frame's sky is slate, not a feature's colour: this is the search as it
 * is, before WorkIt; the violet is WorkIt's own mark. Copy, hedging and
 * sources: `problems` in data.ts.
 */
const GROUND = studioGround({ glow: "var(--color-ink-meta)" });

/** Keyed, since they reach `ProblemTabs` as a list. */
const SCENES = {
  screen: <ScreenScene key="screen" />,
  forms: <FormsScene key="forms" />,
  boards: <BoardsScene key="boards" />,
};

export function Problems() {
  const { title, subtitle, items } = problems;
  return (
    <section aria-labelledby="problems-title" className="py-16 sm:py-24">
      <div className={CONTAINER}>
        <div className="grid gap-5 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:items-end lg:gap-12">
          <h2 id="problems-title" className={cn(TYPE.chapter, "text-ink")}>
            {title}
          </h2>
          <p className={cn(TYPE.lead, "text-ink-meta lg:pb-1.5")}>{subtitle}</p>
        </div>
        <ProblemTabs
          problems={items}
          scenes={items.map((item) => SCENES[item.scene])}
          ground={GROUND}
        />
      </div>
    </section>
  );
}
