import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Logo } from "@/components/logo";
import { EXTENSION_STEP_PATH } from "@/app/onboarding/applicant/steps";

export const metadata: Metadata = {
  title: "Set Up the Extension",
  description: "How to set up WorkIt's extension and account before your first autofill.",
};

const STEPS: { title: string; body: ReactNode }[] = [
  {
    title: "Turn off other autofillers, and pin WorkIt",
    body: "Turn off Simplify, Jobright, and similar tools — two autofillers can fight over the same field. Then pin WorkIt from the puzzle-piece icon beside your address bar.",
  },
  {
    title: "Create your free account and finish onboarding",
    body: "Sign up with Google, LinkedIn, or email (confirm your email first if you used one), then WorkIt walks you through your résumé, school, and job preferences.",
  },
  {
    title: "Add your experience",
    body: "Open the Resumes page and add your work history and skills, so WorkIt has real detail to write into each application.",
  },
  {
    title: "Try the practice application, then go live",
    body: "Onboarding ends with a safe practice run first. After that, open a real posting, click the WorkIt icon, press Autofill This Page, review every field, then press the hiring site's own Submit yourself.",
  },
];

/**
 * Reached right after a Chrome Web Store install (install.js's `installed`,
 * KAN-471/KAN-495) or on demand from the popup's "Set Up WorkIt" button,
 * signed in or not. Outside both the (seeker) and (landing) groups — same
 * tier as /connect/claude — since a just-installed student may not be
 * signed in yet, and this is instructional product UI, not a marketing
 * page.
 *
 * "I Already Have One" goes to `EXTENSION_STEP_PATH`
 * (`/onboarding/applicant?step=extension`), not plain `/login`: that page's
 * own sign-in redirect (`/login?next=`) still applies for a signed-out
 * visitor, and lets onboarding decide where a signed-in one goes next --
 * a student still finishing onboarding lands on its Extension step, same
 * as a brand-new one, and a student who already finished it is sent on to
 * Home with a success message instead (KAN-864, onboarding/applicant's
 * page.tsx). install.js used to open that path directly (before KAN-495),
 * which kept a finished student on the route to the Practice step; sending
 * them to plain `/login` instead would drop them on /home with no way back
 * to it (found in review, KAN-495). Both links are plain relative paths,
 * so they always resolve on whatever origin served this page -- never a
 * hardcoded host, and never a build-time env value that could point at a
 * local dev server in production (the failure mode `/connect/claude/add`
 * below exists to avoid, and the connector link's own doc).
 *
 * Connecting Claude is optional, so it is its own card after the numbered
 * steps, not folded into them: it links to `/connect/claude/add`
 * (lib/claude-connector.ts), never `claudeConnectorLink()` directly, since
 * this page is plain and could prerender -- the same reason the extension's
 * own add-Claude step and KAN-368's /docs/mcp fix use that route instead of
 * reading the connector's address at build time.
 */
export default function ExtensionSetupPage() {
  return (
    <main className="flex flex-1 justify-center p-6 py-16">
      <div className="w-full max-w-2xl">
        <Logo size="card" className="mx-auto" />

        <h1 className="text-title text-ink mt-4 text-center">Thanks for Choosing WorkIt</h1>
        <p className="text-body text-ink-muted mt-2 text-center">
          We help make your job search easier and less stressful. Before WorkIt can start filling
          out applications for you, set up your browser with the steps below.
        </p>

        <ol className="mt-8 flex flex-col gap-4">
          {STEPS.map(({ title, body }, i) => (
            <Card as="li" key={title} padding="lg" className="flex gap-4">
              <span
                aria-hidden
                className="bg-brand-tint text-brand text-body flex size-8 shrink-0 items-center justify-center rounded-full font-semibold"
              >
                {i + 1}
              </span>
              <div className="text-body text-ink-muted flex min-w-0 flex-1 flex-col">
                <h2 className="text-subtitle text-ink mb-1">{title}</h2>
                {body}
              </div>
            </Card>
          ))}
        </ol>

        <Card padding="lg" className="mt-4 flex items-start gap-4">
          <div className="text-body text-ink-muted flex min-w-0 flex-1 flex-col">
            <h2 className="text-subtitle text-ink mb-1 flex items-center gap-2">
              Connect your Claude <Badge variant="tag">Optional</Badge>
            </h2>
            Let your own Claude write application answers and research companies for you — built
            right into the extension. Add it any time from the panel&rsquo;s Settings.
          </div>
          <ButtonLink
            href="/connect/claude/add"
            variant="secondary"
            size="lg"
            target="_blank"
            rel="noreferrer"
            className="shrink-0"
          >
            Add to Claude
          </ButtonLink>
        </Card>

        <div className="mt-8 flex justify-center gap-3">
          <ButtonLink href="/signup" size="lg">
            Create Your Account
          </ButtonLink>
          <ButtonLink href={EXTENSION_STEP_PATH} variant="secondary" size="lg">
            I Already Have One
          </ButtonLink>
        </div>
      </div>
    </main>
  );
}
