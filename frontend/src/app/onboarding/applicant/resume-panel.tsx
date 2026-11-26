"use client";

import { useRef } from "react";

import { Fit } from "@/app/(landing)/fit";

import { ResumeSketch } from "./resume-sketch";

/**
 * Onboarding's right half on the resume step. It follows the student's
 * answer to "Do you have a resume?" (2026-11-17), the pick counting before
 * Continue: their resume being scanned for Yes, which the step opens on,
 * and a resume being generated under their name for No (./resume-sketch).
 *
 * Once the resume is made or saved, the step itself shows it, in the real
 * editor, full width (./made-review), and this half steps aside.
 *
 * The landing tour's Resumes story stood here with nothing picked, and the
 * Jobs page mock (./preview-panel) before it: the user found the one a
 * marketing graphic out of place in the app, and the other said nothing
 * about a resume. `Fit` scales the sketch to the half, as the tour does. A
 * new scene arrives keyed on the answer (`animate-arrive`), so its
 * animations start again on each pick. Decoration, aria-hidden.
 */
export function ResumePanel({
  plan,
  name,
}: {
  plan: "upload" | "build";
  /** The account's name, the one line of words on the sketch. */
  name: string;
}) {
  const box = useRef<HTMLDivElement>(null);
  return (
    <aside
      aria-hidden
      className="bg-brand-tint relative hidden overflow-hidden lg:flex lg:w-1/2 lg:flex-col"
    >
      <div ref={box} className="flex min-h-0 flex-1 items-center justify-center px-10 py-12">
        <div key={plan} className="animate-arrive">
          <Fit box={box} max={1.25}>
            <ResumeSketch mode={plan} name={name} />
          </Fit>
        </div>
      </div>
    </aside>
  );
}
