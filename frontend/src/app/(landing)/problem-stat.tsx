import { ArrowUpRightIcon } from "@phosphor-icons/react/ssr";

import { cn } from "@/lib/cn";

type Stat = { figure: string; text: string; source: string; href: string };

/**
 * The problems section's one figure, shown as a fact with its source
 * (`problems.stat` in data.ts: 81%, Greenhouse's 2026 candidate report).
 *
 * **Archived, unmounted** (the user's call, 2026-11-21). It was the last
 * row of the problems hub (problem-hub.tsx), an outlined strip across the
 * hub's width, and read as hiding at the foot. It waits here for a better
 * place; to bring it back, render `<ProblemStat stat={problems.stat} />`.
 *
 * Its look, from the user's calls of 2026-11-20: no fill, a slate
 * hairline, the number large in ink, its sentence and its source. Filled
 * like the hub's cards it blended in; as an outlined box with quote marks
 * it read as tacked on; its number was a light red, which read as a
 * template's stat callout.
 */
export function ProblemStat({ stat, className }: { stat: Stat; className?: string }) {
  return (
    <figure
      className={cn(
        "grid items-center gap-x-7 gap-y-1.5 rounded-2xl px-5 py-5 ring-1 ring-slate-900/[0.12] ring-inset sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:px-7",
        className,
      )}
    >
      <p className="font-display text-ink text-[3.25rem] leading-none font-medium tracking-[-0.04em]">
        {stat.figure}
      </p>
      <p className="text-ink text-[17px] leading-snug text-pretty">{stat.text}</p>
      <figcaption className="text-ink-meta text-[13px]">
        <a
          href={stat.href}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-ink inline-flex items-center gap-1 underline decoration-slate-900/25 underline-offset-2"
        >
          {stat.source}
          <ArrowUpRightIcon aria-hidden="true" className="size-3" />
        </a>
      </figcaption>
    </figure>
  );
}
