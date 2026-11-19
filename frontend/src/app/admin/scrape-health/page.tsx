import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { cn } from "@/lib/cn";
import { daysOf } from "@/lib/fill-health";
import { getScrapeHealth } from "@/lib/fill-report-queries";

import { Panel } from "../panel";
import { DailyReads, SystemBars } from "./charts";
import { ScrapeRail } from "./rail";
import { ReadsTable } from "./reads-table";
import { ScrapeTiles } from "./tiles";

export const metadata: Metadata = { title: "Scrape Health" };

const when = (iso: string | null) =>
  iso ? new Date(iso).toISOString().slice(0, 16).replace("T", " ") : "Never";

/**
 * The scraper's health (KAN-879), the admins' page, as a dashboard: four
 * headline tiles, the period's board reads per day as a chart beside the
 * boards per hiring system, the Board Reads table with its filters, and a
 * rail (./rail.tsx) with the counts now and the failing boards. The day
 * pills pick the period for all of it. The API keeps its answer for 10
 * minutes, so the page says when it was read and has no Refresh. Only
 * WorkIt's admins (the API's WORKIT_ADMINS) see it; anyone else gets the
 * 404, as /admin/fill-health.
 */
export default async function ScrapeHealthPage({
  searchParams,
}: PageProps<"/admin/scrape-health">) {
  const params = await searchParams;
  const days = daysOf(params.days);
  const { data, status } = await getScrapeHealth(days);
  if (status === 401) redirect("/login");
  if (!data) notFound();

  return (
    <div className="flex min-h-full flex-col lg:h-full lg:flex-row">
      <main className="@container min-w-0 flex-1 px-6 py-8 lg:overflow-y-auto lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-ink text-3xl font-semibold tracking-tight">Scrape Health</h1>
            <p className="text-body text-ink-meta mt-1">
              Read at {when(data.read_at)} UTC. Kept for 10 minutes.
            </p>
          </div>
          <nav aria-label="Period" className="flex flex-wrap gap-2">
            {[1, 7, 14, 30, 90].map((d) => (
              <Link
                key={d}
                href={`/admin/scrape-health?days=${d}`}
                aria-current={d === days ? "true" : undefined}
                className={cn(
                  "text-label rounded-full border px-3.5 py-2",
                  d === days
                    ? "border-brand bg-brand text-on-brand"
                    : "border-border-surface bg-panel text-ink hover:border-ink-meta",
                )}
              >
                {d} {d === 1 ? "day" : "days"}
              </Link>
            ))}
          </nav>
        </div>

        <p className="rounded-card border-brand-pale bg-brand-tint text-body text-ink mt-5 border px-4 py-3">
          The scheduled scrape last imported jobs at {when(data.last_import_at)} UTC. The worker
          these numbers describe is not scheduled yet.
          {data.boards.oldest_pending_at &&
            ` Its oldest pending task was made ${when(data.boards.oldest_pending_at)} UTC.`}
        </p>

        <div className="mt-5 space-y-5">
          <ScrapeTiles data={data} days={days} />
          <div className="grid grid-cols-1 gap-5 @4xl:grid-cols-5">
            <Panel title="Board Reads per Day" className="@4xl:col-span-3">
              <DailyReads rows={data.days} days={days} />
            </Panel>
            <Panel title="Boards by Hiring System" className="@4xl:col-span-2">
              <SystemBars systems={data.systems} />
            </Panel>
          </div>
          <ReadsTable rows={data.days} />
        </div>
      </main>
      <ScrapeRail data={data} />
    </div>
  );
}
