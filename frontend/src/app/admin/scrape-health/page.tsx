import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { daysOf } from "@/lib/fill-health";
import { getScrapeHealth } from "@/lib/fill-report-queries";

export const metadata: Metadata = { title: "Scrape Health" };

const when = (iso: string | null) =>
  iso ? new Date(iso).toISOString().slice(0, 16).replace("T", " ") : "Never";

/**
 * The scraper's health (KAN-879), the admins' page: enabled boards and how
 * many are failing, resting or stale; per day (UTC) per hiring system, the
 * board reads done and failed, their mean time and the new jobs; and the
 * failing boards with their last error. Only WorkIt's admins (the API's
 * WORKIT_ADMINS) see it; anyone else gets the 404, as /admin/fill-health.
 */
export default async function ScrapeHealthPage({
  searchParams,
}: PageProps<"/admin/scrape-health">) {
  const params = await searchParams;
  const days = daysOf(params.days);
  const { data, status } = await getScrapeHealth(days);
  if (status === 401) redirect("/login");
  if (!data) notFound();
  const tiles = [
    ["Boards", data.boards.boards],
    ["Failing", data.boards.failing],
    ["Resting", data.boards.resting],
    ["Stale", data.boards.stale],
    ["Open Jobs", data.boards.open_jobs],
    ["Tasks Pending", data.boards.pending],
    ["Tasks Claimed", data.boards.claimed],
  ] as const;

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8">
      <h1 className="text-title text-ink">Scrape Health</h1>
      <p className="text-body text-ink-muted mt-1">
        How the scheduled scrape is doing. Stale means unread for 2 days or never read. Read at{" "}
        {when(data.read_at)} UTC; the numbers are kept for 10 minutes.
      </p>
      <p className="text-body text-ink mt-3">
        The scheduled scrape last imported jobs at {when(data.last_import_at)} UTC. The worker below
        is not scheduled yet.
      </p>
      <dl className="mt-4 flex flex-wrap gap-3">
        {tiles.map(([label, value]) => (
          <div key={label} className="border-border-subtle rounded-control border px-4 py-2">
            <dt className="text-body text-ink-muted">{label}</dt>
            <dd className="text-title text-ink tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>

      {data.boards.oldest_pending_at && (
        <p className="text-body text-ink-muted mt-3">
          The oldest pending task was made {when(data.boards.oldest_pending_at)} UTC. A worker that
          stopped leaves its tasks pending.
        </p>
      )}

      <h2 className="text-body text-ink mt-8 font-semibold">Boards by Hiring System</h2>
      <table className="text-body mt-2 w-full border-collapse text-left">
        <thead>
          <tr className="text-ink-muted border-border-subtle border-b">
            <th className="py-2 pr-3">Hiring System</th>
            <th className="py-2 pr-3 text-right">Boards</th>
            <th className="py-2 pr-3 text-right">Ever Read</th>
            <th className="py-2 pr-3">Newest Read (UTC)</th>
          </tr>
        </thead>
        <tbody>
          {data.systems.map((s) => (
            <tr key={s.ats} className="border-border-subtle text-ink border-b">
              <td className="py-2 pr-3">{s.ats}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{s.boards}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{s.read}</td>
              <td className="py-2 pr-3 whitespace-nowrap">{when(s.last_read_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="text-body text-ink mt-8 font-semibold">Board Reads</h2>
      <form className="mt-2 flex flex-wrap items-end gap-3" action="/admin/scrape-health">
        <label className="text-body text-ink flex flex-col gap-1">
          Days
          <select
            name="days"
            defaultValue={String(days)}
            className="border-border-subtle rounded-control border px-2 py-1"
          >
            {[1, 7, 14, 30, 90].map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="bg-brand text-on-brand rounded-control text-body px-3 py-1.5"
        >
          Filter
        </button>
      </form>
      {data.days.length === 0 ? (
        <p className="text-body text-ink-muted mt-4">No board reads in this period.</p>
      ) : (
        <table className="text-body mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="text-ink-muted border-border-subtle border-b">
              <th className="py-2 pr-3">Day</th>
              <th className="py-2 pr-3">Hiring System</th>
              <th className="py-2 pr-3 text-right">Done</th>
              <th className="py-2 pr-3 text-right">Failed</th>
              <th className="py-2 pr-3 text-right">Mean Seconds</th>
              <th className="py-2 pr-3 text-right">New Jobs</th>
            </tr>
          </thead>
          <tbody>
            {data.days.map((r) => (
              <tr key={`${r.day}:${r.ats}`} className="border-border-subtle text-ink border-b">
                <td className="py-2 pr-3 whitespace-nowrap">{r.day}</td>
                <td className="py-2 pr-3">{r.ats}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{r.done}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{r.failed}</td>
                <td className="py-2 pr-3 text-right tabular-nums">
                  {r.mean_seconds === null ? "-" : r.mean_seconds.toFixed(1)}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">{r.new_jobs}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 className="text-body text-ink mt-8 font-semibold">Failing Boards</h2>
      {data.failing.length === 0 ? (
        <p className="text-body text-ink-muted mt-2">No board is failing.</p>
      ) : (
        <table className="text-body mt-2 w-full border-collapse text-left">
          <thead>
            <tr className="text-ink-muted border-border-subtle border-b">
              <th className="py-2 pr-3">Company</th>
              <th className="py-2 pr-3">Board</th>
              <th className="py-2 pr-3 text-right">Failures</th>
              <th className="py-2 pr-3">Last Good Read (UTC)</th>
              <th className="py-2 pr-3">Resting Until (UTC)</th>
              <th className="py-2 pr-3">Last Error</th>
            </tr>
          </thead>
          <tbody>
            {data.failing.map((b) => (
              <tr
                key={`${b.ats}:${b.token}`}
                className="border-border-subtle text-ink border-b align-top"
              >
                <td className="py-2 pr-3">{b.company}</td>
                <td className="py-2 pr-3">
                  {b.ats}:{b.token}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">{b.consecutive_failures}</td>
                <td className="py-2 pr-3 whitespace-nowrap">{when(b.last_read_at)}</td>
                <td className="py-2 pr-3 whitespace-nowrap">
                  {b.rest_until ? when(b.rest_until) : "-"}
                </td>
                <td className="min-w-48 py-2 pr-3 break-words">{b.last_error ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
