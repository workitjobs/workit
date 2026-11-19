import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { daysOf } from "@/lib/fill-health";
import { getScrapeHealth } from "@/lib/fill-report-queries";

import { ScrapeRail } from "./rail";

export const metadata: Metadata = { title: "Scrape Health" };

const when = (iso: string | null) =>
  iso ? new Date(iso).toISOString().slice(0, 16).replace("T", " ") : "Never";

const TH = "text-label text-ink-meta px-3 py-2.5 font-normal";
const TD = "px-3 py-3";

/**
 * The scraper's health (KAN-879), the admins' page: per hiring system, the
 * boards and how many were ever read; per day (UTC) per hiring system, the
 * board reads done and failed, their mean time and the new jobs; and a rail
 * (./rail.tsx) with the totals and the failing boards. The API keeps its
 * answer for 10 minutes, so the page says when it was read and has no
 * Refresh. Only WorkIt's admins (the API's WORKIT_ADMINS) see it; anyone
 * else gets the 404, as /admin/fill-health.
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
      <main className="min-w-0 flex-1 px-6 py-8 lg:overflow-y-auto lg:px-10">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-ink text-3xl font-semibold tracking-tight">Scrape Health</h1>
          <p className="border-border-surface bg-panel text-label text-ink-muted rounded-control border px-3 py-2 font-normal">
            Read at {when(data.read_at)} UTC · kept for 10 minutes
          </p>
        </div>
        <p className="rounded-card border-brand-pale bg-brand-tint text-body text-ink mt-5 border px-4 py-3">
          The scheduled scrape last imported jobs at {when(data.last_import_at)} UTC. The worker
          these numbers describe is not scheduled yet.
          {data.boards.oldest_pending_at &&
            ` Its oldest pending task was made ${when(data.boards.oldest_pending_at)} UTC.`}
        </p>

        <Card as="section" padding="lg" className="mt-4" aria-labelledby="reads">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="reads" className="text-title text-ink">
              Board Reads
            </h2>
            <nav aria-label="Days" className="flex flex-wrap gap-2">
              {[1, 7, 14, 30, 90].map((d) => (
                <Link
                  key={d}
                  href={`/admin/scrape-health?days=${d}`}
                  aria-current={d === days ? "true" : undefined}
                  className={cn(
                    "text-label rounded-full border px-3 py-1.5",
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
          {data.days.length === 0 ? (
            <p className="text-body text-ink-muted mt-4">No board reads in this period.</p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="text-body w-full border-collapse text-left">
                <thead>
                  <tr className="border-border-subtle border-b">
                    <th className={TH}>Day (UTC)</th>
                    <th className={TH}>Hiring System</th>
                    <th className={cn(TH, "text-right")}>Done</th>
                    <th className={cn(TH, "text-right")}>Failed</th>
                    <th className={cn(TH, "text-right")}>Mean Seconds</th>
                    <th className={cn(TH, "text-right")}>New Jobs</th>
                  </tr>
                </thead>
                <tbody>
                  {data.days.map((r) => (
                    <tr
                      key={`${r.day}:${r.ats}`}
                      className="border-border-subtle text-ink hover:bg-hover border-b last:border-b-0"
                    >
                      <td className={cn(TD, "whitespace-nowrap")}>{r.day}</td>
                      <td className={cn(TD, "font-medium capitalize")}>{r.ats}</td>
                      <td className={cn(TD, "text-right tabular-nums")}>{r.done}</td>
                      <td
                        className={cn(
                          TD,
                          "text-right tabular-nums",
                          r.failed > 0 && "text-danger font-medium",
                        )}
                      >
                        {r.failed}
                      </td>
                      <td className={cn(TD, "text-right tabular-nums")}>
                        {r.mean_seconds === null ? "-" : r.mean_seconds.toFixed(1)}
                      </td>
                      <td className={cn(TD, "text-right tabular-nums")}>{r.new_jobs}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card as="section" padding="lg" className="mt-4" aria-labelledby="systems">
          <h2 id="systems" className="text-title text-ink">
            Boards by Hiring System
          </h2>
          <div className="mt-3 overflow-x-auto">
            <table className="text-body w-full border-collapse text-left">
              <thead>
                <tr className="border-border-subtle border-b">
                  <th className={TH}>Hiring System</th>
                  <th className={cn(TH, "text-right")}>Boards</th>
                  <th className={cn(TH, "text-right")}>Ever Read</th>
                  <th className={cn(TH, "w-1/4")}>Share Read</th>
                  <th className={TH}>Newest Read (UTC)</th>
                </tr>
              </thead>
              <tbody>
                {data.systems.map((s) => (
                  <tr
                    key={s.ats}
                    className="border-border-subtle text-ink hover:bg-hover border-b last:border-b-0"
                  >
                    <td className={cn(TD, "font-medium capitalize")}>{s.ats}</td>
                    <td className={cn(TD, "text-right tabular-nums")}>{s.boards}</td>
                    <td className={cn(TD, "text-right tabular-nums")}>{s.read}</td>
                    <td className={TD}>
                      <div
                        className="bg-brand-tint h-1.5 overflow-hidden rounded-full"
                        role="img"
                        aria-label={`${s.read} of ${s.boards} boards read`}
                      >
                        <div
                          className="bg-brand h-full rounded-full"
                          style={{ width: `${(s.read / s.boards) * 100}%` }}
                        />
                      </div>
                    </td>
                    <td className={cn(TD, "whitespace-nowrap", !s.last_read_at && "text-ink-meta")}>
                      {when(s.last_read_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </main>
      <ScrapeRail data={data} days={days} />
    </div>
  );
}
