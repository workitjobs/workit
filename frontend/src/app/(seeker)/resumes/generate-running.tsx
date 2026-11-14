"use client";

import { FileTextIcon } from "@phosphor-icons/react/ssr";

import { StepsDialog } from "@/components/steps-dialog";
import { cn } from "@/lib/cn";

/** Generate's steps, in order (KAN-444). The first runs until the API's
 *  first line (`checking`), the API names the next two as it starts them
 *  (`GenerateStreamEvent`), and the last is the editor loading the new
 *  resume, as a Tailor run ends. The dialog opens at `saving`, the first
 *  two ticked, since a copy is asked about before it: the button says
 *  "Checking…" until then. After a Confirm it opens at `reading`. */
const STEP = {
  reading: "Reading your experience bank",
  checking: "Checking your resumes for a copy",
  saving: "Saving your new resume",
  opening: "Opening your resume",
} as const;
export type GenerateStep = keyof typeof STEP;

/** The little page's rows, top to bottom: a section's heading, or a line
 *  at a share of the column. */
const ROWS = [
  { heading: 30 },
  { line: 92 },
  { line: 78 },
  { heading: 24 },
  { line: 96 },
  { line: 86 },
  { line: 64 },
  { heading: 34 },
  { line: 90 },
  { line: 72 },
];

/** A resume, drawn small, whose lines write themselves in from the top:
 *  Generate shown as what it does, a page laid out from the bank. Tailor's
 *  page turns lines brand instead, since it rewrites them. No sparkle on
 *  it: Generate calls no model. */
function WritingPage() {
  return (
    <div
      aria-hidden
      className="bg-brand-tint relative flex h-44 justify-center overflow-hidden pt-6"
    >
      <div className="relative">
        <div className="bg-panel shadow-lift h-56 w-40 rounded-t-md px-4 pt-4">
          <span className="bg-ink/70 mx-auto block h-1.5 w-1/2 rounded-full" />
          <span className="bg-ink/15 mx-auto mt-1 block h-1 w-3/4 rounded-full" />
          {ROWS.map((row, i) => {
            const heading = "heading" in row;
            return (
              <span
                key={`${heading ? "heading" : "line"}-${i}`}
                className={cn(
                  "block h-1 overflow-hidden rounded-full",
                  heading ? "mt-3" : "mt-1.5",
                )}
                style={{ width: `${heading ? row.heading : row.line}%` }}
              >
                <span
                  className={cn(
                    "animate-rewrite block h-full origin-left rounded-full",
                    heading ? "bg-ink/40" : "bg-ink/15",
                  )}
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              </span>
            );
          })}
        </div>
        <span className="bg-brand text-on-brand shadow-lift absolute -top-2.5 -right-3 flex size-7 items-center justify-center rounded-full">
          <FileTextIcon aria-hidden className="size-3.5" />
        </span>
      </div>
    </div>
  );
}

/**
 * Generate on the Resumes page (KAN-444): the shared steps dialog with a
 * page writing itself and Generate's steps as they happen. Until then the
 * button's label read "Generating…" for the whole wait, about 3.6 s from a
 * laptop, and nothing else moved. A saved resume opens in the editor, and
 * the dialog stays until the editor's page replaces this one. A failure
 * closes it and shows its error over the list.
 */
export function GenerateRunning({ step }: { step: GenerateStep | null }) {
  return (
    <StepsDialog
      open={step !== null}
      title="Generating Your Resume"
      art={<WritingPage />}
      steps={STEP}
      at={step ?? "reading"}
    />
  );
}
