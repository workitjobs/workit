"use client";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/shadcn/popover";
import { cn } from "@/lib/cn";

/**
 * A job posting's location where it lists more than one place: the first
 * place, then "+2 more", which opens every place in a small popover, on
 * hover with a mouse and on a press or a tap (2026-11-10). It was the text
 * "Novi, MI +1 more", whose hover title only repeated itself, and on a card
 * the click layer took even that: there was no way to see the other places.
 *
 * The first place truncates and "+N more" never does, so the way to the
 * rest always shows. The trigger sits above a card's click layer
 * (`relative z-2`, components/job-posting-card.tsx), so a press on it opens
 * the list, not the job. Used by the job cards' facts (`JobFactGrid`) and a
 * job's own page (job-detail/job-facts.tsx).
 */
export function PlacesValue({ places, wrap = false }: { places: string[]; wrap?: boolean }) {
  const [first, ...rest] = places;
  return (
    <span
      className={cn("inline-flex max-w-full min-w-0 items-baseline gap-1", wrap && "flex-wrap")}
    >
      <span className={wrap ? "break-words" : "truncate"}>{first}</span>
      <Popover>
        <PopoverTrigger
          openOnHover
          delay={150}
          aria-label={`${rest.length} more ${rest.length === 1 ? "location" : "locations"}`}
          className="text-brand hover:text-brand-hover focus-visible:ring-brand-ring data-popup-open:text-brand-hover relative z-2 shrink-0 cursor-pointer rounded-xs whitespace-nowrap underline decoration-dotted underline-offset-2 transition-colors duration-150 focus-visible:ring-2 focus-visible:outline-none"
        >
          +{rest.length} more
        </PopoverTrigger>
        <PopoverContent align="start" className="w-auto max-w-72 gap-1.5 p-3">
          <p className="text-note text-ink-meta">{places.length} locations</p>
          <ul className="flex flex-col gap-1">
            {places.map((place) => (
              <li key={place} className="text-body text-ink">
                {place}
              </li>
            ))}
          </ul>
        </PopoverContent>
      </Popover>
    </span>
  );
}
