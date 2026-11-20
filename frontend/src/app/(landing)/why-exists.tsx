import { PlayIcon } from "@phosphor-icons/react/ssr";

import { whyExists } from "./data";
import { DraftLines } from "./draft-lines";
import { CONTAINER, SectionHeading, StudioBox, studioGround } from "./layout-parts";

/**
 * That's why WorkIt exists (KAN-923, after Loopsii's "That's why Loopsii
 * exists", the user's ask, 2026-11-20): the turn from the problems to the
 * product, a chapter heading over the product demo, in the drafting grid's
 * frame. The demo stands in a glass frame (`.demo-glass` in landing.css: a
 * frosted white bezel with a bright edge) on WorkIt's violet sky in a
 * `StudioBox`, so the glass has colour to blur and the page's colour stays
 * inside a box.
 *
 * The screen is a placeholder until a recording exists (the user's call):
 * white, with a play mark and "Product demo, coming soon", so it never
 * passes for the product. Replace the screen's contents with the recording
 * (or a screenshot) at the same 16:10, and drop the line.
 */
export function WhyExists() {
  return (
    <section aria-labelledby="why-exists-title" className="py-16 sm:py-24">
      <div className={CONTAINER}>
        <SectionHeading id="why-exists-title" title={whyExists.title} />
        <div className="relative mt-10 sm:mt-14">
          <DraftLines gap="1.25rem" />
          <StudioBox
            ground={studioGround({ glow: "var(--color-brand)" })}
            className="p-4 sm:p-10 lg:p-14"
          >
            <div className="demo-glass mx-auto max-w-5xl rounded-[1.75rem] p-2 sm:p-3">
              <div className="grid aspect-[16/10] place-items-center rounded-[1.25rem] bg-white shadow-[inset_0_0_0_1px_rgb(15_23_42/0.08)]">
                <div className="flex flex-col items-center gap-3">
                  <span
                    aria-hidden="true"
                    className="bg-ink grid size-14 place-items-center rounded-full text-white sm:size-16"
                  >
                    <PlayIcon weight="fill" className="ml-0.5 size-6" />
                  </span>
                  <p className="text-ink-meta text-sm font-medium">{whyExists.demo}</p>
                </div>
              </div>
            </div>
          </StudioBox>
        </div>
      </div>
    </section>
  );
}
