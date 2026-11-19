# Marketing design system (KAN-923)

The rules for every page in `app/(landing)/`: the home page, the feature
pages, Pricing, the Resources pages and the legal pages. Set 2026-11-19,
after the user found the site still looked AI-made (the violet glass
buttons, the bordered sign-up buttons, the lavender gradient on cards).
`home-page-review.md` has the Calendly review behind it. The app's own
screens follow `design.md`, not this file.

## Principles

1. **Colour lives in two places only**: the home hero (its violet headline
   tile and the tiles that light up) and the framed boxes (`StudioBox`). The page, its cards and its buttons are white,
   ink and grey. A violet card, a violet shadow or a violet-tinted white
   anywhere else reads as AI-made.
2. **One accent, used small.** WorkIt violet marks things: a
   check, a feature's icon tile, Plus's limit pills, the slop word. It
   never fills a button or a card. The one exception is the home hero's
   lit tiles, a soft solid violet (`--mk-lit`) with white text.
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
6. **Motion stays in its box.** Nothing pins to the screen; a loop has a
   pause; a reveal plays once.
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
| Panel ground | `.panel-ground` (brand-100) | The home hero's and the features section's panels |
| Empty tile | white at 55%, no edge | The hero's tiles that are not lit; they recede |
| Headline tile | `.hero-copy`: white, a soft violet shadow | The hero's brightest surface; ink text, the Google pair on it |
| Lit tile | `--mk-lit` (#6c56b2, the brand's hue at less chroma) deepening downward, a light top edge, a drop shadow, a 4px glow into the gaps and a faint grain; white text (85% white for second lines) | The hero's fits; the only saturated colour in it. The brand itself was too strong and shifted the rings' green toward cyan |

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

The first screen and nothing else: a pale violet panel the screen's
height, filled edge to edge by tiles. The headline sits in one large white
tile in the middle, the brightest surface. Empty tiles recede at 55% white;
seven tiles light up in turn in a soft solid violet (`--mk-lit`), with a real employer,
the role and the match's strength in the app's bands ("Excellent Match"
or "Good Match", from `lib/match.ts`) behind the app's own 14px match ring
(`MatchGlyph`), drawn on the violet with the bands' light steps
(`--color-match-*-on-fill`, 3.3 to 4.3:1 there)
over a slim white bar that fills, the percentage at its end, set in the
Jobs page job card's weights (role medium, company regular, band
semibold) in white. A match anywhere on the marketing pages says its band
first: a bare number does not tell a student whether to apply. Columns follow the screen's shape so the tiles stay
near square. The four features follow below, in their own section.

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

The frame for every picture and animation: radius 2rem, a feature's
`studioGround`, faint ruled lines and grain (`.studio-box`). One picture
per box; the UI inside floats on it.

### Pills and chips

- `HERO_PILL`: frosted white, `--mk-shadow-float`, the pill above a
  feature page's, Pricing's and a Resources page's h1. The home hero has
  none (the user had it removed).
- A feature chip: `FeatureIcon` plus the feature's name, ink text.
- Status chips (the closing row): white, a logo, a label, the company in
  meta grey.
- `SoonChip` for anything not built yet.

### Tabs

The hero's feature tabs: a white-at-50% track, the open tab a white pill
that slides (`layoutId`), its icon in the feature's colour. Below sm only
the open tab shows its label.

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
| A board of wide grey posting cards | Square tiles, soft violet when lit | Less satisfying than the sketch of a grid |
| A grid capped at 84rem, features inside the hero | A one-screen hero filled edge to edge; features below | Bare grey margins on a wide screen; the next section showed |
| Glass job tiles and a grainy mesh ground (asked for) | Tactile lit tiles with grain on the solid colour, and one stage light behind the headline | Glass had nothing behind it to blur and would redraw every frame; grain in thin gaps reads as dirt |
| A violet label (eyebrow) above every section heading | The heading alone | Read as a template; the user had them all removed |
| 48px panel corners | Nested corners: 16px tiles, 28px cards and panels | Too round beside the tiles |
| Grey ground, white tiles, a lavender headline tile, pastel lit tiles with violet text | Violet ground, receding tiles, a white headline tile, solid violet lit tiles with white text | Every surface at 94 to 100% lightness: no hierarchy, a loading-skeleton look |
| `.gloss-card`, white shading to lavender, violet shadows | `.surface-card`, white and slate | "The purple gradient on cards" |
| `.glass-card` tinted violet with a violet ring | Neutral frosted white | Same |
| Pricing's violet gradient Plus card and its shine | Solid ink card | Same; the shine was decoration |
| Pricing's gradient headline and violet capital pill | `TYPE.display`, `HERO_PILL` | One h1 and one pill on every page |
| Violet shadows on mock UI | `--mk-shadow-float` | Principle 1 |

Still violet on purpose: the panel ground, the hero's lit tiles, checks, feature icon tiles, Plus's limit pills, the billing toggle's selected tab, the "Save 20%" chip and the slop
word. The unmounted scenes (city hero, bridge, pinned tour, 3D pipeline,
applications route) keep their old styles; restyle one before it returns.
