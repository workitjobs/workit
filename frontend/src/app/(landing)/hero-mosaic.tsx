import { LogoFigure } from "@/components/logo";
import { matchTier } from "@/lib/match";

import { heroFits } from "./data";
import { followedJob } from "./feature-data";
import { FIELDS, FlatSheet, RingInk, ShapeTile, Tile, TileField, TileRow } from "./tiles";

/** The resume's bars, top to bottom; the negative one is the line WorkIt
 *  reworded for the posting. */
const SHEET = [80, "head", 100, -88, 66, "head", 100, 74, 100, 50] as const;

/**
 * The home hero's picture (the makeover's direction E, 2026-11-20): the
 * four parts of a search as tiles on one 4 × 4 grid round WorkIt's icon
 * tile, each product's tile holding a real piece of it, flat and
 * straight. A resume with a reworded line (Resume Builder), the followed
 * application's match with its band (Job Matching), tracker rows
 * (Application Tracker) and a form with Submit and the pen note "you
 * click" (Auto Apply: WorkIt fills, the student submits). Three plain
 * tiles with one shape each fill the grid.
 *
 * On load the tiles start a little apart and askew, snap to the grid one
 * after another, and the icon tile pops in last: the search's parts coming
 * together in one app, the headline's promise. All of it is CSS on the
 * server's HTML (`.mosaic` in landing.css), opacity and transform only,
 * and still with reduced motion. It replaced the grid of glass tiles
 * where postings lit up (hero-board.tsx, unmounted), which told Job
 * Matching's story alone; that grid goes to the Job Matching page.
 *
 * Decoration: the headline and its line say what WorkIt does, so the
 * whole picture is hidden from screen readers.
 */
export function HeroMosaic({ className }: { className?: string }) {
  const saved = heroFits[0];
  return (
    <div aria-hidden="true" className={className}>
      <div className="mosaic-box">
        <div className="mosaic">
          <Tile
            name="Resume Builder"
            color={FIELDS.sky.full}
            area="1 / 1 / 3 / 3"
            order={0}
            from={{ x: -2.9, y: -1.9, r: -9 }}
          >
            <FlatSheet lines={SHEET} className="mosaic-sheet" />
          </Tile>

          <Tile
            name="Job Matching"
            color={FIELDS.lilac.full}
            area="1 / 3 / 2 / 5"
            order={1}
            from={{ x: 2.75, y: -2.25, r: 8 }}
          >
            <RingInk className="tile-mark" />
            <span className="tile-band">{matchTier(followedJob.score)}</span>
            <span className="tile-number font-display">{followedJob.score}%</span>
          </Tile>

          <div className="tile tile-icon" style={{ gridArea: "2 / 3 / 3 / 4" }}>
            <LogoFigure />
          </div>

          <ShapeTile
            field="lilac"
            shape="quarter"
            area="2 / 4 / 3 / 5"
            order={4}
            from={{ x: 3.5, y: -0.5, r: 12 }}
          />

          <Tile
            name="Application Tracker"
            color={FIELDS.rose.full}
            area="3 / 1 / 4 / 3"
            order={2}
            from={{ x: -3.25, y: 0.9, r: 7 }}
          >
            <TileRow top={2.75} company={followedJob.company} stage="Applied" current />
            <TileRow top={4.875} company={saved.company} stage="Saved" />
          </Tile>

          <ShapeTile
            field="sky"
            shape="dome"
            area="4 / 1 / 5 / 2"
            order={5}
            from={{ x: -3, y: 2.75, r: -12 }}
          />
          <ShapeTile
            field="rose"
            shape="wedge"
            area="4 / 2 / 5 / 3"
            order={6}
            from={{ x: -0.6, y: 3.5, r: 10 }}
          />

          <Tile
            name="Auto Apply"
            color={FIELDS.mint.full}
            area="3 / 3 / 5 / 5"
            order={3}
            from={{ x: 3, y: 2.5, r: -8 }}
          >
            <TileField top={2.875}>Northview University</TileField>
            <TileField top={5.5}>Authorized to work: Yes</TileField>
            <TileField top={8.125} open>
              Start date
            </TileField>
            <b className="tile-submit">Submit</b>
            <i className="tile-note pen">you click</i>
          </Tile>
        </div>
        <p className="mosaic-note pen">
          <svg viewBox="0 0 36 30" aria-hidden="true">
            <path d="M4 26C6 12 16 6 30 6M22 1l9 5-8 6" />
          </svg>
          one app for all of it
        </p>
      </div>
    </div>
  );
}
