import { ArrowDownIcon, CheckIcon, CursorIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import { MatchGlyph } from "@/components/match-badge";
import { cn } from "@/lib/cn";
import { matchColor, matchTier } from "@/lib/match";

import { heroFits } from "./data";
import { FaviconLogo } from "./favicon-logo";
import { followedJob, resumeFeature } from "./feature-data";
import { FEATURES, type FeatureSlug } from "./features/catalog";
import { FeatureIcon } from "./features/feature-icon";
import { HoldOffscreen } from "./hold-offscreen";
import { StudioBox, studioGround } from "./layout-parts";

/**
 * The home hero's picture (KAN-923's hero, redrawn 2026-11-21): the whole
 * pipeline, one application start to finish, as four cells of the page's
 * own drafting grid under the headline. Each cell is a product, in the
 * order a search meets them, with its mark and name over one framed box
 * (`StudioBox`, on the product's own sky, as its section further down the
 * page): the resume reworded for the posting, the posting's match, the
 * form filled with Submit left to the student, and the application in the
 * tracker. Every cell shows the followed application (`followedJob`), so
 * the four read as one story.
 *
 * It plays in turn: a line in the product's colour fills along the cell's
 * top rule (the product rows' own fill line, `.row-fill`), its scene plays
 * once, and the next cell starts; after the fourth, one turn of rest, then
 * all four clear together and it goes round again. On load the cells are
 * drawn left to right, each dragged out from its corner with an ink
 * square as its handle, and the loop starts as the last closes (the
 * `load-*` rules in landing.css). All CSS on the server's HTML (`.pipe-anim` in landing.css),
 * opacity and transform only, stopped off screen (`HoldOffscreen`) and
 * finished and still with reduced motion.
 *
 * Why this shape (the user's calls): the first makeover hero was a mosaic
 * of flat pastel tiles on a grey panel, built in a look the rest of the
 * page did not have, and it read as off beside the untouched sections. So
 * the hero is drawn from what the page already uses (the drafting grid,
 * the framed boxes, the feature marks, white cards with slate shadows),
 * and it shows all four products where the tile grid before it showed Job
 * Matching alone.
 *
 * Each scene is drawn at 252 × 201px with every size in em, and the box
 * sets the em from its own width (`.pipe-stage`), so a scene is the same
 * picture at any width. On a phone the cells are one row that swipes
 * sideways, so a box is about 268px wide and its words can be read. Each
 * cell is a link to its product's section; its name is the link's text
 * and the scene is hidden from screen readers.
 */
const STAGES: { slug: FeatureSlug; scene: ReactNode }[] = [
  { slug: "resumes", scene: <ResumeScene /> },
  { slug: "matching", scene: <MatchScene /> },
  { slug: "auto-apply", scene: <ApplyScene /> },
  { slug: "tracker", scene: <TrackerScene /> },
];

export function HeroPipeline({ className }: { className?: string }) {
  return (
    <HoldOffscreen className={cn("pipe relative lg:-mx-6", className)}>
      {/* Below sm the cells are one row that swipes sideways, a cell at
          78% of the row so the next one shows at the edge: two by two on a
          phone, each box was 165px wide and the words in its scene 6 to
          8px tall. The row runs to the screen's edges (`-mx-4`). From sm
          it is the grid: two by two, then four across from lg. */}
      <ul className="relative -mx-4 flex snap-x snap-mandatory scroll-pl-4 [scrollbar-width:none] gap-3 overflow-x-auto px-4 sm:mx-0 sm:grid sm:grid-cols-2 sm:gap-4 sm:overflow-visible sm:px-0 lg:grid-cols-4 lg:gap-0 [&::-webkit-scrollbar]:hidden">
        {STAGES.map(({ slug, scene }, i) => {
          const feature = FEATURES[slug];
          return (
            <li
              key={slug}
              className="relative w-[78%] shrink-0 snap-start sm:w-auto lg:px-4 lg:pt-4"
              style={{ "--i": i } as CSSProperties}
            >
              {/* The whole cell is a link to its product's section further
                  down the page (the sections' ids are the slugs, as
                  the product sections' ids): a visitor who sees a product
                  here tries to click it. Its name is the link's text; the
                  scene is decoration. */}
              <Link href={`/#${slug}`} className="group block rounded-2xl">
                <span
                  aria-hidden="true"
                  className="pipe-anim pipe-fill absolute inset-x-0 top-0 hidden h-0.5 origin-left lg:block"
                  style={{ background: feature.glow }}
                />
                <p className="text-ink flex items-center gap-2 text-sm font-medium">
                  <FeatureIcon feature={feature} />
                  {feature.name}
                  <ArrowDownIcon
                    aria-hidden="true"
                    className="text-ink-meta ml-auto size-4 transition-transform duration-200 group-hover:translate-y-0.5"
                  />
                </p>
                <StudioBox
                  ground={studioGround({ glow: feature.glow })}
                  className="pipe-scene mt-3 aspect-[5/4]"
                >
                  <div aria-hidden="true" className="pipe-stage">
                    {scene}
                  </div>
                </StudioBox>
              </Link>
            </li>
          );
        })}
      </ul>
      {/* The grid's own lines, from lg up: a rule across the window at the
          cells' top, one down between each pair of cells to the frame's
          foot (1.5rem below, `DraftLines`' gap in page.tsx), and an ink
          square at every crossing, as the frame's corners have. */}
      <span aria-hidden="true" className="pipe-lines">
        <span className="draft-h top-0" />
        {[25, 50, 75].map((x, k) => (
          <span key={x} className="pipe-v" style={{ left: `${x}%`, "--k": k } as CSSProperties} />
        ))}
        {[0, 25, 50, 75, 100].map((x, k) => (
          <i key={x} className="top-0" style={{ left: `${x}%`, "--k": k } as CSSProperties} />
        ))}
        {/* The foot's squares, the frame's two corners among them
            (`DraftLines first` draws none). Each but the first is a cell's
            handle on load (`.pipe-handle`): it rides the cell's corner as
            the cell is drawn, then rests here. `--k` is that cell. */}
        {[0, 25, 50, 75, 100].map((x, k) => (
          <i
            key={x}
            className={k === 0 ? "top-full" : "pipe-handle top-full"}
            style={{ left: `${x}%`, "--k": k - 1 } as CSSProperties}
          />
        ))}
      </span>
    </HoldOffscreen>
  );
}

/**
 * The same four cells two by two, for the auth screens' scene half
 * (components/auth-frame.tsx, the user's pick of two directions,
 * 2026-11-22): the right half of that frame is two of the hero's columns
 * wide, so each cell keeps the width it has on the home page, and the
 * frame's own lines rule the half in four. The rows share the frame's
 * height and each cell's content is centred in its own. The cells are no
 * links here and the whole block is decoration: beside a form, a picture
 * that takes a click would take it from the form. It plays the hero's
 * loop on the hero's clock, and each cell is drawn out from its corner on
 * load by the same rule (`.pipe li` in landing.css), with the frame's
 * handles (auth-frame.css).
 */
export function PipelineQuad() {
  return (
    <HoldOffscreen className="pipe h-full">
      <ul className="grid h-full grid-cols-2 grid-rows-2">
        {STAGES.map(({ slug, scene }, i) => {
          const feature = FEATURES[slug];
          return (
            <li
              key={slug}
              className="relative flex flex-col justify-center p-4"
              style={{ "--i": i } as CSSProperties}
            >
              <span
                className="pipe-anim pipe-fill absolute inset-x-0 top-0 h-0.5 origin-left"
                style={{ background: feature.glow }}
              />
              <p className="text-ink flex items-center gap-2 text-sm font-medium">
                <FeatureIcon feature={feature} />
                {feature.name}
              </p>
              <StudioBox
                ground={studioGround({ glow: feature.glow })}
                className="pipe-scene mt-3 aspect-[5/4]"
              >
                <div className="pipe-stage">{scene}</div>
              </StudioBox>
            </li>
          );
        })}
      </ul>
    </HoldOffscreen>
  );
}

/** A white piece of mock UI on a scene's sky, its corner and place in em. */
function Card({ className, children }: { className?: string; children?: ReactNode }) {
  return (
    <div
      className={cn(
        "absolute rounded-[0.75em] bg-white shadow-[var(--mk-shadow-float)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** A grey bar that stands for a line of text. */
function Bar({ className }: { className?: string }) {
  return <span className={cn("block h-[0.34em] rounded-full bg-slate-900/[0.12]", className)} />;
}

/** Resume Builder: the resume, two lines reworded for the posting in the
 *  product's blue as the keywords the student picked tick off. */
function ResumeScene() {
  return (
    <>
      <Card className="top-[1.2em] left-[1.1em] h-[12em] w-[7.6em] rounded-b-none px-[0.85em] py-[1em]">
        <span className="bg-ink block h-[0.5em] w-1/2 rounded-full" />
        <Bar className="mt-[0.55em] w-4/5" />
        <Bar className="mt-[1em] w-1/3 bg-slate-900/30" />
        <Bar className="mt-[0.55em]" />
        <span className="pipe-anim pipe-grow-a bg-advanced mt-[0.55em] block h-[0.34em] w-[88%] rounded-full" />
        <span className="pipe-anim pipe-grow-b bg-advanced mt-[0.55em] block h-[0.34em] w-3/5 rounded-full" />
        <Bar className="mt-[1em] w-1/3 bg-slate-900/30" />
        <Bar className="mt-[0.55em]" />
        <Bar className="mt-[0.55em] w-3/4" />
        <Bar className="mt-[0.55em]" />
      </Card>
      <div className="absolute top-[1.5em] left-[9.4em] grid justify-items-start gap-[0.45em]">
        {resumeFeature.job.keywords.map((keyword, i) => (
          <span
            key={keyword}
            className={cn(
              "pipe-anim flex items-center gap-[0.3em] rounded-full bg-white px-[0.6em] py-[0.3em] shadow-[var(--mk-shadow-float)]",
              i === 0 ? "pipe-pop-a" : "pipe-pop-b",
            )}
          >
            <CheckIcon weight="bold" className="text-advanced size-[0.7em]" />
            <span className="text-[0.66em] font-medium">{keyword}</span>
          </span>
        ))}
      </div>
    </>
  );
}

/** Job Matching: the posting's card, its match filling to the app's band. */
function MatchScene() {
  const { title, company, domain, score } = followedJob;
  return (
    <>
      <Card className="inset-x-[2.2em] top-[2em] h-[4em] bg-white/55 shadow-none" />
      <Card className="inset-x-[1.2em] top-[3em] p-[0.8em]">
        <div className="flex items-center gap-[0.55em]">
          <FaviconLogo domain={domain} eager className="size-[1.9em] rounded-[0.45em]" />
          <div className="min-w-0">
            <p className="truncate text-[0.74em] leading-tight font-semibold">{title}</p>
            <p className="text-ink-meta text-[0.68em] leading-tight">{company}</p>
          </div>
        </div>
        <div className="mt-[0.85em] flex items-center gap-[0.35em]">
          <MatchGlyph score={score} className="pipe-anim pipe-pop-b size-[0.95em]" />
          <span
            className="pipe-anim pipe-pop-b text-[0.7em] font-semibold"
            style={{ color: matchColor(score) }}
          >
            {matchTier(score)}
          </span>
          <span className="ml-auto text-[0.74em] font-semibold tabular-nums">{score}%</span>
        </div>
        <div className="mt-[0.45em] h-[0.3em] overflow-hidden rounded-full bg-slate-900/[0.08]">
          <span
            className="pipe-anim pipe-grow-a block h-full rounded-full"
            style={{ width: `${score}%`, background: matchColor(score) }}
          />
        </div>
      </Card>
    </>
  );
}

/** Auto Apply: the form's basic fields fill, and Submit is the student's. */
function ApplyScene() {
  const field = (grow: string, pop: string, width: string) => (
    <div className="mt-[0.6em]">
      <Bar className="h-[0.28em] w-1/3 bg-slate-900/30" />
      <div className="mt-[0.35em] flex h-[1.6em] items-center justify-between rounded-[0.4em] px-[0.5em] shadow-[inset_0_0_0_1px_rgb(15_23_42/0.14)]">
        <span className={cn("pipe-anim bg-ink/45 block h-[0.34em] rounded-full", grow, width)} />
        <CheckIcon weight="bold" className={cn("pipe-anim text-positive size-[0.75em]", pop)} />
      </div>
    </div>
  );
  return (
    <Card className="inset-x-[1.2em] top-[1.1em] p-[0.8em]">
      <p className="text-ink-meta truncate text-[0.66em] leading-tight font-medium">
        {followedJob.company} · {followedJob.title}
      </p>
      {field("pipe-grow-a", "pipe-pop-a", "w-3/5")}
      {field("pipe-grow-b", "pipe-pop-b", "w-2/5")}
      <div className="relative mt-[0.8em]">
        <span className="bg-ink inline-flex h-[1.7em] items-center rounded-[0.45em] px-[0.9em] text-white">
          <span className="text-[0.68em] font-semibold">Submit</span>
        </span>
        <CursorIcon
          weight="fill"
          className="pipe-anim pipe-in-c text-ink absolute top-[0.9em] left-[3.4em] size-[1.15em] drop-shadow-[0_1px_1px_rgb(255_255_255/0.9)]"
        />
      </div>
    </Card>
  );
}

/** One row of the tracker's table: a company and its stage. */
function TrackerRow({
  company,
  domain,
  className,
  children,
}: {
  company: string;
  domain: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex h-[2.3em] items-center gap-[0.5em] border-t border-slate-900/[0.07] px-[0.8em]",
        className,
      )}
    >
      <FaviconLogo domain={domain} eager className="size-[1.35em] rounded-[0.35em]" />
      <span className="text-[0.72em] font-medium">{company}</span>
      {children}
    </div>
  );
}

const STAGE_PILL = "ml-auto rounded-full px-[0.75em] py-[0.25em]";
const STAGE_TEXT = "block text-[0.62em] leading-tight font-semibold";

/** Application Tracker: the application lands as a row, at Applied. */
function TrackerScene() {
  const saved = heroFits.filter((fit) => fit.company !== followedJob.company).slice(0, 2);
  return (
    <Card className="inset-x-[1.2em] top-[1.5em] overflow-hidden">
      <div className="text-ink-meta flex justify-between px-[0.8em] py-[0.55em]">
        <span className="text-[0.56em] font-semibold tracking-[0.06em] uppercase">Company</span>
        <span className="text-[0.56em] font-semibold tracking-[0.06em] uppercase">Stage</span>
      </div>
      <TrackerRow
        company={followedJob.company}
        domain={followedJob.domain}
        className="pipe-anim pipe-in-a"
      >
        <span className={cn("pipe-anim pipe-pop-b bg-brand-tint text-brand-ink", STAGE_PILL)}>
          <span className={STAGE_TEXT}>Applied</span>
        </span>
      </TrackerRow>
      {saved.map((fit) => (
        <TrackerRow key={fit.domain} company={fit.company} domain={fit.domain}>
          <span className={cn("text-ink-meta bg-slate-900/[0.06]", STAGE_PILL)}>
            <span className={STAGE_TEXT}>Saved</span>
          </span>
        </TrackerRow>
      ))}
    </Card>
  );
}
