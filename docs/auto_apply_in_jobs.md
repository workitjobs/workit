# Auto Apply inside Jobs

**Superseded (2026-11-09), kept for its reasons.** A UI audit the same day
chose otherwise: the Cards view got a 1024px column (`max-w-feed`), the
right column was built and taken out (it took no width from a card on a
wide window, squeezed one on a 1280px window, and had no room in the split
view), and the queue's status became a count on the sidebar's Auto Apply
row, which stays. Read `frontend/CLAUDE.md` (the Cards view) for what is
built. The original plan follows. It moves the Auto Apply queue into the Jobs
page as a tab, gives the Jobs page a width limit and a right column, and
then removes Auto Apply from the sidebar. Read it before changing the
seeker sidebar, the Jobs page's layout or any `/auto-apply` address.

## Why

- The sidebar shows seven rows (Inbox is hidden, KAN-428). Auto Apply is the only one that is a step
  inside another row's work: a student picks jobs on the Jobs page and
  queues them there (each card's Auto Apply button). The queue is the
  result of that click, so it belongs beside the feed.
- The Jobs page's cards fill a column up to 1440px wide. Measured against
  Jobright on 2026-11-09, WorkIt's card filled about 89% of the window and
  Jobright's about 59%; the extra width is empty space between a card's
  facts and in front of its buttons. Jobright spends the rest on a right
  column.

## What moves, and what does not

Auto Apply is three pages today:

| Page | Address | Holds | Plan |
|---|---|---|---|
| The queue | `/auto-apply` | Up Next, the setup strip, Add Jobs, the Application Info card | Moves to `/jobs/queue`, a tab of the Jobs page |
| Application Info | `/auto-apply/info` | Work authorization, self-identification, application answers, transcript, writing samples, Workday sign-up | **Stays where it is** |
| Written Answers | `/auto-apply/answers` | The questions a batch's forms ask, and the student's answers | **Stays where it is** |

**Application Info does not go back to Profile.** KAN-550 moved it out of
Profile on purpose: only the autofiller and the student's Claude read it,
and it made Profile a long form the student scrolled past to find their
own name (`profile/profile-screen.tsx`, "What is not here"). Profile's
More of You card keeps linking to it. Both pages keep their addresses, so
the extension's links to them (below) keep working with no change.

## The target

**The Jobs page has two tabs**, as links (`SegmentedLinks`,
`components/ui/segmented-control.tsx`), under the page title: **Jobs**
(`/jobs`, the feed as today) and **Queue** (`/jobs/queue`), whose label
carries the number of queued and needs-you jobs, "Queue 4", so a full
queue shows from the feed. The view switch (cards or split) stays on the
Jobs tab only.

**The Queue tab** is today's `/auto-apply` page as it is: the setup strip
while the extension is missing, Up Next, Add Jobs and the Application Info
card. Its own heading block (`auto-apply-panel.tsx`) gives way to the tabs.

**The Jobs tab's column** stops at about 960px (cards, search and filter
row on one left edge). From `xl`, a right column of about 300px holds
three panels, each a link to where it is kept:

1. **What we match you against**: the resume the match scores read and a
   one-line summary of the saved preferences (`getSavedFilters`), each
   with an edit link. It explains a Weak Match.
2. **Auto Apply queue**: ready, needs you, in progress, and a link to the
   Queue tab. It shows what a card's Auto Apply button did.
3. **Up Next**: the next two dated entries (Home's `up-next.tsx`).

Under `xl` the column hides and the cards take the full 960px. The split
view keeps its own layout (list beside the job) and gets no right column.

**The sidebar** loses its Auto Apply row. On `/jobs/queue`,
`/auto-apply/info` and `/auto-apply/answers` the Jobs row is the current
one.

## Addresses and redirects

| Old | New | How |
|---|---|---|
| `/auto-apply` (with any query) | `/jobs/queue` (same query) | A permanent redirect in `frontend/next.config.ts`'s `redirects()`, so old bookmarks and older extension builds land |
| `/auto-apply/info` | unchanged | — |
| `/auto-apply/answers` | unchanged | — |

`/jobs/queue` is a static segment beside `jobs/[jobId]`; Next.js matches
the static one first. A job's id is never the word `queue`. The Jobs
layout (`jobs/layout.tsx`) draws the jobs rail in the split view for
every page under `/jobs`; the Queue tab must pass through it with no rail.

## Every place that names `/auto-apply` today

Web app (`frontend/src/app/(seeker)/`):

- `seeker-sidebar.tsx`: the nav row, and its comment ("Auto Apply sits
  between Jobs and Applications").
- `bar-title.tsx`, `back-link.tsx`: the top bar's title and the back
  link's parent for `/auto-apply`; the info and answers pages' back links
  (`info/page.tsx`, `info/loading.tsx`, `answers/page.tsx`,
  `answers/loading.tsx`) point to `/auto-apply` and move to `/jobs/queue`.
- `auto-apply/query.ts`: builds the queue's address with its filters.
- `auto-apply/info-link.tsx`, `auto-apply/up-next.tsx`: links to the info
  and answers pages (unchanged).
- `home/top-matches-list.tsx`: the toast's View Queue.
- `jobs/[jobId]/page-actions.tsx`: a comment on rows that open job pages.

Chrome extension (`autofiller_extension/`), runtime:

- `src/popup/popup.js`: opens `${base}/auto-apply`. Change it to
  `/jobs/queue`; the redirect covers builds already installed.
- `src/background/background.js`: opens `/auto-apply/info#writing-samples`
  and `/auto-apply/answers`. Unchanged.

Extension tests (`autofiller_extension/test/*.extension.spec.ts`): ten
specs `goto` `/auto-apply`. Move them to `/jobs/queue` in the same PR as
the redirect, or they test the redirect instead of the page.

## Build order

Each step is one PR and leaves the app whole.

1. **Width limit and right column** on the Jobs tab. No address changes.
2. **Queue tab**: add `/jobs/queue` (the queue page's content, moved), the
   Jobs and Queue tabs, the redirect from `/auto-apply`, the back links,
   the bar title, Home's View Queue, the popup's address and the
   extension specs. The sidebar row stays and points to `/jobs/queue`.
3. **Remove the sidebar row**, and update its comment and
   `frontend/CLAUDE.md`. Last, so step 2 can be checked with the row still
   there.

Steps 2 and 3 change the extension's popup, which ships through the Chrome
Web Store, not on merge; the redirect keeps the old popup working until
then.

## Still open

- The Queue tab's count: queued plus needs-you, or needs-you alone. The
  count is read on every Jobs page load, so it must come from the read the
  page already makes (`getApplicationStages`), not a new one.
- The tab names: "Jobs" and "Queue", or "Recommended" and "Auto Apply
  Queue".
- Whether a phone shows the tabs or keeps Auto Apply in the menu sheet.
