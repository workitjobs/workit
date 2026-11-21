# Design brief: the home page makeover

**Status (2026-11-21): narrowed to the hero.** The user saw the first
makeover hero built in the page and found it off beside the untouched
sections, then asked to keep everything from the logo strip down and to
redraw only the hero, in the site's own grid look, showing the whole
pipeline. That hero is built (`hero-pipeline.tsx`). The rest of this brief
is the record of how the work got there; "What happened" at the foot has
the short version. The four rules it lists as lifted were not used: the
page below the hero still follows `marketing-design-system.md` as written.

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

## What happened

1. **Five directions, as one live page** (2026-11-20). A (Blocks: a
   grid of flat colour tiles with ink shapes), B (Thread: one violet line
   with the logo's dot), C (Desk: tilted cut paper, a marker, Bricolage
   Grotesque), D (a blend of the three) and E (A as the base, with the
   product in its tiles and a turn scene). The user picked C, asked for a
   blend, found A better designed (a system: one grid, one corner, two
   layers; C and D read as collages), and picked E.
2. **E's hero, built** (commit 206903dc): a grey panel with a mosaic of
   pastel tiles and pen notes. In the page, above sections still in the
   site's own look, the user found it off.
3. **The scope narrowed** (2026-11-21, the user's words): everything
   from the logo strip down is untouched and stays, "which is good
   because I still want all of that"; make "a new hero that matches the
   grid feel of our website and captures the whole pipeline".
4. **The hero now**: the headline centred in the drafting grid's frame,
   and under it the pipeline as four cells of that grid, one per product,
   each a `StudioBox` on the product's sky with one application's scene.

What it taught:

- **A direction is judged in the page, not alone.** Each prototype
  looked right on its own sheet. The built hero sat above eight sections
  in another look and read as a different site. Show a new section in
  the real page, between its real neighbours, before more is built on it.
- **A makeover of one section uses the site's language.** A new look
  needs the whole page; one section in it reads as a mistake.
- **The rules were not the limit.** The first answer in this brief
  blamed the rule set. The hero the user accepted breaks none of the
  rules: it uses the drafting grid, the framed boxes and the feature
  marks the page already had.

## Open questions

- The grid of lit postings (`hero-board.tsx`, unmounted): whether it
  goes on the Job Matching page.
