import type { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * One fact about a job: a glyph and the value beside it.
 *
 * The unit both job screens are built from — a search result stacks two of
 * these, a recommendation card lays six out on a grid — which is what moved it
 * here from search/page.tsx.
 *
 * `truncate` on the value rather than on the row is deliberate: it keeps the
 * icon at full size and clips only the text, so a long location loses its tail
 * instead of squeezing its pin. That only works because the icon is `shrink-0`
 * and the row can be given a width by whatever lays it out.
 *
 * The value is ink and the glyph ink-meta: the value is what a reader came
 * for, the glyph only says which fact it is. Both were ink-meta until
 * 2026-10-09, and the job card's facts read as faint beside its title. `title` puts the
 * whole value on the clipped text's hover, for a value that may not fit.
 *
 * `size="md"` is the Jobs page card's (2026-11-09): 14px values beside 16px
 * glyphs in ink-muted. At 12px with 14px grey glyphs the six facts read as
 * fine print under the title, though they are what a student scans the card
 * for. A job's own page takes it too (job-detail/job-facts.tsx, 2026-11-10);
 * the compact cards and the lists keep the small size.
 *
 * `wrap` lets a long value take a second line instead of its tail, with the
 * glyph on the first line: a job's own page, where a phone's two columns cut
 * "Start in Spring 2027" at 14px and a touch screen has no hover to show it.
 */
export function Fact({
  Icon,
  title,
  size = "sm",
  wrap = false,
  className,
  children,
}: {
  Icon: ComponentType<{ className?: string }>;
  title?: string;
  size?: "sm" | "md";
  wrap?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "text-ink flex min-w-0",
        wrap ? "items-start" : "items-center",
        size === "md" ? "text-body gap-2" : "text-note gap-1.5",
        className,
      )}
    >
      <Icon
        aria-hidden
        className={cn(
          "shrink-0",
          size === "md" ? "text-ink-muted size-4" : "text-ink-meta size-3.5",
          // On the first line's middle: (20px line - 16px glyph) / 2.
          wrap && (size === "md" ? "mt-0.5" : "mt-[1px]"),
        )}
      />
      <span title={title} className={wrap ? "min-w-0 break-words" : "truncate"}>
        {children}
      </span>
    </span>
  );
}
