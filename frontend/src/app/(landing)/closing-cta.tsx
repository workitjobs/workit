import { cn } from "@/lib/cn";

import { CONTAINER, PANEL, PANEL_INSET, TYPE } from "./layout-parts";
import { EmailSignUpLink, SocialSignUpButton } from "./social-sign-up";

/**
 * The closing call to action a marketing page ends on, just above the
 * footer: a headline, a line and the hero's sign-up pair, on a rounded panel
 * in the page's own colour. Every feature page draws it. The home page
 * drew one too, over a drifting row of status chips, until the user had it
 * deleted (KAN-923, 2026-11-19): its FAQ now runs into the footer.
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
            <SocialSignUpButton provider="google" />
            <SocialSignUpButton provider="linkedin_oidc" />
            <div className="w-full text-center sm:basis-full">
              <EmailSignUpLink />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
