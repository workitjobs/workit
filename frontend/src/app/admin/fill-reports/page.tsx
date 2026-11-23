import type { Metadata } from "next";
import Link from "next/link";

import { buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { listFillReportGroups, listFillReports } from "@/lib/fill-report-queries";
import {
  groupsQuery,
  PAGE_SIZE,
  reportsQuery,
  signatureOf,
  STATUSES,
  statusOf,
} from "@/lib/fill-reports";
import { systemName } from "@/lib/scrape-status";

import { count, when } from "../format";
import { FIRST_SECTION_TARGET, REPORT_SECTIONS } from "../pages";
import { ADMIN_FRAME, Panel, TD, TH } from "../panel";
import { refuse } from "../refuse";
import { FIELD, FIELD_LABEL, StatusPill } from "./parts";

export const metadata: Metadata = { title: "Fill Reports" };

const LINK = "text-brand-ink font-medium underline-offset-2 hover:underline";

/**
 * Fix reports (KAN-369), the admins' list: the reports students sent from
 * the extension's panel, newest first, filtered by job system, status and
 * engine version, under their groups (KAN-478: one line per job system +
 * field kind + error, with a count; a group's link lists its reports).
 * Only WorkIt's admins (the API's WORKIT_ADMINS) see it; anyone else gets
 * the 404, so the page doesn't say it exists.
 *
 * It is built from the admin pages' parts (KAN-879): the filters in a card,
 * then Groups and Reports as a `Panel` each, with a status as a pill. The
 * filters stay a native GET form, so the address holds them and the page
 * needs no script. It was a bare heading, a form and two unstyled tables.
 */
export default async function FillReportsPage({ searchParams }: PageProps<"/admin/fill-reports">) {
  const params = await searchParams;
  const [{ data, status }, grouped] = await Promise.all([
    listFillReports(reportsQuery(params)),
    listFillReportGroups(groupsQuery(params)),
  ]);
  if (!data) refuse(status);
  const system = typeof params.job_system === "string" ? params.job_system : "";
  const engine = typeof params.engine_version === "string" ? params.engine_version : "";
  const signature = signatureOf(params.signature);
  const chosen = statusOf(params.status);
  const page = Math.max(1, Number.parseInt(String(params.page ?? "1"), 10) || 1);
  const filtered = Boolean(system || engine || chosen || signature);
  const link = (changes: Record<string, string | null>) => {
    const query = new URLSearchParams();
    const next = {
      job_system: system || null,
      status: chosen,
      engine_version: engine || null,
      signature,
      page: null,
      ...changes,
    };
    for (const [key, value] of Object.entries(next)) if (value) query.set(key, value);
    return `/admin/fill-reports${query.size ? `?${query}` : ""}`;
  };
  const groups = grouped.data?.groups ?? [];
  const older = page * PAGE_SIZE < data.total;

  return (
    <main className={cn("@container/main", ADMIN_FRAME)}>
      <h1 className="text-heading text-ink">Fill Reports</h1>
      <p className="text-note text-ink-meta mt-1">
        Problems students reported from the extension. Open one for its fix brief.
      </p>

      <div className="mt-6 flex flex-col gap-4">
        <Card as="section" tone="tile" padding="none" aria-label="Filters">
          <form className="flex flex-wrap items-end gap-4 px-5 py-4" action="/admin/fill-reports">
            <label className={FIELD_LABEL}>
              Job System
              <input
                name="job_system"
                defaultValue={system}
                placeholder="greenhouse"
                className={cn(FIELD, "w-44")}
              />
            </label>
            <label className={FIELD_LABEL}>
              Status
              <select name="status" defaultValue={chosen ?? ""} className={cn(FIELD, "w-36")}>
                <option value="">All</option>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s[0].toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </label>
            <label className={FIELD_LABEL}>
              Engine Version
              <input
                name="engine_version"
                defaultValue={engine}
                placeholder="0.3.2"
                className={cn(FIELD, "w-44")}
              />
            </label>
            <button type="submit" className={buttonClasses({ size: "sm" })}>
              Filter
            </button>
            {filtered && (
              <Link
                href="/admin/fill-reports"
                className={buttonClasses({ variant: "secondary", size: "sm" })}
              >
                Clear Filters
              </Link>
            )}
          </form>
        </Card>

        {/* Each section has its id from ../pages.ts, the sidebar's link to it. Groups always
            draws, so that link has a target when no group matches. */}
        <Panel
          section={REPORT_SECTIONS.groups}
          bodyClassName="p-0"
          className={FIRST_SECTION_TARGET}
          action={
            groups.length > 0 && (
              <span className="text-note text-ink-meta">
                {count(groups.length)} {groups.length === 1 ? "group" : "groups"}
              </span>
            )
          }
        >
          {groups.length === 0 ? (
            <p className="text-body text-ink-muted p-5">
              {!grouped.data
                ? "The groups couldn't be loaded. The reports below are not affected."
                : filtered
                  ? "No groups for these filters."
                  : "No reports yet. A group shows here when students report the same problem: one job system, field kind and error."}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="text-body w-full border-collapse text-left">
                <thead>
                  <tr className="border-border-subtle border-b">
                    <th className={cn(TH, "font-normal")}>Job System</th>
                    <th className={cn(TH, "font-normal")}>Field Kind</th>
                    <th className={cn(TH, "font-normal")}>Error</th>
                    <th className={cn(TH, "text-right font-normal")}>Reports</th>
                    <th className={cn(TH, "font-normal")}>Last Sent (UTC)</th>
                    <th className={cn(TH, "font-normal")}>Engine Versions</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((g) => {
                    const picked = g.signature === signature;
                    return (
                      <tr
                        key={g.signature}
                        aria-current={picked ? "true" : undefined}
                        className={cn(
                          "border-border-subtle text-ink border-b align-top last:border-b-0",
                          picked && "bg-brand-tint",
                        )}
                      >
                        <td className={cn(TD, "font-medium")}>{systemName(g.job_system)}</td>
                        <td className={TD}>
                          {g.field_kind ?? <span className="text-ink-meta">No Field</span>}
                        </td>
                        <td className={TD}>
                          {g.error ? (
                            <span className="bg-danger-tint text-danger text-note rounded-full px-2 py-0.5">
                              {g.error}
                            </span>
                          ) : (
                            <span className="text-ink-meta">Marked Only</span>
                          )}
                        </td>
                        <td className={cn(TD, "text-right tabular-nums")}>
                          <Link href={link({ signature: g.signature })} className={LINK}>
                            {count(g.count)}
                          </Link>
                        </td>
                        <td className={cn(TD, "whitespace-nowrap tabular-nums")}>
                          {when(g.last_at)}
                        </td>
                        <td className={cn(TD, "text-ink-muted")}>{g.engine_versions.join(", ")}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel
          section={REPORT_SECTIONS.reports}
          bodyClassName="p-0"
          action={
            <span className="text-note text-ink-meta">
              {count(data.total)} {data.total === 1 ? "report" : "reports"}
              {signature && (
                <>
                  {" "}
                  in {signature} ·{" "}
                  <Link href={link({ signature: null })} className={LINK}>
                    All Groups
                  </Link>
                </>
              )}
            </span>
          }
        >
          {data.reports.length === 0 ? (
            <p className="text-body text-ink-muted p-5">
              {filtered
                ? "No reports match these filters."
                : "No reports yet. A student sends one from the extension's panel after a fill goes wrong."}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="text-body w-full border-collapse text-left">
                <thead>
                  <tr className="border-border-subtle border-b">
                    <th className={cn(TH, "font-normal")}>Sent (UTC)</th>
                    <th className={cn(TH, "font-normal")}>Job System</th>
                    <th className={cn(TH, "font-normal")}>Status</th>
                    <th className={cn(TH, "font-normal")}>Opened By</th>
                    <th className={cn(TH, "font-normal")}>Marked Wrong</th>
                    <th className={cn(TH, "font-normal")}>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {data.reports.map((r) => (
                    <tr
                      key={r.id}
                      className="border-border-subtle text-ink border-b align-top last:border-b-0"
                    >
                      <td className={cn(TD, "whitespace-nowrap tabular-nums")}>
                        <Link href={`/admin/fill-reports/${r.id}`} className={LINK}>
                          {when(r.created_at)}
                        </Link>
                      </td>
                      <td className={TD}>
                        <Link href={link({ job_system: r.job_system })} className={LINK}>
                          {systemName(r.job_system)}
                        </Link>
                      </td>
                      <td className={TD}>
                        <StatusPill status={r.status} />
                      </td>
                      <td className={cn(TD, "text-ink-muted")}>{r.trigger ?? ""}</td>
                      <td className={TD}>{r.marked.join(", ")}</td>
                      <td className={cn(TD, "text-ink-muted max-w-md [overflow-wrap:anywhere]")}>
                        {r.note ?? ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {(page > 1 || older) && (
            <nav
              aria-label="Report Pages"
              className="border-border-subtle flex items-center justify-between gap-3 border-t px-5 py-3"
            >
              <span className="text-note text-ink-meta tabular-nums">Page {page}</span>
              <span className="flex gap-2">
                {page > 1 && (
                  <Link
                    href={link({ page: String(page - 1) })}
                    className={buttonClasses({ variant: "secondary", size: "sm" })}
                  >
                    Newer
                  </Link>
                )}
                {older && (
                  <Link
                    href={link({ page: String(page + 1) })}
                    className={buttonClasses({ variant: "secondary", size: "sm" })}
                  >
                    Older
                  </Link>
                )}
              </span>
            </nav>
          )}
        </Panel>
      </div>
    </main>
  );
}
