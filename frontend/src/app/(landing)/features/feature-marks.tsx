/**
 * The features' own marks (KAN-923): each a small piece of the real screen
 * on a squircle in the feature's colour, after Calendly's product icons,
 * which the user pointed to over the generic glyphs on solid tiles. The
 * user picked each from two rounds of sketches:
 *
 * - Resume Builder: a resume page, its last line the tailored one.
 * - Job Matching: a job card with the app's match ring on its corner, the
 *   ring large enough to read at 24px (a small match pill in the card did
 *   not, the user's "needs to be improved").
 * - Auto Apply: a stack of filled applications with a check, many filled
 *   at once.
 * - Application Tracker: the tracker's list, each row with its stage
 *   (applied, interview, offer). Not a board: the board view is archived.
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

function Mark({
  color,
  className,
  children,
}: MarkProps & { color: string; children: ReactNode }) {
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

/** The match ring's length for a 90% match, as `MatchGlyph` draws it. */
const RING = 2 * Math.PI * 5.2;

function MatchingMark({ className }: MarkProps) {
  return (
    <Mark color={VIOLET} className={className}>
      <rect x="7" y="8" width="29" height="27" rx="4.5" fill="white" />
      <rect x="11" y="12" width="7" height="7" rx="2" style={{ fill: VIOLET }} />
      <rect x="20.5" y="14" width="9" height="2.5" rx="1.25" style={{ fill: light(VIOLET, 35) }} />
      <rect x="11" y="23" width="20" height="3" rx="1.5" style={{ fill: deep(VIOLET) }} />
      <rect x="11" y="28.5" width="12" height="2.5" rx="1.25" style={{ fill: light(VIOLET, 35) }} />
      {/* The match ring on a white disc, cut out of the card by the ground's
          colour, so it reads as a badge on the card's corner. */}
      <circle
        cx="33.5"
        cy="33.5"
        r="9"
        fill="white"
        strokeWidth="2.5"
        style={{ stroke: ground(VIOLET) }}
      />
      <circle
        cx="33.5"
        cy="33.5"
        r="5.2"
        fill="none"
        strokeWidth="2.4"
        style={{ stroke: light(MATCH, 25) }}
      />
      <circle
        cx="33.5"
        cy="33.5"
        r="5.2"
        fill="none"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeDasharray={RING}
        strokeDashoffset={RING * 0.1}
        transform="rotate(-90 33.5 33.5)"
        style={{ stroke: MATCH }}
      />
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

/** The tracker's rows, each with its stage's colour: applied (violet),
 *  interview (amber), offer (green). */
const ROWS = [
  { y: 10, title: 11, stage: VIOLET },
  { y: 20, title: 9, stage: AMBER },
  { y: 30, title: 12, stage: GREEN },
];

function TrackerMark({ className }: MarkProps) {
  return (
    <Mark color={PINK} className={className}>
      {ROWS.map(({ y, title, stage }) => (
        <g key={y}>
          <rect x="8" y={y} width="32" height="8" rx="3" fill="white" />
          <rect x="11" y={y + 3} width={title} height="2" rx="1" style={{ fill: deep(PINK) }} />
          <rect
            x="26"
            y={y + 1.5}
            width="11"
            height="5"
            rx="2.5"
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
