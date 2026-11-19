import { CheckIcon } from "@phosphor-icons/react/ssr";
import Image from "next/image";

import { cn } from "@/lib/cn";

import { hiringSystems, hiringSystemsSection, moreHiringSystems } from "./data";
import { FEATURES } from "./features/catalog";
import { CONTAINER, StudioBox, studioGround, TYPE } from "./layout-parts";

/**
 * Where the jobs come from (KAN-923), after Calendly's integrations grid:
 * the copy on one side, and on the other the hiring systems WorkIt reads,
 * each logo on a white tile in a framed box, ending on how many more it
 * reads. It replaced the pinned 3D pipeline (hiring-pipeline.tsx, kept
 * unmounted). Still: the page has motion enough above. The Features menu's
 * foot row links here (`#hiring-systems`). Copy: `hiringSystemsSection`.
 */
export function HiringGrid() {
  const { eyebrow, title, subtitle, steps } = hiringSystemsSection;
  const matching = FEATURES.matching;
  return (
    <section id="hiring-systems" aria-labelledby="hiring-systems-title" className="py-16 sm:py-24">
      <div className={cn(CONTAINER, "grid items-center gap-10 lg:grid-cols-2 lg:gap-16")}>
        <div>
          <p className={cn(TYPE.eyebrow, "text-landing-brand-700")}>{eyebrow}</p>
          <h2 id="hiring-systems-title" className={cn(TYPE.product, "text-ink mt-4")}>
            {title}
          </h2>
          <p className="text-ink-meta mt-5 text-lg text-pretty">{subtitle}</p>
          <ul className="mt-7 grid gap-3 sm:grid-cols-2">
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
        <StudioBox
          ground={studioGround({
            tint: matching.tint,
            glow: matching.glow,
            accent: "var(--color-advanced)",
          })}
          className="p-4 sm:p-8"
        >
          <ul className="grid grid-cols-4 gap-2 pb-2 sm:gap-4 sm:pb-4">
            {hiringSystems.map((system, i) => (
              <li
                key={system.name}
                // Every other column sits a little lower, so the grid reads
                // as tiles laid on the box, not a table.
                className={cn(
                  "flex aspect-square flex-col items-center justify-center gap-1.5 rounded-xl bg-white p-1.5 shadow-[0_1px_2px_rgb(30_20_70/0.06),0_10px_24px_-12px_rgb(40_20_90/0.3)] sm:gap-2.5 sm:rounded-2xl sm:p-3",
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
                <span className="text-ink text-[10px] font-semibold sm:text-xs">{system.name}</span>
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
    </section>
  );
}
