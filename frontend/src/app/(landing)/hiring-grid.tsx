import { CheckIcon } from "@phosphor-icons/react/ssr";
import Image from "next/image";

import { cn } from "@/lib/cn";

import { hiringSystems, hiringSystemsSection, moreHiringSystems } from "./data";
import { DraftLines } from "./draft-lines";
import { FEATURES } from "./features/catalog";
import { CONTAINER, SectionHeading, StudioBox, studioGround } from "./layout-parts";

/**
 * Where the jobs come from (KAN-923), after Calendly's integrations
 * section: a centred chapter, not a product. The heading and its line in
 * the chapter's sans (`SectionHeading`), the hiring systems WorkIt reads as
 * one row of logo tiles across a wide framed box, ending on how many more it
 * reads, then what WorkIt does to the postings as four ticks. It sat beside
 * its box in a product section's serif and halves, after the product
 * sections, and read as a fifth product; the user had the Application
 * Tracker take that place. It replaced the pinned 3D pipeline
 * (hiring-pipeline.tsx, kept unmounted). Still: the page has motion enough
 * above. The Features menu's foot row links here (`#hiring-systems`). Copy:
 * `hiringSystemsSection`.
 */
export function HiringGrid() {
  const { title, subtitle, steps } = hiringSystemsSection;
  const matching = FEATURES.matching;
  return (
    <section id="hiring-systems" aria-labelledby="hiring-systems-title" className="py-20 sm:py-28">
      <div className={CONTAINER}>
        <SectionHeading id="hiring-systems-title" title={title} subtitle={subtitle} />
        {/* The drafting grid's frame round the box and its steps, at the
            container's width so its sides join the page's rail, and
            outside the box, which clips what it holds. */}
        <div className="relative mt-12 sm:mt-16">
          <DraftLines gap="1.25rem" />
          <StudioBox
            ground={studioGround({ glow: matching.glow })}
            className="mx-auto max-w-5xl p-4 sm:p-8"
          >
            <ul className="grid grid-cols-4 gap-2 pb-2 sm:gap-4 sm:pb-4 lg:grid-cols-8">
              {hiringSystems.map((system, i) => (
                <li
                  key={system.name}
                  // Every other column sits a little lower, so the row reads
                  // as tiles laid on the box, not a table.
                  className={cn(
                    "flex aspect-square flex-col items-center justify-center gap-1.5 rounded-xl bg-white p-1.5 shadow-[var(--mk-shadow-float)] sm:gap-2.5 sm:rounded-2xl sm:p-3",
                    i % 2 === 1 && "translate-y-2 sm:translate-y-4",
                  )}
                >
                  <Image
                    src={system.logo}
                    alt=""
                    width={40}
                    height={40}
                    className="size-7 object-contain sm:size-10"
                  />
                  <span className="text-ink text-[10px] font-semibold sm:text-xs">
                    {system.name}
                  </span>
                </li>
              ))}
              <li className="text-ink-meta flex aspect-square translate-y-2 flex-col items-center justify-center rounded-xl bg-white/50 p-1.5 text-center ring-1 ring-white/80 sm:translate-y-4 sm:rounded-2xl sm:p-3">
                <span className="text-ink font-display text-lg font-medium sm:text-2xl">
                  +{moreHiringSystems}
                </span>
                <span className="mt-0.5 text-[10px] font-medium sm:mt-1 sm:text-xs">more</span>
              </li>
            </ul>
          </StudioBox>
        </div>
        <ul className="mx-auto mt-10 grid max-w-5xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step) => (
            <li key={step} className="text-ink-muted flex items-start gap-2.5 text-[15px]">
              <span
                aria-hidden="true"
                className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full"
                style={{ background: matching.tint, color: matching.onGlow.fill }}
              >
                <CheckIcon weight="bold" className="size-3" />
              </span>
              {step}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
