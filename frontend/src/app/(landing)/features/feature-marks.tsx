/**
 * The features' own marks (KAN-923): each a small piece of the real screen
 * on a squircle in the feature's colour, after Calendly's product icons,
 * which the user pointed to over the generic glyphs on solid tiles. The
 * user picked each from three rounds of sketches:
 *
 * - Resume Builder: a resume page, its last line the tailored one.
 * - Job Matching: the app's match ring, its arc at 91% in the match's
 *   green, with a check inside (the user's pick, 2026-11-20). A card with
 *   the score over two ticked skills came before, which held too much to
 *   read as matching; before that a job card with a ring badge, which the
 *   user found off. 91% is the followed Stripe application's match
 *   (`followedJob`), the number the hero's Stripe tile shows.
 * - Auto Apply: a grid of four forms, three filled and checked and the
 *   last still filling: several applications at once (the user's pick,
 *   2026-11-20). A stack of forms with one check came before; its faint
 *   back forms did not read as several.
 * - Application Tracker: a table, a header row over columns and a status
 *   column of stage pills (applied, interview, offer), the spreadsheet the
 *   tracker is. A list of rows with stage pills came before; the user
 *   found it off.
 *
 * Drawn on a 48 grid, one colour family each, from the feature's own token
 * (a light mix for the ground, a deep mix for text-like bars), so a token
 * change moves the mark. Server components with no script; `FeatureIcon`
 * draws them, and they are decorative (the feature's name is always beside
 * them).
 */
import type { ComponentType, ReactNode } from "react";

type MarkProps = { className?: string };

/** A squircle: a square with continuous curves, Calendly's tile shape,
 *  softer than a rounded square at the same size. */
const SQUIRCLE = "M24 0C40 0 48 8 48 24S40 48 24 48 0 40 0 24 8 0 24 0Z";

const BLUE = "var(--color-advanced)";
const VIOLET = "var(--color-brand)";
const PEACH = "var(--color-matching)";
const GREEN = "var(--color-positive)";
const PINK = "var(--color-updates)";
const MATCH = "var(--color-match-excellent)";
const AMBER = "var(--color-warning-strong)";

/** The colour mixed toward white, for pale bars. */
const light = (color: string, amount: number) => `color-mix(in oklab, ${color} ${amount}%, white)`;
/** The squircle's ground: the colour at 24% over white, a mid pastel, so the
 *  white pieces on it stand out (at 16% Auto Apply's back forms vanished). */
const ground = (color: string) => light(color, 24);
/** The colour mixed toward ink, for bars that stand for text. */
const deep = (color: string) => `color-mix(in oklab, ${color} 65%, var(--color-ink))`;

function Mark({ color, className, children }: MarkProps & { color: string; children: ReactNode }) {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" className={className}>
      <path d={SQUIRCLE} style={{ fill: ground(color) }} />
      {children}
    </svg>
  );
}

function ResumesMark({ className }: MarkProps) {
  return (
    <Mark color={BLUE} className={className}>
      <rect x="13" y="9" width="22" height="30" rx="3" fill="white" />
      <rect x="17" y="13" width="14" height="3" rx="1.5" style={{ fill: deep(BLUE) }} />
      <rect x="17" y="20" width="14" height="2" rx="1" style={{ fill: light(BLUE, 40) }} />
      <rect x="17" y="25" width="11" height="2" rx="1" style={{ fill: light(BLUE, 40) }} />
      <rect x="17" y="30" width="13" height="2" rx="1" style={{ fill: BLUE }} />
    </Mark>
  );
}

/** The match ring's arc: 91% of its circle (r 10.5), the followed Stripe
 *  application's score, the number the hero's Stripe tile shows. */
const RING = 2 * Math.PI * 10.5;

function MatchingMark({ className }: MarkProps) {
  return (
    <Mark color={PEACH} className={className}>
      <circle cx="24" cy="24" r="15" fill="white" />
      <circle
        cx="24"
        cy="24"
        r="10.5"
        fill="none"
        strokeWidth="4"
        style={{ stroke: light(MATCH, 22) }}
      />
      <circle
        cx="24"
        cy="24"
        r="10.5"
        fill="none"
        strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray={`${RING * 0.91} ${RING}`}
        transform="rotate(-90 24 24)"
        style={{ stroke: MATCH }}
      />
      <path
        d="M19.5 24.3l3 3 6-6.3"
        fill="none"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ stroke: deep(MATCH) }}
      />
    </Mark>
  );
}

/** Auto Apply's four forms, each at its top left: three filled and
 *  checked, the last still filling. */
const FORMS = [
  { x: 9, y: 9, done: true },
  { x: 25, y: 9, done: true },
  { x: 9, y: 25, done: true },
  { x: 25, y: 25, done: false },
];

function AutoApplyMark({ className }: MarkProps) {
  return (
    <Mark color={GREEN} className={className}>
      {FORMS.map(({ x, y, done }) => (
        <g key={`${x}-${y}`}>
          <rect x={x} y={y} width="14" height="14" rx="2.5" fill="white" />
          <rect
            x={x + 2.5}
            y={y + 3}
            width="9"
            height="1.8"
            rx="0.9"
            style={{ fill: deep(GREEN) }}
          />
          <rect
            x={x + 2.5}
            y={y + 6.5}
            width={done ? 6 : 4}
            height="1.8"
            rx="0.9"
            style={{ fill: done ? deep(GREEN) : light(GREEN, 45) }}
          />
          {done ? (
            <circle cx={x + 10.5} cy={y + 10.5} r="2" style={{ fill: GREEN }} />
          ) : (
            <circle
              cx={x + 10.5}
              cy={y + 10.5}
              r="2"
              fill="none"
              strokeWidth="1"
              style={{ stroke: light(GREEN, 45) }}
            />
          )}
        </g>
      ))}
    </Mark>
  );
}

/** The table's rows: their tops, and each one's stage, applied (violet),
 *  interview (amber), offer (green). */
const ROWS = [
  { y: 20, stage: VIOLET },
  { y: 26.8, stage: AMBER },
  { y: 33.4, stage: GREEN },
];

function TrackerMark({ className }: MarkProps) {
  return (
    <Mark color={PINK} className={className}>
      <rect x="8" y="10" width="32" height="28" rx="4" fill="white" />
      {/* The header row, its top corners the table's. */}
      <path d="M8 14a4 4 0 0 1 4-4h24a4 4 0 0 1 4 4v3H8z" style={{ fill: light(PINK, 35) }} />
      <path
        d="M8 24.5h32M8 31.2h32M19 17v21M30 17v21"
        strokeWidth="1"
        style={{ stroke: light(PINK, 22) }}
      />
      {ROWS.map(({ y, stage }) => (
        <g key={y}>
          <rect x="11" y={y} width="5" height="2" rx="1" style={{ fill: deep(PINK) }} />
          <rect x="21.5" y={y} width="6" height="2" rx="1" style={{ fill: light(PINK, 45) }} />
          <rect
            x="32"
            y={y - 0.7}
            width="6"
            height="3.4"
            rx="1.7"
            style={{ fill: light(stage, 45) }}
          />
        </g>
      ))}
    </Mark>
  );
}

export const FEATURE_MARKS = {
  resumes: ResumesMark,
  matching: MatchingMark,
  "auto-apply": AutoApplyMark,
  tracker: TrackerMark,
} satisfies Record<string, ComponentType<MarkProps>>;
