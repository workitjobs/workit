import Link from "next/link";

import { cn } from "@/lib/cn";
import { signInWithOAuth, type OAuthProvider } from "@/lib/oauth-actions";

import { BUTTON_SHAPE, BUTTON_SIZES } from "./buttons";
import { site } from "./data";
import { OAuthForm, OAuthSubmit } from "./oauth-form";

/**
 * The way in for a student with neither account, under every pair of
 * social buttons: /signup takes an email and a password. With only Google
 * and LinkedIn on the page, that way in was hidden behind the header's
 * button (KAN-368). Its ::after widens the tap to about 44px.
 */
export function EmailSignUpLink() {
  return (
    <p className="text-ink-meta text-sm">
      Or{" "}
      <Link
        href={site.primaryCta.href}
        className="text-ink relative font-medium underline decoration-slate-300 underline-offset-4 after:absolute after:-inset-x-2 after:-inset-y-3 after:content-[''] hover:decoration-current"
      >
        sign up with email
      </Link>
    </p>
  );
}

/**
 * "Sign up with Google / LinkedIn", following Google's sign-in branding
 * guidelines, neutral theme (KAN-923): #F2F2F2 fill, no stroke, #1F1F1F
 * Google Sans Medium 14/20 text, standard full-colour logos (never
 * recoloured). The light theme's #747775 border read as a bordered,
 * AI-made button, and the dark theme was too heavy for the user, so the
 * pair is the neutral theme, the guidelines' only one with no stroke; it
 * matches `SecondaryButton`'s soft grey, so a Download for Mac button
 * (KAN-922) sits beside it as a secondary. LinkedIn uses the same treatment
 * so the pair matches
 * (its blue tile keeps a white "in"), and
 * both take the marketing buttons' shape and height (buttons.tsx). Each
 * posts to the same OAuth action as the buttons on /signup, and says
 * "Opening Google…" while it runs (oauth-form.tsx). The home hero and every
 * feature page's hero and closing call to action draw the pair.
 * 44px tall at every width (KAN-580), the marketing buttons' `md` height:
 * Google's rules set a least height, not a most.
 * https://developers.google.com/identity/branding-guidelines
 */
export function SocialSignUpButton({
  provider,
  verb = "Sign up",
  next = null,
  wide,
}: {
  provider: OAuthProvider;
  /** "Continue" on the auth screens, where the same button signs a
   *  returning student in (components/auth-alternatives.tsx). */
  verb?: string;
  /** /login's page to go back to (lib/sign-in-next.ts). */
  next?: string | null;
  /** The button fills its column: the auth screens stack the pair. */
  wide?: boolean;
}) {
  const google = provider === "google";
  const name = google ? "Google" : "LinkedIn";
  return (
    <OAuthForm
      action={signInWithOAuth.bind(null, provider, next)}
      className={wide ? "w-full" : "w-full max-w-72 sm:w-auto"}
    >
      <OAuthSubmit
        label={`${verb} with ${name}`}
        pendingLabel={`Opening ${name}…`}
        className={cn(
          BUTTON_SHAPE,
          BUTTON_SIZES.md,
          "font-google w-full gap-2.5 bg-[#F2F2F2] px-3 text-sm/5 font-medium text-[#1F1F1F] transition-colors hover:bg-[#E8E8E8] disabled:cursor-progress disabled:hover:bg-[#F2F2F2]",
        )}
        icon={
          google ? (
            <svg viewBox="0 0 48 48" className="size-5 shrink-0" aria-hidden="true">
              <path
                fill="#EA4335"
                d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
              />
              <path
                fill="#4285F4"
                d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
              />
              <path
                fill="#FBBC05"
                d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
              />
              <path
                fill="#34A853"
                d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
              />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" className="size-5 shrink-0" aria-hidden="true">
              {/* White under the mark, so its "in" reads white on the dark
                  fill, as LinkedIn's own logo does. */}
              <rect x="2" y="2" width="20" height="20" rx="2" fill="white" />
              <path
                fill="#0A66C2"
                d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 1 1 0-4.125 2.062 2.062 0 0 1 0 4.125zM7.119 20.452H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
              />
            </svg>
          )
        }
      />
    </OAuthForm>
  );
}
