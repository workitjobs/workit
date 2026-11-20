import { problems } from "./data";
import { CONTAINER, SectionHeading } from "./layout-parts";
import { BoardsScene, FormsScene, ScreenScene } from "./problem-scenes";
import { ProblemTabs } from "./problem-tabs";

/**
 * Where applications get lost (KAN-923), right after the logo strip, so the
 * page says why before it says how: the user asked for the common problems
 * with applying, the hiring system's screen first, designed rather than set
 * as text. A centred chapter heading, one wide flat frame holding one
 * real-looking screen, and three problem cards under it; a click on a card
 * shows its screen (`ProblemTabs`). Each card names the problem in one
 * line; the open one adds what WorkIt does, after the WorkIt mark.
 *
 * It follows the taste rules' "chapter" (one wide frame of the thing
 * itself, the names under it). It replaced a bento of three cards, each a
 * small scene centred in a coloured box, which the user found ugly and
 * AI-made; the taste rules say why: the three problems are equal but the
 * bento made one twice the size, the product showed only as small pieces
 * on coloured panels, and the boxes nested three deep. The screens are in
 * problem-scenes.tsx; copy, hedging and sources: `problems` in data.ts.
 */

/** Keyed, since they reach `ProblemTabs` as a list. */
const SCENES = {
  screen: <ScreenScene key="screen" />,
  forms: <FormsScene key="forms" />,
  boards: <BoardsScene key="boards" />,
};

export function Problems() {
  const { title, items } = problems;
  return (
    <section aria-labelledby="problems-title" className="py-16 sm:py-24">
      <div className={CONTAINER}>
        <SectionHeading id="problems-title" title={title} />
        <ProblemTabs problems={items} scenes={items.map((item) => SCENES[item.scene])} />
      </div>
    </section>
  );
}
