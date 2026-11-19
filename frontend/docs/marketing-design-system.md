# Marketing design system (KAN-923)

The rules for every page in `app/(landing)/`: the home page, the feature
pages, Pricing, the Resources pages and the legal pages. Set 2026-11-19,
after the user found the site still looked AI-made (the violet glass
buttons, the bordered sign-up buttons, the lavender gradient on cards).
`home-page-review.md` has the Calendly review behind it. The app's own
screens follow `design.md`, not this file.

## Principles

1. **Colour lives in two places only**: the hero panel and the framed
   boxes (`StudioBox`). The page, its cards and its buttons are white,
   ink and grey. A violet card, a violet shadow or a violet-tinted white
   anywhere else reads as AI-made.
2. **One accent, used small.** WorkIt violet marks things: an eyebrow, a
   check, a feature's icon tile, Plus's limit pills, the slop word. It
   never fills a button, a card or a headline.
3. **Size carries hierarchy, not weight.** Every heading is weight 500;
   the steps of `TYPE` do the work.
4. **Motion stays in its box.** Nothing pins to the screen; a loop has a
   pause; a reveal plays once.
5. **Reuse before drawing.** Every role below is one class or one
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
| Hero ground | `.hero-mesh` | The home hero: violet, blue, pink and a warm glow over brand-50, with grain |

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
| `eyebrow` | Inter 600, capitals, 0.08em | 12 | The label above a heading |

No gradient text (Pricing's ink-to-violet headline went). No full stop on a
section heading; a hero line may keep one.

## Shape and space

- Radius: buttons `rounded-control` (the app's); cards 2rem; boxes 2rem;
  the hero card 2.5rem; panels `PANEL` (2rem, 3rem from lg); pills full.
- Width: `CONTAINER` (max-w-6xl); a reading column max-w-2xl; a chapter
  heading max-w-3xl.
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

Google's own dark theme: #131314 fill, 1px #8E918F inside stroke, #E3E3E3
Google Sans Medium, the full-colour G. LinkedIn takes the same treatment,
its tile with a white "in". Always followed by "Or sign up with email".
The light theme (white with a #747775 stroke) read as a bordered button
beside the ink primary, so it is not used here.

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
per box; the UI inside floats on it. The hero panel has the grain without
the lines.

### Pills and chips

- `HERO_PILL`: frosted white, `--mk-shadow-float`, the pill above every
  page's h1.
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

## What was removed, and why

| Was | Now | Why |
| --- | --- | --- |
| `.glass-btn` violet gradient glass | `.primary-btn` solid ink | Read as AI-made; low contrast |
| Outline button with a violet edge | `SecondaryButton`, soft grey fill | Borders everywhere read as a template |
| Google light theme, grey border | Google dark theme | Bordered buttons beside an ink primary |
| `.gloss-card`, white shading to lavender, violet shadows | `.surface-card`, white and slate | "The purple gradient on cards" |
| `.glass-card` tinted violet with a violet ring | Neutral frosted white | Same |
| Pricing's violet gradient Plus card and its shine | Solid ink card | Same; the shine was decoration |
| Pricing's gradient headline and violet capital pill | `TYPE.display`, `HERO_PILL` | One h1 and one pill on every page |
| Violet shadows on mock UI | `--mk-shadow-float` | Principle 1 |

Still violet on purpose: eyebrows, checks, feature icon tiles, Plus's limit
pills, the billing toggle's selected tab, the "Save 20%" chip and the slop
word. The unmounted scenes (city hero, bridge, pinned tour, 3D pipeline,
applications route) keep their old styles; restyle one before it returns.
