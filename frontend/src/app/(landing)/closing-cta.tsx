import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";

import { FaviconLogo } from "./favicon-logo";
import { CONTAINER, PANEL, PANEL_INSET, TYPE } from "./layout-parts";
import { EmailSignUpLink, SocialSignUpButton } from "./social-sign-up";

/**
 * The closing call to action a marketing page ends on, just above the
 * footer: a headline, a line and the hero's sign-up pair, on a rounded panel
 * in the page's own colour. The home page and every feature page draw it.
 * Its own file, not layout-parts.tsx, so the client scenes that import the
 * frame from there do not pull the sign-up's server action in.
 */
export function ClosingCta({
  title,
  subtitle,
  background,
  chips,
}: {
  title: string;
  subtitle: string;
  /** The panel's fill: a feature's backdrop, or the brand's on the home page. */
  background: string;
  /** The home page's row of status chips drifting above the title
   *  (KAN-923): what the steps look like as they land. Decorative. */
  chips?: readonly { label: string; company: string; domain: string }[];
}) {
  return (
    <section className={cn(PANEL_INSET, "mb-2 sm:mb-6")}>
      <div
        className={cn(
          PANEL,
          "overflow-hidden py-20 text-center sm:py-24",
          chips && "pt-12 sm:pt-16",
        )}
        style={{ background }}
      >
        {chips && (
          // Twice over for a seamless drift (`.drift-row`), faded at both
          // ends; held by Pause Animations, still with reduced motion.
          <div
            aria-hidden="true"
            className="mb-12 overflow-hidden [mask-image:linear-gradient(90deg,transparent,black_15%,black_85%,transparent)] sm:mb-14"
          >
            <ul
              className="drift-row flex w-max gap-3"
              style={{ "--drift": "55s" } as CSSProperties}
            >
              {[...chips, ...chips].map((chip, i) => (
                <li
                  key={i}
                  className="text-ink flex shrink-0 items-center gap-2 rounded-full bg-white py-1.5 pr-4 pl-1.5 text-sm font-medium shadow-[var(--mk-shadow-float)]"
                >
                  <FaviconLogo domain={chip.domain} className="size-7 rounded-full" />
                  {chip.label}
                  <span className="text-ink-meta font-normal">· {chip.company}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
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
