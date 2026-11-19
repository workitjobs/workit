/**
 * The features' own marks (KAN-923): each a small piece of the real screen
 * on a squircle in the feature's colour, after Calendly's product icons,
 * which the user pointed to over the generic glyphs on solid tiles. The
 * user picked each from three rounds of sketches:
 *
 * - Resume Builder: a resume page, its last line the tailored one.
 * - Job Matching: a card with the match's score over two ticked skills,
 *   the score and the checklist the user asked it to show. The score is
 *   91%, the followed Stripe application's match on the home page's journey
 *   (`journey` in data.ts), so the mark repeats a number the page shows.
 *   A job card with a ring badge came before; the user found it off.
 * - Auto Apply: a stack of filled applications with a check, many filled
 *   at once.
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

/** A ticked skill on Job Matching's card: a green disc with a white tick. */
function Tick({ cy }: { cy: number }) {
  return (
    <>
      <circle cx="15.5" cy={cy} r="2.8" style={{ fill: MATCH }} />
      <path
        d={`M14.2 ${cy}l0.9 0.9 1.8-1.9`}
        fill="none"
        stroke="white"
        strokeWidth="1.1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  );
}

function MatchingMark({ className }: MarkProps) {
  return (
    <Mark color={VIOLET} className={className}>
      <rect x="9" y="8" width="30" height="32" rx="5" fill="white" />
      {/* The score, in the match's green on its pale step. */}
      <rect x="13" y="12" width="22" height="9" rx="4.5" style={{ fill: light(MATCH, 22) }} />
      <text
        x="24"
        y="19.2"
        textAnchor="middle"
        fontSize="7.5"
        fontWeight="700"
        style={{ fill: deep(MATCH), fontFamily: "inherit" }}
      >
        91%
      </text>
      <Tick cy={27} />
      <rect x="20" y="26" width="14" height="2.2" rx="1.1" style={{ fill: deep(VIOLET) }} />
      <Tick cy={34} />
      <rect x="20" y="33" width="10" height="2.2" rx="1.1" style={{ fill: deep(VIOLET) }} />
    </Mark>
  );
}

function AutoApplyMark({ className }: MarkProps) {
  return (
    <Mark color={GREEN} className={className}>
      <rect x="16" y="7" width="23" height="18" rx="3" fill="white" fillOpacity="0.55" />
      <rect x="12.5" y="11.5" width="23" height="18" rx="3" fill="white" fillOpacity="0.8" />
      <rect x="9" y="16" width="23" height="22" rx="3" fill="white" />
      <rect x="9" y="16" width="23" height="4" rx="2" style={{ fill: light(GREEN, 45) }} />
      <rect x="12" y="23" width="17" height="3" rx="1.5" style={{ fill: deep(GREEN) }} />
      <rect x="12" y="28" width="12" height="3" rx="1.5" style={{ fill: deep(GREEN) }} />
      <circle
        cx="35"
        cy="35"
        r="6"
        strokeWidth="2"
        style={{ fill: deep(GREEN), stroke: ground(GREEN) }}
      />
      <path
        d="M32.4 35l1.9 1.9 3.4-3.7"
        fill="none"
        stroke="white"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
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
