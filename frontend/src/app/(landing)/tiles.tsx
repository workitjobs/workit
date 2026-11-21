import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * The tile system of the home page's makeover (direction E,
 * frontend/docs/home-page-makeover-brief.md): flat colour tiles on one
 * grid, with ink or white on them and nothing else. The user picked it
 * over tilted paper with shadows because it reads as a system: one corner,
 * one gap, two layers. So a tile never takes a shadow, a gradient or a
 * border, and nothing on one rests tilted.
 *
 * Every size inside a tile is in em, and the grid that holds the tiles
 * sets the em from its own width (`.mosaic` in landing.css), so a picture
 * made of tiles scales as one piece from a phone to a wide screen. A new
 * piece keeps to em for that reason.
 *
 * Each product has one field (`FIELDS`), full for its own tile and pale
 * for a plain one. The pieces are server components with no script; a
 * picture built from them is decoration and hidden from screen readers by
 * its parent.
 */
export type FieldName = "sky" | "lilac" | "mint" | "rose";

/** A product's flat colour: sky for Resume Builder, lilac for Job
 *  Matching, mint for Auto Apply, rose for the Application Tracker. */
export const FIELDS: Record<FieldName, { full: string; pale: string }> = {
  sky: { full: "var(--mk-sky)", pale: "var(--mk-sky-pale)" },
  lilac: { full: "var(--mk-lilac)", pale: "var(--mk-lilac-pale)" },
  mint: { full: "var(--mk-mint)", pale: "var(--mk-mint-pale)" },
  rose: { full: "var(--mk-rose)", pale: "var(--mk-rose-pale)" },
};

/** Where a tile sits before it snaps to the grid, in em and degrees. */
export type TileStart = { x: number; y: number; r: number };

/**
 * One tile. `area` is its place on the grid (`row / column / row end /
 * column end`); `order` and `from` set its turn and its start in the
 * snap-in (landing.css, `tile-snap`), which a still tile leaves out.
 */
export function Tile({
  color,
  area,
  order,
  from,
  name,
  className,
  children,
}: {
  color: string;
  area: string;
  order?: number;
  from?: TileStart;
  name?: string;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div
      className={cn("tile", from && "tile-snap", className)}
      style={
        {
          gridArea: area,
          "--tile": color,
          "--i": order,
          "--x": from && `${from.x}em`,
          "--y": from && `${from.y}em`,
          "--r": from && `${from.r}deg`,
        } as CSSProperties
      }
    >
      {name && <span className="tile-name font-display">{name}</span>}
      {children}
    </div>
  );
}

/** A plain tile's one shape, in the field's full colour on its pale step. */
export function ShapeTile({
  field,
  shape,
  ...tile
}: {
  field: FieldName;
  shape: "quarter" | "half" | "dome" | "wedge";
  area: string;
  order?: number;
  from?: TileStart;
}) {
  return (
    <Tile {...tile} color={FIELDS[field].pale} className={cn("tile-shape", `tile-shape-${shape}`)}>
      <span style={{ background: FIELDS[field].full }} />
    </Tile>
  );
}

type InkProps = { className?: string };

/**
 * The products' ink marks: each feature mark (features/feature-marks.tsx)
 * redrawn as one bold ink shape for a colour tile. The cut-outs take the
 * tile's own colour (`--tile`), so a mark reads as cut from ink on any
 * field.
 */
export function ResumeInk({ className }: InkProps) {
  return (
    <svg viewBox="0 0 80 80" aria-hidden="true" className={className}>
      <path d="M14 6h36l16 16v52H14z" fill="currentColor" />
      <path d="M50 6v16h16z" fill="var(--tile)" opacity={0.6} />
      <g fill="var(--tile)">
        <rect x="22" y="34" width="36" height="5" rx="2.5" />
        <rect x="22" y="46" width="36" height="5" rx="2.5" />
        <rect x="22" y="58" width="22" height="5" rx="2.5" />
      </g>
    </svg>
  );
}

/** The app's match ring with a check in it, its arc at 91%: the followed
 *  application's match (`followedJob`). */
export function RingInk({ className }: InkProps) {
  return (
    <svg viewBox="0 0 80 80" aria-hidden="true" className={className}>
      <g fill="none" stroke="currentColor">
        <circle cx="40" cy="40" r="28" strokeWidth="13" opacity={0.2} />
        <circle
          cx="40"
          cy="40"
          r="28"
          strokeWidth="13"
          strokeLinecap="round"
          strokeDasharray="152 176"
          transform="rotate(-90 40 40)"
        />
        <path d="M30 41l7 7 14-16" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </svg>
  );
}

export function FormInk({ className }: InkProps) {
  return (
    <svg viewBox="0 0 80 80" aria-hidden="true" className={className}>
      <g fill="currentColor">
        <rect x="6" y="9" width="52" height="15" rx="7.5" />
        <circle cx="69" cy="16.5" r="6.5" />
        <rect x="6" y="32.5" width="52" height="15" rx="7.5" />
        <circle cx="69" cy="40" r="6.5" />
        <rect x="6" y="56" width="30" height="15" rx="7.5" />
      </g>
      <circle cx="69" cy="63.5" r="5" fill="none" stroke="currentColor" strokeWidth="3" />
    </svg>
  );
}

export function TableInk({ className }: InkProps) {
  return (
    <svg viewBox="0 0 80 80" aria-hidden="true" className={className}>
      <g fill="currentColor">
        <rect x="6" y="8" width="68" height="13" rx="4" />
        <rect x="6" y="28" width="38" height="11" rx="3" />
        <rect x="50" y="28" width="24" height="11" rx="5.5" />
        <rect x="6" y="45" width="38" height="11" rx="3" />
        <rect x="50" y="45" width="24" height="11" rx="5.5" opacity={0.55} />
        <rect x="6" y="62" width="38" height="11" rx="3" />
        <rect x="50" y="62" width="24" height="11" rx="5.5" opacity={0.3} />
      </g>
    </svg>
  );
}

/**
 * A resume as flat paper, cut off by its tile's foot: a name, headings and
 * lines as bars, with the lines WorkIt reworded in the Resume Builder's
 * blue. `lines` is each bar from the top: a width in percent, "head" for a
 * section heading, or a negative width for a reworded line.
 */
export function FlatSheet({
  lines,
  className,
}: {
  lines: readonly (number | "head")[];
  className?: string;
}) {
  return (
    <div className={cn("flat-sheet", className)}>
      <span className="is-name" />
      {lines.map((line, i) =>
        line === "head" ? (
          <span key={i} className="is-head" />
        ) : (
          <span
            key={i}
            className={line < 0 ? "is-new" : undefined}
            style={{ width: `${Math.abs(line)}%` }}
          />
        ),
      )}
    </div>
  );
}

/** A form's field, filled: its value and a check dot. `open` is a field
 *  still to fill, its dot a ring. */
export function TileField({
  top,
  open,
  children,
}: {
  top: number;
  open?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={cn("tile-field", open && "is-open")} style={{ top: `${top}em` }}>
      <span>{children}</span>
    </div>
  );
}

/** A tracker row: a company and its stage, the current stage in ink. */
export function TileRow({
  top,
  company,
  stage,
  current,
}: {
  top: number;
  company: string;
  stage: string;
  current?: boolean;
}) {
  return (
    <div className="tile-row" style={{ top: `${top}em` }}>
      <span>{company}</span>
      <b className={current ? "is-current" : undefined}>{stage}</b>
    </div>
  );
}
