# The resume editor's Getting Started walkthrough

Built 2026-11-18. Code: `src/app/(seeker)/resumes/[resumeId]/walkthrough.tsx`
(the path and each step's cards), `walkthrough-model.ts` (the pure half: the
steps, counts, the practice examples; tested in `walkthrough-model.test.ts`)
and `src/components/tour.tsx` (`CoachMark`).

## How it got here

1. **A fixed tour, one action per section** (2026-11-17): add a school, a job
   or project, skills, then Format, Fit and Download. The user found it not
   thought through: each step ended once one entry saved, so it assumed one
   school, one job and one project; its Format step left the Sections tab
   open; nothing said what a panel was for; typing on the page was never
   shown; Add Experiences was never tried (and is empty for a new student);
   Fit to One Page was named, never seen; the entry form had no help; and an
   upload got no walkthrough at all.
2. **A checklist of nine places to start**, in any order (2026-11-18). Taken
   out the same day: it asked a new student to choose before they knew the
   editor. A walkthrough starts at the top and goes down.
3. **One path down the page, header first** (2026-11-18, this). Each card is
   a line or two, and a pointing hand taps the control to press (`beacon`)
   rather than being named in words: people will not read long cards.

## Where it runs

- **Onboarding** runs it on the resume it made (`MadeReview`'s `tour`), for
  "No, build one for me" and for an upload, which opens as an editable copy
  (`startFromResume`; the file alone is the fallback when no copy can be
  made).
- **The title row's ⋯, Take the Tour**, runs it on any built resume's page
  (`TitleRowProvider`'s `attachTour`). Never on Tailor's review.
- **From 64rem only** (`useTourFits`). The phone editor's header row says to
  open the panel instead.

## The path

`CHAPTERS`, in the page's own order. The card opens with a brand status
badge, "Step 3 of 9" (`Badge`): a grey "Step 3 of 9 · 1 job" line read as a
stray caption, and its count repeated the title ("1 job added"), so the count
is the title's alone. End Tour leaves at any step.

| Step | Opens | Card | Ring on | Moves on |
| --- | --- | --- | --- | --- |
| Check your details | Sections, the Header open | The top of your resume; fix anything wrong | | Looks Right |
| Add your schools, experience, projects | Sections, that section open | One line on what goes there; then "2 jobs added · Add another, or move on" | The section's + | Skip, or Next once there is one |
| Add your skills | Sections, Technical Skills | Languages and tools; Enter after each | The first + | Skip, or Next |
| Reuse what you've saved | Add Experiences, every group open | Tick one; then its arrow picks the bullets | The first box | A tick, then Next |
| Edit on the page | The page, its first title or bullet lit | Click this line; then Enter saves, the arrows move it, Undo | | A line opened, then Next |
| Format the page | Format | Fonts, spacing and layout; try Body Text; Reset puts it back; Fit to One Page, with a picture | Body Text's + | A size changed, then Next |
| Download it | Download | PDF or Word; WorkIt saves as you go | | Finish |

Rules the steps keep:

- **One path, top first.** No list of places to start.
- **Never assume one entry a section.** A section's step stays open while
  the student adds as many as they have, counting them ("3 jobs added"), and
  moves on only on Next.
- **Show, do not tell.** A card is a line or two; on the control to press,
  a pointing hand (the cursor a browser shows over a link, white under an ink
  outline) glides in, its fingertip taps the control's middle, and a thin
  ring spreads from the tap to just past the control's edge and fades
  (`animate-coach-hand`, `animate-coach-wave`, one 1.6s beat; the hand still,
  with no ring, under reduced motion). A ping that grew to twice the control
  read as far too big (2026-11-18), and an arrow cursor and then a dot alone
  were not the hand the user asked for. A lit section shows its row's actions without a hover, the Skills
  groups' + too (`lit`, `shown`).
- **Let them try it**, and move on when they have (`advance`), 700ms after,
  so they see their action land first; a Skip is always there. Moved on in
  the same frame, a clicked line's step changed before the line had opened,
  which read as a jump.
- **Smooth from step to step.** One card for the whole walk glides with the
  lit box (300ms) and its words fade in; a step scrolls only when its control
  is off screen, smoothly, with the box and card faded out while it runs and
  back in where it lands. A card per step snapped to each new place, and an
  instant scroll on every step moved the page under a gliding box, which read
  as erratic (2026-11-18). A control taller than half the window (the Header,
  a whole panel) counts as on screen once its top is in the window's upper
  third: judged whole, a panel a few pixels taller than the window faded out
  for a scroll that went nowhere. The check runs at once, so a step that
  must scroll fades out before its box starts toward the old place.
- **Practice where a new student has nothing.** Add Experiences shows
  `SAMPLE_BANK` (an example job, an example project and three skills, each
  named as an example) under a "Practice: these are examples" notice, groups
  open, ticked on screen through `mergeChoices` and never sent to the API,
  while the step runs and the student has no saved entry or skill. A student
  with saved experiences practises on their own. Examples never print.
- **A tool not on screen yet** (Fit to One Page) gets a picture in its card
  (`OnePageArt`), not a fake run on the real resume.
- **Help where the work happens**: while a section's step runs, its entry
  form shows a writing tip under its title (`ENTRY_TIPS` in `editor.tsx`,
  `OutlineEntryDialog`'s `tip`), since the coach mark steps aside while a
  dialog is open.
- **Onboarding never scrolls sideways** (`overflow-x-clip` on its root):
  Scout's panel beside the editor widened the page, and the Header row's
  scroll into view slid the whole screen 358px left.

## The coach mark

`CoachMark` is controlled: the screen passes the target, the ring, the words
and the buttons, and decides when to move on. It dims all but the lit control
(the lit box's own shadow, so every control still works), places its card
beside it, steps aside while a dialog is open, and is not drawn below 64rem.
A target is `data-tour` names (several lit as one), or a selector for a
control with none (a line on the page, `[data-box$=".bullet"]`), with a
fallback. **The lit box glides only from one step to the next** (for 350ms
after the step changes) and otherwise sticks to its control every frame:
with the glide always on, it trailed the control by 300ms and slid about.
**The screen holds still while a step shows** (2026-11-18, the user's
call): the wheel and a touch drag scroll nothing, since a scrolled panel
carried the lit box and its card up with it. Each step instead scrolls its
own control into view as it opens (the ring's, else the lit one): a short
one to the middle of its panel, one taller than half the window (the
Header's fields) to the top. At 1440 x 800 the Header fits whole; Format's
Reset Formatting, a line on the page and a long list of saved experiences
are the ones it scrolls to. A dialog a step opened (the entry form) scrolls
as ever. **Still open:** on a window under about 740px tall the Header's
last fields (Other Link, Additional Line) run past the foot and cannot be
reached until Looks Right.
`docs/design.md`, "A tour points; it never blocks", has its look.

## Still open

- The upload path's copy is untested in the browser (no sample file in the
  worktree, and a real one would go to the shared database).
- Leadership, Awards, Certifications and custom sections have no step; their
  + works the same way.
