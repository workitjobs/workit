import {
  ArrowCounterClockwiseIcon,
  CursorClickIcon,
  PencilSimpleLineIcon,
  SquaresFourIcon,
} from "@phosphor-icons/react/ssr";

import { cn } from "@/lib/cn";

import { control } from "./data";
import { CONTAINER, SectionHeading, TYPE } from "./layout-parts";

/** Each promise's mark, by its `icon` in data.ts. */
const ICONS = {
  submit: CursorClickIcon,
  truth: ArrowCounterClockwiseIcon,
  words: PencilSimpleLineIcon,
  five: SquaresFourIcon,
};

/**
 * The promises behind the product (KAN-923), after the product sections:
 * the worry any auto apply tool raises (will it send things for me, make
 * things up, spam employers?) answered as what WorkIt does. The heading
 * holds the left column from lg up, as the FAQ's does, and the four
 * promises sit beside it as `.surface-card`s, each with its mark in ink on
 * a slate tile, never violet (the marketing design system's principle 2).
 * It says positively what the archived statement ("Slop applications get
 * skipped") said as a warning. Copy and sources: `control` in data.ts.
 */
export function Control() {
  const { title, subtitle, promises } = control;
  return (
    <section aria-labelledby="control-title" className="py-20 sm:py-28">
      <div
        className={cn(
          CONTAINER,
          "grid gap-12 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:items-start lg:gap-16",
        )}
      >
        <SectionHeading
          id="control-title"
          align="left"
          className="max-lg:mx-auto max-lg:text-center"
          title={title}
          subtitle={subtitle}
        />
        <ul className="grid gap-3 sm:grid-cols-2">
          {promises.map((promise) => {
            const Icon = ICONS[promise.icon];
            return (
              <li key={promise.title} className="surface-card rounded-2xl p-6">
                <span
                  aria-hidden="true"
                  className="text-ink grid size-10 place-items-center rounded-xl bg-slate-900/[0.05]"
                >
                  <Icon className="size-5" />
                </span>
                <h3 className={cn(TYPE.item, "text-ink mt-5")}>{promise.title}</h3>
                <p className="text-ink-meta mt-2 text-pretty">{promise.body}</p>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
