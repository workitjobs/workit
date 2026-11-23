import { cn } from "@/lib/cn";

import { PrimaryButton } from "./buttons";
import { CONTAINER, PANEL, PANEL_INSET, TYPE } from "./layout-parts";
import { SessionSwap } from "./session-swap";
import { EmailSignUpLink, SocialSignUpButton } from "./social-sign-up";

/**
 * The closing call to action a marketing page ends on, just above the
 * footer: a headline, a line and the hero's sign-up pair, on a rounded panel
 * in the page's own colour. Every feature page draws it, and the home page
 * again since 2026-11-23 (the user's ask: a get started section above the
 * footer), on WorkIt's violet blend, the page's one box that stands for
 * WorkIt as a whole. The home page's first one, over a drifting row of
 * status chips, was deleted on 2026-11-19 (KAN-923); this one is the
 * feature pages' own, with nothing added: a headline, one line, the buttons.
 * A signed-in student sees one Open WorkIt in place of the sign-up pair, as
 * in the header and the home hero (`SessionSwap`).
 * Its own file, not layout-parts.tsx, so the client scenes that import the
 * frame from there do not pull the sign-up's server action in.
 */
export function ClosingCta({
  title,
  subtitle,
  background,
}: {
  title: string;
  subtitle: string;
  /** The panel's fill: the feature's backdrop. */
  background: string;
}) {
  return (
    <section className={cn(PANEL_INSET, "mb-2 sm:mb-6")}>
      <div
        className={cn(PANEL, "overflow-hidden py-20 text-center sm:py-24")}
        style={{ background }}
      >
        <div className={CONTAINER}>
          <h2 className={cn(TYPE.chapter, "text-ink mx-auto max-w-3xl")}>{title}</h2>
          <p className={cn(TYPE.lead, "text-ink-muted mx-auto mt-5 max-w-xl")}>{subtitle}</p>
          <div className="mt-8 flex flex-col flex-wrap items-center justify-center gap-3 sm:flex-row">
            <SessionSwap
              signedOut={
                <>
                  <SocialSignUpButton provider="google" />
                  <SocialSignUpButton provider="linkedin_oidc" />
                </>
              }
              signedIn={
                <PrimaryButton href="/go-home" prefetch={false} size="lg">
                  Open WorkIt
                </PrimaryButton>
              }
            />
            <SessionSwap
              signedOut={
                <div className="w-full text-center sm:basis-full">
                  <EmailSignUpLink />
                </div>
              }
              signedIn={null}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
