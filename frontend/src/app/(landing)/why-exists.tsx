import { Arrive } from "./arrive";
import { whyExists } from "./data";
import { DraftLines } from "./draft-lines";
import { HeroPipeline } from "./hero-pipeline";
import { CONTAINER, SectionHeading } from "./layout-parts";

/**
 * That's why WorkIt exists (KAN-923, after Loopsii's "That's why Loopsii
 * exists", the user's ask, 2026-11-20): the turn from the problems to the
 * product. Under the heading stand the four pipeline cells (hero-pipeline.tsx)
 * in the drafting grid's frame, each a link to its product section, which
 * starts right below.
 *
 * The cells were the hero's until 2026-11-23, and this section held a
 * placeholder for the product demo, a white screen with a play mark and
 * "Product demo, coming soon": the largest picture on the page was empty,
 * and the team found the page less impressive than the old one. So the
 * placeholder went and the cells came here (the team's call), between the
 * problems they answer and the sections they open. A recording of the app
 * can join them once one exists.
 *
 * The frame holds the heading and the cells, as the hero's frame held its
 * words and the cells: the cells draw their own rule across the window at
 * their top, their dividers and the foot's squares (`.pipe-lines`), so the
 * frame's gap is the 1.5rem those lines expect. The cells are drawn as the
 * section arrives (`Arrive`, `.pipe-arrive` in landing.css), no longer on
 * load, when they would have played below the screen.
 */
export function WhyExists() {
  return (
    <section aria-labelledby="why-exists-title" className="py-16 sm:py-24">
      <div className={CONTAINER}>
        <div className="relative">
          <DraftLines gap="1.5rem" />
          <SectionHeading id="why-exists-title" title={whyExists.title} />
          <Arrive className="pipe-arrive mt-10 sm:mt-14">
            <HeroPipeline />
          </Arrive>
        </div>
      </div>
    </section>
  );
}
