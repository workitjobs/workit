import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { cn } from "@/lib/cn";
import { getScrapeHealth } from "@/lib/fill-report-queries";
import { datesOf, HISTORY, statusOf, windowOf } from "@/lib/scrape-status";

import { ADMIN_FRAME } from "../panel";
import { NeedsAttention } from "./needs-attention";
import { ScrapeNumbers } from "./numbers";
import { ReadsChart } from "./reads-chart";
import { ReadsExplorer } from "./reads-explorer";
import { StatusLine } from "./status-line";
import { WindowControls } from "./window-controls";

export const metadata: Metadata = { title: "Scrape Health" };

/**
 * The scraper's health (KAN-879), the admins' page. It answers one
 * question first, whether the scrape is running (./status-line.tsx, by
 * lib/scrape-status.ts's rule), then gives the detail in one scroll: the
 * status beside four numbers in one box, the reads per day beside the
 * failing boards, the boards per hiring system, and the Board Reads table.
 * The window controls in the title row set the days all of it shows, held
 * in the address.
 *
 * It always asks the API for HISTORY days and cuts the window itself, so
 * the API keeps one answer for 10 minutes whatever the window, and the page
 * says when that answer was read and has no Refresh. Only WorkIt's admins
 * (the API's WORKIT_ADMINS) see it; anyone else gets the 404, as
 * /admin/fill-health.
 */
export default async function ScrapeHealthPage({
  searchParams,
}: PageProps<"/admin/scrape-health">) {
  const window = windowOf(await searchParams);
  const { data: all, status } = await getScrapeHealth(HISTORY);
  if (status === 401) redirect("/login");
  if (!all) notFound();

  const readAt = Date.parse(all.read_at);
  /** The newest day the page can show: the day (UTC) the API's answer was read. */
  const today = all.read_at.slice(0, 10);
  const dates = datesOf(window, today);
  /** The answer cut to the page's window, for the tiles, the chart and the table. */
  const rows = all.days.filter((r) => r.day >= dates[0] && r.day <= dates[dates.length - 1]);
  const data = { ...all, days: rows };

  return (
    <main className={cn("@container/main", ADMIN_FRAME)}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-heading text-ink">Scrape Health</h1>
          <p className="text-note text-ink-meta mt-1">
            Read at {all.read_at.slice(0, 16).replace("T", " ")} UTC. The numbers are kept for 10
            minutes.
          </p>
        </div>
        <WindowControls window={window} today={today} />
      </div>

      <div className="mt-6 flex flex-col gap-4">
        {/* Two rows of a wide card beside a narrow one, from 896px of page. */}
        <div className="grid gap-4 @4xl/main:grid-cols-3">
          <StatusLine status={statusOf(all, readAt)} data={all} className="@4xl/main:col-span-2" />
          <ScrapeNumbers data={data} />
          <ReadsChart rows={rows} dates={dates} className="@4xl/main:col-span-2" />
          <NeedsAttention failing={all.failing} />
        </div>
        <ReadsExplorer systems={all.systems} rows={rows} />
      </div>
    </main>
  );
}
