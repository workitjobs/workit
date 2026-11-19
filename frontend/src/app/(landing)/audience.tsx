import { cn } from "@/lib/cn";

import { audience } from "./data";
import { CONTAINER, SectionHeading, TYPE } from "./layout-parts";

/**
 * Who WorkIt is for and the problem it fixes (KAN-923), right after the
 * logo strip, so the page says why before it says how: a centred chapter
 * heading naming the audience, then three pains in the student's own
 * words, side by side under hairlines from lg up (stacked below: at 768
 * wide three columns were 220px, too narrow for the 28px lines), as plain
 * type. No feature names and
 * no cards: the features card and the product sections below answer them.
 * After Calendly's "Built for people whose work runs on meetings", which
 * names its reader before its products. It took the place of the journey
 * ("One application, start to finish", journey.tsx, unmounted), which
 * repeated the four features a third time. Copy: `audience` in data.ts.
 */
export function Audience() {
  const { title, subtitle, pains } = audience;
  return (
    <section aria-labelledby="audience-title" className="py-16 sm:py-24">
      <div className={CONTAINER}>
        <SectionHeading id="audience-title" title={title} subtitle={subtitle} />
        <ul className="mt-12 grid gap-8 sm:mt-16 lg:grid-cols-3 lg:gap-10">
          {pains.map((pain) => (
            <li key={pain.line} className="border-t border-slate-900/10 pt-6">
              <p className={cn(TYPE.card, "text-ink text-balance")}>{pain.line}</p>
              <p className="text-ink-meta mt-3 text-pretty">{pain.detail}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
