import type { ScrapeHealth } from "@/lib/fill-health";
import { systemName } from "@/lib/scrape-status";

import { SCRAPE_SECTIONS } from "../pages";
import { Panel } from "../panel";

/**
 * The boards an admin acts on (KAN-879): each failing board with its
 * hiring system, its failed reads in a row and its last error, most
 * failures first. It was a card in a rail the admin could close, beside a
 * list of counts the tiles already showed; the rail went, and this is the
 * part of it that was not a repeat.
 */
export function NeedsAttention({ failing }: { failing: ScrapeHealth["failing"] }) {
  return (
    <Panel
      section={SCRAPE_SECTIONS.attention}
      bodyClassName="p-0"
      action={
        failing.length > 0 && (
          <span className="text-note text-ink-meta">
            {failing.length} failing {failing.length === 1 ? "board" : "boards"}
          </span>
        )
      }
    >
      {failing.length === 0 ? (
        <p className="text-body text-ink-muted p-5">
          No board is failing. A board shows here after a failed read, with the error.
        </p>
      ) : (
        <ul>
          {failing.map((b) => (
            <li
              key={`${b.ats}:${b.token}`}
              className="border-border-subtle flex items-start gap-3 border-b px-5 py-3 last:border-b-0"
            >
              <div className="min-w-0 flex-1">
                <p className="text-body text-ink font-medium">{b.company}</p>
                <p className="text-note text-ink-meta [overflow-wrap:anywhere]">
                  {systemName(b.ats)} · {b.token}
                </p>
                {b.last_error && (
                  <p className="text-note text-danger mt-1 [overflow-wrap:anywhere]">
                    {b.last_error}
                  </p>
                )}
              </div>
              <span className="bg-danger-tint text-danger text-note rounded-full px-2 py-0.5 whitespace-nowrap">
                {b.consecutive_failures} failed
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
