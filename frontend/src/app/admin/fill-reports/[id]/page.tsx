import { ArrowLeftIcon } from "@phosphor-icons/react/ssr";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { triageFillReport } from "@/lib/fill-report-actions";
import { getFillBrief, getFillReport } from "@/lib/fill-report-queries";
import { STATUSES } from "@/lib/fill-reports";
import { systemName } from "@/lib/scrape-status";

import { ADMIN_FRAME, Panel, TD, TH } from "../../panel";
import { FIELD, FIELD_LABEL, StatusPill, when } from "../parts";
import { CopyBrief } from "./copy-brief";

export const metadata: Metadata = { title: "Fill Report" };

const FIELD_COLUMNS = [
  "Field",
  "Name",
  "Kind",
  "Selector",
  "Source",
  "Planned",
  "Status",
  "Read-Back",
  "Marked",
];

/** One fact about the report: its name over its value. */
function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-note text-ink-meta">{label}</dt>
      <dd className="text-body text-ink font-medium [overflow-wrap:anywhere]">{value}</dd>
    </div>
  );
}

/**
 * One fix report (KAN-369), for an admin: its summary, its triage (status
 * and note), the fields, and the fix brief (copy it, or download it with
 * the form's fixture for a coding agent). 404 for anyone the API doesn't
 * count as an admin. The fixture is a download, never rendered here: it is
 * an employer page's markup.
 *
 * Built from the admin pages' parts (KAN-879): the summary and the triage
 * in a card each, then Fields and Fix Brief as a `Panel` each. The triage
 * stays a native form on a server action, so it saves with no script.
 */
export default async function FillReportPage({ params }: PageProps<"/admin/fill-reports/[id]">) {
  const { id } = await params;
  const [report, brief] = await Promise.all([getFillReport(id), getFillBrief(id)]);
  if (report.status === 401) redirect("/login");
  if (!report.data) notFound();
  const r = report.data;

  return (
    <main className={cn("@container/main", ADMIN_FRAME)}>
      <Link
        href="/admin/fill-reports"
        className="text-label text-ink-muted hover:text-ink inline-flex items-center gap-1.5"
      >
        <ArrowLeftIcon size={16} aria-hidden />
        All Fill Reports
      </Link>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <h1 className="text-heading text-ink">
          Fill Report {r.id.slice(0, 8)}: {systemName(r.job_system)}
        </h1>
        <StatusPill status={r.status} />
      </div>

      <div className="mt-6 flex flex-col gap-4">
        <Card as="section" tone="tile" padding="lg" aria-label="Summary">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 @3xl/main:grid-cols-4">
            <Fact label="Sent (UTC)" value={when(r.created_at)} />
            <Fact label="Engine Version" value={r.engine_version} />
            <Fact label="Browser" value={r.context?.browser ?? "Unknown"} />
            <Fact label="Opened By" value={r.trigger ?? "Unknown"} />
            <div className="col-span-full min-w-0">
              <dt className="text-note text-ink-meta">Job Posting</dt>
              <dd className="text-body text-ink [overflow-wrap:anywhere]">{r.posting_url}</dd>
            </div>
            {r.note && (
              <div className="col-span-full min-w-0">
                <dt className="text-note text-ink-meta">The Student&apos;s Note</dt>
                <dd className="text-body text-ink [overflow-wrap:anywhere]">{r.note}</dd>
              </div>
            )}
          </dl>
          <div className="border-border-subtle mt-5 flex flex-wrap items-center gap-3 border-t pt-4">
            {brief.data && <CopyBrief brief={brief.data} />}
            <a
              href={`/admin/fill-reports/${r.id}/brief`}
              className={buttonClasses({ variant: "secondary", size: "sm" })}
            >
              Download Fix Brief
            </a>
            {r.html && (
              <a
                href={`/admin/fill-reports/${r.id}/fixture`}
                className={buttonClasses({ variant: "secondary", size: "sm" })}
              >
                Download Form Fixture
              </a>
            )}
          </div>
        </Card>

        <Panel section={{ id: "triage", label: "Triage" }}>
          <form action={triageFillReport} className="flex flex-wrap items-end gap-4">
            <input type="hidden" name="id" value={r.id} />
            <label className={FIELD_LABEL}>
              Status
              <select name="status" defaultValue={r.status} className={cn(FIELD, "w-36")}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s[0].toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </label>
            <label className={cn(FIELD_LABEL, "min-w-64 flex-1")}>
              Admin Note
              <input name="admin_note" defaultValue={r.admin_note ?? ""} className={FIELD} />
            </label>
            <button type="submit" className={buttonClasses({ size: "sm" })}>
              Save
            </button>
          </form>
        </Panel>

        <Panel
          section={{ id: "fields", label: "Fields" }}
          bodyClassName="p-0"
          action={
            <span className="text-note text-ink-meta tabular-nums">
              {r.fields.length} {r.fields.length === 1 ? "field" : "fields"}
            </span>
          }
        >
          {r.fields.length === 0 ? (
            <p className="text-body text-ink-muted p-5">This report holds no fields.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="text-body w-full border-collapse text-left">
                <thead>
                  <tr className="border-border-subtle border-b">
                    {FIELD_COLUMNS.map((h) => (
                      <th key={h} className={cn(TH, "font-normal whitespace-nowrap")}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {r.fields.map((f, n) => (
                    <tr
                      key={`${f.name ?? f.label_shape}-${n}`}
                      className={cn(
                        "border-border-subtle text-ink border-b align-top last:border-b-0",
                        f.marked && "bg-danger-tint",
                      )}
                    >
                      <td className={cn(TD, "font-medium")}>{f.label ?? f.label_shape}</td>
                      <td className={cn(TD, "text-note font-mono")}>{f.name ?? ""}</td>
                      <td className={TD}>{f.kind}</td>
                      <td className={cn(TD, "text-note font-mono [overflow-wrap:anywhere]")}>
                        {f.selector ?? ""}
                      </td>
                      <td className={TD}>{f.source ?? ""}</td>
                      <td className={TD}>{f.planned ?? ""}</td>
                      <td className={TD}>{f.status ?? f.error ?? ""}</td>
                      <td className={TD}>{f.readback ?? ""}</td>
                      <td className={cn(TD, f.marked && "text-danger font-medium")}>
                        {f.marked ? "Wrong" : f.edited ? "Edited" : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel section={{ id: "fix-brief", label: "Fix Brief" }}>
          <pre className="bg-well rounded-control text-ink text-note max-h-[60vh] overflow-auto p-4 font-mono whitespace-pre-wrap">
            {brief.data ?? "The brief couldn't be loaded."}
          </pre>
        </Panel>
      </div>
    </main>
  );
}
