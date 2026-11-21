# Marketing design system (KAN-923)

The rules for every page in `app/(landing)/`: the home page, the feature
pages, Pricing, the Resources pages and the legal pages. Set 2026-11-19,
after the user found the site still looked AI-made (the violet glass
buttons, the bordered sign-up buttons, the lavender gradient on cards).
`home-page-review.md` has the Calendly review behind it. The app's own
screens follow `design.md`, not this file.

## The makeover narrowed to the hero (2026-11-21)

For a day (2026-11-20) the user lifted four rules for a home page
makeover after Loopsii: colour across the page, scenes that hold the
screen, a brand shape language, and objects that carry between sections.
A hero in that look was built, and in the page, above sections still in
this system, the user found it off. The user then kept everything from
the logo strip down and had only the hero redrawn in this system. **So
every rule below is in force**, and the lifted four were never used.
`home-page-makeover-brief.md` has the record and what it taught: a new
look needs the whole page, and one section in it reads as a mistake.

## Principles

1. **Colour lives in the framed boxes** (`StudioBox`), the home hero's
   four included (it was two places: the old hero had a grainy violet
   ground under glass tiles, off the page since 2026-11-21). The page and its cards are white,
   ink and grey, and so are its buttons but the main one, which is solid
   WorkIt violet, flat (the user's pick, 2026-11-20). A violet card, a violet shadow or a violet-tinted white
   anywhere else reads as AI-made. **One exception, the four product
   tiles** under "One app for every step of applying" (`FeatureJumps`,
   the user's call, 2026-11-20): each is flat in its feature's pale
   tint, its colour mixed 9% into white (14% on hover), the same share
   for all four so none stands out, and its mark ringed in white with a
   slate shadow so the mark's pastel squircle stands off the tint. Grey,
   the four read as alike. Never a fade to white: a colour washing to
   white was the option the user turned down as AI-made. The logo is
   violet wherever it shows, and What is WorkIt draws it as an app icon
   (`AppIcon`, the user's asks, 2026-11-20): a thin slab of glass tilted
   in 3D and floating over a slate shadow, its face a violet squircle lit
   from above with a frosted sheet and the white figure, its edge deeper
   violets.
2. **One accent, used small.** WorkIt violet marks things: a
   check, Plus's limit pills, the slop word. It
   never fills a button or a card. Two exceptions: the home hero's
   ground, the page's one large field of violet, and a selected item in a
   set the visitor clicks through, whose fill is the pale `brand-tint`
   (its glyph on solid `brand`, no edge), as a selected row is in the app.
   The problems hub's open card used it until the hub moved onto the dark
   band, where it read as off theme; there the open card is solid white
   (the user's calls, 2026-11-20).
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
| Feature colours | `features/catalog.ts` (`tint`, `glow`, `onGlow`): blue (Resume Builder), peach (Job Matching, `--color-matching`), green (Auto Apply), pink (Application Tracker) | Inside that feature's box and on its mark. No feature is violet: violet is the brand's (2026-11-21) |
| Hero ground | `.hero-ground`: deeper violets in the corners, lighter along the edges, a pale pool behind the headline, grey noise in overlay | The home hero's panel; one hue family |
| Empty tile | `.hero-tile`: frosted glass (a faint white, a 14px blur, a white hairline, a brighter top edge) | The hero's tiles that are not lit |
| Headline tile | `.hero-copy`: solid white, a slate shadow | The hero's brightest surface and its one tile that is not glass; ink text, the Google pair on it |
| Lit tile | `.board-lit`: near-white glass over the tile's frost, a white edge, a slate shadow; ink text, the match in the app's own colours | The hero's fits |

Shadows are slate, never violet: `--mk-shadow-card` for a card resting on
the page, `--mk-shadow-float` for UI floating over colour (a mock card in a
box, a chip, a pill, a white button on a fill).

## Type

`TYPE` in `layout-parts.tsx`. Plus Jakarta Sans for headings, Inter for
everything else. A product's heading was Newsreader, the site's only
serif; the user found it fancy and out of place (2026-11-20), so it is
Jakarta too and the face is gone.

| Step | Face | Desktop / phone | Use |
| --- | --- | --- | --- |
| `display` | Jakarta 500 | 72 / 40 | A page's h1 (home, feature, Pricing, Resources) |
| `chapter` | Jakarta 500 | 56 / 34 | `SectionHeading` (hiring systems' too), the closing call to action, the statement |
| `product` | Jakarta 500 | 44 / 30 | A product section's h2 only, two lines at every width (30 to 40 characters, 12em) |
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
| Primary | `PrimaryButton` (`.primary-btn`) | Solid WorkIt violet, flat, white label, a step deeper on hover; never a gradient, glass or glow. It ends in an arrow on a small flat square tile, the grid's square; on hover the arrow leaves right as a second comes in from the left (2026-11-21) |
| Secondary | `SecondaryButton` | Slate at 6%, ink label, no border |
| On a fill | `OnFillButton` | White, ink label, `--mk-shadow-float`, no border |

Two heights only: `md` 44px, `lg` 48px. The header's Get started and Open
WorkIt are primary; Log in is secondary. No glass, no gradient, no
outline.

### The header (`header.tsx`, `floating-header.tsx`)

The drafting grid's top row (2026-11-21). It spans the window: clear at
the page's top, white with a blur and a hairline along its foot once the
page scrolls. On a page that draws the grid, from lg up, the hairline
shows at the top too, the grid's rails run through the bar, and an ink
square marks where each meets the foot; the home hero's frame hangs from
that line. A page with no grid gets the bar without the marks. It was a
rounded white panel with a shadow, inset from the window, which read as
another site's bar. Its menu panels are solid white with a
hairline edge and a deep, close shadow, and hang 8px under the foot line:
at 90% white with a blur and a 5% edge, made for a coloured hero, a panel
was white on white over the white page (the user's catch, 2026-11-21).

### The sign-up pair (`social-sign-up.tsx`)

Google's own neutral theme: #F2F2F2 fill, no stroke, #1F1F1F Google Sans
Medium, the full-colour G. LinkedIn takes the same treatment, its tile
with a white "in". Always followed by "Or sign up with email". It is the
guidelines' only theme with no border: the light theme (white with a
#747775 stroke) read as a bordered button, and the dark theme was too
heavy. The soft grey matches `SecondaryButton`, so Download for Mac
(KAN-922) sits in the same row as a `SecondaryButton`.

### The home hero's pipeline (`hero-pipeline.tsx`)

The first screen: the headline, its line and the sign-up pair centred on
the white page, in the drafting grid's frame, and under them the whole
pipeline as four cells of that grid, one per product in the order a
search meets them (Resume Builder, Job Matching, Auto Apply, Application
Tracker). A cell is the product's mark and name over one `StudioBox` on
the product's own sky, the same sky its section uses further down, so the
hero reads as the page's contents.

- **One application runs through all four** (`followedJob`): its resume
  reworded, its match, its form with Submit left to the student, its row
  in the tracker.
- **It plays in turn**: a line in the product's colour fills along the
  cell's top rule (the product rows' fill line), the cell's scene plays
  once, the next cell starts, and after the fourth one turn rests; at
  its end all four fade clear together, so a loop never starts beside
  full cells. CSS
  only, opacity and transform, stopped off screen, finished and still
  with reduced motion.
- **The entrance draws the grid, with no fades** (the `load-*` rules in
  landing.css): the header's foot line grows from the centre and
  uncovers the header, the words rise from behind their own foot, the
  rails draw, the ink squares pop as lines reach them, each cell is
  dragged out from its corner like a frame in a design tool with an ink
  square as its handle, and the loop starts, about 1.7s. A
  clip and a translate, never opacity or a blur: a fade-in reads as
  AI-made. Never a loading screen.
- **The grid is the page's**: the frame is `DraftLines` (`first`: it hangs
  from the header's foot line, which the header draws), and the
  cells' rule and dividers are the same hairline with the same ink
  squares at each crossing.
- **Scenes are in em**: drawn at 252 × 201px, scaled by the box's own
  width, so a phone's 165px box holds the same picture. Below lg the
  cells are two by two and the lines are off.

Why it has this shape: it replaced a tile grid that told Job Matching's
story alone, and then a mosaic in another look (above). A hero built
from this system's own parts needed no new rule.

### The old home hero's grid (`hero-board.tsx`, unmounted)

Off the home page since 2026-11-20: it told Job Matching's story alone.
Kept in the folder; it may go on that product's page.


The first screen and nothing else: a grainy violet panel the screen's
height, filled edge to edge by frosted glass tiles. The headline sits in
one large solid white tile in the middle, the brightest surface.
Postings light up as bright glass cards one at a time, each on a
different tile in a shuffled order (never two neighbours, never the same
posting twice in a row) that starts at a random tile each visit, the
first 1.5 s after load, each a real employer, the
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

The frame for every picture and animation but one (the problems' visuals
stand on the grey band's stage under a slate dot grid that fades toward
the middle, `.problem-dots`: they show the search as it is, not a WorkIt
feature, so they take no feature's sky; the user's calls, 2026-11-20,
the dots picked from six patterns over a flat stage that read as
boring): 16px corners, a feature's
`studioGround` (a blend of neighbouring colours since 2026-11-21,
after the user's reference: the feature's colour, a neighbour hue pooled
in the lower left, another in the upper right, a pale streak between;
one colour fading to white read as AI-made; at pastel strength, 46% of
each colour over white, the user's pick over full strength, which was
louder than the headline) and no grain (the user had it removed once the
grounds were pastel)
(`.studio-box`, grey noise in overlay; ruled lines across it were
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

### The drafting grid (`draft-lines.tsx`, `.draft` in landing.css)

Faint slate hairlines with a small ink square where they cross, as a
drawing's registration marks, after Loopsii's frames (the user's picks,
2026-11-20: first for the tools collapse, then "grid frame everywhere").
Every section between the hero and the footer is framed: What is
WorkIt, That's why WorkIt exists, "One app for every step of applying"
and its four tiles, each product section,
You stay in control and the hiring systems' box. Each frame is two lines
across the window at the block's top and foot and two down its sides.

- **One rail.** Every frame's sides sit 1.5rem outside the container's
  content, so the side lines run in one line down the page, and they run
  6rem past each frame, so the rail joins across the gap between two
  framed sections. At different offsets the sides jumped from section to
  section, and at 2.5rem the rail broke between the product sections.
- **It takes no room.** `DraftLines` is absolutely placed `gap` above
  and below its block, inside a `relative` parent that spans the
  container's width; nothing shifts, and the problems section still fits
  one screen. Content the frame sits behind must be positioned
  (`relative`), or the absolutely placed lines draw over it.
- **From lg up.** Below it the side lines ran along the window's edge.
- **Neutral**, never a feature's colour. The hero's frame is the page's
  first (`DraftLines first`): its side lines start at its top line, where
  every other frame's run 6rem above to join the frame before, since up
  there they crossed the header. The hero's own cell lines (`.pipe-lines`)
  use the same hairline and squares.

### The grey band (`problems.tsx`)

One light grey band, the problems of a search: flat `--mk-mist`
(#f0f0f0), a step below the white page, with no glow and no grain
(`.problems-ground`), never a feature's colour. It has an ink heading and
a grey line, the hub's cards white with the card shadow (the open one
solid ink with white words, the band's colours turned over), the stage
white at 60% under a slate dot grid, its one texture, and the figure as
an outlined strip with no fill, its number in ink. **It was dark for a
day** (2026-11-20): the ink with a slate pool and dots read as the stock
dark section of an AI-made site, and a flat near-black then read as out
of nowhere, the one dark block between two white sections (the user's
catches). The footer went light grey with it, the same `--mk-mist`, so
the page has no dark block. It is the search
before WorkIt, the chapter the product sections answer. From lg up it
zooms in as it rises (`GrowIn`, from 80%) while What is WorkIt above
fades and shrinks a little, both scroll-linked opacity and transforms;
never a blur, which would rest half on. Its frame breaks the drafting
grid's rail: the band is the rail's pause.

### The demo's glass frame (`.demo-glass`, `why-exists.tsx`)

The product demo stands in a frosted white bezel with a bright top edge
and a white rim, inside a `StudioBox` on WorkIt's violet sky, so the blur
has colour to show and the page's colour stays inside a box. The screen
is a placeholder until a recording exists, named as coming soon.

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
three rounds of sketches:

| Feature | Mark | Why it reads |
| --- | --- | --- |
| Resume Builder | A resume page, its last line in the full blue (the tailored one) | The thing the feature makes |
| Job Matching | The app's match ring, its arc at 91% in the match's green, with a check inside | The match itself, the ring a student sees on every job card (the user's pick, 2026-11-20); 91% is the followed Stripe application's match. A card with the score over two ticked skills held too much to read as matching, and a job card with a ring badge read as off |
| Auto Apply | A grid of four forms, three filled and checked, the last still filling | Several applications filling at once (the user's pick, 2026-11-20); a stack of forms with one check came before, and its faint back forms read as one form |
| Application Tracker | A table: a header row, column lines and a status column of stage pills (applied, interview, offer) | The tracker is a spreadsheet of applications; a list of rows with pills read as off, and a board would show the archived board view |

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

`frontend/CLAUDE.md` holds the rules (reduced motion, scroll
performance). In short: stories loop only on screen; reveals play once
(`Arrive`); the product sections' rows turn on a timer that a click
stops; no shine sweeps or glows. Nothing pins or follows the scroll frame
by frame but the entrances (`GrowIn`'s scale, What is WorkIt stepping
back). A pinned tools collapse into the four product tiles was built and
taken out the same day (2026-11-20): the user found its examples in the
way.
There is no Pause Animations button since the user had it removed, which
leaves WCAG 2.2.2 open (frontend/CLAUDE.md says what).

Motion shows what the product does, in the order it happens: the hero's
tiles light up for a fit and their match bars fill as they do, the
journey's pictures play their step once. Every loop runs on opacity and
transform only (off the main thread) and shares its element's cycle; a
number that counts up or a stroke that
draws would run on the main thread for the whole loop, so a fill is a
translate inside a clipped track.

## What was removed, and why

| Was | Now | Why |
| --- | --- | --- |
| `.glass-btn` violet gradient glass | `.primary-btn` solid ink, then solid flat violet | Read as AI-made; low contrast. Ink went once it was the page's only dark mark |
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
| The journey ("One application, start to finish"), the statement, the home page's closing section | Applying as it is (`problems.tsx`: on the page's one dark band, six problems, three on each side of one large visual on a stage under a fading dot grid, and one sourced figure as an outlined strip), You stay in control (`control.tsx`) | The four features three times over and no why; a page should say who it is for and what it fixes before how |
| Blobs of a feature's colour and a second colour over its tint | A sky in one colour, light to deep, with a horizon band | Flat and muddy beside Calendly's boxes: no light, no direction |
| A violet label (eyebrow) above every section heading | The heading alone | Read as a template; the user had them all removed |
| 48px panel corners | Nested corners: 16px tiles, 28px cards and panels | Too round beside the tiles |
| Grey ground, white tiles, a lavender headline tile, pastel lit tiles with violet text | Violet ground, receding tiles, a white headline tile, lit tiles that stand out | Every surface at 94 to 100% lightness: no hierarchy, a loading-skeleton look |
| `.gloss-card`, white shading to lavender, violet shadows | `.surface-card`, white and slate | "The purple gradient on cards" |
| `.glass-card` tinted violet with a violet ring | Neutral frosted white | Same |
| Pricing's violet gradient Plus card and its shine | Solid ink card | Same; the shine was decoration |
| Pricing's gradient headline and violet capital pill | `TYPE.display`, `HERO_PILL` | One h1 and one pill on every page |
| Violet shadows on mock UI | `--mk-shadow-float` | Principle 1 |

Still violet on purpose: the hero's ground, checks, Plus's limit pills, the billing toggle's selected tab, the "Save 20%" chip and the slop
word. The unmounted scenes (city hero, bridge, pinned tour, 3D pipeline,
applications route) keep their old styles; restyle one before it returns.
