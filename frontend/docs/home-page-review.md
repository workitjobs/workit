# Home page review: Calendly and WorkIt (KAN-923)

KAN-923 (Redesign the marketing home page's hero, type and sections).
Written 2026-11-19. It records what we saw on Calendly's home page, what
reads as AI-made on WorkIt's, and the direction for the new page. We
study Calendly; we do not copy it.

How we looked: Chrome at 1200 × 637 (desktop) and at 606 × 667, the
narrowest window Chrome allows (Calendly's phone layout is on at that
width: its h1 drops to 40px). We scrolled the whole page, took
screenshots, and read sizes and faces from the computed styles. WorkIt
was `npm run dev` on this branch at 1280 × 800.

## 1. Calendly's home page

### Type: three faces, each with one job

| Role | Face | Desktop | Phone | Weight | Tracking |
| --- | --- | --- | --- | --- | --- |
| Hero h1 | Calendly Sans (geometric sans) | 72 / 79 | 40 / 44 | 500 | −2px |
| Section intro h2 (centred) | Calendly Sans | 60 / 66 | 36 / 40 | 500 | −2px |
| Product section h2 (left) | **Wulkan Text (serif)** | 48 / 53 | 28 / 31 | 500 | −2px |
| Hero card h2, stat h3 | Geist | 36 / 40 | 24 / 26 | 500 | −1px |
| Stage card h3 ("Book", "Prep") | Calendly Sans | 28 / 34 | | 500 | 0 |
| Feature list item | Calendly Sans | 20 / 28 | | 500 | 0 |
| Lead paragraph | Geist | 18 / 25 | | 400 | 0 |
| Body | Geist | 16 / 22 | | 400 | 0 |
| Eyebrow ("AI MEETING MANAGEMENT") | sans, capitals | ~12 | | 500 | wide |

- The "slightly decorative" heading is the serif, Wulkan Text, at weight
  500. It heads only the four product sections ("A better way to book
  your meetings") and the customer quotes. Each sans heading is a
  chapter; each serif heading is a product.
- Every heading weight is 500, not 600 or 700. The size steps carry the
  hierarchy: 72, 60, 48, 36, 28, 20.
- Headings are navy (#071A31), body is slate (#5F6D77), on a warm
  off-white page (#FCFBF8), not pure white.

### Hero: the top features are in the hero

- Headline, one line of copy, Google and Microsoft sign-up, "Sign up
  with email · No credit card required". The headline does not move.
- Under the buttons, still inside the hero's gradient panel: a row of
  four product icon tabs (Scheduling, Callie, Notetaker, Payments) with
  arrows, and one white card (920 × 409, radius 48) for the picked one:
  a product chip with a "New" or "Beta" badge, an h2, two lines, Learn
  more, and on the right a framed animation (448 × 289, radius 20) on
  that product's tint. The card changes by itself; the tabs are
  `aria-selected`.
- The hero panel is inset 24px from the window, radius 64, 1152 wide.
  It is about 1.8 screens tall because it holds the card, so the
  features show on the first scroll.

### Each section leads into the next

1. Hero: four products, one at a time.
2. "Built for people whose work runs on meetings": a centred intro, then
   four wide stage cards (1072 × 275, radius 48), Book, Prep, Capture,
   Follow up, each with three steps on a small timeline and a framed
   picture on the right. The cards are joined by a grey connector, so
   they read as one client's day.
3. One section per product, in the hero's order (Scheduling, Callie,
   Notetaker, Payments): product chip, serif h2, then a list of
   sub-features beside one 424 × 424 framed box (radius 64). The box
   swaps to the sub-feature that is open. The box alternates sides.
4. "Real customers. Real results.": a gradient band, quote cards with a
   number as the h3 and a serif quote.
5. Integrations: a grid of logo tiles, then two cards.
6. "From the first meeting to the follow-up": the closing call to
   action, which repeats the hero's promise, over a row of photo cards.
7. A dark navy footer panel.

The thread: the hero names the products, the stage cards show them
working together, the product sections go deep, proof follows, and the
close repeats the promise. Sections are 96px top and bottom on the same
off-white, so the rhythm is even.

### Animation sits in boxes

- No section pins to the screen and none fills it. Every moving thing
  is inside a framed, rounded box: 448 × 289 in the hero card, 424 × 424
  in the product sections, small pictures in the stage cards.
- The box has its own tint or gradient and a white UI card floats in it
  (a calendar, a recap, an email). The page around it is still.
- Text reveals are light: a product heading fades from grey to navy as
  it comes in; lists fade up.
- On a phone the hero card stacks (copy over the box), the stage card
  puts its box under the steps, and the tab row stays one row of icons.

## 2. WorkIt's home page today

Order and height at 1280 × 800: hero with the city (1,200px), the bridge
(260vh pinned), the pinned product tour (four stops × 80vh), the hiring
systems pipeline (pinned, 2,400px), the statement (6,200px), the
applications route (1,850px), the FAQ, the closing call to action. About
17,000px in all; more than half of it pins.

### What reads as AI-made, and why

1. **The headline swaps a gradient word** ("Stop _filling out
   applications_ by hand."). Rolling phrases in a brand gradient are a
   template trope. The hero names no product and shows a violet city, a
   picture of nothing WorkIt does.
2. **One heading size.** Every h2 is Plus Jakarta Sans 600 at 30 to
   36px with tight tracking and a violet eyebrow. Only the hero and the
   statement are bigger. With no steps between, nothing reads as a
   chapter and nothing as a detail.
3. **Scenes take over the screen.** The bridge, the tour, the pipeline
   and the statement each pin for one to six screens. The reader
   scrolls and the page does not move. This is the "AI demo" feel the
   user named.
4. **Glass and violet gradients on everything**: glass cards, a glass
   button, gradient panels. It is the default look of AI-made SaaS
   pages, and it hides which colour belongs to which feature.
5. **The sections do not hand off.** Product (tour), then where postings
   come from (hiring systems), then a warning (the statement), then the
   tracker (applications). The problem statement comes after the
   solution, and the hiring systems interrupt the product story.
6. **Epigram headings with a full stop** ("Slop applications get
   skipped.", "Every application, from saved to signed."), a pattern
   models overuse.
7. **No proof.** The testimonial is hidden until a real quote exists, so
   the page is all animation.

What already works and stays: the inset rounded panels (from Calendly),
the four features in one colour each (`features/catalog.ts`), the one
followed application (Stripe), the four story animations, the honest
claims in the copy, the FAQ, the closing call to action, the header and
the footer.

## 3. Direction, approved 2026-11-19

The user turned down a first, smaller plan as still too plain and approved
this one. Built on branch `KAN-923-home-page-redesign`.

1. **Hero**: a fixed headline ("Your job search, without the busywork.",
   72px), the sign-up pair with room for
   Download for Mac (KAN-922), then the four feature tabs and one card
   that plays the open feature's story in a framed box. Each story plays
   once, then the next tab opens. A richer gradient with grain.
2. **Logo strip**: real employers drifting slowly under one line.
3. **Statement**: "Slop applications get skipped" plays in a framed box,
   not a screen-high panel.
4. **Journey**, "One application, start to finish": four joined cards that
   follow the Stripe application (Build, Match, Fill, Track), each with
   three steps and a small picture that plays once.
5. **Product sections** for Resume Builder, Job Matching and Auto Apply:
   chip, serif heading, the feature page's deep dives as rows that open
   one at a time, and a square framed box with the open one's scene.
6. **Hiring systems grid**: the seven logos on tiles and "+8 more",
   replacing the 3D pipeline.
7. **FAQ** and the **closing call to action** over a slow row of status
   chips.

Type: Plus Jakarta Sans 500 for the hero and chapters, **Newsreader** 500
for product headings, Inter for text; the scale is `TYPE` in
`layout-parts.tsx`. Every animation sits in one shared framed box
(`StudioBox`). Nothing pins. The city hero, the bridge, the pinned tour,
the 3D pipeline and the applications route stay in the folder, unmounted.

**Revised the same day:** the user found the mesh gradient hero too close
to Calendly's, and picked, from four directions, a board of real postings
around the headline whose best fits light up; it became a grid of square
tiles round a large headline tile, the fits lit in soft violet with their
role and match (`hero-board.tsx`). The
sign-up pair went to Google's neutral theme. See
`marketing-design-system.md`.

Checked at 1280 × 800 and 1440 wide (Chrome) and at 375 × 812: no
horizontal scroll, no console errors, the hero's tabs advance and take a
click, and the journey's pictures play to their end. The page is about
9,200px at 1280 wide, from about 17,000.
