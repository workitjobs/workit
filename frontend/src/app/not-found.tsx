import type { Metadata } from "next";

import { ButtonLink } from "@/components/ui/button";

export const metadata: Metadata = { title: "Page Not Found" };

/**
 * The 404 for a URL no route matches, and for notFound() anywhere a closer
 * not-found file does not catch it: the heading, one line under it and a
 * way back in, where Next's stock page was black on white with neither.
 *
 * IT IS A BLOCK, NOT A PAGE FRAME (KAN-935): Next draws it inside whatever
 * layout the 404 happened under, so an unknown /features/ page shows it
 * between the marketing header and footer, and a page in a shell shows it
 * in the shell. Drawn in the grid frame (components/grid-frame.tsx, the
 * frame of /uninstalled and /coming-soon), it put a second logo row and a
 * second foot row inside the marketing page. So it takes the frame's look
 * as one cell: a white box edged by a hairline with an ink square at each
 * corner, the drafting grid's mark, and the frame's heading and line
 * inside. It was a white card with a border, a shadow and the logo.
 *
 * ITS IMPORTS LOAD WITH EVERY PAGE, for the reason below, so it is plain
 * utilities and the app's button: no marketing stylesheet, no font (its
 * heading is Plus Jakarta Sans only under a layout that sets that font's
 * variable, the marketing pages; elsewhere `font-display` falls back to
 * Inter) and no client component.
 *
 * THIS PAGE READS NOTHING FROM THE REQUEST: no cookies, no headers, no
 * session. Next renders the root not-found into the tree of every page under
 * the root layout, as the fallback the layout router holds, even when no 404
 * happens. So one cookies() read here (it used to call getCurrentAccount())
 * made every route dynamic (all 63 on 2026-10-24), the landing page and the
 * legal pages included: each visit ran a server render, and for a signed-in
 * visitor a GET /auth/me to the API, instead of coming from the CDN. A build
 * with the Supabase keys set (the deploy's) lists / as ○ (static) while this
 * holds; a build with no env file (CI's check) shows ○ either way, because
 * the Supabase client throws before it reaches cookies(), so it cannot catch
 * a regression.
 *
 * The way back is still the account's own home, decided when the button is
 * clicked rather than when the page renders: /go-home (app/go-home/route.ts) reads
 * the session and redirects with homePath(), so a company account goes to
 * its Overview, an applicant mid-onboarding to onboarding, and everyone else,
 * signed in or not, to Home. The label says Home, which
 * is where nearly everyone lands while the business side is hidden
 * (KAN-239). No prefetch: a prefetch of /go-home would run that session lookup
 * on every 404 view, for a click that rarely comes.
 */
export default function NotFound() {
  return (
    <main className="flex flex-1 items-center justify-center bg-white p-6">
      <div className="max-w-auth relative box-content w-full px-8 py-10 shadow-[0_0_0_1px_rgb(15_23_42/0.08)]">
        {["top-0 left-0", "top-0 left-full", "top-full left-0", "top-full left-full"].map((at) => (
          <i
            key={at}
            aria-hidden="true"
            className={`bg-ink absolute size-1.5 -translate-1/2 ${at}`}
          />
        ))}

        {/* The frame's heading (`AuthCard`, components/auth-card.tsx). */}
        <h1 className="font-display text-ink text-2xl leading-tight font-medium tracking-[-0.015em] text-balance sm:text-[1.75rem]">
          Page Not Found
        </h1>
        <p className="text-ink-meta mt-2 text-base text-pretty">
          The link may be broken, or the page may have moved.
        </p>

        <ButtonLink href="/go-home" prefetch={false} size="lg" className="mt-6 w-full">
          Back to Home
        </ButtonLink>
      </div>
    </main>
  );
}
