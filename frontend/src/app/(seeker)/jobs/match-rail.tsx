import { CheckIcon } from "@/components/icons";
import { cn } from "@/lib/cn";
import { matchColor, matchTier } from "@/lib/match";

import type { Highlight } from "./data";

/**
 * The scored rail down the right of a recommendation.
 *
 * WHY IT IS NOT DARK. The reference layout paints this panel near-black, which
 * is what makes the score the loudest thing on the row. WorkIt has no dark
 * surface role — `deep` exists only as a tint under a company glyph — so a
 * 200px black block would be the only dark thing in the signed-in app and would
 * read as an advert pinned to every card. On a card the score sits on a tile
 * inset from the card's edge, `--color-well` on the white rail, and earns
 * its prominence from an 88px ring with its tier under it (2026-11-09). It
 * was a 64px ring behind a hairline, which read as a footnote. It was `--color-well` (#f7f7f7), and on
 * the seeker pages' grey ground (#f5f5f5) a grey rail at the card's edge read
 * as the ground showing through, so the card looked cut short (2026-11-03).
 *
 * The arc colours by band, red, yellow or green, from `matchColor` in
 * @/lib/match, rather than one brand colour at every score: the brand is the
 * Applied stage's colour, so a violet ring read as a status. See the note on
 * `TIERS` there. Length still carries the magnitude and the label still
 * carries the band; colour is a third, faster read of the same two facts, not
 * a replacement for either.
 *
 * The label's words are ink-muted, not the band colour: the yellow step is
 * about 3:1 on white, drawn for strokes, short of the 4.5:1 a label needs.
 * Nothing sits before the words. A dot in the band's colour did until KAN-518,
 * and beside the ring it only said the colour twice.
 *
 * Reasons are 13px (2026-11-09; 12px until then, small grey type beside an
 * 88px ring): wins in ink, caveats a step quieter in ink-muted, both clear of
 * AA: the tick and the dot already tell the two kinds apart, so fading
 * the reasons to hesitate further would only say they do not matter.
 *
 * WITH NO SCORE (`score` null) IT IS A PLACEHOLDER, not absent. Nothing
 * scores a live role yet, but the feed card keeps the rail so it has the
 * shape it will have once matching exists: the ring's empty track with a
 * dash in it, "Score Coming Soon" where the tier goes, and three grey bars
 * where the reasons go. A screen reader hears that the score is not
 * available yet rather than a dash. Not a made-up number: a fake 87% on a
 * real role would read as a real verdict.
 *
 * THE ARC DRAWS ITSELF to the score when the rail appears, from twelve
 * o'clock round (--animate-ring-fill), so the length reads as an amount
 * being measured out rather than a shape printed on the card.
 *
 * `standalone` only changes the shape — a card with its own rounded corners
 * and border, rather than a rail flush against a bigger card's edge — not the
 * fill.
 *
 * Its width and edge switch at `@xl`, so it needs an `@container` ancestor:
 * `JobDetailHeader`'s card is one, and stacks the rail under the facts below
 * 576px of card, not at a window breakpoint that cannot see the shell's panel.
 */

/* 64px box, 5px stroke, so the arc's centreline sits 2.5px inside the edge. */
const RADIUS = (64 - 5) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function MatchRing({ score, small = false }: { score: number | null; small?: boolean }) {
  const color = score === null ? undefined : matchColor(score);
  // The compact card's tile draws it at 48px, its number at 14px.
  const figure = small ? "text-body font-semibold" : "text-heading";

  // 88px (2026-11-09): the score is the one thing this tile is for, so it is
  // the largest thing in it. At 64px beside the tier it read as a footnote.
  return (
    <div className={cn("relative", small ? "size-12" : "size-22")}>
      {/* -rotate-90 starts the arc at twelve o'clock rather than three. */}
      <svg viewBox="0 0 64 64" aria-hidden="true" className="size-full -rotate-90">
        <circle
          cx="32"
          cy="32"
          r={RADIUS}
          fill="none"
          strokeWidth="5"
          className="stroke-border-strong"
        />
        {score !== null && (
          <circle
            cx="32"
            cy="32"
            r={RADIUS}
            fill="none"
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={`${(CIRCUMFERENCE * score) / 100} ${CIRCUMFERENCE}`}
            style={{ stroke: color }}
            className="animate-ring-fill"
          />
        )}
      </svg>

      <p className="absolute inset-0 flex items-center justify-center">
        {score === null ? (
          <span aria-hidden="true" className={cn(figure, "text-ink-subtle")}>
            –
          </span>
        ) : (
          <span className="flex items-baseline">
            <span className={cn(figure, "text-ink")}>{score}</span>
            <span className="text-meta text-ink-meta">%</span>
          </span>
        )}
      </p>
    </div>
  );
}

/** A caveat's marker. Sized like the check it replaces, so the text lines up. */
function Dot() {
  return (
    <span aria-hidden="true" className="mt-0.5 flex size-4 shrink-0 items-center justify-center">
      <span className="bg-ink-faint size-1.5 rounded-full" />
    </span>
  );
}

export function MatchRail({
  score,
  highlights,
  standalone = false,
  className,
}: {
  /** Null draws the placeholder rail; see "WITH NO SCORE" above. */
  score: number | null;
  highlights: Highlight[];
  /** A rounded card that floats on its own — the job detail page's layout,
   *  which sits it beside the facts rather than flush against a bigger
   *  card's edge. Default false keeps the recommendation feed's flush rail
   *  unchanged. */
  standalone?: boolean;
  /** Placement, or a different fill where a page needs one. */
  className?: string;
}) {
  return (
    <aside
      aria-label="Why This Matches"
      className={cn(
        "bg-panel border-border-subtle flex shrink-0 flex-col @xl:w-60",
        standalone
          ? "rounded-card items-center gap-2 border p-4"
          : // On a card, the score is a tile of its own, inset from the
            // card's edge on a soft grey (2026-11-09): one area, one main
            // fact. A rule beside the body had made it read as a footnote.
            "p-2 @max-xl:pt-0",
        className,
      )}
    >
      <div
        className={cn(
          "flex flex-1 flex-col items-center gap-2",
          // Centred down the tile as well as across it: top-aligned, the
          // spare height of a taller card pooled under the reasons.
          !standalone && "bg-well rounded-card justify-center px-4 py-3",
        )}
      >
        {/* The ring over its tier, both centred: the score first, its band
          under it. */}
        <MatchRing score={score} />
        {score === null ? (
          <p className="text-caption text-ink-meta font-semibold uppercase">Score Coming Soon</p>
        ) : (
          // The verdict, so ink at 14px: in 13px ink-muted it read as a caption.
          <p className="text-body text-ink font-semibold">{matchTier(score)}</p>
        )}
        {score === null && (
          <>
            <p className="sr-only">
              This role has no match score yet. Reasons it fits you will show here once matching is
              built.
            </p>
            {/* Where the reasons will go: a caveat's dot and a bar per row, at
              the rows' own 15px rhythm. */}
            <ul
              aria-hidden="true"
              className="border-border-subtle mt-1 flex w-full flex-col gap-1.5 border-t pt-3"
            >
              {["w-full", "w-4/5", "w-11/12"].map((width) => (
                <li key={width} className="flex h-[15px] items-center gap-1.5">
                  <Dot />
                  <span className={cn("bg-border-strong h-2 rounded-full", width)} />
                </li>
              ))}
            </ul>
          </>
        )}

        {/* No reasons, no list: an empty one drew a stray rule under the tier. */}
        {score !== null && highlights.length > 0 && (
          // A centred block of left-aligned rows, so the list sits under the
          // ring and tier instead of against the tile's left edge, with no
          // rule: on the grey tile a hairline only cut it in two
          // (2026-11-09).
          <ul className="mt-1 flex w-fit max-w-full flex-col gap-1.5">
            {highlights.map((highlight) => (
              <li key={highlight.text} className="flex items-start gap-1.5">
                {/* The tick and the dot are the whole distinction on screen, so the
                same distinction is spelled out for anyone not seeing them. */}
                <span className="sr-only">
                  {highlight.met ? "In your favour:" : "Worth weighing:"}
                </span>
                {highlight.met ? (
                  <CheckIcon className="text-positive-ink mt-0.5 size-4 shrink-0" />
                ) : (
                  <Dot />
                )}
                {/* A short label (the API's `text`), its whole sentence in
                  the tooltip (`detail`); two lines at most, in case a long
                  skill or field name stretches one. A sentence that ran to
                  four lines made the rail, and so the card, taller than the
                  job's own content. */}
                <span
                  title={highlight.detail ?? highlight.text}
                  className={cn(
                    "text-label line-clamp-2",
                    highlight.met ? "text-ink" : "text-ink-muted",
                  )}
                >
                  {highlight.text}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

/**
 * The compact card's score (2026-11-09): the large card's tile in small, a
 * 48px ring over its tier on `--color-well`, with no reasons, since the open
 * job beside the list shows them. It replaced a pill in the card's footer, so
 * the score reads the same way on both cards.
 */
export function MatchScoreTile({ score, className }: { score: number; className?: string }) {
  return (
    <div
      aria-label={`${score}% match, ${matchTier(score)}`}
      role="img"
      className={cn(
        "bg-well rounded-card flex flex-col items-center justify-center gap-1 px-2 py-2.5",
        className,
      )}
    >
      <MatchRing score={score} small />
      <p aria-hidden="true" className="text-note text-ink font-semibold whitespace-nowrap">
        {matchTier(score)}
      </p>
    </div>
  );
}
