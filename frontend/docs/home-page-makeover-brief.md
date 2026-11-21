# Design brief: the home page makeover

Agreed with the user on 2026-11-20, one question at a time. It is the bar
for every later design decision on the page at `/`. It builds on KAN-923
(`home-page-review.md`, `marketing-design-system.md`); where the two
disagree, this brief wins, and the design system doc is updated to match
before the code that needs it.

## Goal

A student who opens the page signs up. The page must look made by a
design team: the user's words are "higher quality, more impressive, with
motion design, new elements and graphics, animations and proper
storytelling".

## Audience

Students who look for internships and new-grad roles. They have seen many
job tools that sell mass applying, on a laptop first and a phone second.

## The one impression

"WorkIt takes the boring parts of applying off me, so I can make each
application good."

Feels like: confident, crafted, alive. Must not feel like: AI-made, a
template, a tour of features.

## Material

- Lead with: the whole search in one app. The hero shows the four parts
  of a search (a resume, a match, a form, a tracker row) coming together
  round the headline.
- Move: the hero's tile grid of lit postings goes to the Job Matching
  page. It tells one product's story.
- Keep: the words (the headline, the section headings, the product
  lines; a line changes only where a layout needs a shorter one, shown to
  the user first) and the story's order (hero, what WorkIt is, the
  problems, why WorkIt exists, the four products, you stay in control,
  the hiring systems).
- Open to redraw: everything else, the problems hub and the four feature
  marks included.

## What is wrong now

The rules, not the skill. Each rule came from one thing the user
disliked, and each was right alone. Together they forbid the devices a
premium page uses: colour outside two places, any scene that fills or
holds the screen, any object that moves between sections. Also: the page
was built one section at a time with no storyboard, its pictures are
small mock screens, it has no art of its own, and its peak ("That's why
WorkIt exists") is an empty placeholder.

## References

- Loopsii (loopsii.com): take flat colour blocks and bold simple shapes;
  one object carried through the story; feature cards that stack as the
  page scrolls; hand-written side notes. Take them in WorkIt's own way.
- No second site. The difference from Loopsii comes from WorkIt's own
  material: the figure in the logo, the match ring, the resume page, the
  form, the tracker row. The shape set is designed from those.
- Avoid: a copy of Loopsii's layout, palette (lime, peach, sky) or faces.

## Rules lifted (the user's yes, 2026-11-20)

1. **Colour across the page.** Whole sections may sit on flat colour
   fields from a WorkIt palette built on violet and the four feature
   colours. Still no dark bands.
2. **Scenes that hold the screen.** A few sections may pin (hold the
   screen while a scene plays or cards stack), and a scene may fill the
   screen. Each move still plays to its end in time; nothing rests half
   way.
3. **A brand shape language.** Flat graphics made from a small set of
   shapes, in the hero, the tiles and the transitions.
4. **Objects that carry over.** An object may leave one section and land
   in the next as the page scrolls.

Rules that stay: the copy rules (quality, never volume; every claim true
to the app today; WorkIt never submits), violet as the brand colour, a
flat solid main button, slate shadows, everything still with reduced
motion, transforms and opacity only, loops stopped off screen, and the
speed budgets in `frontend/CLAUDE.md`.

## Where to be bold

The one big motion moment is the turn to WorkIt: the problems give way
to "That's why WorkIt exists", and the mess of a search is swept into
one app. The hero stays quick and clear. The other sections stay calmer.

## The demo frame

"That's why WorkIt exists" shows WorkIt's real screens (the Jobs page, a
resume, the tracker) drawn in code as a live scene. No recording is
needed; the scene is updated when the app's look changes.

## Constraints

Next.js 16, Tailwind v4, `motion` on the marketing route only. Checked at
1440 × 900, 1024 × 768 and 375 × 812, and with reduced motion. Below lg
a pinned scene becomes a still or a short timed scene. One KAN ticket
per pull request; no push without the user's yes.

## The direction: E, Grid (the user's pick, 2026-11-20)

The user saw five live directions. A (Blocks: a grid of flat colour
tiles with ink shapes), B (Thread: one violet line with the logo's dot),
C (Desk: tilted cut paper, a marker, Bricolage Grotesque) and D (a blend
of the three) came first. The user picked C, then asked for a blend,
then said A was still designed better. The reason, agreed: A is a
system (one grid, one corner, two layers) and C and D are collages, and
a system is what reads as made by a team. E is A as the base, with the
product put into its tiles and D's turn as the one big moment.

- **One grid.** Tiles of one corner (14px) and one gap (12px), at sizes
  of 1 × 1, 2 × 1 and 2 × 2 cells. Nothing rests tilted or overlapping.
- **Two layers.** A flat colour, then ink or white on it. No shadow on
  a tile and no gradient.
- **Four fields, one per product**: sky (Resume Builder), lilac (Job
  Matching), mint (Auto Apply), rose (Application Tracker), each with a
  pale step for a plain tile. The ground is the grey mist or white.
  Violet is for the app icon tile, the line and the main button.
- **The product is in the tiles**, flat and straight: a resume sheet
  with a reworded line, a match with its band and number, a form with
  Submit, tracker rows.
- **Ink marks.** Each product has one bold ink shape, drawn from its
  feature mark (a sheet, the match ring, form bars, a table).
- **Type.** Plus Jakarta Sans stays. A pen face (Nanum Pen Script)
  writes a few side notes, never a heading or a claim.
- **The line** shows in the turn only: a grey tangle through the
  problems that the logo's dot pulls straight, in violet.
- **Colour comes with WorkIt.** The problems are grey tiles; they take
  their colours as they snap into the app.

Turned down with C and D: Bricolage Grotesque, marker yellow, tilted
paper with shadows, and a rail beside the product cards.

## Storyboard

| Section | Ground | What it shows | What moves |
| --- | --- | --- | --- |
| Hero | Mist panel | The headline on the left; on the right a mosaic of tiles with the four products' pieces round the violet icon tile | Tiles snap to the grid on load, the icon tile last |
| Logo strip | White | Real employers | The slow drift, as today |
| What is WorkIt | White | The icon tile beside the large line | Words read in |
| The problems | Dim grey | Six grey problem tiles and the 81% figure, on a tangled grey line | Tiles arrive; nothing loops |
| The turn | Grey to white | "That's why WorkIt exists" over the app, built from the same tiles | The page's one big moment: the dot pulls the line straight, the tiles snap into the app and take colour |
| One app for every step | White | Four product tiles with ink marks | Tiles pop in order |
| The four products | White | Four large cards, half words and half a product piece on its field | Cards stack as the page scrolls |
| You stay in control | White | Two tiles: Nothing invented, Your words win | Each plays once |
| Hiring systems | Mist | A tile grid of the systems' logos | None |

## Open questions

- The tile grid of lit postings: where it goes on the Job Matching page.
- What is WorkIt's 3D glass icon (the user's ask, 2026-11-20) against a
  flat icon tile: ask before changing it.
