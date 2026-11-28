import type { Metadata } from "next";

import { cn } from "@/lib/cn";
import { versionOf } from "@/lib/fill-health";
import { getFillHealth } from "@/lib/fill-report-queries";
import { datesOf, HISTORY, windowOf } from "@/lib/scrape-status";

import { ADMIN_FRAME } from "../panel";
import { refuse } from "../refuse";
import { WindowControls } from "../scrape-health/window-controls";
import { FillsTable } from "./fills-table";
import { FillMetrics } from "./metrics";

export const metadata: Metadata = { title: "Fill Health" };

/**
 * Fill numbers (KAN-476), the admins' page: how the extension's fills went.
 * Metrics counts the window's fills, all of them and per job system. Fills
 * is the table per job system per day (UTC): fills, the share with no
 * failed field, the share of fields left needing the student, and the top
 * error names. A job system that breaks shows as its No Failed Field share
 * dropping. Only WorkIt's admins (the API's WORKIT_ADMINS) see it; anyone
 * else gets the 404, as /admin/fill-reports.
 *
 * It moves through time as Scrape Health does (KAN-879): the page reads all
 * `HISTORY` days once and cuts them to the window in the address, so the
 * periods are links that ask the API nothing new. The engine
 * version is the one filter the API applies, so the address holds it and
 * every window link keeps it.
 */
export default async function FillHealthPage({ searchParams }: PageProps<"/admin/fill-health">) {
  const params = await searchParams;
  const window = windowOf(params);
  const version = versionOf(params.engine_version) ?? "";
  const query = new URLSearchParams({ days: String(HISTORY) });
  if (version) query.set("engine_version", version);
  const { data, status } = await getFillHealth(`?${query}`);
  if (!data) refuse(status);

  // The API has no read time, so the newest day is today (UTC).
  const today = new Date().toISOString().slice(0, 10);
  const dates = datesOf(window, today);
  const rows = data.rows.filter((r) => r.day >= dates[0] && r.day <= dates[dates.length - 1]);

  return (
    <main className={cn("@container/main", ADMIN_FRAME)}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-heading text-ink">Fill Health</h1>
          <p className="text-note text-ink-meta mt-1">
            How the extension&apos;s fills went. Counts only, never answers.
          </p>
        </div>
        <WindowControls
          window={window}
          path="/admin/fill-health"
          keep={{ engine_version: version }}
        />
      </div>

      <div className="mt-6 flex flex-col gap-4">
        <FillMetrics rows={rows} />
        <FillsTable rows={rows} versions={data.engine_versions} version={version} window={window} />
      </div>
    </main>
  );
}
