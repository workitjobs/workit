import {
  BracketsCurlyIcon,
  CheckCircleIcon,
  ClockIcon,
  CloudSlashIcon,
  FileXIcon,
  HourglassMediumIcon,
  MinusCircleIcon,
  QuestionIcon,
  TextStrikethroughIcon,
  WarningCircleIcon,
  WarningIcon,
} from "@phosphor-icons/react/ssr";
import type { ComponentType } from "react";

import { cn } from "@/lib/cn";
import {
  dollars,
  type ReadingHealth,
  readingTotals,
  reasonOf,
  scoredOn,
  share,
  type Status,
} from "@/lib/resume-reading";

import { dayLabel } from "@/lib/scrape-status";

import { DayColumns, type Series } from "../day-columns";
import { count } from "../format";
import { FIRST_SECTION_TARGET, READING_SECTIONS } from "../pages";
import { Panel, TD, TH } from "../panel";

/**
 * The Resume Reading page's cards (KAN-953). The layout is the outcome of a
 * design review of the first build, which stood every number in an equal
 * white box (frontend/CLAUDE.md, Admin pages, has the rules it left):
 *
 * - The first row stands on the page with no box, and one number leads.
 * - No fact shows twice.
 * - A reason is a glyph, a count and a bar for its share, never a pill.
 * - Red is a model's failure; grey is by design (the daily limit, a file
 *   with no text).
 */

type Glyph = ComponentType<{
  size?: number;
  className?: string;
  weight?: "fill" | "regular";
  "aria-hidden"?: boolean;
}>;

/** Each level's glyph and chip. The glyph and the title say the level, so it is never colour alone. */
const LEVELS: Record<Status["level"], { Icon: Glyph; chip: string }> = {
  red: { Icon: WarningIcon, chip: "bg-danger-tint text-danger" },
  amber: { Icon: WarningCircleIcon, chip: "bg-warning-tint text-warning" },
  green: { Icon: CheckCircleIcon, chip: "bg-positive-tint text-positive-ink" },
  none: { Icon: MinusCircleIcon, chip: "bg-well text-ink-meta" },
};

/**
 * One number of the first row: its label over the figure, a rule at its left
 * from the second on. The lead is `text-hero` (40px) and the rest
 * `text-heading` (26px): at 40px beside 36px the four read as equal, so the
 * lead did not lead. Each is a subgrid over the row's two tracks, labels in
 * one and figures in the other, and the figures sit on one baseline, which
 * two sizes side by side need.
 */
function Figure({
  label,
  value,
  unit,
  lead = false,
}: {
  label: string;
  value: string;
  /** Body text beside the figure: "of 100", "s". */
  unit?: string;
  lead?: boolean;
}) {
  return (
    <div className="@3xl/main:border-border-surface row-span-2 grid grid-rows-subgrid gap-y-1 @3xl/main:border-l @3xl/main:pl-8 @3xl/main:first:border-l-0 @3xl/main:first:pl-0">
      <dt className="text-label text-ink-meta">{label}</dt>
      <dd className="flex items-baseline gap-1.5 self-baseline">
        <span
          className={cn("text-ink font-medium tabular-nums", lead ? "text-hero" : "text-heading")}
        >
          {value}
        </span>
        {unit && <span className="text-body text-ink-muted">{unit}</span>}
      </dd>
    </div>
  );
}

/**
 * The page's answer and its four numbers, on the page's ground with no box:
 * the share AI read leads, since it is what the page is opened for.
 */
export function Now({ status, health }: { status: Status; health: ReadingHealth }) {
  const { ai, all } = readingTotals(health.days);
  const { Icon, chip } = LEVELS[status.level];
  return (
    <section
      id={READING_SECTIONS.status.id}
      aria-labelledby="reading-status"
      className={FIRST_SECTION_TARGET}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-full", chip)}>
          <Icon size={18} weight="fill" aria-hidden />
        </span>
        <h2 id="reading-status" className="text-title text-ink">
          {status.title}
        </h2>
        <p className="text-body text-ink-muted">{status.reason}</p>
      </div>
      <dl className="mt-6 grid grid-cols-2 gap-x-8 gap-y-6 @3xl/main:grid-cols-4">
        <Figure lead label="Read by AI" value={share(ai, all)} />
        <Figure label="Readings" value={count(all)} />
        <Figure
          label="AI Readings Today"
          value={count(health.today.used)}
          unit={`of ${count(health.today.cap)}`}
        />
        <Figure
          label="Median AI Reading Time"
          value={health.median_seconds === null ? "–" : health.median_seconds.toFixed(1)}
          unit={health.median_seconds === null ? undefined : "s"}
        />
      </dl>
    </section>
  );
}

/** AI in brand under the rule-based parser in amber: a weaker reading, not a failure, so not red. */
const SERIES: readonly Series[] = [
  { label: "AI Reading", swatch: "bg-brand" },
  { label: "Rule-Based Parser", swatch: "bg-warning-fill" },
];

/** Readings per day (UTC) by reader, on the admin pages' shared chart. */
export function PerDay({
  days,
  dates,
  className,
}: {
  days: ReadingHealth["days"];
  /** The window's days, YYYY-MM-DD, oldest first. */
  dates: string[];
  className?: string;
}) {
  const { ai, parser } = readingTotals(days);
  return (
    <DayColumns
      section={READING_SECTIONS.perDay}
      dates={dates}
      series={SERIES}
      values={new Map(days.map((d) => [d.day, [d.ai, d.parser]]))}
      says={([a, p]) => `${count(a)} by AI, ${count(p)} by the rule-based parser`}
      caption={`${count(ai)} resumes read by AI and ${count(parser)} by the rule-based parser`}
      plotClassName="min-h-40"
      className={className}
    />
  );
}

/** One glyph per reason, so the list scans by shape. */
const REASON_ICON: Record<string, Glyph> = {
  no_uses_left: HourglassMediumIcon,
  model_unavailable: CloudSlashIcon,
  timeout: ClockIcon,
  wrong_shape: BracketsCurlyIcon,
  nothing_backed: TextStrikethroughIcon,
  no_text: FileXIcon,
};

/** Why AI did not read, most first: a glyph, the reason, its count and a bar for its share of the largest. */
export function Reasons({
  reasons,
  className,
}: {
  reasons: ReadingHealth["reasons"];
  className?: string;
}) {
  const most = Math.max(...reasons.map((r) => r.readings), 1);
  return (
    <Panel section={READING_SECTIONS.reasons} className={className} bodyClassName="px-5 py-2">
      {reasons.length === 0 ? (
        <p className="text-body text-ink-muted py-3">
          The rule-based parser read no resume alone in this period.
        </p>
      ) : (
        <ul>
          {reasons.map((r) => {
            const { label, fault } = reasonOf(r.reason);
            const Icon = REASON_ICON[r.reason] ?? QuestionIcon;
            return (
              <li key={r.reason} className="border-border-subtle border-b py-2.5 last:border-b-0">
                <div className="flex items-center gap-3">
                  <Icon
                    size={18}
                    aria-hidden
                    className={cn("shrink-0", fault ? "text-danger" : "text-ink-meta")}
                  />
                  <p className="text-body text-ink min-w-0 flex-1 font-medium">{label}</p>
                  <p className="text-body text-ink tabular-nums">{count(r.readings)}</p>
                </div>
                {/* Starts under the label: the glyph's 18px and the row's 12px gap. */}
                <span className="bg-well mt-1.5 ml-[30px] block h-1 overflow-hidden rounded-full">
                  <span
                    // A by-design reason is a lighter grey than a failure's red, so the failures lead.
                    className={cn(
                      "block h-full rounded-full",
                      fault ? "bg-danger" : "bg-ink-subtle",
                    )}
                    style={{ width: `${(r.readings / most) * 100}%` }}
                  />
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}

/**
 * The newest recorded scoring run as numbers: the saved reading's score
 * leads, the two readers alone under it. Bars were tried first and said
 * little: 97%, 93% and 72% all drew a bar that looked nearly full.
 */
export function Accuracy({
  run,
  className,
}: {
  run: ReadingHealth["accuracy"];
  className?: string;
}) {
  return (
    <Panel
      section={READING_SECTIONS.accuracy}
      className={className}
      action={run && <span className="text-note text-ink-meta">Scored {dayLabel(run.ran)}</span>}
    >
      {run === null ? (
        <p className="text-body text-ink-muted">No scoring run is recorded yet.</p>
      ) : (
        <>
          <p className="text-label text-ink-meta">Combined Reading (Saved)</p>
          <p className="text-hero text-ink mt-1 font-medium tabular-nums">
            {run.combined.toFixed(1)}%
          </p>
          <dl className="border-border-subtle mt-5 border-t">
            {[
              { label: "AI Reading Alone", score: run.ai },
              { label: "Rule-Based Parser Alone", score: run.parser },
            ].map((r) => (
              <div
                key={r.label}
                className="border-border-subtle flex items-baseline justify-between gap-3 border-b py-3"
              >
                <dt className="text-body text-ink-muted">{r.label}</dt>
                <dd className="text-subtitle text-ink tabular-nums">{r.score.toFixed(1)}%</dd>
              </div>
            ))}
          </dl>
          <p className="text-note text-ink-meta mt-3">
            Fields right on {scoredOn(run)}, read with {run.model}.
          </p>
        </>
      )}
    </Panel>
  );
}

/** Each model that replied: its readings and share, its median time, its tokens a reading and their paid cost. */
export function Models({
  models,
  className,
}: {
  models: ReadingHealth["models"];
  className?: string;
}) {
  const all = models.reduce((sum, m) => sum + m.readings, 0);
  const head = cn(TH, "text-right font-normal whitespace-nowrap");
  const cell = cn(TD, "text-right tabular-nums");
  return (
    <Panel section={READING_SECTIONS.models} className={className} bodyClassName="p-0">
      {models.length === 0 ? (
        <p className="text-body text-ink-muted p-5">No model replied in this period.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="text-body w-full border-collapse text-left">
              <thead>
                <tr className="border-border-subtle border-b">
                  <th className={cn(TH, "font-normal")}>Model</th>
                  <th className={head}>Readings</th>
                  <th className={head}>Share</th>
                  <th className={head}>Median Time</th>
                  <th className={head}>Tokens / Reading</th>
                  <th className={head}>Paid Cost</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr
                    key={m.model ?? ""}
                    className="border-border-subtle text-ink border-b last:border-b-0"
                  >
                    <td className={cn(TD, "font-medium whitespace-nowrap")}>
                      {m.model ?? <span className="text-ink-muted font-normal">Not Recorded</span>}
                    </td>
                    <td className={cell}>{count(m.readings)}</td>
                    <td className={cell}>{share(m.readings, all)}</td>
                    <td className={cell}>
                      {m.median_seconds === null ? "–" : `${m.median_seconds.toFixed(1)} s`}
                    </td>
                    <td className={cell}>
                      {m.model === null
                        ? "–"
                        : count(Math.round((m.input_tokens + m.output_tokens) / m.readings))}
                    </td>
                    <td className={cell}>{m.cost === null ? "–" : dollars(m.cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {models.some((m) => m.model !== null && m.cost === null) && (
            <p className="text-note text-ink-meta border-border-subtle border-t px-5 py-3">
              A model with no paid cost has no price set in MODEL_PRICES.
            </p>
          )}
        </>
      )}
    </Panel>
  );
}
