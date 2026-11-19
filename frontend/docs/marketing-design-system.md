# Marketing design system (KAN-923)

The rules for every page in `app/(landing)/`: the home page, the feature
pages, Pricing, the Resources pages and the legal pages. Set 2026-11-19,
after the user found the site still looked AI-made (the violet glass
buttons, the bordered sign-up buttons, the lavender gradient on cards).
`home-page-review.md` has the Calendly review behind it. The app's own
screens follow `design.md`, not this file.

## Principles

1. **Colour lives in two places only**: the home hero (its grainy violet
   ground under glass tiles) and the framed boxes (`StudioBox`). The page, its cards and its buttons are white,
   ink and grey. A violet card, a violet shadow or a violet-tinted white
   anywhere else reads as AI-made.
2. **One accent, used small.** WorkIt violet marks things: a
   check, Plus's limit pills, the slop word. It
   never fills a button or a card. The one exception is the home hero's
   ground, the page's one large field of violet.
3. **A heading stands alone.** No small label above a section heading
   (an "eyebrow"): the violet ones over every heading read as a template,
   and the user had them all removed. `SectionHeading` takes no eyebrow.
4. **Value before hue.** Check a screen in greyscale: the surfaces that
   must separate need distinct lightness, and the main action must be the
   strongest contrast in its area. The home hero once had every surface
   between 94% and 100% lightness (pairs at 1.01 to 1.11 contrast) and read
   as a loading skeleton; a different hue did not fix it, a lightness step
   did. Keep one colour temperature per area: violet-tinted greys with
   violet, never a cool grey beside a violet tint.
5. **Size carries hierarchy, not weight.** Every heading is weight 500;
   the steps of `TYPE` do the work.
6. **Motion stays in its box.** No scene fills the screen; a loop has a
   pause; a reveal plays once. The one thing that pins is a product
   section, as one block at the screen's middle, while the scroll opens
   its rows.
7. **Reuse before drawing.** Every role below is one class or one
   component. A page may not invent a sixth button or a second card.

## Colour roles

| Role | Token | Use |
| --- | --- | --- |
| Ink | `--color-ink` #121a28 | Headings, the primary button, the featured plan |
| Body | `--color-ink-muted` | Lead lines, body copy |
| Meta | `--color-ink-meta` | Subtitles, captions, secondary rows |
| Page | white | Every page's ground |
| Hairline | `--mk-hairline` (slate at 8%) | A card's edge, drawn as a shadow |
| Accent | `--color-landing-brand-*`, `--color-brand` | Small marks only (principle 2) |
| Feature colours | `features/catalog.ts` (`tint`, `glow`, `onGlow`) | Inside that feature's box and on its mark |
| Hero ground | `.hero-ground`: deeper violets in the corners, lighter along the edges, a pale pool behind the headline, grey noise in overlay | The home hero's panel; one hue family |
| Empty tile | `.hero-tile`: frosted glass (a faint white, a 14px blur, a white hairline, a brighter top edge) | The hero's tiles that are not lit |
| Headline tile | `.hero-copy`: solid white, a slate shadow | The hero's brightest surface and its one tile that is not glass; ink text, the Google pair on it |
| Lit tile | `.board-lit`: near-white glass over the tile's frost, a white edge, a slate shadow; ink text, the match in the app's own colours | The hero's fits |

Shadows are slate, never violet: `--mk-shadow-card` for a card resting on
the page, `--mk-shadow-float` for UI floating over colour (a mock card in a
box, a chip, a pill, a white button on a fill).

## Type

`TYPE` in `layout-parts.tsx`. Plus Jakarta Sans for headings, Newsreader
for a product's heading, Inter for everything else.

| Step | Face | Desktop / phone | Use |
| --- | --- | --- | --- |
| `display` | Jakarta 500 | 72 / 40 | A page's h1 (home, feature, Pricing, Resources) |
| `chapter` | Jakarta 500 | 56 / 34 | `SectionHeading`, the closing call to action, the statement |
| `product` | Newsreader 500 | 48 / 30 | A product section's h2, hiring systems |
| `card` | Jakarta 500 | 28 / 24 | A card's heading |
| `item` | Jakarta 500 | 18 | A row's title (the product accordion) |
| `lead` | Inter 400 | 19 / 18 | The line under a display or chapter heading |
| `eyebrow` | Inter 600, capitals, 0.08em | 12 | A small grey line (the logo strip's, a journey step's); never a label above a heading |

No gradient text (Pricing's ink-to-violet headline went). No full stop on a
section heading; a hero line may keep one.

## Shape and space

- **Corners nest**: an outer corner is the inner corner plus the padding
  between them, so the curves run parallel. Tiles and framed boxes are
  16px (`rounded-2xl`); a card holding one 12px in is 28px; panels
  (`PANEL`, the footer included) are 24px on a phone and 28px from sm,
  where they hold the hero's tiles 8px and 12px in. Buttons keep
  `rounded-control`; pills are full. Panels were 48px from lg, which the
  user found too round beside the tiles.
- Width: `CONTAINER` (max-w-6xl); a reading column max-w-2xl; a chapter
  heading max-w-3xl. The home hero alone fills the panel edge to edge.
- Section rhythm: `py-16 sm:py-24` for a product section, `py-20 sm:py-28`
  for a chapter.

## Components

### Buttons (`buttons.tsx`)

| Role | Component | Look |
| --- | --- | --- |
| Primary | `PrimaryButton` (`.primary-btn`) | Solid ink, white label, lighter on hover |
| Secondary | `SecondaryButton` | Slate at 6%, ink label, no border |
| On a fill | `OnFillButton` | White, ink label, `--mk-shadow-float`, no border |

Two heights only: `md` 44px, `lg` 48px. The header's Get started and Open
WorkIt are primary; Log in is secondary. No glass, no gradient, no
outline.

### The sign-up pair (`social-sign-up.tsx`)

Google's own neutral theme: #F2F2F2 fill, no stroke, #1F1F1F Google Sans
Medium, the full-colour G. LinkedIn takes the same treatment, its tile
with a white "in". Always followed by "Or sign up with email". It is the
guidelines' only theme with no border: the light theme (white with a
#747775 stroke) read as a bordered button, and the dark theme was too
heavy. The soft grey matches `SecondaryButton`, so Download for Mac
(KAN-922) sits in the same row as a `SecondaryButton`.

### The home hero's grid (`hero-board.tsx`)

The first screen and nothing else: a grainy violet panel the screen's
height, filled edge to edge by frosted glass tiles. The headline sits in
one large solid white tile in the middle, the brightest surface. Seven
tiles light up in turn as bright glass cards, each a real employer, the
role and the match's strength in the app's bands ("Excellent Match" or
"Good Match", from `lib/match.ts`) behind the app's own 14px match ring
(`MatchGlyph`), over a slim bar in the band's colour that fills, the
percentage at its end, set in the Jobs page job card's weights (role
medium, company regular, band semibold) in ink. A match anywhere on the
marketing pages says its band first: a bare number does not tell a
student whether to apply. Columns follow the screen's shape so the tiles
stay near square. The four features follow below, in their own section.

A lit tile holds **two groups, by proximity**: the job (company, role)
at the top and the verdict (band, bar, percentage) at the foot. The gap
between them is at least 10px and the gap inside the verdict 4px, so the
band reads with its bar. At 6px each way the band read as part of the
role. The role takes two lines, one or none by the tile's height, and
never shrinks into the verdict.

The glass costs little because its blur reads a still ground: only the
lit layer inside each tile changes, and it has no blur of its own (a
tile with a backdrop filter is the backdrop root of its content, so a
second blur would see nothing).

### Cards

- **`.surface-card`**: white, `--mk-shadow-card`. Every solid card: the
  hero's feature card, the journey's steps, a feature page's steps and
  related cards, Pricing's Pro plan. Carries no `ring-*` or `shadow-*`
  utility.
- **`.glass-card`**: frosted white over colour (a story's scene title,
  Pricing's board). Neutral; never tinted.
- **Mock UI inside a box**: `bg-white rounded-2xl` with
  `--mk-shadow-float`.
- Paper (a resume) stays flat paper.

### `StudioBox` (`layout-parts.tsx`)

The frame for every picture and animation: 16px corners, a feature's
`studioGround` and a fine grain (`.studio-box`; ruled lines across it were
taken out, the user found them odd over the gradients). One picture
per box; the UI inside floats on it.

The ground is a sky in the feature's one colour, after Calendly's boxes:

| Where | Ground |
| --- | --- |
| Top | The colour at 24% over white |
| Middle (about 42%) | The colour at 7%, near white, with a bright white band behind the card, like a horizon |
| Lower (72%) | The colour at 38% |
| Foot | The colour at full strength, 10% toward ink |

Why it works where the blobs did not: one hue and one light. Value runs
from light to deep in one direction, so the box has depth and the white
card reads as lit from above; the old ground was four blobs (one in a
second colour) at one lightness, with no source and no direction, which
read as muddy. Nothing writes straight on the lower fifth: no one text
colour holds 4.5:1 on every foot (ink fails on the blue, violet and pink;
white fails on the green). Text there sits on a card or a pill.

### Pills and chips

- `HERO_PILL`: frosted white, `--mk-shadow-float`, the pill above a
  feature page's, Pricing's and a Resources page's h1. The home hero has
  none (the user had it removed).
- A feature chip: `FeatureIcon` (the feature's mark, below) plus the
  feature's name, ink text.
- Status chips (the closing row): white, a logo, a label, the company in
  meta grey.
- `SoonChip` for anything not built yet.

### Feature marks (`features/feature-marks.tsx`)

Each feature has its own mark, after Calendly's product icons: a small
piece of the feature's real screen on a squircle (a square with
continuous curves) in the feature's colour. The user picked each from
two rounds of sketches:

| Feature | Mark | Why it reads |
| --- | --- | --- |
| Resume Builder | A resume page, its last line in the full blue (the tailored one) | The thing the feature makes |
| Job Matching | A job card with the app's match ring as a badge on its corner | The ring is the match everywhere on the site; it is large enough to read at 24px, where a pill inside the card was not |
| Auto Apply | A stack of filled forms with a check | Many applications filled at once |
| Application Tracker | The tracker's list, a stage pill on each row (applied, interview, offer) | The tracker is a list; its board view is archived, so a board would show a screen students cannot find |

Rules: one colour family per mark, from the feature's token (the ground
at 24% over white, text-like bars mixed toward ink, white pieces on top);
drawn on a 48 grid; legible at 24px, the smallest size (`FeatureIcon`
`sm`; `md` is 36px). Generic glyphs on solid colour tiles (a file, a
target, a bolt, a kanban) came before, and the user found them generic.
The Resources menu still draws glyph tiles on one neutral colour.

### Tabs

The hero's feature tabs: a slate-at-5% track, the open tab a white pill
that slides (`layoutId`), each tab with its feature's mark (softer while
closed). Below sm only the open tab shows its label. The track is
`isolate`, so the pill's `-z-10` stays above the track's grey; without it
the pill painted under the grey and the open tab did not show.

## Motion

`frontend/CLAUDE.md` holds the rules (Pause Animations, reduced motion,
scroll performance). In short: stories loop only on screen and pause;
drifting rows (`.drift-row`) pause; reveals play once (`Arrive`); nothing
pins; no shine sweeps or glows.

Motion shows what the product does, in the order it happens: the hero's
tiles light up for a fit and their match bars fill as they do, the
journey's pictures play their step once. Every loop runs on opacity and
transform only (off the main thread), shares its element's cycle, and
joins the Pause Animations list; a number that counts up or a stroke that
draws would run on the main thread for the whole loop, so a fill is a
translate inside a clipped track.

## What was removed, and why

| Was | Now | Why |
| --- | --- | --- |
| `.glass-btn` violet gradient glass | `.primary-btn` solid ink | Read as AI-made; low contrast |
| Outline button with a violet edge | `SecondaryButton`, soft grey fill | Borders everywhere read as a template |
| Google light theme, grey border | Google neutral theme, no border | Bordered buttons looked AI-made; the dark theme was too heavy |
| Violet, blue and pink mesh gradient hero | A grid of square tiles that light up | Too close to Calendly's, no feel |
| A board of wide grey posting cards | Square tiles that light up | Less satisfying than the sketch of a grid |
| A grid capped at 84rem, features inside the hero | A one-screen hero filled edge to edge; features below | Bare grey margins on a wide screen; the next section showed |
| Glass tiles and a grainy ground, first turned down for solid violet lit tiles with white text on a flat brand-100 panel | Frosted glass tiles over a grainy violet ground (`.hero-ground`), lit tiles as bright glass cards in ink | The user did not like the solid cards and asked again; the cost worry did not hold (the blur reads a still ground: 8.4ms frames, none over 20ms) |
| Product rows that opened on a click, one "Explore" link by the heading | Calendly's rows: an icon and an arrow link per row to its deep dive | The user pointed back to Calendly |
| A sticky heading with the rows scrolling up beneath it | The whole section pinned at the screen's middle, the scroll opening one row at a time, a line filling under the open row | The section went to the top and then the list moved inside it, and a row's title was cut by the heading; the user found it broken |
| Ruled white lines across framed boxes | Grain only | Looked odd over the gradients |
| Generic glyphs on solid colour tiles (a file, a target, a bolt, a kanban) | Each feature's own mark: a piece of its screen on a squircle | Generic; the user pointed to Calendly's product icons |
| Blobs of a feature's colour and a second colour over its tint | A sky in one colour, light to deep, with a horizon band | Flat and muddy beside Calendly's boxes: no light, no direction |
| A violet label (eyebrow) above every section heading | The heading alone | Read as a template; the user had them all removed |
| 48px panel corners | Nested corners: 16px tiles, 28px cards and panels | Too round beside the tiles |
| Grey ground, white tiles, a lavender headline tile, pastel lit tiles with violet text | Violet ground, receding tiles, a white headline tile, lit tiles that stand out | Every surface at 94 to 100% lightness: no hierarchy, a loading-skeleton look |
| `.gloss-card`, white shading to lavender, violet shadows | `.surface-card`, white and slate | "The purple gradient on cards" |
| `.glass-card` tinted violet with a violet ring | Neutral frosted white | Same |
| Pricing's violet gradient Plus card and its shine | Solid ink card | Same; the shine was decoration |
| Pricing's gradient headline and violet capital pill | `TYPE.display`, `HERO_PILL` | One h1 and one pill on every page |
| Violet shadows on mock UI | `--mk-shadow-float` | Principle 1 |

Still violet on purpose: the hero's ground, checks, Job Matching's mark, Plus's limit pills, the billing toggle's selected tab, the "Save 20%" chip and the slop
word. The unmounted scenes (city hero, bridge, pinned tour, 3D pipeline,
applications route) keep their old styles; restyle one before it returns.
